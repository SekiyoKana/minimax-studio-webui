# 桌面应用

桌面应用使用 pywebview 打开本机 FastAPI 服务。应用只在本机保存任务、上传文件、生成结果、节点配置、AI 配置和互联授权；推理请求发送到配置的远端 ComfyUI 节点。

默认远端 ComfyUI 地址为：

```text
http://100.77.224.102:8188
```

启动时可以通过环境变量覆盖：

```bash
H3_DEFAULT_COMFY_URL=http://100.77.224.102:8188
H3_DEFAULT_COMFY_NAME="远端 ComfyUI · tapcash-llm"
H3_DESKTOP_PORT=38193
```

## 本地数据

| 系统 | 数据目录 |
|---|---|
| macOS | `~/Library/Application Support/MiniMax H3 Studio` |
| Windows | `%LOCALAPPDATA%\\MiniMax H3 Studio` |

目录中的 `data/config.db` 使用 SQLite 保存节点配置、AI 服务配置、API Key、本机名称、互联设备、持久授权和本机素材文件夹。API Key 不写入网页存储、任务 JSON 或素材文件。任务 JSON 使用可选 `folder_id` 保存本机任务的文件夹归属。

## 本地运行

```bash
python3 -m venv .venv-desktop
. .venv-desktop/bin/activate
pip install -r requirements-desktop.txt
python scripts/run_desktop.py
```

## 打包

在目标系统上构建，避免跨平台复制可执行文件：

```bash
pip install -r requirements-desktop.txt
python scripts/build_desktop.py
```

构建脚本使用 PyInstaller `onedir` 模式，并将 `static/`、`workflows/` 和 H3 Studio 图标一并打包。

macOS 输出：

```text
dist/MiniMaxH3Studio.app
dist/MiniMaxH3Studio.dmg
```

DMG 根目录包含 `MiniMaxH3Studio.app` 和 `Applications` 快捷入口。将应用拖到 `Applications` 即可安装。应用使用本地签名，首次打开时如果 macOS 显示来源确认提示，在 Finder 中右键应用并选择“打开”。

Windows 输出位于 `dist/MiniMaxH3Studio/`，入口为 `MiniMaxH3Studio.exe`。Windows 构建需要在 Windows 环境中执行。

## 多端互联

1. 在两个设备中设置不同的本机名称。
2. 打开右上角密钥图标，开启互联。
3. 将本机端口地址和当前六位验证码提供给另一台设备。
4. 另一台设备输入地址和验证码并建立互联。
5. 验证成功后，双方的素材库显示归属方标签。远端素材支持下载和作为输入。

验证码每 30 秒刷新一次。授权令牌保存在双方本机 SQLite 中，除非任一设备撤销授权，否则不需要重复验证。关闭互联后，设备拒绝新的素材导出请求；已保存的授权记录可以在互联窗口中撤销。

互联地址只接受局域网、回环地址和 Tailscale `100.64.0.0/10` 地址。桌面模式的普通 API 仅允许本机回环访问，配对、授权素材导出和撤销接口允许局域网设备访问。
