# 项目验证快照

[English](en/PROJECT_SNAPSHOT.md)

记录日期：2026-08-07，Asia/Shanghai。

## 固定版本

| 组件 | 版本 |
|---|---|
| Ubuntu | 22.04.5 LTS |
| NVIDIA 驱动 | 575.51.03 |
| GPU | 2×RTX 4090 24 GB，ComfyUI 使用 GPU 1 |
| Python | 3.11.10 |
| PyTorch | 2.6.0+cu124 |
| CUDA Runtime | 12.4 |
| ComfyUI | `563b98eefbe643a4cd510ee7f0b43e79880d5a3f` |
| ComfyUI Frontend | 1.48.6 |
| Turbo 节点 | `96cc1ddc001617da132dd73f31cd43666bf1d8d4` |
| VideoHelperSuite | `993082e4f2473bf4acaf06f51e33877a7eb38960` |

## 服务配置

ComfyUI 参数：

```text
--listen 0.0.0.0 --reserve-vram 8 --lowvram
CUDA_VISIBLE_DEVICES=1
```

GitHub 安装脚本默认将 ComfyUI 限制在 `127.0.0.1`，API 监听 `0.0.0.0:8193`。

## 端到端测试

| 项目 | 结果 |
|---|---|
| 模型 | MiniMax H3 FL2VA FP8 Scaled |
| 方案 | Turbo LoRA，双时间轴采样 |
| 输入 | 单张 608×352 PNG |
| 输出设置 | 608×352，5 秒，10 步 |
| 总耗时 | 98.4 秒 |
| 输出时长 | 5.167 秒 |
| 视频 | H.264，608×352，24 fps |
| 音频 | AAC，双声道 |
| 结果 | 完成 |

首次测试发现 Turbo 节点在 ComfyUI `--lowvram` 模式下发生 CPU 与 CUDA 张量设备不一致。`patches/turbo-lowvram-device.patch` 修复后，第二次测试完成。

## 自动测试

```text
20 tests passed
node --check static/app.js passed
bash syntax checks passed
five workflow JSON files passed parsing
```

## 资源观测

模型加载后观测值：

| 项目 | 数值 |
|---|---:|
| ComfyUI RSS | 49,423,828 KiB |
| API RSS | 74,864 KiB |
| GPU 1 已用显存 | 6,152 MiB，处于任务完成后的缓存状态 |
| 核心模型文件 | 64,196,466,943 bytes |

显存峰值随分辨率、时长、参考素材和解码阶段变化。任务完成后的缓存值不能作为峰值。
