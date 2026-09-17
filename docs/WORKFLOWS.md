# 工作流清单

[English](en/WORKFLOWS.md)

所有文件均为 ComfyUI API 格式 JSON，可直接提交给 `/prompt`。

基础节点和模型目录参考 [ComfyUI MiniMax H3 官方教程](https://docs.comfy.org/tutorials/partner-nodes/minimax/minimax-h3)。本目录中的 API 工作流加入了服务端动态参数、任务编号输出和 Turbo LoRA 节点。

| 文件 | 模型 | 方案 | SHA-256 |
|---|---|---|---|
| `minimax_h3_fl2va_fp8_720p_15s_api.json` | FL2VA FP8 Scaled | 普通流 | `b8fa94ef488d2b923e17562d79e23bde4bd997d2ec0d7ba158ece76d0b5a5b64` |
| `minimax_h3_ref2va_fp8_scaled_api.json` | Ref2VA FP8 Scaled | 普通流 | `dcd2db8828bb631abd6ff3707d545037047815dc54743d1fab2f98ac53749561` |
| `minimax_h3_fl2va_fp8_turbo_lora_api.json` | FL2VA FP8 Scaled + FL2VA 8-step v1.0 768p LoRA | `res_multistep`，8 步，视频偏移 6/音频偏移 3 | `5e87d9516fd32d922258c14332a00724d99223633575c5f06d778fe6177afe6c` |
| `minimax_h3_ref2va_fp8_turbo_lora_api.json` | Ref2VA FP8 Scaled + Ref2VA 8-step v1.0 768p LoRA | `res_multistep`，8 步，视频偏移 6/音频偏移 3 | `be1cc430fe8274f18a4263620d2371e34e73d38c2464590e081be64e1d3e0a51` |
| `minimax_h3_fl2va_fp8_sa_api.json` | FL2VA FP8 + FL2VA 8-step v1.0 768p LoRA + Sol-Attn + Latent 3D Upscaler | H3 SA，双阶段 8 步 | `8d6b3d4165877d1cf2046712c5f7b4ceb48d352e0dbade149a25406e7df68e6d` |
| `minimax_h3_ref2va_fp8_sa_api.json` | Ref2VA FP8 + Ref2VA 8-step v1.0 768p LoRA + Sol-Attn + Latent 3D Upscaler | H3 SA，双阶段 8 步 | `fa5930a90671514e3b468927b6d5175c80cf36106db8a8282e90b12e1e3a4121` |
| `minimax_h3_fl2va_vdn_api.json` | FL2VA FP8 + VDN-H3 Video Delta Net | VDN-H3，8–50 步自动选择 stage | `42db673ea1927d17e43e0687017f1f33765e8d5da6446c74b717141314cfaa93` |
| `minimax_h3_ref2va_vdn_api.json` | Ref2VA FP8 + VDN-H3 Video Delta Net | VDN-H3，8–50 步自动选择 stage | `937d67a67c6c5d79b23a27650442e295559251eb6e8911c8ec6aa38628328919` |
| `minimax_h3_ref2va_fp8_nsfw_lora_api.json` | Ref2VA FP8 Scaled | NaughtyTimes LoRA | `4fbdcb94d6014fedfd6af50d081feaae891ca97867f888a00673563891e9dad7` |
| `minimax_h3_ref2va_fp8_digital_human_api.json` | Ref2VA FP8 Scaled | 单图数字人音频驱动 | `829babe98437529714c4608185be9a63cd5db3ea09544d813a060b6e47138c06` |
| `minimax_music3_int8_api.json` | Music3 INT8 | 文本与歌词生成音乐 | `f3f3d2af89aadd9b25bd4d49628e28b13ba6e9e05e3afc551f4edd5177980fa5` |
| `minimax_h3_ref2va_fp8_tts_api.json` | Ref2VA FP8 Scaled | 人物音频参考与对白生成语音，音频-only | `b80991825b1e959b4dc6eb7a8714458dcc1620eedce5bc36fc96b5bf66bb65b6` |

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

TTS 工作流动态节点：

| 节点 | 参数 |
|---|---|
| `92` | FLAC 输出文件前缀 |
| `121` | `VAEDecodeAudio`，仅解码音频 |
| `124` | 采样步数 |
| `129` | 随机种子 |
| `136` | TTS 提示词、32×32 尺寸、帧数和音频参考 |
| `200+` | 动态 `LoadAudio` 参考节点 |

Turbo 工作流增加：

| 节点 | 类型 | 配置 |
|---|---|---|
| `123` | `KSamplerSelect` | `res_multistep` |
| `124` | `BasicScheduler` | `simple`，8 步 |
| `142` | `LoraLoaderModelOnly` | FL2VA 或 Ref2VA 对应的 768p 8-step v1.0 LoRA，模型强度 1.0 |
| `143` | `MiniMaxH3SigmaShift` | 视频偏移 6.0，音频偏移 3.0 |

H3 SA 工作流增加低分辨率首阶段、Latent 3D 放大和高分辨率 Sol-Attn 二阶段。首阶段尺寸按目标尺寸的约三分之二计算，二阶段尺寸使用请求尺寸。`ref2va-fp8` 的图片、视频和音频参考在首阶段动态注入，首阶段输出的联合潜变量继续传入二阶段。

H3 SA 可调参数：`sa_tau`、`sa_start_percent`、`sa_end_percent`、`sa_min_tokens`、`sa_int8_qk`、`sa_int8_pv`、`sa_sink_conditioning`、`sa_morton`、`sa_morton_curve`、`sa_dense_blocks` 和 `sa_stage2_denoise`。默认值与远端 `SolAttnPatch` 节点签名一致，`steps` 固定为 8。

VDN-H3 工作流通过 `ApplyVDNH3` 注入 Video Delta Net 混合注意力。步数控件开放 8–50 步，默认 50 步：选择 8 步时自动使用 `stage-dmd-step-250` 并启用 turbo adapter，选择 9–50 步时自动使用 `stage-b-step-2000` 并关闭 turbo adapter。两种路径均使用 `merge` 和 `stream`。VDN-H3 与 Sol-Attn 节点不叠加，检查点放置于 `ComfyUI/models/vdn/`。

可选 NaughtyTimes 工作流增加节点 `141`，类型为 `LoraLoaderBypass`，模型强度 0.5，CLIP 强度 0.0。

数字人工作流增加：

| 节点 | 类型 | 配置 |
|---|---|---|
| `137` | `LoadImage` | 单张人物参考图像 |
| `171` | `LoadAudio` | 驱动音频，同时作为 Ref2VA 音频参考 |
| `172` | `VRGDG_MiniMaxH3AudioDrive` | 将源音频编码到联合潜变量并锁定音频去噪遮罩 |
| `130` | `CreateVideo` | 使用节点 `172` 返回的原始音频合成最终视频 |

## 自定义节点

Ref2VA 视频参考由 API 动态创建 `VHS_LoadVideo` 节点，因此需要 [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)。固定版本源码包位于 [`comfyui_nodes/`](../comfyui_nodes/)。

8-step LoRA 工作流使用 ComfyUI 内置的 LoRA 加载器和采样节点，无需 Turbo 自定义节点。FL2VA 和 Ref2VA 使用各自对应的 768p 8-step v1.0 LoRA。

数字人工作流需要 `VRGDG_MiniMaxH3AudioDrive`。仓库中的最小节点包只包含该节点及上游许可说明。服务端通过 `ffprobe` 读取驱动音频时长，当前 API 工作流不依赖 ComfyUI-SoundFlow 或 `SoundFlow_GetLength`。

Music3 使用 ComfyUI 原生节点 `MiniMaxMusic3TextEncode`、`EmptyMiniMaxMusic3LatentAudio`，以及 ComfyUI-MultiGPU 的 `CLIPLoaderMultiGPU`。文本编码器固定使用当前 ComfyUI 进程的 CUDA 设备。API 任务启用强制时长模式，在目标时长前屏蔽 `<|audio_end|>`，工作流固定 30 步、Euler 采样器、`simple` 调度器和分块音频解码，输出 FLAC。

H3 TTS 使用 Ref2VA FP8、视频 VAE 和音频 VAE。服务将画面尺寸强制为 32×32，节点 `121` 仅输出音频，工作流不包含 `VAEDecode`、`CreateVideo` 或 `SaveVideo`。输出通过 `SaveAudio` 保存为 FLAC。音频参考支持 0 至 3 段，未提供音频参考时根据提示词中的人物特征生成声音，提示词优化使用六段式人物和对白描述。

## 参数限制

| 参数 | 范围 |
|---|---|
| 普通 H3、双采、8-step 时长 | 1 至 15 秒 |
| H3 SA 时长 | 1 至 300 秒，超过单段上限时自动拼接 |
| VDN-H3 时长 | 1 至 15 秒 |
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
| H3 TTS 时长 | 1 至 15 秒 |
| H3 TTS 步数 | 4 至 50 |
| H3 TTS 尺寸 | 固定 32×32，音频-only |
| H3 TTS 音频参考 | 0 至 3 段 |

H3 SA 支持 1 至 300 秒。超过单段 H3 时长上限时，服务自动按合法帧网格分段，使用固定的 22 帧音视频上下文连续生成，裁切重复帧并合并为一个 MP4。Sol-Attn 和二阶段精修参数使用服务端验证默认值。

VDN-H3 当前按单段 1 至 15 秒执行，线性分支状态覆盖长时序注意力。步数可在 8–50 之间调整，默认 50 步。8 步使用 `stage-dmd-step-250`，其余步数使用 `stage-b-step-2000`。官方检查点目录结构保持不变。
