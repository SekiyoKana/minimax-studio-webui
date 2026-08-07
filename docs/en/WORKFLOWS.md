# Workflow Manifest

[中文](../WORKFLOWS.md)

All files use the ComfyUI API JSON format and can be submitted directly to `/prompt`.

See the [official ComfyUI MiniMax H3 tutorial](https://docs.comfy.org/tutorials/partner-nodes/minimax/minimax-h3) for the base nodes and model directories. The API workflows in this repository add server-side dynamic parameters, job-specific output names, and Turbo LoRA nodes.

| File | Model | Mode | SHA-256 |
|---|---|---|---|
| `minimax_h3_fl2va_fp8_720p_15s_api.json` | FL2VA FP8 Scaled | Native | `b8fa94ef488d2b923e17562d79e23bde4bd997d2ec0d7ba158ece76d0b5a5b64` |
| `minimax_h3_ref2va_fp8_scaled_api.json` | Ref2VA FP8 Scaled | Native | `dcd2db8828bb631abd6ff3707d545037047815dc54743d1fab2f98ac53749561` |
| `minimax_h3_fl2va_fp8_turbo_lora_api.json` | FL2VA FP8 Scaled | Turbo LoRA | `b3c40f5db47e4a62e4ec8dd5be90603db380c68cdfb76e9f3302f40cb99f7640` |
| `minimax_h3_ref2va_fp8_turbo_lora_api.json` | Ref2VA FP8 Scaled | Turbo LoRA | `2cee435f126917ae2b693c07437b4f045e52f7ac6a4b816a6f3376460f82aca0` |
| `minimax_h3_ref2va_fp8_nsfw_lora_api.json` | Ref2VA FP8 Scaled | NaughtyTimes LoRA | `4fbdcb94d6014fedfd6af50d081feaae891ca97867f888a00673563891e9dad7` |

## Dynamic Nodes

The API updates these nodes before submission:

| Node | Parameter |
|---|---|
| `92` | Output filename prefix |
| `124` | Sampling steps |
| `129` | Random seed |
| `136` | Prompt, width, height, frame count, and reference assets |
| `137` | FL2VA first frame |
| `139` | Optional FL2VA last frame |
| `200+` | Dynamic Ref2VA image, video, and audio loader nodes |

Turbo workflows add:

| Node | Type | Configuration |
|---|---|---|
| `123` | `MiniMaxH3TurboSampler` | Dual-timeline sampler |
| `142` | `MiniMaxH3TurboLoRA` | `ckpt500`, strength 1.0 |

The optional NaughtyTimes workflow adds node `141` with type `LoraLoaderBypass`, model strength 0.5, and CLIP strength 0.0.

## Custom Nodes

The API dynamically creates `VHS_LoadVideo` nodes for Ref2VA video references, so [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) is required.

Turbo workflows require [ComfyUI-MiniMax-H3-Turbo](https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo). The deployment includes [`turbo-lowvram-device.patch`](../../patches/turbo-lowvram-device.patch) to fix the Adaln LoRA CPU and CUDA tensor-device mismatch under `--lowvram` mode.

## Parameter Limits

| Parameter | Range |
|---|---|
| Duration | 1 to 15 seconds |
| Steps | 4 to 50, default 10 |
| Width and height | Multiples of 32; shortest side at least 352 |
| FL2VA assets | 1 to 2 images |
| Ref2VA images | Up to 9 |
| Ref2VA videos | Up to 3, each 1 to 15 seconds |
| Ref2VA audio clips | Up to 3, each 1 to 15 seconds |
