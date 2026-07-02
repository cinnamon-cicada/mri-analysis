"""
Queue abstraction for MRI processing jobs.

Local backend (default) — dispatches jobs as asyncio tasks in the same
process, capped at 2 concurrent FastSurfer runs.
Firestore backend — enqueue() is a no-op; writing the job doc via
storage.set_job() (status="queued") IS the trigger. A Firestore-triggered
Cloud Function (dispatcher.py) watches the "jobs" collection and starts
Cloud Run Job executions directly via the Cloud Run Admin API, enforcing
the same 2-concurrent cap transactionally against live job status.

Switch by setting QUEUE_BACKEND=firestore for production (STORAGE_BACKEND
should also be "firebase" in that case).
"""
import asyncio
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


_local_semaphore: asyncio.Semaphore | None = None


def _get_local_semaphore() -> asyncio.Semaphore:
    # Lazily created (rather than at import time) so it binds to whichever
    # event loop is actually running when first used, not whatever loop
    # happened to exist at import time.
    global _local_semaphore
    if _local_semaphore is None:
        _local_semaphore = asyncio.Semaphore(2)
    return _local_semaphore


async def _run_local(job_id: str, file_ref: str) -> None:
    from storage import get_storage
    from worker import process_job

    storage = get_storage()
    async with _get_local_semaphore():
        storage.set_job(job_id, {"status": "processing"})
        try:
            result = await asyncio.to_thread(process_job, job_id, file_ref)
            storage.set_results(job_id, result)
            storage.set_job(job_id, {"status": "completed"})
        except Exception as e:
            storage.set_job(job_id, {"status": "failed", "error": str(e)})


class NoopQueue(QueueBackend):
    """
    Production backend: does nothing on enqueue. The job doc written by
    storage.set_job(status="queued") is itself the trigger — dispatcher.py
    reacts to that Firestore write and starts a Cloud Run Job execution.
    """

    async def enqueue(self, job_id: str, file_ref: str) -> None:
        pass


_queue: QueueBackend | None = None


def get_queue() -> QueueBackend:
    global _queue
    if _queue is None:
        if os.environ.get("QUEUE_BACKEND") == "firestore":
            _queue = NoopQueue()
        else:
            _queue = LocalQueue()
    return _queue
