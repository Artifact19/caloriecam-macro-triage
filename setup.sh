#!/usr/bin/env bash
# One-shot environment setup (Linux/macOS).  ./setup.sh [--cuda]
set -euo pipefail
cd "$(dirname "$0")"
USE_CUDA=0
[[ "${1:-}" == "--cuda" ]] && USE_CUDA=1

[[ -d .venv ]] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip

if [[ "$USE_CUDA" == "1" ]]; then
  pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124
else
  pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
fi
pip install -r backend/requirements.txt
pip install -r notebooks/requirements-notebooks.txt
python -m ipykernel install --user --name python3 --display-name "Python 3 (meal-triage)" >/dev/null 2>&1 || true

( cd frontend && if [[ -f package-lock.json ]]; then npm ci; else npm install; fi )

[[ -f .env || ! -f .env.example ]] || cp .env.example .env
echo
echo "Setup complete. Next: python scripts/run_notebooks.py, then ./start.sh"

