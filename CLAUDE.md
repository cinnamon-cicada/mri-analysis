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
- `local` (default, unset also falls back here): `LocalQueue` dispatches `worker.process_job()` as an asyncio background task in the same process, capped at 2 concurrent runs via a module-level semaphore.
- `firestore`: `NoopQueue` — enqueue() does nothing. Writing the job doc via `storage.set_job(status="queued")` (which now also stores `file_ref`/`created_at`) IS the trigger; see Dispatcher below.

**Capacity limit**: `POST /upload` checks `storage.count_active_jobs()` (jobs with status `queued` or `processing`) before storing anything, and returns `503 {"error": "capacity", "message": "..."}` at 5 active jobs. Note this shares its threshold (5) with the per-IP rate limit below but is a completely different mechanism — one caps total server load across all clients, the other caps request rate from one IP.

**Worker** (`backend/worker.py`): stages the uploaded file into `{subject_id}/anat/{subject_id}_T1w.nii.gz`, invokes FastSurfer via Docker (`deepmi/fastsurfer:latest`), then calls `analysis.compare_to_benchmark()`. Runs can take many hours per subject.

**Worker entrypoint** (`backend/worker_entrypoint.py`): plain script (no HTTP) run as a Cloud Run Job execution. Reads `JOB_ID`/`FILE_REF` from env vars supplied per-execution by the dispatcher, calls `process_job()`, and writes only the terminal `completed`/`failed` status — `processing` is set earlier by the dispatcher's claim transaction, not here.

**Dispatcher** (`backend/dispatcher.py`): a 2nd-gen Cloud Function triggered on writes to the `jobs` Firestore collection (deployed with its own minimal `backend/requirements.txt`, separate from the root one). On every firing it ignores the event payload and re-derives live state: in a Firestore transaction, count `processing` docs, and if under 2, atomically claim the oldest `queued` doc and start a `mri-worker` Cloud Run Job execution via the Admin API. Self-driving — the worker's own status writes re-trigger it, so no polling/scheduler is needed. Needs a composite index on `jobs(status ASC, created_at ASC)` (`infra/firestore.indexes.json`) since its query filters on `status` and orders by a different field.

This replaced an earlier Cloud-Tasks-based design: the worker was briefly a Cloud Run Service invoked over HTTP, but Cloud Run Services have a hard 60-minute request timeout — incompatible with FastSurfer runs that take many hours. Cloud Tasks' concurrency dispatch limit also only gates outstanding HTTP calls, not actual job duration, so it couldn't enforce "2 concurrent" once the worker stopped being an HTTP endpoint.

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
| `QUEUE_BACKEND` | Production | `firestore` to select the no-op queue (dispatcher-driven); unset/anything else uses `LocalQueue` |
| `FIREBASE_STORAGE_BUCKET` | Firebase backend | e.g. `the-brain-benchmark-project.appspot.com` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Firebase/GCP backends | Path to `backend/service-account-key.json` |
| `GCP_PROJECT` | Dispatcher | `the-brain-benchmark-project` |
| `GCP_WORKER_JOB_LOCATION` | Dispatcher | e.g. `us-central1`; defaults to `us-central1` if unset |
| `GCP_WORKER_JOB_NAME` | Dispatcher | Cloud Run Job name; defaults to `mri-worker` if unset |
| `FREESURFER_LICENSE` | Worker | Default: `./license.txt` (gitignored) |
| `FASTSURFER_OUTPUT_DIR` | Worker | Default: `./processed_data/web_jobs` |

## GCP Infrastructure

Project: `the-brain-benchmark-project` (account: `eluo.5230@gmail.com`), billing linked to `010AA9-FCFD52-661122` (My Maps Billing Account). Also registered as a Firebase project.

APIs enabled: Cloud Run, Pub/Sub, Firestore, Cloud Storage, Cloud Build, Artifact Registry, Secret Manager, Firebase, Eventarc, Cloud Functions.

Provisioned resources:
- Artifact Registry Docker repo `mri` (us-central1)
- Firestore native database (us-central1), with a composite index on `jobs(status ASC, created_at ASC)` (`infra/firestore.indexes.json`) for the dispatcher's queued-job query
- Secret `freesurfer-license` (contents of repo-root `license.txt`)
- Service accounts:
  - `mri-api-sa@the-brain-benchmark-project.iam.gserviceaccount.com` — roles: Datastore User, Storage Object Creator (the latter needed because `POST /upload` calls `FirebaseStorage.store_file()` directly from the API process — the original plan omitted this and uploads would 403). No longer has Cloud Tasks Enqueuer or Run Invoker — the API doesn't call the worker over HTTP anymore.
  - `mri-worker-sa@the-brain-benchmark-project.iam.gserviceaccount.com` — roles: Storage Object Admin, Datastore User, Secret Manager Secret Accessor (incl. on `freesurfer-license`)
  - `mri-dispatcher-sa@the-brain-benchmark-project.iam.gserviceaccount.com` — roles: Datastore User (transactional claim), Run Developer (permission to call `jobs.run`)
- Firestore rules/indexes and Storage rules (`infra/firestore.rules`, `infra/firestore.indexes.json`, `infra/storage.rules`) deployed via `firebase deploy --only firestore:rules,firestore:indexes,storage`
- `backend/service-account-key.json` — a downloaded key for `mri-api-sa`, gitignored. Verified it authenticates and (post-fix) can write to the Storage bucket.

REMOVED: the `mri-jobs` Cloud Tasks queue (deleted — no longer used, see Queue abstraction above).

## FastSurfer / Docker

The Docker image `deepmi/fastsurfer:latest` is pulled at first run. GPU is disabled in `utils.run_fastsurfer_docker()` (flag commented out — re-enable with `--gpus all` if a GPU is available). Processing timeout is 24 hours per subject (`subprocess.run(..., timeout=86400)`), matching the Cloud Run Job's `timeoutSeconds`. This was previously 1 hour — a leftover from before FastSurfer runs were confirmed to take many hours per subject, and one that would have silently killed every real production run regardless of the Job's own timeout.

FreeSurfer license (`license.txt`) must be obtained free from https://surfer.nmr.mgh.harvard.edu/registration.html and placed at the repo root or pointed to via `FREESURFER_LICENSE`.

## Legal

`legal/` contains ToS, Privacy Policy, and non-diagnostic language templates. Any user-facing result copy must follow the rules in `legal/non-diagnostic-language-template.md` — in particular, never use clinical terms like "abnormal", "atrophy", or "pathology" in outputs.
