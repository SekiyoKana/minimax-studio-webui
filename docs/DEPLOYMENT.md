# 云 GPU 部署

[English](en/DEPLOYMENT.md)

## 服务器基线

最低配置用于单任务、608×352、5 秒、10 步测试：

| 项目 | 最低配置 | 当前验证环境 |
|---|---|---|
| 操作系统 | Ubuntu 22.04 | Ubuntu 22.04.5 LTS |
| GPU | 1×24 GB NVIDIA GPU | 2×RTX 4090，工作流固定使用其中 1 张 |
| 驱动 | 550.54.14 | 575.51.03 |
| Python | 3.11 | 3.11.10 |
| PyTorch | 2.6.0 + cu124 | 2.6.0 + cu124 |
| 内存 | 64 GB + 32 GB swap | 125 GiB + 2 GiB swap |
| 可用 SSD | 100 GB | 365 GB |

当前服务器在模型加载后的 ComfyUI RSS 约为 49.4 GB。64 GB 内存基线尚未在当前服务器单独复测，需要保留 swap。

## 前置命令

安装脚本要求以下命令已经存在：

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

Ubuntu 系统工具可通过以下命令安装：

```bash
sudo apt-get update
sudo apt-get install -y git ffmpeg aria2 rsync curl openssl python3.11 python3.11-venv
```

Ubuntu 22.04 默认源可能不包含 Python 3.11。云 GPU 镜像可以预装 Python 3.11、Conda Python 3.11，或通过受控软件源安装。

## 安装参数

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `INSTALL_ROOT` | `$HOME/minimax-h3-stack` | ComfyUI、API 和模型的根目录 |
| `PYTHON_BIN` | `python3.11` | 用于创建虚拟环境的 Python |
| `GPU_ID` | `0` | ComfyUI 使用的物理 GPU 编号 |
| `MODEL_PROVIDER` | `modelscope` | 核心模型来源，可改为 `huggingface` |
| `COMFY_HOST` | `127.0.0.1` | ComfyUI 监听地址 |
| `COMFY_PORT` | `8188` | ComfyUI 端口 |
| `API_HOST` | `0.0.0.0` | Web 与 API 监听地址 |
| `API_PORT` | `8193` | Web 与 API 端口 |
| `COMFY_RESERVE_VRAM_GB` | `8` | ComfyUI 预留显存参数 |
| `INSTALL_NSFW` | `0` | 是否安装可选 NaughtyTimes LoRA |
| `NSFW_LORA_FILE` | 空 | 已授权的本地 LoRA 文件 |
| `NSFW_LORA_URL` | 空 | 已授权的下载地址 |
| `START_SERVICES` | `1` | 安装后启动 systemd 用户服务 |
| `SKIP_MODELS` | `0` | 跳过模型下载，用于已有模型目录 |
| `ENABLE_LINGER` | `1` | 尝试让用户服务在退出登录后继续运行 |
| `DRY_RUN` | `0` | 只显示安装计划 |

## 一键安装示例

```bash
INSTALL_ROOT=/data/minimax-h3-stack \
PYTHON_BIN=/opt/conda/bin/python \
GPU_ID=1 \
MODEL_PROVIDER=modelscope \
bash scripts/install.sh
```

模型下载、Python 环境安装和服务部署均在执行脚本的 GPU 服务器上完成。

## 端口

| 端口 | 默认监听 | 用途 |
|---|---|---|
| 8188 | `127.0.0.1` | ComfyUI 内部服务 |
| 8193 | `0.0.0.0` | 客户网页和 API |

仅需要向客户开放 8193。公网部署需要在上游配置 TLS、身份验证和访问控制。

## 服务文件

安装脚本将服务写入：

```text
~/.config/systemd/user/comfyui.service
~/.config/systemd/user/minimax-h3-api.service
```

退出 SSH 后保持服务运行：

```bash
sudo loginctl enable-linger "$USER"
```

## 已有模型目录

模型必须位于以下 ComfyUI 目录：

```text
ComfyUI/models/diffusion_models/
ComfyUI/models/text_encoders/
ComfyUI/models/vae/
ComfyUI/models/loras/
```

使用已有文件时仍需要运行校验：

```bash
python3 scripts/download_models.py \
  --manifest model-manifest.json \
  --comfy-root /data/minimax-h3-stack/ComfyUI \
  --verify-only
```
