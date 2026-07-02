import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from analysis import get_population_distribution, list_population_segments
from auth import verify_bearer_token
from queue_system import get_queue
from storage import get_storage

import os

limiter = Limiter(key_func=get_remote_address)

# Hard cap on an uploaded scan, matching infra/storage.rules. Enforced by
# reading the body in chunks so an oversized (or unbounded/chunked) upload is
# rejected before it can exhaust the API process's memory.
MAX_UPLOAD_BYTES = 200 * 1024 * 1024

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


async def _read_capped(file: UploadFile, limit: int) -> bytes | None:
    """Read the whole upload, or return None once it exceeds `limit` bytes.

    Bounds peak memory at ~limit regardless of Content-Length (which may be
    absent or spoofed on a chunked request), so it's a real DoS guard rather
    than a post-hoc size check on an already-buffered body.
    """
    chunks = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def _authorize_job_access(job: dict, authorization: str | None) -> None:
    """Gate access to a job's status/results.

    Anonymous jobs (no `uid`) are protected only by the unguessable UUID job
    id, preserving the anonymous-upload flow. A job tied to a signed-in user
    additionally requires that user's own bearer token — otherwise anyone
    holding the id could read that user's results.
    """
    owner = job.get("uid")
    if owner is None:
        return
    claims = verify_bearer_token(authorization)
    if claims.get("uid") != owner:
        raise HTTPException(status_code=403, detail="forbidden")


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

    @app.get("/data")
    async def data_page(request: Request):
        return templates.TemplateResponse(request, "data.html")

    @app.get("/login")
    async def login_page(request: Request):
        return templates.TemplateResponse(request, "login.html")

    @app.get("/self")
    async def self_page(request: Request):
        return templates.TemplateResponse(request, "self.html")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/api/firebase-config")
async def firebase_config():
    """Public Firebase web config for the client SDK, sourced from env so no
    keys are committed. Returns 501 when auth isn't configured (e.g. local dev
    without Firebase), which the frontend treats as 'sign-in unavailable'."""
    api_key = os.environ.get("FIREBASE_API_KEY")
    if not api_key:
        return JSONResponse({"error": "auth not configured"}, status_code=501)
    project_id = os.environ.get("GCP_PROJECT", "the-brain-benchmark-project")
    return {
        "apiKey": api_key,
        "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", f"{project_id}.firebaseapp.com"),
        "projectId": project_id,
        "appId": os.environ.get("FIREBASE_APP_ID", ""),
    }


@app.get("/api/me")
async def me(authorization: str | None = Header(default=None)):
    """Return the signed-in user's record, creating it (with email) on first
    access. Requires a valid Firebase ID token."""
    claims = verify_bearer_token(authorization)
    uid = claims["uid"]
    email = claims.get("email")

    storage = get_storage()
    user = storage.get_user(uid) or {}
    if email and user.get("email") != email:
        storage.set_user(uid, {"email": email})
        user["email"] = email

    return {
        "uid": uid,
        "email": user.get("email", email),
        "benchmark_results": user.get("benchmark_results", {}),
        "last_job_id": user.get("last_job_id"),
    }


@app.get("/api/population/segments")
async def population_segments():
    return list_population_segments()


@app.get("/api/population/distribution/{segment}")
async def population_distribution(segment: str, bins: int = 20):
    # Clamp bins from the query string: an unbounded value makes np.histogram
    # allocate an enormous array (memory/CPU DoS), and <1 raises ValueError.
    bins = max(1, min(bins, 200))
    try:
        return get_population_distribution(segment, bins=bins)
    except KeyError:
        return JSONResponse({"error": "unknown segment"}, status_code=404)


@app.post("/upload")
@limiter.limit("5/minute")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    storage = get_storage()
    if storage.count_active_jobs() >= 5:
        return JSONResponse(
            {"error": "capacity", "message": "Please upload later due to reaching server capacity."},
            status_code=503,
        )

    # Anonymous uploads stay supported; a signed-in user's token associates the
    # job with them so results land on their /self record when it completes.
    job_doc = {"status": "queued"}
    if authorization:
        job_doc["uid"] = verify_bearer_token(authorization)["uid"]

    job_id = str(uuid.uuid4())
    data = await _read_capped(file, MAX_UPLOAD_BYTES)
    if data is None:
        return JSONResponse(
            {"error": "too_large", "message": "File exceeds the 200 MB limit."},
            status_code=413,
        )

    file_ref = storage.store_file(job_id, data)
    # file_ref/created_at are read back by the Firestore-triggered dispatcher
    # (dispatcher.py), which has no other way to learn which file a queued
    # job refers to or which queued job is oldest.
    job_doc.update({"file_ref": file_ref, "created_at": time.time()})
    storage.set_job(job_id, job_doc)

    await get_queue().enqueue(job_id, file_ref)

    return {"job_id": job_id, "status": "queued"}


@app.get("/status/{job_id}")
async def get_status(job_id: str, authorization: str | None = Header(default=None)):
    job = get_storage().get_job(job_id)
    if job is None:
        return JSONResponse({"status": "not_found"}, status_code=404)
    _authorize_job_access(job, authorization)
    return JSONResponse(job)


@app.get("/results/{job_id}")
async def get_results(job_id: str, authorization: str | None = Header(default=None)):
    storage = get_storage()
    job = storage.get_job(job_id)
    if job is None:
        return JSONResponse({"error": "job not found"}, status_code=404)
    _authorize_job_access(job, authorization)
    if job.get("status") != "completed":
        return JSONResponse({"error": "results not ready", "status": job.get("status")}, status_code=202)
    results = storage.get_results(job_id)
    if results is None:
        return JSONResponse({"error": "results missing"}, status_code=500)
    return JSONResponse(results)
