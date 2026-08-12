# API Requests

[中文](../API.md)

Interactive API documentation is available at `http://SERVER_IP:8193/docs`.

When `H3_API_KEY` is set, every `/api/v1/*` request requires the following header:

```http
Authorization: Bearer YOUR_API_KEY
```

The current web interface has no service-level API-key field. Public deployments may leave `H3_API_KEY` empty and apply authentication at the reverse-proxy layer.

## Health Check

```bash
curl http://127.0.0.1:8193/health
```

## Create an FL2VA Turbo Job

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=Locked camera. A character stands beside a window while the curtain moves slightly in the breeze. The room is quiet.' \
  -F 'reference_manifest=[{"type":"image"}]' \
  -F 'references=@first-frame.png;type=image/png' \
  -F 'model_variant=fl2va-fp8' \
  -F 'execution_mode=turbo-lora' \
  -F 'width=864' \
  -F 'height=480' \
  -F 'duration=5' \
  -F 'steps=8'
```

For an FL2VA last-frame request, submit two images in order:

```bash
-F 'reference_manifest=[{"type":"image"},{"type":"image"}]' \
-F 'references=@first-frame.png;type=image/png' \
-F 'references=@last-frame.png;type=image/png'
```

## Create a Ref2VA Job

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=The character faces the camera and speaks in a studio while preserving the referenced appearance and voice.' \
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

## Create a Digital Human Job

Digital human mode requires one character image and one driving audio file between 1 and 15 seconds. The service uses the actual audio duration, runs 20 sampling steps, and writes the unchanged source audio into the final video.

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=The character speaks naturally to the camera in a locked shot while preserving identity and clothing.' \
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

`duration` remains in the form protocol for compatibility. The stored job uses the actual duration of the driving audio.

## Query Jobs

```bash
curl http://127.0.0.1:8193/api/v1/generations/JOB_ID
```

List jobs with pagination:

```bash
curl 'http://127.0.0.1:8193/api/v1/generations?page=1&page_size=20&status_filter=completed'
```

## Update a Queued Job

```bash
curl -X PATCH http://127.0.0.1:8193/api/v1/generations/JOB_ID \
  -H 'Content-Type: application/json' \
  -d '{"steps":12,"title":"Updated job title"}'
```

After execution starts, only the title can be changed.

## Cancel and Delete

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations/JOB_ID/cancel
curl -X DELETE http://127.0.0.1:8193/api/v1/generations/JOB_ID
```

## Download an Artifact

```bash
curl http://127.0.0.1:8193/api/v1/generations/JOB_ID/result -o result.mp4
```

## Logs and Events

Current logs and queue state:

```bash
curl http://127.0.0.1:8193/api/v1/logs
```

Server-Sent Events:

```bash
curl -N http://127.0.0.1:8193/api/v1/events
```

Public logs omit the job ID, title, prompt, and reference-asset information for incognito jobs.

## OpenAI-compatible Prompt Optimization

```bash
curl -X POST http://127.0.0.1:8193/api/v1/prompts/optimize \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"A character enters the room and speaks",
    "base_url":"https://api.openai.com/v1",
    "api_key":"YOUR_OPENAI_API_KEY",
    "model":"gpt-4.1-mini",
    "duration":5,
    "model_variant":"fl2va-fp8",
    "references":[]
  }'
```

AI-service settings are stored in browser `sessionStorage`. The API key is not written to server-side job files.
