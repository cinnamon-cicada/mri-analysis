"""
Minimal FastAPI entrypoint for the Cloud Run Job worker.
Cloud Tasks POST /run with {"job_id": "...", "file_ref": "..."}.
The job terminates (process exits) immediately after the task completes.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from worker import process_job
from storage import get_storage

app = FastAPI()


@app.post("/run")
async def run(request: Request):
    import asyncio
    body = await request.json()
    job_id = body["job_id"]
    file_ref = body["file_ref"]

    storage = get_storage()
    storage.set_job(job_id, {"status": "processing"})

    try:
        result = await asyncio.to_thread(process_job, job_id, file_ref)
        storage.set_results(job_id, result)
        storage.set_job(job_id, {"status": "completed"})
        return JSONResponse({"status": "completed"})
    except Exception as e:
        storage.set_job(job_id, {"status": "failed", "error": str(e)})
        return JSONResponse({"status": "failed", "error": str(e)}, status_code=500)
