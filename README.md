<div align="center">

<img src="assets/h3-studio-logo.png" alt="MiniMax H3 Studio" width="128" />

# MiniMax H3 Studio

MiniMax H3、Music3、RunningHub 与视频超分的 Web、HTTP API 和桌面工作台

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square)](https://fastapi.tiangolo.com/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-backend-222222?style=flat-square)](https://github.com/Comfy-Org/ComfyUI)
[![MiniMax H3](https://img.shields.io/badge/MiniMax-H3-DF4A32?style=flat-square)](https://huggingface.co/MiniMaxAI/MiniMax-H3)

[English](README.en.md)

</div>

MiniMax H3 Studio 将 FastAPI、JobStore、ComfyUI 和 RunningHub 集成为一个任务工作台，提供视频生成、音乐与语音生成、数字人、视频超分、素材管理、节点调度、任务恢复和 Agent API。

![工作台](docs/images/h3-studio-overview.jpg)

> [!IMPORTANT]
> 仓库不包含模型权重。部署前需要确认 MiniMax H3、Music3、LoRA、ComfyUI 和自定义节点的许可条件。

## 功能

| 模块 | 内容 |
|---|---|
| 视频生成 | FL2VA、Ref2VA、8 步 LoRA、双采样、H3 SA、VDN H3、数字人和 H3 NSFW |
| 视频超分 | 真人、动画、3D 分类的 2x、4x 图片和视频超分 |
| 自动超分 | 在同一个视频任务内生成视频并继续超分，最终直接返回超分视频 |
| 长视频处理 | 根据 GPU 空闲显存、输入分辨率和倍率自动切片，支持逐片进度、checkpoint 恢复、合并和清理 |
| 音频生成 | Music3 INT8、H3 TTS、歌词和曲风辅助 |
| 任务系统 | 持久化队列、节点调度、取消、重新生成、checkpoint 恢复和 SSE 事件 |
| 素材库 | 搜索、状态筛选、视频封面、文件夹、重命名、下载和本地清理 |
| 多端互联 | 局域网或 Tailscale 配对、远端节点代理和只读远端素材 |
| Agent 接入 | `/docs`、`/openapi.json` 和 `/AGENT.md` |

## 超分模型

当前默认模型矩阵：

| 分类 | 2x | 4x |
|---|---|---|
| 真人 | `RealESRGAN_x2plus.pth` | `4x_foolhardy_Remacri.pth` |
| 动画 | `4x-AnimeSharp.pth`，结果缩放到 2x | `4x-AnimeSharp.pth` |
| 3D | `2xNomosUni_span_multijpg.pth` | `4x-UltraSharp.pth` |

远程 ComfyUI 中还检测到 3 个 LTX 2x 潜空间模型。它们需要 `LatentUpscaleModelLoader` 和独立潜空间工作流，当前像素图像和视频超分流使用的 `UpscaleModelLoader` 无法加载这些模型，因此暂不加入默认矩阵。

消融结果见 [超分模型消融报告](reports/ablation/upscale_ablation.md)，原始结果见 [upscale_ablation.json](reports/ablation/upscale_ablation.json)。

## 快速开始

### API 服务

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements-api.txt

export H3_ROOT="$PWD"
export H3_COMFY_URL="http://127.0.0.1:8188"
export H3_PORT=8193
./run.sh
```

没有 ComfyUI 时可以使用测试引擎：

```bash
H3_FAKE_ENGINE=1 H3_ENGINE=fake ./run.sh
```

### 桌面应用

```bash
python3 -m venv .venv-desktop
. .venv-desktop/bin/activate
pip install -r requirements-desktop.txt
python scripts/run_desktop.py
```

使用远程 ComfyUI：

```bash
H3_DEFAULT_COMFY_URL=http://192.168.1.20:8188 \
H3_DEFAULT_COMFY_NAME="远端 ComfyUI" \
python scripts/run_desktop.py
```

## API 示例

服务默认地址为 `http://127.0.0.1:8193`。设置 `H3_API_KEY` 后，API 请求需要携带：

```http
Authorization: Bearer YOUR_H3_API_KEY
```

### 创建视频任务

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=固定机位，人物持续向前行走，保持人物身份和环境连续。' \
  -F 'reference_manifest=[{"type":"image"}]' \
  -F 'references=@first-frame.png;type=image/png' \
  -F 'model_variant=fl2va-fp8' \
  -F 'execution_mode=turbo-lora' \
  -F 'width=864' \
  -F 'height=480' \
  -F 'duration=5' \
  -F 'steps=8' \
  -F 'comfy_node=auto'
```

### 创建视频超分任务

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'task_type=upscale' \
  -F 'upscale_category=real' \
  -F 'upscale_scale=2' \
  -F 'reference_manifest=[{"type":"video"}]' \
  -F 'references=@input.mp4;type=video/mp4' \
  -F 'comfy_node=auto'
```

### 生成后自动超分

普通视频生成任务支持在同一个任务内继续执行超分：

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=固定机位，雪原上的人物向镜头走来。' \
  -F 'reference_manifest=[{"type":"image"}]' \
  -F 'references=@first-frame.png;type=image/png' \
  -F 'model_variant=fl2va-fp8' \
  -F 'execution_mode=turbo-lora' \
  -F 'width=864' \
  -F 'height=480' \
  -F 'duration=5' \
  -F 'steps=8' \
  -F 'auto_upscale=true' \
  -F 'auto_upscale_category=real' \
  -F 'auto_upscale_scale=2' \
  -F 'comfy_node=auto'
```

网页端可在发送区的“更多设置”中启用“生成后自动超分”。提交时会确认超分类型和倍率。

| 参数 | 取值 |
|---|---|
| `auto_upscale` | `true` 或 `false` |
| `auto_upscale_category` | `real`、`anime`、`3d` |
| `auto_upscale_scale` | `2`、`4` |

### 查询和下载

```bash
curl http://127.0.0.1:8193/api/v1/generations/JOB_ID
curl http://127.0.0.1:8193/api/v1/generations/JOB_ID/result -o output.mp4
```

常用入口：

| 方法 | 路径 | 作用 |
|---|---|---|
| `GET` | `/health` | 服务、节点和队列状态 |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/openapi.json` | OpenAPI JSON |
| `POST` | `/api/v1/generations` | 创建任务 |
| `GET` | `/api/v1/generations/{job_id}` | 查询任务 |
| `POST` | `/api/v1/generations/{job_id}/cancel` | 取消任务 |
| `GET` | `/api/v1/generations/{job_id}/result` | 下载产物 |
| `GET` | `/api/v1/events` | SSE 事件流 |

完整字段和错误码见 [API 参考](docs/API.md)。Agent 调用顺序见 [AGENT.md](AGENT.md)。

## 长视频和任务恢复

视频超分任务使用一个 JobStore 任务。服务会根据以下因素计算切片帧预算：

1. 目标 ComfyUI 节点的 GPU 空闲显存。
2. 输入视频分辨率和帧率。
3. 请求的超分倍率。

每个切片使用 `ImageUpscaleWithModelBatched` 按单帧处理。任务日志显示完整切片进度，例如 `视频切片 1/20`。每个正在处理的切片都会保存远端 checkpoint，任务中断后从最后一个有效切片继续。合并成功后会清理 API 中间文件、ComfyUI 输入切片、ComfyUI 输出片段、PNG 元数据和 sidecar。

API 和 ComfyUI 的单文件上传上限默认均为 2048 MB，可通过 `H3_MAX_UPLOAD_MB` 调整 API 上限。

## 工作流

所有文件均为 ComfyUI API 格式，可直接提交给 `/prompt`：

| 文件 | 作用 |
|---|---|
| `minimax_h3_fl2va_fp8_720p_15s_api.json` | FL2VA 普通视频 |
| `minimax_h3_ref2va_fp8_scaled_api.json` | Ref2VA 普通视频 |
| `minimax_h3_fl2va_fp8_turbo_lora_api.json` | FL2VA 8 步加速 |
| `minimax_h3_ref2va_fp8_turbo_lora_api.json` | Ref2VA 8 步加速 |
| `minimax_h3_fl2va_fp8_sa_api.json` | FL2VA H3 SA |
| `minimax_h3_ref2va_fp8_sa_api.json` | Ref2VA H3 SA |
| `minimax_h3_fl2va_vdn_api.json` | FL2VA VDN H3 |
| `minimax_h3_ref2va_vdn_api.json` | Ref2VA VDN H3 |
| `comfy_upscale_image_api.json` | 图片超分 |
| `comfy_upscale_video_api.json` | 视频逐帧超分 |
| `minimax_music3_int8_api.json` | Music3 音乐生成 |
| `minimax_h3_ref2va_fp8_tts_api.json` | H3 TTS |

固定版本 ComfyUI 节点包和 SHA-256 清单见 [comfyui_nodes](comfyui_nodes/)。

## 部署

远程 GPU 部署要求 Ubuntu 22.04、NVIDIA GPU、Python 3.11、FFmpeg、aria2、rsync 和 ComfyUI。安装脚本支持 ModelScope 和 Hugging Face 模型来源：

```bash
INSTALL_ROOT=/data/minimax-h3-stack \
PYTHON_BIN=python3.11 \
GPU_ID=0 \
MODEL_PROVIDER=modelscope \
bash scripts/install.sh
```

当前远程验证环境为 2× RTX 4090。ComfyUI 默认端口为 `8188`，API 默认端口为 `8193`。视频超分输入上限使用 `--max-upload-size 2048`。

详细配置见 [云 GPU 部署](docs/DEPLOYMENT.md)，任务恢复和备份见 [运行维护](docs/OPERATIONS.md)。

## 验证

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node --check static/app.js
python3 -m py_compile app/main.py app/jobs.py
python3 scripts/run_upscale_ablation.py \
  --base-url http://127.0.0.1:8188 \
  --input /path/to/input.png
git diff --check
```

超分模型消融报告见 [reports/ablation/upscale_ablation.md](reports/ablation/upscale_ablation.md)。

## 项目结构

```text
app/                  FastAPI、任务队列、节点调度和推理客户端
static/               中英文响应式网页
workflows/            H3、超分和 Music3 API 工作流
comfyui_nodes/        固定版本节点源码包和清单
scripts/              安装、下载、验证、桌面和消融测试脚本
deploy/               systemd 服务模板
docs/                 API、部署、模型、工作流和运维文档
reports/ablation/     消融测试原始结果和报告
data/                 SQLite 配置、任务状态、上传素材和产物
tests/                API 契约和桌面功能测试
AGENT.md              AI Agent 接口和 Skill 接入说明
```

## 文档

| 文档 | 内容 |
|---|---|
| [API 参考](docs/API.md) | HTTP 字段、错误码、任务和节点接口 |
| [云 GPU 部署](docs/DEPLOYMENT.md) | 服务器、模型、服务和端口配置 |
| [运行维护](docs/OPERATIONS.md) | 队列、checkpoint、日志和备份 |
| [模型清单](docs/MODELS.md) | 模型来源、校验和超分模型审计 |
| [工作流清单](docs/WORKFLOWS.md) | ComfyUI API 工作流和节点说明 |
| [桌面应用](docs/DESKTOP.md) | macOS、Windows 和远程节点配置 |
| [Agent 指南](AGENT.md) | 自动化调用顺序和接入约束 |

项目许可、安全说明、第三方项目和节点许可分别见仓库中的专用文件。
