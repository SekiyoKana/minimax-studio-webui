#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-$HOME/minimax-h3-stack}"
API_ROOT="${API_ROOT:-$INSTALL_ROOT/minimax-h3-api}"
API_URL="${API_URL:-http://127.0.0.1:8193}"
ENV_FILE="${ENV_FILE:-$API_ROOT/.env}"

set -a
source "$ENV_FILE"
set +a

temp_root="$(mktemp -d)"
trap 'rm -rf "$temp_root"' EXIT
reference="$temp_root/reference.png"
result="$temp_root/result.mp4"
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i "color=c=0x223044:s=608x352:d=1" \
  -vf "drawbox=x=80:y=70:w=448:h=212:color=0xD8C9A7:t=fill" \
  -frames:v 1 "$reference"

auth_headers=()
[[ -n "${H3_API_KEY:-}" ]] && auth_headers+=(-H "Authorization: Bearer $H3_API_KEY")
response="$(curl -fsS -X POST "$API_URL/api/v1/generations" \
  "${auth_headers[@]}" \
  -H "X-H3-Incognito-Code: $H3_INCOGNITO_CODE" \
  -F "prompt=固定镜头，米色矩形位于深蓝灰色背景中央，轻微柔和的环境光变化，画面稳定，无人物，无文字。" \
  -F 'reference_manifest=[{"type":"image"}]' \
  -F "references=@$reference;type=image/png" \
  -F "model_variant=fl2va-fp8" \
  -F "execution_mode=turbo-lora" \
  -F "width=608" \
  -F "height=352" \
  -F "duration=5" \
  -F "steps=8" \
  -F "incognito=true")"
job_id="$(printf '%s' "$response" | "$API_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
echo "验证任务: $job_id"

for _ in $(seq 1 240); do
  response="$(curl -fsS "${auth_headers[@]}" "$API_URL/api/v1/generations/$job_id")"
  status="$(printf '%s' "$response" | "$API_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  progress="$(printf '%s' "$response" | "$API_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin).get("progress", 0))')"
  echo "$status $progress%"
  case "$status" in
    completed) break ;;
    failed|cancelled)
      printf '%s' "$response" | "$API_ROOT/.venv/bin/python" -m json.tool
      exit 1
      ;;
  esac
  sleep 5
done

[[ "$status" == "completed" ]] || { echo "验证任务超时" >&2; exit 1; }
curl -fsS "${auth_headers[@]}" "$API_URL/api/v1/generations/$job_id/result" -o "$result"
ffprobe -v error \
  -show_entries format=duration,size:stream=index,codec_name,width,height,channels \
  -of json "$result"
