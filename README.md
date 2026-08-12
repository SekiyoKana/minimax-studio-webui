# MiniMax H3 API

中文 | [English](README.en.md)

MiniMax H3 FP8 视频生成服务，包含客户网页、HTTP API、任务队列、生成进度、素材库、无痕任务、OpenAI 兼容提示词优化、FL2VA、Ref2VA 和 Turbo LoRA 工作流。

推理由独立 ComfyUI 服务执行。Web 与 API 服务负责参数校验、素材上传、任务队列、进度同步、产物管理和隐私隔离。

## 执行方案

| 方案 | 模型 | 采样 | 参考素材 |
|---|---|---|---|
| 普通 FL2VA | FP8 Scaled | 原生采样 | 1 张首帧，可选 1 张尾帧 |
| 普通 Ref2VA | FP8 Scaled | 原生采样 | 最多 9 张图片、3 段视频、3 段音频 |
| Turbo FL2VA | FP8 Scaled + 8-step LoRA v1.0 | `res_multistep`，固定 8 步 | 1 张首帧，可选 1 张尾帧 |
| Turbo Ref2VA | Ref2VA FP8 Scaled + FL2VA 8-step LoRA v1.0 | `res_multistep`，固定 8 步 | 最多 9 张图片、3 段视频、3 段音频 |
| 可选 H3 NSFW | Ref2VA FP8 Scaled + NaughtyTimes LoRA | 原生采样 | 仅在无痕模式中启用 |

网页默认采样步数为 10。8-step LoRA 加速方案固定使用 8 步，LoRA 强度为 1.0。Ref2VA 加速方案暂时复用 FL2VA 8-step LoRA，直到 Ref2VA 专用版本发布。NaughtyTimes LoRA 强度为 0.5。

## 最小可运行配置

| 项目 | 配置 |
|---|---|
| 操作系统 | Ubuntu 22.04 x86_64 |
| GPU | 1 张 NVIDIA RTX 4090 24 GB，或同级 24 GB NVIDIA GPU |
| 驱动 | NVIDIA 550.54.14 或更高版本，支持 CUDA 12.4 Runtime |
| 内存 | 64 GB RAM，并配置至少 32 GB swap |
| 存储 | 100 GB 可用 SSD 空间 |
| Python | 3.11 |
| 系统工具 | Git、FFmpeg、aria2、rsync、curl、OpenSSL、systemd |

64 GB 内存配置用于 608×352、5 秒的最低运行基线。当前验证服务器使用 125 GiB RAM。720p、15 秒或多个并发任务需要增加内存和磁盘余量。

当前 ComfyUI 工作流单次任务使用一张 GPU。安装脚本通过 `GPU_ID` 指定该 GPU。

## 一键安装

以下命令需要在云 GPU 服务器中执行：

```bash
git clone https://github.com/SekiyoKana/minimax-h3-api.git
cd minimax-h3-api
INSTALL_ROOT=/data/minimax-h3-stack GPU_ID=0 bash scripts/install.sh
```

默认行为：

1. 固定安装经过验证的 ComfyUI 和自定义节点版本。
2. 创建隔离 Python 环境。
3. 从 ModelScope 或 Hugging Face 下载约 65.4 GB 的必需模型。
4. 校验每个模型的文件大小和 SHA-256。
5. 安装 systemd 用户服务并启动 ComfyUI 与 API。
6. 为无痕模式生成随机授权码并保存到 `.env`。

安装完成后访问：

```text
http://SERVER_IP:8193/
http://SERVER_IP:8193/docs
```

NaughtyTimes LoRA 当前需要用户自行获得授权文件：

```bash
INSTALL_ROOT=/data/minimax-h3-stack \
GPU_ID=0 \
INSTALL_NSFW=1 \
NSFW_LORA_FILE=/data/models/NaughtyTimes-lora-MINIMAXH3.safetensors \
bash scripts/install.sh
```

## 验证

```bash
INSTALL_ROOT=/data/minimax-h3-stack bash scripts/verify_install.sh
INSTALL_ROOT=/data/minimax-h3-stack bash scripts/smoke_generation.sh
```

`verify_install.sh` 检查源码测试、模型校验、ComfyUI 节点、服务健康状态和队列。`smoke_generation.sh` 提交 608×352、5 秒、8 步的 8-step LoRA 无痕任务。

## 项目结构

```text
app/                 FastAPI、任务队列、ComfyUI 客户端、提示词规范
static/              客户网页
workflows/           五份 API 格式 ComfyUI 工作流
scripts/             安装、模型下载、环境验证、生成测试
deploy/              systemd 服务模板
patches/             历史兼容补丁
docs/                模型、工作流、API、部署和运维文档
model-manifest.json  模型链接、大小、SHA-256 和许可信息
```

## 文档

1. [云 GPU 部署](docs/DEPLOYMENT.md)
2. [模型清单](docs/MODELS.md)
3. [工作流清单](docs/WORKFLOWS.md)
4. [API 请求](docs/API.md)
5. [运行维护](docs/OPERATIONS.md)
6. [验证快照](docs/PROJECT_SNAPSHOT.md)
7. [第三方项目与许可](THIRD_PARTY_NOTICES.md)
8. [英文文档](README.en.md)

模型权重不会提交到 Git。使用前需要阅读 MiniMax H3 Community License Agreement 及各 LoRA 作者条款。

## 许可

本项目自有源码采用 [MIT License](LICENSE)。模型权重、ComfyUI、自定义节点、字体和其他第三方组件适用各自许可，详情见[第三方项目与许可](THIRD_PARTY_NOTICES.md)。
