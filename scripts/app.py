from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import uuid
import os
from utils import queue_manager

from threading import Thread
from concurrent.futures import ProcessPoolExecutor
from queue import Queue

app = FastAPI()

UPLOAD_DIR = "uploads"
RESULTS_DIR = "analysis_app"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Static + Templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# -----------------------
# App on Startup
# -----------------------
@app.on_event("startup")
def startup():
    if hasattr(app.state, "initialized"):
        return

    app.state.initialized = True

    app.state.job_queue = Queue()
    app.state.executor = ProcessPoolExecutor(max_workers=2)

    Thread(
        target=queue_manager,
        args=(app.state.job_queue, app.state.executor),
        daemon=True
    ).start()

# -----------------------
# Frontend Route
# -----------------------
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


# -----------------------
# Upload Endpoint
# -----------------------
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/{job_id}.nii.gz"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    app.state.job_queue.put({
        "job_id": job_id,
        "file_path": file_path
    })

    return {"job_id": job_id, "status": "queued"}


# -----------------------
# Job Status (Mock)
# -----------------------
job_status = {}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in job_status:
        return JSONResponse({"status": "processing"})

    return JSONResponse(job_status[job_id])


# -----------------------
# Simulated Result Writer
# -----------------------
def save_result(job_id, result_data):
    job_status[job_id] = {
        "status": "completed",
        "result": result_data
    }