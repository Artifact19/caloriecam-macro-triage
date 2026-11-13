#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[[ -d .venv ]] || { echo "Run ./setup.sh first."; exit 1; }
# shellcheck disable=SC1091
source .venv/bin/activate
python scripts/validate_artifacts.py --warn-only
cd backend
echo
echo "Backend: http://127.0.0.1:8001  (API docs: http://127.0.0.1:8001/docs)"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

