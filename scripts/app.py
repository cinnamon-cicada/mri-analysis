from fastapi import FastAPI, UploadFile, File
import shutil
import uuid
from queue_system import job_queue

app = FastAPI()

UPLOAD_DIR = "/uploads"

@app.post(UPLOAD_DIR)
async def upload(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/{job_id}.nii.gz"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Add job to queue
    job_queue.put({
        "job_id": job_id,
        "file_path": file_path
    })

    return {"job_id": job_id, "status": "queued"}

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import shutil
import uuid
import os
from queue_system import job_queue

app = FastAPI()

UPLOAD_DIR = "uploads"
RESULTS_DIR = "results"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Serve static files if needed later
app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------
# Frontend (Minimal UI)
# -----------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MRI Analysis</title>
        <style>
            body {
                background-color: #111;
                color: #eee;
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
            }
            .container {
                background: #1c1c1c;
                padding: 30px;
                border-radius: 10px;
                display: inline-block;
                box-shadow: 0 0 10px rgba(255,255,255,0.1);
            }
            input, button {
                margin: 10px;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            input {
                background: #333;
                color: white;
            }
            button {
                background: #555;
                color: white;
                cursor: pointer;
            }
            button:hover {
                background: #777;
            }
            .status {
                margin-top: 20px;
                color: #ccc;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>MRI Brain Scan Upload</h1>
            <form id="uploadForm">
                <input type="file" name="file" required />
                <br>
                <button type="submit">Upload</button>
            </form>

            <div class="status" id="status"></div>
        </div>

        <script>
            const form = document.getElementById('uploadForm');
            const statusDiv = document.getElementById('status');

            form.onsubmit = async (e) => {
                e.preventDefault();

                const formData = new FormData(form);

                statusDiv.innerText = "Uploading...";

                const res = await fetch("/upload", {
                    method: "POST",
                    body: formData
                });

                const data = await res.json();

                statusDiv.innerText = "Job ID: " + data.job_id + " (queued)";

                checkStatus(data.job_id);
            };

            async function checkStatus(job_id) {
                const interval = setInterval(async () => {
                    const res = await fetch(`/status/${job_id}`);
                    const data = await res.json();

                    statusDiv.innerText = "Status: " + data.status;

                    if (data.status === "completed") {
                        clearInterval(interval);
                        statusDiv.innerText += "\\nResult: " + JSON.stringify(data.result);
                    }
                }, 3000);
            }
        </script>
    </body>
    </html>
    """


# -----------------------
# Upload Endpoint
# -----------------------
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/{job_id}.nii.gz"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Add job to queue
    job_queue.put({
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
    # In real app, this would check your worker/FastSurfer output
    if job_id not in job_status:
        return JSONResponse({"status": "processing"})

    return JSONResponse(job_status[job_id])


# -----------------------
# Simulated Result Writer (hook for FastSurfer)
# -----------------------
def save_result(job_id, result_data):
    """
    Call this from your FastSurfer worker when processing is done.
    """
    job_status[job_id] = {
        "status": "completed",
        "result": result_data
    }