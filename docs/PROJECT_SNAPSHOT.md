# 项目验证快照

[English](en/PROJECT_SNAPSHOT.md)

记录日期：2026-08-12，Asia/Shanghai。

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
| VideoHelperSuite | `993082e4f2473bf4acaf06f51e33877a7eb38960` |

## 服务配置

ComfyUI 参数：

```text
--listen 0.0.0.0 --reserve-vram 8 --lowvram
CUDA_VISIBLE_DEVICES=1
```

GitHub 安装脚本默认将 ComfyUI 限制在 `127.0.0.1`，API 监听 `0.0.0.0:8193`。

## 8-step LoRA 测试

| 项目 | 结果 |
|---|---|
| FL2VA 任务 | `c321687f-0c15-4f1f-b18b-cda1f3648b68` |
| FL2VA 模型 | MiniMax H3 FL2VA FP8 Scaled |
| FL2VA 配置 | `res_multistep`，8 步，LoRA 强度 1.0 |
| FL2VA 总耗时 | 1,252.447 秒 |
| FL2VA 结果 | 完成 |
| Ref2VA 任务 | `2e9c5f35-1286-4884-9ea2-1e518d875b70` |
| Ref2VA 模型 | MiniMax H3 Ref2VA FP8 Scaled |
| Ref2VA 配置 | Ref2VA 8-step v1.0 768p LoRA，强度 1.0 |
| Ref2VA 总耗时 | 93.793 秒 |
| Ref2VA 结果 | 完成 |

两条任务均使用 `simple` 调度器、视频偏移 6.0 和音频偏移 3.0，并分别使用对应的 768p 8-step v1.0 LoRA。

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
| 必需模型文件 | 65,372,810,071 bytes |

显存峰值随分辨率、时长、参考素材和解码阶段变化。任务完成后的缓存值不能作为峰值。
