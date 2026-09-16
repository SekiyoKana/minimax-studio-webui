#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-$HOME/minimax-h3-stack}"
COMFY_ROOT="${COMFY_ROOT:-$INSTALL_ROOT/ComfyUI}"
VDN_COMMIT="23470b0dd182c1eefe714a1809898aec020a1114"
VDN_ROOT="$COMFY_ROOT/custom_nodes/ComfyUI-VDN-H3"

command -v git >/dev/null 2>&1 || { echo "缺少 git" >&2; exit 1; }
command -v hf >/dev/null 2>&1 || { echo "缺少 hf CLI，请先安装 huggingface_hub" >&2; exit 1; }

if [[ ! -d "$VDN_ROOT/.git" ]]; then
  git clone https://github.com/Saganaki22/ComfyUI-VDN-H3.git "$VDN_ROOT"
fi
git -C "$VDN_ROOT" fetch --depth 1 origin "$VDN_COMMIT"
git -C "$VDN_ROOT" checkout --detach "$VDN_COMMIT"

mkdir -p "$COMFY_ROOT/models/vdn"
hf download OpenVDN/vdn-minimax-h3 \
  --include "stage-dmd-step-250/*" \
  --include "stage-b-step-2000/*" \
  --local-dir "$COMFY_ROOT/models/vdn"

echo "VDN-H3 节点以及 stage-dmd-step-250 和 stage-b-step-2000 检查点已安装"
