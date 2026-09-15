#!/bin/sh
set -eu

# Railway injects PORT at runtime. 8080 is only a safe local fallback.
APP_PORT="${PORT:-8080}"

exec gunicorn \
  -w "${GUNICORN_WORKERS:-2}" \
  -k gthread \
  --threads "${GUNICORN_THREADS:-4}" \
  --bind "0.0.0.0:${APP_PORT}" \
  api.app:app
