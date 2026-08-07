# Third-party Projects and Licenses

[中文](THIRD_PARTY_NOTICES.md)

This repository does not contain model weights or copies of the ComfyUI and custom-node source trees. The installer checks out pinned commits from the original projects.

| Project | Source | Pinned Revision | License |
|---|---|---|---|
| ComfyUI | [comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI) | `563b98eefbe643a4cd510ee7f0b43e79880d5a3f` | GPL-3.0 |
| ComfyUI MiniMax H3 Turbo | [Larryvrh/ComfyUI-MiniMax-H3-Turbo](https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo) | `96cc1ddc001617da132dd73f31cd43666bf1d8d4` | Apache-2.0 |
| ComfyUI VideoHelperSuite | [Kosinkadink/ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) | `993082e4f2473bf4acaf06f51e33877a7eb38960` | GPL-3.0 |
| MiniMax H3 | [MiniMaxAI/MiniMax-H3](https://huggingface.co/MiniMaxAI/MiniMax-H3) | Pinned files in the model manifest | MiniMax H3 Community License Agreement |
| ComfyUI-format H3 weights | [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3) | `eb8a16107c595128b3a578f82d2ce2f75920c355` | MiniMax H3 Community License Agreement |
| MiniMax H3 Turbo LoRA | [larryvrh/MiniMax-H3-Turbo-Lora](https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora) | `7a44622816e16032cb0b6d044d8820da39a1dfdc` | Apache-2.0 |
| NaughtyTimes MiniMax H3 LoRA | [SexGod1979/NaughtyTimes_MiniMax-H3](https://huggingface.co/SexGod1979/NaughtyTimes_MiniMax-H3) | User-supplied file | Author terms |
| Lucide | [lucide-icons/lucide](https://github.com/lucide-icons/lucide) | 0.468.0 CDN | ISC |
| Google Fonts | [Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC), [DM Mono](https://fonts.google.com/specimen/DM+Mono) | CDN | SIL Open Font License 1.1 |

`patches/turbo-lowvram-device.patch` is a runtime compatibility modification for the pinned Turbo node. Deployments must preserve the upstream Apache-2.0 license and the modification notice.

Original source code in this repository is licensed under the [MIT License](LICENSE). The MIT License does not alter the license terms for model weights, ComfyUI, custom nodes, fonts, or other third-party components.
