# ComfyUI 节点包

[English](#english)

本目录保存 MiniMax H3 Studio 工作流所需的固定版本节点源码。每个依赖单独打包，并提供 SHA-256 校验值。

| 压缩包 | 内容 | 安装位置 | SHA-256 |
|---|---|---|---|
| `ComfyUI-core-7fe8a61.zip` | ComfyUI 核心源码，包含工作流引用的加载、采样、MiniMax H3、Music3 和音视频节点 | 作为 ComfyUI 主目录 | `4b392b42c943f3806c89694309b9cf7c9c293ce4707c866205c41ae6cc09f4d5` |
| `ComfyUI-VideoHelperSuite-993082e.zip` | Ref2VA 视频参考使用的 `VHS_LoadVideo` | `ComfyUI/custom_nodes/` | `064ced8c704f8f847430f581044e3b510d312e29169db202e30aa1e8be2176d5` |
| `ComfyUI-MultiGPU-62f98ed.zip` | Music3 文本编码器使用的 `CLIPLoaderMultiGPU` | `ComfyUI/custom_nodes/` | `bc9332560726c56388f30eea3e29364c01bf3e767cfaf33a64d464758e193c57` |
| `comfyui-minimax-h3-audio-drive-de65ec5.zip` | 数字人工作流使用的 `VRGDG_MiniMaxH3AudioDrive` 最小节点包 | `ComfyUI/custom_nodes/` | `a316573e223e3673ad9e76afdec83680e95c0e94974c3eb9793035b163225b80` |
| `ComfyUI-YCNodes-MiniMax-H3-ba2ec50.zip` | 双采工作流使用的 `H3SigmaRefiner` 和 `MiniMaxH3ImageToVideoTail` | `ComfyUI/custom_nodes/` | `246c3862d4ae6fe46be64d7a21a018bf12ddedb1fbd9fa59b1b35d4ede864267` |
| `Comfyui_Minimax_h3_latent_Upscaler-52a48af.zip` | 双采工作流使用的 `MinimaxH3LatentUpscaler3D` | `ComfyUI/custom_nodes/` | `dba5985f49d01c3497a36b136b5ace53ee926abaee9a2a908338ff97eec26ec7` |
| `ComfyUI-SolAttn_triton-842c4ea.zip` | 双采工作流使用的 `SolAttnPatch` | `ComfyUI/custom_nodes/` | `2968e53cee05670e49d95261b308164b6cccfd375080ad713e0559c2e6f265a3` |
| `ComfyUI-VDN-H3-23470b0.zip` | VDN-H3 `ApplyVDNH3` Video Delta Net 节点 | `ComfyUI/custom_nodes/` | `0d476d7ef88686638d33b8b893757d53a907980ee07b080257f5e11b357bf306` |

安装自定义节点时，解压压缩包并将其顶层目录放入 `ComfyUI/custom_nodes/`。完成后使用运行 ComfyUI 的 Python 环境安装对应目录中的 `requirements.txt`，然后重启 ComfyUI。

VDN-H3 节点和官方 8 步检查点可使用 [`scripts/install_vdn_h3.sh`](../scripts/install_vdn_h3.sh) 安装。检查点下载自 `OpenVDN/vdn-minimax-h3`，目标目录为 `ComfyUI/models/vdn/stage-dmd-step-250/`。


> [!IMPORTANT]
> Music3 强制时长功能还需要对固定版本 ComfyUI 应用 [`patches/comfyui-music3-force-duration.patch`](../patches/comfyui-music3-force-duration.patch)。[`scripts/install.sh`](../scripts/install.sh) 会自动完成该操作。

> [!NOTE]
> `comfyui-minimax-h3-audio-drive` 从上游 `comfyui-vrgamedevgirl` 中提取工作流实际使用的单个节点，并保留上游 AGPL-3.0 许可说明。当前工作流不依赖 ComfyUI-SoundFlow。

来源、完整提交信息和各压缩包提供的节点列表见 [`manifest.json`](manifest.json)。

## English

This directory contains pinned source packages for every ComfyUI node dependency used by MiniMax H3 Studio. Each dependency is distributed separately and has a recorded SHA-256 checksum.

Extract the ComfyUI archive as the main ComfyUI installation. Extract each custom-node archive under `ComfyUI/custom_nodes/`, install any included `requirements.txt` with the Python environment that runs ComfyUI, and restart ComfyUI.

The Music3 forced-duration feature also requires [`patches/comfyui-music3-force-duration.patch`](../patches/comfyui-music3-force-duration.patch). The project installer applies this patch automatically. See [`manifest.json`](manifest.json) for upstream sources, exact commits, licenses, checksums, and the complete node list provided by each archive.
