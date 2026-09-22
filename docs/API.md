# API 请求

[English](en/API.md)

交互文档位于 `http://SERVER_IP:8193/docs`。

设置了 `H3_API_KEY` 时，所有 `/api/v1/*` 请求需要以下请求头：

```http
Authorization: Bearer YOUR_API_KEY
```

当前网页没有服务级 API Key 输入项。对外部署可以保持 `H3_API_KEY` 为空，并在反向代理层完成身份验证。

## 健康检查

```bash
curl http://127.0.0.1:8193/health
```

响应中的 `nodes` 包含各推理节点的类型、在线状态、容量、当前任务和手动队列深度。`parallel_capacity` 为所有在线节点的容量总和。服务默认每 60 秒检查并保活一次节点。

创建 ComfyUI 任务时使用 `comfy_node=auto` 自动调度，或填写 `nodes[].id` 手动指定节点。RunningHub 工作流可以填写 `rh:<runninghub_resource_id>`，在绑定同一资源 ID 的可用节点之间自动调度。未填写时默认为 `auto`。

## 推理节点管理

ComfyUI 与 RunningHub 节点及健康检查间隔保存在 `data/config.db`。以下修改会立即应用到调度器：

```bash
curl http://127.0.0.1:8193/api/v1/comfy/nodes

curl -X POST http://127.0.0.1:8193/api/v1/comfy/nodes \
  -H 'Content-Type: application/json' \
  -d '{"name":"GPU 2","url":"http://10.0.0.12:8188"}'

curl -X POST http://127.0.0.1:8193/api/v1/comfy/nodes \
  -H 'Content-Type: application/json' \
  -d '{"name":"RunningHub 工作流","provider":"runninghub","api_key":"YOUR_RUNNINGHUB_API_KEY","workflow_url":"https://www.runninghub.ai/zh-cn/ai-detail/2086401261143273474","max_concurrency":2}'

curl -X PATCH http://127.0.0.1:8193/api/v1/comfy/nodes/gpu-2 \
  -H 'Content-Type: application/json' \
  -d '{"name":"GPU 2","url":"http://10.0.0.12:8188","enabled":true}'

curl -X PATCH http://127.0.0.1:8193/api/v1/comfy/settings \
  -H 'Content-Type: application/json' \
  -d '{"health_interval_seconds":60}'
```

创建节点时服务自动生成 ID，并在响应的 `id` 字段中返回。

节点字段：

| 字段 | ComfyUI | RunningHub |
|---|---|---|
| `name` | 节点名称 | 节点名称，工作流名称由服务自动识别 |
| `provider` | `comfyui` | `runninghub` |
| `url` | ComfyUI HTTP API 地址 | 可省略，服务根据 `workflow_url` 自动确定 |
| `api_key` | 可留空 | 必填 |
| `workflow_url` | 忽略 | 必填，RunningHub 工作流或 AI 应用完整地址 |
| `max_concurrency` | 固定为 1 | 1 至 64，默认 1 |

API Key 仅写入 SQLite。查询节点时响应包含 `has_api_key`，不包含密钥内容。编辑同类型节点时将 `api_key` 留空会保留当前密钥。切换节点类型时需要重新填写适用于新类型的密钥。

RunningHub 节点状态刷新会调用官方 `accountStatus` 接口，并返回 `account_balance_coins`、`account_balance_money`、`account_currency` 与 `account_current_tasks`。账户查询失败会保留最近一次数据并记录 `account_error`，工作流仍可正常使用。工作流信息查询失败会记录 `workflow_error`，最近一次成功识别的参数定义会保留。任务调用前后各读取一次余额，任务记录包含 `runninghub_billing`，节点状态包含最近一次调用的实际消耗。相同 API Key 存在并发调用时，余额差值可能包含同期扣费。

服务依据 [RunningHub 官方 API 文档](https://www.runninghub.ai/runninghub-api-doc-en/) 从 `workflow_url` 解析资源 ID 和类型。AI 应用通过 `apiCallDemo` 与 `webapp/detail` 读取参数，普通工作流通过 `getJsonApiFormat` 读取 API-format JSON。节点响应中的 `workflow_name` 和 `runninghub_schema` 分别包含工作流名称与动态参数定义。

### 创建 RunningHub 任务

页面会按 `runninghub_schema.fields` 动态显示文本、数值、枚举、开关、图片、视频、音频和普通文件字段。`prompt` 自动写入 `runninghub_schema.primary_text_key`；没有主文本字段时可以留空。其他参数使用字段 `key` 组成 `runninghub_parameters` JSON。上传文件可在 `reference_manifest` 中指定 `field_key`，未指定时按同类型字段顺序绑定。

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'comfy_node=rh:2086401261143273474' \
  -F 'prompt=主文本输入' \
  -F 'runninghub_parameters={"12.steps":8,"15.cfg":1.5}' \
  -F 'reference_manifest=[{"type":"image","field_key":"36.image"}]' \
  -F 'references=@reference.png;type=image/png'
```

字段键取自 `GET /api/v1/comfy/nodes` 返回的 `runninghub_schema`。RunningHub 任务不使用本服务的 H3 模型、执行方案、分辨率、时长和步数固定控件。使用 `rh:<runninghub_resource_id>` 时，绑定同一资源 ID 的可用 RunningHub 节点共享并发槽位；使用具体节点 ID 时定向执行。

删除节点使用 `DELETE /api/v1/comfy/nodes/{node_id}`。正在执行任务、存在定向排队任务或属于最后一个启用节点时，服务拒绝停用或删除。

## 创建超分任务

超分任务通过 ComfyUI 节点执行，支持图片和视频输入。服务根据分类和倍率选择模型，视频任务逐帧处理并按源帧率合成 MP4。

真人图片 2x：

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'task_type=upscale' \
  -F 'upscale_category=real' \
  -F 'upscale_scale=2' \
  -F 'reference_manifest=[{"type":"image"}]' \
  -F 'references=@input.png;type=image/png' \
  -F 'comfy_node=auto'
```

动画视频 4x：

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'task_type=upscale' \
  -F 'upscale_category=anime' \
  -F 'upscale_scale=4' \
  -F 'reference_manifest=[{"type":"video"}]' \
  -F 'references=@input.mp4;type=video/mp4' \
  -F 'comfy_node=auto'
```

`upscale_category` 可取 `real`、`anime`、`3d`。`upscale_scale` 可取 `2`、`4`。超分任务无需提示词、分辨率、时长和采样步数参数。

超分单文件上传上限为 2048 MB，可通过环境变量 `H3_MAX_UPLOAD_MB` 调整。

普通视频生成任务支持生成后自动超分。提交时使用 `auto_upscale=true`，并设置 `auto_upscale_category=real|anime|3d` 与 `auto_upscale_scale=2|4`。任务只创建一个记录，完成后直接返回超分视频。

## 创建 VDN-H3 任务

VDN-H3 支持 8–50 步，支持 FL2VA 与 Ref2VA。8 步自动使用 `stage-dmd-step-250`，9–50 步自动使用 `stage-b-step-2000`：

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=固定机位，人物持续向前行走，保持连续运动和环境声音。' \
  -F 'reference_manifest=[{"type":"image"}]' \
  -F 'references=@first-frame.png;type=image/png' \
  -F 'model_variant=fl2va-fp8' \
  -F 'execution_mode=vdn-h3' \
  -F 'width=864' \
  -F 'height=480' \
  -F 'duration=15' \
  -F 'steps=8'
```

## 创建 FL2VA Turbo 任务

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=固定镜头，一名角色站在窗边，窗帘随风轻微摆动，环境安静。' \
  -F 'reference_manifest=[{"type":"image"}]' \
  -F 'references=@first-frame.png;type=image/png' \
  -F 'model_variant=fl2va-fp8' \
  -F 'execution_mode=turbo-lora' \
  -F 'comfy_node=auto' \
  -F 'width=864' \
  -F 'height=480' \
  -F 'duration=5' \
  -F 'steps=8'
```

FL2VA 尾帧请求需要按顺序提交两张图片：

```bash
-F 'reference_manifest=[{"type":"image"},{"type":"image"}]' \
-F 'references=@first-frame.png;type=image/png' \
-F 'references=@last-frame.png;type=image/png'
```

## 创建 Ref2VA 任务

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=角色在工作室内面向镜头说话，保持参考人物外观和参考声音。' \
  -F 'reference_manifest=[{"type":"image"},{"type":"video"},{"type":"audio"}]' \
  -F 'references=@character.png;type=image/png' \
  -F 'references=@motion.mp4;type=video/mp4' \
  -F 'references=@voice.wav;type=audio/wav' \
  -F 'model_variant=ref2va-fp8' \
  -F 'execution_mode=native' \
  -F 'width=864' \
  -F 'height=480' \
  -F 'duration=5' \
  -F 'steps=20'
```

## 创建 H3 SA 任务

H3 SA 支持 `fl2va-fp8` 和 `ref2va-fp8`。`ref2va-fp8` 继续支持最多 9 张图片、3 段视频和 3 段音频参考。首阶段使用低分辨率 H3，随后进行 Latent 3D 放大和 Sol-Attn 二阶段精修。`steps` 固定为 8。

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=角色在室内缓慢转身，保持参考人物身份、服装和环境连续。' \
  -F 'reference_manifest=[{"type":"image"},{"type":"video"},{"type":"audio"}]' \
  -F 'references=@character.png;type=image/png' \
  -F 'references=@motion.mp4;type=video/mp4' \
  -F 'references=@voice.wav;type=audio/wav' \
  -F 'model_variant=ref2va-fp8' \
  -F 'execution_mode=h3-sa' \
  -F 'width=1344' \
  -F 'height=768' \
  -F 'duration=5' \
  -F 'steps=8' \
  -F 'sa_tau=1.3' \
  -F 'sa_start_percent=0.2' \
  -F 'sa_end_percent=0.9' \
  -F 'sa_min_tokens=4096' \
  -F 'sa_int8_qk=true' \
  -F 'sa_int8_pv=true' \
  -F 'sa_sink_conditioning=exact_kv_and_rows' \
  -F 'sa_morton=false' \
  -F 'sa_morton_curve=2d_frame' \
  -F 'sa_dense_blocks=0' \
  -F 'sa_stage2_denoise=0.35'
```

H3 SA 参数也可在网页的“更多设置”中调整。`sa_start_percent` 必须小于 `sa_end_percent`，`sa_dense_blocks` 使用 ComfyUI Sol-Attn 的层编号表达式。

## 创建数字人任务

数字人模式需要一张人物图片和一段 1 至 15 秒的驱动音频。服务使用驱动音频的实际时长，固定执行 20 个采样步，并将源音频直接写入最终视频。

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=人物面对镜头自然说话，固定机位，保持人物身份和服装。' \
  -F 'reference_manifest=[{"type":"image"},{"type":"audio"}]' \
  -F 'references=@character.png;type=image/png' \
  -F 'references=@speech.wav;type=audio/wav' \
  -F 'model_variant=ref2va-fp8' \
  -F 'execution_mode=digital-human' \
  -F 'width=864' \
  -F 'height=480' \
  -F 'duration=5' \
  -F 'steps=20'
```

`duration` 为兼容表单协议保留，任务参数会使用驱动音频的实际时长。

## 创建 Music3 音乐任务

`prompt` 描述曲风、情绪、速度、调式、乐器、人声与编曲。`lyrics` 支持 `[Intro]`、`[Verse]`、`[Chorus]`、`[Bridge]`、`[Instrumental]` 和 `[Outro]` 等段落标签。纯音乐可填写 `[Instrumental]`。

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=Mandarin synth-pop, 112 BPM, bright female vocal, analog bass, wide chorus, polished studio mix.' \
  -F $'lyrics=[Verse]\n城市灯光落在雨里\n\n[Chorus]\n和我一起奔向清晨' \
  -F 'model_variant=music3-int8' \
  -F 'execution_mode=music3' \
  -F 'duration=60' \
  -F 'steps=30'
```

Music3 最大时长为 300 秒。API 任务启用强制时长模式，在请求时长达到前屏蔽模型结束标记，产物长度按请求时长生成。产物格式为 32 kHz、16-bit、立体声 FLAC。

## 创建 H3 TTS 人物语音任务

TTS 模式输入人物年龄、性格、说话方式和完整对白，可上传 0 至 3 段音频作为说话者音色参考。未上传音频时，声音根据提示词中的人物特征生成。多说话者对白应在提示词中明确 `(S1)`、`(S2)`；存在音频参考时再标注对应的 `<Audio N>`。服务固定工作流尺寸为 32×32，仅输出 FLAC 音频。

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=(S1) 成年女性，语速平稳，语气克制。<d>[中文] 你好，今天我们开始录音。</d>' \
  -F 'reference_manifest=[{"type":"audio"},{"type":"audio"}]' \
  -F 'references=@speaker-1.wav;type=audio/wav' \
  -F 'references=@speaker-2.wav;type=audio/wav' \
  -F 'model_variant=ref2va-fp8' \
  -F 'execution_mode=tts' \
  -F 'duration=5' \
  -F 'steps=20'
```

`width` 和 `height` 即使在请求中提供也会被服务改为 32。TTS 时长范围为 1 至 15 秒，采样步数范围为 4 至 50。提示词优化接口传入 `execution_mode=tts` 时，返回六段式英文 H3 TTS 提示词，对白保持原始语言和原文。

## 查询任务

```bash
curl http://127.0.0.1:8193/api/v1/generations/JOB_ID
```

列表与分页：

```bash
curl 'http://127.0.0.1:8193/api/v1/generations?page=1&page_size=20&status_filter=completed'
```

## 修改排队任务

```bash
curl -X PATCH http://127.0.0.1:8193/api/v1/generations/JOB_ID \
  -H 'Content-Type: application/json' \
  -d '{"steps":12,"title":"更新后的任务名称"}'
```

任务开始执行后仅允许修改标题。

## 取消与删除

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations/JOB_ID/cancel
curl -X DELETE http://127.0.0.1:8193/api/v1/generations/JOB_ID
```

## 重新生成

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations/JOB_ID/regenerate \\
  -H 'Content-Type: application/json' \\
  -d '{"folder_id": null}'
```

原任务进入已完成、失败或已取消状态后可以重新生成。新任务保留原提示词、参考文件、生成参数、随机种子和节点选择，参考文件会复制到新任务目录。

重新生成接口接收 JSON 请求体 `{"folder_id": "folder-id"}`。`folder_id` 为 `null` 时任务进入未分组。无痕任务不支持文件夹。

## 下载产物

```bash
curl http://127.0.0.1:8193/api/v1/generations/JOB_ID/result -o result.mp4
```

## 日志与事件

当前日志和队列：

```bash
curl http://127.0.0.1:8193/api/v1/logs
```

Server-Sent Events：

```bash
curl -N http://127.0.0.1:8193/api/v1/events
```

无痕任务在公共日志中不返回任务标识、标题、提示词和参考素材信息。

## Music3 AI 编曲与写词

`/api/v1/music/assist` 使用配置的 OpenAI Chat Completions 兼容服务。`arrangement` 严格遵循 MiniMax Music3 官方 `music-caption-rewriter` Skill，返回包含 `### Global Metadata`、`### Vocal Details` 和 `### Arrangement` 的英文 Structured Caption。歌词正文仅用于情绪和段落指令分析，不会被复述。`lyrics` 返回带 `[Verse]`、`[Chorus]` 等标签的原创歌词，结果可直接放入 Music3 任务的 `lyrics` 字段。

AI 服务配置写入本机 `data/config.db`：

```bash
curl -X PATCH http://127.0.0.1:8193/api/v1/settings/ai \
  -H 'Content-Type: application/json' \
  -d '{"enabled":true,"base_url":"https://api.openai.com/v1","model":"gpt-4.1-mini","api_key":"YOUR_OPENAI_API_KEY"}'
```

```bash
curl -N -X POST http://127.0.0.1:8193/api/v1/music/assist \
  -H 'Content-Type: application/json' \
  -d '{
    "task":"arrangement",
    "prompt":"中文城市流行，夜间氛围，克制的女声，合成器与电钢琴，副歌扩大声场",
    "lyrics":"[Verse]\n雨落在玻璃上\n\n[Chorus]\n和我走进天亮",
    "duration":120,
    "base_url":"https://api.openai.com/v1",
    "model":"gpt-4.1-mini"
  }'
```

将请求中的 `task` 改为 `lyrics` 可生成原创分段歌词。提示词接口读取本机 SQLite 中已保存的 API Key。

## OpenAI 兼容提示词优化

```bash
curl -X POST http://127.0.0.1:8193/api/v1/prompts/optimize \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"角色走进房间并说话",
    "base_url":"https://api.openai.com/v1",
    "model":"gpt-4.1-mini",
    "duration":5,
    "model_variant":"fl2va-fp8",
    "references":[]
  }'
```

AI 服务配置和 API Key 保存在本机 `data/config.db`，网页端不使用 `localStorage` 或 `sessionStorage` 保存密钥。

## 多端互联

桌面模式提供以下接口：

| 方法 | 路径 | 作用 |
|---|---|---|
| `GET` | `/api/v1/peering/status` | 本机名称、互联开关、六位验证码、端口地址和已授权设备 |
| `PATCH` | `/api/v1/peering/settings` | 修改本机名称或互联开关 |
| `POST` | `/api/v1/peering/connect` | 使用一次性验证码建立持久授权 |
| `DELETE` | `/api/v1/peering/peers/{device_id}` | 撤销设备访问授权 |
| `GET` | `/api/v1/peering/library` | 返回本机和已授权设备的归属方标签素材库 |

素材文件夹接口仅管理本机任务。远端素材不返回文件夹归属，也不接受文件夹写入操作。`folder_id=__unfiled__` 查询未分组任务，省略该参数返回全部素材。

| 方法 | 路径 | 作用 |
|---|---|---|
| `GET` | `/api/v1/asset-folders` | 返回本机文件夹和任务数量 |
| `POST` | `/api/v1/asset-folders` | 创建单层文件夹 |
| `PATCH` | `/api/v1/asset-folders/{folder_id}` | 重命名文件夹 |
| `POST` | `/api/v1/asset-folders/move` | 批量移动本机任务或移入未分组 |
| `DELETE` | `/api/v1/asset-folders/{folder_id}` | 删除文件夹、任务记录和关联文件 |

互联设备通过 Bearer 令牌访问 `/api/v1/peering/export/*`。令牌只保存在双方本机 SQLite。互联地址仅允许局域网、回环和 Tailscale 地址。
