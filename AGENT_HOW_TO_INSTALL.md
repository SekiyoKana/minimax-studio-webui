# Agent ComfyUI 安装指南

本文面向在云 GPU 主机上部署 MiniMax H3 Studio 工作流的 Agent。安装器只在目标主机本地安装 ComfyUI、节点、模型和工作流，不会配置本项目的 Web/API 服务。

## 安装器

交付资源 ZIP 为 `scripts/MiniMaxH3-ComfyUI-Resources.zip`，内含固定版本 ComfyUI 核心压缩包、项目节点包、工作流、模型清单、Music3 补丁和 Windows 使用的 Python 安装核心。Linux 使用 `scripts/install_minimax_comfyui.py` 与 ZIP；Windows 使用 `scripts/install_minimax_comfyui.ps1` 与 ZIP，BAT 文件可作为双击入口。PS1 从 ZIP 解出 Python 核心到临时目录运行，因此 Windows 不需要单独分发 `.py` 文件。入口脚本和资源 ZIP 留在同一目录；不需要将它们复制或移动到 ComfyUI 目录。安装脚本不从 GitHub 拉取项目资源。运行后输入目标 ComfyUI 路径；目标目录须是有效 ComfyUI 根目录（含 `main.py` 与 `comfy/`）、空目录，或其父目录存在且可写的新目录。检查通过后直接开始安装。

在云主机上，优先在 GPU 实例内运行，不能在 Agent 所在的 CPU 控制节点执行模型下载。先确认 Python 3.11、NVIDIA 驱动、磁盘空间以及云厂商对大文件下载的限制：

```bash
nvidia-smi
python3.11 --version
df -h .
```

Linux 云主机命令：

```bash
python3.11 scripts/install_minimax_comfyui.py --comfy-root /data/ComfyUI --model-profile auto --yes
```

可选模型方案：`h3-fl2va`、`h3-ref2va`、`music3`、`full` 或 `none`。`auto` 在 24 GB 级 NVIDIA GPU 上选择项目已验证的 H3 FL2VA + 8 步 LoRA；在 16 至 23 GB 显存上选择较小的 Music3 INT8；更低显存或没有 NVIDIA GPU 时只导入平台兼容的节点和工作流模板，不下载模型。模板下载对应权重后才能运行。Music3 的 16 GB 显存门槛是按权重体积估算，项目没有该显存档位的验证记录。

`full` 下载模型清单中所有 `required=true` 权重，约 79 GB；不含需要另行授权的 NaughtyTimes LoRA、VDN-H3 检查点和外部超分模型。H3 单模型方案通常约 44 GB，Music3 约 12 GB。项目已验证的 H3 最低服务器基线为一张 24 GB NVIDIA GPU、64 GB 系统内存和至少 100 GB SSD 空间。显存需求会随分辨率、时长、参考素材及解码过程变化。

## 下载源选择

运行器会对 ModelScope、Hugging Face 和 `hf-mirror.com` 的代表性权重进行 1 MiB HTTP Range 连通性与速度探测。模型下载按测得速度排序，并为每个文件尝试清单中的可用源；只有 Hugging Face 文件会映射到 HF-Mirror。下载使用 `.part` 文件续传，并在完成后按 `model-manifest.json` 的文件大小和 SHA-256 校验。检查失败时不要将该文件作为有效模型启动 ComfyUI；重新运行安装器可续传。

ZIP 内的节点包在安装前逐个检查 SHA-256，工作流也会在导入前验证固定摘要。Windows 不会导入需要 Triton 的 H3 SA 工作流；VDN-H3 需要单独下载的检查点，不会被误报成完整安装。Music3 工作流使用项目的强制时长补丁。

## Agent 执行和验收

1. 将脚本和资源 ZIP 一起放到目标 GPU 实例可访问的位置，在实例上运行脚本并传入该实例的 ComfyUI 根目录。安装器验证该目录后直接写入目标位置；已有 ComfyUI 时保留已存在的核心文件和节点目录。
2. 持续读取命令输出和退出码。完整模型下载可能持续数小时；网络中断后重跑同一命令，`.part` 文件会续传。
3. 安装后用该 ComfyUI Python 环境启动服务，默认只监听本机：

   ```bash
   /data/ComfyUI/.venv/bin/python /data/ComfyUI/main.py --listen 127.0.0.1 --port 8188
   ```

4. 等待健康检查，再验证已选工作流会用到的节点：

   ```bash
   curl -fsS http://127.0.0.1:8188/system_stats
   curl -fsS http://127.0.0.1:8188/object_info/MiniMaxH3ImageToVideo
   curl -fsS http://127.0.0.1:8188/object_info/LoraLoaderModelOnly
   ```

   H3 Ref2VA 模板还需检查 `MiniMaxH3ReferenceToVideo`、`VHS_LoadVideo`；数字人模板还需 `VRGDG_MiniMaxH3AudioDrive`。Music3 方案检查 `MiniMaxMusic3TextEncode` 与 `CLIPLoaderMultiGPU`，并确认强制时长补丁已应用。H3 SA 模板仅 Linux NVIDIA 方案导入，需检查 `SolAttnPatch`。

5. 查看 ComfyUI 启动日志中是否有自定义节点导入错误，再抽查工作流目录中的 JSON 和目标模型文件。只有在云服务商提供防火墙、认证与 TLS 时才开放 Web/API 端口；ComfyUI 的 8188 端口默认保持本机访问。

## Windows PC

在 Windows PC 上安装 Python 3.11，并将 BAT、PS1 和资源 ZIP 放在同一目录。双击 `install_minimax_comfyui.bat`，或在 PowerShell 中运行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install_minimax_comfyui.ps1`。两种入口都会要求输入目标目录；Agent 可附加 `--comfy-root "D:\ComfyUI" --model-profile auto --yes`。BAT 使用进程级 ExecutionPolicy Bypass 启动 PS1，不需要更改系统执行策略。Windows 端不安装 SolAttn/Triton SA 节点；工作流和节点按自动模型方案导入。

## Android APK 远程客户端

`android/` 和 `dist/MiniMaxStudio-android-debug.apk` 是纯远程客户端。APK 不包含 Python、ComfyUI、模型或本地部署服务，适合手机和平板。先在 GPU 云主机或局域网服务器安装并启动 MiniMax Studio API，再把服务器地址交给 APK；APK 首次启动会请求输入地址并调用 `/health` 检查，检查通过后打开远程工作台。

APK 模式固定使用 `fl2va-fp8`、`turbo-lora` 和 8 步采样，只保留这一条生成流。ComfyUI 与 RunningHub 节点必须在 Studio 服务端的“推理节点”中配置；APK 仍可选择这些远端节点，并继续使用服务端已有的多端互联、队列、素材库和任务恢复能力。内网地址可使用 `http://服务器IP:8193`，公网应使用 HTTPS 和反向代理认证。

如果 API 服务设置了 `H3_API_KEY`，在 APK 连接页填写同一 Key；应用会把认证保存在本机应用存储并同步到 WebView Cookie，使 API、SSE、视频、图片和下载请求都能通过服务端认证。未设置 `H3_API_KEY` 时保持为空即可。

Agent 云服务验收顺序：

1. 在 GPU 实例执行上面的 ComfyUI 安装器，启动 ComfyUI，并在 MiniMax Studio API 中添加 ComfyUI 或 RunningHub 节点。
2. 确认 `curl -fsS http://127.0.0.1:8193/health` 返回 `{"status":"ok"}`；外部访问时只暴露 API 服务端口，不直接开放 ComfyUI 8188。
3. 将 `dist/MiniMaxStudio-android-debug.apk` 侧载到 Android 手机或平板，输入 API 服务地址并完成检测。
4. 在 APK 中提交一条带图片参考的任务，确认节点状态、进度事件、视频结果下载和 RunningHub 工作流参数正常；再用“多端互联”检查其他 Studio 设备可见。

构建 APK 需要 JDK 17、Android SDK Platform 34 和网络可用的 Gradle 8.9：在 `android/` 目录执行 `gradlew.bat assembleDebug`，产物为 `android/app/build/outputs/apk/debug/app-debug.apk`。正式发布必须使用组织自己的签名密钥替换调试签名。

## 限制

- ZIP 已包含 ComfyUI 核心源码压缩包，首次安装仍需联网下载 PyTorch 与 Python 依赖。NVIDIA 环境使用 PyTorch 2.6.0 + CUDA 12.4；请确保驱动版本至少为 550.54.14。
- ModelScope/Hugging Face 访问可能受网络策略或模型许可影响。测速只代表开始安装时的网络情况；实际大文件下载仍可能被限速或要求账号授权。
- API 格式工作流保存至 `user/default/workflows/`，用于 ComfyUI `/prompt` API。它们不是 ComfyUI 前端画布使用的 GUI 工作流格式；有些官方桌面安装采用不同用户目录，需要在其用户目录中查找这些 API JSON 文件。
- 权重受各自模型许可证约束。部署前应确认组织和用途符合 MiniMax H3、Music3 及相关权重许可。
