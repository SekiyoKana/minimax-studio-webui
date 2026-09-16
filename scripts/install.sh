#!/usr/bin/env bash
set -euo pipefail

COMFY_COMMIT="7fe8a6138504f90ff7be82f3babf416da32876b1"
VHS_COMMIT="993082e4f2473bf4acaf06f51e33877a7eb38960"
MULTIGPU_COMMIT="62f98eda3a1081a551c8efca367973ac854e9d5e"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_ROOT="${INSTALL_ROOT:-$HOME/minimax-h3-stack}"
API_ROOT="$INSTALL_ROOT/minimax-studio-webui"
COMFY_ROOT="$INSTALL_ROOT/ComfyUI"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
GPU_ID="${GPU_ID:-0}"
MODEL_PROVIDER="${MODEL_PROVIDER:-modelscope}"
INSTALL_NSFW="${INSTALL_NSFW:-0}"
NSFW_LORA_FILE="${NSFW_LORA_FILE:-}"
NSFW_LORA_URL="${NSFW_LORA_URL:-}"
COMFY_HOST="${COMFY_HOST:-127.0.0.1}"
COMFY_PORT="${COMFY_PORT:-8188}"
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8193}"
COMFY_RESERVE_VRAM_GB="${COMFY_RESERVE_VRAM_GB:-8}"
START_SERVICES="${START_SERVICES:-1}"
ENABLE_LINGER="${ENABLE_LINGER:-1}"
SKIP_MODELS="${SKIP_MODELS:-0}"
DRY_RUN="${DRY_RUN:-0}"

fail() {
  echo "错误: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "缺少命令 $1"
}

clone_at_commit() {
  local url="$1"
  local destination="$2"
  local commit="$3"
  local allow_dirty="${4:-0}"
  if [[ ! -d "$destination/.git" ]]; then
    git clone "$url" "$destination"
  elif [[ -n "$(git -C "$destination" status --porcelain)" ]]; then
    if [[ "$allow_dirty" != "1" ]]; then
      fail "$destination 存在未提交修改，安装程序没有覆盖该目录"
    fi
    [[ "$(git -C "$destination" rev-parse HEAD)" == "$commit" ]] \
      || fail "$destination 已有未提交修改且版本不匹配"
    return
  fi
  git -C "$destination" fetch --depth 1 origin "$commit"
  git -C "$destination" checkout --detach "$commit"
}

render_service() {
  local source="$1"
  local destination="$2"
  sed \
    -e "s|@@API_ROOT@@|$API_ROOT|g" \
    -e "s|@@COMFY_ROOT@@|$COMFY_ROOT|g" \
    -e "s|@@ENV_FILE@@|$API_ROOT/.env|g" \
    -e "s|@@COMFY_PYTHON@@|$COMFY_ROOT/.venv/bin/python|g" \
    -e "s|@@COMFY_HOST@@|$COMFY_HOST|g" \
    -e "s|@@COMFY_PORT@@|$COMFY_PORT|g" \
    -e "s|@@COMFY_RESERVE_VRAM_GB@@|$COMFY_RESERVE_VRAM_GB|g" \
    "$source" > "$destination"
}

case "$INSTALL_ROOT" in
  *" "*) fail "INSTALL_ROOT 不能包含空格" ;;
  *[^A-Za-z0-9_./-]*) fail "INSTALL_ROOT 只能包含字母、数字、下划线、点、斜线和短横线" ;;
esac

for command in git curl openssl; do
  require_command "$command"
done
require_command "$PYTHON_BIN"

"$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' \
  || fail "需要 Python 3.11 或更高版本"
[[ "$GPU_ID" =~ ^[0-9]+$ ]] || fail "GPU_ID 必须是非负整数"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "安装目录: $INSTALL_ROOT"
  echo "Python: $PYTHON_BIN"
  echo "GPU: $GPU_ID"
  echo "模型来源: $MODEL_PROVIDER"
  echo "包含可选 NaughtyTimes LoRA: $INSTALL_NSFW"
  echo "ComfyUI commit: $COMFY_COMMIT"
  echo "VideoHelperSuite commit: $VHS_COMMIT"
  echo "ComfyUI-MultiGPU commit: $MULTIGPU_COMMIT"
  exit 0
fi

for command in aria2c ffmpeg patch rsync nvidia-smi systemctl; do
  require_command "$command"
done

gpu_memory_mib="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | sed -n "$((GPU_ID + 1))p" | tr -d ' ')"
[[ "$gpu_memory_mib" =~ ^[0-9]+$ ]] || fail "GPU_ID=$GPU_ID 不存在"
(( gpu_memory_mib >= 23000 )) || fail "需要至少 24 GB 级别的 NVIDIA GPU"

mkdir -p "$INSTALL_ROOT"
available_kib="$(df -Pk "$INSTALL_ROOT" | awk 'NR==2 {print $4}')"
(( available_kib >= 100 * 1024 * 1024 )) || fail "安装目录至少需要 100 GiB 可用空间"

clone_at_commit "https://github.com/comfyanonymous/ComfyUI.git" "$COMFY_ROOT" "$COMFY_COMMIT"
clone_at_commit \
  "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git" \
  "$COMFY_ROOT/custom_nodes/ComfyUI-VideoHelperSuite" \
  "$VHS_COMMIT"
clone_at_commit \
  "https://github.com/pollockjj/ComfyUI-MultiGPU.git" \
  "$COMFY_ROOT/custom_nodes/comfyui-multigpu" \
  "$MULTIGPU_COMMIT"

if ! grep -q 'force_duration' "$COMFY_ROOT/comfy_extras/nodes_minimax_music.py"; then
  patch -d "$COMFY_ROOT" -p1 < "$REPO_ROOT/patches/comfyui-music3-force-duration.patch"
fi

if [[ ! -x "$COMFY_ROOT/.venv/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$COMFY_ROOT/.venv"
fi
"$COMFY_ROOT/.venv/bin/python" -m pip install --upgrade pip wheel setuptools
"$COMFY_ROOT/.venv/bin/python" -m pip install \
  torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
  --index-url https://download.pytorch.org/whl/cu124
"$COMFY_ROOT/.venv/bin/python" -m pip install -r "$COMFY_ROOT/requirements.txt"
"$COMFY_ROOT/.venv/bin/python" -m pip install torchao==0.9.0
if [[ -f "$COMFY_ROOT/custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt" ]]; then
  "$COMFY_ROOT/.venv/bin/python" -m pip install \
    -r "$COMFY_ROOT/custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt"
fi

mkdir -p "$API_ROOT"
if [[ "$(realpath -m "$REPO_ROOT")" != "$(realpath -m "$API_ROOT")" ]]; then
  rsync -a \
    --exclude '.env' \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude 'data' \
    --exclude '__pycache__' \
    "$REPO_ROOT/" "$API_ROOT/"
fi
chmod +x "$API_ROOT/run.sh" "$API_ROOT/scripts/"*.sh "$API_ROOT/scripts/"*.py

if [[ ! -x "$API_ROOT/.venv/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$API_ROOT/.venv"
fi
"$API_ROOT/.venv/bin/python" -m pip install --upgrade pip wheel setuptools
"$API_ROOT/.venv/bin/python" -m pip install -r "$API_ROOT/requirements-api.txt"

mkdir -p "$COMFY_ROOT/user/default/workflows"
rsync -a "$API_ROOT/workflows/" "$COMFY_ROOT/user/default/workflows/"

if [[ "$SKIP_MODELS" != "1" ]]; then
  model_args=(
    --manifest "$API_ROOT/model-manifest.json"
    --comfy-root "$COMFY_ROOT"
    --provider "$MODEL_PROVIDER"
  )
  if [[ "$INSTALL_NSFW" == "1" ]]; then
    model_args+=(--include-nsfw)
    [[ -n "$NSFW_LORA_FILE" ]] && model_args+=(--nsfw-file "$NSFW_LORA_FILE")
    [[ -n "$NSFW_LORA_URL" ]] && model_args+=(--nsfw-url "$NSFW_LORA_URL")
  fi
  "$API_ROOT/.venv/bin/python" "$API_ROOT/scripts/download_models.py" "${model_args[@]}"
fi

if [[ ! -f "$API_ROOT/.env" ]]; then
  incognito_code="${H3_INCOGNITO_CODE:-$(openssl rand -hex 24)}"
  umask 077
  {
    echo "H3_ROOT=$API_ROOT"
    echo "H3_COMFY_ROOT=$COMFY_ROOT"
    echo "H3_ENGINE=comfyui"
    echo "H3_HOST=$API_HOST"
    echo "H3_PORT=$API_PORT"
    echo "H3_COMFY_OUTPUT_DIR=$COMFY_ROOT/output"
    echo "H3_COMFY_WORKFLOW=$API_ROOT/workflows/minimax_h3_fl2va_fp8_720p_15s_api.json"
    echo "H3_COMFY_REF2VA_WORKFLOW=$API_ROOT/workflows/minimax_h3_ref2va_fp8_scaled_api.json"
    echo "H3_COMFY_SA_WORKFLOW=$API_ROOT/workflows/minimax_h3_fl2va_fp8_sa_api.json"
    echo "H3_COMFY_REF2VA_SA_WORKFLOW=$API_ROOT/workflows/minimax_h3_ref2va_fp8_sa_api.json"
    echo "H3_COMFY_VDN_WORKFLOW=$API_ROOT/workflows/minimax_h3_fl2va_vdn_api.json"
    echo "H3_COMFY_REF2VA_VDN_WORKFLOW=$API_ROOT/workflows/minimax_h3_ref2va_vdn_api.json"
    echo "H3_COMFY_TURBO_WORKFLOW=$API_ROOT/workflows/minimax_h3_fl2va_fp8_turbo_lora_api.json"
    echo "H3_COMFY_REF2VA_TURBO_WORKFLOW=$API_ROOT/workflows/minimax_h3_ref2va_fp8_turbo_lora_api.json"
    echo "H3_COMFY_NSFW_WORKFLOW=$API_ROOT/workflows/minimax_h3_ref2va_fp8_nsfw_lora_api.json"
    echo "H3_COMFY_DIGITAL_HUMAN_WORKFLOW=$API_ROOT/workflows/minimax_h3_ref2va_fp8_digital_human_api.json"
    echo "H3_COMFY_TTS_WORKFLOW=$API_ROOT/workflows/minimax_h3_ref2va_fp8_tts_api.json"
    echo "H3_COMFY_MUSIC3_WORKFLOW=$API_ROOT/workflows/minimax_music3_int8_api.json"
    echo "H3_COMFY_POLL_SECONDS=2"
    printf 'H3_GPU_LABEL="MiniMax H3 FP8 / GPU %s / 24 GB"\n' "$GPU_ID"
    echo "H3_INCOGNITO_CODE=$incognito_code"
    echo "H3_API_KEY=${H3_API_KEY:-}"
    echo "H3_MAX_UPLOAD_MB=512"
    echo "CUDA_VISIBLE_DEVICES=$GPU_ID"
  } > "$API_ROOT/.env"
fi

service_dir="$HOME/.config/systemd/user"
mkdir -p "$service_dir"
render_service "$API_ROOT/deploy/comfyui.service.in" "$service_dir/comfyui.service"
render_service "$API_ROOT/deploy/minimax-studio-webui.service.in" "$service_dir/minimax-studio-webui.service"

if [[ "$ENABLE_LINGER" == "1" ]] && command -v loginctl >/dev/null 2>&1; then
  if [[ "$(id -u)" == "0" ]]; then
    loginctl enable-linger "$USER"
  elif sudo -n true >/dev/null 2>&1; then
    sudo loginctl enable-linger "$USER"
  else
    echo "提示: 执行 sudo loginctl enable-linger $USER 可让用户服务在退出登录后继续运行"
  fi
fi

if [[ "$START_SERVICES" == "1" ]]; then
  systemctl --user daemon-reload
  systemctl --user enable --now comfyui.service
  for _ in $(seq 1 90); do
    curl -fsS "http://127.0.0.1:$COMFY_PORT/system_stats" >/dev/null 2>&1 && break
    sleep 2
  done
  curl -fsS "http://127.0.0.1:$COMFY_PORT/system_stats" >/dev/null \
    || fail "ComfyUI 未在预期时间内启动"
  systemctl --user enable --now minimax-studio-webui.service
  for _ in $(seq 1 30); do
    curl -fsS "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1 && break
    sleep 2
  done
  curl -fsS "http://127.0.0.1:$API_PORT/health" || fail "API 服务未启动"
  echo
fi

echo "安装完成"
echo "项目目录: $API_ROOT"
echo "模型目录: $COMFY_ROOT/models"
echo "Web 页面: http://SERVER_IP:$API_PORT/"
echo "API 文档: http://SERVER_IP:$API_PORT/docs"
echo "配置文件: $API_ROOT/.env"
echo "无痕授权码: 执行 sed -n 's/^H3_INCOGNITO_CODE=//p' $API_ROOT/.env 查看"
