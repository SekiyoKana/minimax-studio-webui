<div align="center">

<img src="assets/h3-studio-logo.png" alt="MiniMax H3 Studio" width="128" />

# MiniMax H3 Studio

MiniMax H3 视频、语音、Music3 与 ComfyUI 工作流控制服务

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-backend-222222?style=flat-square)](https://github.com/Comfy-Org/ComfyUI)
[![MiniMax H3](https://img.shields.io/badge/MiniMax-H3-DF4A32?style=flat-square)](https://huggingface.co/MiniMaxAI/MiniMax-H3)

[中文](README.md) | [English](README.en.md)

[功能](#功能) · [数据流程](#数据流程) · [更新日志](#更新日志) · [部署](#部署) · [API](#api) · [验证](#验证)

</div>

MiniMax H3 Studio 为 MiniMax H3、H3 TTS、数字人、Music3 和通用 RunningHub 工作流提供统一的网页界面、HTTP API 与桌面入口。服务负责请求校验、参考文件上传、持久化队列、推理节点调度、实时事件、任务恢复、素材管理和产物交付。

![工作台](docs/images/h3-studio-overview.jpg)

> [!IMPORTANT]
> 仓库不包含模型权重。部署前请确认 MiniMax H3、Music3、相关 LoRA、ComfyUI 和自定义节点的许可条件。

## 功能

| 模块 | 能力 |
|---|---|
| 视频生成 | FL2VA、Ref2VA、8 步 LoRA、双阶段采样、H3 SA、VDN H3、数字人和 H3 NSFW |
| 音频生成 | Music3 INT8 和 H3 TTS，支持歌词、曲风描述和音频参考 |
| 长视频 | H3 SA 按合法帧网格拆分、传递上下文、裁切重复帧并合并视频 |
| VDN H3 | 8 至 50 步，自动选择 DMD 或 B stage 路径 |
| 任务队列 | 持久化排队、节点调度、取消、重新生成、checkpoint 恢复和实时进度 |
| 总体耗时 | 从任务开始由推理节点处理起计算，排队等待时间不计入 |
| 素材库 | 搜索、分页、状态筛选、视频首帧封面缓存、预览、下载和重命名 |
| 文件夹 | 单层文件夹、双击进入、批量移动、未分组根目录和删除保护 |
| 本地素材管理 | 容量统计、30 天前视频预览清理、素材所有权校验和产物删除 |
| 详情窗口 | 无背景模糊、窗口阴影、多个窗口同时打开、独立拖拽和详情侧栏收起 |
| 节点管理 | ComfyUI 与 RunningHub 节点配置、健康检查、启停和并发设置 |
| 多端互联 | 局域网或 Tailscale 配对、授权撤销、本机代理任务和远端素材只读访问 |
| Agent 接入 | Swagger UI、OpenAPI JSON、公开 `AGENT.md` 和 Skill 创建规范 |

前端还包括素材库宽度拖拽、宽度 `localStorage` 持久化、最大 50% 宽度、固定素材卡片尺寸、隐藏滚动条、调整宽度后的补页加载、日志产物定位和实时日志尾部跟随控制。

## 界面截图

| 工作台 | 数字人工作流 |
|---|---|
| ![工作台](docs/images/h3-studio-overview.jpg) | ![数字人](docs/images/h3-studio-digital-human.jpg) |

## 数据流程

```mermaid
flowchart LR
    A[网页或 Agent 请求] --> B[FastAPI 参数校验]
    B --> C[保存上传文件与任务 JSON]
    C --> D[JobStore 持久化队列]
    D --> E[节点健康检查与调度]
    E --> F{推理后端}
    F --> G[ComfyUI]
    F --> H[RunningHub]
    G --> I[checkpoint、进度和事件]
    H --> I
    I --> J[生成产物与视频首帧封面]
    J --> K[素材库、文件夹和下载接口]
```

任务目录和配置数据保存在 `data/`：

| 路径 | 数据 |
|---|---|
| `data/config.db` | 节点、文件夹、桌面设置和互联设备 |
| `data/jobs/` | 任务 JSON、任务日志和 checkpoint |
| `data/uploads/` | 任务参考文件 |
| `data/outputs/` | API 管理的生成产物、sidecar 和视频封面 |

任务进入终态后，`elapsed_seconds` 使用 `started_at` 到终态时间的差值。旧任务缺少 `started_at` 时使用创建时间兼容显示。

## 更新日志

### 2026-09-23：视频超分与自动超分

- 增加真人、动画、3D 三类图片和视频 2x、4x 超分。
- 增加生成后自动超分选项，普通视频生成任务完成后在同一任务内继续执行超分，并直接返回超分视频。
- 增加长视频按 GPU 空闲显存、输入分辨率和倍率自动切片，支持切片进度、checkpoint 恢复、合并和中间文件清理。
- 将 ComfyUI 和 API 单文件上传上限调整为 2048 MB。
- 核对远程 ComfyUI 中新增的 LTX 2x 模型，确认其需要潜空间超分工作流，当前像素超分流继续使用已验证的图像超分模型。

更新记录同时包含代码、工作流、文档、测试和云端发布过程。当前工作区状态截至 2026-09-23。

### 2026-08-07 至 2026-08-13：基础服务与视频方案

- 建立 FastAPI 服务、ComfyUI 引擎适配、任务队列和网页工作台。
- 增加 FL2VA、Ref2VA、8 步 LoRA 和数字人工作流。
- 增加驱动音频时长读取、视频产物回传和基础 API 文档。
- 加入项目 Logo、工作台截图和英文文档。

### 2026-08-14：Music3 与多节点调度

- 增加 Music3 INT8 工作流、曲风和歌词辅助接口。
- 增加多 ComfyUI 节点配置、健康检查、容量和任务调度。
- 增加 Music3 强制时长补丁、FLAC 输出和余额状态保存。
- 增加消融测试脚本、模型清单和安装校验流程。

### 2026-08-17：RunningHub 动态工作流

- 支持 RunningHub 工作流和 AI App 资源地址解析。
- 根据远端 schema 动态生成文本、数值、枚举、开关和媒体字段。
- 保存工作流 schema、账户余额、当前任务和单次调用费用。
- 在远端参数或账户查询失败时保留最近一次可用运行信息。

### 2026-08-19 至 2026-08-20：桌面应用与多端互联

- 增加 macOS 和 Windows 桌面应用入口。
- 增加设备配对、持久授权、授权撤销、远端任务代理和共享素材库。
- 增加运行日志浮窗、日志启动器拖拽和触控拖拽。
- 增加 `AGENT.md` 安装指南和固定版本节点包清单。

### 2026-09-16：H3 SA、VDN H3 与部署包完善

- 增加 H3 SA 两阶段采样、Latent 3D Upscaler、Sol-Attn 和 Context Loop。
- 增加 VDN H3 的 8 步 DMD 与 9 至 50 步 B stage 自动选择。
- 增加 checkpoint、断线恢复、任务重新提交和节点迁移。
- 补充 VDN H3 节点包、工作流、模型清单和云 GPU 安装脚本。

### 2026-09-17：素材库、Agent 文档与界面交互

- 增加 `asset_folders` 单层文件夹、旧任务迁移和 `folder_id` 归属。
- 根目录只显示未分类本机任务，远端素材保持只读。
- 增加新建、重命名、删除、批量移动和文件夹拖拽归类。
- 删除文件夹前阻止进行中任务，确认后清理任务记录、参考文件、产物、sidecar、封面和日志。
- 增加本地素材容量统计、30 天前视频清理预览、总大小展示和非本机素材删除保护。
- 生成文件使用目录名称前缀和时间戳，已完成产物支持用户重命名。
- 视频首帧封面落盘缓存，重复刷新时直接使用缓存。
- 增加 `/AGENT.md` 公共路由，返回 Markdown 并禁用缓存；同步 OpenAPI、鉴权、任务、素材和 Skill 创建说明。
- 将总体耗时改为从任务开始执行起计算，排队时间不计入。
- 素材库增加固定卡片布局、宽度持久化、隐藏滚动条、调整宽度后的补页加载和目录式文件夹卡片。
- 详情窗口改为无模糊浮动窗口，支持多开、独立拖拽、窗口置顶和默认收起的详情侧栏。

### 更新数据的发布流程

每次更新遵循以下流程：

1. 扫描后端、前端、工作流、测试和文档，确认数据结构与接口影响范围。
2. 修改代码和静态资源，涉及 SQLite 时保留迁移和旧数据兼容逻辑。
3. 增加后端接口契约、前端静态契约和行为回归测试。
4. 执行 Python 语法检查、JavaScript 语法检查、完整 unittest 和差异检查。
5. 更新静态资源版本参数，避免浏览器缓存旧的 HTML、CSS 和 JavaScript。
6. 发布前检查云 GPU 的任务队列、GPU 状态、磁盘空间和 ComfyUI 健康状态。
7. 在 `/home/tapcash/ssd2/backups/` 创建远端备份，排除 `data/`、模型、虚拟环境和用户产物。
8. 分目录同步源码、静态资源、工作流、测试和文档，校验本地与远端 SHA-256。
9. 有执行中任务时只同步可热加载的静态资源；API 重启前确认 checkpoint 可恢复，避免中断生成。
10. 重启 API 后验证 `/health`、`/AGENT.md`、`/docs`、`/openapi.json`、任务恢复、ComfyUI 和完整远端测试。

## 生成方案

| 方案 | 参考输入 | 时长 | 步数 | 产物 |
|---|---|---:|---:|---|
| FL2VA | 首帧图片，可选尾帧图片 | 1 至 15 秒 | 4 至 50 | MP4 |
| Ref2VA | 最多 9 张图片、3 段视频、3 段音频 | 1 至 15 秒 | 4 至 50 | MP4 |
| H3 SA | FL2VA 或 Ref2VA 参考素材 | 1 至 300 秒 | 固定 8 | MP4 |
| VDN H3 | FL2VA 或 Ref2VA 参考素材 | 1 至 15 秒 | 8 至 50 | MP4 |
| 数字人 | 人物图片和驱动音频 | 由音频决定 | 固定 20 | MP4 |
| H3 TTS | 人物特征、对白和音频参考 | 1 至 15 秒 | 4 至 50 | FLAC |
| Music3 | 曲风描述和可选歌词 | 1 至 300 秒 | 固定 30 | FLAC |
| RunningHub | 目标工作流定义的字段 | 由工作流定义 | 由工作流定义 | 由工作流定义 |

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

指定远端 ComfyUI：

```bash
H3_DEFAULT_COMFY_URL=http://192.168.1.20:8188 \
H3_DEFAULT_COMFY_NAME="远端 ComfyUI" \
python scripts/run_desktop.py
```

### API 入口

| 地址 | 作用 |
|---|---|
| `/` | Web 工作台 |
| `/health` | 服务、节点和队列状态 |
| `/docs` | Swagger UI |
| `/openapi.json` | OpenAPI JSON |
| `/AGENT.md` | AI Agent 和 Skill 接入说明 |

设置 `H3_API_KEY` 后，普通 API 请求使用：

```http
Authorization: Bearer YOUR_H3_API_KEY
```

## API

创建视频任务：

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

任务查询和产物下载：

```bash
curl http://127.0.0.1:8193/api/v1/generations/JOB_ID
curl http://127.0.0.1:8193/api/v1/generations/JOB_ID/result -o output.mp4
```

常用接口：

| 方法 | 路径 | 作用 |
|---|---|---|
| `GET` | `/health` | 服务、节点和队列状态 |
| `GET` | `/api/v1/comfy/nodes` | 查询推理节点 |
| `POST` | `/api/v1/generations` | 创建任务 |
| `GET` | `/api/v1/generations/{job_id}` | 查询任务 |
| `POST` | `/api/v1/generations/{job_id}/cancel` | 取消任务 |
| `POST` | `/api/v1/generations/{job_id}/regenerate` | 重新生成 |
| `GET` | `/api/v1/generations/{job_id}/result` | 下载产物 |
| `GET` | `/api/v1/events` | SSE 事件流 |
| `POST` | `/api/v1/prompts/optimize` | H3 提示词优化 |
| `POST` | `/api/v1/music/assist` | Music3 曲风或歌词辅助 |

完整字段、错误码、RunningHub 动态参数、多端互联和素材接口见 [API 参考](docs/API.md)。面向自动化 Agent 的调用顺序、工具封装和验收要求见 [`AGENT.md`](AGENT.md)。

## 素材管理

### 文件夹与归属

文件夹为单层结构，名称长度为 1 至 80 个字符，同级名称按大小写折叠后判重。新任务可以指定 `folder_id`，选择根目录或未分组时归入未分组。

```text
GET    /api/v1/asset-folders
POST   /api/v1/asset-folders
PATCH  /api/v1/asset-folders/{folder_id}
POST   /api/v1/asset-folders/move
DELETE /api/v1/asset-folders/{folder_id}
```

外层素材列表只显示未分类本机任务。双击文件夹进入后显示其中的视频素材。移动使用任务归属关系，不复制文件。远端素材保持只读，不接受移动、重命名和删除。

删除文件夹前会检查排队中和执行中的任务。检查通过后删除文件夹内已结束任务的记录、参考文件、生成产物、sidecar、封面和日志。

### 本地素材管理

```text
GET  /api/v1/assets/local
GET  /api/v1/assets/local/clear-old-video/preview
POST /api/v1/assets/local/clear-old-video
POST /api/v1/assets/local/delete
```

清理 30 天前视频前，客户端应展示所有项目、创建时间、单项大小和总大小，再执行确认。非本机创建的文件和文件夹不可删除。

## 工作流与节点包

API 格式工作流位于 [`workflows/`](workflows/)，固定版本节点包和 SHA-256 清单位于 [`comfyui_nodes/`](comfyui_nodes/)。主要工作流包括：

- `minimax_h3_fl2va_fp8_720p_15s_api.json`
- `minimax_h3_ref2va_fp8_scaled_api.json`
- `minimax_h3_fl2va_fp8_turbo_lora_api.json`
- `minimax_h3_ref2va_fp8_turbo_lora_api.json`
- `minimax_h3_fl2va_fp8_sa_api.json`
- `minimax_h3_ref2va_fp8_sa_api.json`
- `minimax_h3_fl2va_vdn_api.json`
- `minimax_h3_ref2va_vdn_api.json`
- `minimax_h3_ref2va_fp8_digital_human_api.json`
- `minimax_h3_ref2va_fp8_tts_api.json`
- `minimax_music3_int8_api.json`

服务提交前会注入提示词、参考文件、分辨率、帧数、步数、随机种子、文件夹名称前缀和输出路径。

## 部署

安装脚本：

```bash
INSTALL_ROOT=/data/minimax-h3-stack \
PYTHON_BIN=python3.11 \
GPU_ID=0 \
MODEL_PROVIDER=modelscope \
bash scripts/install.sh
```

常用环境变量：

| 变量 | 作用 |
|---|---|
| `INSTALL_ROOT` | ComfyUI、API 和模型根目录 |
| `PYTHON_BIN` | API 和 ComfyUI 使用的 Python |
| `GPU_ID` | ComfyUI 使用的 GPU 编号 |
| `MODEL_PROVIDER` | `modelscope` 或 `huggingface` |
| `COMFY_PORT` | ComfyUI 端口，默认 8188 |
| `API_PORT` | API 端口，默认 8193 |
| `SKIP_MODELS` | 已有模型且校验通过时跳过下载 |
| `START_SERVICES` | 安装后启动服务 |
| `DRY_RUN` | 只打印安装计划 |

部署文档见 [云 GPU 部署](docs/DEPLOYMENT.md)。运行维护、任务恢复和备份规则见 [运行维护](docs/OPERATIONS.md)。

## 验证

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node --check static/app.js
python3 -m py_compile app/main.py app/jobs.py
git diff --check
```

部署目录验证：

```bash
INSTALL_ROOT=/data/minimax-h3-stack bash scripts/verify_install.sh
```

## 项目结构

```text
app/                  FastAPI、任务队列、节点调度和推理客户端
static/               中英文响应式网页
workflows/            H3、H3 SA、VDN H3 和 Music3 API 工作流
comfyui_nodes/        固定版本节点源码包和校验清单
scripts/              安装、下载、验证、桌面打包和生成测试
deploy/               systemd 服务模板
patches/              ComfyUI 兼容补丁
docs/                 API、部署、模型、工作流和运维文档
data/                 SQLite 配置、任务状态、上传素材和产物
tests/                API 契约与桌面功能测试
AGENT.md              AI Agent 接口调用和 Skill 创建指南
```

## 文档

- [API 参考](docs/API.md)
- [云 GPU 部署](docs/DEPLOYMENT.md)
- [运行维护](docs/OPERATIONS.md)
- [模型清单](docs/MODELS.md)
- [工作流清单](docs/WORKFLOWS.md)
- [桌面应用](docs/DESKTOP.md)
- [ComfyUI 节点包](comfyui_nodes/README.md)
- [AI Agent 指南](AGENT.md)
- [安全说明](SECURITY.md)
- [第三方项目与许可](THIRD_PARTY_NOTICES.md)
