#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/frontend"
[[ -d node_modules ]] || npm ci
npm run dev -- --host 127.0.0.1 --port 5173

