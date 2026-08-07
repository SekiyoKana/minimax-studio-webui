# 模型清单

[English](en/MODELS.md)

结构化清单位于 [`model-manifest.json`](../model-manifest.json)。所有固定链接和 SHA-256 已在 2026-08-07 核对。

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
| `minimax_h3_turbo_4step_ckpt500.safetensors` | 779,849,872 | `82d0acff583b04ad9a4238a7440b584b56094bfb7c4fdb2981f67c7a4784b62d` | [Hugging Face 固定版本](https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora/resolve/7a44622816e16032cb0b6d044d8820da39a1dfdc/minimax_h3_turbo_4step_ckpt500.safetensors) |

作者资料：

1. [MiniMax H3 Turbo LoRA 模型卡](https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora)
2. [ComfyUI MiniMax H3 Turbo 节点](https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo)

当前工作流使用 LoRA 强度 1.0 和作者提供的双时间轴采样器。步数允许 4 至 50，默认 10。作者将该版本标记为早期预览版本。

## 可选 NaughtyTimes LoRA

| 文件 | 大小 | SHA-256 | 作者页面 |
|---|---:|---|---|
| `NaughtyTimes-lora-MINIMAXH3.safetensors` | 2,479,265,096 | `69bf5e2158021b81d7519260ea1b6fdd66b6787211eaad3afa3375d57087effb` | [SexGod1979/NaughtyTimes_MiniMax-H3](https://huggingface.co/SexGod1979/NaughtyTimes_MiniMax-H3) |

作者页面在 2026-08-07 返回 HTTP 401，公开下载状态无法确认。安装脚本不会下载该文件。使用者需要提供自己已获授权的本地文件或下载地址，并遵守作者条款。

## 存储统计

必需模型总大小为 64,196,466,943 bytes，约 64.2 GB。包含可选 NaughtyTimes LoRA 后总大小为 66,675,732,039 bytes。
