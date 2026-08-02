"""
Job worker — runs the full MRI pipeline for one uploaded scan.

In production this runs as a Cloud Run Job execution, started by the
Firestore-triggered dispatcher (see dispatcher.py) via the Cloud Run
Admin API. In local dev it runs in a background thread via LocalQueue.
"""
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("mri.worker")

FREESURFER_LICENSE = os.environ.get("FREESURFER_LICENSE", "./license.txt")
FASTSURFER_OUTPUT_DIR = os.environ.get("FASTSURFER_OUTPUT_DIR", "./processed_data/web_jobs")


def process_job(job_id: str, file_ref: str) -> dict:
    """
    Full pipeline for one uploaded MRI file:
      1. Stage file in the directory structure FastSurfer expects
      2. Run FastSurfer via Docker
      3. Compare FastSurfer output against benchmark stats
      4. Return results dict

    Parameters
    ----------
    job_id : str
    file_ref : str
        Storage reference from StorageBackend.store_file()

    Returns
    -------
    dict  Percentile results, written to storage by the queue runner.
    """
    from analysis import compare_to_benchmark
    from deface import deface_file
    from storage import get_storage
    from utils import run_fastsurfer

    storage = get_storage()

    logger.info("job_started", extra={"event": "job_started", "job_id": job_id})
    try:
        with tempfile.TemporaryDirectory() as staging:
            subject_id = f"job_{job_id[:8]}"
            anat_dir = Path(staging) / subject_id / "anat"
            anat_dir.mkdir(parents=True)

            staged_file = anat_dir / f"{subject_id}_T1w.nii.gz"
            staged_file.write_bytes(storage.load_file(file_ref))

            # Deface before anything else touches this file: overwrites the
            # staged copy in place, then replaces the persisted raw upload
            # with the defaced bytes so the facially-intact original is at
            # rest for as short a window as possible (bounded by queue depth,
            # not by how long the file is retained overall — see the
            # storage.delete_file() call below, which removes it entirely
            # once the comparison it exists for is done).
            deface_file(staged_file)
            file_ref = storage.store_file(job_id, staged_file.read_bytes())

            output_dir = Path(FASTSURFER_OUTPUT_DIR) / job_id
            run_fastsurfer(
                subjects=[subject_id],
                input_dir=staging,
                output_dir=str(output_dir),
                freesurfer_license=FREESURFER_LICENSE,
            )

            subject_output = output_dir / subject_id
            results = compare_to_benchmark(str(subject_output))

            # The scan has served its purpose the moment the comparison is
            # done — only the measured values/percentiles need to survive
            # past this point, not the volume itself. Delete unconditionally
            # here (not in a `finally`) so a failed comparison leaves the
            # file in place for retry/debugging rather than deleting on error.
            storage.delete_file(file_ref)
    except Exception:
        logger.exception("job_failed", extra={"event": "job_failed", "job_id": job_id})
        raise

    logger.info("job_completed", extra={"event": "job_completed", "job_id": job_id})
    return results


def attach_results_to_user(job_id: str, results: dict) -> None:
    """Copy a completed job's measured values and percentiles onto the
    uploading user's record. This is the only place those values persist
    once the raw scan is deleted (see process_job), so it's a
    {segment: {value, percentile}} map, not just percentiles.

    No-op for anonymous uploads (jobs without a `uid`). Called from both
    completion paths (LocalQueue and the Cloud Run Job entrypoint) so /self
    can show the signed-in user their latest results.
    """
    from storage import get_storage

    storage = get_storage()
    job = storage.get_job(job_id) or {}
    uid = job.get("uid")
    if not uid:
        return

    flat = {
        label: {"value": value, "percentile": pct}
        for label, pct, value in (
            results.get("volume_percentiles", []) + results.get("thickness_percentiles", [])
        )
    }
    storage.set_user(uid, {"benchmark_results": flat, "last_job_id": job_id})
