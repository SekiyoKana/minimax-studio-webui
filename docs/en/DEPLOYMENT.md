# Cloud GPU Deployment

[中文](../DEPLOYMENT.md)

## Server Baseline

The minimum configuration targets one 608x352, 5-second, 8-step accelerated job:

| Item | Minimum | Verified Environment |
|---|---|---|
| Operating system | Ubuntu 22.04 | Ubuntu 22.04.5 LTS |
| GPU | 1 NVIDIA GPU with 24 GB VRAM | 2 RTX 4090 GPUs; each workflow uses one |
| Driver | 550.54.14 | 575.51.03 |
| Python | 3.11 | 3.11.10 |
| PyTorch | 2.6.0 + cu124 | 2.6.0 + cu124 |
| Memory | 64 GB + 32 GB swap | 125 GiB + 2 GiB swap |
| Available SSD | 100 GB | 365 GB |

ComfyUI RSS after model loading was approximately 49.4 GB on the verified server. The 64 GB RAM baseline has not been independently retested on that server, so swap must remain available.

## Prerequisites

The installer requires the following commands:

```bash
git --version
python3.11 --version
nvidia-smi
ffmpeg -version
aria2c --version
rsync --version
curl --version
openssl version
systemctl --version
```

Install Ubuntu system tools with:

```bash
sudo apt-get update
sudo apt-get install -y git ffmpeg aria2 rsync curl openssl python3.11 python3.11-venv
```

The default Ubuntu 22.04 repositories may not contain Python 3.11. Use a cloud GPU image with Python 3.11, a Conda Python 3.11 environment, or an approved package source.

## ComfyUI Node Packages

The root-level [`comfyui_nodes/`](../../comfyui_nodes/) directory contains pinned source archives for ComfyUI core, VideoHelperSuite, ComfyUI-MultiGPU, and the digital-human audio-drive node. Each dependency is a separate ZIP file. Sources, commits, licenses, and SHA-256 checksums are recorded in [`comfyui_nodes/manifest.json`](../../comfyui_nodes/manifest.json).

The installer checks out the same revisions from the upstream repositories by default. Use the archives for offline installation or source verification. Music3 also requires `patches/comfyui-music3-force-duration.patch`.

## Installer Settings

| Environment Variable | Default | Description |
|---|---|---|
| `INSTALL_ROOT` | `$HOME/minimax-h3-stack` | Root directory for ComfyUI, the API, and models |
| `PYTHON_BIN` | `python3.11` | Python interpreter used to create virtual environments |
| `GPU_ID` | `0` | Physical GPU assigned to ComfyUI |
| `MODEL_PROVIDER` | `modelscope` | Core-model provider; `huggingface` is also supported |
| `COMFY_HOST` | `127.0.0.1` | ComfyUI listen address |
| `COMFY_PORT` | `8188` | ComfyUI port |
| `API_HOST` | `0.0.0.0` | Web and API listen address |
| `API_PORT` | `8193` | Web and API port |
| `COMFY_RESERVE_VRAM_GB` | `8` | ComfyUI reserved-VRAM argument |
| `INSTALL_NSFW` | `0` | Install the optional NaughtyTimes LoRA |
| `NSFW_LORA_FILE` | Empty | Authorized local LoRA file |
| `NSFW_LORA_URL` | Empty | Authorized LoRA download URL |
| `START_SERVICES` | `1` | Start systemd user services after installation |
| `SKIP_MODELS` | `0` | Skip model downloads when reusing an existing model directory |
| `ENABLE_LINGER` | `1` | Attempt to keep user services running after logout |
| `DRY_RUN` | `0` | Print the installation plan only |

## Installation Example

```bash
INSTALL_ROOT=/data/minimax-h3-stack \
PYTHON_BIN=/opt/conda/bin/python \
GPU_ID=1 \
MODEL_PROVIDER=modelscope \
bash scripts/install.sh
```

Model downloads, Python environment setup, and service deployment all run on the GPU server executing the script.

## Ports

| Port | Default Listen Address | Purpose |
|---|---|---|
| 8188 | `127.0.0.1` | Internal ComfyUI service |
| 8193 | `0.0.0.0` | Customer web interface and API |

Only port 8193 must be exposed to clients. Public deployments require upstream TLS, authentication, and access control.

## Service Files

The installer writes:

```text
~/.config/systemd/user/comfyui.service
~/.config/systemd/user/minimax-studio-webui.service
```

Keep the services running after SSH logout:

```bash
sudo loginctl enable-linger "$USER"
```

## Existing Model Directory

Models must be stored in these ComfyUI directories:

```text
ComfyUI/models/diffusion_models/
ComfyUI/models/text_encoders/
ComfyUI/models/vae/
ComfyUI/models/loras/
```

Existing model files must still pass verification:

```bash
python3 scripts/download_models.py \
  --manifest model-manifest.json \
  --comfy-root /data/minimax-h3-stack/ComfyUI \
  --verify-only
```
