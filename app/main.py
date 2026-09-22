from __future__ import annotations

import asyncio
import json
import math
import mimetypes
import re
import secrets
import shutil
import subprocess
import time
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path
from typing import Annotated, Any, AsyncIterator, Literal
from urllib.parse import quote, urlparse

import httpx
from cryptography.exceptions import InvalidTag
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .engine import create_engine, probe_node
from .jobs import JobManager, JobStore, ROOT_FOLDER_ID, TERMINAL_STATES, UNFILED_FOLDER_ID, create_video_preview, output_file_name, output_file_stem, utc_now
from .local_state import LocalStateStore
from .music_prompts import MUSIC3_ARRANGEMENT_SYSTEM_PROMPT, MUSIC3_LYRICS_SYSTEM_PROMPT
from .nodes import NodeRegistry
from .peering import is_loopback_client, local_peer_addresses, normalize_peer_url
from .prompts import FL2VA_SYSTEM_PROMPT
from .ref2va_prompts import REF2VA_SYSTEM_PROMPT
from .tts_prompts import TTS_SYSTEM_PROMPT
from .runninghub import assign_media_fields, normalize_parameters, output_media_type
from .settings import settings


ExecutionMode = Literal["native", "turbo-lora", "dual-sampling", "h3-sa", "vdn-h3", "h3-nsfw", "digital-human", "tts", "music3"]
ModelVariant = Literal["fl2va-fp8", "ref2va-fp8", "music3-int8"]
TaskType = Literal["generation", "upscale"]
UpscaleCategory = Literal["real", "anime", "3d"]
UpscaleScale = int


settings.ensure_directories()
store = JobStore(settings.jobs_dir)
node_registry = NodeRegistry(settings.data_dir / "config.db")
local_state = LocalStateStore(settings.data_dir / "config.db")
manager = JobManager(
    store,
    lambda node: create_engine(settings, node),
    nodes=node_registry.configs(),
    health_probe=(
        probe_node
        if settings.engine_backend == "comfyui" and not settings.fake_engine
        else None
    ),
    health_interval=node_registry.health_interval(),
    node_runtime_update=node_registry.update_runtime,
)
proxy_poll_tasks: dict[str, asyncio.Task] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    manager.start()
    for job_id in store.active_proxy_job_ids():
        schedule_proxy_poll(job_id)
    try:
        yield
    finally:
        tasks = list(proxy_poll_tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        proxy_poll_tasks.clear()
        manager.stop()


app = FastAPI(
    title="MiniMax H3 and Music3 API",
    version="6.0.0",
    description="MiniMax H3 video and MiniMax Music3 audio generation through ComfyUI and RunningHub API nodes.",
    lifespan=lifespan,
)


@app.middleware("http")
async def desktop_network_boundary(request: Request, call_next):
    if settings.desktop_mode and not is_loopback_client(request.client.host if request.client else None):
        path = request.url.path
        remote_allowed = (
            path == "/AGENT.md"
            or path == "/docs"
            or path == "/openapi.json"
            or path == "/api/v1/peering/pair"
            or path == "/api/v1/peering/revoke"
            or path.startswith("/api/v1/peering/export/")
            or path.startswith("/api/v1/peering/proxy/")
        )
        if not remote_allowed:
            return JSONResponse(status_code=403, content={"detail": "桌面应用仅允许本机访问普通接口"})
    return await call_next(request)


class GenerationPatch(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    title: str | None = Field(None, max_length=120)
    prompt: str | None = Field(None, max_length=12000)
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    steps: int | None = None
    seed: int | None = Field(None, ge=0, le=2**31 - 1)
    model_variant: ModelVariant | None = None
    execution_mode: ExecutionMode | None = None
    task_type: TaskType | None = None
    upscale_category: UpscaleCategory | None = None
    upscale_scale: UpscaleScale | None = None
    auto_upscale: bool | None = None
    auto_upscale_category: UpscaleCategory | None = None
    auto_upscale_scale: UpscaleScale | None = None
    sa_tau: float | None = Field(None, ge=0, le=4)
    sa_start_percent: float | None = Field(None, ge=0, le=1)
    sa_end_percent: float | None = Field(None, ge=0, le=1)
    sa_min_tokens: int | None = Field(None, ge=0, le=1048576)
    sa_int8_qk: bool | None = None
    sa_int8_pv: bool | None = None
    sa_sink_conditioning: Literal["exact_kv", "exact_kv_and_rows", "off"] | None = None
    sa_morton: bool | None = None
    sa_morton_curve: Literal["3d", "2d_frame"] | None = None
    sa_dense_blocks: str | None = Field(None, max_length=256)
    sa_stage2_denoise: float | None = Field(None, ge=0, le=1)
    lyrics: str | None = Field(None, max_length=12000)
    comfy_node: str | None = Field(None, min_length=1, max_length=200)
    runninghub_parameters: dict[str, object] | None = None


class RegenerateRequest(BaseModel):
    folder_id: str | None = Field(default=None, max_length=100)


class AssetFolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class AssetFolderUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class AssetFolderMove(BaseModel):
    job_ids: list[str] = Field(min_length=1, max_length=500)
    folder_id: str | None = Field(default=None, max_length=100)


class GenerationRename(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class OptimizePromptRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prompt: str = Field(min_length=2, max_length=12000)
    base_url: str = Field(min_length=8, max_length=500)
    model: str = Field(min_length=1, max_length=200)
    references: list[dict[str, str]] = Field(default_factory=list, max_length=15)
    duration: float = Field(default=5, ge=1, le=300)
    model_variant: Literal["fl2va-fp8", "ref2va-fp8"] = "fl2va-fp8"
    execution_mode: Literal["native", "h3-sa", "vdn-h3", "tts"] = "native"


class MusicAssistRequest(BaseModel):
    task: Literal["arrangement", "lyrics"]
    prompt: str = Field(min_length=2, max_length=12000)
    lyrics: str = Field(default="", max_length=12000)
    duration: float = Field(default=60, ge=1, le=300)
    base_url: str = Field(min_length=8, max_length=500)
    model: str = Field(min_length=1, max_length=200)


class ComfyNodeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(default="", max_length=500)
    provider: Literal["comfyui", "runninghub"] = "comfyui"
    api_key: str = Field(default="", max_length=2000)
    workflow_url: str = Field(default="", max_length=500)
    max_concurrency: int = Field(default=1, ge=1, le=64)


class ComfyNodeUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(default="", max_length=500)
    enabled: bool = True
    provider: Literal["comfyui", "runninghub"] | None = None
    api_key: str | None = Field(default=None, max_length=2000)
    workflow_url: str | None = Field(default=None, max_length=500)
    max_concurrency: int | None = Field(default=None, ge=1, le=64)


class ComfySettingsUpdate(BaseModel):
    health_interval_seconds: float = Field(ge=5, le=3600)


class AISettingsUpdate(BaseModel):
    enabled: bool = False
    base_url: str = Field(default="", max_length=500)
    model: str = Field(default="", max_length=200)
    api_key: str | None = Field(default=None, max_length=2000)
    clear_api_key: bool = False


class PeeringSettingsUpdate(BaseModel):
    enabled: bool | None = None
    machine_name: str | None = Field(default=None, max_length=80)


class GeneralSettingsUpdate(BaseModel):
    show_runtime_logs: bool | None = None
    show_peering: bool | None = None
    backup_outputs: bool | None = None
    remote_disconnect_policy: Literal["encrypt", "delete"] | None = None
    remote_records_key: str | None = Field(default=None, min_length=8, max_length=256)


class AssetArtifactsDeleteRequest(BaseModel):
    job_ids: list[str] = Field(min_length=1, max_length=200)


class LocalAssetsDeleteRequest(BaseModel):
    asset_ids: list[str] = Field(min_length=1, max_length=500)


class PeerAssetUnlockRequest(BaseModel):
    owner_device_id: str = Field(min_length=8, max_length=100)
    records_key: str = Field(min_length=8, max_length=256)


class PeerConnectRequest(BaseModel):
    address: str = Field(min_length=8, max_length=500)
    code: str = Field(min_length=6, max_length=6)


class PeerPairRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=100)
    device_name: str = Field(min_length=1, max_length=80)
    address: str = Field(min_length=8, max_length=500)
    code: str = Field(min_length=6, max_length=6)
    callback_token: str = Field(min_length=20, max_length=200)
    records_key: str = Field(min_length=8, max_length=256)


class IncognitoAuthRequest(BaseModel):
    code: str = Field(min_length=1, max_length=200)


async def authorize(authorization: Annotated[str | None, Header()] = None) -> None:
    if not settings.api_key:
        return
    if authorization != f"Bearer {settings.api_key}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 API Key")


def align_frames(duration: float) -> int:
    frames = max(5, round(duration * 24))
    while frames % 17 != 5:
        frames += 1
    return frames


def validate_generation(
    width: int,
    height: int,
    duration: float,
    steps: int,
    execution_mode: str = "native",
) -> None:
    if execution_mode == "upscale":
        return
    if execution_mode == "music3":
        if not 1 <= duration <= 300:
            raise HTTPException(status_code=422, detail="Music3 时长范围为 1–300 秒")
        if steps != 30:
            raise HTTPException(status_code=422, detail="Music3 固定使用 30 步")
        return
    if execution_mode == "tts":
        if width != 32 or height != 32:
            raise HTTPException(status_code=422, detail="H3 TTS 固定使用 32×32 画面尺寸")
        if not 1 <= duration <= 15:
            raise HTTPException(status_code=422, detail="H3 TTS 时长范围为 1–15 秒")
        if not 4 <= steps <= 50:
            raise HTTPException(status_code=422, detail="H3 TTS 采样步数范围为 4–50")
        return
    if execution_mode == "dual-sampling":
        if not 1 <= duration <= 15:
            raise HTTPException(status_code=422, detail="双采工作流时长范围为 1–15 秒")
        if not 4 <= steps <= 50:
            raise HTTPException(status_code=422, detail="双采工作流采样步数范围为 4–50")
        if width % 32 or height % 32 or width < 352 or height < 352:
            raise HTTPException(status_code=422, detail="宽高必须是 32 的倍数，且不低于 352×352")
        return
    if execution_mode == "h3-sa" and steps != 8:
        raise HTTPException(status_code=422, detail="H3 SA 固定使用 8 步 LoRA 采样")
    if execution_mode == "vdn-h3" and not 8 <= steps <= 50:
        raise HTTPException(status_code=422, detail="VDN-H3 步数范围为 8–50")
    if width % 32 or height % 32 or width < 352 or height < 352:
        raise HTTPException(status_code=422, detail="宽高必须是 32 的倍数，且不低于 352×352")
    max_duration = 300 if execution_mode == "h3-sa" else 15
    if not 1 <= duration <= max_duration:
        duration_label = "H3 SA" if execution_mode == "h3-sa" else "VDN-H3" if execution_mode == "vdn-h3" else "H3"
        raise HTTPException(status_code=422, detail=f"{duration_label} 时长范围为 1–{max_duration:g} 秒")
    if execution_mode == "turbo-lora" and steps != 8:
        raise HTTPException(status_code=422, detail="8-step LoRA 加速模式固定使用 8 步")
    if execution_mode == "digital-human" and steps != 20:
        raise HTTPException(status_code=422, detail="数字人模式固定使用 20 步")
    if execution_mode not in {"turbo-lora", "digital-human"} and not 4 <= steps <= 50:
        raise HTTPException(status_code=422, detail="采样步数范围为 4–50")


def validate_sa_parameters(
    *,
    tau: float = 1.3,
    start_percent: float = 0.2,
    end_percent: float = 0.9,
    min_tokens: int = 4096,
    stage2_denoise: float = 0.35,
) -> None:
    values = (tau, start_percent, end_percent, stage2_denoise)
    if not all(math.isfinite(float(value)) for value in values):
        raise HTTPException(status_code=422, detail="H3 SA 参数必须为有限数值")
    if not 0 <= tau <= 4:
        raise HTTPException(status_code=422, detail="H3 SA tau 范围为 0–4")
    if not 0 <= start_percent < end_percent <= 1:
        raise HTTPException(status_code=422, detail="H3 SA 加速起止比例必须满足 0 ≤ start < end ≤ 1")
    if not 0 <= stage2_denoise <= 1:
        raise HTTPException(status_code=422, detail="H3 SA 二阶段 denoise 范围为 0–1")
    if type(min_tokens) is not int or not 0 <= min_tokens <= 1048576:
        raise HTTPException(status_code=422, detail="H3 SA 最小 token 数范围为 0–1048576")


def classify_upload(upload: UploadFile, allow_file: bool = False) -> str:
    content_type = (upload.content_type or "").lower()
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    if content_type.startswith("audio/"):
        return "audio"
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
        return "image"
    if suffix in {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}:
        return "video"
    if suffix in {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus"}:
        return "audio"
    if allow_file:
        return "file"
    raise HTTPException(status_code=422, detail=f"不支持的素材类型：{upload.filename}")


def remote_output_suffix(response: httpx.Response, media_type: str) -> str:
    disposition = response.headers.get("content-disposition", "")
    if disposition:
        message = Message()
        message["content-disposition"] = disposition
        filename = message.get_filename() or ""
        suffix = Path(filename).suffix.lower()
        if 1 < len(suffix) <= 10 and suffix[1:].isalnum():
            return suffix

    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    known_suffixes = {
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/x-matroska": ".mkv",
        "audio/flac": ".flac",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/ogg": ".ogg",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    if content_type in known_suffixes:
        return known_suffixes[content_type]
    guessed = mimetypes.guess_extension(content_type, strict=False) if content_type else None
    if guessed and 1 < len(guessed) <= 10 and guessed[1:].isalnum():
        return guessed.lower()
    return {"video": ".mp4", "audio": ".flac", "image": ".png"}.get(media_type, ".bin")


def validate_references(
    model_variant: str,
    kinds: list[str],
    execution_mode: str = "native",
) -> None:
    if execution_mode == "upscale":
        if len(kinds) != 1 or kinds[0] not in {"image", "video"}:
            raise HTTPException(status_code=422, detail="超分任务需要上传 1 张图片或 1 段视频")
        return
    if execution_mode == "music3":
        if kinds:
            raise HTTPException(status_code=422, detail="Music3 不使用参考素材")
        return
    if execution_mode == "tts":
        if model_variant != "ref2va-fp8" or any(kind != "audio" for kind in kinds):
            raise HTTPException(status_code=422, detail="H3 TTS 仅支持 0 至 3 段音频参考")
        if len(kinds) > 3:
            raise HTTPException(status_code=422, detail="H3 TTS 最多支持 3 段音频参考")
        return
    if execution_mode == "dual-sampling":
        if model_variant != "ref2va-fp8" or not kinds or any(kind != "image" for kind in kinds):
            raise HTTPException(status_code=422, detail="双采工作流需要至少一张图片参考")
        if len(kinds) > 9:
            raise HTTPException(status_code=422, detail="双采工作流最多支持 9 张图片参考")
        return
    if not kinds:
        raise HTTPException(status_code=422, detail="至少需要一份参考素材")
    if execution_mode == "digital-human":
        if model_variant != "ref2va-fp8" or sorted(kinds) != ["audio", "image"]:
            raise HTTPException(status_code=422, detail="数字人模式需要上传 1 张人物图片和 1 段驱动音频")
        return
    counts = {kind: kinds.count(kind) for kind in ("image", "video", "audio")}
    if model_variant == "fl2va-fp8":
        if any(kind != "image" for kind in kinds) or not 1 <= counts["image"] <= 2:
            raise HTTPException(status_code=422, detail="FL2VA 仅支持 1 张首帧，或首帧/尾帧两张图片")
        return
    if counts["image"] > 9 or counts["video"] > 3 or counts["audio"] > 3:
        raise HTTPException(status_code=422, detail="Ref2VA 最多支持 9 张图片、3 段视频和 3 段音频")


def validate_execution_mode(
    execution_mode: str,
    model_variant: str,
    incognito: bool,
) -> None:
    if execution_mode == "upscale":
        return
    if execution_mode == "music3":
        if model_variant != "music3-int8":
            raise HTTPException(status_code=422, detail="Music3 执行方案仅支持 Music3 INT8")
        return
    if model_variant == "music3-int8":
        raise HTTPException(status_code=422, detail="Music3 INT8 必须使用 Music3 执行方案")
    if execution_mode in {"native", "turbo-lora"}:
        return
    if execution_mode == "h3-sa":
        if model_variant not in {"fl2va-fp8", "ref2va-fp8"}:
            raise HTTPException(status_code=422, detail="H3 SA 仅支持 FL2VA FP8 或 Ref2VA FP8")
        return
    if execution_mode == "vdn-h3":
        if model_variant not in {"fl2va-fp8", "ref2va-fp8"}:
            raise HTTPException(status_code=422, detail="VDN-H3 仅支持 FL2VA FP8 或 Ref2VA FP8")
        return
    if execution_mode == "dual-sampling":
        if model_variant != "ref2va-fp8":
            raise HTTPException(status_code=422, detail="双采工作流仅支持 Ref2VA FP8")
        return
    if execution_mode == "digital-human":
        if model_variant != "ref2va-fp8":
            raise HTTPException(status_code=422, detail="数字人模式仅支持 Ref2VA FP8")
        return
    if execution_mode == "tts":
        if model_variant != "ref2va-fp8":
            raise HTTPException(status_code=422, detail="H3 TTS 模式仅支持 Ref2VA FP8")
        return
    if execution_mode != "h3-nsfw":
        raise HTTPException(status_code=422, detail="不支持的执行方案")
    if not incognito:
        raise HTTPException(status_code=403, detail="H3 NSFW 模式仅限无痕模式")
    if model_variant != "ref2va-fp8":
        raise HTTPException(status_code=422, detail="H3 NSFW 模式仅支持 Ref2VA FP8")


def validate_upscale_parameters(
    task_type: str,
    category: str,
    scale: int,
) -> None:
    if task_type != "upscale":
        return
    if category not in {"real", "anime", "3d"}:
        raise HTTPException(status_code=422, detail="超分分类必须为 real、anime 或 3d")
    if scale not in {2, 4}:
        raise HTTPException(status_code=422, detail="超分倍率必须为 2 或 4")


def validate_auto_upscale_parameters(
    enabled: bool,
    task_type: str,
    model_variant: str,
    execution_mode: str,
    category: str,
    scale: int,
    provider: str = "comfyui",
) -> None:
    if not enabled:
        return
    if provider != "comfyui":
        raise HTTPException(status_code=422, detail="自动超分需要使用 ComfyUI 节点")
    if task_type != "generation" or execution_mode in {"music3", "tts"} or model_variant == "music3-int8":
        raise HTTPException(status_code=422, detail="当前任务类型不支持生成后自动超分")
    if not category or scale not in {2, 4}:
        raise HTTPException(status_code=422, detail="自动超分参数无效")
    validate_upscale_parameters("upscale", category, scale)


def probe_media(path: Path, max_duration: float | None = 15.1) -> tuple[float, bool]:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        payload = json.loads(result.stdout)
        durations = [float(payload.get("format", {}).get("duration") or 0)]
        durations.extend(float(item.get("duration") or 0) for item in payload.get("streams", []))
        duration = max(durations)
        has_audio = any(item.get("codec_type") == "audio" for item in payload.get("streams", []))
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        raise HTTPException(status_code=422, detail=f"无法读取媒体时长：{path.name}") from exc
    if duration <= 0:
        raise HTTPException(status_code=422, detail=f"无法读取媒体时长：{path.name}")
    if max_duration is not None and (duration < 1 or duration > max_duration):
        raise HTTPException(status_code=422, detail=f"视频和音频素材时长必须为 1–15 秒：{path.name}")
    return duration, has_audio


def probe_video_fps(path: Path) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=r_frame_rate",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        raw = result.stdout.strip()
        if "/" in raw:
            numerator, denominator = raw.split("/", 1)
            fps = float(numerator) / float(denominator)
        else:
            fps = float(raw)
        if math.isfinite(fps) and 1 <= fps <= 120:
            return fps
    except (OSError, ValueError, ZeroDivisionError, subprocess.SubprocessError):
        pass
    return 24.0


async def save_upload(upload: UploadFile, destination: Path) -> int:
    written = 0
    limit = settings.max_upload_mb * 1024 * 1024
    with destination.open("wb") as target:
        while chunk := await upload.read(1024 * 1024):
            written += len(chunk)
            if written > limit:
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"单个文件不能超过 {settings.max_upload_mb} MB")
            target.write(chunk)
    return written


@app.get("/health")
async def health():
    nodes = manager.nodes_public()
    online = sum(1 for node in nodes if node["healthy"])
    return {
        "status": "ok",
        "engine": "fake" if settings.fake_engine else settings.engine_backend,
        "gpu": settings.gpu_label,
        "queue_depth": manager.queue_depth,
        "nodes": nodes,
        "online_nodes": online,
        "parallel_capacity": manager.parallel_capacity,
        "health_interval_seconds": manager.health_interval,
        "revision": store.revision,
    }


def reload_comfy_nodes() -> None:
    try:
        manager.reconfigure(node_registry.configs(), node_registry.health_interval())
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def runninghub_runtime_values(profile: dict[str, object]) -> dict[str, object]:
    allowed = {
        "workflow_name",
        "runninghub_schema",
        "runninghub_schema_updated_at",
        "account_balance_coins",
        "account_balance_money",
        "account_currency",
        "account_current_tasks",
        "account_api_type",
        "account_error",
    }
    return {key: value for key, value in profile.items() if key in allowed}


async def identify_runninghub_node(config) -> dict[str, object]:
    profile = await asyncio.to_thread(probe_node, config)
    if not isinstance(profile, dict):
        raise HTTPException(status_code=422, detail="RunningHub 工作流参数识别失败")
    if profile.get("workflow_error"):
        raise HTTPException(status_code=422, detail=str(profile["workflow_error"]))
    if not isinstance(profile.get("runninghub_schema"), dict):
        raise HTTPException(status_code=422, detail="RunningHub 工作流未返回参数定义")
    return profile


def prepare_runninghub_request(
    workflow_profile: dict[str, object],
    prompt: str,
    parameters: object,
    manifest: list[dict[str, object]],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    schema = workflow_profile.get("runninghub_schema")
    if not isinstance(schema, dict):
        raise HTTPException(status_code=422, detail="RunningHub 工作流参数定义不可用")
    if not isinstance(parameters, dict):
        raise HTTPException(status_code=422, detail="runninghub_parameters 必须是对象")
    try:
        primary_text_key = str(schema.get("primary_text_key") or "")
        submitted_parameters = dict(parameters)
        if primary_text_key and prompt:
            submitted_parameters[primary_text_key] = prompt
        normalized = normalize_parameters(schema, submitted_parameters)
        assigned_manifest = assign_media_fields(schema, manifest)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return normalized, assigned_manifest


@app.get("/api/v1/comfy/nodes", dependencies=[Depends(authorize)])
async def list_comfy_nodes():
    statuses = {item["id"]: item for item in manager.nodes_public()}
    nodes = []
    for row in node_registry.list(enabled_only=False):
        status_data = statuses.get(row["id"], {})
        nodes.append({**row, **status_data})
    return {
        "data": nodes,
        "health_interval_seconds": node_registry.health_interval(),
    }


@app.post("/api/v1/comfy/nodes", status_code=201, dependencies=[Depends(authorize)])
async def create_comfy_node(payload: ComfyNodeCreate):
    node_id = f"node-{secrets.token_hex(4)}"
    try:
        profile: dict[str, object] = {}
        config = node_registry.build_config(
            node_id,
            payload.name,
            payload.url,
            payload.provider,
            payload.api_key,
            payload.workflow_url,
            payload.max_concurrency,
        )
        if payload.provider == "runninghub":
            profile = await identify_runninghub_node(config)
        node = node_registry.create(
            node_id,
            payload.name,
            payload.url,
            payload.provider,
            payload.api_key,
            payload.workflow_url,
            payload.max_concurrency,
            str(profile.get("workflow_name") or ""),
            profile.get("runninghub_schema")
            if isinstance(profile.get("runninghub_schema"), dict)
            else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if profile:
        node_registry.update_runtime(node_id, runninghub_runtime_values(profile))
        node = node_registry.get(node_id) or node
    reload_comfy_nodes()
    return node


@app.patch("/api/v1/comfy/nodes/{node_id}", dependencies=[Depends(authorize)])
async def update_comfy_node(node_id: str, payload: ComfyNodeUpdate):
    existing = node_registry.get(node_id)
    if not existing:
        raise HTTPException(status_code=404, detail="推理节点不存在")
    provider = payload.provider or existing["provider"]
    workflow_url = (
        payload.workflow_url
        if payload.workflow_url is not None
        else existing["workflow_url"]
    )
    max_concurrency = (
        payload.max_concurrency
        if payload.max_concurrency is not None
        else int(existing["max_concurrency"])
    )
    node_url = payload.url.strip() or existing["url"]
    config_changed = any(
        (
            existing["url"] != node_url.rstrip("/"),
            existing["provider"] != provider,
            existing["workflow_url"] != workflow_url,
            int(existing["max_concurrency"]) != max_concurrency,
            bool((payload.api_key or "").strip()),
        )
    )
    if (config_changed or not payload.enabled) and manager.node_in_use(node_id):
        raise HTTPException(status_code=409, detail="节点正在执行任务或存在定向排队任务")
    try:
        current_config = node_registry.config(node_id)
        effective_api_key = payload.api_key
        if (
            provider == existing["provider"]
            and not (payload.api_key or "").strip()
            and current_config
        ):
            effective_api_key = current_config.api_key
        profile: dict[str, object] = {}
        config = node_registry.build_config(
            node_id,
            payload.name,
            node_url,
            provider,
            effective_api_key or "",
            workflow_url,
            max_concurrency,
        )
        if provider == "runninghub":
            profile = await identify_runninghub_node(config)
        node = node_registry.update(
            node_id,
            payload.name,
            node_url,
            payload.enabled,
            provider,
            payload.api_key,
            workflow_url,
            max_concurrency,
            str(profile.get("workflow_name") or ""),
            profile.get("runninghub_schema")
            if isinstance(profile.get("runninghub_schema"), dict)
            else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    runtime_values = runninghub_runtime_values(profile)
    if provider != "runninghub":
        runtime_values = {
            "workflow_name": "",
            "runninghub_schema": None,
            "account_balance_coins": None,
            "account_balance_money": None,
            "account_currency": "",
            "account_current_tasks": None,
            "account_api_type": "",
            "account_error": "",
            "last_call_consumed_coins": None,
            "last_call_consumed_money": None,
            "last_call_cost_at": "",
            "last_call_job_id": "",
        }
    if runtime_values:
        node_registry.update_runtime(node_id, runtime_values)
        node = node_registry.get(node_id) or node
    reload_comfy_nodes()
    return node


@app.delete("/api/v1/comfy/nodes/{node_id}", dependencies=[Depends(authorize)])
async def delete_comfy_node(node_id: str):
    existing = node_registry.get(node_id)
    if not existing:
        raise HTTPException(status_code=404, detail="推理节点不存在")
    if manager.node_in_use(node_id):
        raise HTTPException(status_code=409, detail="节点正在执行任务或存在定向排队任务")
    node_registry.delete(node_id)
    reload_comfy_nodes()
    return {"deleted": True}


@app.patch("/api/v1/comfy/settings", dependencies=[Depends(authorize)])
async def update_comfy_settings(payload: ComfySettingsUpdate):
    seconds = node_registry.set_health_interval(payload.health_interval_seconds)
    reload_comfy_nodes()
    return {"health_interval_seconds": seconds}


@app.get("/api/v1/settings/general", dependencies=[Depends(authorize)])
async def get_general_settings():
    result = local_state.general_settings()
    result["health_interval_seconds"] = node_registry.health_interval()
    return result


@app.patch("/api/v1/settings/general", dependencies=[Depends(authorize)])
async def update_general_settings(payload: GeneralSettingsUpdate):
    try:
        result = local_state.update_general_settings(**payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {**result, "health_interval_seconds": node_registry.health_interval()}


@app.get("/api/v1/settings/ai", dependencies=[Depends(authorize)])
async def get_ai_settings():
    return local_state.ai_config()


@app.patch("/api/v1/settings/ai", dependencies=[Depends(authorize)])
async def update_ai_settings(payload: AISettingsUpdate):
    try:
        return local_state.update_ai_config(
            enabled=payload.enabled,
            base_url=payload.base_url,
            model=payload.model,
            api_key=payload.api_key,
            clear_api_key=payload.clear_api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def peer_bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    prefix = "Bearer "
    return authorization[len(prefix) :].strip() if authorization.startswith(prefix) else ""


def authenticate_peer_request(request: Request, allow_disabled: bool = False) -> dict[str, Any]:
    peer = local_state.authenticate_peer(peer_bearer_token(request))
    if not peer:
        raise HTTPException(status_code=401, detail="互联设备授权无效")
    if not allow_disabled and not local_state.sharing_enabled:
        raise HTTPException(status_code=403, detail="本机互联功能未开启")
    return peer


def peer_status_payload() -> dict[str, Any]:
    revision, events = local_state.events_since(0)
    addresses = local_peer_addresses(settings.port)
    return {
        "device_id": local_state.device_id,
        "machine_name": local_state.machine_name,
        "sharing_enabled": local_state.sharing_enabled,
        "pairing_code": local_state.pairing_code(),
        "pairing_expires_in": 30 - int(time.time()) % 30,
        "addresses": addresses,
        "address": addresses[0],
        "peers": local_state.peers(),
        "revision": revision,
        "events": events[-20:],
    }


def _safe_local_data_path(raw_path: str) -> Path | None:
    try:
        path = Path(raw_path).resolve()
        path.relative_to(settings.data_dir.resolve())
        return path
    except (OSError, ValueError):
        return None


def _protected_asset_metadata(peer_device_id: str | None = None) -> list[dict[str, Any]]:
    records = local_state.plain_remote_records("job_snapshot_meta", peer_device_id)
    values: list[dict[str, Any]] = []
    for record in records:
        value = record.get("value")
        if not isinstance(value, dict) or not value.get("job_id"):
            continue
        values.append({**value, "_meta_record_id": record["record_id"]})
    return values


def restore_peer_records(peer_device_id: str, records_key: str = "") -> None:
    for metadata in _protected_asset_metadata(peer_device_id):
        key_id = str(metadata.get("key_id") or "")
        if not key_id:
            continue
        unlocked_key = local_state.unlocked_peer_key(peer_device_id, key_id)
        if not unlocked_key and records_key:
            try:
                if secrets.compare_digest(local_state.records_key_id(records_key), key_id):
                    unlocked_key = records_key
            except ValueError:
                unlocked_key = None
        if not unlocked_key:
            peer = local_state.peer(peer_device_id, include_secrets=True)
            peer_key = str((peer or {}).get("records_key") or "")
            try:
                if peer_key and secrets.compare_digest(local_state.records_key_id(peer_key), key_id):
                    unlocked_key = peer_key
            except ValueError:
                unlocked_key = None
        if not unlocked_key:
            continue

        snapshot_record_id = str(
            metadata.get("snapshot_record_id")
            or f"job-snapshot:{peer_device_id}:{metadata['job_id']}"
        )
        try:
            snapshot = local_state.read_peer_encrypted_record(
                snapshot_record_id,
                peer_device_id,
                unlocked_key,
            )
        except (InvalidTag, UnicodeDecodeError, ValueError):
            continue
        if not isinstance(snapshot, dict) or not snapshot.get("id"):
            continue
        if metadata.get("asset_deleted"):
            retained_files = []
            for item in snapshot.get("_protected_files", []) or []:
                if item.get("kind") in {"result", "sidecar"}:
                    encrypted_path = _safe_local_data_path(str(item.get("encrypted_path") or ""))
                    if encrypted_path:
                        encrypted_path.unlink(missing_ok=True)
                    continue
                retained_files.append(item)
            snapshot["_protected_files"] = retained_files
            snapshot["result_path"] = None
            snapshot["result_url"] = None
            snapshot["asset_deleted"] = True
            snapshot["asset_deleted_at"] = metadata.get("asset_deleted_at") or utc_now()
        if store.get(str(snapshot["id"])):
            for item in snapshot.get("_protected_files", []) or []:
                encrypted_path = _safe_local_data_path(str(item.get("encrypted_path") or ""))
                if encrypted_path:
                    encrypted_path.unlink(missing_ok=True)
            local_state.delete_remote_record(snapshot_record_id)
            local_state.delete_remote_record(str(metadata["_meta_record_id"]))
            continue
        restored = store.restore_protected_job(
            snapshot,
            lambda payload, nonce: local_state.decrypt_peer_bytes(
                payload, nonce, peer_device_id, unlocked_key
            ),
        )
        local_state.delete_remote_record(snapshot_record_id)
        local_state.delete_remote_record(str(metadata["_meta_record_id"]))
        if (
            restored.get("request", {}).get("remote_proxy")
            and restored.get("status") not in TERMINAL_STATES
        ):
            schedule_proxy_poll(str(restored["id"]))


async def protect_peer_state(peer_device_id: str) -> None:
    peer = local_state.peer(peer_device_id, include_secrets=True)
    peer_jobs = store.jobs_for_peer(peer_device_id)
    for job in peer_jobs:
        job_id = str(job.get("id") or "")
        if not job_id or job.get("status") in TERMINAL_STATES:
            continue
        if job.get("request", {}).get("remote_proxy"):
            task = proxy_poll_tasks.get(job_id)
            if task and not task.done():
                task.cancel()
            continue
        manager.cancel(job_id)

    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        pending = [
            job
            for job in store.jobs_for_peer(peer_device_id)
            if job.get("status") not in TERMINAL_STATES
            and not job.get("request", {}).get("remote_proxy")
        ]
        if not pending:
            break
        await asyncio.sleep(0.1)

    pending_ids = {
        str(job.get("id") or "")
        for job in store.jobs_for_peer(peer_device_id)
        if job.get("status") not in TERMINAL_STATES
        and not job.get("request", {}).get("remote_proxy")
    }
    if pending_ids:
        for job_id in sorted(pending_ids):
            store.update(
                job_id,
                status="cancelled",
                stage="互联已断开，任务已取消",
                progress=0,
                cancel_requested=True,
            )

    delete = local_state.remote_disconnect_policy() == "delete"
    records_key = str((peer or {}).get("records_key") or "")
    if delete or not records_key:
        store.protect_peer_jobs(peer_device_id, delete=True)
        local_state.delete_remote_records(peer_device_id)
        return

    key_id = local_state.records_key_id(records_key)
    local_state.encrypt_remote_records(peer_device_id)
    snapshots = store.protect_peer_jobs(
        peer_device_id,
        delete=False,
        encrypt_bytes=lambda payload: local_state.encrypt_peer_bytes(
            payload, peer_device_id, records_key
        ),
    )
    for snapshot in snapshots:
        snapshot_record_id = f"job-snapshot:{peer_device_id}:{snapshot['id']}"
        protected_files = snapshot.get("_protected_files", []) or []
        result_files = [
            dict(item)
            for item in protected_files
            if item.get("kind") in {"result", "sidecar"}
        ]
        result_file = next(
            (item for item in result_files if item.get("kind") == "result"),
            None,
        )
        media_type = str(snapshot.get("request", {}).get("media_type") or "file")
        original_path = str((result_file or {}).get("original_path") or "")
        local_state.put_peer_encrypted_record(
            record_id=snapshot_record_id,
            peer_device_id=peer_device_id,
            record_type="job_snapshot",
            value=snapshot,
            records_key=records_key,
        )
        local_state.put_remote_record(
            record_id=f"job-snapshot-meta:{peer_device_id}:{snapshot['id']}",
            peer_device_id=peer_device_id,
            record_type="job_snapshot_meta",
            value={
                "job_id": str(snapshot["id"]),
                "snapshot_record_id": snapshot_record_id,
                "title": str(snapshot.get("title") or snapshot["id"]),
                "owner_device_id": peer_device_id,
                "owner_name": str((peer or {}).get("name") or peer_device_id),
                "created_at": str(snapshot.get("created_at") or utc_now()),
                "media_type": media_type,
                "file_name": Path(original_path).name if original_path else "",
                "key_id": key_id,
                "result_files": result_files,
                "asset_deleted": bool(snapshot.get("asset_deleted")),
            },
            encrypted=False,
        )


@app.get("/api/v1/peering/status", dependencies=[Depends(authorize)])
async def get_peering_status(since: Annotated[int, Query(ge=0)] = 0):
    revision, events = local_state.events_since(since)
    payload = peer_status_payload()
    payload["revision"] = revision
    payload["events"] = events
    return payload


@app.patch("/api/v1/peering/settings", dependencies=[Depends(authorize)])
async def update_peering_settings(payload: PeeringSettingsUpdate):
    try:
        local_state.update_desktop_settings(
            machine_name=payload.machine_name,
            sharing_enabled=payload.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return peer_status_payload()


@app.post("/api/v1/peering/connect", dependencies=[Depends(authorize)])
async def connect_peer(payload: PeerConnectRequest):
    if not local_state.sharing_enabled:
        raise HTTPException(status_code=403, detail="请先开启本机互联功能")
    try:
        address = normalize_peer_url(payload.address)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    callback_token = secrets.token_urlsafe(32)
    body = {
        "device_id": local_state.device_id,
        "device_name": local_state.machine_name,
        "address": local_peer_addresses(settings.port)[0],
        "code": payload.code,
        "callback_token": callback_token,
        "records_key": local_state.get_setting("remote_records_key"),
    }
    try:
        timeout = httpx.Timeout(15, connect=5)
        async with httpx.AsyncClient(base_url=address, timeout=timeout, trust_env=False) as client:
            response = await client.post("/api/v1/peering/pair", json=body)
            if response.status_code >= 400:
                try:
                    detail = response.json().get("detail")
                except (ValueError, AttributeError):
                    detail = None
                raise HTTPException(status_code=422, detail=detail or "远端设备拒绝了互联请求")
            result = response.json()
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"无法连接远端设备：{exc}") from exc
    try:
        remote_address = normalize_peer_url(str(result.get("address") or address))
        remote_records_key = str(result["records_key"])
        restore_peer_records(str(result["device_id"]), remote_records_key)
        peer = local_state.upsert_peer(
            device_id=str(result["device_id"]),
            name=str(result.get("machine_name") or "H3 Studio"),
            base_url=remote_address,
            access_token=str(result["access_token"]),
            inbound_token=callback_token,
            records_key=remote_records_key,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="远端设备返回的互联信息无效") from exc
    return {"connected": True, "peer": peer, "status": peer_status_payload()}


@app.post("/api/v1/peering/pair")
async def pair_peer(payload: PeerPairRequest):
    if not local_state.sharing_enabled:
        raise HTTPException(status_code=403, detail="远端设备未开启互联功能")
    if not local_state.verify_pairing_code(payload.code):
        raise HTTPException(status_code=401, detail="本机互联密钥已失效")
    try:
        address = normalize_peer_url(payload.address)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    access_token = secrets.token_urlsafe(32)
    restore_peer_records(payload.device_id, payload.records_key)
    local_state.upsert_peer(
        device_id=payload.device_id,
        name=payload.device_name,
        base_url=address,
        access_token=payload.callback_token,
        inbound_token=access_token,
        records_key=payload.records_key,
    )
    return {
        "device_id": local_state.device_id,
        "machine_name": local_state.machine_name,
        "address": local_peer_addresses(settings.port)[0],
        "access_token": access_token,
        "records_key": local_state.get_setting("remote_records_key"),
    }


@app.delete("/api/v1/peering/peers/{device_id}", dependencies=[Depends(authorize)])
async def revoke_peer(device_id: str):
    peer = local_state.peer(device_id, include_secrets=True)
    if not peer:
        raise HTTPException(status_code=404, detail="互联设备不存在")
    remote_revoked = False
    try:
        timeout = httpx.Timeout(10, connect=4)
        async with httpx.AsyncClient(base_url=peer["base_url"], timeout=timeout, trust_env=False) as client:
            response = await client.post(
                "/api/v1/peering/revoke",
                headers={"Authorization": f"Bearer {peer['access_token']}"},
            )
            remote_revoked = response.is_success
    except httpx.HTTPError:
        remote_revoked = False
    await protect_peer_state(device_id)
    local_state.delete_peer(device_id)
    return {"revoked": True, "remote_revoked": remote_revoked, "status": peer_status_payload()}


@app.post("/api/v1/peering/revoke")
async def revoke_peer_from_remote(request: Request):
    peer = authenticate_peer_request(request, allow_disabled=True)
    await protect_peer_state(peer["device_id"])
    local_state.delete_peer(peer["device_id"])
    return {"revoked": True}


def public_peer_asset(job: dict[str, Any], owner_name: str, owner_id: str) -> dict[str, Any]:
    job["owner_name"] = owner_name
    job["owner_device_id"] = owner_id
    job["source"] = {"device_id": owner_id, "name": owner_name}
    return job


def public_local_job(item: dict[str, Any]) -> dict[str, Any]:
    item["owner_name"] = local_state.machine_name
    item["owner_device_id"] = local_state.device_id
    item["peer_asset"] = False
    item["source"] = {"device_id": local_state.device_id, "name": local_state.machine_name}
    return item


def normalize_folder_id(folder_id: str | None) -> str | None:
    value = str(folder_id or "").strip()
    if not value or value == UNFILED_FOLDER_ID:
        return None
    if not local_state.asset_folder(value):
        raise HTTPException(status_code=404, detail="素材文件夹不存在")
    return value


def local_job_is_owned(job: dict[str, Any]) -> bool:
    request_data = job.get("request", {})
    if request_data.get("remote_proxy"):
        return False
    owner_device_id = str(
        job.get("owner_device_id")
        or request_data.get("proxy_source_device_id")
        or local_state.device_id
    )
    return owner_device_id == local_state.device_id


def local_folder_is_owned(folder_id: str) -> bool:
    return bool(local_state.asset_folder(folder_id))


def job_folder_name(folder_id: str | None) -> str:
    return str(local_state.asset_folder(folder_id or "").get("name") or "") if folder_id else ""


def prepare_job_output_name(job: dict[str, Any]) -> dict[str, Any]:
    job["folder_name"] = job_folder_name(job.get("folder_id"))
    job["output_stem"] = output_file_stem(job)
    return job


def rename_job_output(job: dict[str, Any], name: str) -> dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=422, detail="文件名不能为空")
    safe_stem = re.sub(r"[^\w\-.\u0080-\uffff]+", "_", clean_name, flags=re.UNICODE).strip("._")
    if not safe_stem:
        raise HTTPException(status_code=422, detail="文件名无有效字符")
    old_path = Path(str(job.get("result_path") or ""))
    if not old_path.is_file():
        raise HTTPException(status_code=410, detail="生成产物不存在")
    new_path = old_path.with_name(f"{safe_stem}{old_path.suffix.lower()}")
    preview_path = old_path.with_name(f"{old_path.stem}.preview.jpg")
    new_preview_path = new_path.with_name(f"{new_path.stem}.preview.jpg")
    if new_path != old_path and new_path.exists():
        raise HTTPException(status_code=409, detail="同名文件已存在")
    old_path.rename(new_path)
    sidecar = old_path.with_suffix(".json")
    if sidecar.is_file():
        sidecar.rename(new_path.with_suffix(".json"))
    if preview_path.is_file():
        preview_path.rename(new_preview_path)
    return store.update(
        str(job["id"]),
        title=clean_name,
        output_stem=safe_stem,
        result_path=str(new_path),
        preview_path=str(new_preview_path) if new_preview_path.is_file() else None,
        preview_url=f"/api/v1/generations/{job['id']}/preview" if new_preview_path.is_file() else None,
        event_message="生成文件名已更新",
    )


def folder_filter_value(folder_id: str | None) -> str | None:
    value = str(folder_id or "").strip()
    if not value or value == "all":
        return None
    if value == UNFILED_FOLDER_ID:
        return UNFILED_FOLDER_ID
    if value == ROOT_FOLDER_ID:
        return ROOT_FOLDER_ID
    return normalize_folder_id(value)


def public_remote_job(item: dict[str, Any]) -> dict[str, Any]:
    item.pop("folder_id", None)
    item.pop("preview_path", None)
    item.pop("preview_url", None)
    return item


@app.get("/api/v1/asset-folders", dependencies=[Depends(authorize)])
async def list_asset_folders():
    counts = store.folder_counts()
    folders = [
        {**folder, "count": counts.get(str(folder["id"]), 0)}
        for folder in local_state.asset_folders()
    ]
    return {
        "data": folders,
        "unfiled": {"id": UNFILED_FOLDER_ID, "name": "未分组", "count": counts.get(None, 0)},
        "total": sum(counts.values()),
    }


@app.post("/api/v1/asset-folders", status_code=201, dependencies=[Depends(authorize)])
async def create_asset_folder(payload: AssetFolderCreate):
    try:
        return local_state.create_asset_folder(payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/v1/asset-folders/{folder_id}", dependencies=[Depends(authorize)])
async def rename_asset_folder(folder_id: str, payload: AssetFolderUpdate):
    try:
        return local_state.rename_asset_folder(folder_id, payload.name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="素材文件夹不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/asset-folders/move", dependencies=[Depends(authorize)])
async def move_asset_folder_items(payload: AssetFolderMove):
    folder_id = normalize_folder_id(payload.folder_id)
    jobs: list[dict[str, Any]] = []
    for job_id in payload.job_ids:
        if job_id.startswith("peer::"):
            raise HTTPException(status_code=403, detail="远端素材保持只读")
        job = store.get(job_id)
        if not job or job.get("request", {}).get("incognito") or job.get("request", {}).get("remote_proxy"):
            raise HTTPException(status_code=404, detail="本机素材不存在")
        jobs.append(job)
    for job in jobs:
        store.update(job["id"], folder_id=folder_id, event_message="素材文件夹已更新")
    return {"moved": [job["id"] for job in jobs], "folder_id": folder_id}


@app.delete("/api/v1/asset-folders/{folder_id}", dependencies=[Depends(authorize)])
async def delete_asset_folder(folder_id: str):
    if not local_folder_is_owned(folder_id):
        raise HTTPException(status_code=404, detail="素材文件夹不存在")
    jobs = store.jobs_in_folder(folder_id)
    if any(not local_job_is_owned(job) for job in jobs):
        raise HTTPException(status_code=403, detail="文件夹包含非本机创建的素材，无法删除")
    active = [job["id"] for job in jobs if job.get("status") not in TERMINAL_STATES]
    if active:
        raise HTTPException(
            status_code=409,
            detail="文件夹包含进行中任务，请先取消或等待任务结束",
        )
    for job in jobs:
        await delete_generation(job["id"])
    local_state.delete_asset_folder(folder_id)
    return {"id": folder_id, "status": "deleted", "deleted_jobs": [job["id"] for job in jobs]}


def proxy_remote_job_id(job: dict[str, Any]) -> str:
    request_data = job.get("request") or {}
    return str(
        job.get("proxy_remote_job_id")
        or request_data.get("proxy_remote_job_id")
        or ""
    )


def peer_proxy_relationships(peer_device_id: str) -> tuple[dict[str, str], set[str]]:
    local_proxy_jobs: dict[str, str] = {}
    local_execution_ids: set[str] = set()
    for job in store.jobs_for_peer(peer_device_id):
        request_data = job.get("request") or {}
        if request_data.get("remote_proxy") and job.get("proxy_peer_id") == peer_device_id:
            remote_id = proxy_remote_job_id(job)
            if remote_id:
                local_proxy_jobs[remote_id] = str(job.get("id") or "")
        if request_data.get("proxy_source_device_id") == peer_device_id:
            local_execution_ids.add(str(job.get("id") or ""))
    return local_proxy_jobs, local_execution_ids


def peer_job_is_duplicate(
    item: dict[str, Any],
    local_proxy_jobs: dict[str, str],
    local_execution_ids: set[str],
) -> bool:
    remote_id = str(item.get("id") or "")
    if remote_id and remote_id in local_proxy_jobs:
        return True
    request_data = item.get("request") or {}
    return bool(
        (item.get("remote_proxy") or request_data.get("remote_proxy"))
        and proxy_remote_job_id(item) in local_execution_ids
    )


def public_remote_node(node: dict[str, Any], peer: dict[str, Any]) -> dict[str, Any]:
    opaque_node_id = str(node.get("proxy_node_id") or local_state.opaque_node_id(str(node.get("name") or "node")))
    return {
        "id": f"peer::{peer['device_id']}::{opaque_node_id}",
        "name": str(node.get("name") or "远程节点"),
        "healthy": bool(node.get("healthy")),
        "busy": bool(node.get("busy")),
        "capacity": int(node.get("capacity") or 1),
        "running_count": int(node.get("running_count") or 0),
        "queue_depth": int(node.get("queue_depth") or 0),
        "owner_name": peer.get("name") or peer.get("device_id"),
        "owner_device_id": peer.get("device_id"),
        "remote_proxy": True,
        "proxy_node_id": str(node.get("proxy_node_id") or ""),
        "source": {
            "device_id": peer.get("device_id"),
            "name": peer.get("name") or peer.get("device_id"),
        },
    }


def exported_proxy_nodes() -> list[dict[str, Any]]:
    return [
        {
            "name": node.get("name"),
            "healthy": node.get("healthy"),
            "busy": node.get("busy"),
            "capacity": node.get("capacity"),
            "running_count": node.get("running_count"),
            "queue_depth": node.get("queue_depth"),
            "proxy_node_id": local_state.opaque_node_id(
                str(node.get("id") or node.get("name") or "node")
            ),
        }
        for node in manager.nodes_public()
    ]


def parse_remote_node_id(node_id: str) -> tuple[str, str] | None:
    parts = node_id.split("::", 2)
    if len(parts) != 3 or parts[0] != "peer" or not parts[1] or not parts[2]:
        return None
    return parts[1], parts[2]


def resolve_remote_node(peer_device_id: str, opaque_id: str) -> str | None:
    peer = local_state.peer(peer_device_id, include_secrets=True)
    if not peer:
        return None
    for node in manager.nodes_public():
        if local_state.opaque_node_id(str(node.get("id") or node.get("name") or "node")) == opaque_id:
            return str(node.get("id"))
    return None


@app.get("/api/v1/peering/export/assets")
async def export_peer_assets(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    query: Annotated[str | None, Query(max_length=200)] = None,
):
    authenticate_peer_request(request)
    items, total, revision = store.list_with_revision(
        page, page_size, status="completed", query=query, scope="normal"
    )
    items = [public_remote_job(item) for item in items]
    return {"data": items, "page": page, "page_size": page_size, "total": total, "pages": max(1, math.ceil(total / page_size)), "store_revision": revision}


@app.get("/api/v1/peering/export/generations")
async def export_peer_generations(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    query: Annotated[str | None, Query(max_length=200)] = None,
):
    authenticate_peer_request(request)
    items, total, revision = store.list_with_revision(
        page, page_size, status=status_filter, query=query, scope="normal"
    )
    items = [public_remote_job(item) for item in items]
    return {
        "data": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": max(1, math.ceil(total / page_size)),
        "store_revision": revision,
    }


@app.get("/api/v1/peering/export/generations/{job_id}")
async def export_peer_generation(request: Request, job_id: str):
    peer = authenticate_peer_request(request)
    job = store.get(job_id)
    if not job or job.get("request", {}).get("incognito"):
        raise HTTPException(status_code=404, detail="共享任务不存在")
    local_state.mark_seen(peer["device_id"])
    return public_peer_asset(public_remote_job(store.public(job_id) or {}), local_state.machine_name, local_state.device_id)


@app.get("/api/v1/peering/export/generations/{job_id}/result")
async def export_peer_generation_result(request: Request, job_id: str):
    return await export_peer_asset_result(request, job_id)


@app.get("/api/v1/peering/export/nodes")
async def export_peer_nodes(request: Request):
    authenticate_peer_request(request)
    return {"data": exported_proxy_nodes(), "revision": manager.revision}


@app.get("/api/v1/peering/export/logs")
async def export_peer_logs(request: Request, limit: Annotated[int, Query(ge=1, le=500)] = 100):
    peer = authenticate_peer_request(request)
    logs = store.logs(limit)
    for item in logs:
        item["owner_name"] = local_state.machine_name
        item["owner_device_id"] = local_state.device_id
        item["remote"] = False
    local_owner = {"device_id": local_state.device_id, "name": local_state.machine_name}
    queue = []
    for item in manager.queue_snapshot():
        assigned = item.get("assigned_node") or {}
        item["assigned_node"] = {
            "name": str(assigned.get("name") or "推理节点"),
            "healthy": bool(assigned.get("healthy", True)),
            "busy": True,
            "owner_name": local_state.machine_name,
            "owner_device_id": local_state.device_id,
        }
        queue.append(item)
    return {
        "data": logs,
        "queue": queue,
        "nodes": [public_remote_node(node, local_owner) for node in manager.nodes_public()],
        "revision": f"{store.revision}:{manager.revision}",
        "conversation_revision": str(store.revision),
        "source": {"device_id": local_state.device_id, "name": local_state.machine_name},
        "peer_device_id": peer["device_id"],
    }


@app.get("/api/v1/peering/export/events")
async def export_peer_events(
    request: Request,
    since: Annotated[int, Query(ge=0)] = 0,
):
    authenticate_peer_request(request)
    store_cursor = event_store_cursor(request.headers.get("last-event-id", ""), since)

    async def events() -> AsyncIterator[str]:
        nonlocal store_cursor
        last_revision = ""
        idle_ticks = 0
        yield "retry: 3000\n\n"
        while not await request.is_disconnected():
            payload = local_event_snapshot(store_cursor)
            payload["nodes"] = exported_proxy_nodes()
            revision = str(payload["revision"])
            if revision != last_revision:
                yield (
                    f"id: {revision}\n"
                    "event: snapshot\n"
                    f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                )
                store_cursor = int(payload["store_revision"])
                last_revision = revision
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks >= 15:
                    yield ": keep-alive\n\n"
                    idle_ticks = 0
            await asyncio.sleep(1)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/v1/peering/proxy/generations")
async def proxy_generation_from_peer(request: Request):
    peer = authenticate_peer_request(request)
    proxy_node_id = request.headers.get("x-h3-proxy-node", "").strip()
    if not proxy_node_id:
        raise HTTPException(status_code=422, detail="远程代理节点标识缺失")
    target_node = next(
        (
            str(node.get("id"))
            for node in manager.nodes_public()
            if secrets.compare_digest(
                local_state.opaque_node_id(str(node.get("id") or node.get("name") or "node")),
                proxy_node_id,
            )
        ),
        None,
    )
    if not target_node:
        raise HTTPException(status_code=404, detail="远程代理节点不存在")
    form = await request.form()
    data: dict[str, str] = {}
    files: list[tuple[str, tuple[str, bytes, str]]] = []
    for key, value in form.multi_items():
        if isinstance(value, UploadFile):
            content = await value.read()
            files.append(
                (
                    key,
                    (
                        value.filename or "reference",
                        content,
                        value.content_type or "application/octet-stream",
                    ),
                )
            )
        else:
            data[key] = str(value)
    proxy_records_key = data.pop("proxy_records_key", "")
    if proxy_records_key:
        try:
            local_state.update_peer_records_key(peer["device_id"], proxy_records_key)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    data["comfy_node"] = target_node
    data["proxy_source_device_id"] = peer["device_id"]
    headers: dict[str, str] = {}
    if settings.api_key:
        headers["authorization"] = f"Bearer {settings.api_key}"
    if request.headers.get("x-h3-incognito-code"):
        headers["x-h3-incognito-code"] = request.headers["x-h3-incognito-code"]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://local", trust_env=False) as client:
        response = await client.post(
            "/api/v1/generations",
            data=data,
            files=files,
            headers=headers,
        )
    return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("content-type"))


@app.post("/api/v1/peering/proxy/generations/{job_id}/cancel")
async def cancel_proxy_generation_from_peer(request: Request, job_id: str):
    peer = authenticate_peer_request(request)
    job = store.get(job_id)
    if not job or job.get("request", {}).get("incognito"):
        raise HTTPException(status_code=404, detail="共享任务不存在")
    if job.get("request", {}).get("proxy_source_device_id") != peer["device_id"]:
        raise HTTPException(status_code=403, detail="无权操作该共享任务")
    if not manager.cancel(job_id):
        raise HTTPException(status_code=409, detail="任务已结束，无法取消")
    return store.public(job_id, manager.queue_position(job_id))


@app.delete("/api/v1/peering/proxy/generations/{job_id}")
async def delete_proxy_generation_from_peer(request: Request, job_id: str):
    peer = authenticate_peer_request(request)
    job = store.get(job_id)
    if not job or job.get("request", {}).get("incognito"):
        raise HTTPException(status_code=404, detail="共享任务不存在")
    if job.get("request", {}).get("proxy_source_device_id") != peer["device_id"]:
        raise HTTPException(status_code=403, detail="无权删除该共享任务")
    if job.get("status") not in TERMINAL_STATES:
        raise HTTPException(status_code=409, detail="请先取消任务，任务结束后再删除")
    manager.remove(job_id)
    store.delete(job_id)
    return {"id": job_id, "status": "deleted"}


@app.get("/api/v1/peering/export/assets/{job_id}")
async def export_peer_asset(request: Request, job_id: str):
    peer = authenticate_peer_request(request)
    job = store.get(job_id)
    if not job or job.get("status") != "completed" or job.get("request", {}).get("incognito"):
        raise HTTPException(status_code=404, detail="共享素材不存在")
    local_state.mark_seen(peer["device_id"])
    return public_peer_asset(store.public(job_id) or {}, local_state.machine_name, local_state.device_id)


@app.get("/api/v1/peering/export/assets/{job_id}/result")
async def export_peer_asset_result(request: Request, job_id: str):
    authenticate_peer_request(request)
    job = store.get(job_id)
    if not job or job.get("status") != "completed" or job.get("request", {}).get("incognito"):
        raise HTTPException(status_code=404, detail="共享素材不存在")
    path = Path(job.get("result_path") or "")
    if not path.is_file():
        raise HTTPException(status_code=410, detail="共享产物已不存在")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@app.get("/api/v1/peering/export/assets/{job_id}/references/{index}")
async def export_peer_asset_reference(request: Request, job_id: str, index: int):
    authenticate_peer_request(request)
    job = store.get(job_id)
    if not job or job.get("request", {}).get("incognito"):
        raise HTTPException(status_code=404, detail="共享素材不存在")
    input_paths = job.get("input_paths", [])
    references = job.get("request", {}).get("references", [])
    if index < 0 or index >= len(input_paths) or index >= len(references):
        raise HTTPException(status_code=404, detail="参考素材不存在")
    path = Path(input_paths[index]).resolve()
    upload_root = (settings.uploads_dir / job_id).resolve()
    try:
        path.relative_to(upload_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="参考素材不存在") from exc
    if not path.is_file():
        raise HTTPException(status_code=410, detail="参考素材已不存在")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


def decorate_remote_asset(item: dict[str, Any], peer: dict[str, Any]) -> dict[str, Any]:
    source_job_id = str(item.get("id") or "")
    peer_id = str(peer["device_id"])
    item["source_job_id"] = source_job_id
    item["id"] = f"peer::{peer_id}::{source_job_id}"
    item["peer_asset"] = True
    item["owner_name"] = peer.get("name") or peer_id
    item["owner_device_id"] = peer_id
    item["detail_url"] = f"/api/v1/peering/library/{peer_id}/assets/{source_job_id}"
    item["result_url"] = f"/api/v1/peering/library/{peer_id}/assets/{source_job_id}/result"
    for index, reference in enumerate(item.get("request", {}).get("references", [])):
        reference["url"] = (
            f"/api/v1/peering/library/{peer_id}/assets/{source_job_id}/references/{index}"
        )
    return item


async def proxy_peer_response(peer: dict[str, Any], path: str):
    client = httpx.AsyncClient(
        base_url=peer["base_url"],
        headers={"Authorization": f"Bearer {peer['access_token']}"},
        timeout=httpx.Timeout(60, connect=10),
        trust_env=False,
    )
    try:
        response = await client.send(client.build_request("GET", path), stream=True)
        if response.status_code >= 400:
            detail = (await response.aread()).decode("utf-8", errors="replace")[:500]
            await response.aclose()
            await client.aclose()
            raise HTTPException(status_code=response.status_code, detail=detail or "远端素材不可用")
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"无法读取远端素材：{exc}") from exc

    async def stream():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    headers = {}
    for key in ("content-disposition", "content-length"):
        if response.headers.get(key):
            headers[key] = response.headers[key]
    return StreamingResponse(stream(), media_type=response.headers.get("content-type"), headers=headers)


@app.get("/api/v1/peering/library", dependencies=[Depends(authorize)])
async def list_shared_library(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    query: Annotated[str | None, Query(max_length=200)] = None,
    folder_id: Annotated[str | None, Query(max_length=100)] = None,
):
    resolved_folder_id = folder_filter_value(folder_id)
    local_folder_id = UNFILED_FOLDER_ID if resolved_folder_id == ROOT_FOLDER_ID else resolved_folder_id
    local_items, local_total, local_revision = store.list_with_revision(
        page,
        page_size,
        status=status_filter,
        query=query,
        scope="normal",
        folder_id=local_folder_id,
    )
    for item in local_items:
        public_local_job(item)

    remote_items: list[dict[str, Any]] = []
    remote_total = 0
    remote_pages = 1
    peer_errors: list[dict[str, str]] = []
    if resolved_folder_id is None and local_state.sharing_enabled and status_filter in {None, "", "completed"}:
        for peer in local_state.peers(include_secrets=True):
            try:
                timeout = httpx.Timeout(20, connect=5)
                async with httpx.AsyncClient(
                    base_url=peer["base_url"],
                    headers={"Authorization": f"Bearer {peer['access_token']}"},
                    timeout=timeout,
                    trust_env=False,
                ) as client:
                    response = await client.get(
                        "/api/v1/peering/export/assets",
                        params={"page": page, "page_size": page_size, "query": query or ""},
                    )
                    response.raise_for_status()
                    payload = response.json()
                local_proxy_jobs, local_execution_ids = peer_proxy_relationships(
                    peer["device_id"]
                )
                remote_data = list(payload.get("data", []))
                visible_remote_data = [
                    item
                    for item in remote_data
                    if not peer_job_is_duplicate(
                        item, local_proxy_jobs, local_execution_ids
                    )
                ]
                remote_total += max(
                    0,
                    int(payload.get("total") or 0)
                    - (len(remote_data) - len(visible_remote_data)),
                )
                remote_pages = max(remote_pages, int(payload.get("pages") or 1))
                remote_items.extend(
                    decorate_remote_asset(item, peer) for item in visible_remote_data
                )
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                peer_errors.append({"device_id": peer["device_id"], "name": peer["name"], "error": str(exc)})

    items = sorted(
        [*local_items, *remote_items],
        key=lambda item: item.get("created_at") or "",
        reverse=True,
    )
    return {
        "data": items,
        "page": page,
        "page_size": page_size,
        "total": local_total + remote_total,
        "pages": max(1, math.ceil(local_total / page_size), remote_pages),
        "store_revision": local_revision,
        "peer_errors": peer_errors,
    }


async def peer_json(peer: dict[str, Any], path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    timeout = httpx.Timeout(20, connect=5)
    async with httpx.AsyncClient(
        base_url=peer["base_url"],
        headers={"Authorization": f"Bearer {peer['access_token']}"},
        timeout=timeout,
        trust_env=False,
    ) as client:
        response = await client.get(path, params=params or {})
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("远端返回数据格式无效")
    return payload


def event_store_cursor(last_event_id: str, since: int) -> int:
    try:
        return int(last_event_id.split(":", 1)[0]) if last_event_id else since
    except ValueError:
        return since


def local_event_snapshot(store_cursor: int) -> dict[str, Any]:
    delta = store.changes_since(store_cursor)
    for job in delta["jobs"]:
        position = manager.queue_position(job["id"])
        if position is not None and job["status"] == "queued":
            job["queue_position"] = position
    return {
        "revision": f"{delta['revision']}:{manager.revision}",
        "store_revision": delta["revision"],
        "jobs": delta["jobs"],
        "deleted_job_ids": delta["deleted_job_ids"],
        "reset_required": delta["reset_required"],
        "logs": store.logs(100),
        "queue": manager.queue_snapshot(),
        "nodes": manager.nodes_public(),
    }


def decorate_peer_event_snapshot(payload: dict[str, Any], peer: dict[str, Any]) -> dict[str, Any]:
    peer_id = str(peer["device_id"])
    proxy_jobs, local_execution_ids = peer_proxy_relationships(peer_id)
    duplicate_peer_job_ids = {
        str(item.get("id") or "")
        for item in [*payload.get("jobs", []), *payload.get("queue", [])]
        if peer_job_is_duplicate(item, proxy_jobs, local_execution_ids)
    }
    jobs = []
    for item in payload.get("jobs", []):
        if not peer_job_is_duplicate(item, proxy_jobs, local_execution_ids):
            jobs.append(decorate_remote_asset(deepcopy(item), peer))
    queue = []
    for item in payload.get("queue", []):
        if not peer_job_is_duplicate(item, proxy_jobs, local_execution_ids):
            queue.append(decorate_remote_asset(deepcopy(item), peer))
    logs = []
    for item in payload.get("logs", []):
        log = deepcopy(item)
        remote_job_id = str(log.get("job_id") or "")
        if remote_job_id in duplicate_peer_job_ids:
            continue
        if remote_job_id:
            log["job_id"] = proxy_jobs.get(
                remote_job_id, f"peer::{peer_id}::{remote_job_id}"
            )
        log.update(
            owner_name=peer.get("name") or peer_id,
            owner_device_id=peer_id,
            remote=True,
        )
        logs.append(log)
    deleted_job_ids = [
        f"peer::{peer_id}::{job_id}"
        for job_id in payload.get("deleted_job_ids", [])
        if str(job_id) not in proxy_jobs
    ]
    return {
        "peer_device_id": peer_id,
        "peer_name": peer.get("name") or peer_id,
        "revision": str(payload.get("revision") or ""),
        "store_revision": int(payload.get("store_revision") or 0),
        "jobs": jobs,
        "deleted_job_ids": deleted_job_ids,
        "reset_required": bool(payload.get("reset_required")),
        "logs": logs,
        "queue": queue,
        "nodes": [
            public_remote_node(deepcopy(node), peer)
            for node in payload.get("nodes", [])
        ],
    }


async def relay_peer_events(
    peer: dict[str, Any],
    event_queue: asyncio.Queue[tuple[str, dict[str, Any]]],
    stop_event: asyncio.Event,
) -> None:
    last_event_id = ""
    while not stop_event.is_set():
        headers = {"Authorization": f"Bearer {peer['access_token']}"}
        if last_event_id:
            headers["Last-Event-ID"] = last_event_id
        try:
            timeout = httpx.Timeout(connect=5, read=None, write=10, pool=5)
            async with httpx.AsyncClient(
                base_url=peer["base_url"],
                headers=headers,
                timeout=timeout,
                trust_env=False,
            ) as client:
                async with client.stream("GET", "/api/v1/peering/export/events") as response:
                    response.raise_for_status()
                    event_type = "message"
                    event_id = ""
                    data_lines: list[str] = []
                    async for line in response.aiter_lines():
                        if stop_event.is_set():
                            return
                        if not line:
                            if event_type == "snapshot" and data_lines:
                                payload = json.loads("\n".join(data_lines))
                                await event_queue.put(
                                    ("peer_snapshot", decorate_peer_event_snapshot(payload, peer))
                                )
                                if event_id:
                                    last_event_id = event_id
                            event_type = "message"
                            event_id = ""
                            data_lines = []
                            continue
                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                        elif line.startswith("id:"):
                            event_id = line[3:].strip()
                        elif line.startswith("data:"):
                            data_lines.append(line[5:].lstrip())
        except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError):
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=3)
            except TimeoutError:
                pass


def peer_error(peer: dict[str, Any], exc: Exception) -> dict[str, str]:
    return {
        "device_id": str(peer.get("device_id") or ""),
        "name": str(peer.get("name") or ""),
        "error": str(exc),
    }


@app.get("/api/v1/peering/nodes", dependencies=[Depends(authorize)])
async def list_shared_nodes():
    local_nodes = []
    for item in manager.nodes_public():
        local_nodes.append({
            **item,
            "owner_name": local_state.machine_name,
            "owner_device_id": local_state.device_id,
            "remote_proxy": False,
            "source": {"device_id": local_state.device_id, "name": local_state.machine_name},
        })
    remote_nodes: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    if local_state.sharing_enabled:
        for peer in local_state.peers(include_secrets=True):
            try:
                payload = await peer_json(peer, "/api/v1/peering/export/nodes")
                remote_nodes.extend(public_remote_node(node, peer) for node in payload.get("data", []))
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                errors.append(peer_error(peer, exc))
    return {"data": [*local_nodes, *remote_nodes], "peer_errors": errors}


@app.get("/api/v1/peering/conversations", dependencies=[Depends(authorize)])
async def list_shared_conversations(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    query: Annotated[str | None, Query(max_length=200)] = None,
    device_ids: Annotated[str | None, Query(max_length=2000)] = None,
):
    requested_devices = {value.strip() for value in (device_ids or "").split(",") if value.strip()}
    local_id = local_state.device_id
    include_local = not requested_devices or local_id in requested_devices
    local_items: list[dict[str, Any]] = []
    local_total = 0
    local_revision = store.revision
    if include_local:
        local_items, local_total, local_revision = store.list_with_revision(
            1, 100, status=status_filter, query=query, scope="normal"
        )
        for item in local_items:
            public_local_job(item)

    remote_items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    remote_revisions: list[str] = []
    peers = local_state.peers(include_secrets=True)
    for peer in peers:
        if requested_devices and peer["device_id"] not in requested_devices:
            continue
        try:
            payload = await peer_json(
                peer,
                "/api/v1/peering/export/generations",
                {"page": 1, "page_size": 100, "status": status_filter or "", "query": query or ""},
            )
            remote_revisions.append(
                f"{peer['device_id']}:{int(payload.get('store_revision') or 0)}"
            )
            local_proxy_jobs, local_execution_ids = peer_proxy_relationships(
                peer["device_id"]
            )
            for item in payload.get("data", []):
                if peer_job_is_duplicate(
                    item, local_proxy_jobs, local_execution_ids
                ):
                    continue
                decorated = decorate_remote_asset(item, peer)
                remote_items.append(decorated)
                local_state.put_remote_record(
                    record_id=f"job:{peer['device_id']}:{item.get('id')}",
                    peer_device_id=peer["device_id"],
                    record_type="job",
                    value=decorated,
                    encrypted=False,
                )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            errors.append(peer_error(peer, exc))

    all_items = sorted([*local_items, *remote_items], key=lambda item: item.get("created_at") or "", reverse=True)
    total = len(all_items)
    start = (page - 1) * page_size
    return {
        "data": all_items[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": max(1, math.ceil(total / page_size)),
        "store_revision": local_revision,
        "conversation_revision": "|".join([f"{local_id}:{local_revision}", *sorted(remote_revisions)]),
        "peer_errors": errors,
        "devices": [
            {"device_id": local_id, "name": local_state.machine_name, "local": True},
            *[{"device_id": peer["device_id"], "name": peer["name"], "local": False} for peer in peers],
        ],
    }


@app.get("/api/v1/peering/runtime", dependencies=[Depends(authorize)])
async def shared_runtime(limit: Annotated[int, Query(ge=1, le=500)] = 100):
    local_logs = store.logs(limit)
    for item in local_logs:
        item.update({"owner_name": local_state.machine_name, "owner_device_id": local_state.device_id, "remote": False})
    nodes_payload = await list_shared_nodes()
    logs = list(local_logs)
    errors = list(nodes_payload.get("peer_errors", []))
    conversation_revisions = [f"{local_state.device_id}:{store.revision}"]
    if local_state.sharing_enabled:
        for peer in local_state.peers(include_secrets=True):
            try:
                payload = await peer_json(peer, "/api/v1/peering/export/logs", {"limit": limit})
                for item in payload.get("data", []):
                    item.update({"owner_name": peer["name"], "owner_device_id": peer["device_id"], "remote": True})
                logs.extend(payload.get("data", []))
                conversation_revisions.append(
                    f"{peer['device_id']}:{int(payload.get('conversation_revision') or payload.get('store_revision') or 0)}"
                )
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                errors.append(peer_error(peer, exc))
    logs.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    return {
        "logs": logs[:limit],
        "queue": manager.queue_snapshot(),
        "nodes": nodes_payload.get("data", []),
        "peer_errors": errors,
        "revision": f"{store.revision}:{manager.revision}",
        "conversation_revision": "|".join(sorted(conversation_revisions)),
    }


@app.get("/api/v1/peering/library/{peer_id}/assets/{job_id}", dependencies=[Depends(authorize)])
async def get_shared_asset(peer_id: str, job_id: str):
    peer = local_state.peer(peer_id, include_secrets=True)
    if not peer:
        raise HTTPException(status_code=404, detail="互联设备不存在")
    try:
        timeout = httpx.Timeout(20, connect=5)
        async with httpx.AsyncClient(
            base_url=peer["base_url"],
            headers={"Authorization": f"Bearer {peer['access_token']}"},
            timeout=timeout,
            trust_env=False,
        ) as client:
            response = await client.get(f"/api/v1/peering/export/assets/{job_id}")
            response.raise_for_status()
            return decorate_remote_asset(response.json(), peer)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail="远端素材不存在") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"无法读取远端素材：{exc}") from exc


@app.get("/api/v1/peering/library/{peer_id}/assets/{job_id}/result", dependencies=[Depends(authorize)])
async def get_shared_asset_result(peer_id: str, job_id: str):
    peer = local_state.peer(peer_id, include_secrets=True)
    if not peer:
        raise HTTPException(status_code=404, detail="互联设备不存在")
    return await proxy_peer_response(peer, f"/api/v1/peering/export/assets/{job_id}/result")


@app.get("/api/v1/peering/library/{peer_id}/assets/{job_id}/references/{index}", dependencies=[Depends(authorize)])
async def get_shared_asset_reference(peer_id: str, job_id: str, index: int):
    peer = local_state.peer(peer_id, include_secrets=True)
    if not peer:
        raise HTTPException(status_code=404, detail="互联设备不存在")
    return await proxy_peer_response(peer, f"/api/v1/peering/export/assets/{job_id}/references/{index}")


@app.post("/api/v1/incognito/authorize", dependencies=[Depends(authorize)])
async def authorize_incognito(payload: IncognitoAuthRequest):
    if not secrets.compare_digest(payload.code, settings.incognito_code):
        raise HTTPException(status_code=403, detail="授权码不正确")
    return {"authorized": True}


@app.get("/api/v1/generations", dependencies=[Depends(authorize)])
async def list_generations(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[
        Literal["queued", "running", "completed", "failed", "cancelled"] | None,
        Query(alias="status"),
    ] = None,
    query: Annotated[str | None, Query(max_length=200)] = None,
    include_incognito: Annotated[bool, Query()] = False,
    scope: Annotated[Literal["normal", "incognito", "all"] | None, Query()] = None,
    folder_id: Annotated[str | None, Query(max_length=100)] = None,
):
    resolved_folder_id = folder_filter_value(folder_id) if scope != "incognito" else None
    if scope == "incognito" and folder_id:
        raise HTTPException(status_code=422, detail="无痕任务不支持文件夹")
    items, total, snapshot_revision = store.list_with_revision(
        page,
        page_size,
        status_filter,
        query,
        include_incognito=include_incognito,
        scope=scope,
        folder_id=resolved_folder_id,
    )
    for item in items:
        position = manager.queue_position(item["id"])
        if position is not None and item["status"] == "queued":
            item["queue_position"] = position
    return {
        "data": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": max(1, math.ceil(total / page_size)),
        "store_revision": snapshot_revision,
    }


@app.post("/api/v1/generations", status_code=202, dependencies=[Depends(authorize)])
async def create_generation(
    prompt: Annotated[str, Form(description="Generation prompt or primary workflow text input.")] = "",
    reference_manifest: Annotated[
        str, Form(description="Ordered image, video, and audio reference manifest.")
    ] = "[]",
    references: Annotated[
        list[UploadFile], File(description="Reference files in manifest order.")
    ] = [],
    model_variant: Annotated[ModelVariant, Form()] = "fl2va-fp8",
    execution_mode: Annotated[ExecutionMode, Form()] = "native",
    task_type: Annotated[TaskType, Form()] = "generation",
    upscale_category: Annotated[UpscaleCategory, Form()] = "real",
    upscale_scale: Annotated[UpscaleScale, Form()] = 2,
    auto_upscale: Annotated[bool, Form()] = False,
    auto_upscale_category: Annotated[UpscaleCategory, Form()] = "real",
    auto_upscale_scale: Annotated[UpscaleScale, Form()] = 2,
    width: Annotated[int, Form()] = 832,
    height: Annotated[int, Form()] = 480,
    duration: Annotated[float, Form()] = 5,
    steps: Annotated[int, Form()] = 10,
    sa_tau: Annotated[float, Form(ge=0, le=4)] = 1.3,
    sa_start_percent: Annotated[float, Form(ge=0, le=1)] = 0.2,
    sa_end_percent: Annotated[float, Form(ge=0, le=1)] = 0.9,
    sa_min_tokens: Annotated[int, Form(ge=0, le=1048576)] = 4096,
    sa_int8_qk: Annotated[bool, Form()] = True,
    sa_int8_pv: Annotated[bool, Form()] = True,
    sa_sink_conditioning: Annotated[Literal["exact_kv", "exact_kv_and_rows", "off"], Form()] = "exact_kv_and_rows",
    sa_morton: Annotated[bool, Form()] = False,
    sa_morton_curve: Annotated[Literal["3d", "2d_frame"], Form()] = "2d_frame",
    sa_dense_blocks: Annotated[str, Form(max_length=256)] = "0",
    sa_stage2_denoise: Annotated[float, Form(ge=0, le=1)] = 0.35,
    seed: Annotated[str | None, Form()] = None,
    lyrics: Annotated[str, Form(max_length=12000)] = "",
    title: Annotated[str | None, Form(max_length=120)] = None,
    comfy_node: Annotated[str, Form(max_length=200)] = "auto",
    runninghub_parameters: Annotated[
        str, Form(description="JSON object keyed by RunningHub schema field keys.")
    ] = "{}",
    folder_id: Annotated[str | None, Form(max_length=100)] = None,
    incognito: Annotated[bool, Form()] = False,
    incognito_code: Annotated[str | None, Header(alias="X-H3-Incognito-Code")] = None,
    proxy_source_device_id: Annotated[str | None, Form()] = None,
):
    prompt = prompt.strip()
    normalized_folder_id = normalize_folder_id(folder_id)
    if incognito and normalized_folder_id:
        raise HTTPException(status_code=422, detail="无痕任务不支持文件夹")
    if len(prompt) > 12000:
        raise HTTPException(status_code=422, detail="提示词不能超过 12000 个字符")
    validate_upscale_parameters(task_type, upscale_category, upscale_scale)
    if incognito and not secrets.compare_digest(incognito_code or "", settings.incognito_code):
        raise HTTPException(status_code=403, detail="无痕模式授权已失效")
    remote_target = parse_remote_node_id(comfy_node)
    if remote_target:
        return await submit_proxy_generation(
            prompt=prompt,
            reference_manifest=reference_manifest,
            references=references,
            model_variant=model_variant,
            execution_mode=execution_mode,
            task_type=task_type,
            upscale_category=upscale_category,
            upscale_scale=upscale_scale,
            auto_upscale=auto_upscale,
            auto_upscale_category=auto_upscale_category,
            auto_upscale_scale=auto_upscale_scale,
            width=width,
            height=height,
            duration=duration,
            steps=steps,
            sa_tau=sa_tau,
            sa_start_percent=sa_start_percent,
            sa_end_percent=sa_end_percent,
            sa_min_tokens=sa_min_tokens,
            sa_int8_qk=sa_int8_qk,
            sa_int8_pv=sa_int8_pv,
            sa_sink_conditioning=sa_sink_conditioning,
            sa_morton=sa_morton,
            sa_morton_curve=sa_morton_curve,
            sa_dense_blocks=sa_dense_blocks,
            sa_stage2_denoise=sa_stage2_denoise,
            seed=seed,
            lyrics=lyrics,
            title=title,
            comfy_node=comfy_node,
            runninghub_parameters=runninghub_parameters,
            incognito=incognito,
            incognito_code=incognito_code,
            peer_device_id=remote_target[0],
            proxy_node_id=remote_target[1],
            proxy_source_device_id=proxy_source_device_id,
            folder_id=normalized_folder_id,
        )
    if auto_upscale and comfy_node == "auto":
        comfy_candidate = next(
            (
                node["id"]
                for node in manager.nodes_public()
                if node.get("provider") == "comfyui" and node.get("healthy")
            ),
            None,
        )
        if not comfy_candidate:
            raise HTTPException(status_code=422, detail="自动超分没有可用的 ComfyUI 节点")
        comfy_node = comfy_candidate
    if comfy_node == "auto" and not manager.node_ids:
        raise HTTPException(status_code=422, detail="当前没有可用推理节点，请添加推理节点")
    if not manager.accepts_node(comfy_node):
        raise HTTPException(status_code=422, detail="指定的推理节点不存在")
    workflow_profile = manager.workflow_profile(comfy_node)
    if manager.node_provider(comfy_node) == "runninghub" and not workflow_profile:
        raise HTTPException(status_code=422, detail="RunningHub 工作流参数定义不可用")
    is_runninghub = bool(
        workflow_profile and workflow_profile.get("provider") == "runninghub"
    )
    if is_runninghub and task_type == "upscale":
        raise HTTPException(status_code=422, detail="超分任务需要使用 ComfyUI 节点")
    validate_auto_upscale_parameters(
        auto_upscale,
        task_type,
        model_variant,
        execution_mode,
        auto_upscale_category,
        auto_upscale_scale,
        "runninghub" if is_runninghub else "comfyui",
    )
    if not is_runninghub:
        minimum_prompt_length = 0 if task_type == "upscale" else 2 if execution_mode == "music3" else 8
        if len(prompt) < minimum_prompt_length:
            raise HTTPException(
                status_code=422,
                detail=f"提示词至少需要 {minimum_prompt_length} 个字符",
            )
        effective_execution_mode = "upscale" if task_type == "upscale" else execution_mode
        validate_execution_mode(effective_execution_mode, model_variant, incognito)
        if execution_mode == "tts":
            width = 32
            height = 32
        validate_generation(width, height, duration, steps, effective_execution_mode)
        if execution_mode == "h3-sa":
            validate_sa_parameters(
                tau=sa_tau,
                start_percent=sa_start_percent,
                end_percent=sa_end_percent,
                min_tokens=sa_min_tokens,
                stage2_denoise=sa_stage2_denoise,
            )

    try:
        seed_raw = (seed or "").strip()
        seed_value = int(seed_raw) if seed_raw else secrets.randbelow(2**31)
        manifest = json.loads(reference_manifest)
        dynamic_parameters = json.loads(runninghub_parameters)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="参数格式不正确") from exc
    if not 0 <= seed_value < 2**31:
        raise HTTPException(status_code=422, detail="随机种子超出范围")
    if not isinstance(manifest, list):
        raise HTTPException(status_code=422, detail="reference_manifest 必须是数组")

    uploads = references
    if len(uploads) != len(manifest):
        raise HTTPException(status_code=422, detail="素材数量与 reference_manifest 不一致")

    if any(not isinstance(item, dict) for item in manifest):
        raise HTTPException(status_code=422, detail="reference_manifest 的每一项必须是对象")
    manifest_kinds = [item.get("type") for item in manifest]
    kinds = [
        "file"
        if is_runninghub and expected_kind == "file"
        else classify_upload(upload, allow_file=is_runninghub)
        for upload, expected_kind in zip(uploads, manifest_kinds, strict=True)
    ]
    if kinds != manifest_kinds:
        raise HTTPException(status_code=422, detail="素材顺序或类型与 reference_manifest 不一致")
    if is_runninghub:
        if not isinstance(dynamic_parameters, dict):
            raise HTTPException(status_code=422, detail="runninghub_parameters 必须是对象")
        dynamic_parameters, manifest = prepare_runninghub_request(
            workflow_profile or {}, prompt, dynamic_parameters, manifest
        )
    else:
        validate_references(
            model_variant,
            kinds,
            "upscale" if task_type == "upscale" else execution_mode,
        )

    job_id = secrets.token_hex(8)
    upload_dir = settings.uploads_dir / job_id
    upload_dir.mkdir(parents=True)
    input_paths = []
    public_manifest = []
    try:
        for index, (upload, kind) in enumerate(zip(uploads, kinds, strict=True), start=1):
            suffix = Path(upload.filename or "").suffix.lower()[:10]
            destination = upload_dir / f"{index:02d}_{kind}{suffix}"
            size = await save_upload(upload, destination)
            item: dict[str, object] = {
                "type": kind,
                "name": upload.filename,
                "size": size,
            }
            field_key = str(manifest[index - 1].get("field_key") or "")
            if field_key:
                item["field_key"] = field_key
            if not is_runninghub and task_type != "upscale" and model_variant == "fl2va-fp8":
                item["role"] = "first_frame" if index == 1 else "last_frame"
            if kind in {"video", "audio"}:
                media_duration, has_audio = probe_media(
                    destination,
                    None if is_runninghub or task_type == "upscale" else 15.1,
                )
                item["duration"] = round(media_duration, 3)
                if kind == "video":
                    item["has_audio"] = has_audio
                    if task_type == "upscale":
                        item["source_fps"] = round(probe_video_fps(destination), 6)
            input_paths.append(str(destination))
            public_manifest.append(item)
    except Exception:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise

    if not is_runninghub and execution_mode == "digital-human":
        audio_reference = next(item for item in public_manifest if item["type"] == "audio")
        duration = float(audio_reference["duration"])
        validate_generation(width, height, duration, steps, execution_mode)

    created_at = utc_now()
    schema = (
        workflow_profile.get("runninghub_schema")
        if is_runninghub and workflow_profile
        else None
    )
    media_type = (
        output_media_type(schema)
        if isinstance(schema, dict)
        else "audio"
        if execution_mode in {"music3", "tts"}
        else str(public_manifest[0]["type"])
        if task_type == "upscale"
        else "video"
    )
    workflow_name = str(
        workflow_profile.get("workflow_name") or "RunningHub"
        if is_runninghub and workflow_profile
        else ""
    )
    upscale_title = (
        f"{ {'real': '真人', 'anime': '动画', '3d': '3D'}.get(upscale_category, '超分') } · {upscale_scale}x 超分"
        if task_type == "upscale"
        else ""
    )
    job = {
        "id": job_id,
        "title": (title or (prompt.splitlines()[0] if prompt else workflow_name or upscale_title))[:120],
        "folder_id": normalized_folder_id,
        "status": "queued",
        "stage": "等待推理节点执行",
        "progress": 0,
        "created_at": created_at,
        "updated_at": created_at,
        "cancel_requested": False,
        "request": {
            "prompt": prompt,
            "lyrics": lyrics.strip() if execution_mode == "music3" else "",
            "model_variant": model_variant,
            "execution_mode": execution_mode,
            "task_type": task_type,
            "upscale_category": upscale_category,
            "upscale_scale": upscale_scale,
            "auto_upscale": auto_upscale,
            "auto_upscale_category": auto_upscale_category,
            "auto_upscale_scale": auto_upscale_scale,
            "width": width,
            "height": height,
            "duration": duration,
            "num_frames": align_frames(duration),
            "steps": steps,
            "sa_tau": sa_tau,
            "sa_start_percent": sa_start_percent,
            "sa_end_percent": sa_end_percent,
            "sa_min_tokens": sa_min_tokens,
            "sa_int8_qk": sa_int8_qk,
            "sa_int8_pv": sa_int8_pv,
            "sa_sink_conditioning": sa_sink_conditioning,
            "sa_morton": sa_morton,
            "sa_morton_curve": sa_morton_curve,
            "sa_dense_blocks": sa_dense_blocks,
            "sa_stage2_denoise": sa_stage2_denoise,
            "seed": seed_value,
            "references": public_manifest,
            "media_type": media_type,
            **(
                {
                    "source_fps": public_manifest[0].get("source_fps", 24.0),
                    "has_audio": bool(public_manifest[0].get("has_audio")),
                }
                if task_type == "upscale" and public_manifest[0]["type"] == "video"
                else {}
            ),
            "comfy_node": comfy_node,
            "incognito": incognito,
            **(
                {
                    "proxy_source_device_id": proxy_source_device_id,
                    "remote_proxy_requested": True,
                }
                if proxy_source_device_id
                else {}
            ),
            **(
                {
                    "provider": "runninghub",
                    "runninghub_resource_id": workflow_profile.get("workflow_id"),
                    "runninghub_resource_type": workflow_profile.get(
                        "runninghub_resource_type"
                    ),
                    "runninghub_workflow_name": workflow_name,
                    "runninghub_schema": schema,
                    "runninghub_parameters": dynamic_parameters,
                }
                if is_runninghub and workflow_profile
                else {}
            ),
        },
        "input_paths": input_paths,
    }
    prepare_job_output_name(job)
    store.create(job)
    manager.submit(job_id)
    response = store.public(job_id, manager.queue_position(job_id))
    response["status_url"] = f"/api/v1/generations/{job_id}"
    return response


async def submit_proxy_generation(
    *,
    prompt: str,
    reference_manifest: str,
    references: list[UploadFile],
    model_variant: str,
    execution_mode: str,
    task_type: str,
    upscale_category: str,
    upscale_scale: int,
    auto_upscale: bool,
    auto_upscale_category: str,
    auto_upscale_scale: int,
    width: int,
    height: int,
    duration: float,
    steps: int,
    sa_tau: float,
    sa_start_percent: float,
    sa_end_percent: float,
    sa_min_tokens: int,
    sa_int8_qk: bool,
    sa_int8_pv: bool,
    sa_sink_conditioning: str,
    sa_morton: bool,
    sa_morton_curve: str,
    sa_dense_blocks: str,
    sa_stage2_denoise: float,
    seed: str | None,
    lyrics: str,
    title: str | None,
    comfy_node: str,
    runninghub_parameters: str,
    incognito: bool,
    incognito_code: str | None,
    peer_device_id: str,
    proxy_node_id: str,
    proxy_source_device_id: str | None,
    folder_id: str | None,
) -> dict[str, Any]:
    peer = local_state.peer(peer_device_id, include_secrets=True)
    if not peer:
        raise HTTPException(status_code=404, detail="互联设备不存在")
    proxy_node_name = ""
    try:
        nodes_payload = await peer_json(peer, "/api/v1/peering/export/nodes")
        proxy_node_name = str(
            next(
                (
                    node.get("name")
                    for node in nodes_payload.get("data", [])
                    if secrets.compare_digest(str(node.get("proxy_node_id") or ""), proxy_node_id)
                ),
                "",
            )
            or ""
        )
    except (httpx.HTTPError, ValueError, TypeError):
        pass
    data = {
        "prompt": prompt,
        "reference_manifest": reference_manifest,
        "model_variant": model_variant,
        "execution_mode": execution_mode,
        "task_type": task_type,
        "upscale_category": upscale_category,
        "upscale_scale": str(upscale_scale),
        "auto_upscale": "true" if auto_upscale else "false",
        "auto_upscale_category": auto_upscale_category,
        "auto_upscale_scale": str(auto_upscale_scale),
        "width": str(width),
        "height": str(height),
        "duration": str(duration),
        "steps": str(steps),
        "sa_tau": str(sa_tau),
        "sa_start_percent": str(sa_start_percent),
        "sa_end_percent": str(sa_end_percent),
        "sa_min_tokens": str(sa_min_tokens),
        "sa_int8_qk": "true" if sa_int8_qk else "false",
        "sa_int8_pv": "true" if sa_int8_pv else "false",
        "sa_sink_conditioning": sa_sink_conditioning,
        "sa_morton": "true" if sa_morton else "false",
        "sa_morton_curve": sa_morton_curve,
        "sa_dense_blocks": sa_dense_blocks,
        "sa_stage2_denoise": str(sa_stage2_denoise),
        "seed": seed or "",
        "lyrics": lyrics,
        "title": title or "",
        "comfy_node": "auto",
        "runninghub_parameters": runninghub_parameters,
        "incognito": "true" if incognito else "false",
        "proxy_source_device_id": proxy_source_device_id or "",
        "proxy_records_key": local_state.get_setting("remote_records_key"),
    }
    files: list[tuple[str, tuple[str, bytes, str]]] = []
    for upload in references:
        content = await upload.read()
        files.append(
            (
                "references",
                (
                    upload.filename or "reference",
                    content,
                    upload.content_type or "application/octet-stream",
                ),
            )
        )
    headers = {
        "Authorization": f"Bearer {peer['access_token']}",
        "X-H3-Proxy-Node": proxy_node_id,
    }
    if incognito_code:
        headers["X-H3-Incognito-Code"] = incognito_code
    try:
        timeout = httpx.Timeout(60, connect=10)
        async with httpx.AsyncClient(base_url=peer["base_url"], timeout=timeout, trust_env=False) as client:
            response = await client.post(
                "/api/v1/peering/proxy/generations",
                data=data,
                files=files,
                headers=headers,
            )
            if response.status_code >= 400:
                detail = response.text[:500]
                try:
                    detail = str(response.json().get("detail") or detail)
                except ValueError:
                    pass
                raise HTTPException(status_code=response.status_code, detail=detail)
            remote = response.json()
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"远程代理提交失败：{exc}") from exc
    local_id = f"proxy-{secrets.token_hex(8)}"
    now = utc_now()
    request_data = deepcopy(remote.get("request") or {})
    request_data.update(
        {
            "comfy_node": comfy_node,
            "remote_proxy": True,
            "proxy_peer_id": peer_device_id,
            "proxy_remote_job_id": str(remote.get("id") or ""),
            "proxy_node_id": proxy_node_id,
            "proxy_node_name": str(remote.get("assigned_node", {}).get("name") or proxy_node_name),
        }
    )
    assigned_node = {
        "name": request_data["proxy_node_name"] or "远程代理节点",
        "owner_name": peer.get("name") or peer_device_id,
        "owner_device_id": peer_device_id,
        "remote_proxy": True,
    }
    job = {
        "id": local_id,
        "title": remote.get("title") or title or prompt[:120],
        "folder_id": folder_id,
        "status": remote.get("status") or "queued",
        "stage": "已提交远程代理节点",
        "progress": int(remote.get("progress") or 0),
        "created_at": remote.get("created_at") or now,
        "updated_at": remote.get("updated_at") or now,
        "cancel_requested": False,
        "request": request_data,
        "input_paths": [],
        "proxy_peer_id": peer_device_id,
        "proxy_remote_job_id": str(remote.get("id") or ""),
        "proxy_remote_result_url": str(remote.get("result_url") or ""),
        "owner_name": peer.get("name") or peer_device_id,
        "owner_device_id": peer_device_id,
        "assigned_node": assigned_node,
    }
    prepare_job_output_name(job)
    store.create(job)
    schedule_proxy_poll(local_id)
    result = store.public(local_id)
    result["owner_name"] = peer.get("name") or peer_device_id
    result["owner_device_id"] = peer_device_id
    result["remote_proxy"] = True
    result["result_url"] = f"/api/v1/generations/{local_id}/result"
    return result


async def sync_proxy_generation(job_id: str) -> dict[str, Any] | None:
    local_job = store.get(job_id)
    if not local_job or not local_job.get("request", {}).get("remote_proxy"):
        return local_job
    peer = local_state.peer(str(local_job.get("proxy_peer_id") or ""), include_secrets=True)
    remote_id = str(local_job.get("proxy_remote_job_id") or "")
    if not peer or not remote_id:
        return local_job
    remote = await peer_json(peer, f"/api/v1/peering/export/generations/{remote_id}")
    changes: dict[str, Any] = {
        "status": remote.get("status", local_job.get("status")),
        "stage": remote.get("stage", local_job.get("stage")),
        "progress": remote.get("progress", local_job.get("progress", 0)),
        "assigned_node": {
            "name": local_job.get("request", {}).get("proxy_node_name") or "远程代理节点",
            "owner_name": peer.get("name") or local_job.get("proxy_peer_id"),
            "owner_device_id": local_job.get("proxy_peer_id"),
            "remote_proxy": True,
        },
    }
    for key in ("started_at", "completed_at", "error"):
        if remote.get(key) is not None:
            changes[key] = remote[key]
    if remote.get("status") == "completed":
        changes["proxy_remote_result_url"] = remote.get("result_url") or local_job.get("proxy_remote_result_url")
        changes["result_url"] = f"/api/v1/generations/{job_id}/result"
    return store.update(job_id, **changes)


async def poll_proxy_generation(job_id: str) -> None:
    try:
        while True:
            job = store.get(job_id)
            if not job or job.get("status") in TERMINAL_STATES:
                return
            try:
                synced = await sync_proxy_generation(job_id)
                if not synced or synced.get("status") in TERMINAL_STATES:
                    return
            except (httpx.HTTPError, ValueError, TypeError, KeyError):
                pass
            await asyncio.sleep(max(2.0, settings.comfy_poll_seconds))
    finally:
        proxy_poll_tasks.pop(job_id, None)


def schedule_proxy_poll(job_id: str) -> None:
    existing = proxy_poll_tasks.get(job_id)
    if existing and not existing.done():
        return
    proxy_poll_tasks[job_id] = asyncio.create_task(poll_proxy_generation(job_id))


@app.get("/api/v1/generations/{job_id}", dependencies=[Depends(authorize)])
async def get_generation(job_id: str):
    local_job = store.get(job_id)
    if local_job and local_job.get("request", {}).get("remote_proxy"):
        try:
            await sync_proxy_generation(job_id)
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            pass
    job = store.public(job_id, manager.queue_position(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@app.patch("/api/v1/generations/{job_id}", dependencies=[Depends(authorize)])
async def update_generation(
    job_id: str,
    patch: GenerationPatch,
    incognito_code: Annotated[str | None, Header(alias="X-H3-Incognito-Code")] = None,
):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    values = patch.model_dump(exclude_none=True)
    if not values:
        return store.public(job_id, manager.queue_position(job_id))
    if job["status"] != "queued" and set(values) != {"title"}:
        raise HTTPException(status_code=409, detail="只有排队中的任务可以修改生成参数")

    title = values.pop("title", None)
    request_data = dict(job["request"])
    request_data.update(values)
    request_data.setdefault("model_variant", "fl2va-fp8")
    request_data.setdefault("execution_mode", "native")
    request_data.setdefault("comfy_node", "auto")
    if not manager.accepts_node(request_data["comfy_node"]):
        raise HTTPException(status_code=422, detail="指定的推理节点不存在")
    workflow_profile = manager.workflow_profile(request_data["comfy_node"])
    if (
        manager.node_provider(request_data["comfy_node"]) == "runninghub"
        and not workflow_profile
    ):
        raise HTTPException(status_code=422, detail="RunningHub 工作流参数定义不可用")
    is_runninghub = bool(
        workflow_profile and workflow_profile.get("provider") == "runninghub"
    )
    if request_data.get("execution_mode") == "tts":
        request_data["width"] = 32
        request_data["height"] = 32
    if request_data.get("provider") == "runninghub" and not is_runninghub:
        raise HTTPException(status_code=422, detail="请选择与原任务工作流匹配的 RunningHub 节点")
    if is_runninghub and workflow_profile:
        references = request_data.get("references", [])
        manifest = [
            {
                "type": item.get("type"),
                "field_key": item.get("field_key", ""),
            }
            for item in references
        ]
        parameters, assigned_manifest = prepare_runninghub_request(
            workflow_profile,
            str(request_data.get("prompt") or "").strip(),
            request_data.get("runninghub_parameters"),
            manifest,
        )
        for reference, assigned in zip(references, assigned_manifest, strict=True):
            reference["field_key"] = assigned["field_key"]
        schema = workflow_profile["runninghub_schema"]
        request_data.update(
            provider="runninghub",
            runninghub_resource_id=workflow_profile["workflow_id"],
            runninghub_resource_type=workflow_profile["runninghub_resource_type"],
            runninghub_workflow_name=workflow_profile["workflow_name"],
            runninghub_schema=schema,
            runninghub_parameters=parameters,
            media_type=output_media_type(schema),
        )
    else:
        request_data.pop("provider", None)
        task_type = request_data.get("task_type", "generation")
        validate_upscale_parameters(
            task_type,
            str(request_data.get("upscale_category") or "real"),
            int(request_data.get("upscale_scale") or 2),
        )
        validate_auto_upscale_parameters(
            bool(request_data.get("auto_upscale")),
            task_type,
            str(request_data.get("model_variant") or "fl2va-fp8"),
            str(request_data.get("execution_mode") or "native"),
            str(request_data.get("auto_upscale_category") or "real"),
            int(request_data.get("auto_upscale_scale") or 2),
            "comfyui",
        )
        minimum_prompt_length = 0 if task_type == "upscale" else 2 if request_data["execution_mode"] == "music3" else 8
        if len(request_data.get("prompt", "").strip()) < minimum_prompt_length:
            raise HTTPException(
                status_code=422,
                detail=f"提示词至少需要 {minimum_prompt_length} 个字符",
            )
        effective_execution_mode = "upscale" if task_type == "upscale" else request_data["execution_mode"]
        validate_execution_mode(
            effective_execution_mode,
            request_data["model_variant"],
            bool(request_data.get("incognito")),
        )
        if request_data["execution_mode"] == "h3-nsfw" and not secrets.compare_digest(
            incognito_code or "",
            settings.incognito_code,
        ):
            raise HTTPException(status_code=403, detail="无痕模式授权已失效")
        validate_references(
            request_data["model_variant"],
            [item["type"] for item in request_data.get("references", [])],
            effective_execution_mode,
        )
        if request_data["execution_mode"] == "digital-human":
            audio_reference = next(
                item for item in request_data["references"] if item["type"] == "audio"
            )
            request_data["duration"] = float(audio_reference["duration"])
        validate_generation(
            request_data["width"],
            request_data["height"],
            request_data["duration"],
            request_data["steps"],
            effective_execution_mode,
        )
        if request_data["execution_mode"] == "h3-sa":
            validate_sa_parameters(
                tau=float(request_data.get("sa_tau", 1.3)),
                start_percent=float(request_data.get("sa_start_percent", 0.2)),
                end_percent=float(request_data.get("sa_end_percent", 0.9)),
                min_tokens=int(request_data.get("sa_min_tokens", 4096)),
                stage2_denoise=float(request_data.get("sa_stage2_denoise", 0.35)),
            )
        request_data["media_type"] = (
            request_data["references"][0]["type"]
            if task_type == "upscale" and request_data.get("references")
            else "audio"
            if request_data["execution_mode"] in {"music3", "tts"}
            else "video"
        )
        request_data["num_frames"] = align_frames(request_data["duration"])
    changes: dict[str, object] = {"request": request_data, "event_message": "任务参数已修改"}
    if title is not None:
        changes["title"] = title.strip() or job.get("title", "")
    store.update(job_id, **changes)
    return store.public(job_id, manager.queue_position(job_id))


@app.post("/api/v1/generations/{job_id}/cancel", status_code=202, dependencies=[Depends(authorize)])
async def cancel_generation(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.get("request", {}).get("remote_proxy"):
        peer = local_state.peer(str(job.get("proxy_peer_id") or ""), include_secrets=True)
        remote_id = str(job.get("proxy_remote_job_id") or "")
        if not peer or not remote_id:
            raise HTTPException(status_code=410, detail="远程代理记录已不存在")
        try:
            timeout = httpx.Timeout(15, connect=5)
            async with httpx.AsyncClient(
                base_url=peer["base_url"],
                headers={"Authorization": f"Bearer {peer['access_token']}"},
                timeout=timeout,
                trust_env=False,
            ) as client:
                response = await client.post(f"/api/v1/peering/proxy/generations/{remote_id}/cancel")
                if response.status_code >= 400:
                    raise HTTPException(status_code=response.status_code, detail="远程任务无法取消")
                remote = response.json()
        except HTTPException:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=f"远程任务取消失败：{exc}") from exc
        store.update(
            job_id,
            status=remote.get("status", "cancelled"),
            stage=remote.get("stage", "正在取消"),
            progress=remote.get("progress", 0),
            cancel_requested=True,
        )
        schedule_proxy_poll(job_id)
        return store.public(job_id)
    if not manager.cancel(job_id):
        raise HTTPException(status_code=409, detail="任务已结束，无法取消")
    return store.public(job_id, manager.queue_position(job_id))


@app.post(
    "/api/v1/generations/{job_id}/regenerate",
    status_code=202,
    dependencies=[Depends(authorize)],
)
async def regenerate_generation(
    job_id: str,
    payload: RegenerateRequest,
    incognito_code: Annotated[str | None, Header(alias="X-H3-Incognito-Code")] = None,
):
    source_job = store.get(job_id)
    if not source_job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if source_job["status"] not in TERMINAL_STATES:
        raise HTTPException(status_code=409, detail="任务结束后才能重新生成")
    folder_id = normalize_folder_id(payload.folder_id)

    request_data = deepcopy(source_job.get("request", {}))
    model_variant = request_data.get("model_variant", "fl2va-fp8")
    execution_mode = request_data.get("execution_mode", "native")
    comfy_node = request_data.get("comfy_node", "auto")
    incognito = bool(request_data.get("incognito"))
    if incognito and not secrets.compare_digest(incognito_code or "", settings.incognito_code):
        raise HTTPException(status_code=403, detail="无痕模式授权已失效")
    if incognito and folder_id:
        raise HTTPException(status_code=422, detail="无痕任务不支持文件夹")
    if not manager.accepts_node(comfy_node):
        raise HTTPException(status_code=422, detail="原任务指定的推理节点不存在")
    workflow_profile = manager.workflow_profile(comfy_node)
    references = request_data.get("references", [])
    if request_data.get("provider") == "runninghub":
        if not workflow_profile or workflow_profile.get("provider") != "runninghub":
            raise HTTPException(status_code=422, detail="原任务的 RunningHub 工作流当前不可用")
        if str(workflow_profile.get("workflow_id") or "") != str(
            request_data.get("runninghub_resource_id") or ""
        ):
            raise HTTPException(status_code=422, detail="原任务绑定的 RunningHub 工作流已变更")
        manifest = [
            {
                "type": item.get("type"),
                "field_key": item.get("field_key", ""),
            }
            for item in references
        ]
        parameters, assigned_manifest = prepare_runninghub_request(
            workflow_profile,
            str(request_data.get("prompt") or "").strip(),
            request_data.get("runninghub_parameters"),
            manifest,
        )
        for reference, assigned in zip(references, assigned_manifest, strict=True):
            reference["field_key"] = assigned["field_key"]
        schema = workflow_profile["runninghub_schema"]
        request_data.update(
            runninghub_resource_type=workflow_profile["runninghub_resource_type"],
            runninghub_workflow_name=workflow_profile["workflow_name"],
            runninghub_schema=schema,
            runninghub_parameters=parameters,
            media_type=output_media_type(schema),
        )
    else:
        if manager.node_provider(comfy_node) == "runninghub":
            raise HTTPException(status_code=422, detail="原任务指定节点的类型已变更")
        validate_upscale_parameters(
            str(request_data.get("task_type") or "generation"),
            str(request_data.get("upscale_category") or "real"),
            int(request_data.get("upscale_scale") or 2),
        )
        validate_auto_upscale_parameters(
            bool(request_data.get("auto_upscale")),
            str(request_data.get("task_type") or "generation"),
            model_variant,
            execution_mode,
            str(request_data.get("auto_upscale_category") or "real"),
            int(request_data.get("auto_upscale_scale") or 2),
            "comfyui",
        )
        if execution_mode == "tts":
            request_data["width"] = 32
            request_data["height"] = 32
        effective_execution_mode = "upscale" if request_data.get("task_type") == "upscale" else execution_mode
        validate_execution_mode(effective_execution_mode, model_variant, incognito)
        validate_generation(
            request_data.get("width", 832),
            request_data.get("height", 480),
            request_data.get("duration", 5),
            request_data.get("steps", 10),
            effective_execution_mode,
        )
        if execution_mode == "h3-sa":
            validate_sa_parameters(
                tau=float(request_data.get("sa_tau", 1.3)),
                start_percent=float(request_data.get("sa_start_percent", 0.2)),
                end_percent=float(request_data.get("sa_end_percent", 0.9)),
                min_tokens=int(request_data.get("sa_min_tokens", 4096)),
                stage2_denoise=float(request_data.get("sa_stage2_denoise", 0.35)),
            )
        validate_references(
            model_variant,
            [item.get("type") for item in references],
            effective_execution_mode,
        )
        request_data["media_type"] = (
            references[0].get("type")
            if request_data.get("task_type") == "upscale" and references
            else "audio"
            if execution_mode in {"music3", "tts"}
            else "video"
        )

    source_paths = source_job.get("input_paths", [])
    if len(source_paths) != len(references):
        raise HTTPException(status_code=410, detail="原任务参考文件不完整")
    new_job_id = secrets.token_hex(8)
    upload_dir = settings.uploads_dir / new_job_id
    cloned_paths: list[str] = []
    try:
        if source_paths:
            upload_dir.mkdir(parents=True)
        source_root = (settings.uploads_dir / job_id).resolve()
        for source_path in source_paths:
            source = Path(source_path).resolve()
            try:
                source.relative_to(source_root)
            except ValueError as exc:
                raise HTTPException(status_code=410, detail="原任务参考文件路径无效") from exc
            if not source.is_file():
                raise HTTPException(status_code=410, detail="原任务参考文件已不存在")
            destination = upload_dir / source.name
            shutil.copy2(source, destination)
            cloned_paths.append(str(destination))
    except Exception:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise

    for reference in references:
        reference.pop("url", None)
    if request_data.get("provider") != "runninghub":
        request_data["num_frames"] = align_frames(request_data.get("duration", 5))
    created_at = utc_now()
    regenerated_job = {
        "id": new_job_id,
        "title": source_job.get("title") or request_data.get("prompt", "")[:120],
        "folder_id": folder_id,
        "status": "queued",
        "stage": "等待推理节点执行",
        "progress": 0,
        "created_at": created_at,
        "updated_at": created_at,
        "cancel_requested": False,
        "request": request_data,
        "input_paths": cloned_paths,
    }
    prepare_job_output_name(regenerated_job)
    store.create(regenerated_job)
    manager.submit(new_job_id)
    response = store.public(new_job_id, manager.queue_position(new_job_id))
    response["status_url"] = f"/api/v1/generations/{new_job_id}"
    return response


@app.delete("/api/v1/generations/{job_id}", dependencies=[Depends(authorize)])
async def delete_generation(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job["status"] not in TERMINAL_STATES:
        raise HTTPException(status_code=409, detail="请先取消任务，任务结束后再删除")
    if job.get("request", {}).get("remote_proxy"):
        peer = local_state.peer(str(job.get("proxy_peer_id") or ""), include_secrets=True)
        remote_id = proxy_remote_job_id(job)
        if not peer or not remote_id:
            raise HTTPException(status_code=410, detail="远程代理记录已不存在")
        try:
            timeout = httpx.Timeout(15, connect=5)
            async with httpx.AsyncClient(
                base_url=peer["base_url"],
                headers={"Authorization": f"Bearer {peer['access_token']}"},
                timeout=timeout,
                trust_env=False,
            ) as client:
                response = await client.delete(
                    f"/api/v1/peering/proxy/generations/{remote_id}"
                )
            if response.status_code not in {200, 404}:
                detail = response.text[:500]
                try:
                    detail = str(response.json().get("detail") or detail)
                except ValueError:
                    pass
                raise HTTPException(status_code=response.status_code, detail=detail)
        except HTTPException:
            raise
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"远程任务删除失败：{exc}") from exc
    manager.remove(job_id)
    store.delete(job_id)
    return {"id": job_id, "status": "deleted"}


def _asset_media_type(value: str, file_name: str) -> tuple[str, str]:
    category = value if value in {"video", "audio", "image", "file"} else "file"
    guessed = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    if category == "file":
        if guessed.startswith("video/"):
            category = "video"
        elif guessed.startswith("audio/"):
            category = "audio"
        elif guessed.startswith("image/"):
            category = "image"
    return category, guessed


def _local_asset_entry(job: dict[str, Any]) -> dict[str, Any]:
    request_data = job.get("request", {})
    result_path = Path(str(job.get("result_path") or ""))
    file_name = result_path.name if job.get("result_path") else ""
    media_type, mime_type = _asset_media_type(
        str(request_data.get("media_type") or "file"), file_name
    )
    owner_device_id = str(
        job.get("owner_device_id")
        or request_data.get("proxy_source_device_id")
        or local_state.device_id
    )
    owner_name = str(job.get("owner_name") or "")
    if not owner_name and owner_device_id != local_state.device_id:
        owner_name = str((local_state.peer(owner_device_id) or {}).get("name") or owner_device_id)
    if not owner_name:
        owner_name = local_state.machine_name
    available = bool(job.get("result_path") and result_path.is_file())
    preview_path = Path(str(job.get("preview_path") or ""))
    return {
        "id": f"job::{job['id']}",
        "job_id": str(job["id"]),
        "name": str(job.get("title") or request_data.get("prompt") or job["id"]),
        "file_name": file_name,
        "media_type": media_type,
        "mime_type": mime_type,
        "owner_name": owner_name,
        "owner_device_id": owner_device_id,
        "created_at": str(job.get("created_at") or ""),
        "preview_url": f"/api/v1/generations/{quote(str(job['id']), safe='')}/preview" if preview_path.is_file() else "",
        "encrypted": False,
        "locked": False,
        "asset_deleted": bool(job.get("asset_deleted")) or not available,
        "folder_id": job.get("folder_id"),
        "size": result_path.stat().st_size if available else 0,
        "can_delete": local_job_is_owned(job),
    }


def _protected_asset_entry(metadata: dict[str, Any]) -> dict[str, Any]:
    peer_device_id = str(metadata.get("owner_device_id") or "")
    job_id = str(metadata.get("job_id") or "")
    key_id = str(metadata.get("key_id") or "")
    file_name = str(metadata.get("file_name") or "")
    media_type, mime_type = _asset_media_type(
        str(metadata.get("media_type") or "file"), file_name
    )
    locked = not bool(local_state.unlocked_peer_key(peer_device_id, key_id))
    deleted = bool(metadata.get("asset_deleted"))
    result_size = 0
    for item in metadata.get("result_files", []) or []:
        if item.get("kind") != "result":
            continue
        path = _safe_local_data_path(str(item.get("encrypted_path") or ""))
        if path and path.is_file():
            result_size += path.stat().st_size
    return {
        "id": f"protected::{peer_device_id}::{job_id}",
        "job_id": job_id,
        "name": str(metadata.get("title") or file_name or job_id),
        "file_name": file_name,
        "media_type": media_type,
        "mime_type": mime_type,
        "owner_name": str(metadata.get("owner_name") or peer_device_id),
        "owner_device_id": peer_device_id,
        "created_at": str(metadata.get("created_at") or ""),
        "preview_url": (
            f"/api/v1/assets/local/protected/{quote(peer_device_id, safe='')}/{quote(job_id, safe='')}/result"
            if not locked and not deleted
            else ""
        ),
        "encrypted": True,
        "locked": locked,
        "asset_deleted": deleted,
        "key_id": key_id,
        "size": result_size,
        "can_delete": False,
    }


def _find_protected_asset(peer_device_id: str, job_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in _protected_asset_metadata(peer_device_id)
            if secrets.compare_digest(str(item.get("job_id") or ""), job_id)
        ),
        None,
    )


@app.get("/api/v1/assets/local", dependencies=[Depends(authorize)])
async def list_local_assets(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 24,
    folder_id: Annotated[str | None, Query(max_length=100)] = None,
):
    resolved_folder_id = folder_filter_value(folder_id)
    local_folder_id = (
        UNFILED_FOLDER_ID
        if resolved_folder_id in {None, ROOT_FOLDER_ID}
        else resolved_folder_id
    )
    items = [
        entry
        for job in store.local_asset_jobs()
        if not local_folder_id or (
            not job.get("folder_id")
            if local_folder_id == UNFILED_FOLDER_ID
            else job.get("folder_id") == local_folder_id
        )
        if not (entry := _local_asset_entry(job))["asset_deleted"]
    ]
    if resolved_folder_id in {None, ROOT_FOLDER_ID, UNFILED_FOLDER_ID}:
        items.extend(
            entry
            for item in _protected_asset_metadata()
            if not (entry := _protected_asset_entry(item))["asset_deleted"]
        )
    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    total = len(items)
    start = (page - 1) * page_size
    total_size = sum(int(item.get("size") or 0) for item in items)
    all_local_items = [
        entry
        for job in store.local_asset_jobs()
        if not (entry := _local_asset_entry(job))["asset_deleted"]
    ]
    all_local_items.extend(
        entry
        for item in _protected_asset_metadata()
        if not (entry := _protected_asset_entry(item))["asset_deleted"]
    )
    return {
        "data": items[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": max(1, math.ceil(total / page_size)),
        "folder_id": resolved_folder_id or ROOT_FOLDER_ID,
        "total_size": total_size,
        "library_total": len(all_local_items),
        "library_total_size": sum(int(item.get("size") or 0) for item in all_local_items),
    }


def old_video_asset_candidates() -> list[dict[str, Any]]:
    cutoff = datetime.now(UTC) - timedelta(days=30)
    candidates: list[dict[str, Any]] = []
    for job in store.local_asset_jobs():
        if not local_job_is_owned(job):
            continue
        if str(job.get("request", {}).get("media_type") or "") != "video":
            continue
        try:
            created_at = datetime.fromisoformat(str(job.get("created_at") or ""))
        except ValueError:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if created_at > cutoff:
            continue
        result_path = Path(str(job.get("result_path") or ""))
        if not result_path.is_file():
            continue
        candidates.append(
            {
                "asset_id": f"job::{job['id']}",
                "job_id": str(job["id"]),
                "name": str(job.get("title") or result_path.name),
                "file_name": result_path.name,
                "size": result_path.stat().st_size,
                "created_at": str(job.get("created_at") or ""),
                "folder_id": job.get("folder_id"),
            }
        )
    return sorted(candidates, key=lambda item: item.get("created_at") or "")


@app.get("/api/v1/assets/local/clear-old-video/preview", dependencies=[Depends(authorize)])
async def preview_old_video_assets():
    items = old_video_asset_candidates()
    return {
        "items": items,
        "count": len(items),
        "total_size": sum(int(item.get("size") or 0) for item in items),
        "cutoff_days": 30,
    }


@app.post("/api/v1/assets/local/clear-old-video", dependencies=[Depends(authorize)])
async def clear_old_video_assets():
    candidates = old_video_asset_candidates()
    deleted: list[str] = []
    for item in candidates:
        if store.delete_artifacts(item["job_id"]):
            deleted.append(item["asset_id"])
    return {
        "deleted": deleted,
        "count": len(deleted),
        "total_size": sum(
            int(item.get("size") or 0)
            for item in candidates
            if item["asset_id"] in deleted
        ),
        "cutoff_days": 30,
    }


@app.post("/api/v1/assets/local/delete", dependencies=[Depends(authorize)])
async def delete_local_assets(payload: LocalAssetsDeleteRequest):
    deleted: list[str] = []
    rejected: list[str] = []
    for asset_id in dict.fromkeys(payload.asset_ids):
        if asset_id.startswith("job::"):
            job_id = asset_id.removeprefix("job::")
            job = store.get(job_id) if job_id else None
            if job and local_job_is_owned(job) and store.delete_artifacts(job_id):
                deleted.append(asset_id)
            else:
                rejected.append(asset_id)
            continue
        if asset_id.startswith("protected::"):
            rejected.append(asset_id)
            continue
        rejected.append(asset_id)
    return {"deleted": deleted, "rejected": rejected}


@app.post("/api/v1/assets/local/unlock", dependencies=[Depends(authorize)])
async def unlock_local_peer_assets(payload: PeerAssetUnlockRequest):
    metadata = _protected_asset_metadata(payload.owner_device_id)
    try:
        key_id = local_state.records_key_id(payload.records_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    matches = [item for item in metadata if secrets.compare_digest(str(item.get("key_id") or ""), key_id)]
    if not matches:
        raise HTTPException(status_code=422, detail="远程记录密钥不匹配")
    verified = False
    for item in matches:
        snapshot_record_id = str(
            item.get("snapshot_record_id")
            or f"job-snapshot:{payload.owner_device_id}:{item['job_id']}"
        )
        try:
            snapshot = local_state.read_peer_encrypted_record(
                snapshot_record_id,
                payload.owner_device_id,
                payload.records_key,
            )
            if isinstance(snapshot, dict):
                verified = True
                break
        except (InvalidTag, UnicodeDecodeError, ValueError):
            continue
    if not verified:
        raise HTTPException(status_code=422, detail="远程记录密钥不匹配")
    local_state.cache_unlocked_peer_key(
        payload.owner_device_id, key_id, payload.records_key
    )
    return {"unlocked": len(matches), "owner_device_id": payload.owner_device_id, "key_id": key_id}


@app.get(
    "/api/v1/assets/local/protected/{peer_device_id}/{job_id}/result",
    dependencies=[Depends(authorize)],
)
async def get_protected_local_asset(peer_device_id: str, job_id: str):
    metadata = _find_protected_asset(peer_device_id, job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="加密素材不存在")
    if metadata.get("asset_deleted"):
        raise HTTPException(status_code=410, detail="该资产已删除")
    key_id = str(metadata.get("key_id") or "")
    records_key = local_state.unlocked_peer_key(peer_device_id, key_id)
    if not records_key:
        raise HTTPException(status_code=423, detail="文件被加密，请先输入所属设备密钥")
    result_file = next(
        (
            item
            for item in metadata.get("result_files", []) or []
            if item.get("kind") == "result"
        ),
        None,
    )
    if not result_file:
        raise HTTPException(status_code=410, detail="该资产已删除")
    encrypted_path = _safe_local_data_path(str(result_file.get("encrypted_path") or ""))
    if not encrypted_path or not encrypted_path.is_file():
        raise HTTPException(status_code=410, detail="加密产物文件已不存在")
    packed = encrypted_path.read_bytes()
    if not packed.startswith(b"H3E1") or len(packed) < 17:
        raise HTTPException(status_code=500, detail="加密产物格式无效")
    try:
        content = local_state.decrypt_peer_bytes(
            packed[16:], packed[4:16], peer_device_id, records_key
        )
    except InvalidTag as exc:
        local_state.clear_unlocked_peer_key(peer_device_id)
        raise HTTPException(status_code=423, detail="所属设备密钥已失效") from exc
    file_name = str(metadata.get("file_name") or result_file.get("original_path") or "")
    _, mime_type = _asset_media_type(str(metadata.get("media_type") or "file"), file_name)
    return Response(content=content, media_type=mime_type)


@app.post("/api/v1/assets/delete-artifacts", dependencies=[Depends(authorize)])
async def delete_asset_artifacts(payload: AssetArtifactsDeleteRequest):
    deleted: list[str] = []
    rejected: list[str] = []
    for job_id in payload.job_ids:
        if job_id.startswith("peer::") or not store.get(job_id):
            rejected.append(job_id)
            continue
        if store.delete_artifacts(job_id):
            deleted.append(job_id)
    return {"deleted": deleted, "rejected": rejected}


@app.get("/api/v1/generations/{job_id}/result", dependencies=[Depends(authorize)])
async def get_result(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="任务尚未完成")
    if job.get("request", {}).get("remote_proxy") and not job.get("result_path"):
        peer = local_state.peer(str(job.get("proxy_peer_id") or ""), include_secrets=True)
        remote_id = str(job.get("proxy_remote_job_id") or "")
        if not peer or not remote_id:
            raise HTTPException(status_code=410, detail="远程代理记录已不存在")
        if local_state.backup_outputs_enabled():
            output_dir = settings.outputs_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            try:
                async with httpx.AsyncClient(base_url=peer["base_url"], timeout=httpx.Timeout(120, connect=10), trust_env=False) as client:
                    response = await client.get(
                        f"/api/v1/peering/export/generations/{remote_id}/result",
                        headers={"Authorization": f"Bearer {peer['access_token']}"},
                    )
                    response.raise_for_status()
                output_path = output_dir / output_file_name(job, remote_output_suffix(response, str(job.get('request', {}).get('media_type') or 'file')))
                output_path.write_bytes(response.content)
                store.update(job_id, result_path=str(output_path), result_url=f"/api/v1/generations/{job_id}/result")
                job = store.get(job_id) or job
            except (httpx.HTTPError, OSError) as exc:
                raise HTTPException(status_code=502, detail=f"远程产物下载失败：{exc}") from exc
        else:
            return await proxy_peer_response(peer, f"/api/v1/peering/export/generations/{remote_id}/result")
    path = Path(job["result_path"])
    if not path.exists():
        raise HTTPException(status_code=410, detail="结果文件已不存在")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@app.get("/api/v1/generations/{job_id}/preview", dependencies=[Depends(authorize)])
async def get_generation_preview(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    preview = Path(str(job.get("preview_path") or ""))
    result = Path(str(job.get("result_path") or ""))
    if not preview.is_file() and result.is_file():
        preview = create_video_preview(result) or Path("")
        if preview.is_file():
            store.update(job_id, preview_path=str(preview), preview_url=f"/api/v1/generations/{job_id}/preview")
    if not preview.is_file():
        raise HTTPException(status_code=410, detail="视频封面不存在")
    return FileResponse(
        preview,
        media_type="image/jpeg",
        filename=preview.name,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.patch("/api/v1/generations/{job_id}/name", dependencies=[Depends(authorize)])
async def rename_generation(job_id: str, payload: GenerationRename):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.get("status") != "completed" or not job.get("result_path"):
        raise HTTPException(status_code=409, detail="仅已完成且存在产物的任务支持重命名")
    return store.public(rename_job_output(job, payload.name)["id"])


@app.get("/api/v1/generations/{job_id}/references/{index}", dependencies=[Depends(authorize)])
async def get_reference(job_id: str, index: int):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    input_paths = job.get("input_paths", [])
    references = job.get("request", {}).get("references", [])
    if index < 0 or index >= len(input_paths) or index >= len(references):
        raise HTTPException(status_code=404, detail="参考素材不存在")
    path = Path(input_paths[index]).resolve()
    upload_root = (settings.uploads_dir / job_id).resolve()
    try:
        path.relative_to(upload_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="参考素材不存在") from exc
    if not path.is_file():
        raise HTTPException(status_code=410, detail="参考素材已不存在")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@app.get("/api/v1/logs", dependencies=[Depends(authorize)])
async def get_logs(limit: Annotated[int, Query(ge=1, le=500)] = 100):
    return {
        "data": store.logs(limit),
        "queue": manager.queue_snapshot(),
        "nodes": manager.nodes_public(),
        "revision": f"{store.revision}:{manager.revision}",
    }


@app.get("/api/v1/events", dependencies=[Depends(authorize)])
async def stream_events(
    request: Request,
    since: Annotated[int, Query(ge=0)] = 0,
):
    store_cursor = event_store_cursor(request.headers.get("last-event-id", ""), since)

    async def events() -> AsyncIterator[str]:
        nonlocal store_cursor
        last_revision = ""
        idle_ticks = 0
        peer_tasks: dict[str, asyncio.Task[None]] = {}
        peer_events: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        stop_event = asyncio.Event()
        yield "retry: 3000\n\n"
        try:
            while not await request.is_disconnected():
                peers = {
                    str(peer["device_id"]): peer
                    for peer in local_state.peers(include_secrets=True)
                    if local_state.sharing_enabled
                }
                for peer_id in list(peer_tasks):
                    if peer_id in peers:
                        continue
                    peer_tasks.pop(peer_id).cancel()
                    await peer_events.put(
                        ("peer_removed", {"peer_device_id": peer_id})
                    )
                for peer_id, peer in peers.items():
                    if peer_id not in peer_tasks or peer_tasks[peer_id].done():
                        peer_tasks[peer_id] = asyncio.create_task(
                            relay_peer_events(peer, peer_events, stop_event)
                        )

                peering_revision, _ = local_state.events_since(0)
                pairing_period = int(time.time() // 30) if local_state.sharing_enabled else 0
                payload = local_event_snapshot(store_cursor)
                revision = (
                    f"{payload['revision']}:{peering_revision}:{pairing_period}"
                )
                if revision != last_revision:
                    payload["revision"] = revision
                    payload["peering_status"] = peer_status_payload()
                    yield (
                        f"id: {revision}\n"
                        "event: snapshot\n"
                        f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    )
                    store_cursor = int(payload["store_revision"])
                    last_revision = revision
                    idle_ticks = 0

                remote_event_sent = False
                while not peer_events.empty():
                    event_type, remote_payload = peer_events.get_nowait()
                    yield (
                        f"event: {event_type}\n"
                        f"data: {json.dumps(remote_payload, ensure_ascii=False)}\n\n"
                    )
                    remote_event_sent = True
                if remote_event_sent:
                    idle_ticks = 0
                elif revision == last_revision:
                    idle_ticks += 1
                    if idle_ticks >= 15:
                        yield ": keep-alive\n\n"
                        idle_ticks = 0
                await asyncio.sleep(1)
        finally:
            stop_event.set()
            tasks = list(peer_tasks.values())
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def openai_chat_url(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=422, detail="Base URL 必须是有效的 HTTP(S) 地址")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def openai_stream_response(
    url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float,
) -> StreamingResponse:
    async def stream() -> AsyncIterator[str]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request_body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "stream": True,
        }
        try:
            timeout = httpx.Timeout(180, connect=20)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                async with client.stream("POST", url, headers=headers, json=request_body) as response:
                    if not response.is_success:
                        detail = (await response.aread()).decode("utf-8", errors="replace")[:800]
                        message = f"上游 AI 服务返回 {response.status_code}: {detail}"
                        yield f"event: error\ndata: {json.dumps({'message': message}, ensure_ascii=False)}\n\n"
                        return
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(raw)
                            choice = (chunk.get("choices") or [{}])[0]
                            text = (choice.get("delta") or {}).get("content")
                            if text is None:
                                text = (choice.get("message") or {}).get("content")
                            if text:
                                yield f"event: delta\ndata: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
                        except (json.JSONDecodeError, TypeError, AttributeError):
                            continue
            yield "event: done\ndata: {}\n\n"
        except httpx.HTTPError as exc:
            message = f"无法连接 AI 服务：{exc}"
            yield f"event: error\ndata: {json.dumps({'message': message}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/v1/prompts/optimize", dependencies=[Depends(authorize)])
async def optimize_prompt(payload: OptimizePromptRequest):
    if payload.execution_mode != "tts" and payload.duration > 15 and payload.execution_mode != "h3-sa":
        raise HTTPException(status_code=422, detail="提示词优化的 H3 时长范围为 1–15 秒")
    if payload.execution_mode == "native" and payload.duration > 15:
        raise HTTPException(status_code=422, detail="普通 H3 提示词优化的时长范围为 1–15 秒")
    url = openai_chat_url(payload.base_url)
    stored_ai = local_state.ai_config(include_secret=True)
    api_key = str(stored_ai.get("api_key") or "")
    labels = []
    if payload.execution_mode == "tts":
        for index, item in enumerate(
            (item for item in payload.references if item.get("type") == "audio"),
            start=1,
        ):
            labels.append(f"<Audio {index}>：{item.get('name') or '人物音频参考'}")
        system_prompt = TTS_SYSTEM_PROMPT
    elif payload.model_variant == "fl2va-fp8":
        for index, item in enumerate(payload.references[:2], start=1):
            if item.get("type") != "image":
                continue
            role = "首帧" if index == 1 else "尾帧"
            labels.append(f"<Picture {index}>（{role}）：{item.get('name') or '参考图片'}")
        system_prompt = FL2VA_SYSTEM_PROMPT
    else:
        counts = {"image": 0, "video": 0, "audio": 0}
        prefixes = {"image": "Picture", "video": "Video", "audio": "Audio"}
        for item in payload.references:
            kind = item.get("type", "")
            if kind not in counts:
                continue
            counts[kind] += 1
            labels.append(
                f"<{prefixes[kind]} {counts[kind]}>：{item.get('name') or '参考素材'}"
            )
        system_prompt = REF2VA_SYSTEM_PROMPT
    context = "\n".join(labels) if labels else "未提供带名称的参考素材。"
    if payload.execution_mode == "tts":
        user_message = (
            f"目标音频时长：{payload.duration:g} 秒。\n"
            f"按说话者顺序排列的音频参考：\n{context}\n\n"
            f"用户提供的人物特征与完整对白：\n{payload.prompt.strip()}\n\n"
            "输出符合 H3 Ref2VA 习惯的六段式英文提示词，并保持对白原始语言和原文。"
        )
    else:
        user_message = (
            f"目标视频时长：{payload.duration:g} 秒。\n"
            f"按稳定顺序排列的参考素材：\n{context}\n\n"
            f"用户的自然语言需求：\n{payload.prompt.strip()}\n\n"
            "请严格使用简体中文输出最终 H3 提示词。"
        )

    return openai_stream_response(
        url,
        api_key,
        payload.model,
        system_prompt,
        user_message,
        0.3,
    )


@app.post("/api/v1/music/assist", dependencies=[Depends(authorize)])
async def assist_music(payload: MusicAssistRequest):
    url = openai_chat_url(payload.base_url)
    stored_ai = local_state.ai_config(include_secret=True)
    api_key = str(stored_ai.get("api_key") or "")
    lyrics = payload.lyrics.strip() or "未提供歌词或歌词草稿。"
    if payload.task == "arrangement":
        system_prompt = MUSIC3_ARRANGEMENT_SYSTEM_PROMPT
        user_message = (
            f"Target duration: {payload.duration:g} seconds.\n\n"
            f"Music description:\n{payload.prompt.strip()}\n\n"
            f"Tagged lyrics for emotional context and section directives only:\n{lyrics}"
        )
        temperature = 0.35
    else:
        system_prompt = MUSIC3_LYRICS_SYSTEM_PROMPT
        user_message = (
            f"目标时长：{payload.duration:g} 秒。\n\n"
            f"歌曲需求：\n{payload.prompt.strip()}\n\n"
            f"现有歌词或草稿：\n{lyrics}"
        )
        temperature = 0.65
    return openai_stream_response(
        url,
        api_key,
        payload.model,
        system_prompt,
        user_message,
        temperature,
    )


static_dir = Path(__file__).resolve().parents[1] / "static"
app.mount("/assets", StaticFiles(directory=static_dir), name="assets")


@app.get("/AGENT.md", include_in_schema=False)
async def agent_documentation():
    document_path = Path(__file__).resolve().parents[1] / "AGENT.md"
    try:
        content = document_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=503, detail="AGENT.md 暂不可用") from exc
    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(
        static_dir / "index.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
