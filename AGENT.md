# MiniMax H3 Studio Agent Integration Guide

本文档面向需要调用 MiniMax H3 Studio 的 AI Agent、自动化程序和 Skill 作者。部署后可以通过以下地址读取同一份文档：

```text
GET {BASE_URL}/AGENT.md
```

其中 `BASE_URL` 是服务根地址，例如 `http://SERVER_IP:8193`。接口的机器可读定义位于 `{BASE_URL}/openapi.json`，交互式文档位于 `{BASE_URL}/docs`。

## 1. 项目作用

MiniMax H3 Studio 提供统一的 Web 和 HTTP API，用于：

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

## 2. 访问与鉴权

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

## 3. Agent 调用流程

建议的最小调用流程如下：

1. 请求 `/health`，确认服务可用并读取 `nodes`、`online_nodes`、`parallel_capacity`。
2. 请求 `/api/v1/comfy/nodes`，选择可用的本机节点，或读取远端互联节点。
3. 请求 `/api/v1/asset-folders`，需要分类时创建或复用文件夹并保存返回的 `id`。
4. 使用 `multipart/form-data` 请求 `/api/v1/generations` 创建任务。
5. 保存创建响应中的 `id` 和 `status_url`，按间隔请求任务详情，直到状态为 `completed`、`failed` 或 `cancelled`。
6. `completed` 时请求 `/api/v1/generations/{job_id}/result` 下载产物，视频封面使用 `/preview`。
7. 需要整理任务时调用文件夹移动接口，需要修改显示名称时调用名称接口。

创建任务后不要因为网络超时直接重复提交。优先使用已保存的 `job_id` 查询状态，避免生成重复产物。

### 默认视频方案

Agent 创建普通视频时，默认使用 8 步 LoRA：

```text
execution_mode=turbo-lora
steps=8
```

当前项目验证中，8 步 LoRA 的处理速度最快，生成效果接近原生 H3 20 步方案。`model_variant` 根据参考素材类型选择：

| 参考素材 | `model_variant` | `execution_mode` | `steps` |
|---|---|---|---:|
| 首帧图片或首尾帧图片 | `fl2va-fp8` | `turbo-lora` | 8 |
| 多张图片、视频或音频参考 | `ref2va-fp8` | `turbo-lora` | 8 |

系列短剧、连续剧情或多场景任务应先创建一个文件夹，再将返回的 `folder_id` 传入该系列的每个生成请求。这样可以使同一短剧的任务和产物保持在同一文件夹中。

推荐流程：

1. `POST /api/v1/asset-folders` 创建短剧文件夹，或使用已有同名文件夹。
2. 保存响应中的 `folder_id`。
3. 每次调用 `/api/v1/generations` 时提交相同的 `folder_id`。
4. 重新生成时按接口要求重新选择目标文件夹。

其他方案按以下条件选择：

| 方案 | 选择条件 |
|---|---|
| `turbo-lora` | 普通视频的默认执行方案，使用 8 步并根据参考素材选择 FL2VA 或 Ref2VA |
| `native` | 需要原生 H3 20 步基线或需要完整原生采样时 |
| `h3-sa` | 需要高分辨率二阶段精修或 15 秒以上长视频时 |
| `vdn-h3` | 需要 8 至 50 步 VDN H3 时 |
| `dual-sampling` | 需要双阶段采样和 Latent 3D 放大时 |
| `digital-human` | 输入人物图片和驱动音频时 |
| `tts` | 只需要人物语音 FLAC 时 |
| `music3` | 需要 Music3 音乐 FLAC 时 |

8 步 LoRA 默认路径仍需执行节点健康检查、参数校验和终态轮询。Agent 应根据任务类型切换 `model_variant`，不要将 8 步视频参数用于数字人、TTS、Music3 或 RunningHub 任务。

## 4. 健康检查与节点

```bash
curl "$BASE_URL/health"
curl -H "Authorization: Bearer $H3_API_KEY" "$BASE_URL/api/v1/comfy/nodes"
```

`/health` 返回：

- `status`：服务状态。
- `engine`：`comfyui` 或 `fake`。
- `nodes`：节点 ID、提供方、健康状态、并发容量和任务信息。
- `online_nodes`：当前在线节点数。
- `parallel_capacity`：在线节点并发容量总和。
- `queue_depth`：服务队列深度。
- `revision`：任务存储修订号。

`/api/v1/comfy/nodes` 返回节点配置和运行状态。节点提供方为 `comfyui` 或 `runninghub`。创建和修改节点需要管理员级别的服务访问权限，RunningHub 节点还需要 `api_key` 和 `workflow_url`。查询节点时不会返回密钥内容，只返回 `has_api_key`。

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

执行方案与模式组合、分辨率、时长、步数和参考素材数量由服务校验。Agent 应先读取 `/openapi.json`，再根据目标模式构造请求，避免假设所有字段在所有模式下都有效。

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

1. 读取 `{BASE_URL}/AGENT.md` 获取项目用途、权限边界和业务规则。
2. 读取 `{BASE_URL}/openapi.json` 获取实际路径、参数类型、必填字段和响应结构。
3. 将 `BASE_URL` 和 `H3_API_KEY` 作为运行时配置，不把地址和密钥硬编码到 Skill 源码。
4. 封装以下最小工具：健康检查、节点选择、文件夹列表、任务创建、任务轮询、任务取消、产物下载、文件夹移动和素材列表。
5. 普通视频创建工具默认提交 `fl2va-fp8`、`turbo-lora` 和 `steps=8`；使用 Ref2VA 参考素材时切换到 `ref2va-fp8`。
6. 任务创建工具使用 multipart 上传；将 `reference_manifest` 与文件列表同时生成，确保数量和顺序一致。
7. 任务轮询工具根据 `status` 处理成功、失败和取消，遇到 `409`、`502` 时保留 `job_id` 并采用有限重试。
8. 文件夹工具只使用返回的文件夹 ID；将 `null` 或 `__unfiled__` 作为未分组目标；禁止向远端素材发起移动和删除请求。
9. 下载工具在状态为 `completed` 后再请求 `result`，需要预览时使用 `preview`，不要把预览文件当作正式产物。
10. 删除工具必须在客户端完成明确确认。清理 30 天前视频时，先请求 preview，展示完整条目和总大小，再调用执行接口。
11. 验收时使用测试节点或 fake engine 创建一个最小 8 步 LoRA 任务，完成状态轮询、产物下载、文件夹归类、重命名和清理路径验证。

推荐的 Skill 工具抽象：

```text
check_health() -> health payload
list_nodes() -> available nodes
list_folders() -> folders and counts
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
