# MiniMax H3 API

[中文](README.md) | English

A MiniMax H3 FP8 video generation service with a customer-facing web interface, HTTP API, job queue, generation progress, asset library, incognito jobs, OpenAI-compatible prompt optimization, and FL2VA, Ref2VA, and Turbo LoRA workflows.

Inference runs through an independent ComfyUI service. The web and API service handles parameter validation, asset uploads, job queuing, progress synchronization, artifact management, and privacy isolation.

## Execution Modes

| Mode | Model | Sampling | Reference Assets |
|---|---|---|---|
| Native FL2VA | FP8 Scaled | Native sampler | 1 first-frame image and an optional last-frame image |
| Native Ref2VA | FP8 Scaled | Native sampler | Up to 9 images, 3 videos, and 3 audio clips |
| Turbo FL2VA | FP8 Scaled + 8-step LoRA v1.0 | `res_multistep`, fixed at 8 steps | 1 first-frame image and an optional last-frame image |
| Turbo Ref2VA | Ref2VA FP8 Scaled + FL2VA 8-step LoRA v1.0 | `res_multistep`, fixed at 8 steps | Up to 9 images, 3 videos, and 3 audio clips |
| Optional H3 NSFW | Ref2VA FP8 Scaled + NaughtyTimes LoRA | Native sampler | Available only in incognito mode |

The web interface defaults to 10 sampling steps. The 8-step LoRA acceleration mode is fixed at 8 steps with LoRA strength 1.0. Ref2VA acceleration temporarily reuses the FL2VA 8-step LoRA until a dedicated Ref2VA release is available. The NaughtyTimes LoRA strength is 0.5.

## Minimum Configuration

| Item | Requirement |
|---|---|
| Operating system | Ubuntu 22.04 x86_64 |
| GPU | 1 NVIDIA RTX 4090 24 GB, or an equivalent NVIDIA GPU with 24 GB VRAM |
| Driver | NVIDIA 550.54.14 or newer with CUDA 12.4 runtime support |
| Memory | 64 GB RAM with at least 32 GB swap |
| Storage | 100 GB of available SSD space |
| Python | 3.11 |
| System tools | Git, FFmpeg, aria2, rsync, curl, OpenSSL, and systemd |

The 64 GB memory configuration is the minimum baseline for a single 608x352, 5-second job. The verified server has 125 GiB RAM. Additional memory and storage capacity are required for 720p, 15-second, or concurrent jobs.

Each ComfyUI workflow job uses one GPU. Select the physical GPU with the installer's `GPU_ID` setting.

## One-command Installation

Run the following commands on the cloud GPU server:

```bash
git clone https://github.com/SekiyoKana/minimax-h3-api.git
cd minimax-h3-api
INSTALL_ROOT=/data/minimax-h3-stack GPU_ID=0 bash scripts/install.sh
```

The installer performs the following operations:

1. Checks out the verified ComfyUI and custom-node revisions.
2. Creates isolated Python environments.
3. Downloads approximately 65.4 GB of required models from ModelScope or Hugging Face.
4. Verifies every model's file size and SHA-256 checksum.
5. Installs and starts the ComfyUI and API systemd user services.
6. Generates a random incognito access code and stores it in `.env`.

After installation, open:

```text
http://SERVER_IP:8193/
http://SERVER_IP:8193/docs
```

The NaughtyTimes LoRA currently requires an authorized file supplied by the user:

```bash
INSTALL_ROOT=/data/minimax-h3-stack \
GPU_ID=0 \
INSTALL_NSFW=1 \
NSFW_LORA_FILE=/data/models/NaughtyTimes-lora-MINIMAXH3.safetensors \
bash scripts/install.sh
```

## Verification

```bash
INSTALL_ROOT=/data/minimax-h3-stack bash scripts/verify_install.sh
INSTALL_ROOT=/data/minimax-h3-stack bash scripts/smoke_generation.sh
```

`verify_install.sh` checks source tests, model checksums, ComfyUI nodes, service health, and queue state. `smoke_generation.sh` submits a 608x352, 5-second, 8-step LoRA incognito job.

## Repository Structure

```text
app/                 FastAPI service, job queue, ComfyUI client, prompt rules
static/              Customer-facing web interface
workflows/           Five ComfyUI API-format workflows
scripts/             Installation, model download, verification, smoke test
deploy/              systemd service templates
patches/             Historical compatibility patches
docs/                Model, workflow, API, deployment, and operations docs
model-manifest.json  Model URLs, sizes, SHA-256 checksums, and licenses
```

## Documentation

1. [Cloud GPU Deployment](docs/en/DEPLOYMENT.md)
2. [Model Manifest](docs/en/MODELS.md)
3. [Workflow Manifest](docs/en/WORKFLOWS.md)
4. [API Requests](docs/en/API.md)
5. [Operations](docs/en/OPERATIONS.md)
6. [Verification Snapshot](docs/en/PROJECT_SNAPSHOT.md)
7. [Security](SECURITY.en.md)
8. [Third-party Projects and Licenses](THIRD_PARTY_NOTICES.en.md)

Model weights are not committed to Git. Review the MiniMax H3 Community License Agreement and the terms for each LoRA before use.

## License

Original source code in this repository is licensed under the [MIT License](LICENSE). Model weights, ComfyUI, custom nodes, fonts, and other third-party components remain subject to their respective licenses. See [Third-party Projects and Licenses](THIRD_PARTY_NOTICES.en.md).
