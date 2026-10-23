# MiniMax H3 Studio · Agent 接入指南

本文档面向需要调用 MiniMax H3 Studio 的 AI Agent、自动化程序和 Skill 作者。部署后可以在同一地址读取本文档：

```text
GET {BASE_URL}/AGENT.md
```

`BASE_URL` 是服务根地址，例如 `http://SERVER_IP:8193`。接口的机器可读定义位于 `{BASE_URL}/openapi.json`，交互式文档位于 `{BASE_URL}/docs`。

阅读顺序：先读「版本与默认约定」，按其中的默认参数直接开工；需要具体接口字段时再查后续章节，并以 `openapi.json` 为准。

## 版本与默认约定

本节是所有调用的前置约定，优先级高于后文的接口细节。

### 版本

| 项目 | 值 |
|---|---|
| 文档版本 | `1.0.0` |
| 对应服务版本 | `APP_VERSION = 1.0.0` |
| 版本来源 | `GET {BASE_URL}/health` 的 `version` 字段 |
| 更新责任 | 仅项目维护者更新版本号，Agent 不得自行修改 |

**每次会话或每批任务提交前检查版本：**

1. 调用 `GET {BASE_URL}/health`，读取 `version`。
2. 与本地 Skill 或脚本记录的 `project_version`（或本文档标注的版本）比较。
3. 版本一致：继续调用业务接口。
4. 版本不一致：重新拉取 `{BASE_URL}/AGENT.md` 和 `{BASE_URL}/openapi.json`：
   - 文档或接口有变化：按新文档更新 Skill，并更新记录的 `project_version`。
   - 文档和接口都没有变化：在 Skill 中标记 `version_mismatch`，保留原逻辑继续，不阻塞任务。
5. 版本检查只用于发现文档或接口变化，不替代 `openapi.json` 的参数校验。

### 默认约定

除用户明确要求其他方案外，按下表执行：

| 场景 | 默认做法 |
|---|---|
| 普通视频 | `execution_mode=turbo-lora`、`steps=8` |
| 首帧 / 首尾帧 | `model_variant=fl2va-fp8` + `turbo-lora` + `steps=8` |
| 多张图片 / 视频 / 音频参考 | `model_variant=ref2va-fp8` + `turbo-lora` + `steps=8` |
| 批量 / 系列 / 短剧任务 | **先创建文件夹，再在文件夹内批量创建任务** |
| 任务等待 | 保存 `id` 与 `status_url`，轮询到终态，不重复提交 |
| 产物下载 | `completed` 后请求 `/result`，视频封面使用 `/preview` |
| 鉴权 | `Authorization: Bearer`，密钥不进 URL、日志或模型上下文 |
| 无痕任务 | `incognito=true` + `X-H3-Incognito-Code`，不进入文件夹系统 |
| 删除、清理类操作 | 客户端明确确认后再执行 |
| 版本检查 | 每轮业务请求前比对 `/health.version` |

默认视频参数：

```text
execution_mode=turbo-lora
steps=8
model_variant=fl2va-fp8   # 或 ref2va-fp8
```

### 三条硬规则

1. **批量任务先建文件夹。** 系列短剧、连续剧情、多场景任务，或任何一次要生成多条的任务，先调用 `POST /api/v1/asset-folders` 创建（或复用同名）文件夹，保存返回的 `folder_id`，然后让这一批次的每个生成请求都带上同一个 `folder_id`。不要先散落创建任务再逐个移动。
2. **请求前检查版本。** 调用业务接口前先读取 `/health.version`；版本不一致时按上一节的流程刷新文档，不带着过期约定继续批量提交。
3. **默认使用 8 步流。** 普通视频默认 `turbo-lora` + `steps=8`，速度最快且效果接近原生 H3 20 步方案；只有需要原生基线、高分辨率二阶段、VDN 或双采等特殊能力时，才切换到其他执行方案。

### 禁止事项

- 不要因为网络超时重复提交同一任务，先按已保存的 `job_id` 查询状态。
- 不要把 `H3_API_KEY`、RunningHub API Key、互联设备令牌、无痕授权码或参考文件内容写入日志、URL 或模型上下文。
- 不要对远端素材执行移动、重命名或删除。
- 不要在客户端未确认时执行删除任务、删除文件夹、清理 30 天视频等破坏性操作。
- 不要自行修改版本号，也不要假设 `openapi.json` 中不存在的字段可用。

## 1. 最小调用流程

建议的最小调用流程如下：

1. 请求 `/health`，确认服务可用，读取 `version`、`nodes`、`online_nodes`、`parallel_capacity`。
2. 请求 `/api/v1/comfy/nodes`，选择可用的本机节点或远端互联节点。
3. 若是批量或系列任务，先请求 `/api/v1/asset-folders` 创建文件夹并保存 `folder_id`。
4. 使用 `multipart/form-data` 请求 `/api/v1/generations` 创建任务。
5. 保存创建响应中的 `id` 和 `status_url`，按间隔请求任务详情，直到状态为 `completed`、`failed` 或 `cancelled`。
6. 状态为 `completed` 时请求 `/api/v1/generations/{job_id}/result` 下载产物，视频封面使用 `/preview`。
7. 需要整理任务时调用文件夹移动接口，需要修改显示名称时调用名称接口。

创建任务后不要因为网络超时直接重复提交。优先使用已保存的 `job_id` 查询状态，避免生成重复产物。

## 2. 项目作用与组件

MiniMax H3 Studio 提供统一的 Web 与 HTTP API，用于：

- 通过 ComfyUI 节点生成 MiniMax H3 视频和 Music3 音频。
- 通过 RunningHub 工作流执行动态参数任务。
- 上传图片、视频、音频和工作流文件作为参考素材。
- 保存任务记录、参考文件、生成产物、视频首帧封面和运行日志。
- 使用单层文件夹管理本机生成任务和产物。
- 通过多端互联访问授权设备的任务、素材和推理节点。

服务由 FastAPI 应用、任务存储、任务调度器、推理引擎适配器和 SQLite 本地状态存储组成：

| 组件 | 作用 |
|---|---|
| FastAPI | 提供 Web 页面、OpenAPI 和 HTTP API |
| `app/jobs.py` | 保存任务、维护队列、运行状态、日志和产物清理 |
| `app/engine.py` | 调用 ComfyUI、RunningHub 和测试引擎 |
| `app/local_state.py` | 保存节点、文件夹、桌面设置和互联设备 |
| `static/` | 提供素材库、任务流、日志和设置页面 |
| `data/jobs/` | 保存任务 JSON、任务日志和事件状态 |
| `data/uploads/` | 保存任务参考文件 |
| `data/outputs/` | 保存本机生成产物和封面 |

默认 API 端口为 `8193`。ComfyUI 默认使用本机内部端口 `8188`，通常不应直接暴露给外部调用者。

## 3. 访问与鉴权

以下地址公开提供只读信息：

| 方法 | 地址 | 说明 |
|---|---|---|
| `GET` | `/` | Web 应用 |
| `GET` | `/health` | 服务和推理节点健康状态 |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/openapi.json` | OpenAPI JSON |
| `GET` | `/AGENT.md` | 本文档 |

当服务设置了环境变量 `H3_API_KEY` 时，普通 API 请求使用以下请求头：

```http
Authorization: Bearer YOUR_H3_API_KEY
```

所有 `/api/v1/*` 普通调用都应携带该请求头。未设置 `H3_API_KEY` 时，普通接口不要求服务级 API Key。不要把 API Key 放在 URL 查询参数中，也不要写入 Skill 日志或模型上下文。

无痕（私密）接口额外要求请求头 `X-H3-Incognito-Code`。授权码由用户在客户端输入，可通过 `POST /api/v1/incognito/authorize` 校验；无痕任务的生成请求必须同时设置 `incognito=true`，且不进入文件夹系统。授权码只放在请求头，不要写入日志、URL 或产物。

多端互联的内部接口使用设备级 Bearer 令牌。`/api/v1/peering/pair`、`/api/v1/peering/revoke`、`/api/v1/peering/export/*` 和 `/api/v1/peering/proxy/*` 不使用服务级 API Key，调用时必须遵循互联接口的设备令牌规则。

错误响应统一为 JSON：

```json
{"detail": "错误说明"}
```

常见状态码如下：

| 状态码 | 含义 |
|---|---|
| `400` | 请求格式错误 |
| `401` | 服务级或设备级鉴权失败 |
| `403` | 当前身份无权执行操作，或资源只读 |
| `404` | 任务、文件夹、节点或文件不存在 |
| `409` | 状态冲突，例如任务仍在运行或文件夹包含进行中任务 |
| `410` | 记录存在，关联文件已经清理 |
| `422` | 参数校验失败或工作流参数无效 |
| `502` | 远端节点或互联设备调用失败 |

## 4. 健康检查与节点

```bash
curl "$BASE_URL/health"
curl -H "Authorization: Bearer $H3_API_KEY" "$BASE_URL/api/v1/comfy/nodes"
```

`/health` 返回：

- `status`：服务状态。
- `engine`：`comfyui` 或 `fake`。
- `gpu`：GPU 标签。
- `nodes`：节点 ID、提供方、健康状态、并发容量和任务信息。
- `online_nodes`：当前在线节点数。
- `parallel_capacity`：在线节点并发容量总和。
- `queue_depth`：服务队列深度。
- `health_interval_seconds`：健康检查间隔。
- `version`：服务版本号，用于 Skill 的版本一致性检查。
- `revision`：任务存储修订号。
- `platform`：`macos`、`windows` 或 `linux`。

`/api/v1/comfy/nodes` 返回节点配置和运行状态。节点提供方为 `comfyui` 或 `runninghub`。创建和修改节点需要管理员级别的服务访问权限，RunningHub 节点还需要 `api_key` 和 `workflow_url`。查询节点时不会返回密钥内容，只返回 `has_api_key`。

开启设置中的实验性功能 `bind_local_comfyui` 后，本机 ComfyUI 节点可用 `POST /api/v1/comfy/nodes/{node_id}/local-comfy/start` 与 `/stop` 由服务托管启动和关闭，节点响应携带 `takeover` 和 `local_runtime`；节点编辑接口可传 `launch_path` 指定 ComfyUI 目录或 `main.py`。应用退出（含窗口关闭）时由 `LocalComfySupervisor.shutdown()` 结束本应用启动的进程，Windows 下另用 kill-on-close Job 对象兜底强制退出场景。详见 `docs/API.md` 的「本地 ComfyUI 接管（实验性）」。

创建 ComfyUI 节点：

```bash
curl -X POST "$BASE_URL/api/v1/comfy/nodes" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"name":"GPU 2","url":"http://10.0.0.12:8188","provider":"comfyui","max_concurrency":1}'
```

创建 RunningHub 节点：

```bash
curl -X POST "$BASE_URL/api/v1/comfy/nodes" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"name":"RunningHub H3","provider":"runninghub","api_key":"YOUR_RUNNINGHUB_API_KEY","workflow_url":"https://www.runninghub.ai/zh-cn/ai-detail/2086401261143273474","max_concurrency":2}'
```

任务的 `comfy_node` 支持以下取值：

- `auto`：由调度器选择可用节点。
- 节点 `id`：定向提交到指定节点。
- `rh:RESOURCE_ID`：在绑定同一 RunningHub 资源 ID 的节点中自动调度。

### ComfyUI 工作流配置

工作流配置保存在 `data/config.db`。内置预设使用数据库中的稳定 ID，包含 `description`、`description_en` 双语简介，只能修改 `visible_in_composer`；自定义工作流支持完整 CRUD，并可选填写最多 500 字符的 `description`。

```text
GET    /api/v1/workflows
POST   /api/v1/workflows
GET    /api/v1/workflows/{workflow_id}
PATCH  /api/v1/workflows/{workflow_id}
DELETE /api/v1/workflows/{workflow_id}
POST   /api/v1/workflows/{workflow_id}/sync
```

自定义工作流通过 `POST /api/v1/workflows` 创建，`workflow_json` 必须是 ComfyUI API 格式（编辑器 UI 格式不能直接使用），并按需提供 `field_mappings`、`reference_mappings`、`static_inputs`、`result_node_id`、`media_type`、`target_node_ids` 和 `visible_in_composer`。`field_mappings` 支持 `prompt`、`lyrics`、`width`、`height`、`ratio`、`megapixels`、`duration`、`num_frames`、`steps` 和 `seed`。

在私密模式中创建的自定义工作流及 H3 NSFW · NaughtyTimes LoRA 预设仅对携带有效 `X-H3-Incognito-Code` 请求头的工作流接口可见或可操作。提交私密工作流任务还必须设置 `incognito=true`；普通模式不能提交或重新生成私密工作流任务。

自定义工作流执行必须提交 `workflow_id`，并将 `comfy_node` 指定为已同步的目标 ComfyUI 节点，或使用 `auto` 让调度器从已同步且在线的目标节点中选择。运行任务使用创建时保存的工作流快照。省略 `workflow_id` 时继续使用 `model_variant` 与 `execution_mode` 的原有请求方式。

`reference_mappings` 支持“槽位”绑定：把 `input` 写成 `ref_images`、`ref_videos` 或 `ref_audios` 并附加 `"slot": true`，引擎会按媒体类型和从 1 开始的 `index` 动态创建 `LoadImage`、`VHS_LoadVideo`、`LoadAudio` 节点并接到 `ref_image_N`、`ref_video_N`、`ref_audio_N` 上，因此参考素材数量不受固定节点数量限制。`result_node_id` 必须指向包含 `filename_prefix` 输入的结果节点。

服务只保存配置，不会替目标 ComfyUI 安装节点或模型；执行前先确认目标服务器已包含工作流引用的节点、模型和其他资源。通过远程互联节点执行自定义工作流前，还要在目标设备导入相同配置。工作流导入、校验和同步失败的原始报错会同时写入「实时日志」（`GET /api/v1/logs`）。

## 5. 创建生成任务

接口：

```text
POST /api/v1/generations
Content-Type: multipart/form-data
```

普通视频请求示例：

```bash
curl -X POST "$BASE_URL/api/v1/generations" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -F 'prompt=固定机位，人物持续向前行走，保持连续运动和环境声音。' \
  -F 'reference_manifest=[{"type":"image"}]' \
  -F 'references=@first-frame.png;type=image/png' \
  -F 'model_variant=fl2va-fp8' \
  -F 'execution_mode=turbo-lora' \
  -F 'comfy_node=auto' \
  -F 'width=864' \
  -F 'height=480' \
  -F 'duration=15' \
  -F 'steps=8' \
  -F 'folder_id=FOLDER_ID'
```

Music3 音频请求示例：

```bash
curl -X POST "$BASE_URL/api/v1/generations" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -F 'prompt=Mandarin synth-pop, 112 BPM, bright female vocal, analog bass, wide chorus.' \
  -F $'lyrics=[Verse]\n城市灯光落在雨里\n\n[Chorus]\n和我一起奔向清晨' \
  -F 'model_variant=music3-int8' \
  -F 'execution_mode=music3' \
  -F 'duration=60' \
  -F 'steps=30'
```

主要表单字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `prompt` | string | 生成提示词或 RunningHub 主文本字段 |
| `reference_manifest` | JSON array | 按上传顺序描述参考素材，例如 `[{"type":"image"}]` |
| `references` | file[] | 与 manifest 数量和顺序一致的上传文件 |
| `model_variant` | enum | `fl2va-fp8`、`ref2va-fp8`、`music3-int8` |
| `execution_mode` | enum | `native`、`turbo-lora`、`dual-sampling`、`h3-sa`、`vdn-h3`、`h3-nsfw`、`digital-human`、`tts`、`music3` |
| `workflow_id` | string | 可选的内置预设或自定义工作流 ID；指定后按该工作流配置执行 |
| `width`、`height` | integer | 视频分辨率；TTS 会固定为 `32 × 32` |
| `duration` | number | 视频或音频时长；数字人模式使用驱动音频实际时长 |
| `steps` | integer | 采样步数，具体范围由执行方案决定 |
| `seed` | integer | `0` 到 `2^31 - 1`，省略时由服务随机生成 |
| `title` | string | 任务显示名称，最多 120 个字符 |
| `comfy_node` | string | `auto`、节点 ID 或 `rh:RESOURCE_ID` |
| `runninghub_parameters` | JSON object | RunningHub 动态字段参数 |
| `folder_id` | string or null | 本机文件夹 ID；省略或 `null` 表示未分组 |
| `incognito` | boolean | 无痕任务；需要 `X-H3-Incognito-Code`，且不进入文件夹系统 |

参考素材类型包括 `image`、`video`、`audio`。RunningHub 工作流还可使用 `file`。上传文件的实际类型必须与 manifest 一致。RunningHub 的字段键来自节点查询结果中的 `runninghub_schema.fields`，可通过 manifest 项的 `field_key` 指定绑定字段。

执行方案与模式组合、分辨率、时长、步数和参考素材数量由服务校验。主要约束如下：

| 执行方案 | 主要约束 |
|---|---|
| 通用 | 宽高必须是 32 的倍数，且不低于 `352 × 352` |
| 通用 | 采样步数范围 `4–50` |
| `turbo-lora` | 默认视频方案，使用 8 步并根据参考素材选择 FL2VA 或 Ref2VA |
| `native` | 原生 H3 20 步基线；时长 1–15 秒 |
| `h3-sa` | 固定 8 步，时长 1–300 秒，用于高分辨率二阶段精修或长视频 |
| `vdn-h3` | 步数 8–50；8 步时使用 DMD 检查点 |
| `dual-sampling` | 仅 `ref2va-fp8`，至少一张图片参考，时长 1–15 秒 |
| `digital-human` | 固定 20 步，需 1 张人物图片 + 1 段驱动音频 |
| `tts` | 固定 `32 × 32`，时长 1–15 秒，最多 3 段音频参考 |
| `music3` | 固定 30 步，时长 1–300 秒 |
| `h3-nsfw` | 仅无痕模式（`incognito=true` + 有效授权码），仅 `ref2va-fp8` |

选型参考：需要原生 20 步基线选 `native`；需要高分辨率二阶段精修或 15 秒以上长视频选 `h3-sa`；需要 8–50 步 VDN 选 `vdn-h3`；需要双阶段采样与 Latent 3D 放大选 `dual-sampling`；输入人物图片 + 驱动音频选 `digital-human`；只要人物语音 FLAC 选 `tts`；要 Music3 音乐 FLAC 选 `music3`。

超分任务复用同一接口：提交 `task_type=upscale`，用 `upscale_category`（`real`、`anime`、`3d`）和 `upscale_scale`（`2` 或 `4`）选择模型，支持图片和视频输入，视频按源帧率合成 MP4。

8 步 LoRA 默认路径仍需执行节点健康检查、参数校验和终态轮询。不要把 8 步视频参数用于数字人、TTS、Music3、超分或 RunningHub 任务。

Agent 应先读取 `/openapi.json`，再根据目标模式构造请求，避免假设所有字段在所有模式下都有效。

远端 RunningHub 或互联推理任务可以携带本地 `folder_id`。服务只把本机代理任务归入本地文件夹，不向远端节点写入目录信息。

## 6. 查询、修改和控制任务

查询任务列表：

```bash
curl "$BASE_URL/api/v1/generations?page=1&page_size=20&status=completed&query=短剧" \
  -H "Authorization: Bearer $H3_API_KEY"
```

支持的 `status` 为 `queued`、`running`、`completed`、`failed`、`cancelled`。列表响应包含 `data`、`page`、`page_size`、`total`、`pages` 和 `store_revision`。

查询单个任务：

```bash
curl "$BASE_URL/api/v1/generations/JOB_ID" \
  -H "Authorization: Bearer $H3_API_KEY"
```

任务响应中的重要字段包括 `id`、`status`、`stage`、`progress`、`title`、`folder_id`、`request`、`created_at`、`started_at`、`updated_at`、`completed_at`、`elapsed_seconds`、`result_url`、`preview_url` 和 `references`。`elapsed_seconds` 从任务开始由推理节点处理起计算，排队等待时间不计入；排队任务的值为 `0`。排队任务可能包含 `queue_position`。

排队任务可以修改生成参数；任务开始执行后仅允许修改 `title`：

```bash
curl -X PATCH "$BASE_URL/api/v1/generations/JOB_ID" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"steps":12,"title":"新的任务名称"}'
```

取消任务：

```bash
curl -X POST "$BASE_URL/api/v1/generations/JOB_ID/cancel" \
  -H "Authorization: Bearer $H3_API_KEY"
```

只有已完成、失败或已取消的任务可以删除。删除任务会清理任务记录、参考文件、生成产物、JSON sidecar、视频封面和任务日志：

```bash
curl -X DELETE "$BASE_URL/api/v1/generations/JOB_ID" \
  -H "Authorization: Bearer $H3_API_KEY"
```

重新生成必须为每个新任务单独指定文件夹：

```bash
curl -X POST "$BASE_URL/api/v1/generations/JOB_ID/regenerate" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"folder_id":"FOLDER_ID"}'
```

`folder_id: null` 表示未分组。重新生成会复制原任务的参考文件和生成参数，并创建新的任务 ID。无痕任务不支持文件夹。

## 7. 产物与参考文件

下载已完成产物：

```bash
curl "$BASE_URL/api/v1/generations/JOB_ID/result" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -o output-file
```

读取视频首帧封面：

```bash
curl "$BASE_URL/api/v1/generations/JOB_ID/preview" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -o preview.jpg
```

封面接口对已经生成的封面使用长期缓存。视频没有封面时，服务会尝试从产物生成一次并保存到任务记录。

读取参考文件：

```bash
curl "$BASE_URL/api/v1/generations/JOB_ID/references/0" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -o reference-file
```

用户可以修改已完成产物的显示名称和文件名：

```bash
curl -X PATCH "$BASE_URL/api/v1/generations/JOB_ID/name" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"name":"第一集开场"}'
```

名称最多 120 个字符。服务会清理文件名中的路径分隔符和无效字符，同名产物返回 `409`。

`POST /api/v1/assets/delete-artifacts` 只清理已完成任务的生成产物，保留任务记录和参考文件：

```json
{"job_ids": ["JOB_ID_1", "JOB_ID_2"]}
```

## 8. 文件夹与素材库

文件夹为 SQLite 中的单层对象。文件夹名称长度为 1 至 80 个字符，同级名称按大小写折叠后判重。无痕任务不进入文件夹系统。

批量任务的标准做法：

1. `POST /api/v1/asset-folders` 创建文件夹，或复用已有同名文件夹。
2. 保存响应中的 `folder_id`。
3. 该批次每个生成请求都提交相同的 `folder_id`。
4. 重新生成时，为新任务重新指定目标文件夹。

列出文件夹和数量：

```bash
curl "$BASE_URL/api/v1/asset-folders" \
  -H "Authorization: Bearer $H3_API_KEY"
```

响应结构：

```json
{
  "data": [{"id":"folder-...","name":"第一集","count":3}],
  "unfiled": {"id":"__unfiled__","name":"未分组","count":2},
  "total": 5
}
```

创建、重命名和删除：

```bash
curl -X POST "$BASE_URL/api/v1/asset-folders" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"name":"第一集"}'

curl -X PATCH "$BASE_URL/api/v1/asset-folders/FOLDER_ID" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"name":"第一集修订"}'

curl -X DELETE "$BASE_URL/api/v1/asset-folders/FOLDER_ID" \
  -H "Authorization: Bearer $H3_API_KEY"
```

删除文件夹前，服务会检查文件夹内的所有任务。存在排队中或执行中的任务时返回 `409`，文件夹和内容保持不变。检查通过后，服务会删除文件夹内所有已结束任务的任务记录、参考文件、生成产物、封面、sidecar 和日志，最后删除文件夹。

批量移动本机任务：

```bash
curl -X POST "$BASE_URL/api/v1/asset-folders/move" \
  -H "Authorization: Bearer $H3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"job_ids":["JOB_ID_1","JOB_ID_2"],"folder_id":"FOLDER_ID"}'
```

将 `folder_id` 设置为 `null` 或 `__unfiled__` 会移入未分组。`job_ids` 必须是本机任务 ID，远端素材 ID 会被拒绝并返回 `403`。移动操作改变任务的 `folder_id`，不会复制文件。

素材库筛选：

| 请求 | 结果 |
|---|---|
| `GET /api/v1/generations?folder_id=__root__` | 本机未分组任务 |
| `GET /api/v1/generations?folder_id=__unfiled__` | 本机未分组任务 |
| `GET /api/v1/generations?folder_id=FOLDER_ID` | 指定文件夹内的本机任务 |
| `GET /api/v1/peering/library?folder_id=__root__` | 未分组的本机素材 |
| `GET /api/v1/peering/library?folder_id=FOLDER_ID` | 指定文件夹内的本机素材 |
| `GET /api/v1/peering/library` | 本机素材和授权设备的远端素材 |

省略文件夹筛选的 `/api/v1/generations` 返回本机所有普通任务。`/api/v1/peering/library` 省略筛选时还会合并远端素材。外层素材列表使用 `__root__` 读取未分类内容，分类内容需要进入对应文件夹读取。

## 9. 本地素材容量与清理

管理本地素材接口：

```bash
curl "$BASE_URL/api/v1/assets/local?page=1&page_size=24&folder_id=__root__" \
  -H "Authorization: Bearer $H3_API_KEY"
```

响应包含：

- `data`：当前筛选页的素材。
- `total`、`pages`、`page`、`page_size`：当前筛选结果分页信息。
- `total_size`：当前筛选结果大小，单位为字节。
- `library_total`、`library_total_size`：本地素材库总数量和总大小。
- `can_delete`：该素材是否允许当前服务删除。

本机创建且产物存在的素材可以删除。授权设备产生的素材、受保护的远端素材和非本机所有的文件返回 `can_delete: false`，删除请求会进入 `rejected`。服务不会删除非本机创建的文件或文件夹。

清理 30 天前视频前先获取完整预览：

```bash
curl "$BASE_URL/api/v1/assets/local/clear-old-video/preview" \
  -H "Authorization: Bearer $H3_API_KEY"
```

预览响应包含 `items`、`count`、`total_size` 和 `cutoff_days`。每个 `items` 条目包含 `asset_id`、`job_id`、`name`、`file_name`、`size`、`created_at` 和 `folder_id`。客户端应在确认前展示所有待清理文件和 `total_size`，并将字节转换为可读单位。

确认后执行：

```bash
curl -X POST "$BASE_URL/api/v1/assets/local/clear-old-video" \
  -H "Authorization: Bearer $H3_API_KEY"
```

该操作只删除本机所有者的、已完成且超过 30 天的有结果视频产物，保留任务记录和参考文件。响应包含实际删除的 `asset_id`、`count`、`total_size` 和 `cutoff_days`。

按素材 ID 删除产物：

```json
POST /api/v1/assets/local/delete
{"asset_ids":["job::JOB_ID"]}
```

响应包含 `deleted` 和 `rejected`。删除整个文件夹或任务记录属于更高范围的操作，应先在客户端显示确认信息。

## 10. 多端互联与远端素材

互联状态和授权操作：

| 方法 | 路径 | 作用 |
|---|---|---|
| `GET` | `/api/v1/peering/status` | 本机名称、互联开关、验证码和授权设备 |
| `PATCH` | `/api/v1/peering/settings` | 修改本机名称和互联开关 |
| `POST` | `/api/v1/peering/connect` | 使用一次性验证码建立授权 |
| `DELETE` | `/api/v1/peering/peers/{device_id}` | 撤销设备授权 |
| `GET` | `/api/v1/peering/library` | 合并本机和授权设备素材 |
| `GET` | `/api/v1/peering/conversations` | 合并任务流 |
| `GET` | `/api/v1/peering/runtime` | 合并日志、队列和节点 |
| `GET` | `/api/v1/peering/nodes` | 合并推理节点 |

远端素材会带有 `peer_asset: true`、`owner_name`、`owner_device_id` 和 `source`。远端素材不返回本地 `folder_id`，不接受本地文件夹移动、重命名或删除。远端任务可以通过本机代理创建，本机只保存代理任务与本地文件夹的关系。

共享素材的读取接口：

```text
GET /api/v1/peering/library/{peer_id}/assets/{job_id}
GET /api/v1/peering/library/{peer_id}/assets/{job_id}/result
GET /api/v1/peering/library/{peer_id}/assets/{job_id}/references/{index}
```

## 11. 日志和事件

查询日志、队列和节点：

```bash
curl "$BASE_URL/api/v1/logs?limit=100" \
  -H "Authorization: Bearer $H3_API_KEY"
```

实时事件使用 Server-Sent Events：

```bash
curl -N "$BASE_URL/api/v1/events?since=0" \
  -H "Authorization: Bearer $H3_API_KEY"
```

客户端应保存 `Last-Event-ID`，重连时通过请求头或 `since` 参数恢复事件。日志事件包含任务 ID、状态、阶段和时间等字段。无痕任务的敏感输入信息不会出现在公共日志中。

## 12. AI 辅助接口

提示词优化：

```text
POST /api/v1/prompts/optimize
Content-Type: application/json
```

请求字段包括 `prompt`、`base_url`、`model`、`references`、`duration`、`model_variant` 和 `execution_mode`。Music3 辅助接口为：

```text
POST /api/v1/music/assist
Content-Type: application/json
```

请求字段包括 `task`、`prompt`、`lyrics`、`duration`、`base_url` 和 `model`。`task` 为 `arrangement` 或 `lyrics`。这些接口使用用户配置的 OpenAI Chat Completions 兼容服务，服务端保存配置中的密钥，Agent 不应在日志中输出密钥。

## 13. Skill 创建规范

需要基于本服务创建 Skill 时，Agent 应执行以下步骤：

1. 读取 `{BASE_URL}/AGENT.md` 获取项目用途、权限边界、版本与默认约定。
2. 读取 `{BASE_URL}/health` 记录 `version`，并读取 `{BASE_URL}/openapi.json` 获取实际路径、参数类型、必填字段和响应结构。
3. 将 `BASE_URL` 和 `H3_API_KEY` 作为运行时配置，不把地址和密钥硬编码到 Skill 源码。
4. 封装以下最小工具：健康检查、节点选择、文件夹列表、任务创建、任务轮询、任务取消、产物下载、文件夹移动和素材列表。
5. 普通视频创建工具默认提交 `fl2va-fp8`、`turbo-lora` 和 `steps=8`；使用 Ref2VA 参考素材时切换到 `ref2va-fp8`。
6. 任务创建工具使用 multipart 上传；将 `reference_manifest` 与文件列表同时生成，确保数量和顺序一致。
7. 任务轮询工具根据 `status` 处理成功、失败和取消，遇到 `409`、`502` 时保留 `job_id` 并采用有限重试。
8. 文件夹工具只使用返回的文件夹 ID；将 `null` 或 `__unfiled__` 作为未分组目标；禁止向远端素材发起移动和删除请求。
9. 下载工具在状态为 `completed` 后再请求 `result`，需要预览时使用 `preview`，不要把预览文件当作正式产物。
10. 删除工具必须在客户端完成明确确认。清理 30 天前视频时，先请求 preview，展示完整条目和总大小，再调用执行接口。
11. 验收时使用测试节点或 fake engine 创建一个最小 8 步 LoRA 任务，完成状态轮询、产物下载、文件夹归类、重命名和清理路径验证。

### 版本一致性与 Skill 更新

Skill 学习或创建时必须记录当前服务版本，并在后续调用中检查版本是否发生变化：

1. 首次读取 `{BASE_URL}/AGENT.md` 或创建 Skill 时，调用 `GET {BASE_URL}/health`，将返回的 `version` 写入 Skill 元数据（例如 `project_version`）。
2. 每次使用 Skill 前读取当前 `/health.version`，与 Skill 中记录的 `project_version` 比较。
3. 如果版本不一致，重新读取 `{BASE_URL}/AGENT.md` 并检查内容是否更新：
   - 有更新：按新文档修改 Skill，并更新 Skill 中记录的 `project_version`。
   - 没有更新：在 Skill 中标记版本不一致（例如 `version_mismatch`），保留原 Skill 继续使用，不阻塞任务。
4. 版本号由项目维护者主动提示更新；Agent 不得自行推断、递增或提交版本号变更。
5. 版本检查只用于发现文档或接口变化，不替代 `openapi.json` 的接口校验。

推荐的 Skill 工具抽象：

```text
check_health() -> health payload
list_nodes() -> available nodes
list_folders() -> folders and counts
create_folder(name) -> folder payload
create_generation(form, files) -> job payload
wait_generation(job_id, timeout) -> terminal job payload
download_result(job_id, destination) -> local file
list_assets(folder_id, page, page_size) -> asset page
move_assets(job_ids, folder_id) -> move result
regenerate(job_id, folder_id) -> new job payload
```

Skill 应将 HTTP 响应中的 `detail` 原样转换为可诊断错误，同时保留状态码和 `job_id`。不得记录 `H3_API_KEY`、RunningHub API Key、互联设备令牌、无痕授权码或参考文件的敏感内容。

## 14. 部署和验证

服务部署目录应包含本文件、`app/`、`static/`、`workflows/` 和 `docs/`。默认服务名称为 `minimax-studio-webui.service`，ComfyUI 服务名称为 `comfyui.service`。

服务端验证命令：

```bash
systemctl --user is-active minimax-studio-webui.service
systemctl --user is-active comfyui.service
curl -fsS http://127.0.0.1:8193/health
curl -fsS http://127.0.0.1:8193/AGENT.md
curl -fsS http://127.0.0.1:8193/docs
curl -fsS http://127.0.0.1:8193/openapi.json
```

测试命令：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

部署或更新时保留服务端 `.env`、`data/`、`models/`、`vendor/`、`.venv/` 和备份目录。更新前检查服务端任务状态、磁盘容量和工作区修改，避免覆盖任务记录、用户上传文件和生成产物。

## 15. 皮肤与模块兼容规则

界面外观通过皮肤切换，皮肤属于纯展示层。开发新模块、修改界面或新增皮肤时必须遵守以下规则，确保默认皮肤与既有皮肤都不被破坏：

- 不因外观模式改变任何 API、数据结构、DOM 结构、元素顺序、可见性或交互行为。`data-skin` 只允许出现在 `<html>` 上（日间为 `default`，夜间为 `aurora`），日间模式不设置该属性；`data-theme` 记录 `light`、`dark` 或 `system`。
- 所有颜色、圆角、字体使用 `:root` 设计令牌（`--canvas`、`--surface`、`--surface-soft`、`--surface-warm`、`--fill-secondary`、`--fill-tertiary`、`--fill-quaternary`、`--ink`、`--muted`、`--quiet`、`--line`、`--line-strong`、`--accent`、`--accent-soft`、`--blue`、`--green`、`--warning`、`--danger`、`--radius`、`--text-*`、`--sans`、`--display`、`--mono`）；禁止新增写死色值或 `font-size`。Apple 风格基线位于 `static/design.css`，新组件应复用其中已有的表面、字号和控件规则。
- 文字大小只能使用 `--text-*` 令牌（micro 10 / caption 11 / small 12 / ui 13 / body 14 / lead 16 / heading-sm 20 / heading 24 / display 28 / hero 32）；需要新字号时先扩展令牌，不得写死 `font-size`。
- 旧组件仍写死颜色时，只允许在 `static/skins/skins.css` 内以 `html[data-skin="<id>"]` 前缀覆盖其装饰属性，不得修改基础规则。测试 `test_skins_are_scoped_and_selectable_from_settings` 会校验所有规则均已限定作用域。
- 皮肤资源放在 `static/skins/<id>/`，预览图固定命名 `preview.jpg`（16:10）。
- 注册新外观模式需要同时完成：`static/app.js` 的 `THEMES` 常量、`resolveThemeSkin()` 解析逻辑、`SKIN_THEME_COLORS` 主题色，以及设置「外观」面板中的 `data-theme-option` 卡片。选择结果保存在 `localStorage` 的 `h3-theme` 键，旧 `h3-skin` 会自动迁移；跟随系统模式监听 `prefers-color-scheme`。
- Canvas、WebGL、图表等无法被 CSS 换肤的绘制，必须监听 `document` 上的 `h3:themechange` 事件，读取 `event.detail.theme` / `event.detail.skin` 后重绘；`h3:skinchange` 仍会在解析后的皮肤变化时派发。初始化时使用 `currentTheme()` 与 `currentSkin()` 获取当前模式与皮肤。
- 自动化 Agent 调用 API 时不依赖皮肤，皮肤不会产生任何接口、字段或错误码差异。
- 发布前验证默认皮肤仍符合当前视觉基线；调整基础设计时同步更新 README 截图和静态资源版本号，并手动检查「极光玻璃」皮肤下的工作台、设置、工作流管理、素材库、节点管理和任务详情页面。
