# 运行维护

[English](en/OPERATIONS.md)

以下示例使用默认安装目录 `$HOME/minimax-h3-stack`。

## 服务状态

```bash
systemctl --user status comfyui.service --no-pager
systemctl --user status minimax-h3-api.service --no-pager
```

## 启动、停止和重启

```bash
systemctl --user start comfyui.service minimax-h3-api.service
systemctl --user stop minimax-h3-api.service comfyui.service
systemctl --user restart comfyui.service
systemctl --user restart minimax-h3-api.service
```

修改 `.env` 或 systemd 服务后：

```bash
systemctl --user daemon-reload
systemctl --user restart comfyui.service minimax-h3-api.service
```

重启前检查队列：

```bash
curl -fsS http://127.0.0.1:8188/queue
curl -fsS http://127.0.0.1:8193/api/v1/logs
```

## 实时日志

```bash
journalctl --user -u comfyui.service -f
journalctl --user -u minimax-h3-api.service -f
```

最近 200 行：

```bash
journalctl --user -u comfyui.service -n 200 --no-pager
journalctl --user -u minimax-h3-api.service -n 200 --no-pager
```

## GPU 状态

```bash
nvidia-smi
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

修改使用的 GPU：

```bash
sed -i 's/^CUDA_VISIBLE_DEVICES=.*/CUDA_VISIBLE_DEVICES=1/' \
  "$HOME/minimax-h3-stack/minimax-h3-api/.env"
systemctl --user restart comfyui.service
```

## 健康检查

```bash
curl -fsS http://127.0.0.1:8188/system_stats
curl -fsS http://127.0.0.1:8193/health
```

完整验证：

```bash
INSTALL_ROOT="$HOME/minimax-h3-stack" bash scripts/verify_install.sh
```

## 数据目录

| 路径 | 内容 |
|---|---|
| `minimax-h3-api/data/config.db` | ComfyUI 节点与服务设置 SQLite 数据库 |
| `minimax-h3-api/data/jobs` | 任务状态 JSON |
| `minimax-h3-api/data/uploads` | 用户上传的参考素材 |
| `minimax-h3-api/data/outputs` | API 管理的 MP4 和参数 sidecar |
| `ComfyUI/input/minimax-h3-api` | 通过 ComfyUI API 上传的任务输入 |
| `ComfyUI/output/minimax-h3-api` | ComfyUI 生成的节点侧产物，API 通过 HTTP 回传 |

无痕任务的上传素材、任务文件和产物在结束后保留 30 分钟，随后由服务清理。公共素材库和普通对话流不会返回这些任务。

## 备份

备份源码和任务元数据时排除模型文件：

```bash
rsync -a \
  --exclude '.venv' \
  --exclude '.cache' \
  "$HOME/minimax-h3-stack/minimax-h3-api/" \
  /backup/minimax-h3-api/
```

模型可以依据 `model-manifest.json` 重新下载和校验。
