import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from queue_system import get_queue
from storage import get_storage

import os

limiter = Limiter(key_func=get_remote_address)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Serve frontend in local dev; in production Firebase Hosting handles static assets.
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    templates = Jinja2Templates(directory=FRONTEND_DIR)

    @app.get("/")
    async def home(request: Request):
        return templates.TemplateResponse(request, "home.html")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/upload")
@limiter.limit("5/minute")
async def upload(request: Request, file: UploadFile = File(...)):
    storage = get_storage()
    if storage.count_active_jobs() >= 5:
        return JSONResponse(
            {"error": "capacity", "message": "Please upload later due to reaching server capacity."},
            status_code=503,
        )

    job_id = str(uuid.uuid4())
    data = await file.read()

    file_ref = storage.store_file(job_id, data)
    # file_ref/created_at are read back by the Firestore-triggered dispatcher
    # (dispatcher.py), which has no other way to learn which file a queued
    # job refers to or which queued job is oldest.
    storage.set_job(job_id, {"status": "queued", "file_ref": file_ref, "created_at": time.time()})

    await get_queue().enqueue(job_id, file_ref)

    return {"job_id": job_id, "status": "queued"}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = get_storage().get_job(job_id)
    if job is None:
        return JSONResponse({"status": "not_found"}, status_code=404)
    return JSONResponse(job)


@app.get("/results/{job_id}")
async def get_results(job_id: str):
    storage = get_storage()
    job = storage.get_job(job_id)
    if job is None:
        return JSONResponse({"error": "job not found"}, status_code=404)
    if job.get("status") != "completed":
        return JSONResponse({"error": "results not ready", "status": job.get("status")}, status_code=202)
    results = storage.get_results(job_id)
    if results is None:
        return JSONResponse({"error": "results missing"}, status_code=500)
    return JSONResponse(results)
