"""
Job worker — runs the full MRI pipeline for one uploaded scan.

In production this runs as a Cloud Run Job execution, started by the
Firestore-triggered dispatcher (see dispatcher.py) via the Cloud Run
Admin API. In local dev it runs in a background thread via LocalQueue.
"""
import os
import tempfile
from pathlib import Path

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
    from storage import get_storage
    from utils import run_fastsurfer

    storage = get_storage()

    with tempfile.TemporaryDirectory() as staging:
        subject_id = f"job_{job_id[:8]}"
        anat_dir = Path(staging) / subject_id / "anat"
        anat_dir.mkdir(parents=True)

        staged_file = anat_dir / f"{subject_id}_T1w.nii.gz"
        staged_file.write_bytes(storage.load_file(file_ref))

        output_dir = Path(FASTSURFER_OUTPUT_DIR) / job_id
        run_fastsurfer(
            subjects=[subject_id],
            input_dir=staging,
            output_dir=str(output_dir),
            freesurfer_license=FREESURFER_LICENSE,
        )

        subject_output = output_dir / subject_id
        return compare_to_benchmark(str(subject_output))


def attach_results_to_user(job_id: str, results: dict) -> None:
    """Copy a completed job's percentiles onto the uploading user's record.

    No-op for anonymous uploads (jobs without a `uid`). Called from both
    completion paths (LocalQueue and the Cloud Run Job entrypoint) so /self can
    show the signed-in user their latest results as a flat {segment: percentile}
    map, per the user data model.
    """
    from storage import get_storage

    storage = get_storage()
    job = storage.get_job(job_id) or {}
    uid = job.get("uid")
    if not uid:
        return

    flat = {
        label: pct
        for label, pct in (
            results.get("volume_percentiles", []) + results.get("thickness_percentiles", [])
        )
    }
    storage.set_user(uid, {"benchmark_results": flat, "last_job_id": job_id})
