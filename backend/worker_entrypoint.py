"""
Plain-script entrypoint for the Cloud Run Job worker.

Cloud Run Jobs has no HTTP request/response — the dispatcher (see
dispatcher.py) starts an execution via the Cloud Run Admin API, passing
JOB_ID and FILE_REF as per-execution container env var overrides. This
script reads those, runs the pipeline, and reports the outcome to storage.

Status is NOT set to "processing" here — the dispatcher already claimed
the slot and set that status transactionally before triggering this
execution. This script only ever transitions a job to "completed" or
"failed".
"""
import os
import sys

from storage import get_storage
from worker import process_job


def main() -> int:
    job_id = os.environ["JOB_ID"]
    file_ref = os.environ["FILE_REF"]

    storage = get_storage()
    try:
        result = process_job(job_id, file_ref)
        storage.set_results(job_id, result)
        storage.set_job(job_id, {"status": "completed"})
        return 0
    except Exception as e:
        storage.set_job(job_id, {"status": "failed", "error": str(e)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
