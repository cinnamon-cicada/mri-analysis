"""
Queue abstraction for MRI processing jobs.

Local backend (default) — dispatches jobs as asyncio tasks in the same process.
Cloud Tasks backend — enqueues to GCP Cloud Tasks, which triggers a Cloud Run Job.

Switch by setting QUEUE_BACKEND=cloudtasks and providing:
  GCP_PROJECT, GCP_QUEUE_LOCATION, GCP_QUEUE_NAME, GCP_WORKER_URL
"""
import asyncio
import json
import os
from abc import ABC, abstractmethod


class QueueBackend(ABC):
    @abstractmethod
    async def enqueue(self, job_id: str, file_ref: str) -> None:
        """Dispatch a processing job."""


class LocalQueue(QueueBackend):
    """Runs the worker in the background on the same process via asyncio.

    Caps FastSurfer runs at 2 concurrent, matching the production dispatcher's
    slot limit — jobs beyond that sit at status "queued" until a slot frees.
    """

    async def enqueue(self, job_id: str, file_ref: str) -> None:
        asyncio.create_task(_run_local(job_id, file_ref))


_local_semaphore = asyncio.Semaphore(2)


async def _run_local(job_id: str, file_ref: str) -> None:
    from storage import get_storage
    from worker import process_job

    storage = get_storage()
    async with _local_semaphore:
        storage.set_job(job_id, {"status": "processing"})
        try:
            result = await asyncio.to_thread(process_job, job_id, file_ref)
            storage.set_results(job_id, result)
            storage.set_job(job_id, {"status": "completed"})
        except Exception as e:
            storage.set_job(job_id, {"status": "failed", "error": str(e)})


class CloudTasksQueue(QueueBackend):
    """
    Enqueues to GCP Cloud Tasks. The task HTTP-POSTs the job payload to
    GCP_WORKER_URL/run, which should be a deployed Cloud Run Job endpoint.
    """

    def __init__(self):
        from google.cloud import tasks_v2
        self._client = tasks_v2.CloudTasksClient()
        self._parent = self._client.queue_path(
            os.environ["GCP_PROJECT"],
            os.environ["GCP_QUEUE_LOCATION"],
            os.environ["GCP_QUEUE_NAME"],
        )
        self._worker_url = os.environ["GCP_WORKER_URL"]
        self._api_sa_email = os.environ["GCP_API_SA_EMAIL"]

    async def enqueue(self, job_id: str, file_ref: str) -> None:
        payload = json.dumps({"job_id": job_id, "file_ref": file_ref}).encode()
        task = {
            "http_request": {
                "http_method": "POST",
                "url": f"{self._worker_url}/run",
                "headers": {"Content-Type": "application/json"},
                "body": payload,
                "oidc_token": {
                    "service_account_email": self._api_sa_email,
                },
            }
        }
        await asyncio.to_thread(
            self._client.create_task,
            request={"parent": self._parent, "task": task},
        )


_queue: QueueBackend | None = None


def get_queue() -> QueueBackend:
    global _queue
    if _queue is None:
        if os.environ.get("QUEUE_BACKEND") == "cloudtasks":
            _queue = CloudTasksQueue()
        else:
            _queue = LocalQueue()
    return _queue
