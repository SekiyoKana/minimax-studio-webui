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

响应中的 `nodes` 包含各 ComfyUI 节点的在线状态、当前任务和手动队列深度。`parallel_capacity` 为当前在线节点数量。服务每 60 秒检查并保活一次节点。

创建任务时使用 `comfy_node=auto` 自动调度，或填写 `nodes[].id` 手动指定节点。未填写时默认为 `auto`。

## ComfyUI 节点管理

节点和健康检查间隔保存在 `data/config.db`。以下修改会立即应用到调度器：

```bash
curl http://127.0.0.1:8193/api/v1/comfy/nodes

curl -X POST http://127.0.0.1:8193/api/v1/comfy/nodes \
  -H 'Content-Type: application/json' \
  -d '{"name":"GPU 2","url":"http://10.0.0.12:8188"}'

curl -X PATCH http://127.0.0.1:8193/api/v1/comfy/nodes/gpu-2 \
  -H 'Content-Type: application/json' \
  -d '{"name":"GPU 2","url":"http://10.0.0.12:8188","enabled":true}'

curl -X PATCH http://127.0.0.1:8193/api/v1/comfy/settings \
  -H 'Content-Type: application/json' \
  -d '{"health_interval_seconds":60}'
```

创建节点时服务自动生成 ID，并在响应的 `id` 字段中返回。

删除节点使用 `DELETE /api/v1/comfy/nodes/{node_id}`。正在执行任务、存在定向排队任务或属于最后一个启用节点时，服务拒绝停用或删除。

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

Music3 最大时长为 300 秒，模型可能提前结束歌曲。产物格式为 32 kHz、16-bit、立体声 FLAC。

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

```bash
curl -N -X POST http://127.0.0.1:8193/api/v1/music/assist \
  -H 'Content-Type: application/json' \
  -d '{
    "task":"arrangement",
    "prompt":"中文城市流行，夜间氛围，克制的女声，合成器与电钢琴，副歌扩大声场",
    "lyrics":"[Verse]\n雨落在玻璃上\n\n[Chorus]\n和我走进天亮",
    "duration":120,
    "base_url":"https://api.openai.com/v1",
    "api_key":"YOUR_OPENAI_API_KEY",
    "model":"gpt-4.1-mini"
  }'
```

将请求中的 `task` 改为 `lyrics` 可生成原创分段歌词。API Key 仅用于本次请求，不会写入任务文件。

## OpenAI 兼容提示词优化

```bash
curl -X POST http://127.0.0.1:8193/api/v1/prompts/optimize \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"角色走进房间并说话",
    "base_url":"https://api.openai.com/v1",
    "api_key":"YOUR_OPENAI_API_KEY",
    "model":"gpt-4.1-mini",
    "duration":5,
    "model_variant":"fl2va-fp8",
    "references":[]
  }'
```

AI 服务配置保存在浏览器 `sessionStorage`，API Key 不写入服务端任务文件。
