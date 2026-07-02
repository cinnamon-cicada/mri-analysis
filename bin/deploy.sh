#!/usr/bin/env bash
#
# Phase 4 — build & deploy. Corrected replacement for the commands in
# plan.txt, which had three defects that would fail or misdeploy:
#   1. Used the nonexistent project id "brainbenchmark-mri" (the real one is
#      "the-brain-benchmark-project").
#   2. Deployed the dispatcher without GOOGLE_FUNCTION_SOURCE=dispatcher.py, so
#      the Python buildpack would pick backend/main.py (the batch pipeline)
#      instead of dispatcher.py as the function source.
#   3. Set no GCP_PROJECT env var, which dispatcher.py reads at import time —
#      the function would crash on cold start with a KeyError.
#
# WARNING: this performs BILLABLE, OUTWARD-FACING deploys (Cloud Build minutes,
# a public Cloud Run API service, a Firestore-triggered function, Firebase
# Hosting). Review before running. Requires gcloud authed as eluo.5230@gmail.com
# and the Firebase CLI on PATH. Run from the repo root.
set -euo pipefail

PROJECT=the-brain-benchmark-project
REGION=us-central1
REPO="${REGION}-docker.pkg.dev/${PROJECT}/mri"

echo "==> 4a. Build & push images via Cloud Build"
gcloud builds submit --project="${PROJECT}" \
  --config=infra/cloudbuild.yaml \
  --substitutions=_IMAGE="${REPO}/api:latest",_DOCKERFILE=infra/Dockerfile.api .

gcloud builds submit --project="${PROJECT}" \
  --config=infra/cloudbuild.yaml \
  --substitutions=_IMAGE="${REPO}/worker:latest",_DOCKERFILE=infra/Dockerfile.worker .

echo "==> 4b. Deploy the worker as a Cloud Run Job"
gcloud run jobs replace infra/cloudrun_worker.yaml \
  --region="${REGION}" --project="${PROJECT}"

echo "==> 4c. Deploy the dispatcher (2nd-gen Cloud Function)"
gcloud functions deploy mri-dispatcher \
  --gen2 \
  --runtime=python311 \
  --region="${REGION}" \
  --project="${PROJECT}" \
  --source=backend \
  --entry-point=dispatch \
  --set-build-env-vars=GOOGLE_FUNCTION_SOURCE=dispatcher.py \
  --set-env-vars="GCP_PROJECT=${PROJECT},GCP_WORKER_JOB_LOCATION=${REGION},GCP_WORKER_JOB_NAME=mri-worker" \
  --trigger-location="${REGION}" \
  --trigger-event-filters="type=google.cloud.firestore.document.v1.written" \
  --trigger-event-filters="database=(default)" \
  --trigger-event-filters-path-pattern="document=jobs/{jobId}" \
  --service-account="mri-dispatcher-sa@${PROJECT}.iam.gserviceaccount.com"

echo "==> 4d. Deploy the API Cloud Run Service"
gcloud run services replace infra/cloudrun_service.yaml \
  --region="${REGION}" --project="${PROJECT}"

# The API is reached through Firebase Hosting rewrites (see infra/firebase.json).
# If Hosting returns 403 on /upload etc., grant the invoker role. Public access:
#   gcloud run services add-iam-policy-binding mri-api \
#     --region="${REGION}" --project="${PROJECT}" \
#     --member=allUsers --role=roles/run.invoker

echo "==> 4e. Deploy Firestore rules/indexes, Storage rules, and Hosting"
( cd infra && firebase deploy --project="${PROJECT}" \
    --only firestore:rules,firestore:indexes,storage,hosting )

echo "==> Done. Smoke test: curl https://<mri-api-url>/healthz  →  {\"status\":\"ok\"}"
