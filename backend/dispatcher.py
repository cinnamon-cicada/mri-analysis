"""
Firestore-triggered dispatcher — replaces Cloud Tasks as the thing that
decides "start the next job."

Deployed as a 2nd-gen Cloud Function (backend/requirements.txt lists its
deps), triggered on every write to the "jobs" Firestore collection. On
each firing it ignores the event payload and just re-derives live state:
inside a Firestore transaction, count docs with status == "processing";
if under MAX_CONCURRENT, atomically claim the oldest "queued" doc by
flipping it to "processing", then (outside the transaction) start a
Cloud Run Job execution for it via the Cloud Run Admin API, passing
JOB_ID/FILE_REF as container env overrides.

This is self-driving: when a running job finishes and worker.py flips its
status to completed/failed, that write re-triggers this function, which
then picks up the next queued job. No polling or Cloud Scheduler needed.

Deploy note: the Python Functions Framework buildpack looks for main.py
by default; since this module is named dispatcher.py, the deploy command
needs --set-build-env-vars=GOOGLE_FUNCTION_SOURCE=dispatcher.py (see
Phase 4 in the handoff).

Requires a composite Firestore index on jobs(status ASC, created_at ASC)
— see infra/firestore.indexes.json — since the queued-job query filters
on status and orders by a different field.
"""
import os

import functions_framework
from google.cloud import firestore, run_v2

MAX_CONCURRENT = 2

PROJECT = os.environ["GCP_PROJECT"]
LOCATION = os.environ.get("GCP_WORKER_JOB_LOCATION", "us-central1")
JOB_NAME = os.environ.get("GCP_WORKER_JOB_NAME", "mri-worker")

_db = firestore.Client()
_jobs_client = run_v2.JobsClient()


@functions_framework.cloud_event
def dispatch(cloud_event) -> None:
    transaction = _db.transaction()
    claimed = _claim_next_job(transaction)
    if claimed is not None:
        job_id, file_ref = claimed
        _start_execution(job_id, file_ref)


@firestore.transactional
def _claim_next_job(transaction) -> tuple[str, str] | None:
    """Atomically claim the oldest queued job if a processing slot is free.

    Returns (job_id, file_ref) if a job was claimed, else None.
    """
    jobs_ref = _db.collection("jobs")

    processing_count = (
        jobs_ref.where("status", "==", "processing")
        .count()
        .get(transaction=transaction)
    )[0][0].value
    if processing_count >= MAX_CONCURRENT:
        return None

    queued = list(
        jobs_ref.where("status", "==", "queued")
        .order_by("created_at")
        .limit(1)
        .get(transaction=transaction)
    )
    if not queued:
        return None

    doc = queued[0]
    transaction.update(doc.reference, {"status": "processing"})
    return doc.id, doc.to_dict()["file_ref"]


def _start_execution(job_id: str, file_ref: str) -> None:
    request = run_v2.RunJobRequest(
        name=f"projects/{PROJECT}/locations/{LOCATION}/jobs/{JOB_NAME}",
        overrides=run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(
                    env=[
                        run_v2.EnvVar(name="JOB_ID", value=job_id),
                        run_v2.EnvVar(name="FILE_REF", value=file_ref),
                    ]
                )
            ],
            task_count=1,
        ),
    )
    _jobs_client.run_job(request=request)
