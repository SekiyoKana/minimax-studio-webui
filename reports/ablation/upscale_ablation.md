# 超分模型消融报告

测试日期：2026-09-22

测试节点：远程 ComfyUI，GPU 1，NVIDIA GeForce RTX 4090，24 GiB

测试输入：256×256 固定图像，当前图像超分 API 工作流，`UpscaleModelLoader`、`ImageUpscaleWithModel`、`ImageScaleBy` 和 `SaveImage`。

`reconstruction_mae` 表示将输出缩回输入尺寸后与输入图像的平均绝对误差，数值仅用于本次固定输入的重建对照，不能单独代表通用视觉质量。

| 模型 | 原生倍率 | 状态 | 输出尺寸 | 耗时 | 重建 MAE |
|---|---:|---|---:|---:|---:|
| `RealESRGAN_x2plus.pth` | 2x | 成功 | 512×512 | 0.798 s | 6.08028 |
| `2xNomosUni_span_multijpg.pth` | 2x | 成功 | 512×512 | 0.536 s | 6.20642 |
| `4x-AnimeSharp.pth` | 4x | 成功 | 1024×1024 | 0.562 s | 2.49642 |
| `4x_foolhardy_Remacri.pth` | 4x | 成功 | 1024×1024 | 0.567 s | 2.80143 |
| `4x-UltraSharp.pth` | 4x | 成功 | 1024×1024 | 0.577 s | 1.86549 |
| `4x_NMKD-Siax_200k.pth` | 4x | 成功 | 1024×1024 | 0.566 s | 2.57545 |
| `4x-ClearRealityV1.pth` | 4x | 成功 | 1024×1024 | 0.563 s | 3.80514 |
| `ltx-2.3-spatial-upscaler-x2-1.0.safetensors` | 2x | 失败 |  | 0.524 s |  |
| `ltx-2.3-spatial-upscaler-x2-1.1.safetensors` | 2x | 失败 |  | 0.525 s |  |
| `ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors` | 2x | 失败 |  | 0.519 s |  |

## 结果

1. 现有 7 个像素超分模型可以通过当前图像和视频工作流执行。
2. `RealESRGAN_x2plus.pth` 保留为真人 2x 模型，重建误差低于 `2xNomosUni_span_multijpg.pth`。
3. `4x-AnimeSharp.pth` 保留为动画 4x 模型，2x 动画请求继续使用 4x 输出后 0.5 倍 Lanczos 缩放。
4. `4x-UltraSharp.pth` 保留为 3D 4x 模型，本次固定输入的重建误差最低。
5. LTX 模型已确认属于潜空间超分模型。当前 `UpscaleModelLoader` 使用 Spandrel 图像模型加载器，执行时返回 `spandrel.__helpers.registry.UnsupportedModelError`。这些模型需要单独的潜空间工作流，暂不纳入当前像素图像和视频流。

完整原始结果见 [`upscale_ablation.json`](upscale_ablation.json)。
