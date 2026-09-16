#!/usr/bin/env python3
"""Run local, GPU-free structural ablations for the H3 workflow builder.

The script loads and builds every local workflow without submitting a task to
ComfyUI. It records graph components, dynamic reference injection, and
execution-mode-specific parameters. Remote services are intentionally not
accessed by this script.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports" / "ablation"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine import ComfyUIH3Engine
from app.settings import Settings


def align_frames(duration: float) -> int:
    frames = max(5, round(duration * 24))
    while frames % 17 != 5:
        frames += 1
    return frames


def job_for(variant: str, mode: str, *, steps: int = 8) -> tuple[dict[str, Any], list[str]]:
    references: list[dict[str, Any]]
    names: list[str]
    if variant == "music3-int8":
        references, names = [], []
    elif mode == "digital-human":
        references = [{"type": "image"}, {"type": "audio"}]
        names = ["ablation_portrait.png", "ablation_drive.wav"]
    elif mode == "tts":
        references = [{"type": "audio"}, {"type": "audio"}]
        names = ["ablation_speaker_1.wav", "ablation_speaker_2.wav"]
    elif variant == "fl2va-fp8":
        references = [{"type": "image"}]
        names = ["ablation_first_frame.png"]
    elif mode == "dual-sampling":
        references = [{"type": "image"}, {"type": "image"}]
        names = ["ablation_ref_1.png", "ablation_ref_2.png"]
    else:
        references = [
            {"type": "image"},
            {"type": "video", "has_audio": True},
            {"type": "audio"},
        ]
        names = ["ablation_ref.png", "ablation_motion.mp4", "ablation_voice.wav"]

    request: dict[str, Any] = {
        "prompt": "固定机位，人物缓慢转身，保持身份、服装、光线和环境连续。",
        "lyrics": "[Instrumental]" if variant == "music3-int8" else "",
        "model_variant": variant,
        "execution_mode": mode,
        "width": 608,
        "height": 352,
        "duration": 3.0,
        "num_frames": align_frames(3.0),
        "steps": 30 if mode == "music3" else steps,
        "seed": 1729,
        "references": references,
        "ref_image_size": "match",
        "sa_tau": 1.3,
        "sa_start_percent": 0.2,
        "sa_end_percent": 0.9,
        "sa_min_tokens": 4096,
        "sa_int8_qk": True,
        "sa_int8_pv": True,
        "sa_sink_conditioning": "exact_kv_and_rows",
        "sa_morton": False,
        "sa_morton_curve": "2d_frame",
        "sa_dense_blocks": "0",
        "sa_stage2_denoise": 0.35,
    }
    if mode == "music3":
        request["prompt"] = "Instrumental synth-pop, 112 BPM, bright analog bass, wide chorus."
    if mode == "tts":
        request["prompt"] = "(S1) 成年女性，语速平稳，语气克制。<d>[中文] 开始录音。</d>"
    return {"id": f"ablation-{variant}-{mode}-{steps}", "input_paths": [], "request": request}, names


def class_types(workflow: dict[str, Any]) -> list[str]:
    return sorted({str(node.get("class_type")) for node in workflow.values()})


def component_flags(workflow: dict[str, Any]) -> dict[str, bool]:
    types = set(class_types(workflow))
    return {
        "turbo_lora": "LoraLoaderModelOnly" in types,
        "nsfw_lora": "LoraLoaderBypass" in types,
        "sigma_shift": "MiniMaxH3SigmaShift" in types,
        "sol_attn": "SolAttnPatch" in types,
        "vdn": "ApplyVDNH3" in types,
        "latent_upscaler": "MinimaxH3LatentUpscaler3D" in types,
        "sigma_refiner": "H3SigmaRefiner" in types,
        "audio_drive": "VRGDG_MiniMaxH3AudioDrive" in types,
        "audio_output": "SaveAudio" in types,
        "video_output": "SaveVideo" in types,
    }


def compact_inputs(workflow: dict[str, Any]) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    for node_id in ("3", "9", "13", "92", "124", "127", "136", "142", "143", "144", "148"):
        node = workflow.get(node_id)
        if not node:
            continue
        inputs = node.get("inputs", {})
        selected[node_id] = {
            key: value
            for key, value in inputs.items()
            if key in {
                "caption", "device", "filename_prefix", "force_duration", "height", "length",
                "lora_name", "model", "noise_seed", "prompt", "ref_image_size", "sampler_name",
                "scheduler", "seed", "shift_audio", "shift_video", "steps", "strength_model",
                "tau", "start_percent", "end_percent", "min_tokens", "int8_qk", "int8_pv",
                "sink_conditioning", "morton", "morton_curve", "dense_blocks", "vdn_checkpoint",
                "apply_turbo_adapter", "width", "mode.width", "mode.height", "denoise",
            }
        }
    return selected


def workflow_path(settings: Settings, variant: str, mode: str) -> Path:
    paths = {
        ("fl2va-fp8", "native"): settings.comfy_workflow,
        ("fl2va-fp8", "turbo-lora"): settings.comfy_turbo_workflow,
        ("ref2va-fp8", "native"): settings.comfy_ref2va_workflow,
        ("ref2va-fp8", "turbo-lora"): settings.comfy_ref2va_turbo_workflow,
        ("ref2va-fp8", "dual-sampling"): settings.comfy_dual_sampling_workflow,
        ("fl2va-fp8", "h3-sa"): settings.comfy_sa_workflow,
        ("ref2va-fp8", "h3-sa"): settings.comfy_ref2va_sa_workflow,
        ("fl2va-fp8", "vdn-h3"): settings.comfy_vdn_workflow,
        ("ref2va-fp8", "vdn-h3"): settings.comfy_ref2va_vdn_workflow,
        ("ref2va-fp8", "h3-nsfw"): settings.comfy_nsfw_workflow,
        ("ref2va-fp8", "digital-human"): settings.comfy_digital_human_workflow,
        ("ref2va-fp8", "tts"): settings.comfy_tts_workflow,
        ("music3-int8", "music3"): settings.comfy_music3_workflow,
    }
    return paths[(variant, mode)]


def run_case(engine: ComfyUIH3Engine, settings: Settings, variant: str, mode: str, steps: int) -> dict[str, Any]:
    job, names = job_for(variant, mode, steps=steps)
    workflow = engine._build_workflow(
        job,
        names,
        music3_device="cuda:0" if mode == "music3" else None,
    )
    flags = component_flags(workflow)
    return {
        "case": f"{variant}/{mode}/{steps}steps",
        "model_variant": variant,
        "execution_mode": mode,
        "steps": steps,
        "workflow_file": str(workflow_path(settings, variant, mode).relative_to(ROOT)),
        "workflow_exists": workflow_path(settings, variant, mode).is_file(),
        "node_count": len(workflow),
        "class_types": class_types(workflow),
        "dynamic_reference_nodes": sorted(
            node_id for node_id in workflow if node_id.isdigit() and int(node_id) >= 200
        ),
        "component_flags": flags,
        "inputs": compact_inputs(workflow),
    }


def validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    by_case = {item["case"]: item for item in cases}
    checks: list[tuple[bool, str]] = []

    native = by_case["fl2va-fp8/native/8steps"]
    turbo = by_case["fl2va-fp8/turbo-lora/8steps"]
    sa = by_case["fl2va-fp8/h3-sa/8steps"]
    vdn8 = by_case["fl2va-fp8/vdn-h3/8steps"]
    vdn50 = by_case["fl2va-fp8/vdn-h3/50steps"]
    dual = by_case["ref2va-fp8/dual-sampling/8steps"]
    checks.extend(
        [
            (
                not any(
                    native["component_flags"][name]
                    for name in (
                        "turbo_lora", "nsfw_lora", "sigma_shift", "sol_attn", "vdn",
                        "latent_upscaler", "sigma_refiner", "audio_drive", "audio_output",
                    )
                ),
                "native 不包含扩展加速、放大或专用输出节点",
            ),
            (turbo["component_flags"]["turbo_lora"] and turbo["component_flags"]["sigma_shift"], "turbo-lora 包含 LoRA 与 Sigma Shift"),
            (sa["component_flags"]["turbo_lora"] and sa["component_flags"]["sigma_shift"] and sa["component_flags"]["sol_attn"] and sa["component_flags"]["latent_upscaler"], "H3 SA 包含 LoRA、Sigma Shift、Sol-Attn 和潜空间放大"),
            (vdn8["component_flags"]["vdn"] and not vdn8["component_flags"]["sol_attn"], "VDN-H3 不叠加 Sol-Attn"),
            (vdn8["inputs"]["144"]["vdn_checkpoint"] == "stage-dmd-step-250" and vdn8["inputs"]["144"]["apply_turbo_adapter"], "VDN-H3 8 步选择 DMD stage 并启用 turbo adapter"),
            (vdn50["inputs"]["144"]["vdn_checkpoint"] == "stage-b-step-2000" and not vdn50["inputs"]["144"]["apply_turbo_adapter"], "VDN-H3 50 步选择 B stage 并关闭 turbo adapter"),
            (dual["component_flags"]["latent_upscaler"] and dual["component_flags"]["sol_attn"] and dual["component_flags"]["sigma_refiner"], "双采包含潜空间放大、Sol-Attn 和 Sigma Refiner"),
        ]
    )
    return [f"{'通过' if passed else '失败'}：{description}" for passed, description in checks]


def git_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 本地工作流结构消融实验",
        "",
        f"实验时间：{report['generated_at']}",
        f"代码版本：`{report['git_revision']}`",
        "",
        "## 实验设置",
        "",
        "所有案例均使用本地 `workflows/` 文件和 `ComfyUIH3Engine._build_workflow`。未提交 ComfyUI 任务，未访问远端服务。分辨率为 608×352，时长为 3 秒，随机种子为 1729。",
        "",
        "## 案例结果",
        "",
        "| 案例 | 工作流 | 节点数 | 动态参考节点 | 组件 | 关键配置 |",
        "|---|---|---:|---:|---|---|",
    ]
    for item in report["cases"]:
        flags = [name for name, enabled in item["component_flags"].items() if enabled]
        inputs = item["inputs"]
        if item["execution_mode"] == "vdn-h3":
            config = f"{inputs['144'].get('vdn_checkpoint')}，turbo={inputs['144'].get('apply_turbo_adapter')}"
        elif item["execution_mode"] == "music3":
            config = f"steps={inputs['9'].get('steps')}，force_duration={inputs['13'].get('force_duration')}"
        else:
            config = f"steps={item['steps']}"
        lines.append(
            f"| `{item['case']}` | `{item['workflow_file']}` | {item['node_count']} | {len(item['dynamic_reference_nodes'])} | {', '.join(flags) or '基础节点'} | {config} |"
        )
    lines.extend(["", "## 检查结果", ""])
    lines.extend(f"- {check}" for check in report["checks"])
    lines.extend(["", "## 解释范围", "", "本实验确认工作流构图和服务端参数分支的结构差异。未执行模型推理，因此不对画面质量、运动一致性、音频质量或显存峰值作出结论。"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    settings = Settings()
    engine = ComfyUIH3Engine(settings)
    cases: list[dict[str, Any]] = []
    case_specs = [
        ("fl2va-fp8", "native", 8),
        ("fl2va-fp8", "turbo-lora", 8),
        ("ref2va-fp8", "native", 8),
        ("ref2va-fp8", "turbo-lora", 8),
        ("ref2va-fp8", "dual-sampling", 8),
        ("fl2va-fp8", "h3-sa", 8),
        ("ref2va-fp8", "h3-sa", 8),
        ("fl2va-fp8", "vdn-h3", 8),
        ("fl2va-fp8", "vdn-h3", 50),
        ("ref2va-fp8", "vdn-h3", 8),
        ("ref2va-fp8", "h3-nsfw", 8),
        ("ref2va-fp8", "digital-human", 20),
        ("ref2va-fp8", "tts", 20),
        ("music3-int8", "music3", 30),
    ]
    for variant, mode, steps in case_specs:
        cases.append(run_case(engine, settings, variant, mode, steps))

    report = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
        "git_revision": git_revision(),
        "scope": "local-workflow-structure",
        "remote_tasks_submitted": False,
        "cases": cases,
        "checks": validate_cases(cases),
        "context_loop_segments": {
            str(duration): engine._split_h3_frames(round(duration * 24))
            for duration in (3, 15, 20, 30)
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "ablation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "ablation.md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    return 0 if all(item.startswith("通过：") for item in report["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
