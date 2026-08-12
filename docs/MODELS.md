# 模型清单

[English](en/MODELS.md)

结构化清单位于 [`model-manifest.json`](../model-manifest.json)。所有固定链接和 SHA-256 已在 2026-08-12 核对。

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
| `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | 1,956,193,000 | `2339acdf19bfe123f46b971ea35d367a84adb85de43627e1eceafa5a5b2b111e` | [Hugging Face 固定版本](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/050494d5fe05bd1b1140b8565ea51dc33a5085a5/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors) |

作者资料：

1. [LightX2V MiniMax H3 Turbo LoRA 模型卡](https://huggingface.co/lightx2v/Minimax-h3-Turbo)
2. [ModelTC MiniMax H3 Turbo](https://github.com/ModelTC/Minimax-H3-Turbo)

当前工作流使用 LoRA 强度 1.0、`res_multistep` 采样器和 `MiniMaxH3SigmaShift`，步数固定为 8。Ref2VA 加速方案暂时复用该 FL2VA LoRA，直到 Ref2VA 专用版本发布。

## 可选 NaughtyTimes LoRA

| 文件 | 大小 | SHA-256 | 作者页面 |
|---|---:|---|---|
| `NaughtyTimes-lora-MINIMAXH3.safetensors` | 2,479,265,096 | `69bf5e2158021b81d7519260ea1b6fdd66b6787211eaad3afa3375d57087effb` | [SexGod1979/NaughtyTimes_MiniMax-H3](https://huggingface.co/SexGod1979/NaughtyTimes_MiniMax-H3) |

作者页面在 2026-08-07 返回 HTTP 401，公开下载状态无法确认。安装脚本不会下载该文件。使用者需要提供自己已获授权的本地文件或下载地址，并遵守作者条款。

## 存储统计

必需模型总大小为 65,372,810,071 bytes，约 65.4 GB。包含可选 NaughtyTimes LoRA 后总大小为 67,852,075,167 bytes。
