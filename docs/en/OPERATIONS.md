# Operations

[中文](../OPERATIONS.md)

The examples below use the default installation directory, `$HOME/minimax-h3-stack`.

## Service Status

```bash
systemctl --user status comfyui.service --no-pager
systemctl --user status minimax-h3-api.service --no-pager
```

## Start, Stop, and Restart

```bash
systemctl --user start comfyui.service minimax-h3-api.service
systemctl --user stop minimax-h3-api.service comfyui.service
systemctl --user restart comfyui.service
systemctl --user restart minimax-h3-api.service
```

After changing `.env` or a systemd service file:

```bash
systemctl --user daemon-reload
systemctl --user restart comfyui.service minimax-h3-api.service
```

Inspect the queues before restarting:

```bash
curl -fsS http://127.0.0.1:8188/queue
curl -fsS http://127.0.0.1:8193/api/v1/logs
```

After ComfyUI returns a `prompt_id` or RunningHub returns a `taskId`, the API persists a remote-task checkpoint in `data/jobs/<job_id>.json`. Restarting only `minimax-h3-api.service` preserves the recorded progress and reconnects to the original node without uploading inputs or submitting the task again. Temporary query failures are retried for the interval configured by `H3_REMOTE_RECONNECT_SECONDS`.

Recovery is unavailable in these cases:

- The ComfyUI service executing the task was restarted and the task no longer exists in its queue or history.
- RunningHub deleted or invalidated the corresponding `taskId`.
- The task was submitted before this feature was deployed and its job file has no `remote_checkpoint`.

Before the first deployment of this feature, wait for existing active jobs to finish. Subsequent API-only restarts do not require ComfyUI or RunningHub jobs to finish.

## Live Logs

```bash
journalctl --user -u comfyui.service -f
journalctl --user -u minimax-h3-api.service -f
```

Most recent 200 lines:

```bash
journalctl --user -u comfyui.service -n 200 --no-pager
journalctl --user -u minimax-h3-api.service -n 200 --no-pager
```

## GPU Status

```bash
nvidia-smi
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

Change the assigned GPU:

```bash
sed -i 's/^CUDA_VISIBLE_DEVICES=.*/CUDA_VISIBLE_DEVICES=1/' \
  "$HOME/minimax-h3-stack/minimax-h3-api/.env"
systemctl --user restart comfyui.service
```

## Health Checks

```bash
curl -fsS http://127.0.0.1:8188/system_stats
curl -fsS http://127.0.0.1:8193/health
```

Run complete verification:

```bash
INSTALL_ROOT="$HOME/minimax-h3-stack" bash scripts/verify_install.sh
```

## Data Directories

| Path | Contents |
|---|---|
| `minimax-h3-api/data/config.db` | SQLite database for ComfyUI nodes and service settings |
| `minimax-h3-api/data/jobs` | Job-state JSON files |
| `minimax-h3-api/data/uploads` | User-uploaded reference assets |
| `minimax-h3-api/data/outputs` | API-managed MP4 files and parameter sidecars |
| `ComfyUI/input/minimax-h3-api` | Job inputs uploaded through the ComfyUI API |
| `ComfyUI/output/minimax-h3-api` | Node-side artifacts returned to the API over HTTP |

Uploads, job files, and artifacts for incognito jobs remain for 30 minutes after completion and are then removed by the service. The public asset library and normal conversation stream do not return these jobs.

## Backup

Back up source code and job metadata while excluding model files:

```bash
rsync -a \
  --exclude '.venv' \
  --exclude '.cache' \
  "$HOME/minimax-h3-stack/minimax-h3-api/" \
  /backup/minimax-h3-api/
```

Models can be downloaded and verified again from `model-manifest.json`.
