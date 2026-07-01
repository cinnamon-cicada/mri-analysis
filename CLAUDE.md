# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Conventions

- Run relevant tests or linting when appropriate.
- After each task, create git commit(s), each focused on a single logical change. Do not combine unrelated work.
- Use a clear, concise commit message following Conventional Commits (e.g. `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
- You are a critical senior SWE developer at a FAANG company. Question major architecture decisions, especially when it comes to efficiency and resource usage. Do not agree with my choices without a solid reason.

## Commands

```bash
# Activate virtual environment (required before all Python commands)
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the web app locally (local storage + in-process queue)
./bin/run_app.sh

# Run batch analysis pipeline (from repo root, with venv active)
cd backend && python main.py 1        # ADHD-200 comparison
cd backend && python main.py 2        # Outlier/uniqueness vs HCP-YA
cd backend && python main.py 1 2      # Run both in sequence
```

## Architecture

This project has two independent modes that share the `backend/` Python modules:

### 1. Web App (FastAPI)

`backend/app.py` exposes three endpoints: `POST /upload`, `GET /status/{job_id}`, `GET /results/{job_id}`. Both storage and queue are injected via environment variable — the same code runs locally and in production without modification.

**Storage abstraction** (`backend/storage.py`):
- `local` (default): in-memory job metadata + local filesystem files. Not safe for multi-worker deployments.
- `firebase`: GCS for raw scan files, Firestore for job metadata. Requires `FIREBASE_STORAGE_BUCKET` and `GOOGLE_APPLICATION_CREDENTIALS`.

**Queue abstraction** (`backend/queue_system.py`):
- `local` (default): dispatches `worker.process_job()` as an asyncio background task in the same process.
- `cloudtasks`: enqueues an HTTP task to GCP Cloud Tasks, which POSTs to `GCP_WORKER_URL/run` — a separately deployed Cloud Run Service running `worker_entrypoint.py`.

**Worker** (`backend/worker.py`): stages the uploaded file into `{subject_id}/anat/{subject_id}_T1w.nii.gz`, invokes FastSurfer via Docker (`deepmi/fastsurfer:latest`), then calls `analysis.compare_to_benchmark()`.

**Worker entrypoint** (`backend/worker_entrypoint.py`): thin FastAPI app that receives `POST /run` from Cloud Tasks and runs `process_job()`. This is what gets deployed as the Cloud Run Service (it serves HTTP, so it cannot be a Cloud Run Job).

**Rate limiting**: `/upload` is limited to 5 requests/minute per IP via `slowapi`.

### 2. Batch Analysis Pipeline

`backend/main.py` orchestrates preprocessing and analysis for research datasets. Inputs must be organized as `{input_dir}/{subject_id}/anat/{subject_id}_T1w.nii.gz`. FastSurfer outputs go to `./processed_data/`, results to `./analysis/`.

`backend/preprocess.py` handles ADHD-200-specific preprocessing (downloading, organizing). `backend/utils.py` handles generic FastSurfer preparation (RAS reorientation, compression) and the Docker invocation shared with the web worker.

### Benchmark stats

`backend/benchmark/HCP_YA_ALL.csv` holds the HCP-YA general population reference data (N=889). `analysis.compare_to_benchmark()` and `preprocess.run_outlier_analysis()` load it directly (via a path relative to `backend/`) and compute percentiles from live population stats. `backend/benchmark/adhd_stats.json` is a legacy precomputed ADHD-200 mean/std file, no longer used by `compare_to_benchmark()`. The `analysis` parameter in `get_volume()` / `get_thickness()` selects which region set to extract — currently only `'adhd'` is implemented.

## Environment Variables

| Variable | Required for | Notes |
|---|---|---|
| `STORAGE_BACKEND` | Production | `firebase` to enable GCS + Firestore |
| `QUEUE_BACKEND` | Production | `cloudtasks` to enable GCP Cloud Tasks |
| `FIREBASE_STORAGE_BUCKET` | Firebase backend | e.g. `the-brain-benchmark-project.appspot.com` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Firebase/GCP backends | Path to `backend/service-account-key.json` |
| `GCP_PROJECT` | Cloud Tasks backend | `the-brain-benchmark-project` |
| `GCP_QUEUE_LOCATION` | Cloud Tasks backend | e.g. `us-central1` |
| `GCP_QUEUE_NAME` | Cloud Tasks backend | Queue name in Cloud Tasks |
| `GCP_WORKER_URL` | Cloud Tasks backend | Cloud Run Service URL |
| `GCP_API_SA_EMAIL` | Cloud Tasks backend | Service account email used for the OIDC token on enqueued tasks |
| `FREESURFER_LICENSE` | Worker | Default: `./license.txt` (gitignored) |
| `FASTSURFER_OUTPUT_DIR` | Worker | Default: `./processed_data/web_jobs` |

## GCP Infrastructure

Project: `the-brain-benchmark-project` (account: `eluo.5230@gmail.com`), billing linked to `010AA9-FCFD52-661122` (My Maps Billing Account).

No APIs, service accounts, or other resources are provisioned on this project yet — that happens next. Once created, the service accounts are expected to be `mri-api-sa@the-brain-benchmark-project.iam.gserviceaccount.com` and `mri-worker-sa@the-brain-benchmark-project.iam.gserviceaccount.com` (see `infra/cloudrun_service.yaml` / `infra/cloudrun_worker.yaml`), each with a narrower role set than a single shared service account.

## FastSurfer / Docker

The Docker image `deepmi/fastsurfer:latest` is pulled at first run. GPU is disabled in `utils.run_fastsurfer_docker()` (flag commented out — re-enable with `--gpus all` if a GPU is available). Processing timeout is 1 hour per subject.

FreeSurfer license (`license.txt`) must be obtained free from https://surfer.nmr.mgh.harvard.edu/registration.html and placed at the repo root or pointed to via `FREESURFER_LICENSE`.

## Legal

`legal/` contains ToS, Privacy Policy, and non-diagnostic language templates. Any user-facing result copy must follow the rules in `legal/non-diagnostic-language-template.md` — in particular, never use clinical terms like "abnormal", "atrophy", or "pathology" in outputs.
