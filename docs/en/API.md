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

The `nodes` array reports each inference node's provider, health, capacity, active jobs, and manual queue depth. `parallel_capacity` is the sum of all online node capacities. The service checks and keeps each node active every 60 seconds by default.

Use `comfy_node=auto` to schedule a ComfyUI task automatically or provide a `nodes[].id` value to select a node manually. For a RunningHub workflow, use `rh:<runninghub_resource_id>` to schedule across available nodes bound to the same resource ID. The default is `auto`.

## Inference Node Management

ComfyUI and RunningHub nodes and the health-check interval are stored in `data/config.db`. These changes apply to the scheduler immediately:

```bash
curl http://127.0.0.1:8193/api/v1/comfy/nodes

curl -X POST http://127.0.0.1:8193/api/v1/comfy/nodes \
  -H 'Content-Type: application/json' \
  -d '{"name":"GPU 2","url":"http://10.0.0.12:8188"}'

curl -X POST http://127.0.0.1:8193/api/v1/comfy/nodes \
  -H 'Content-Type: application/json' \
  -d '{"name":"RunningHub workflow","provider":"runninghub","api_key":"YOUR_RUNNINGHUB_API_KEY","workflow_url":"https://www.runninghub.ai/zh-cn/ai-detail/2086401261143273474","max_concurrency":2}'

curl -X PATCH http://127.0.0.1:8193/api/v1/comfy/nodes/gpu-2 \
  -H 'Content-Type: application/json' \
  -d '{"name":"GPU 2","url":"http://10.0.0.12:8188","enabled":true}'

curl -X PATCH http://127.0.0.1:8193/api/v1/comfy/settings \
  -H 'Content-Type: application/json' \
  -d '{"health_interval_seconds":60}'
```

The service generates the node ID and returns it in the response `id` field.

Node fields:

| Field | ComfyUI | RunningHub |
|---|---|---|
| `name` | Node name | Node name; the service identifies the workflow name |
| `provider` | `comfyui` | `runninghub` |
| `url` | ComfyUI HTTP API address | Optional; derived from `workflow_url` |
| `api_key` | Optional | Required |
| `workflow_url` | Ignored | Required full RunningHub workflow or AI app URL |
| `max_concurrency` | Fixed at 1 | 1 to 64, default 1 |

API keys are written only to SQLite. Node query responses include `has_api_key` and omit the secret value. Leaving `api_key` empty while editing the same provider preserves the saved key. Changing providers requires a key valid for the new provider.

RunningHub node-status refreshes call the official `accountStatus` endpoint and return `account_balance_coins`, `account_balance_money`, `account_currency`, and `account_current_tasks`. Account-query failures preserve the latest data in `account_error` and do not prevent workflow use. Workflow-query failures populate `workflow_error` and preserve the most recently identified schema. The service reads the balance before and after each task. Job records include `runninghub_billing`, while node status includes the most recent measured call cost. Concurrent calls using the same API key can cause a balance delta to include other charges from the same period.

Following the [official RunningHub API documentation](https://www.runninghub.ai/runninghub-api-doc-en/), the service resolves the resource ID and type from `workflow_url`. It reads AI app parameters through `apiCallDemo` and `webapp/detail`, and reads regular workflow API-format JSON through `getJsonApiFormat`. Node responses expose the detected name in `workflow_name` and the dynamic parameter definition in `runninghub_schema`.

### Create a RunningHub Job

The interface renders text, number, enum, switch, image, video, audio, and generic file inputs from `runninghub_schema.fields`. `prompt` maps to `runninghub_schema.primary_text_key` and may be empty when the workflow has no primary text field. Send other values as a `runninghub_parameters` JSON object keyed by each field's `key`. Upload entries may specify `field_key` in `reference_manifest`; entries without it are assigned to matching fields in order.

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations \
  -F 'comfy_node=rh:2086401261143273474' \
  -F 'prompt=Primary text input' \
  -F 'runninghub_parameters={"12.steps":8,"15.cfg":1.5}' \
  -F 'reference_manifest=[{"type":"image","field_key":"36.image"}]' \
  -F 'references=@reference.png;type=image/png'
```

Read field keys from `runninghub_schema` returned by `GET /api/v1/comfy/nodes`. RunningHub jobs do not use this service's fixed H3 model, execution-mode, resolution, duration, or step controls. With `rh:<runninghub_resource_id>`, available RunningHub nodes bound to the same resource ID share capacity. A concrete node ID performs directed execution.

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

Music3 accepts a maximum duration of 300 seconds. API jobs enable forced-duration mode, suppressing the model end token until the requested duration is reached. The service returns 32 kHz, 16-bit stereo FLAC.

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

## Regenerate

```bash
curl -X POST http://127.0.0.1:8193/api/v1/generations/JOB_ID/regenerate
```

A completed, failed, or cancelled job can be regenerated. The new job keeps the original prompt, reference files, generation parameters, seed, and node selection. Reference files are copied into the new job directory.

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
