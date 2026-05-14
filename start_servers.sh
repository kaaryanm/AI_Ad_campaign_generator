#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
ENV_FILE="$BACKEND_DIR/.env"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required but not found."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Error: npm is required but not found."
  exit 1
fi

if [ -f "$ENV_FILE" ]; then
  # Export variables defined in backend/.env to this shell.
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "Error: OPENAI_API_KEY is not set."
  echo "Set it in $ENV_FILE or export it before running this script."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating Python virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "Installing backend requirements..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

echo "Installing frontend dependencies..."
npm --prefix "$FRONTEND_DIR" install

echo "Starting backend on http://localhost:8000"
"$VENV_DIR/bin/python" -m uvicorn app.main:app --reload --port 8000 --app-dir "$BACKEND_DIR" &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:5173"
npm --prefix "$FRONTEND_DIR" run dev &
FRONTEND_PID=$!

cleanup() {
  echo
  echo "Stopping servers..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

while true; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    break
  fi
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    break
  fi
  sleep 1
done
