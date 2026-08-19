# Workflow Manifest

[中文](../WORKFLOWS.md)

All files use the ComfyUI API JSON format and can be submitted directly to `/prompt`.

See the [official ComfyUI MiniMax H3 tutorial](https://docs.comfy.org/tutorials/partner-nodes/minimax/minimax-h3) for the base nodes and model directories. The API workflows in this repository add server-side dynamic parameters, job-specific output names, and Turbo LoRA nodes.

| File | Model | Mode | SHA-256 |
|---|---|---|---|
| `minimax_h3_fl2va_fp8_720p_15s_api.json` | FL2VA FP8 Scaled | Native | `b8fa94ef488d2b923e17562d79e23bde4bd997d2ec0d7ba158ece76d0b5a5b64` |
| `minimax_h3_ref2va_fp8_scaled_api.json` | Ref2VA FP8 Scaled | Native | `dcd2db8828bb631abd6ff3707d545037047815dc54743d1fab2f98ac53749561` |
| `minimax_h3_fl2va_fp8_turbo_lora_api.json` | FL2VA FP8 Scaled + 8-step LoRA v1.0 | `res_multistep`, 8 steps | `e5ce3e5640424a8427f467ee9a27d9e30278a6f11b46193d14ec9841af92c3e0` |
| `minimax_h3_ref2va_fp8_turbo_lora_api.json` | Ref2VA FP8 Scaled + FL2VA 8-step LoRA v1.0 | `res_multistep`, 8 steps | `138ea319f489b545b075196cf5ff1bc3ef73fe918d82f0a5d31e80a73a10f586` |
| `minimax_h3_ref2va_fp8_nsfw_lora_api.json` | Ref2VA FP8 Scaled | NaughtyTimes LoRA | `4fbdcb94d6014fedfd6af50d081feaae891ca97867f888a00673563891e9dad7` |
| `minimax_h3_ref2va_fp8_digital_human_api.json` | Ref2VA FP8 Scaled | Single-image audio-driven digital human | `829babe98437529714c4608185be9a63cd5db3ea09544d813a060b6e47138c06` |
| `minimax_music3_int8_api.json` | Music3 INT8 | Text and lyrics to music | `f3f3d2af89aadd9b25bd4d49628e28b13ba6e9e05e3afc551f4edd5177980fa5` |
| `minimax_h3_ref2va_fp8_tts_api.json` | Ref2VA FP8 Scaled | Character voice references and dialogue to audio | `b80991825b1e959b4dc6eb7a8714458dcc1620eedce5bc36fc96b5bf66bb65b6` |

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

TTS workflow dynamic nodes:

| Node | Parameter |
|---|---|
| `92` | FLAC output filename prefix |
| `121` | `VAEDecodeAudio`, audio decode only |
| `124` | Sampling steps |
| `129` | Random seed |
| `136` | TTS prompt, 32x32 size, frame count, and audio references |
| `200+` | Dynamic `LoadAudio` reference nodes |

Turbo workflows add:

| Node | Type | Configuration |
|---|---|---|
| `123` | `KSamplerSelect` | `res_multistep` |
| `124` | `BasicScheduler` | `simple`, 8 steps |
| `142` | `LoraLoaderModelOnly` | FL2VA 8-step LoRA v1.0, model strength 1.0 |
| `143` | `MiniMaxH3SigmaShift` | Video shift 12.0, audio shift 3.0 |

The optional NaughtyTimes workflow adds node `141` with type `LoraLoaderBypass`, model strength 0.5, and CLIP strength 0.0.

The digital human workflow adds:

| Node | Type | Configuration |
|---|---|---|
| `137` | `LoadImage` | One character reference image |
| `171` | `LoadAudio` | Driving audio and Ref2VA audio reference |
| `172` | `VRGDG_MiniMaxH3AudioDrive` | Encodes source audio into the joint latent and locks its denoise mask |
| `130` | `CreateVideo` | Muxes the unchanged source audio returned by node `172` |

## Custom Nodes

The API dynamically creates `VHS_LoadVideo` nodes for Ref2VA video references, so [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) is required.

The 8-step LoRA workflows use ComfyUI's built-in LoRA loader and sampling nodes, with no Turbo custom node dependency. Ref2VA acceleration temporarily reuses the FL2VA 8-step LoRA.

The digital human workflow requires the attached `comfyui-vrgamedevgirl` package for `VRGDG_MiniMaxH3AudioDrive`. The attached `ComfyUI-SoundFlow` package is installed in the cloud ComfyUI environment. The API workflow uses server-side `ffprobe` duration detection and does not depend on `SoundFlow_GetLength`.

Music3 uses ComfyUI's native `MiniMaxMusic3TextEncode` and `EmptyMiniMaxMusic3LatentAudio` nodes with ComfyUI-MultiGPU's `CLIPLoaderMultiGPU`. The text encoder is pinned to the current ComfyUI process CUDA device. API jobs enable forced-duration mode and suppress `<|audio_end|>` until the requested duration is reached. The workflow uses 30 Euler steps, the `simple` scheduler, tiled audio decoding, and FLAC output.

H3 TTS uses Ref2VA FP8 with the video and audio VAEs. The service forces the visual size to 32x32. Node `121` returns audio only, and the workflow contains no `VAEDecode`, `CreateVideo`, or `SaveVideo` node. `SaveAudio` writes FLAC output. TTS accepts zero to three audio references; without audio references, the voice is generated from the character traits in the prompt. Prompt optimization uses a six-section character and dialogue description.

## Parameter Limits

| Parameter | Range |
|---|---|
| Duration | 1 to 15 seconds |
| Steps | Native modes 4 to 50; 8-step LoRA acceleration fixed at 8 |
| Width and height | Multiples of 32; shortest side at least 352 |
| FL2VA assets | 1 to 2 images |
| Ref2VA images | Up to 9 |
| Ref2VA videos | Up to 3, each 1 to 15 seconds |
| Ref2VA audio clips | Up to 3, each 1 to 15 seconds |
| Digital human assets | 1 character image and 1 driving audio file between 1 and 15 seconds |
| Digital human steps | Fixed at 20 |
| Music3 duration | 1 to 300 seconds |
| Music3 steps | Fixed at 30 |
| H3 TTS duration | 1 to 15 seconds |
| H3 TTS steps | 4 to 50 |
| H3 TTS size | Fixed at 32x32, audio-only |
| H3 TTS audio references | 0 to 3 clips |
