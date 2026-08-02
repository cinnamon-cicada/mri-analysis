"""Deface uploaded structural MRI volumes before they're ever persisted at
rest or fed to FastSurfer. A full head T1 volume is a known re-identification
vector — the subject's face can be reconstructed from the surface geometry —
so this has to run before the raw upload is stored or processed, not after.
"""
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("mri.deface")

DEFACE_TIMEOUT_SECONDS = 300


def deface_file(path: Path) -> None:
    """Deface the NIfTI volume at `path` in place via `pydeface`.

    Defacing only removes non-brain tissue (face/ears), so running it before
    FastSurfer sees the file doesn't affect cortical/subcortical segmentation.
    Raises on failure — callers must not fall back to processing/storing the
    original (faced) file if this fails.
    """
    path = Path(path)
    tmp_out = path.with_name(f"deface_tmp_{path.name}")

    try:
        subprocess.run(
            ["pydeface", str(path), "--outfile", str(tmp_out), "--force"],
            check=True,
            capture_output=True,
            text=True,
            timeout=DEFACE_TIMEOUT_SECONDS,
        )
    except subprocess.CalledProcessError as e:
        logger.error(
            "deface_failed",
            extra={"event": "deface_failed", "stdout": e.stdout[-3000:], "stderr": e.stderr[-3000:]},
        )
        raise
    except subprocess.TimeoutExpired:
        logger.error("deface_timeout", extra={"event": "deface_timeout"})
        raise

    tmp_out.replace(path)
