import time
from queue_system import job_queue
import subprocess

def run_fastsurfer(file_path):
    print(f"Processing {file_path}")

    # Example FastSurfer command
    subprocess.run([
        "fastsurfer",
        "--t1", file_path,
        "--sd", "outputs",
        "--sid", file_path.split("/")[-1]
    ])

while True:
    job = job_queue.get()
    print(f"Starting job {job['job_id']}")

    run_fastsurfer(job["file_path"])

    print(f"Finished job {job['job_id']}")
    job_queue.task_done()