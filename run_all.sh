#!/bin/bash
#!/usr/bin/env bash
# NETRA launcher. Install dependencies once using the README instructions.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  [[ -z "$BACKEND_PID" ]] || kill "$BACKEND_PID" 2>/dev/null || true
  [[ -z "$FRONTEND_PID" ]] || kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Fail with a useful message instead of silently starting only one half.
if ! python3 -c 'import fastapi, pydantic_settings, uvicorn' >/dev/null 2>&1; then
  echo "Backend dependencies are missing. Run: python3 -m pip install -r backend/requirements.txt" >&2
  exit 1
fi
if [[ ! -x "$ROOT_DIR/frontend/node_modules/.bin/vite" ]]; then
  echo "Frontend dependencies are missing. Run: cd frontend && npm install" >&2
  exit 1
fi

echo "Starting NETRA backend on http://127.0.0.1:8000..."
(cd "$ROOT_DIR/backend" && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!

for attempt in {1..30}; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Backend exited during startup. Check the error above." >&2
    exit 1
  fi
  if python3 -c 'from urllib.request import urlopen; urlopen("http://127.0.0.1:8000/health", timeout=1)' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! python3 -c 'from urllib.request import urlopen; urlopen("http://127.0.0.1:8000/health", timeout=1)' >/dev/null 2>&1; then
  echo "Backend did not become ready at http://127.0.0.1:8000/health" >&2
  exit 1
fi

echo "Starting NETRA frontend on http://127.0.0.1:3000..."
(cd "$ROOT_DIR/frontend" && npm run dev -- --host 127.0.0.1) &
FRONTEND_PID=$!

echo "NETRA is running: http://localhost:3000 (API docs: http://localhost:8000/docs)"
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done
echo "A NETRA service stopped. See the output above for details." >&2
exit 1
