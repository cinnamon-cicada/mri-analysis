from concurrent.futures import ProcessPoolExecutor
from fastsurfer import process_mri_job

# ✅ LIMIT: only 2 FastSurfer jobs at once
executor = ProcessPoolExecutor(max_workers=2)


def submit_job(job_id: str, file_path: str):
    executor.submit(process_mri_job, job_id, file_path)