#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${H3_ROOT:-$SCRIPT_DIR}"
export H3_ROOT="$ROOT"
export HF_HOME="${HF_HOME:-$ROOT/.cache/huggingface}"

exec "$ROOT/.venv/bin/python" -m uvicorn app.main:app \
  --app-dir "$ROOT" \
  --host "${H3_HOST:-0.0.0.0}" \
  --port "${H3_PORT:-8193}" \
  --workers 1 \
  --timeout-graceful-shutdown 5 \
  --no-access-log \
  --proxy-headers
