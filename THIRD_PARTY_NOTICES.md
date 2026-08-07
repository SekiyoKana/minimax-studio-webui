# 第三方项目与许可

本仓库不包含模型权重，也不复制 ComfyUI 或自定义节点源码。安装脚本从原始项目检出固定 commit。

| 项目 | 来源 | 固定版本 | 许可 |
|---|---|---|---|
| ComfyUI | [comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI) | `563b98eefbe643a4cd510ee7f0b43e79880d5a3f` | GPL-3.0 |
| ComfyUI MiniMax H3 Turbo | [Larryvrh/ComfyUI-MiniMax-H3-Turbo](https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo) | `96cc1ddc001617da132dd73f31cd43666bf1d8d4` | Apache-2.0 |
| ComfyUI VideoHelperSuite | [Kosinkadink/ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) | `993082e4f2473bf4acaf06f51e33877a7eb38960` | GPL-3.0 |
| MiniMax H3 | [MiniMaxAI/MiniMax-H3](https://huggingface.co/MiniMaxAI/MiniMax-H3) | 模型清单中的固定文件 | MiniMax H3 Community License Agreement |
| ComfyUI 格式 H3 权重 | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3) | `eb8a16107c595128b3a578f82d2ce2f75920c355` | MiniMax H3 Community License Agreement |
| MiniMax H3 Turbo LoRA | [larryvrh/MiniMax-H3-Turbo-Lora](https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora) | `7a44622816e16032cb0b6d044d8820da39a1dfdc` | Apache-2.0 |
| NaughtyTimes MiniMax H3 LoRA | [SexGod1979/NaughtyTimes_MiniMax-H3](https://huggingface.co/SexGod1979/NaughtyTimes_MiniMax-H3) | 用户提供文件 | 作者条款 |
| Lucide | [lucide-icons/lucide](https://github.com/lucide-icons/lucide) | 0.468.0 CDN | ISC |
| Google Fonts | [Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC), [DM Mono](https://fonts.google.com/specimen/DM+Mono) | CDN | SIL Open Font License 1.1 |

`patches/turbo-lowvram-device.patch` 是对 Turbo 节点固定版本的运行兼容修改。部署时需要保留上游 Apache-2.0 许可和修改说明。

本项目源码尚未由所有者指定仓库级许可。上传 GitHub 前可以根据发布范围补充项目自身的 `LICENSE`。
