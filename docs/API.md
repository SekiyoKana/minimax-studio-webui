# API 请求

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

## 创建 FL2VA Turbo 任务

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=固定镜头，一名角色站在窗边，窗帘随风轻微摆动，环境安静。' \
  -F 'reference_manifest=[{"type":"image"}]' \
  -F 'references=@first-frame.png;type=image/png' \
  -F 'model_variant=fl2va-fp8' \
  -F 'execution_mode=turbo-lora' \
  -F 'width=864' \
  -F 'height=480' \
  -F 'duration=5' \
  -F 'steps=10'
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
