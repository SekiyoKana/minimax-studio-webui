#!/usr/bin/env python3
"""在本地生成一批"看不见的"占位任务，用于开发历史列表 / 宫格 / 详情页。

真实任务记录保存在 ``data/jobs/<id>.json``，产物在 ``data/outputs``，参考素材在
``data/uploads/<job_id>``。本脚本直接按同样的结构写入这些目录，因此不需要跑模型，
也能让界面出现完整的历史任务（封面、进度、失败原因、筛选状态等）。

所有记录都带有 ``demo_placeholder: true`` 标记且 id 以 ``demo-`` 开头，
``--clean`` 只会删除这类记录，不会碰真实任务。

用法::

    python3 scripts/seed_demo_jobs.py              # 重建一批占位任务（默认 13 条）
    python3 scripts/seed_demo_jobs.py --count 24   # 生成更多，方便测分页
    python3 scripts/seed_demo_jobs.py --no-active  # 不要 running / queued 占位
    python3 scripts/seed_demo_jobs.py --clean      # 只清理占位任务

写入后需要重启服务（``pkill -f "uvicorn app.main:app"`` 后重新启动）才能看到效果，
因为任务列表是在进程启动时从磁盘加载到内存的。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import secrets
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_PREFIX = "demo-"
PLACEHOLDER_KEY = "demo_placeholder"

# 渐变色板，尽量让宫格封面之间有明显区分。
PALETTES = [
    ("0x141e30", "0x243b55", "0x6dd5ed"),
    ("0x2b1055", "0x7597de", "0xd76ba1"),
    ("0x1c0a00", "0xff6b35", "0xffd166"),
    ("0x052e16", "0x1f8a70", "0xb7e4c7"),
    ("0x0f0c29", "0x302b63", "0xc026d3"),
    ("0x120a2a", "0x8a2be2", "0x67e8f9"),
]

MEDIA_SUFFIX = {"video": ".mp4", "image": ".png", "audio": ".flac"}
GRADIENT_TYPES = ("linear", "radial", "circular", "spiral")


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return value.isoformat()


def align_frames(duration: float) -> int:
    frames = max(5, round(duration * 24))
    while frames % 17 != 5:
        frames += 1
    return frames


def ratio_label(width: int, height: int) -> str:
    divisor = math.gcd(width, height) or 1
    return f"{width // divisor}:{height // divisor}"


def ffmpeg_bin() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise SystemExit("未找到 ffmpeg，请先安装后再生成占位素材。")
    return binary


def run_ffmpeg(args: list[str]) -> None:
    process = subprocess.run(args, capture_output=True, text=True)
    if process.returncode != 0:
        stderr = (process.stderr or process.stdout or "").strip().splitlines()
        detail = stderr[-1] if stderr else f"exit={process.returncode}"
        raise RuntimeError(f"ffmpeg 生成占位素材失败：{detail}")


def gradient_source(
    width: int,
    height: int,
    palette: tuple[str, str, str],
    *,
    duration: float,
    look: int = 0,
) -> str:
    c0, c1, c2 = palette
    kind = GRADIENT_TYPES[look % len(GRADIENT_TYPES)]
    return (
        f"gradients=size={width}x{height}:c0={c0}:c1={c1}:c2={c2}"
        f":x0=0:y0=0:x1={width}:y1={height}:type={kind}"
        f":speed=0.008:duration={duration}:rate=24"
    )


def color_grade(look: int) -> str:
    """每条记录的色相和噪点都错开，避免宫格封面看起来一模一样。"""
    hue = (look * 53) % 360
    return f"hue=h={hue}:s=1.08,vignette=PI/5,noise=alls=5:allf=t+u"


def make_video(
    path: Path,
    width: int,
    height: int,
    duration: float,
    palette: tuple[str, str, str],
    look: int = 0,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", gradient_source(width, height, palette, duration=duration, look=look),
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", f"{duration:.3f}",
            "-vf", color_grade(look),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart",
            str(path),
        ]
    )


def make_image(
    path: Path,
    width: int,
    height: int,
    palette: tuple[str, str, str],
    look: int = 0,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    hue = (look * 53) % 360
    run_ffmpeg(
        [
            ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", gradient_source(width, height, palette, duration=1, look=look),
            "-frames:v", "1", "-vf", f"hue=h={hue}:s=1.08,vignette=PI/5", str(path),
        ]
    )


def make_audio(path: Path, duration: float, *, quiet: bool = False) -> None:
    """合成一段柔和的三音和弦，作为音乐 / 配音占位素材。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    volume = "0.06" if quiet else "0.12"
    fade_out_start = max(0.0, duration - 1.0)
    run_ffmpeg(
        [
            ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"sine=frequency=261.63:duration={duration}:sample_rate=48000",
            "-f", "lavfi", "-i", f"sine=frequency=329.63:duration={duration}:sample_rate=48000",
            "-f", "lavfi", "-i", f"sine=frequency=392.00:duration={duration}:sample_rate=48000",
            "-filter_complex",
            f"[0:a][1:a][2:a]amix=inputs=3:normalize=0,volume={volume},"
            f"afade=t=in:st=0:d=0.8,afade=t=out:st={fade_out_start:.2f}:d=1",
            "-c:a", "flac", "-t", f"{duration:.3f}", str(path),
        ]
    )


def make_preview(video: Path, preview: Path) -> bool:
    run_ffmpeg(
        [
            ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
            "-ss", "0.5", "-i", str(video), "-frames:v", "1",
            "-vf", "scale=320:-2:force_original_aspect_ratio=decrease",
            "-q:v", "4", str(preview),
        ]
    )
    return preview.is_file()


CATALOG: list[dict[str, Any]] = [
    {
        "minutes_ago": 3,
        "status": "queued",
        "kind": "video",
        "title": "雨夜霓虹街头",
        "prompt": "雨夜的霓虹街头，镜头缓慢推近，一位撑着透明雨伞的行人穿过斑马线，地面积水反光，电影感浅景深。",
        "width": 1376, "height": 768, "duration": 5, "steps": 40,
        "stage": "等待推理节点执行",
    },
    {
        "minutes_ago": 7,
        "status": "running",
        "kind": "video",
        "mode": "h3-sa",
        "title": "雪山日出航拍",
        "prompt": "雪山日出，云海翻涌，航拍镜头从峡谷中缓缓升起，金色阳光掠过山脊，空气通透。",
        "width": 1280, "height": 736, "duration": 8, "steps": 30,
        "progress": 62, "stage": "采样中 · 62%",
    },
    {
        "minutes_ago": 38,
        "status": "completed",
        "kind": "video",
        "variant": "ref2va-fp8",
        "title": "机械蜂鸟",
        "prompt": "参考图中的机械蜂鸟在雨林花丛中悬停，金属翅膀高频振动，露珠被气流吹散，微距镜头。",
        "width": 1152, "height": 640, "duration": 6, "steps": 50,
        "references": [{"type": "image", "name": "hummingbird-frame.png", "width": 640, "height": 360}],
    },
    {
        "minutes_ago": 96,
        "status": "completed",
        "kind": "video",
        "mode": "turbo-lora",
        "title": "赛博城市天际线",
        "prompt": "赛博朋克城市天际线，全息广告牌在雨中闪烁，飞行器拖着光轨穿过楼群，镜头缓慢横移。",
        "width": 960, "height": 544, "duration": 5, "steps": 8,
    },
    {
        "minutes_ago": 184,
        "status": "completed",
        "kind": "video",
        "mode": "digital-human",
        "variant": "ref2va-fp8",
        "title": "数字人口播",
        "prompt": "数字人主播端坐在工作台前，自然地介绍新一代视频生成模型，口型与音频对齐，室内柔光。",
        "width": 864, "height": 480, "duration": 12, "steps": 40,
        "references": [
            {"type": "image", "name": "portrait.png", "width": 512, "height": 512},
            {"type": "audio", "name": "driving-voice.flac", "duration": 6, "quiet": True},
        ],
    },
    {
        "minutes_ago": 310,
        "status": "completed",
        "kind": "audio",
        "mode": "music3",
        "variant": "music3-int8",
        "title": "夏夜海边",
        "prompt": "夏夜海边的电子流行，节奏轻快，带一点复古合成器味道。",
        "lyrics": "海风把霓虹吹散\n我们沿着海岸线奔跑\n把整个夏天\n装进耳机里\n",
        "width": 0, "height": 0, "duration": 24, "steps": 8,
    },
    {
        "minutes_ago": 540,
        "status": "completed",
        "kind": "audio",
        "mode": "tts",
        "variant": "ref2va-fp8",
        "title": "欢迎语配音",
        "prompt": "欢迎使用 MiniMax H3 Studio，本段语音来自本地占位任务，仅用于界面开发。",
        "width": 0, "height": 0, "duration": 6, "steps": 8,
        "references": [{"type": "audio", "name": "voice-sample.flac", "duration": 4, "quiet": True}],
    },
    {
        "minutes_ago": 790,
        "status": "completed",
        "kind": "image",
        "mode": "custom",
        "workflow_name": "分镜图生成器",
        "title": "机器人第一次看到雪",
        "prompt": "四格漫画分镜：一台旧机器人第一次看到雪，从好奇到伸出手掌接住雪花，最后露出微笑。",
        "width": 1024, "height": 1024, "duration": 0, "steps": 30,
        "references": [{"type": "image", "name": "robot-sheet.png", "width": 512, "height": 512}],
    },
    {
        "minutes_ago": 1320,
        "status": "completed",
        "kind": "video",
        "task_type": "upscale",
        "title": "真人 · 2x 超分",
        "prompt": "",
        "width": 1920, "height": 1088, "duration": 5, "steps": 1,
        "references": [{"type": "video", "name": "input-take.mp4", "duration": 3}],
        "upscale_category": "real", "upscale_scale": 2,
    },
    {
        "minutes_ago": 1810,
        "status": "completed",
        "kind": "video",
        "mode": "runninghub",
        "workflow_name": "Kling 2.1 图生视频",
        "title": "沙漠日落航拍",
        "prompt": "无人机贴着沙丘飞行，日落把沙脊染成橘红色，远处驼队剪影缓慢移动。",
        "width": 1280, "height": 720, "duration": 5, "steps": 0,
        "references": [{"type": "image", "name": "desert-dune.png", "width": 640, "height": 360}],
    },
    {
        "minutes_ago": 2430,
        "status": "completed",
        "kind": "video",
        "mode": "vdn-h3",
        "title": "深海发光生物",
        "prompt": "深海中的发光水母群缓慢漂浮，蓝色生物光在黑暗中舒展，镜头从底部仰拍。",
        "width": 1344, "height": 768, "duration": 7, "steps": 36,
    },
    {
        "minutes_ago": 3140,
        "status": "failed",
        "kind": "video",
        "title": "森林晨雾",
        "prompt": "清晨的森林，薄雾在树干之间流动，丁达尔光束穿过树冠，镜头缓慢向前推进。",
        "width": 1376, "height": 768, "duration": 6, "steps": 40,
        "progress": 37,
        "stage": "生成失败",
        "error": "显存不足：加载扩散模型时 CUDA out of memory（已重试 3 次）",
    },
    {
        "minutes_ago": 3900,
        "status": "cancelled",
        "kind": "video",
        "mode": "turbo-lora",
        "title": "老式打字机特写",
        "prompt": "老式打字机特写，手指敲下回车键，纸页上墨迹刚刚干透，暖色台灯光。",
        "width": 960, "height": 544, "duration": 5, "steps": 8,
        "stage": "已取消",
    },
]


def build_logs(
    spec: dict[str, Any],
    created: datetime,
    started: datetime | None,
    finished: datetime | None,
) -> list[dict[str, Any]]:
    status = str(spec["status"])
    events: list[tuple[datetime, str, str, str, int]] = [
        (created, "任务已创建并进入队列", "info", "queued", 0),
    ]
    if started:
        events.append((started, "任务已分配至 GPU0", "info", "running", 1))
    if finished and started:
        span = max(1.0, (finished - started).total_seconds())
        mid = started + timedelta(seconds=span * 0.6)
        if status in {"completed", "running"}:
            events.append((mid, "采样中", "info", "running", int(spec.get("progress") or 60)))
        if status == "completed":
            events.append((finished, "生成完成", "info", "completed", 100))
        elif status == "failed":
            events.append((finished, f"生成失败：{spec.get('error') or '未知错误'}", "error", "failed", int(spec.get("progress") or 0)))
        elif status == "cancelled":
            events.append((finished, "任务已取消", "info", "cancelled", 0))
    elif status == "running":
        events.append((utc_now() - timedelta(seconds=30), "采样中", "info", "running", int(spec.get("progress") or 0)))
    return [
        {
            "timestamp": iso(moment),
            "job_id": spec["_id"],
            "level": level,
            "status": event_status,
            "progress": progress,
            "message": message,
        }
        for moment, message, level, event_status, progress in sorted(events, key=lambda item: item[0])
    ]


def reference_file(
    reference: dict[str, Any],
    upload_dir: Path,
    palette: tuple[str, str, str],
    look: int,
) -> Path:
    kind = reference["type"]
    path = upload_dir / reference["name"]
    if kind == "image":
        make_image(
            path,
            int(reference.get("width") or 640),
            int(reference.get("height") or 360),
            palette,
            look,
        )
    elif kind == "audio":
        make_audio(path, float(reference.get("duration") or 4), quiet=bool(reference.get("quiet")))
    elif kind == "video":
        make_video(path, 640, 360, float(reference.get("duration") or 3), palette, look)
    else:
        path.write_bytes(b"placeholder")
    return path


def build_job(spec: dict[str, Any], data_dir: Path, index: int) -> dict[str, Any]:
    now = utc_now()
    created = now - timedelta(minutes=int(spec["minutes_ago"]))
    status = str(spec["status"])
    finished = created + timedelta(
        seconds=float(spec.get("render_seconds") or (120 + index % 5 * 40))
    )
    started = created + timedelta(seconds=18) if status in {"completed", "failed", "cancelled", "running"} else None
    job_id = f"{DEMO_PREFIX}{secrets.token_hex(4)}"
    spec["_id"] = job_id
    updated = finished if status in {"completed", "failed", "cancelled"} else now

    kind = str(spec["kind"])
    duration = float(spec.get("duration") or 0)
    width = int(spec.get("width") or 0)
    height = int(spec.get("height") or 0)
    palette = PALETTES[index % len(PALETTES)]
    media_type = "audio" if kind == "audio" else "image" if kind == "image" else "video"

    upload_dir = data_dir / "uploads" / job_id
    input_paths: list[str] = []
    references: list[dict[str, Any]] = []
    if spec.get("references"):
        upload_dir.mkdir(parents=True, exist_ok=True)
        for reference in spec["references"]:
            path = reference_file(
                reference,
                upload_dir,
                PALETTES[(index + 2) % len(PALETTES)],
                index + 2,
            )
            input_paths.append(str(path))
            entry: dict[str, Any] = {
                "name": path.name,
                "type": reference["type"],
                "size": path.stat().st_size,
            }
            if reference["type"] in {"audio", "video"}:
                entry["duration"] = float(reference.get("duration") or 0)
            references.append(entry)

    output_stem = created.strftime("%Y%m%d_%H%M%S_%f")[:-3]
    result_path: Path | None = None
    preview_path: Path | None = None
    if status == "completed":
        result_path = data_dir / "outputs" / f"{output_stem}{MEDIA_SUFFIX[kind]}"
        if kind == "video":
            make_video(result_path, width, height, duration, palette, index)
            preview_path = result_path.with_name(f"{result_path.stem}.preview.jpg")
            if not make_preview(result_path, preview_path):
                preview_path = None
        elif kind == "image":
            make_image(result_path, width, height, palette, index)
        else:
            make_audio(result_path, duration)

    mode = str(spec.get("mode") or "native")
    task_type = str(spec.get("task_type") or "generation")
    variant = str(spec.get("variant") or "fl2va-fp8")
    request: dict[str, Any] = {
        "prompt": spec["prompt"],
        "lyrics": spec.get("lyrics") or "",
        "model_variant": variant,
        "execution_mode": mode,
        "task_type": task_type,
        "upscale_category": spec.get("upscale_category") or "",
        "upscale_scale": spec.get("upscale_scale") or 2,
        "auto_upscale": False,
        "auto_upscale_category": "real",
        "auto_upscale_scale": 2,
        "width": width,
        "height": height,
        "ratio": ratio_label(width, height) if width and height else "",
        "megapixels": round(width * height / 1_000_000, 2) if width and height else 0,
        "duration": duration,
        "num_frames": align_frames(duration) if duration else 0,
        "steps": int(spec.get("steps") or 0),
        "seed": int(spec.get("seed") or (100000 + index * 7919 % 899999)),
        "references": references,
        "media_type": media_type,
        "comfy_node": "auto",
        "incognito": False,
    }
    if task_type == "upscale":
        request.update({"source_fps": 24.0, "has_audio": True})
    if mode == "custom":
        request.update({
            "workflow_id": "wf-demo-storyboard",
            "workflow_name": spec.get("workflow_name") or "自定义工作流",
        })
    if mode == "runninghub":
        request.update({
            "provider": "runninghub",
            "workflow_id": "rh-kling-2-1",
            "workflow_name": spec.get("workflow_name") or "RunningHub",
            "runninghub_resource_id": "kling-2-1",
            "runninghub_resource_type": "workflow",
            "runninghub_workflow_name": spec.get("workflow_name") or "RunningHub",
            "runninghub_schema": {},
            "runninghub_parameters": {},
            "comfy_node": "rh:kling-2-1",
        })

    job: dict[str, Any] = {
        "id": job_id,
        PLACEHOLDER_KEY: True,
        "title": spec["title"],
        "folder_id": None,
        "folder_name": "",
        "status": status,
        "stage": spec.get("stage") or ("生成完成" if status == "completed" else "等待推理节点执行"),
        "progress": int(spec.get("progress") or (100 if status == "completed" else 0)),
        "created_at": iso(created),
        "updated_at": iso(updated),
        "cancel_requested": False,
        "request": request,
        "output_stem": output_stem,
        "input_paths": input_paths,
        "logs": [],
    }
    if started and status != "queued":
        job["started_at"] = iso(started)
    if status in {"completed", "failed", "cancelled"}:
        job["completed_at"] = iso(finished)
    if spec.get("error"):
        job["error"] = spec["error"]
    if status in {"completed", "running", "failed"}:
        node_name = "Kling 2.1" if mode == "runninghub" else "GPU0"
        job["assigned_node"] = {
            "id": "rh:kling-2-1" if mode == "runninghub" else "node-demo-gpu",
            "name": node_name,
            "provider": "runninghub" if mode == "runninghub" else "comfyui",
        }
    if result_path:
        job["result_path"] = str(result_path)
        job["result_url"] = f"/api/v1/generations/{job_id}/result"
    if preview_path:
        job["preview_path"] = str(preview_path)
        job["preview_url"] = f"/api/v1/generations/{job_id}/preview"
    job["logs"] = build_logs({**spec, "_id": job_id}, created, started, finished if status in {"completed", "failed", "cancelled"} else None)
    return job


def is_demo_job(job: Any) -> bool:
    return (
        isinstance(job, dict)
        and job.get(PLACEHOLDER_KEY) is True
        and str(job.get("id") or "").startswith(DEMO_PREFIX)
    )


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def remove_path(path: Path, data_dir: Path, *, directory: bool = False) -> None:
    if not inside(path, data_dir):
        return
    if directory:
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def clean(data_dir: Path) -> int:
    jobs_dir = data_dir / "jobs"
    removed = 0
    for path in sorted(jobs_dir.glob("*.json")):
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not is_demo_job(job) or path.name != f"{job['id']}.json":
            continue
        for raw in job.get("input_paths") or []:
            remove_path(Path(str(raw)), data_dir)
        remove_path(data_dir / "uploads" / job["id"], data_dir, directory=True)
        if job.get("result_path"):
            result = Path(str(job["result_path"]))
            remove_path(result, data_dir)
            remove_path(result.with_suffix(".json"), data_dir)
            remove_path(result.with_name(f"{result.stem}.preview.jpg"), data_dir)
        remove_path(path, data_dir)
        removed += 1
    return removed


def expanded_catalog(count: int, *, include_active: bool = True) -> list[dict[str, Any]]:
    active = {"queued", "running"}
    specs = [
        dict(item)
        for item in CATALOG
        if include_active or item["status"] not in active
    ]
    if count <= len(specs):
        return specs[:count]
    # 超出内置数量时，复制"已完成"记录并拉开时间，方便测分页。
    completed = [item for item in specs if item["status"] == "completed"]
    if not completed:
        return specs
    offset = max(item["minutes_ago"] for item in specs)
    added = 0
    while len(specs) < count:
        source = dict(completed[added % len(completed)])
        added += 1
        source["minutes_ago"] = offset + 90 * added
        source["title"] = f"{source['title']} #{len(specs) + 1}"
        source["seed"] = 100000 + len(specs) * 3571 % 899999
        specs.append(source)
    return specs


def guard_present() -> bool:
    """占位任务靠 app/jobs.py 里的标记跳过调度，否则 running/queued 会被真实执行。"""
    try:
        source = (PROJECT_ROOT / "app" / "jobs.py").read_text(encoding="utf-8")
    except OSError:
        return False
    return PLACEHOLDER_KEY in source


def seed(data_dir: Path, count: int, *, include_active: bool) -> list[dict[str, Any]]:
    jobs_dir = data_dir / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    if not guard_present():
        print(
            "警告：app/jobs.py 中没有占位任务保护逻辑，已跳过 running / queued 占位，"
            "避免被调度到真实推理节点。",
            file=sys.stderr,
        )
        include_active = False
    specs = expanded_catalog(count, include_active=include_active)
    jobs = []
    for index, spec in enumerate(specs):
        job = build_job(spec, data_dir, index)
        target = jobs_dir / f"{job['id']}.json"
        temp = target.with_suffix(".json.tmp")
        temp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(target)
        jobs.append(job)
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description="生成/清理本地占位任务数据")
    parser.add_argument(
        "--count",
        type=int,
        default=len(CATALOG),
        help=f"占位任务数量（默认 {len(CATALOG)}）",
    )
    parser.add_argument("--clean", action="store_true", help="只清理占位任务，不生成新任务")
    parser.add_argument("--no-active", action="store_true", help="不生成 running / queued 占位任务")
    parser.add_argument(
        "--data-dir",
        default=str(Path(os.getenv("H3_ROOT", str(PROJECT_ROOT))) / "data"),
        help="数据目录，默认 <项目根>/data（遵循 H3_ROOT）",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    if not data_dir.is_dir():
        parser.error(f"数据目录不存在：{data_dir}")
    if args.count < 1:
        parser.error("--count 必须大于 0")

    removed = clean(data_dir)
    if args.clean:
        print(f"已清理 {removed} 条占位任务及其素材。")
        print("重启服务后，这些记录才会从界面消失。")
        return 0

    jobs = seed(data_dir, args.count, include_active=not args.no_active)
    print(f"已清理 {removed} 条旧占位任务，新生成 {len(jobs)} 条：")
    for job in sorted(jobs, key=lambda item: item["created_at"], reverse=True):
        media = job["request"]["media_type"]
        extra = f" · {job['request'].get('workflow_name')}" if job["request"].get("workflow_name") else ""
        print(f"  {job['status']:<9} {media:<5} {job['title']}{extra}")
    print()
    print(f"数据目录：{data_dir}")
    print("任务列表在服务启动时从磁盘加载，重启服务后即可在界面看到。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
