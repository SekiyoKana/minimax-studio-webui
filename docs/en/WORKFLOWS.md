# Workflow Manifest

[中文](../WORKFLOWS.md)

All files use the ComfyUI API JSON format and can be submitted directly to `/prompt`.

At startup, the service imports the built-in workflow files into the SQLite workflow configuration table. The UI and generation API select a configuration with `workflow_id`; users can upload a ComfyUI API JSON file from the workflow manager or create one with `POST /api/v1/workflows`. Presets only expose a composer visibility toggle, while custom workflows support update, delete, download and `POST /api/v1/workflows/{workflow_id}/sync`.

Imported files must use ComfyUI API format, where each node ID maps to an object containing `class_type` and `inputs`. A ComfyUI editor UI workflow export is not sufficient. The service stores the JSON but does not install nodes or models on the target ComfyUI server. Confirm that the target server already contains every referenced custom node, model, and resource before running the workflow. A custom configuration used through a remote peer must also be imported on the target device first.

See the [official ComfyUI MiniMax H3 tutorial](https://docs.comfy.org/tutorials/partner-nodes/minimax/minimax-h3) for the base nodes and model directories. The API workflows in this repository add server-side dynamic parameters, job-specific output names, and Turbo LoRA nodes.

| File | Model | Mode | SHA-256 |
|---|---|---|---|
| `H3Studio_minimax_h3_fl2va_fp8_720p_15s_api.json` | FL2VA FP8 Scaled | Native | `b8fa94ef488d2b923e17562d79e23bde4bd997d2ec0d7ba158ece76d0b5a5b64` |
| `H3Studio_minimax_h3_ref2va_fp8_scaled_api.json` | Ref2VA FP8 Scaled | Native | `dcd2db8828bb631abd6ff3707d545037047815dc54743d1fab2f98ac53749561` |
| `H3Studio_minimax_h3_fl2va_fp8_turbo_lora_api.json` | FL2VA FP8 Scaled + FL2VA 8-step v1.1 768p LoRA | `res_multistep`, 8 steps, video shift 6 / audio shift 3 | `bce319075406e69f241135a5beba03cd5c3524515dcae8d38f7eaf1464c4f5b0` |
| `H3Studio_minimax_h3_ref2va_fp8_turbo_lora_api.json` | Ref2VA FP8 Scaled + Ref2VA 8-step v1.1 768p LoRA | `res_multistep`, 8 steps, video shift 6 / audio shift 3 | `8100999f681895992d471e2f08c2c070b7c67fbf87e40f983968b88859829dcc` |
| `H3Studio_minimax_h3_fl2va_fp8_sa_api.json` | FL2VA FP8 + FL2VA 8-step v1.1 768p LoRA + Sol-Attn + Latent 3D Upscaler | H3 SA, two 8-step stages | `a34613e039da0674afdbea382ea6a8ff5b9bb92ffd986df7459eeb95126c9e87` |
| `H3Studio_minimax_h3_ref2va_fp8_sa_api.json` | Ref2VA FP8 + Ref2VA 8-step v1.1 768p LoRA + Sol-Attn + Latent 3D Upscaler | H3 SA, two 8-step stages | `f79d53fea723eb0f4fdde03efd4c212a73d1096084172c0259cec428efaa23ef` |
| `H3Studio_minimax_h3_fl2va_vdn_api.json` | FL2VA FP8 + VDN-H3 Video Delta Net | VDN-H3, automatic stage selection for 8–50 steps | `42db673ea1927d17e43e0687017f1f33765e8d5da6446c74b717141314cfaa93` |
| `H3Studio_minimax_h3_ref2va_vdn_api.json` | Ref2VA FP8 + VDN-H3 Video Delta Net | VDN-H3, automatic stage selection for 8–50 steps | `937d67a67c6c5d79b23a27650442e295559251eb6e8911c8ec6aa38628328919` |
| `H3Studio_minimax_h3_ref2va_fp8_nsfw_lora_api.json` | Ref2VA FP8 Scaled | NaughtyTimes LoRA | `4fbdcb94d6014fedfd6af50d081feaae891ca97867f888a00673563891e9dad7` |
| `H3Studio_minimax_h3_ref2va_fp8_digital_human_api.json` | Ref2VA FP8 Scaled | Single-image audio-driven digital human | `829babe98437529714c4608185be9a63cd5db3ea09544d813a060b6e47138c06` |
| `H3Studio_minimax_music3_int8_api.json` | Music3 INT8 | Text and lyrics to music | `d3915167d6fd0077066705a48070f933705a4fa8dde51154a4ee1be23c881ed9` |
| `H3Studio_minimax_h3_ref2va_fp8_tts_api.json` | Ref2VA FP8 Scaled | Character voice references and dialogue to audio | `e5dd94e0e21e6b614ff1ba5837c8be211726793627d23dbe6b642a4d08bb7baf` |

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
| `142` | `LoraLoaderModelOnly` | Corresponding FL2VA or Ref2VA 768p 8-step v1.1 LoRA, model strength 1.0 |
| `143` | `MiniMaxH3SigmaShift` | Video shift 6.0, audio shift 3.0 |

H3 SA adds a low-resolution first H3 stage, Latent 3D upscaling, and a high-resolution Sol-Attn refinement stage. The first-stage size is approximately two thirds of the requested target, and the second stage uses the requested size. Ref2VA image, video, and audio references are injected dynamically into the first stage, then its joint latent is passed to the second stage.

H3 SA parameters are `sa_tau`, `sa_start_percent`, `sa_end_percent`, `sa_min_tokens`, `sa_int8_qk`, `sa_int8_pv`, `sa_sink_conditioning`, `sa_morton`, `sa_morton_curve`, `sa_dense_blocks`, and `sa_stage2_denoise`. The `steps` value is fixed at 8.

VDN-H3 applies the `ApplyVDNH3` Video Delta Net hybrid-attention patch. The steps control accepts 8–50 and defaults to 50: 8 steps selects `stage-dmd-step-250` with the turbo adapter, while 9–50 steps selects `stage-b-step-2000` with the turbo adapter disabled. Both paths use merged adapters and streamed branch weights. Do not combine it with Sol-Attn. Place checkpoints under `ComfyUI/models/vdn/`.

The super-resolution video flow calculates a frame budget from the target GPU's free VRAM, input resolution, and requested scale. FFmpeg splits longer videos into segments. Each segment uses `ImageUpscaleWithModelBatched` with a per-frame batch, then `VHS_VideoCombine` preserves the source frame rate and audio. The API merges completed segments into the final MP4.

The optional NaughtyTimes workflow adds node `141` with type `LoraLoaderBypass`, model strength 0.5, and CLIP strength 0.0.

The digital human workflow adds:

| Node | Type | Configuration |
|---|---|---|
| `137` | `LoadImage` | One character reference image |
| `171` | `LoadAudio` | Driving audio and Ref2VA audio reference |
| `172` | `VRGDG_MiniMaxH3AudioDrive` | Encodes source audio into the joint latent and locks its denoise mask |
| `130` | `CreateVideo` | Muxes the unchanged source audio returned by node `172` |

## Custom Nodes

The API dynamically creates `VHS_LoadVideo` nodes for Ref2VA video references, so [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) is required. A pinned source package is available under [`comfyui_nodes/`](../../comfyui_nodes/).

The 8-step LoRA workflows use ComfyUI's built-in LoRA loader and sampling nodes, with no Turbo custom node dependency. FL2VA and Ref2VA use their corresponding 768p 8-step v1.1 LoRAs.

The digital-human workflow requires `VRGDG_MiniMaxH3AudioDrive`. The minimal archive in this repository contains only that node and its upstream license notice. The service reads driving-audio duration with server-side `ffprobe`; the current API workflow does not depend on ComfyUI-SoundFlow or `SoundFlow_GetLength`.

Music3 uses ComfyUI's native `MiniMaxMusic3TextEncode` and `EmptyMiniMaxMusic3LatentAudio` nodes with ComfyUI-MultiGPU's `CLIPLoaderMultiGPU`. The text encoder is pinned to the current ComfyUI process CUDA device. API jobs enable forced-duration mode and suppress `<|audio_end|>` until the requested duration is reached. The workflow uses 30 Euler steps, the `simple` scheduler, tiled audio decoding, and FLAC output.

H3 TTS uses Ref2VA FP8 with the video and audio VAEs. The service forces the visual size to 32x32. Node `121` returns audio only, and the workflow contains no `VAEDecode`, `CreateVideo`, or `SaveVideo` node. `SaveAudio` writes FLAC output. TTS accepts zero to three audio references; without audio references, the voice is generated from the character traits in the prompt. Prompt optimization uses a six-section character and dialogue description.

## Parameter Limits

| Parameter | Range |
|---|---|
| Native H3, dual sampling, and 8-step duration | 1 to 15 seconds |
| H3 SA duration | 1 to 300 seconds; longer requests are stitched automatically |
| VDN-H3 duration | 1 to 15 seconds |
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

H3 SA accepts 1 to 300 seconds. When the requested duration exceeds one H3 segment, the service automatically splits it on the valid frame grid, carries a fixed 22-frame audiovisual context between segments, removes repeated leading frames, and merges one MP4. Sol-Attn and stage-two refinement use validated server defaults.

VDN-H3 currently accepts 1 to 15 seconds per segment. The steps value defaults to 50 and can be adjusted from 8 to 50: 8 uses `stage-dmd-step-250`, and other values use `stage-b-step-2000`. Its linear branch maintains long-range temporal state within the segment. Keep the official directory layouts unchanged.
