# Agent 安装指南

本文档供代码 Agent 在云 GPU 服务器上安装和验证 MiniMax H3 Studio。Agent 应在用户明确授权的服务器和目录中执行命令，不应修改已有的未提交源码或覆盖已有模型文件。

## 安装目标

安装脚本会部署以下组件：

- 固定提交版本的 ComfyUI
- ComfyUI-VideoHelperSuite 和 ComfyUI-MultiGPU
- MiniMax H3 Studio API 服务
- ComfyUI 与 API 的独立 Python 虚拟环境
- 模型文件、工作流和 systemd 用户服务

仓库根目录的 [`comfyui_nodes/`](comfyui_nodes/) 保存各节点的固定版本源码包。默认安装脚本从上游仓库检出相同提交，压缩包用于离线复核或手动安装。

## 执行顺序

Agent 应按以下顺序执行：

1. 确认当前目录是 `minimax-h3-api` 仓库，并读取本文件、`README.md` 和 [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)。
2. 检查工作区是否存在用户未提交修改。不要覆盖这些修改。
3. 检查操作系统、Python、GPU、磁盘空间和安装脚本所需命令。
4. 先运行一次 `DRY_RUN=1`，向用户报告安装目录、Python、GPU、模型来源和固定提交。
5. 获得安装授权后执行安装脚本。首次安装默认会下载模型并启动服务。
6. 使用 `systemctl --user`、ComfyUI `/system_stats` 和 API `/health` 验证安装结果。
7. 报告 API 地址、配置文件、模型目录、服务状态和验证结果。不要在输出中公开无痕授权码、API Key 或其他密钥。

## 前置检查

最低运行基线：Ubuntu 22.04、Python 3.11、24 GB 级别 NVIDIA GPU、64 GB RAM、至少 100 GiB 可用磁盘空间。安装脚本还需要 `git`、`curl`、`openssl`、`aria2c`、`ffmpeg`、`patch`、`rsync`、`nvidia-smi` 和 `systemctl`。

Agent 可以先执行：

```bash
git status --short
python3.11 --version
nvidia-smi
df -h "${INSTALL_ROOT:-$HOME/minimax-h3-stack}"
for command in git curl openssl aria2c ffmpeg patch rsync nvidia-smi systemctl; do
  command -v "$command"
done
```

缺少系统命令时，在用户授权下安装 Ubuntu 软件包：

```bash
sudo apt-get update
sudo apt-get install -y git ffmpeg aria2 rsync curl openssl python3.11 python3.11-venv
```

## 计划检查

```bash
DRY_RUN=1 \
INSTALL_ROOT=/data/minimax-h3-stack \
PYTHON_BIN=python3.11 \
GPU_ID=0 \
MODEL_PROVIDER=modelscope \
bash scripts/install.sh
```

`DRY_RUN=1` 不会创建目录、下载代码、下载模型或启动服务。Agent 应检查计划输出中的安装目录和 GPU 编号是否符合用户要求。

## 标准安装

```bash
INSTALL_ROOT=/data/minimax-h3-stack \
PYTHON_BIN=python3.11 \
GPU_ID=0 \
MODEL_PROVIDER=modelscope \
bash scripts/install.sh
```

常用参数：

| 变量 | 用途 |
|---|---|
| `INSTALL_ROOT` | ComfyUI、API 和模型的根目录，默认 `$HOME/minimax-h3-stack` |
| `PYTHON_BIN` | 创建虚拟环境的 Python，要求 3.11 或更高版本 |
| `GPU_ID` | ComfyUI 使用的物理 GPU 编号 |
| `MODEL_PROVIDER` | 模型来源，支持 `modelscope` 或 `huggingface` |
| `COMFY_PORT` | ComfyUI 内部端口，默认 `8188` |
| `API_PORT` | Web 与 API 端口，默认 `8193` |
| `START_SERVICES` | 是否安装后启动服务，默认 `1` |
| `SKIP_MODELS` | 已有并已校验模型时设为 `1` |
| `INSTALL_NSFW` | 需要并已获授权时设为 `1` |
| `ENABLE_LINGER` | 是否尝试启用用户服务 linger，默认 `1` |

安装脚本会拒绝包含空格的 `INSTALL_ROOT`，会检查 GPU 显存和磁盘空间，并且不会覆盖包含未提交修改的现有 ComfyUI 目录。

## 已有模型

只有在目标 ComfyUI 模型目录已经准备完成时，Agent 才可以跳过下载：

```bash
SKIP_MODELS=1 \
INSTALL_ROOT=/data/minimax-h3-stack \
GPU_ID=0 \
bash scripts/install.sh
```

安装后必须执行模型校验：

```bash
python3 scripts/download_models.py \
  --manifest model-manifest.json \
  --comfy-root /data/minimax-h3-stack/ComfyUI \
  --verify-only
```

## 安装验证

```bash
systemctl --user is-enabled comfyui.service minimax-h3-api.service
systemctl --user is-active comfyui.service minimax-h3-api.service
curl -fsS http://127.0.0.1:8188/system_stats
curl -fsS http://127.0.0.1:8193/health
```

运行仓库测试：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

部署目录的完整检查：

```bash
INSTALL_ROOT=/data/minimax-h3-stack bash scripts/verify_install.sh
```

验证失败时，Agent 应先读取服务日志和健康接口结果，再报告具体失败步骤：

```bash
journalctl --user -u comfyui.service -n 200 --no-pager
journalctl --user -u minimax-h3-api.service -n 200 --no-pager
```

## 服务与访问

默认端口：

| 端口 | 监听地址 | 用途 |
|---|---|---|
| `8188` | `127.0.0.1` | ComfyUI 内部服务 |
| `8193` | `0.0.0.0` | Web 页面和 API |

仅向用户开放 `8193`。不要将 ComfyUI 的 `8188` 端口直接暴露到公网。公网部署还需要 TLS、身份验证和访问控制。

服务文件位置：

```text
~/.config/systemd/user/comfyui.service
~/.config/systemd/user/minimax-h3-api.service
```

退出 SSH 后仍需保持用户服务运行时，在用户明确授权后执行：

```bash
sudo loginctl enable-linger "$USER"
```

## 配置与敏感信息

API 配置文件为 `${INSTALL_ROOT}/minimax-h3-api/.env`。该文件包含无痕授权码和可选 API Key，权限必须保持为用户私有。Agent 不应在聊天输出、日志摘要或提交记录中展示这些值。

安装完成后向用户报告：

- 实际安装目录
- API 页面和文档地址
- ComfyUI 与 API 服务状态
- 模型校验结果
- 需要用户后续配置的节点或密钥

## 停止条件

遇到以下情况时停止安装并请求用户确认：

- 目标目录存在未提交修改
- 目标目录包含未知版本的 ComfyUI 或模型文件
- GPU、磁盘或 Python 版本不满足基线
- 需要删除、覆盖或迁移用户数据
- 需要公开 ComfyUI 端口或写入外部密钥
- 模型许可、NSFW LoRA 或第三方节点授权未确认
