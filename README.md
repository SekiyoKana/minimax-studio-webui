<div align="center">

<img src="assets/h3-studio-logo.png" alt="MiniMax H3 Studio" width="128" />

# MiniMax H3 Studio

MiniMax H3 视频、语音、Music3 与 ComfyUI 工作流控制服务

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-backend-222222?style=flat-square)](https://github.com/Comfy-Org/ComfyUI)
[![MiniMax H3](https://img.shields.io/badge/MiniMax-H3-DF4A32?style=flat-square)](https://huggingface.co/MiniMaxAI/MiniMax-H3)

[中文](README.md) | [English](README.en.md)

[功能](#功能) · [生成方案](#生成方案) · [远端部署](#远端部署) · [任务恢复](#任务恢复) · [API](#api) · [工作流](#工作流) · [验证](#验证)

</div>

MiniMax H3 Studio 为 MiniMax H3 和 Music3 提供统一的网页、HTTP API 与桌面入口。服务端负责素材上传、参数校验、持久化任务队列、节点调度、实时事件和产物管理，ComfyUI 负责模型加载与 GPU 推理。

![MiniMax H3 Studio 工作台](docs/images/h3-studio-overview.jpg)

> [!IMPORTANT]
> 仓库不包含模型权重。部署前请阅读 MiniMax H3、MiniMax Music3、VDN-H3、相关 LoRA、ComfyUI 和自定义节点的许可条件。

## 功能

| 模块 | 能力 |
|---|---|
| 视频生成 | FL2VA、Ref2VA、8-step LoRA、H3 SA、VDN-H3、数字人和 H3 TTS |
| 长视频 | H3 SA 超过 15 秒时自动按合法帧网格拆分、Context Loop 连续生成、裁切重复帧并合并 MP4 |
| VDN-H3 | 8–50 步可调，默认 50 步，根据步数自动选择官方 DMD 或 B stage |
| 音乐生成 | Music3 INT8，支持结构化曲风描述、歌词和 1–300 秒时长 |
| 对话流 | 任务记录、实时进度、取消、重新生成、参数回填和产物下载 |
| 任务恢复 | ComfyUI 断线检测、checkpoint 恢复、任务丢失后的重新提交和节点迁移 |
| 素材库 | 搜索、状态筛选、预览、详情、下载和本地产物管理 |
| 节点管理 | ComfyUI 与 RunningHub 节点新增、启停、健康检查和并发配置 |
| 提示词工具 | H3、Ref2VA、TTS、Music3 曲风和歌词提示词优化 |
| 多端互联 | 局域网或 Tailscale 配对、授权撤销和素材共享 |

## 生成方案

| 方案 | 输入 | 时长 | 步数 | 输出 |
|---|---|---:|---:|---|
| 普通 FL2VA | 1 张首帧，可选 1 张尾帧 | 1–15 秒 | 4–50 | MP4 |
| 普通 Ref2VA | 最多 9 张图片、3 段视频、3 段音频 | 1–15 秒 | 4–50 | MP4 |
| 8-step LoRA | FL2VA 或 Ref2VA 参考素材 | 1–15 秒 | 固定 8 | MP4 |
| MiniMax H3 SA | FL2VA 或 Ref2VA 参考素材 | 1–300 秒 | 固定 8 | MP4 |
| VDN-H3 | FL2VA 或 Ref2VA 参考素材 | 1–15 秒 | 8–50 | MP4 |
| 数字人 | 1 张人物图片和 1 段驱动音频 | 由音频决定 | 固定 20 | MP4 |
| H3 TTS | 人物特征、对白、0–3 段音频参考 | 1–15 秒 | 4–50 | FLAC |
| Music3 | 曲风描述和可选歌词 | 1–300 秒 | 固定 30 | FLAC |
| RunningHub | 目标工作流定义的字段 | 由工作流决定 | 由工作流决定 | 由工作流决定 |

### H3 SA Context Loop

H3 SA 使用低分辨率首阶段、Latent 3D 放大和高分辨率 Sol-Attn 二阶段。时长超过 15 秒时，服务按 H3 合法帧网格拆分，每段最多 362 帧，后续段自动携带 22 帧音视频上下文和上一段 AV latent checkpoint。重复前缀会在输出前裁切，最终片段通过 FFmpeg 合并。

### VDN-H3

VDN-H3 使用 `ApplyVDNH3` 模型补丁节点，不与 Sol-Attn 叠加：

| 步数 | 检查点 | Turbo adapter | 适用路径 |
|---:|---|---|---|
| 8 | `stage-dmd-step-250` | 启用 | 官方 8-step DMD |
| 9–50 | `stage-b-step-2000` | 关闭 | 官方 B stage，推荐 50 步 |

两条路径均使用 `merge` LoRA、`stream` 分支权重和 `grouped` 注意力后端。官方 B stage 的目录名为 `stage-b-step-2000`，项目按此目录加载检查点。

## 远端部署

项目默认面向云 GPU 服务器运行。当前已验证环境为 Ubuntu 22.04、2 张 RTX 4090、Python 3.11、PyTorch 2.6.0 + CUDA 12.4。

验证环境目录和端口：

| 服务 | 地址 | GPU | 目录 |
|---|---|---|---|
| API 与网页 | `http://SERVER_IP:8193` | 调度服务 | `/home/tapcash/ssd2/minimax-h3-api` |
| ComfyUI GPU 1 | `127.0.0.1:8188` | RTX 4090，GPU 1 | `/home/tapcash/ssd2/ComfyUI` |
| ComfyUI GPU 0 | `100.77.224.102:8189` | RTX 4090，GPU 0 | `/home/tapcash/ssd2/ComfyUI` |

只向外部开放 API 端口。ComfyUI 端口应限制为 API 服务或受信任网络访问。

验证环境中，API 使用 `8193`，ComfyUI 节点使用 `8188` 和 `8189`。部署完成后，应通过 `/health` 和两个 ComfyUI 的 `/system_stats` 检查实际状态。

### 一键安装

在 GPU 服务器执行：

```bash
git clone https://github.com/SekiyoKana/minimax-studio-webui.git
cd minimax-studio-webui

INSTALL_ROOT=/data/minimax-h3-stack \
GPU_ID=0 \
MODEL_PROVIDER=modelscope \
bash scripts/install.sh
```

安装脚本负责基础 ComfyUI、API 环境、核心模型、Music3 补丁和 systemd 服务。VDN-H3 使用独立脚本安装节点以及两个官方 stage：

```bash
INSTALL_ROOT=/data/minimax-h3-stack \
bash scripts/install_vdn_h3.sh
```

脚本会安装：

- `ComfyUI/custom_nodes/ComfyUI-VDN-H3`
- `ComfyUI/models/vdn/stage-dmd-step-250/`
- `ComfyUI/models/vdn/stage-b-step-2000/`

模型默认优先从 ModelScope 下载，也可以通过项目安装脚本选择 Hugging Face。模型文件应使用 [`scripts/verify_install.sh`](scripts/verify_install.sh) 和 [`scripts/download_models.py`](scripts/download_models.py) 校验。

> [!WARNING]
> 高分辨率、长时长和 VDN-H3 任务的显存和内存需求高于普通短片段。RTX 4090 上应先使用较低分辨率和较短时长验证工作流。

### 启动后端

登录 GPU 服务器后，在项目目录执行以下命令：

```bash
cd /home/tapcash/ssd2/minimax-h3-api

# 当前验证服务器的 API 服务
systemctl --user enable --now minimax-h3-api.service

# 当前验证服务器的 ComfyUI 服务
sudo systemctl enable --now comfyui.service
sudo systemctl enable --now comfyui_gpu_0.service
```

使用 `scripts/install.sh` 进行标准安装时，API 服务名为 `minimax-studio-webui.service`，启动命令为：

```bash
systemctl --user enable --now comfyui.service
systemctl --user enable --now minimax-studio-webui.service
```

启动完成后，API 与网页地址为：

```text
http://SERVER_IP:8193
```

### 查看服务状态

```bash
systemctl --user status minimax-h3-api.service --no-pager
sudo systemctl status comfyui.service --no-pager
sudo systemctl status comfyui_gpu_0.service --no-pager
```

查看 API 日志：

```bash
journalctl --user -u minimax-h3-api.service -f
```

健康检查：

```bash
curl http://127.0.0.1:8193/health
```

### 服务管理

```bash
systemctl --user restart minimax-h3-api.service
sudo systemctl restart comfyui.service
sudo systemctl restart comfyui_gpu_0.service
```

标准安装对应的 API 服务名为 `minimax-studio-webui.service`。

### 任务恢复

API 将任务状态保存在 `data/jobs/<job_id>.json`，ComfyUI 返回 `prompt_id` 后写入远端任务 checkpoint。API 服务重启后会优先查询原任务，并保留原任务进度和节点信息。

ComfyUI WebSocket 断开后，API 使用 HTTP `/history` 和 `/queue` 查询任务状态。原 `prompt_id` 同时从 ComfyUI 队列和历史中消失约 5–6 秒后，API 会清除旧 checkpoint 并重新提交任务，最多重新提交 3 次。原节点不可用时，任务改用自动调度选择健康节点。

查看恢复日志：

```bash
journalctl --user -u minimax-h3-api.service --no-pager \
  | grep -E '任务状态暂不可见|远端任务已丢失|重新提交|重新连接'
```

## 桌面应用

桌面应用支持 macOS 和 Windows。本机保存任务记录、素材、生成结果、节点配置和 AI 配置，远端 ComfyUI 执行 GPU 推理。

```bash
python3 -m venv .venv-desktop
. .venv-desktop/bin/activate
pip install -r requirements-desktop.txt
python scripts/run_desktop.py
```

指定远端节点：

```bash
H3_DEFAULT_COMFY_URL=http://192.168.1.20:8188 \
H3_DEFAULT_COMFY_NAME="远端 ComfyUI" \
python scripts/run_desktop.py
```

桌面应用数据目录：

| 系统 | 目录 |
|---|---|
| macOS | `~/Library/Application Support/MiniMax H3 Studio` |
| Windows | `%LOCALAPPDATA%\\MiniMax H3 Studio` |

打包命令：

```bash
python scripts/build_desktop.py
```

## API

API 文档地址：`http://SERVER_IP:8193/docs`

### VDN-H3 50 步任务

`execution_mode=vdn-h3` 开启 VDN-H3。选择 `steps=50` 时服务自动使用 `stage-b-step-2000`。

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=固定机位，人物持续向前行走，保持身份、光线和环境声音连续。' \
  -F 'reference_manifest=[{"type":"image"}]' \
  -F 'references=@first-frame.png;type=image/png' \
  -F 'model_variant=fl2va-fp8' \
  -F 'execution_mode=vdn-h3' \
  -F 'width=864' \
  -F 'height=480' \
  -F 'duration=15' \
  -F 'steps=50' \
  -F 'seed=1234' \
  -F 'comfy_node=auto'
```

### VDN-H3 8 步任务

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=连续电影镜头，人物完成一个自然转身。' \
  -F 'reference_manifest=[{"type":"image"}]' \
  -F 'references=@first-frame.png;type=image/png' \
  -F 'model_variant=fl2va-fp8' \
  -F 'execution_mode=vdn-h3' \
  -F 'width=608' \
  -F 'height=352' \
  -F 'duration=5' \
  -F 'steps=8'
```

### 常用接口

| 方法 | 路径 | 功能 |
|---|---|---|
| `GET` | `/health` | 服务、节点、队列和 GPU 状态 |
| `GET` | `/api/v1/comfy/nodes` | 查询推理节点 |
| `POST` | `/api/v1/generations` | 创建生成任务 |
| `GET` | `/api/v1/generations/{job_id}` | 查询任务状态和日志 |
| `POST` | `/api/v1/generations/{job_id}/cancel` | 取消任务 |
| `POST` | `/api/v1/generations/{job_id}/regenerate` | 重新生成 |
| `GET` | `/api/v1/generations/{job_id}/result` | 下载生成产物 |
| `GET` | `/api/v1/events` | SSE 实时事件流 |
| `POST` | `/api/v1/prompts/optimize` | 优化 H3 提示词 |
| `POST` | `/api/v1/music/assist` | Music3 曲风或歌词辅助 |

设置 `H3_API_KEY` 后，`/api/v1/*` 需要使用：

```text
Authorization: Bearer YOUR_API_KEY
```

完整请求字段、Ref2VA 素材顺序和错误码见 [`docs/API.md`](docs/API.md)。

## 工作流

所有 JSON 文件均为 ComfyUI API 格式，可直接提交给 ComfyUI `/prompt` 接口。服务端会在提交前注入提示词、素材、分辨率、帧数、步数、随机种子和输出前缀。

| 文件 | 方案 |
|---|---|
| `minimax_h3_fl2va_fp8_720p_15s_api.json` | 普通 FL2VA |
| `minimax_h3_ref2va_fp8_scaled_api.json` | 普通 Ref2VA |
| `minimax_h3_fl2va_fp8_turbo_lora_api.json` | FL2VA 8-step LoRA |
| `minimax_h3_ref2va_fp8_turbo_lora_api.json` | Ref2VA 8-step LoRA |
| `minimax_h3_ref2va_fp8_dual_sampling_upscale_api.json` | Ref2VA 双阶段采样与 Latent 3D 放大 |
| `minimax_h3_fl2va_fp8_sa_api.json` | H3 SA FL2VA |
| `minimax_h3_ref2va_fp8_sa_api.json` | H3 SA Ref2VA |
| `minimax_h3_fl2va_vdn_api.json` | VDN-H3 FL2VA，8–50 步动态 stage |
| `minimax_h3_ref2va_vdn_api.json` | VDN-H3 Ref2VA，8–50 步动态 stage |
| `minimax_h3_ref2va_fp8_digital_human_api.json` | 数字人音频驱动 |
| `minimax_h3_ref2va_fp8_tts_api.json` | H3 TTS |
| `minimax_music3_int8_api.json` | Music3 INT8 |

VDN-H3 节点不与 `SolAttnPatch` 叠加。VDN-H3 节点安装包和来源记录见 [`comfyui_nodes/README.md`](comfyui_nodes/README.md) 与 [`comfyui_nodes/manifest.json`](comfyui_nodes/manifest.json)。

### ComfyUI 节点包

固定版本源码包位于 [`comfyui_nodes/`](comfyui_nodes/)。

| 节点包 | 用途 |
|---|---|
| `ComfyUI-VDN-H3-23470b0.zip` | VDN-H3 的 `ApplyVDNH3` 和高级节点 |
| `ComfyUI-SolAttn_triton-842c4ea.zip` | H3 SA 的 Sol-Attn |
| `Comfyui_Minimax_h3_latent_Upscaler-52a48af.zip` | H3 SA 的 Latent 3D Upscaler |
| `ComfyUI-VideoHelperSuite-993082e.zip` | Ref2VA 视频参考的 `VHS_LoadVideo` |
| `ComfyUI-MultiGPU-62f98ed.zip` | Music3 的多 GPU 文本编码器 |
| `comfyui-minimax-h3-audio-drive-de65ec5.zip` | 数字人的音频驱动节点 |

各压缩包的来源、提交、许可和 SHA-256 见 [`comfyui_nodes/manifest.json`](comfyui_nodes/manifest.json)。

## 配置

复制 `.env.example` 后按部署目录修改：

| 变量 | 作用 |
|---|---|
| `H3_ROOT` | API 项目根目录 |
| `H3_ENGINE` | 推理后端，默认 `comfyui` |
| `H3_HOST` | API 监听地址，默认 `0.0.0.0` |
| `H3_PORT` | API 与网页端口，默认 `8193` |
| `H3_COMFY_URL` | 默认 ComfyUI 地址 |
| `H3_COMFY_POLL_SECONDS` | ComfyUI 状态轮询间隔，默认 2 秒 |
| `H3_COMFY_VDN_WORKFLOW` | VDN-H3 FL2VA 工作流路径 |
| `H3_COMFY_REF2VA_VDN_WORKFLOW` | VDN-H3 Ref2VA 工作流路径 |
| `H3_COMFY_OUTPUT_DIR` | ComfyUI 输出目录 |
| `H3_API_KEY` | 可选 Bearer Token |
| `H3_MAX_UPLOAD_MB` | 上传文件大小上限，默认 512 MB |
| `H3_REMOTE_RECONNECT_SECONDS` | 远端任务重连时间窗口 |

节点地址、启用状态、健康检查间隔和 RunningHub 配置保存在 `data/config.db`。

## 验证

运行项目测试：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node --check static/app.js
git diff --check
```

当前本地契约测试覆盖 API、工作流动态参数、VDN-H3 8/50 步 stage 选择、桌面应用和节点包清单。

远端检查：

```bash
curl http://SERVER_IP:8193/health
curl http://COMFY_IP:8188/object_info/ApplyVDNH3
curl http://COMFY_IP:8189/object_info/ApplyVDNH3
```

## 项目结构

```text
app/                  FastAPI、任务队列、节点调度和 ComfyUI 客户端
static/               中英文响应式网页
workflows/            H3、H3 SA、VDN-H3、双阶段采样和 Music3 API 工作流
comfyui_nodes/        固定版本节点源码包和校验清单
scripts/              安装、模型下载、验证、桌面打包和生成测试
deploy/               systemd 服务模板
patches/              ComfyUI 兼容补丁
docs/                 API、部署、模型、工作流和运行维护文档
data/                 SQLite 配置、任务状态、上传素材和 API 产物
tests/                API 契约与桌面功能测试
model-manifest.json   核心模型来源、大小和 SHA-256
```

## 文档

- [云 GPU 部署](docs/DEPLOYMENT.md)
- [API 参考](docs/API.md)
- [模型清单](docs/MODELS.md)
- [工作流清单](docs/WORKFLOWS.md)
- [桌面应用](docs/DESKTOP.md)
- [运行维护](docs/OPERATIONS.md)
- [ComfyUI 节点包](comfyui_nodes/README.md)
- [安全说明](SECURITY.md)
- [第三方项目与许可](THIRD_PARTY_NOTICES.md)
