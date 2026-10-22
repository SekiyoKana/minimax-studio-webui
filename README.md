<div align="center">

<img src="assets/h3-studio-logo.png" alt="MiniMax H3 Studio" width="128" />

# MiniMax H3 Studio

MiniMax H3 视频、语音、Music3 与 ComfyUI 工作流控制服务

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-backend-222222?style=flat-square)](https://github.com/Comfy-Org/ComfyUI)
[![MiniMax H3](https://img.shields.io/badge/MiniMax-H3-DF4A32?style=flat-square)](https://huggingface.co/MiniMaxAI/MiniMax-H3)

[中文](README.md) | [English](README.en.md)

[功能](#功能) · [界面](#界面) · [工作流](#工作流) · [本地-comfyui](#本地-comfyui) · [数据流程](#数据流程) · [更新日志](#更新日志) · [部署](#部署) · [API](#api) · [验证](#验证)

</div>

MiniMax H3 Studio 为 MiniMax H3、H3 TTS、数字人、Music3 和通用 RunningHub 工作流提供统一的网页界面、HTTP API、桌面入口与 Android 远程客户端。服务负责请求校验、参考文件上传、持久化队列、推理节点调度、实时事件、任务恢复、素材管理和产物交付。

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
| 素材预览 | 点击任意素材都在弹窗内预览：图片、视频播放器、音频「文件名 + 播放器」，无法识别的文件显示未知文件图标 |
| 文件夹 | 单层文件夹、双击进入、批量移动、未分组根目录和删除保护 |
| 本地素材管理 | 容量统计、30 天前视频预览清理、素材所有权校验和产物删除 |
| 详情窗口 | 无背景模糊、窗口阴影、多个窗口同时打开、独立拖拽和详情侧栏收起 |
| 节点管理 | ComfyUI 与 RunningHub 节点配置、健康检查、启停、并发设置和本机/远程判定 |
| 工作流管理 | 内置预设与自定义 ComfyUI 工作流、字段与素材映射、结果节点选择、节点同步和校验 |
| 参考素材槽位 | 自定义工作流可按类型和序号声明 `ref_images` / `ref_videos` / `ref_audios` 槽位，上传数量不再受工作流固定节点数限制 |
| 运行日志 | 顶部功能栏入口、队列数量角标、可拖动弹框、实时进度、工作流同步与生成报错 |
| 本地 ComfyUI | 实验性功能：可直接从应用启动并托管本机 ComfyUI，支持启动路径、私有环境和退出时结束进程 |
| 皮肤系统 | 设置内切换日间 / 夜间 / 跟随系统，皮肤仅改变视觉，不影响功能与数据 |
| 多端互联 | 局域网或 Tailscale 配对、授权撤销、本机代理任务和远端素材只读访问 |
| Android 客户端 | 手机和平板远程连接 Studio 服务，固定 FL2VA FP8 + 8 步 LoRA，支持远端 ComfyUI、RunningHub、多端互联、任务进度和结果下载；当前为 Beta，尚未完成实机测试 |
| Agent 接入 | Swagger UI、OpenAPI JSON、公开 `AGENT.md` 和 Skill 创建规范 |

前端还包括素材库宽度拖拽、宽度 `localStorage` 持久化、最大 50% 宽度、固定素材卡片尺寸、隐藏滚动条、调整宽度后的补页加载、日志产物定位和实时日志尾部跟随控制。

> [!WARNING]
> Android APK 当前处于 Beta 阶段，尚未经过真实 Android 手机或平板实机测试。目前仅完成 APK 构建和代码静态检查；安装、连接、文件选择、下载等设备行为尚未实机验证。

## 界面

| 工作台 | 极光玻璃皮肤 |
|---|---|
| ![工作台](docs/images/h3-studio-overview.jpg) | ![极光玻璃皮肤](docs/images/h3-studio-aurora.jpg) |

| 工作流管理 | 推理节点 |
|---|---|
| ![工作流管理](docs/images/h3-studio-workflows.jpg) | ![推理节点](docs/images/h3-studio-nodes.jpg) |

| 运行日志 | 外观与皮肤 |
|---|---|
| ![运行日志](docs/images/h3-studio-ops.jpg) | ![外观与皮肤](docs/images/h3-studio-skins.jpg) |

## 外观与皮肤

界面提供三种外观模式，在「设置 → 外观」中切换，立即生效：

| 模式 | 行为 |
|---|---|
| 日间 | 固定浅色外观 |
| 夜间 | 固定深色外观 |
| 跟随系统 | 读取 `prefers-color-scheme`，系统深浅色变化时实时切换（默认） |

模式保存在本机 `localStorage` 的 `h3-theme` 键；旧版本的 `h3-skin` 会自动迁移为日间或夜间。底层仍由两套皮肤样式实现：

| 模式 | 底层皮肤 | 风格 |
|---|---|---|
| 日间 | 原野（默认） | Apple 风格浅色：浅灰画布、单一 Action Blue、发丝分隔与胶囊控件 |
| 夜间 | 极光玻璃 Aurora Glass | 深色玻璃拟态：极光背景、青色与紫色渐变、衬线标题 |
| 跟随系统 | 自动选择 | 系统深色时用极光玻璃，否则用原野 |

| 外观设置 | 夜间工作台 |
|---|---|
| ![外观设置](docs/images/h3-studio-skins.jpg) | ![夜间工作台](docs/images/h3-studio-aurora.jpg) |

外观是纯展示层：CSS 只覆盖设计令牌和装饰属性，不改变 DOM 结构、元素顺序、可见性、文案或任何 JavaScript 行为。生成、队列、素材、工作流和 API 在三种模式下完全一致。

### 文字层级

界面文字统一为 10 级，全部通过 `:root` 的 `--text-*` 令牌引用。新增模块不得写死 `font-size`，需要新字号时先扩展令牌。

| 令牌 | 字号 | 用途 |
|---|---:|---|
| `--text-micro` | 10px | 大写分组标签、徽标 |
| `--text-caption` | 11px | 元信息、辅助说明 |
| `--text-small` | 12px | 次级标签、控件文字 |
| `--text-ui` | 13px | 表单、按钮、列表 |
| `--text-body` | 14px | 基础正文 |
| `--text-lead` | 16px | 对话正文、强调 |
| `--text-heading-sm` | 20px | 分区标题 |
| `--text-heading` | 24px | 弹窗与侧栏标题 |
| `--text-display` | 28px | 页面标题 |
| `--text-hero` | 32px | 空状态主标题 |

### 新增外观与皮肤的规则

追加新模块、新外观模式或新皮肤时遵守以下约定，三种模式和既有皮肤都不会被破坏：

1. 组件颜色与字号只使用 `:root` 设计令牌（`--canvas`、`--surface`、`--ink`、`--line`、`--accent`、`--blue`、`--text-*` 等），不要写死色值或 `font-size`。
2. 皮肤样式写入 [`static/skins/skins.css`](static/skins/skins.css)，且必须限定在 `html[data-skin="<id>"]` 之下；不得为了某个皮肤修改基础规则。
3. 皮肤只能覆盖颜色、边框、阴影、圆角、字体和背景；不得改变布局结构、尺寸、元素顺序、可见性或交互逻辑。
4. 皮肤资源放在 `static/skins/<id>/`，预览图固定命名 `preview.jpg`（16:10）。
5. 新增外观模式需要同时更新 [`static/app.js`](static/app.js) 的 `THEMES`、`resolveThemeSkin()` 和设置外观面板的 `data-theme-option` 卡片；`data-skin` 仍只取 `default`（日间）或 `aurora`（夜间）。
6. 新模块若使用 Canvas、WebGL 或图表等无法被 CSS 换肤的绘制方式，监听 `h3:themechange` 事件读取 `event.detail.theme` / `event.detail.skin` 后重绘；`h3:skinchange` 仍会在解析后的皮肤变化时派发。
7. 合并前运行完整测试；默认模式必须保持为当前视觉基线，调整基础设计时同步更新文档截图和静态资源版本号，并至少手动检查一次三种模式的关键页面。

## 工作流

内置预设与自定义工作流统一保存在 `data/config.db`。网页端「工作流」弹框可以上传 ComfyUI API 格式 JSON、配置通用字段与参考素材映射、选择结果节点、保存静态输入、指定目标节点和生成区显示。

```text
GET    /api/v1/workflows
POST   /api/v1/workflows
GET    /api/v1/workflows/{workflow_id}
PATCH  /api/v1/workflows/{workflow_id}
DELETE /api/v1/workflows/{workflow_id}
POST   /api/v1/workflows/{workflow_id}/sync
```

- **按任务快照执行**：提交 `workflow_id` 后使用创建时保存的工作流图、映射、版本和目标节点；调度只选择已同步且在线的目标节点。
- **参考素材槽位**：映射里 `input` 填 `ref_images` / `ref_videos` / `ref_audios` 并带 `"slot": true` 时，引擎按素材序号动态创建 `LoadImage`、`VHS_LoadVideo`、`LoadAudio`，接到 `ref_image_N` / `ref_video_N` / `ref_audio_N`。上传更多参考素材时会继续扩展槽位，不再受工作流内固定节点数量限制。
- **报错集中到运行日志**：导入、校验、同步失败不再占用弹框顶部的提示区域，而是写入右侧「运行日志」并保留上游原始报错。
- **同步与校验**：保存后服务会尝试把工作流副本同步到目标节点的 ComfyUI 用户目录，并按节点记录同步状态。

## 本地 ComfyUI

设置 →「实验性功能」中的「绑定本地 ComfyUI 服务」默认关闭。开启后：

- 判定为本机环境的 ComfyUI 节点（`localhost`、`127.0.0.1`、本机网卡 IP）在推理节点列表中显示黄色的「可接管」标签；托管服务运行起来后标签变为绿色的「已接管」。
- 编辑节点时可填写 ComfyUI 启动路径（目录或 `main.py`），支持 Windows 与 macOS 的写法：`~` 展开、正斜杠与反斜杠互换、`file://` 前缀均可识别。
- 节点卡片右上角的开关用于启动 / 停止托管进程。启动时优先使用启动目录中的私有环境（`venv`、`.venv`、`env`，Windows 取 `Scripts/python`，macOS 取 `bin/python`），找不到则回退全局 Python。
- 子进程以 `--listen 127.0.0.1 --port <节点端口>` 运行，日志写入 `data/local-comfy/<节点>.log` 并同步到运行日志；启动失败会在卡片内显示原始报错。
- 应用退出时会结束自己启动的托管进程（Windows 额外用 Job 对象兜底）；外部启动的 ComfyUI 不受影响，应用内也无法关闭，只会提示手动关闭。

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
| `data/config.db` | 节点、文件夹、工作流、桌面设置和互联设备 |
| `data/jobs/` | 任务 JSON、任务日志和 checkpoint |
| `data/uploads/` | 任务参考文件 |
| `data/outputs/` | API 管理的生成产物、sidecar 和视频封面 |
| `data/local-comfy/` | 托管的本地 ComfyUI 进程日志 |

任务进入终态后，`elapsed_seconds` 使用 `started_at` 到终态时间的差值。旧任务缺少 `started_at` 时使用创建时间兼容显示。

## 更新日志

### 2026-10-23

- 素材点击统一改为弹窗预览：参考素材缩略图、消息素材卡片、详情源文件列表都不再触发浏览器下载或跳转，图片显示图片、视频显示播放器、音频显示「文件名 + 播放器」、无法识别的文件显示未知文件图标；下载能力保留在明确的「下载」按钮上。
- 自定义工作流支持可变数量的图片、视频和音频：参考素材映射可绑定 `ref_images` / `ref_videos` / `ref_audios` 槽位，引擎按序号自动创建加载节点，编辑器选择工作流后会自动识别可用槽位。
- 工作流导入、校验、同步的报错改由右侧「运行日志」弹框展示并记录原始错误，工作流列表不再被提示文本挤占。
- 推理节点列表的本机 ComfyUI 标签区分状态：未运行显示黄色的「可接管」，托管服务运行后变为绿色的「已接管」。
- 修复新增工作流同步失败：ComfyUI 的 `/userdata/{file}` 只匹配单段路径，同步改为把目录分隔符编码成 `%2F` 写入 `workflows/`，不再返回 405。

### 2026-10-22

- 界面按 apple.com 的语言重做：浅灰画布、发丝分隔线、单一 Action Blue、胶囊按钮与分段控件，字号收敛为 10 级 `--text-*` 令牌。
- 外观从皮肤列表改为「日间 / 夜间 / 跟随系统」三种模式，底层继续使用原野与极光玻璃两套皮肤；跟随系统监听 `prefers-color-scheme` 实时切换。
- 运行日志从浮动窗口移入顶部功能栏，队列数量以角标显示；弹框不显示遮罩、可拖动、点击入口/关闭按钮或按 Esc 关闭。
- 设置新增「实验性功能」页签：绑定本地 ComfyUI 服务，支持可接管判定、启动路径、私有环境、实时日志与退出时结束托管进程。
- 前端请求统一发送 `Accept-Language`，后端 `HTTPException` 按语言返回错误；补齐设置、节点、工作流、素材、超分、互联等弹窗的中英文文案。
- 推理节点按地址区分本机 / 远程，弹框改为固定尺寸的横幅卡片，新增 / 编辑改为独立弹窗；新增 RunningHub 端点开关与自动调度排除选项。
- Music3 切换到该工作流时输入区改为提示词与歌词左右分栏；视频超分改为独立入口，先选择类型与倍率再提交，不重置当前工作区。

### 2026-10-21：自定义工作流管理与参考图压缩

- 内置预设与自定义工作流统一写入 `data/config.db`，新增工作流增删改、查询与同步接口。
- 网页端新增工作流管理面板：上传 ComfyUI API 格式 JSON，配置通用字段与参考素材映射，选择结果节点，保存静态输入，指定目标节点和生成区显示。
- 自定义工作流按任务快照执行；提交 `workflow_id` 后使用创建时保存的图、映射、版本和目标节点，调度只选择已同步且在线的节点。
- 新增 `auto_compress_large_images` 设置，参考图片超过 1 MB 时在浏览器本地压缩后再上传。
- 设置窗口拆分为模型、系统、上传三个页签；自定义工作流支持视频、音频和图片产物识别。

### 2026-10-02：数据库工作流配置（Beta）

- 增加通过数据库保存 ComfyUI 工作流配置、工作流导入和节点同步接口。
- 私密模式中的自定义工作流与 H3 NSFW 预设仅对有效授权码可见。

### 2026-09-27：Android 远程客户端 Beta

- 增加纯远程 Android APK，支持手机和平板布局；客户端不在设备上安装 Python、ComfyUI、节点或模型。
- 增加首次启动服务器地址检测、可选 `H3_API_KEY`、WebView Cookie 认证、文件选择、结果下载和返回键处理。
- 增加 `android/` Gradle 工程和 debug APK 产物，暂定为 Beta 版本。

### 2026-09-23：视频超分与自动超分

- 增加真人、动画、3D 三类图片和视频 2x、4x 超分，以及生成后自动超分。
- 长视频按 GPU 空闲显存、输入分辨率和倍率自动切片，支持切片进度、checkpoint 恢复、合并和中间文件清理。
- 将 ComfyUI 和 API 单文件上传上限调整为 2048 MB。

### 2026-09-17：素材库、Agent 文档与界面交互

- 增加 `asset_folders` 单层文件夹、旧任务迁移和 `folder_id` 归属；根目录只显示未分类本机任务，远端素材保持只读。
- 增加新建、重命名、删除、批量移动和文件夹拖拽归类；删除文件夹前阻止进行中任务，确认后清理任务记录、参考文件、产物、sidecar、封面和日志。
- 增加本地素材容量统计、30 天前视频清理预览、总大小展示和非本机素材删除保护。
- 视频首帧封面落盘缓存；已完成产物支持用户重命名。
- 增加 `/AGENT.md` 公共路由，返回 Markdown 并禁用缓存；将总体耗时改为从任务开始执行起计算。
- 详情窗口改为无模糊浮动窗口，支持多开、独立拖拽、窗口置顶和默认收起的详情侧栏。

### 2026-09-16：H3 SA、VDN H3 与部署包完善

- 增加 H3 SA 两阶段采样、Latent 3D Upscaler、Sol-Attn 和 Context Loop。
- 增加 VDN H3 的 8 步 DMD 与 9 至 50 步 B stage 自动选择。
- 增加 checkpoint、断线恢复、任务重新提交和节点迁移。
- 补充 VDN H3 节点包、工作流、模型清单和云 GPU 安装脚本。

### 2026-08-19 至 2026-08-20：桌面应用与多端互联

- 增加 macOS 和 Windows 桌面应用入口，以及 GitHub Actions 的双平台构建产物。
- 增加设备配对、持久授权、授权撤销、远端任务代理和共享素材库。
- 增加 `AGENT.md` 安装指南和固定版本节点包清单。

### 2026-08-17：RunningHub 动态工作流

- 支持 RunningHub 工作流和 AI App 资源地址解析。
- 根据远端 schema 动态生成文本、数值、枚举、开关和媒体字段。
- 保存工作流 schema、账户余额、当前任务和单次调用费用。

### 2026-08-14：Music3 与多节点调度

- 增加 Music3 INT8 工作流、曲风和歌词辅助接口。
- 增加多 ComfyUI 节点配置、健康检查、容量和任务调度。
- 增加 Music3 强制时长补丁、FLAC 输出和余额状态保存。

### 2026-08-07 至 2026-08-13：基础服务与视频方案

- 建立 FastAPI 服务、ComfyUI 引擎适配、任务队列和网页工作台。
- 增加 FL2VA、Ref2VA、8 步 LoRA 和数字人工作流。
- 增加驱动音频时长读取、视频产物回传和基础 API 文档。

更新日志按时间倒序排列，同一天的所有改动合并为一条，当前状态截至 2026-10-23。Android APK 仍处于 Beta，尚未完成实机验证。

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

桌面版可用 `python scripts/build_desktop.py` 打包（PyInstaller，Windows 生成 `dist/MiniMaxH3Studio` 目录，macOS 生成 `.app` / `.dmg`）。推送到 `main`、`beta` 或打 `v*` 标签时，[GitHub Actions](.github/workflows/build-desktop.yml) 会在 Windows 与 macOS 上构建并上传产物。

### Android APK

`android/` 是纯远程客户端，不在手机或平板上安装 Python、ComfyUI、节点或模型。安装 APK 后输入已运行的 MiniMax Studio 服务地址；应用会先检查 `/health`，再连接服务。ComfyUI 和 RunningHub 节点仍在 Studio 服务端配置，多端互联也由服务端管理。APK 生成界面固定使用 MiniMax H3 FL2VA FP8 和 8-step LoRA。

内网服务可填写 `http://服务器IP:8193`，外网服务建议使用 HTTPS。服务根地址需要能直接打开 Studio 网页与 `/health` 接口。若服务设置了 `H3_API_KEY`，在 APK 连接页一并填写；未设置时留空。

构建需要 JDK 17 和 Android SDK Platform 34：

```bash
cd android
bash gradlew assembleDebug
```

Windows 使用 `gradlew.bat assembleDebug`。可安装 APK 位于 `android/app/build/outputs/apk/debug/app-debug.apk`。该调试版 APK 可直接侧载；公开发布时应使用自己的签名密钥构建 release 版本。

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
| `POST` | `/api/v1/comfy/nodes/{node_id}/local-comfy/start` | 启动托管的本机 ComfyUI |
| `POST` | `/api/v1/comfy/nodes/{node_id}/local-comfy/stop` | 停止托管的本机 ComfyUI |
| `GET` | `/api/v1/workflows` | 查询内置预设与自定义工作流 |
| `POST` | `/api/v1/workflows` | 创建工作流 |
| `PATCH` | `/api/v1/workflows/{workflow_id}` | 修改工作流或生成区显示 |
| `DELETE` | `/api/v1/workflows/{workflow_id}` | 删除自定义工作流 |
| `POST` | `/api/v1/workflows/{workflow_id}/sync` | 同步并校验目标节点工作流 |
| `POST` | `/api/v1/generations` | 创建任务 |
| `GET` | `/api/v1/generations/{job_id}` | 查询任务 |
| `POST` | `/api/v1/generations/{job_id}/cancel` | 取消任务 |
| `POST` | `/api/v1/generations/{job_id}/regenerate` | 重新生成 |
| `GET` | `/api/v1/generations/{job_id}/result` | 下载产物 |
| `GET` | `/api/v1/events` | SSE 事件流 |
| `POST` | `/api/v1/prompts/optimize` | H3 提示词优化 |
| `POST` | `/api/v1/music/assist` | Music3 曲风或歌词辅助 |

提交任务时可传入 `workflow_id` 选择内置预设或自定义工作流；省略时继续按 `model_variant` 与 `execution_mode` 选择内置方案。

完整字段、错误码、RunningHub 动态参数、多端互联和素材接口见 [API 参考](docs/API.md)。面向自动化 Agent 的调用顺序、工具封装和验收要求见 [`AGENT.md`](AGENT.md)。

## 素材管理

### 预览与下载

素材的点击行为统一为预览：参考素材缩略图、消息中的素材卡片和详情里的源文件列表都会打开预览弹窗。弹窗按类型展示图片、视频播放器或「文件名 + 播放器」的音频卡片，无法识别的内容显示未知文件图标与提示。下载只发生在明确的下载按钮上。

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

Linux 和 Windows PC 使用同一套安装逻辑及配套资源包。Linux 使用 Python 安装脚本和资源 ZIP；Windows 使用 PowerShell 脚本和资源 ZIP，BAT 文件提供双击入口。运行后输入目标 ComfyUI 目录，无需将安装文件迁移到目标目录。安装器会检查目标路径，复用有效的 ComfyUI 安装，或在空目录/新目录中安装 ComfyUI 本体，然后自动导入资源并下载匹配显存的模型。节点包、工作流、补丁和 Windows 所需的 Python 安装核心均在 ZIP 中，不会从 GitHub 下载安装脚本或项目资源。模型权重、PyTorch 和 Python 依赖仍需联网下载；安装器会测速 ModelScope、Hugging Face 和 HF-Mirror 后选择下载源。详见 [Agent ComfyUI 安装指南](AGENT_HOW_TO_INSTALL.md)。

Linux 使用 Python 3.11 运行：

```bash
python3.11 scripts/install_minimax_comfyui.py
```

Windows 安装 Python 3.11，将 `scripts/install_minimax_comfyui.ps1` 与 `scripts/MiniMaxH3-ComfyUI-Resources.zip` 放在同一目录；双击 `scripts/install_minimax_comfyui.bat` 可启动 PowerShell 入口，也可运行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install_minimax_comfyui.ps1`。PowerShell 从 ZIP 提取安装核心到临时目录运行，Windows 不需要单独放置 `.py` 文件。自动方案在 24 GB 级 NVIDIA GPU 上使用 H3 FL2VA 8 步模型；16 至 23 GB 显存时选择 Music3 INT8；更低显存或未检测到 NVIDIA GPU 时只安装兼容节点和工作流。Agent 可使用 `--comfy-root`、`--model-profile` 和 `--model-provider` 参数进行无交互部署。

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
app/                  FastAPI、任务队列、工作流配置、节点调度、本地 ComfyUI 托管和推理客户端
static/               中英文响应式网页
static/design.css     Apple 风格视觉层（画布、字号、表面、控件）
static/skins/         皮肤样式、预览图与背景资源
workflows/            H3、H3 SA、VDN H3 和 Music3 API 工作流
comfyui_nodes/        固定版本节点源码包和校验清单
scripts/              安装、下载、验证、桌面打包和生成测试
android/              纯远程 Android 客户端（Beta）
deploy/               systemd 服务模板
patches/              ComfyUI 兼容补丁
docs/                 API、部署、模型、工作流和运维文档
data/                 SQLite 配置、任务状态、上传素材和产物
tests/                API 契约、工作流和桌面功能测试
AGENT.md              AI Agent 接口调用和 Skill 创建指南
AGENT_HOW_TO_INSTALL.md  ComfyUI 与节点包安装指南
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
