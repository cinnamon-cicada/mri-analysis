#!/bin/bash

# Activate venv
source venv/bin/activate

# Start worker in background
python worker.py &

# Start FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000