# 工作流清单

[English](en/WORKFLOWS.md)

所有文件均为 ComfyUI API 格式 JSON，可直接提交给 `/prompt`。

基础节点和模型目录参考 [ComfyUI MiniMax H3 官方教程](https://docs.comfy.org/tutorials/partner-nodes/minimax/minimax-h3)。本目录中的 API 工作流加入了服务端动态参数、任务编号输出和 Turbo LoRA 节点。

| 文件 | 模型 | 方案 | SHA-256 |
|---|---|---|---|
| `minimax_h3_fl2va_fp8_720p_15s_api.json` | FL2VA FP8 Scaled | 普通流 | `b8fa94ef488d2b923e17562d79e23bde4bd997d2ec0d7ba158ece76d0b5a5b64` |
| `minimax_h3_ref2va_fp8_scaled_api.json` | Ref2VA FP8 Scaled | 普通流 | `dcd2db8828bb631abd6ff3707d545037047815dc54743d1fab2f98ac53749561` |
| `minimax_h3_fl2va_fp8_turbo_lora_api.json` | FL2VA FP8 Scaled | Turbo LoRA | `b3c40f5db47e4a62e4ec8dd5be90603db380c68cdfb76e9f3302f40cb99f7640` |
| `minimax_h3_ref2va_fp8_turbo_lora_api.json` | Ref2VA FP8 Scaled | Turbo LoRA | `2cee435f126917ae2b693c07437b4f045e52f7ac6a4b816a6f3376460f82aca0` |
| `minimax_h3_ref2va_fp8_nsfw_lora_api.json` | Ref2VA FP8 Scaled | NaughtyTimes LoRA | `4fbdcb94d6014fedfd6af50d081feaae891ca97867f888a00673563891e9dad7` |

## 动态节点

API 在提交前修改以下节点：

| 节点 | 参数 |
|---|---|
| `92` | 输出文件前缀 |
| `124` | 采样步数 |
| `129` | 随机种子 |
| `136` | 提示词、宽度、高度、帧数和参考素材 |
| `137` | FL2VA 首帧 |
| `139` | FL2VA 可选尾帧 |
| `200+` | Ref2VA 动态图片、视频和音频加载节点 |

Turbo 工作流增加：

| 节点 | 类型 | 配置 |
|---|---|---|
| `123` | `MiniMaxH3TurboSampler` | 双时间轴采样器 |
| `142` | `MiniMaxH3TurboLoRA` | `ckpt500`，强度 1.0 |

可选 NaughtyTimes 工作流增加节点 `141`，类型为 `LoraLoaderBypass`，模型强度 0.5，CLIP 强度 0.0。

## 自定义节点

Ref2VA 视频参考由 API 动态创建 `VHS_LoadVideo` 节点，因此需要 [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)。

Turbo 工作流需要 [ComfyUI-MiniMax-H3-Turbo](https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo)。当前部署包含 [`turbo-lowvram-device.patch`](../patches/turbo-lowvram-device.patch)，用于修复 `--lowvram` 模式下 Adaln LoRA 张量位于 CPU 与 CUDA 的设备不一致错误。

## 参数限制

| 参数 | 范围 |
|---|---|
| 时长 | 1 至 15 秒 |
| 步数 | 4 至 50，默认 10 |
| 宽高 | 32 的倍数，最小边不低于 352 |
| FL2VA 素材 | 1 至 2 张图片 |
| Ref2VA 图片 | 最多 9 张 |
| Ref2VA 视频 | 最多 3 段，每段 1 至 15 秒 |
| Ref2VA 音频 | 最多 3 段，每段 1 至 15 秒 |
