# Project Verification Snapshot

[中文](../PROJECT_SNAPSHOT.md)

Recorded on 2026-08-07, Asia/Shanghai.

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
| Turbo node | `96cc1ddc001617da132dd73f31cd43666bf1d8d4` |
| VideoHelperSuite | `993082e4f2473bf4acaf06f51e33877a7eb38960` |

## Service Configuration

ComfyUI arguments:

```text
--listen 0.0.0.0 --reserve-vram 8 --lowvram
CUDA_VISIBLE_DEVICES=1
```

The GitHub installer restricts ComfyUI to `127.0.0.1` by default. The API listens on `0.0.0.0:8193`.

## End-to-end Test

| Item | Result |
|---|---|
| Model | MiniMax H3 FL2VA FP8 Scaled |
| Mode | Turbo LoRA with dual-timeline sampling |
| Input | One 608x352 PNG image |
| Output settings | 608x352, 5 seconds, 10 steps |
| Total elapsed time | 98.4 seconds |
| Output duration | 5.167 seconds |
| Video | H.264, 608x352, 24 fps |
| Audio | AAC, stereo |
| Result | Completed |

The first test found a CPU and CUDA tensor-device mismatch in the Turbo node under ComfyUI `--lowvram` mode. The second test completed after applying `patches/turbo-lowvram-device.patch`.

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
| Core model files | 64,196,466,943 bytes |

Peak VRAM depends on resolution, duration, reference assets, and the decoding phase. Post-completion cache usage does not represent peak usage.
