# 模型清单

[English](en/MODELS.md)

结构化清单位于 [`model-manifest.json`](../model-manifest.json)。Music3 文件链接和 SHA-256 已在 2026-08-14 核对。

## 核心模型

| 文件 | 大小 | SHA-256 | ModelScope 固定版本 | Hugging Face 固定版本 |
|---|---:|---|---|---|
| `minimax_h3_fl2va_pruned_fp8_scaled.safetensors` | 20,958,205,608 | `12944c1f7791637e7de12208aef04da82bd26b95271b1b47d817364315ade993` | [下载](https://modelscope.cn/models/Comfy-Org/MiniMax-H3/resolve/76ec60097dff950063c12c76e1cd895a238f144d/diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors) | [下载](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/eb8a16107c595128b3a578f82d2ce2f75920c355/diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors) |
| `minimax_h3_ref2va_pruned_fp8_scaled.safetensors` | 20,958,205,608 | `f86f2f79ebd2d76eb8eeb46091e83982e6ff51d255747e7b16e92834b392b8e9` | [下载](https://modelscope.cn/models/Comfy-Org/MiniMax-H3/resolve/0eb85c07af38ed6e0388fcd94b196338845781d6/diffusion_models/minimax_h3_ref2va_pruned_fp8_scaled.safetensors) | [下载](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/eb8a16107c595128b3a578f82d2ce2f75920c355/diffusion_models/minimax_h3_ref2va_pruned_fp8_scaled.safetensors) |
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 15,687,142,551 | `35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6` | [下载](https://modelscope.cn/models/Comfy-Org/MiniMax-H3/resolve/160418ce87d04db418a33a0dbe904d5a2d774e3f/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) | [下载](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/eb8a16107c595128b3a578f82d2ce2f75920c355/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) |
| `minimax_h3_audio_vae_fp32.safetensors` | 605,254,808 | `8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48` | [下载](https://modelscope.cn/models/Comfy-Org/MiniMax-H3/resolve/dcdcca14e93e72d8cba0b6312771cf0779e85cc1/vae/minimax_h3_audio_vae_fp32.safetensors) | [下载](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/eb8a16107c595128b3a578f82d2ce2f75920c355/vae/minimax_h3_audio_vae_fp32.safetensors) |
| `minimax_h3_video_vae_fp16.safetensors` | 5,207,808,496 | `7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522` | [下载](https://modelscope.cn/models/Comfy-Org/MiniMax-H3/resolve/76fce18cb387285747955c88756974596c9a5bb8/vae/minimax_h3_video_vae_fp16.safetensors) | [下载](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/eb8a16107c595128b3a578f82d2ce2f75920c355/vae/minimax_h3_video_vae_fp16.safetensors) |

核心模型发布页：

1. [Comfy-Org MiniMax-H3 on ModelScope](https://modelscope.cn/models/Comfy-Org/MiniMax-H3)
2. [Comfy-Org MiniMax-H3 on Hugging Face](https://huggingface.co/Comfy-Org/MiniMax-H3)
3. [MiniMax H3 Community License Agreement](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE)

## Turbo LoRA

| 文件 | 大小 | SHA-256 | 下载 |
|---|---:|---|---|
| `minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors` | 1,956,193,000 | `08cfe946033af7d27719b964b6e0a0e50c32138daabbd6ce4137e23df6bf9980` | [Hugging Face 固定版本](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/f3d9da6dac47dcb985684ca150f02893f619a171/minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors) |
| `minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors` | 1,956,193,000 | `6a56f41ab4229c9dd845b9501bbd475ee57e112d846cf2e819d534a1ae928c5a` | [Hugging Face 固定版本](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/0eebcc7e79f9cb200927c80b8e7595265b770e34/minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors) |

作者资料：

1. [LightX2V MiniMax H3 Turbo LoRA 模型卡](https://huggingface.co/lightx2v/Minimax-h3-Turbo)
2. [ModelTC MiniMax H3 Turbo](https://github.com/ModelTC/Minimax-H3-Turbo)

当前 FL2VA 和 Ref2VA 工作流分别使用对应的 768p 8-step v1.0 LoRA，LoRA 强度为 1.0，`res_multistep` 采样器固定使用 8 步。视频偏移为 6.0，音频偏移为 3.0。

## 超分模型

远程 ComfyUI 当前检测到以下像素超分模型：

| 分类 | 2x | 4x |
|---|---|---|
| 真人 | `RealESRGAN_x2plus.pth` | `4x_foolhardy_Remacri.pth` |
| 动画 | `4x-AnimeSharp.pth`，结果缩放到 2x | `4x-AnimeSharp.pth` |
| 3D | `2xNomosUni_span_multijpg.pth` | `4x-UltraSharp.pth` |

远程模型目录还存在 `ltx-2.3-spatial-upscaler-x2-1.0.safetensors`、`ltx-2.3-spatial-upscaler-x2-1.1.safetensors` 和 `ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors`。这些文件可由 ComfyUI 的 `LatentUpscaleModelLoader` 识别，当前像素图像流使用的 `UpscaleModelLoader` 会返回 `UnsupportedModelError`。消融测试结果见 [`reports/ablation/upscale_ablation.md`](../reports/ablation/upscale_ablation.md)。

## MiniMax Music3

| 文件 | 大小 | SHA-256 | ModelScope | Hugging Face |
|---|---:|---|---|---|
| `minimax_music3_dit_int8_convrot.safetensors` | 2,502,161,682 | `d6b959633e69899f99f3a92d6741c0fe79f26958a30811e50e372ef978b24d5f` | [下载](https://modelscope.cn/models/Comfy-Org/MiniMax-Music-3/resolve/fbc3502b5d2ca0049348ee28b632f270b35e193a/diffusion_models/minimax_music3_dit_int8_convrot.safetensors) | [下载](https://huggingface.co/Comfy-Org/MiniMax-Music-3/resolve/6444666eb6edfb2c7fcab5f8b81da8b84b4b17b6/diffusion_models/minimax_music3_dit_int8_convrot.safetensors) |
| `minimax_music3_text_encoder_pruned_int8_convrot.safetensors` | 9,196,611,886 | `010b7416d2336a08c711bc22ee65849c9623069ddb7d89bec011a75699e52014` | [下载](https://modelscope.cn/models/Comfy-Org/MiniMax-Music-3/resolve/fbc3502b5d2ca0049348ee28b632f270b35e193a/text_encoders/minimax_music3_text_encoder_pruned_int8_convrot.safetensors) | [下载](https://huggingface.co/Comfy-Org/MiniMax-Music-3/resolve/6444666eb6edfb2c7fcab5f8b81da8b84b4b17b6/text_encoders/minimax_music3_text_encoder_pruned_int8_convrot.safetensors) |
| `minimax_music3_dav.safetensors` | 216,696,128 | `2a32155b769be01445fcc2a8663b910fc9e1751e18dc1c3ec528064512d9ef0c` | [下载](https://modelscope.cn/models/Comfy-Org/MiniMax-Music-3/resolve/fbc3502b5d2ca0049348ee28b632f270b35e193a/vae/minimax_music3_dav.safetensors) | [下载](https://huggingface.co/Comfy-Org/MiniMax-Music-3/resolve/6444666eb6edfb2c7fcab5f8b81da8b84b4b17b6/vae/minimax_music3_dav.safetensors) |

## 可选 NaughtyTimes LoRA

| 文件 | 大小 | SHA-256 | 作者页面 |
|---|---:|---|---|
| `NaughtyTimes-lora-MINIMAXH3.safetensors` | 2,479,265,096 | `69bf5e2158021b81d7519260ea1b6fdd66b6787211eaad3afa3375d57087effb` | [SexGod1979/NaughtyTimes_MiniMax-H3](https://huggingface.co/SexGod1979/NaughtyTimes_MiniMax-H3) |

作者页面在 2026-08-07 返回 HTTP 401，公开下载状态无法确认。安装脚本不会下载该文件。使用者需要提供自己已获授权的本地文件或下载地址，并遵守作者条款。

## 存储统计

必需模型总大小为 77,288,279,767 bytes，约 77.3 GB。包含可选 NaughtyTimes LoRA 后总大小为 79,767,544,863 bytes。
