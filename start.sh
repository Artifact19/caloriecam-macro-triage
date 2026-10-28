#!/usr/bin/env bash
# Single-command launcher: starts backend + frontend together. Ctrl+C stops both.
set -euo pipefail
cd "$(dirname "$0")"

[[ -d .venv ]] || ./setup.sh
[[ -d frontend/node_modules ]] || ( cd frontend && npm ci )

./run_backend.sh &
BACK=$!
./run_frontend.sh &
FRONT=$!
trap 'kill $BACK $FRONT 2>/dev/null || true' INT TERM EXIT

sleep 6
URL="http://127.0.0.1:5173"
( command -v xdg-open >/dev/null && xdg-open "$URL" ) || ( command -v open >/dev/null && open "$URL" ) || echo "Open $URL"
wait

