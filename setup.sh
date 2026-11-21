#!/usr/bin/env bash
# Mac / Linux setup. Windows users: double-click setup.bat instead.
set -e
cd "$(dirname "$0")/backend"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
echo "Setup finished. Run ./run.sh"
