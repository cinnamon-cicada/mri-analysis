#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."

source "$ROOT/env/bin/activate"

cd "$ROOT/backend"

# Local dev: in-process queue, local filesystem storage
export STORAGE_BACKEND=local
export QUEUE_BACKEND=local
export GOOGLE_APPLICATION_CREDENTIALS="$ROOT/backend/service-account-key.json"

uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
