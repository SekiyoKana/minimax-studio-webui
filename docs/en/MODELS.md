# Model Manifest

[中文](../MODELS.md)

The structured manifest is stored in [`model-manifest.json`](../../model-manifest.json). Music3 URLs and SHA-256 checksums were verified on 2026-08-14.

## Core Models

| File | Size | SHA-256 | Pinned ModelScope Revision | Pinned Hugging Face Revision |
|---|---:|---|---|---|
| `minimax_h3_fl2va_pruned_fp8_scaled.safetensors` | 20,958,205,608 | `12944c1f7791637e7de12208aef04da82bd26b95271b1b47d817364315ade993` | [Download](https://modelscope.cn/models/Comfy-Org/MiniMax-H3/resolve/76ec60097dff950063c12c76e1cd895a238f144d/diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors) | [Download](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/eb8a16107c595128b3a578f82d2ce2f75920c355/diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors) |
| `minimax_h3_ref2va_pruned_fp8_scaled.safetensors` | 20,958,205,608 | `f86f2f79ebd2d76eb8eeb46091e83982e6ff51d255747e7b16e92834b392b8e9` | [Download](https://modelscope.cn/models/Comfy-Org/MiniMax-H3/resolve/0eb85c07af38ed6e0388fcd94b196338845781d6/diffusion_models/minimax_h3_ref2va_pruned_fp8_scaled.safetensors) | [Download](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/eb8a16107c595128b3a578f82d2ce2f75920c355/diffusion_models/minimax_h3_ref2va_pruned_fp8_scaled.safetensors) |
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 15,687,142,551 | `35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6` | [Download](https://modelscope.cn/models/Comfy-Org/MiniMax-H3/resolve/160418ce87d04db418a33a0dbe904d5a2d774e3f/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) | [Download](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/eb8a16107c595128b3a578f82d2ce2f75920c355/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) |
| `minimax_h3_audio_vae_fp32.safetensors` | 605,254,808 | `8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48` | [Download](https://modelscope.cn/models/Comfy-Org/MiniMax-H3/resolve/dcdcca14e93e72d8cba0b6312771cf0779e85cc1/vae/minimax_h3_audio_vae_fp32.safetensors) | [Download](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/eb8a16107c595128b3a578f82d2ce2f75920c355/vae/minimax_h3_audio_vae_fp32.safetensors) |
| `minimax_h3_video_vae_fp16.safetensors` | 5,207,808,496 | `7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522` | [Download](https://modelscope.cn/models/Comfy-Org/MiniMax-H3/resolve/76fce18cb387285747955c88756974596c9a5bb8/vae/minimax_h3_video_vae_fp16.safetensors) | [Download](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/eb8a16107c595128b3a578f82d2ce2f75920c355/vae/minimax_h3_video_vae_fp16.safetensors) |

Core model pages:

1. [Comfy-Org MiniMax-H3 on ModelScope](https://modelscope.cn/models/Comfy-Org/MiniMax-H3)
2. [Comfy-Org MiniMax-H3 on Hugging Face](https://huggingface.co/Comfy-Org/MiniMax-H3)
3. [MiniMax H3 Community License Agreement](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE)

## Turbo LoRA

| File | Size | SHA-256 | Download |
|---|---:|---|---|
| `minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors` | 1,956,193,000 | `08cfe946033af7d27719b964b6e0a0e50c32138daabbd6ce4137e23df6bf9980` | [Pinned Hugging Face revision](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/f3d9da6dac47dcb985684ca150f02893f619a171/minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors) |
| `minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors` | 1,956,193,000 | `6a56f41ab4229c9dd845b9501bbd475ee57e112d846cf2e819d534a1ae928c5a` | [Pinned Hugging Face revision](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/0eebcc7e79f9cb200927c80b8e7595265b770e34/minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors) |

Author resources:

1. [LightX2V MiniMax H3 Turbo LoRA model card](https://huggingface.co/lightx2v/Minimax-h3-Turbo)
2. [ModelTC MiniMax H3 Turbo](https://github.com/ModelTC/Minimax-H3-Turbo)

The FL2VA and Ref2VA workflows use their corresponding 768p 8-step v1.0 LoRAs. Both use LoRA strength 1.0, the `res_multistep` sampler, eight steps, video shift 6.0, and audio shift 3.0.

## MiniMax Music3

| File | Size | SHA-256 | ModelScope | Hugging Face |
|---|---:|---|---|---|
| `minimax_music3_dit_int8_convrot.safetensors` | 2,502,161,682 | `d6b959633e69899f99f3a92d6741c0fe79f26958a30811e50e372ef978b24d5f` | [Download](https://modelscope.cn/models/Comfy-Org/MiniMax-Music-3/resolve/fbc3502b5d2ca0049348ee28b632f270b35e193a/diffusion_models/minimax_music3_dit_int8_convrot.safetensors) | [Download](https://huggingface.co/Comfy-Org/MiniMax-Music-3/resolve/6444666eb6edfb2c7fcab5f8b81da8b84b4b17b6/diffusion_models/minimax_music3_dit_int8_convrot.safetensors) |
| `minimax_music3_text_encoder_pruned_int8_convrot.safetensors` | 9,196,611,886 | `010b7416d2336a08c711bc22ee65849c9623069ddb7d89bec011a75699e52014` | [Download](https://modelscope.cn/models/Comfy-Org/MiniMax-Music-3/resolve/fbc3502b5d2ca0049348ee28b632f270b35e193a/text_encoders/minimax_music3_text_encoder_pruned_int8_convrot.safetensors) | [Download](https://huggingface.co/Comfy-Org/MiniMax-Music-3/resolve/6444666eb6edfb2c7fcab5f8b81da8b84b4b17b6/text_encoders/minimax_music3_text_encoder_pruned_int8_convrot.safetensors) |
| `minimax_music3_dav.safetensors` | 216,696,128 | `2a32155b769be01445fcc2a8663b910fc9e1751e18dc1c3ec528064512d9ef0c` | [Download](https://modelscope.cn/models/Comfy-Org/MiniMax-Music-3/resolve/fbc3502b5d2ca0049348ee28b632f270b35e193a/vae/minimax_music3_dav.safetensors) | [Download](https://huggingface.co/Comfy-Org/MiniMax-Music-3/resolve/6444666eb6edfb2c7fcab5f8b81da8b84b4b17b6/vae/minimax_music3_dav.safetensors) |

## Optional NaughtyTimes LoRA

| File | Size | SHA-256 | Author Page |
|---|---:|---|---|
| `NaughtyTimes-lora-MINIMAXH3.safetensors` | 2,479,265,096 | `69bf5e2158021b81d7519260ea1b6fdd66b6787211eaad3afa3375d57087effb` | [SexGod1979/NaughtyTimes_MiniMax-H3](https://huggingface.co/SexGod1979/NaughtyTimes_MiniMax-H3) |

The author page returned HTTP 401 on 2026-08-07, so public availability could not be confirmed. The installer does not download this file. Users must supply an authorized local file or download URL and comply with the author's terms.

## Storage

Required models total 77,288,279,767 bytes, approximately 77.3 GB. Including the optional NaughtyTimes LoRA, the total is 79,767,544,863 bytes.
