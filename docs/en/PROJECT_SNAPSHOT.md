# Project Verification Snapshot

[中文](../PROJECT_SNAPSHOT.md)

Recorded on 2026-08-12, Asia/Shanghai.

## Pinned Versions

| Component | Version |
|---|---|
| Ubuntu | 22.04.5 LTS |
| NVIDIA driver | 575.51.03 |
| GPU | 2 RTX 4090 24 GB GPUs; ComfyUI uses GPU 1 |
| Python | 3.11.10 |
| PyTorch | 2.6.0+cu124 |
| CUDA runtime | 12.4 |
| ComfyUI | `563b98eefbe643a4cd510ee7f0b43e79880d5a3f` |
| ComfyUI frontend | 1.48.6 |
| VideoHelperSuite | `993082e4f2473bf4acaf06f51e33877a7eb38960` |

## Service Configuration

ComfyUI arguments:

```text
--listen 0.0.0.0 --reserve-vram 8 --lowvram
CUDA_VISIBLE_DEVICES=1
```

The GitHub installer restricts ComfyUI to `127.0.0.1` by default. The API listens on `0.0.0.0:8193`.

## 8-step LoRA Tests

| Item | Result |
|---|---|
| FL2VA job | `c321687f-0c15-4f1f-b18b-cda1f3648b68` |
| FL2VA model | MiniMax H3 FL2VA FP8 Scaled |
| FL2VA configuration | `res_multistep`, 8 steps, LoRA strength 1.0 |
| FL2VA elapsed time | 1,252.447 seconds |
| FL2VA result | Completed |
| Ref2VA job | `2e9c5f35-1286-4884-9ea2-1e518d875b70` |
| Ref2VA model | MiniMax H3 Ref2VA FP8 Scaled |
| Ref2VA configuration | FL2VA 8-step LoRA v1.0, strength 1.0 |
| Ref2VA elapsed time | 93.793 seconds |
| Ref2VA result | Completed |

Both jobs use the `simple` scheduler, video shift 12.0, and audio shift 3.0. Ref2VA acceleration reuses the FL2VA 8-step LoRA until a dedicated LoRA is released.

## Automated Tests

```text
20 tests passed
node --check static/app.js passed
bash syntax checks passed
five workflow JSON files passed parsing
```

## Resource Observations

Observed after model loading:

| Item | Value |
|---|---:|
| ComfyUI RSS | 49,423,828 KiB |
| API RSS | 74,864 KiB |
| GPU 1 VRAM used | 6,152 MiB after job completion with cache retained |
| Required model files | 65,372,810,071 bytes |

Peak VRAM depends on resolution, duration, reference assets, and the decoding phase. Post-completion cache usage does not represent peak usage.
