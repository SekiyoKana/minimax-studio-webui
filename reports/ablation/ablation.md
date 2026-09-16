# 本地工作流结构消融实验

实验时间：2026-09-16T08:15:16.977512+00:00
代码版本：`d1a6050573daf232836a5206477f1ad6d179618e`

## 实验设置

所有案例均使用本地 `workflows/` 文件和 `ComfyUIH3Engine._build_workflow`。未提交 ComfyUI 任务，未访问远端服务。分辨率为 608×352，时长为 3 秒，随机种子为 1729。

## 案例结果

| 案例 | 工作流 | 节点数 | 动态参考节点 | 组件 | 关键配置 |
|---|---|---:|---:|---|---|
| `fl2va-fp8/native/8steps` | `workflows/minimax_h3_fl2va_fp8_720p_15s_api.json` | 16 | 0 | video_output | steps=8 |
| `fl2va-fp8/turbo-lora/8steps` | `workflows/minimax_h3_fl2va_fp8_turbo_lora_api.json` | 18 | 0 | turbo_lora, sigma_shift, video_output | steps=8 |
| `ref2va-fp8/native/8steps` | `workflows/minimax_h3_ref2va_fp8_scaled_api.json` | 17 | 3 | video_output | steps=8 |
| `ref2va-fp8/turbo-lora/8steps` | `workflows/minimax_h3_ref2va_fp8_turbo_lora_api.json` | 19 | 3 | turbo_lora, sigma_shift, video_output | steps=8 |
| `ref2va-fp8/dual-sampling/8steps` | `workflows/minimax_h3_ref2va_fp8_dual_sampling_upscale_api.json` | 32 | 2 | sigma_shift, sol_attn, latent_upscaler, sigma_refiner, video_output | steps=8 |
| `fl2va-fp8/h3-sa/8steps` | `workflows/minimax_h3_fl2va_fp8_sa_api.json` | 30 | 0 | turbo_lora, sigma_shift, sol_attn, latent_upscaler, video_output | steps=8 |
| `ref2va-fp8/h3-sa/8steps` | `workflows/minimax_h3_ref2va_fp8_sa_api.json` | 32 | 3 | turbo_lora, sigma_shift, sol_attn, latent_upscaler, video_output | steps=8 |
| `fl2va-fp8/vdn-h3/8steps` | `workflows/minimax_h3_fl2va_vdn_api.json` | 17 | 0 | vdn, video_output | stage-dmd-step-250，turbo=True |
| `fl2va-fp8/vdn-h3/50steps` | `workflows/minimax_h3_fl2va_vdn_api.json` | 17 | 0 | vdn, video_output | stage-b-step-2000，turbo=False |
| `ref2va-fp8/vdn-h3/8steps` | `workflows/minimax_h3_ref2va_vdn_api.json` | 18 | 3 | vdn, video_output | stage-dmd-step-250，turbo=True |
| `ref2va-fp8/h3-nsfw/8steps` | `workflows/minimax_h3_ref2va_fp8_nsfw_lora_api.json` | 18 | 3 | nsfw_lora, video_output | steps=8 |
| `ref2va-fp8/digital-human/20steps` | `workflows/minimax_h3_ref2va_fp8_digital_human_api.json` | 16 | 0 | audio_drive, video_output | steps=20 |
| `ref2va-fp8/tts/20steps` | `workflows/minimax_h3_ref2va_fp8_tts_api.json` | 14 | 2 | audio_output | steps=20 |
| `music3-int8/music3/30steps` | `workflows/minimax_music3_int8_api.json` | 9 | 0 | audio_output | steps=30，force_duration=True |

## 检查结果

- 通过：native 不包含扩展加速、放大或专用输出节点
- 通过：turbo-lora 包含 LoRA 与 Sigma Shift
- 通过：H3 SA 包含 LoRA、Sigma Shift、Sol-Attn 和潜空间放大
- 通过：VDN-H3 不叠加 Sol-Attn
- 通过：VDN-H3 8 步选择 DMD stage 并启用 turbo adapter
- 通过：VDN-H3 50 步选择 B stage 并关闭 turbo adapter
- 通过：双采包含潜空间放大、Sol-Attn 和 Sigma Refiner

## 解释范围

本实验确认工作流构图和服务端参数分支的结构差异。未执行模型推理，因此不对画面质量、运动一致性、音频质量或显存峰值作出结论。
