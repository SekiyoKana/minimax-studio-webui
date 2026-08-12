from __future__ import annotations

import asyncio
import json
import math
import mimetypes
import secrets
import shutil
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncIterator, Literal
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .engine import create_engine
from .jobs import JobManager, JobStore, TERMINAL_STATES, utc_now
from .prompts import FL2VA_SYSTEM_PROMPT
from .ref2va_prompts import REF2VA_SYSTEM_PROMPT
from .settings import settings


ExecutionMode = Literal["native", "turbo-lora", "h3-nsfw", "digital-human"]


settings.ensure_directories()
store = JobStore(settings.jobs_dir)
manager = JobManager(store, lambda: create_engine(settings))


@asynccontextmanager
async def lifespan(_: FastAPI):
    manager.start()
    yield
    manager.stop()


app = FastAPI(
    title="MiniMax H3 FP8 API",
    version="5.0.0",
    description="ComfyUI-backed MiniMax H3 FL2VA and Ref2VA video generation.",
    lifespan=lifespan,
)


class GenerationPatch(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    title: str | None = Field(None, max_length=120)
    prompt: str | None = Field(None, min_length=8, max_length=12000)
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    steps: int | None = None
    seed: int | None = Field(None, ge=0, le=2**31 - 1)
    model_variant: Literal["fl2va-fp8", "ref2va-fp8"] | None = None
    execution_mode: ExecutionMode | None = None


class OptimizePromptRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prompt: str = Field(min_length=2, max_length=12000)
    base_url: str = Field(min_length=8, max_length=500)
    api_key: str = Field(default="", max_length=1000)
    model: str = Field(min_length=1, max_length=200)
    references: list[dict[str, str]] = Field(default_factory=list, max_length=15)
    duration: float = Field(default=5, ge=1, le=15)
    model_variant: Literal["fl2va-fp8", "ref2va-fp8"] = "fl2va-fp8"


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
    if width % 32 or height % 32 or width < 352 or height < 352:
        raise HTTPException(status_code=422, detail="宽高必须是 32 的倍数，且不低于 352×352")
    if not 1 <= duration <= 15:
        raise HTTPException(status_code=422, detail="时长范围为 1–15 秒")
    if execution_mode == "turbo-lora" and steps != 8:
        raise HTTPException(status_code=422, detail="8-step LoRA 加速模式固定使用 8 步")
    if execution_mode == "digital-human" and steps != 20:
        raise HTTPException(status_code=422, detail="数字人模式固定使用 20 步")
    if execution_mode not in {"turbo-lora", "digital-human"} and not 4 <= steps <= 50:
        raise HTTPException(status_code=422, detail="采样步数范围为 4–50")


def classify_upload(upload: UploadFile) -> str:
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
    raise HTTPException(status_code=422, detail=f"不支持的素材类型：{upload.filename}")


def validate_references(
    model_variant: str,
    kinds: list[str],
    execution_mode: str = "native",
) -> None:
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
    if execution_mode in {"native", "turbo-lora"}:
        return
    if execution_mode == "digital-human":
        if model_variant != "ref2va-fp8":
            raise HTTPException(status_code=422, detail="数字人模式仅支持 Ref2VA FP8")
        return
    if execution_mode != "h3-nsfw":
        raise HTTPException(status_code=422, detail="不支持的执行方案")
    if not incognito:
        raise HTTPException(status_code=403, detail="H3 NSFW 模式仅限无痕模式")
    if model_variant != "ref2va-fp8":
        raise HTTPException(status_code=422, detail="H3 NSFW 模式仅支持 Ref2VA FP8")


def probe_media(path: Path) -> tuple[float, bool]:
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
    if duration < 1 or duration > 15.1:
        raise HTTPException(status_code=422, detail=f"视频和音频素材时长必须为 1–15 秒：{path.name}")
    return duration, has_audio


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
    return {
        "status": "ok",
        "engine": "fake" if settings.fake_engine else settings.engine_backend,
        "gpu": settings.gpu_label,
        "queue_depth": manager.queue_depth,
        "revision": store.revision,
    }


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
):
    items, total = store.list(
        page,
        page_size,
        status_filter,
        query,
        include_incognito=include_incognito,
        scope=scope,
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
    }


@app.post("/api/v1/generations", status_code=202, dependencies=[Depends(authorize)])
async def create_generation(
    prompt: Annotated[str, Form(description="MiniMax H3 audiovisual generation prompt.")],
    reference_manifest: Annotated[str, Form(description="Ordered image, video, and audio reference manifest.")],
    references: Annotated[list[UploadFile], File(description="Reference files in manifest order.")],
    model_variant: Annotated[Literal["fl2va-fp8", "ref2va-fp8"], Form()] = "fl2va-fp8",
    execution_mode: Annotated[ExecutionMode, Form()] = "native",
    width: Annotated[int, Form()] = 832,
    height: Annotated[int, Form()] = 480,
    duration: Annotated[float, Form()] = 5,
    steps: Annotated[int, Form()] = 10,
    seed: Annotated[str | None, Form()] = None,
    title: Annotated[str | None, Form(max_length=120)] = None,
    incognito: Annotated[bool, Form()] = False,
    incognito_code: Annotated[str | None, Header(alias="X-H3-Incognito-Code")] = None,
):
    prompt = prompt.strip()
    if len(prompt) < 8:
        raise HTTPException(status_code=422, detail="提示词至少需要 8 个字符")
    if incognito and not secrets.compare_digest(incognito_code or "", settings.incognito_code):
        raise HTTPException(status_code=403, detail="无痕模式授权已失效")
    validate_execution_mode(execution_mode, model_variant, incognito)
    validate_generation(width, height, duration, steps, execution_mode)

    try:
        seed_raw = (seed or "").strip()
        seed_value = int(seed_raw) if seed_raw else secrets.randbelow(2**31)
        manifest = json.loads(reference_manifest)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="参数格式不正确") from exc
    if not 0 <= seed_value < 2**31:
        raise HTTPException(status_code=422, detail="随机种子超出范围")
    if not isinstance(manifest, list):
        raise HTTPException(status_code=422, detail="reference_manifest 必须是数组")

    uploads = references
    if len(uploads) != len(manifest):
        raise HTTPException(status_code=422, detail="素材数量与 reference_manifest 不一致")

    kinds = [classify_upload(upload) for upload in uploads]
    if any(not isinstance(item, dict) for item in manifest):
        raise HTTPException(status_code=422, detail="reference_manifest 的每一项必须是对象")
    if kinds != [item.get("type") for item in manifest]:
        raise HTTPException(status_code=422, detail="素材顺序或类型与 reference_manifest 不一致")
    validate_references(model_variant, kinds, execution_mode)

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
            if model_variant == "fl2va-fp8":
                item["role"] = "first_frame" if index == 1 else "last_frame"
            if kind in {"video", "audio"}:
                media_duration, has_audio = probe_media(destination)
                item["duration"] = round(media_duration, 3)
                if kind == "video":
                    item["has_audio"] = has_audio
            input_paths.append(str(destination))
            public_manifest.append(item)
    except Exception:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise

    if execution_mode == "digital-human":
        audio_reference = next(item for item in public_manifest if item["type"] == "audio")
        duration = float(audio_reference["duration"])
        validate_generation(width, height, duration, steps, execution_mode)

    created_at = utc_now()
    job = {
        "id": job_id,
        "title": (title or prompt.splitlines()[0])[:120],
        "status": "queued",
        "stage": "等待 ComfyUI FP8 执行",
        "progress": 0,
        "created_at": created_at,
        "updated_at": created_at,
        "cancel_requested": False,
        "request": {
            "prompt": prompt,
            "model_variant": model_variant,
            "execution_mode": execution_mode,
            "width": width,
            "height": height,
            "duration": duration,
            "num_frames": align_frames(duration),
            "steps": steps,
            "seed": seed_value,
            "references": public_manifest,
            "incognito": incognito,
        },
        "input_paths": input_paths,
    }
    store.create(job)
    manager.submit(job_id)
    response = store.public(job_id, manager.queue_position(job_id))
    response["status_url"] = f"/api/v1/generations/{job_id}"
    return response


@app.get("/api/v1/generations/{job_id}", dependencies=[Depends(authorize)])
async def get_generation(job_id: str):
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
    validate_execution_mode(
        request_data["execution_mode"],
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
        request_data["execution_mode"],
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
        request_data["execution_mode"],
    )
    request_data["num_frames"] = align_frames(request_data["duration"])
    changes: dict[str, object] = {"request": request_data, "event_message": "任务参数已修改"}
    if title is not None:
        changes["title"] = title.strip() or job.get("title", "")
    store.update(job_id, **changes)
    return store.public(job_id, manager.queue_position(job_id))


@app.post("/api/v1/generations/{job_id}/cancel", status_code=202, dependencies=[Depends(authorize)])
async def cancel_generation(job_id: str):
    if not store.get(job_id):
        raise HTTPException(status_code=404, detail="任务不存在")
    if not manager.cancel(job_id):
        raise HTTPException(status_code=409, detail="任务已结束，无法取消")
    return store.public(job_id, manager.queue_position(job_id))


@app.delete("/api/v1/generations/{job_id}", dependencies=[Depends(authorize)])
async def delete_generation(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job["status"] not in TERMINAL_STATES:
        raise HTTPException(status_code=409, detail="请先取消任务，任务结束后再删除")
    manager.remove(job_id)
    store.delete(job_id)
    return {"id": job_id, "status": "deleted"}


@app.get("/api/v1/generations/{job_id}/result", dependencies=[Depends(authorize)])
async def get_result(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="任务尚未完成")
    path = Path(job["result_path"])
    if not path.exists():
        raise HTTPException(status_code=410, detail="结果文件已不存在")
    media_type = "video/mp4" if path.suffix == ".mp4" else "image/jpeg"
    return FileResponse(path, media_type=media_type, filename=path.name)


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
        "revision": store.revision,
    }


@app.get("/api/v1/events", dependencies=[Depends(authorize)])
async def stream_events(request: Request):
    async def events() -> AsyncIterator[str]:
        last_revision = -1
        idle_ticks = 0
        while not await request.is_disconnected():
            revision = store.revision
            if revision != last_revision:
                payload = {
                    "revision": revision,
                    "logs": store.logs(100),
                    "queue": manager.queue_snapshot(),
                }
                yield f"event: snapshot\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                last_revision = revision
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks >= 15:
                    yield ": keep-alive\n\n"
                    idle_ticks = 0
            await asyncio.sleep(1)

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def openai_chat_url(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=422, detail="Base URL 必须是有效的 HTTP(S) 地址")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


@app.post("/api/v1/prompts/optimize", dependencies=[Depends(authorize)])
async def optimize_prompt(payload: OptimizePromptRequest):
    url = openai_chat_url(payload.base_url)
    labels = []
    if payload.model_variant == "fl2va-fp8":
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
    user_message = (
        f"目标视频时长：{payload.duration:g} 秒。\n"
        f"按稳定顺序排列的参考素材：\n{context}\n\n"
        f"用户的自然语言需求：\n{payload.prompt.strip()}\n\n"
        "请严格使用简体中文输出最终 H3 提示词。"
    )

    async def stream() -> AsyncIterator[str]:
        headers = {"Content-Type": "application/json"}
        if payload.api_key:
            headers["Authorization"] = f"Bearer {payload.api_key}"
        request_body = {
            "model": payload.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.3,
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
            message = f"无法连接提示词优化服务：{exc}"
            yield f"event: error\ndata: {json.dumps({'message': message}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


static_dir = Path(__file__).resolve().parents[1] / "static"
app.mount("/assets", StaticFiles(directory=static_dir), name="assets")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(static_dir / "index.html")


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
