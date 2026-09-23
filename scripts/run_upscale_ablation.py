#!/usr/bin/env python3
"""Run an operational ComfyUI ablation over installed image upscalers."""

from __future__ import annotations

import argparse
import json
import time
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageChops, ImageStat


DEFAULT_MODELS = [
    ("RealESRGAN_x2plus.pth", 2),
    ("2xNomosUni_span_multijpg.pth", 2),
    ("4x-AnimeSharp.pth", 4),
    ("4x_foolhardy_Remacri.pth", 4),
    ("4x-UltraSharp.pth", 4),
    ("4x_NMKD-Siax_200k.pth", 4),
    ("4x-ClearRealityV1.pth", 4),
    ("ltx-2.3-spatial-upscaler-x2-1.0.safetensors", 2),
    ("ltx-2.3-spatial-upscaler-x2-1.1.safetensors", 2),
    ("ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors", 2),
]


def output_items(history: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for node_output in (history.get("outputs") or {}).values():
        if not isinstance(node_output, dict):
            continue
        for items in node_output.values():
            if isinstance(items, list):
                values.extend(item for item in items if isinstance(item, dict))
    return values


def reconstruction_mae(source: Image.Image, result: Image.Image) -> float:
    restored = result.convert("RGB").resize(source.size, Image.Resampling.LANCZOS)
    difference = ImageChops.difference(source.convert("RGB"), restored)
    return round(sum(ImageStat.Stat(difference).mean) / 3, 5)


def run_ablation(
    base_url: str,
    input_path: Path,
    workflow_path: Path,
    output_path: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    source_bytes = input_path.read_bytes()
    source_image = Image.open(BytesIO(source_bytes)).convert("RGB")
    run_id = f"run-{int(time.time())}"
    records: list[dict[str, Any]] = []
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=60, trust_env=False) as client:
        upload = client.post(
            "/upload/image",
            data={"type": "input", "subfolder": f"upscale-ablation/{run_id}", "overwrite": "true"},
            files={"image": (input_path.name, source_bytes, "image/png")},
        )
        upload.raise_for_status()
        uploaded = upload.json()
        input_name = f"{str(uploaded.get('subfolder') or '').strip('/')}/{uploaded.get('name')}"
        template = json.loads(workflow_path.read_text(encoding="utf-8"))
        for index, (model_name, expected_scale) in enumerate(DEFAULT_MODELS, start=1):
            record: dict[str, Any] = {
                "model": model_name,
                "expected_scale": expected_scale,
                "status": "submitted",
            }
            workflow = deepcopy(template)
            workflow["1"]["inputs"]["image"] = input_name
            workflow["2"]["inputs"]["model_name"] = model_name
            workflow["4"]["inputs"]["scale_by"] = 1.0
            workflow["5"]["inputs"]["filename_prefix"] = f"upscale-ablation/{run_id}/{index:02d}-{Path(model_name).stem}"
            started = time.monotonic()
            try:
                submitted = client.post(
                    "/prompt",
                    json={"prompt": workflow, "client_id": f"upscale-ablation-{run_id}"},
                )
                submitted.raise_for_status()
                prompt_id = submitted.json()["prompt_id"]
                record["prompt_id"] = prompt_id
                while time.monotonic() - started < timeout_seconds:
                    history = client.get(f"/history/{prompt_id}").json().get(prompt_id)
                    if history:
                        status = history.get("status") or {}
                        record["status"] = status.get("status_str") or "unknown"
                        if record["status"] != "success":
                            record["messages"] = status.get("messages", [])[-3:]
                            break
                        item = next(
                            (
                                candidate
                                for candidate in output_items(history)
                                if Path(str(candidate.get("filename") or "")).suffix.lower()
                                in {".png", ".jpg", ".jpeg", ".webp"}
                            ),
                            None,
                        )
                        if not item:
                            record["status"] = "missing_output"
                            break
                        response = client.get(
                            "/view",
                            params={
                                "filename": item["filename"],
                                "subfolder": item.get("subfolder", ""),
                                "type": item.get("type", "output"),
                            },
                        )
                        response.raise_for_status()
                        result_image = Image.open(BytesIO(response.content))
                        record.update(
                            output_width=result_image.width,
                            output_height=result_image.height,
                            output_bytes=len(response.content),
                            reconstruction_mae=reconstruction_mae(source_image, result_image),
                        )
                        break
                    time.sleep(0.5)
                else:
                    record["status"] = "timeout"
            except Exception as exc:  # Keep the ablation running for later candidates.
                record["status"] = "error"
                record["error"] = str(exc)[:500]
            record["elapsed_seconds"] = round(time.monotonic() - started, 3)
            records.append(record)

    result = {
        "schema_version": 1,
        "run_id": run_id,
        "base_url": base_url,
        "input": str(input_path),
        "input_width": source_image.width,
        "input_height": source_image.height,
        "models": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8188")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, default=Path("workflows/comfy_upscale_image_api.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/ablation/upscale_ablation.json"))
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    result = run_ablation(args.base_url, args.input, args.workflow, args.output, args.timeout)
    for record in result["models"]:
        print(record["status"], record["model"], record.get("elapsed_seconds"), record.get("error", ""))


if __name__ == "__main__":
    main()
