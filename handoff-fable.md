# Handoff — Brain Benchmark MRI Project

For a new session (any model) picking this up cold. Full detail lives in
`CLAUDE.md` (architecture reference, kept in sync with code) and
`handoff.txt` (long-form revision history, if you need the "why").

## What this is

FastAPI web app: upload a T1 MRI scan → FastSurfer (Docker) segments it →
percentiles vs. the HCP-YA reference population (N=889). Plus a batch
pipeline (`backend/main.py`) for research datasets. GCP project:
`the-brain-benchmark-project` (account `eluo.5230@gmail.com`).

## Current state (all done, tested, committed)

- Local dev env (`env/`), tests (`tests/test_pipeline.py`, 28 pass —
  `pytest tests/ -k "not TestDockerSmoke"`) all green.
- Worker runs as a **Cloud Run Job**, not a Service — FastSurfer takes
  "many hours" per subject, and Services have a hard 60-min timeout.
  A Firestore-triggered dispatcher (`backend/dispatcher.py`, a 2nd-gen
  Cloud Function) replaced Cloud Tasks entirely; it enforces a
  2-concurrent-job cap transactionally and starts Job executions via
  the Cloud Run Admin API.
- `POST /upload` capacity-limits at 5 active jobs (503 + toast).
- GCP infra provisioned: Artifact Registry, Firestore (+ composite
  index for the dispatcher's query), the 3 service accounts
  (`mri-api-sa`, `mri-worker-sa`, `mri-dispatcher-sa`), Secret Manager
  (FreeSurfer license), Firestore/Storage rules deployed.
- `/data` page (population histogram, with axes) and a `/self` profile
  icon (dead link — see Blocked below) exist on the frontend.

## Not done / blocked

- **Phase 4 (build + deploy) hasn't been run.** Images aren't built,
  nothing is actually deployed to Cloud Run yet. `infra/*.yaml` are
  ready with real values substituted.
- **`/self`, `/login`, user accounts — explicitly blocked** on you
  confirming Firebase Auth vs. a custom auth scheme. Don't build
  either without that decision; see `handoff.txt`'s OPEN QUESTION.
  Firebase Auth is the recommendation (infra's already there).
- `backend/service-account-key.json` exists locally (gitignored,
  `mri-api-sa` key) for local testing of the firebase/GCP backends.

## Gotchas worth knowing before touching things

- The GCP project was originally documented as `brainbenchmark-mri` —
  that project **never existed**. Everything now correctly says
  `the-brain-benchmark-project`. If you see the old name anywhere
  outside `handoff.txt`'s historical notes, it's stale.
- `storage.set_job()` does a Firestore **merge**, not overwrite — this
  matters because the dispatcher reads `file_ref`/`created_at` off the
  job doc, written once at upload time.
- FastSurfer's subprocess timeout was hardcoded to 1h and silently
  would have killed every real run — fixed to 24h to match the Job's
  `timeoutSeconds`. If you see `timeout=3600` reappear anywhere, it's
  a regression.
- `tests/test_pipeline.py`'s Docker-dependent tests need
  `tests/fixtures/test_scan.nii.gz` (already committed, a tiny
  public-domain scan) — without it they auto-skip.
- CLAUDE.md has a standing instruction: act as a critical senior
  engineer, push back on questionable architecture calls rather than
  agreeing by default.
