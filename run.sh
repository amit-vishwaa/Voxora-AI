#!/usr/bin/env bash
cd "$(dirname "$0")/backend"
. .venv/bin/activate
echo "Voxora Voice: http://localhost:8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
