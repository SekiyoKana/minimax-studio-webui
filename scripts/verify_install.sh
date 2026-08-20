#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-$HOME/minimax-h3-stack}"
API_ROOT="${API_ROOT:-$INSTALL_ROOT/minimax-studio-webui}"
COMFY_ROOT="${COMFY_ROOT:-$INSTALL_ROOT/ComfyUI}"
API_URL="${API_URL:-http://127.0.0.1:8193}"
COMFY_URL="${COMFY_URL:-http://127.0.0.1:8188}"

test -x "$API_ROOT/.venv/bin/python"
test -x "$COMFY_ROOT/.venv/bin/python"
"$API_ROOT/.venv/bin/python" -m unittest discover -s "$API_ROOT/tests" -v
"$API_ROOT/.venv/bin/python" "$API_ROOT/scripts/download_models.py" \
  --manifest "$API_ROOT/model-manifest.json" \
  --comfy-root "$COMFY_ROOT" \
  --verify-only
curl -fsS "$COMFY_URL/object_info/LoraLoaderModelOnly" >/dev/null
curl -fsS "$COMFY_URL/object_info/MiniMaxH3SigmaShift" >/dev/null
curl -fsS "$COMFY_URL/object_info/KSamplerSelect" >/dev/null
curl -fsS "$COMFY_URL/object_info/VHS_LoadVideo" >/dev/null
curl -fsS "$COMFY_URL/object_info/MiniMaxMusic3TextEncode" >/dev/null
curl -fsS "$COMFY_URL/object_info/EmptyMiniMaxMusic3LatentAudio" >/dev/null
curl -fsS "$COMFY_URL/object_info/CLIPLoaderMultiGPU" >/dev/null
curl -fsS "$API_URL/health"
echo
curl -fsS "$COMFY_URL/queue"
echo
