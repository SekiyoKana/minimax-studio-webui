# 工作流清单

[English](en/WORKFLOWS.md)

所有文件均为 ComfyUI API 格式 JSON，可直接提交给 `/prompt`。

基础节点和模型目录参考 [ComfyUI MiniMax H3 官方教程](https://docs.comfy.org/tutorials/partner-nodes/minimax/minimax-h3)。本目录中的 API 工作流加入了服务端动态参数、任务编号输出和 Turbo LoRA 节点。

| 文件 | 模型 | 方案 | SHA-256 |
|---|---|---|---|
| `minimax_h3_fl2va_fp8_720p_15s_api.json` | FL2VA FP8 Scaled | 普通流 | `b8fa94ef488d2b923e17562d79e23bde4bd997d2ec0d7ba158ece76d0b5a5b64` |
| `minimax_h3_ref2va_fp8_scaled_api.json` | Ref2VA FP8 Scaled | 普通流 | `dcd2db8828bb631abd6ff3707d545037047815dc54743d1fab2f98ac53749561` |
| `minimax_h3_fl2va_fp8_turbo_lora_api.json` | FL2VA FP8 Scaled + 8-step LoRA v1.0 | `res_multistep`，8 步 | `e5ce3e5640424a8427f467ee9a27d9e30278a6f11b46193d14ec9841af92c3e0` |
| `minimax_h3_ref2va_fp8_turbo_lora_api.json` | Ref2VA FP8 Scaled + FL2VA 8-step LoRA v1.0 | `res_multistep`，8 步 | `138ea319f489b545b075196cf5ff1bc3ef73fe918d82f0a5d31e80a73a10f586` |
| `minimax_h3_ref2va_fp8_nsfw_lora_api.json` | Ref2VA FP8 Scaled | NaughtyTimes LoRA | `4fbdcb94d6014fedfd6af50d081feaae891ca97867f888a00673563891e9dad7` |
| `minimax_h3_ref2va_fp8_digital_human_api.json` | Ref2VA FP8 Scaled | 单图数字人音频驱动 | `829babe98437529714c4608185be9a63cd5db3ea09544d813a060b6e47138c06` |
| `minimax_music3_int8_api.json` | Music3 INT8 | 文本与歌词生成音乐 | `f3f3d2af89aadd9b25bd4d49628e28b13ba6e9e05e3afc551f4edd5177980fa5` |

## 动态节点

API 在提交前修改以下节点：

| 节点 | 参数 |
|---|---|
| `92` | 输出文件前缀 |
| `124` | 采样步数 |
| `129` | 随机种子 |
| `136` | 提示词、宽度、高度、帧数和参考素材 |
| `137` | FL2VA 首帧 |
| `139` | FL2VA 可选尾帧 |
| `200+` | Ref2VA 动态图片、视频和音频加载节点 |

Turbo 工作流增加：

| 节点 | 类型 | 配置 |
|---|---|---|
| `123` | `KSamplerSelect` | `res_multistep` |
| `124` | `BasicScheduler` | `simple`，8 步 |
| `142` | `LoraLoaderModelOnly` | FL2VA 8-step LoRA v1.0，模型强度 1.0 |
| `143` | `MiniMaxH3SigmaShift` | 视频偏移 12.0，音频偏移 3.0 |

可选 NaughtyTimes 工作流增加节点 `141`，类型为 `LoraLoaderBypass`，模型强度 0.5，CLIP 强度 0.0。

数字人工作流增加：

| 节点 | 类型 | 配置 |
|---|---|---|
| `137` | `LoadImage` | 单张人物参考图像 |
| `171` | `LoadAudio` | 驱动音频，同时作为 Ref2VA 音频参考 |
| `172` | `VRGDG_MiniMaxH3AudioDrive` | 将源音频编码到联合潜变量并锁定音频去噪遮罩 |
| `130` | `CreateVideo` | 使用节点 `172` 返回的原始音频合成最终视频 |

## 自定义节点

Ref2VA 视频参考由 API 动态创建 `VHS_LoadVideo` 节点，因此需要 [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)。

8-step LoRA 工作流使用 ComfyUI 内置的 LoRA 加载器和采样节点，无需 Turbo 自定义节点。Ref2VA 加速方案暂时复用 FL2VA 8-step LoRA。

数字人工作流需要附件中的 `comfyui-vrgamedevgirl`，核心节点为 `VRGDG_MiniMaxH3AudioDrive`。附件中的 `ComfyUI-SoundFlow` 已纳入云端 ComfyUI 插件环境；服务端通过 `ffprobe` 读取驱动音频时长，API 工作流不依赖 `SoundFlow_GetLength`。

Music3 使用 ComfyUI 原生节点 `MiniMaxMusic3TextEncode`、`EmptyMiniMaxMusic3LatentAudio`，以及 ComfyUI-MultiGPU 的 `CLIPLoaderMultiGPU`。文本编码器固定使用当前 ComfyUI 进程的 CUDA 设备。工作流固定 30 步、Euler 采样器、`simple` 调度器和分块音频解码，输出 FLAC。

## 参数限制

| 参数 | 范围 |
|---|---|
| 时长 | 1 至 15 秒 |
| 步数 | 普通流 4 至 50，8-step LoRA 加速固定 8 |
| 宽高 | 32 的倍数，最小边不低于 352 |
| FL2VA 素材 | 1 至 2 张图片 |
| Ref2VA 图片 | 最多 9 张 |
| Ref2VA 视频 | 最多 3 段，每段 1 至 15 秒 |
| Ref2VA 音频 | 最多 3 段，每段 1 至 15 秒 |
| 数字人素材 | 1 张人物图片和 1 段 1 至 15 秒驱动音频 |
| 数字人步数 | 固定 20 |
| Music3 时长 | 1 至 300 秒 |
| Music3 步数 | 固定 30 |
