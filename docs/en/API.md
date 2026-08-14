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

The `nodes` array reports each ComfyUI node's health, active job, and manual queue depth. `parallel_capacity` is the current number of online nodes. The service checks and keeps each node active every 60 seconds.

Use `comfy_node=auto` for automatic scheduling or provide a `nodes[].id` value to select a node manually. The default is `auto`.

## ComfyUI Node Management

Nodes and the health-check interval are stored in `data/config.db`. These changes apply to the scheduler immediately:

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

The service generates the node ID and returns it in the response `id` field.

Delete a node with `DELETE /api/v1/comfy/nodes/{node_id}`. The service rejects disabling or deleting a node that is running a job, has manually targeted queued jobs, or is the final enabled node.

## Create an FL2VA Turbo Job

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=Locked camera. A character stands beside a window while the curtain moves slightly in the breeze. The room is quiet.' \
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

## Create a Music3 Job

Use `prompt` for genre, mood, tempo, key, instrumentation, vocals, and arrangement. `lyrics` supports section tags such as `[Intro]`, `[Verse]`, `[Chorus]`, `[Bridge]`, `[Instrumental]`, and `[Outro]`.

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'prompt=Mandarin synth-pop, 112 BPM, bright female vocal, analog bass, wide chorus, polished studio mix.' \
  -F $'lyrics=[Verse]\nCity lights fall through the rain\n\n[Chorus]\nRun with me into the dawn' \
  -F 'model_variant=music3-int8' \
  -F 'execution_mode=music3' \
  -F 'duration=60' \
  -F 'steps=30'
```

Music3 accepts a maximum duration of 300 seconds and may end a song earlier. The service returns 32 kHz, 16-bit stereo FLAC.

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

## Music3 AI Arrangement and Lyrics

`/api/v1/music/assist` calls the configured OpenAI Chat Completions-compatible service. `arrangement` follows the official MiniMax Music3 `music-caption-rewriter` Skill and returns an English Structured Caption with `### Global Metadata`, `### Vocal Details`, and `### Arrangement`. Lyric lines are used only for emotional and section-directive analysis and are not reproduced. `lyrics` returns original lyrics with tags such as `[Verse]` and `[Chorus]`, ready for the Music3 `lyrics` field.

```bash
curl -N -X POST http://127.0.0.1:8193/api/v1/music/assist \
  -H 'Content-Type: application/json' \
  -d '{
    "task":"arrangement",
    "prompt":"Urban synth-pop at night, restrained female vocal, electric piano and analog synths, wider chorus",
    "lyrics":"[Verse]\nRain falls on the glass\n\n[Chorus]\nWalk with me into the dawn",
    "duration":120,
    "base_url":"https://api.openai.com/v1",
    "api_key":"YOUR_OPENAI_API_KEY",
    "model":"gpt-4.1-mini"
  }'
```

Set `task` to `lyrics` to generate original section-tagged lyrics. The API key is used for this request and is not written to job files.

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
