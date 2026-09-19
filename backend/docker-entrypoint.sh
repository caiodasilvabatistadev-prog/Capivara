#!/bin/sh
set -eu

chown appuser:appuser /app/data
exec gosu appuser sh -c 'exec uvicorn app.main:app --host 0.0.0.0 --no-access-log --port "${PORT:-8000}"'
