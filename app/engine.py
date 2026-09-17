from __future__ import annotations

import json
import logging
import math
import mimetypes
import os
import re
import shutil
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from PIL import Image

from .nodes import ComfyNodeConfig
from .jobs import output_file_name
from .runninghub import (
    build_ai_app_schema,
    build_workflow_schema,
    node_info_list as build_runninghub_node_info_list,
    output_media_type,
)
from .settings import Settings


logger = logging.getLogger(__name__)


class RunningHubTransientResponseError(RuntimeError):
    pass


class RemoteTaskUnavailableError(RuntimeError):
    retry_remote_checkpoint = True


class RemoteTaskNotFoundError(RuntimeError):
    retry_fresh_task = True


def _remote_checkpoint_id(
    checkpoint: dict[str, Any] | None,
    provider: str,
    node_id: str,
) -> str:
    if not checkpoint:
        return ""
    remote_id = str(checkpoint.get("remote_id") or "")
    if not remote_id:
        raise RuntimeError("远端任务 checkpoint 缺少任务标识")
    if str(checkpoint.get("provider") or "") != provider:
        raise RuntimeError("远端任务 checkpoint 的服务类型与当前节点不一致")
    if str(checkpoint.get("node_id") or "") != node_id:
        raise RuntimeError("远端任务 checkpoint 的节点与当前节点不一致")
    return remote_id


def _write_remote_checkpoint(
    callback: Callable[[dict[str, Any] | None], None] | None,
    *,
    provider: str,
    node_id: str,
    remote_id: str,
    client_id: str = "",
) -> None:
    if callback:
        checkpoint = {
            "provider": provider,
            "node_id": node_id,
            "remote_id": remote_id,
            "submitted_at": datetime.now(UTC).isoformat(),
        }
        if client_id:
            checkpoint["client_id"] = client_id
        callback(checkpoint)


def _runninghub_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def runninghub_account_profile(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        raise RuntimeError("RunningHub 账户状态响应缺少 data")
    current_tasks = _runninghub_number(data.get("currentTaskCounts"))
    return {
        "account_balance_coins": _runninghub_number(data.get("remainCoins")),
        "account_balance_money": _runninghub_number(data.get("remainMoney")),
        "account_currency": str(data.get("currency") or "").upper(),
        "account_current_tasks": int(current_tasks) if current_tasks is not None else None,
        "account_api_type": str(data.get("apiType") or "").upper(),
    }


def runninghub_billing_delta(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, Any]:
    def consumed(field: str) -> float | None:
        previous = _runninghub_number(before.get(field))
        current = _runninghub_number(after.get(field))
        if previous is None or current is None or current > previous:
            return None
        return round(previous - current, 6)

    return {
        **after,
        "consumed_coins": consumed("account_balance_coins"),
        "consumed_money": consumed("account_balance_money"),
        "measured_at": datetime.now(UTC).isoformat(),
    }


class ProgressAdapter:
    def __init__(self, total: int, callback: Callable[[int, str], None], cancelled: Callable[[], bool]):
        self.total = max(1, total)
        self.callback = callback
        self.cancelled = cancelled

    def __call__(self, iterable):
        for index, item in enumerate(iterable):
            if self.cancelled():
                raise InterruptedError("generation cancelled")
            percent = 20 + round((index / self.total) * 68)
            self.callback(percent, f"联合音视频采样 {index + 1}/{self.total}")
            yield item


class FakeEngine:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, job, progress, cancelled):
        progress(50, "测试模式")
        if job["request"].get("model_variant") == "music3-int8" or job["request"].get("execution_mode") == "tts":
            import wave

            output = self.settings.outputs_dir / output_file_name(job, ".wav")
            with wave.open(str(output), "wb") as target:
                target.setnchannels(1 if job["request"].get("execution_mode") == "tts" else 2)
                target.setsampwidth(2)
                target.setframerate(32000)
                target.writeframes(b"\0\0" * 3200)
            return output
        source = Path(job["input_paths"][0])
        output = self.settings.outputs_dir / output_file_name(job, ".jpg")
        shutil.copy2(source, output)
        return output


class MiniMaxH3Engine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pipe = None

    def _validate_models(self) -> None:
        required = {
            "Ref2VA DiT": self.settings.dit_path,
            "Qwen3-VL text encoder": self.settings.text_encoder_path,
            "video VAE": self.settings.video_vae_path,
            "audio VAE": self.settings.audio_vae_path,
            "processor": self.settings.processor_path,
        }
        missing = [f"{name}: {path}" for name, path in required.items() if not path.exists()]
        if missing:
            raise FileNotFoundError("缺少模型文件：" + "; ".join(missing))

    def _select_gpu(
        self,
        progress: Callable[[int, str], None],
        cancelled: Callable[[], bool],
    ) -> int:
        threshold_mib = round(self.settings.min_free_vram_gb * 1024)
        while True:
            try:
                output = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.free",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                )
                free_mib = [
                    int(line.strip())
                    for line in output.splitlines()
                    if line.strip()
                ]
            except (OSError, subprocess.SubprocessError, ValueError):
                free_mib = []

            candidates = [
                (available, index)
                for index, available in enumerate(free_mib)
                if available >= threshold_mib
            ]
            if candidates:
                available, index = max(candidates)
                progress(2, f"已选择 GPU {index}（空闲 {available / 1024:.1f} GiB）")
                return index
            progress(
                1,
                "等待任意 GPU 空闲（当前 "
                + ", ".join(
                    f"GPU {index}: {available / 1024:.1f} GiB"
                    for index, available in enumerate(free_mib)
                )
                + f"；需要 {self.settings.min_free_vram_gb:g} GiB）",
            )
            for _ in range(10):
                if cancelled():
                    raise InterruptedError("generation cancelled")
                time.sleep(1)

    def _load(
        self,
        progress: Callable[[int, str], None],
        cancelled: Callable[[], bool],
    ) -> None:
        if self.pipe is not None:
            return
        self._validate_models()
        selected_gpu = self._select_gpu(progress, cancelled)
        os.environ["CUDA_VISIBLE_DEVICES"] = str(selected_gpu)
        import torch
        from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline, ModelConfig
        from .diffsynth_compat import register_comfy_vae_configs

        torch.cuda.set_device(0)
        progress(3, "加载独立 DiffSynth 推理引擎")
        register_comfy_vae_configs()
        vram = {
            "offload_dtype": torch.bfloat16,
            "offload_device": "cpu",
            "onload_dtype": torch.bfloat16,
            "onload_device": "cpu",
            "preparing_dtype": torch.bfloat16,
            "preparing_device": "cuda",
            "computation_dtype": torch.bfloat16,
            "computation_device": "cuda",
        }
        self.pipe = MiniMaxH3Pipeline.from_pretrained(
            torch_dtype=torch.bfloat16,
            device="cuda",
            model_configs=[
                ModelConfig(path=str(self.settings.text_encoder_path), **vram),
                ModelConfig(path=str(self.settings.dit_path), **vram),
                ModelConfig(path=str(self.settings.video_vae_path), **vram),
                ModelConfig(path=str(self.settings.audio_vae_path)),
            ],
            processor_config=ModelConfig(path=str(self.settings.processor_path), skip_download=True),
            vram_limit=self.settings.vram_limit_gb,
        )
        progress(15, "模型已就绪")

    @staticmethod
    def _read_video(path: str, height: int, width: int, fps: int = 24):
        from diffsynth.utils.data import VideoData

        video = VideoData(path, height=height, width=width)
        frames = video.raw_data()
        source_fps = float(video.data.reader.get_meta_data().get("fps", fps))
        duration = len(frames) / max(source_fps, 1)
        output_count = min(round(duration * fps), 15 * fps)
        output = []
        for index in range(output_count):
            source_index = min(round(index * source_fps / fps), len(frames) - 1)
            output.append(frames[source_index])
        return output

    def _build_references(self, job: dict[str, Any]) -> list[dict[str, Any]]:
        from diffsynth.utils.data.audio import read_audio

        references = []
        manifest = job["request"]["references"]
        for item, path in zip(manifest, job["input_paths"], strict=True):
            kind = item["type"]
            if kind == "image":
                references.append({"type": "image", "image": Image.open(path).convert("RGB")})
                continue
            if kind == "audio":
                waveform, sample_rate = read_audio(path, duration=15, resample=True, resample_rate=32000)
                references.append({"type": "audio", "audio": waveform, "sample_rate": sample_rate})
                continue
            frames = self._read_video(path, job["request"]["height"], job["request"]["width"])
            try:
                waveform, sample_rate = read_audio(
                    path,
                    duration=len(frames) / 24,
                    resample=True,
                    resample_rate=32000,
                )
                references.append(
                    {"type": "video_audio", "video": frames, "audio": waveform, "sample_rate": sample_rate}
                )
            except Exception:
                references.append({"type": "video", "video": frames})
        return references

    def generate(self, job, progress, cancelled):
        self._load(progress, cancelled)
        if cancelled():
            raise InterruptedError("generation cancelled")
        request = job["request"]
        progress(16, "解析参考素材")
        references = self._build_references(job)
        adapter = ProgressAdapter(request["steps"], progress, cancelled)
        video, audio = self.pipe(
            prompt=request["prompt"],
            height=request["height"],
            width=request["width"],
            num_frames=request["num_frames"],
            num_inference_steps=request["steps"],
            seed=request["seed"],
            references=references,
            tiled=True,
            tile_size=256,
            tile_overlap=64,
            progress_bar_cmd=adapter,
        )
        if cancelled():
            raise InterruptedError("generation cancelled")
        progress(90, "解码并写入音视频")
        from diffsynth.utils.data.audio_video import write_video_audio

        output = self.settings.outputs_dir / output_file_name(job, ".mp4")
        write_video_audio(
            video=video,
            audio=audio,
            output_path=str(output),
            fps=24,
            audio_sample_rate=self.pipe.audio_vae.sample_rate,
        )
        sidecar = output.with_suffix(".json")
        sidecar.write_text(json.dumps(job["request"], ensure_ascii=False, indent=2), encoding="utf-8")
        progress(99, "整理交付文件")
        return output


class ComfyUIH3Engine:
    H3_CONTEXT_FRAMES = 22
    H3_MAX_SEGMENT_FRAMES = 362
    NODE_STAGES = {
        "3": (7, "加载 Music3 文本编码器"),
        "6": (5, "加载 Music3 INT8 DiT"),
        "7": (9, "加载 Music3 音频解码器"),
        "13": (12, "编码音乐描述与歌词"),
        "9": (15, "Music3 音频采样"),
        "42": (92, "分块解码 Music3 音频"),
        "127": (6, "加载 MiniMax H3 FP8 模型"),
        "128": (8, "加载 Qwen3-VL 文本编码器"),
        "142": (10, "加载 H3 SA 8-step LoRA"),
        "143": (12, "应用 H3 Sigma Shift"),
        "141": (10, "加载 H3 NSFW LoRA"),
        "136": (12, "编码提示词与首尾帧"),
        "26": (27, "执行 H3 SA Latent 3D 放大"),
        "144": (38, "应用 H3 SA Sol-Attn / VDN-H3"),
        "171": (10, "加载数字人驱动音频"),
        "172": (14, "编码并锁定数字人驱动音频"),
        "125": (15, "联合音视频采样"),
        "149": (62, "H3 SA Sol-Attn 二阶段采样"),
        "121": (90, "解码音频"),
        "122": (92, "解码视频"),
        "130": (95, "合成音视频"),
        "92": (97, "保存 MP4 产物"),
    }

    def __init__(self, settings: Settings, node: ComfyNodeConfig | None = None):
        self.settings = settings
        self.node = node or ComfyNodeConfig("default", settings.gpu_label, settings.comfy_url)
        self.comfy_url = self.node.url.rstrip("/")
        self.api_headers = (
            {"Authorization": f"Bearer {self.node.api_key}"}
            if self.node.api_key
            else {}
        )

    @staticmethod
    def _variant(job: dict[str, Any]) -> str:
        # Jobs created before model selection was added are FL2VA jobs.
        return job.get("request", {}).get("model_variant") or "fl2va-fp8"

    @staticmethod
    def _execution_mode(job: dict[str, Any]) -> str:
        return job.get("request", {}).get("execution_mode") or "native"

    def _load_workflow(self, variant: str, execution_mode: str = "native") -> dict[str, Any]:
        workflow_paths = {
            ("fl2va-fp8", "native"): self.settings.comfy_workflow,
            ("fl2va-fp8", "turbo-lora"): self.settings.comfy_turbo_workflow,
            ("ref2va-fp8", "native"): self.settings.comfy_ref2va_workflow,
            ("ref2va-fp8", "turbo-lora"): self.settings.comfy_ref2va_turbo_workflow,
            ("ref2va-fp8", "dual-sampling"): self.settings.comfy_dual_sampling_workflow,
            ("fl2va-fp8", "h3-sa"): self.settings.comfy_sa_workflow,
            ("ref2va-fp8", "h3-sa"): self.settings.comfy_ref2va_sa_workflow,
            ("fl2va-fp8", "vdn-h3"): self.settings.comfy_vdn_workflow,
            ("ref2va-fp8", "vdn-h3"): self.settings.comfy_ref2va_vdn_workflow,
            ("ref2va-fp8", "h3-nsfw"): self.settings.comfy_nsfw_workflow,
            ("ref2va-fp8", "digital-human"): self.settings.comfy_digital_human_workflow,
            ("ref2va-fp8", "tts"): self.settings.comfy_tts_workflow,
            ("music3-int8", "music3"): self.settings.comfy_music3_workflow,
        }
        try:
            workflow_path = workflow_paths[(variant, execution_mode)]
        except KeyError as exc:
            raise ValueError(f"不支持的执行方案：{variant}/{execution_mode}") from exc
        if not workflow_path.exists():
            raise FileNotFoundError(f"ComfyUI 工作流不存在：{workflow_path}")
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        if variant == "music3-int8":
            required = {"3", "6", "7", "9", "10", "13", "15", "42", "92"}
            missing = sorted(required.difference(workflow))
            if missing:
                raise ValueError(f"ComfyUI Music3 工作流缺少节点：{', '.join(missing)}")
            return workflow
        required = {"92", "124", "125", "129", "136", "137"}
        if variant == "ref2va-fp8":
            required.discard("137")
        if execution_mode == "turbo-lora":
            required.update({"142", "143"})
        if execution_mode == "vdn-h3":
            required.add("144")
        if execution_mode in {"dual-sampling", "h3-sa"}:
            required = {"10", "11", "26", "35", "92", "119", "120", "121", "122", "123", "124", "125", "126", "127", "128", "129", "130", "136", "140", "142", "143", "144", "145", "146", "147", "148", "149", "150", "151"}
            if execution_mode == "h3-sa":
                required.discard("140")
            if execution_mode == "h3-sa" and variant == "fl2va-fp8":
                required.add("137")
        if execution_mode == "h3-nsfw":
            required.add("141")
        if execution_mode == "digital-human":
            required.update({"137", "171", "172"})
        if execution_mode == "tts":
            required.update({"119", "120", "121", "127", "128"})
        missing = sorted(required.difference(workflow))
        if missing:
            raise ValueError(f"ComfyUI 工作流缺少节点：{', '.join(missing)}")
        return workflow

    def _upload_inputs(self, client, job: dict[str, Any]) -> list[str]:
        paths = [Path(path) for path in job["input_paths"]]
        manifest = job["request"]["references"]
        if len(paths) != len(manifest):
            raise ValueError("参考素材清单与文件不一致")
        subfolder = f"minimax-studio-webui/{job['id']}"
        uploaded = []
        for index, (source, item) in enumerate(zip(paths, manifest, strict=True), start=1):
            suffix = source.suffix.lower() or ".bin"
            filename = f"{index:02d}_{item['type']}{suffix}"
            content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            with source.open("rb") as handle:
                response = client.post(
                    "/upload/image",
                    data={"type": "input", "subfolder": subfolder, "overwrite": "true"},
                    files={"image": (filename, handle, content_type)},
                )
            response.raise_for_status()
            result = response.json()
            stored_name = str(result.get("name") or filename)
            stored_folder = str(result.get("subfolder") or subfolder).strip("/")
            uploaded.append(f"{stored_folder}/{stored_name}" if stored_folder else stored_name)
        return uploaded

    @staticmethod
    def _comfy_cuda_device(system_stats: dict[str, Any]) -> str:
        for device in system_stats.get("devices", []):
            if device.get("type") == "cuda" and isinstance(device.get("index"), int):
                return f"cuda:{device['index']}"
        raise RuntimeError("当前 ComfyUI 节点未报告 CUDA 设备，Music3 无法执行")

    def _build_workflow(
        self,
        job: dict[str, Any],
        input_names: list[str],
        music3_device: str | None = None,
        context_video_name: str | None = None,
        context_latent_path: str | None = None,
        context_clip_index: int = 0,
        save_latent_prefix: str | None = None,
        save_latent_clip_index: int = 0,
    ) -> dict[str, Any]:
        variant = self._variant(job)
        execution_mode = self._execution_mode(job)
        workflow = self._load_workflow(variant, execution_mode)
        request = job["request"]
        workflow["92"]["inputs"]["filename_prefix"] = f"minimax-studio-webui/{job['id']}"
        if variant == "music3-int8":
            if music3_device:
                workflow["3"]["inputs"]["device"] = music3_device
            workflow["13"]["inputs"].update(
                caption=request["prompt"],
                lyrics=request.get("lyrics") or "[Instrumental]",
                seed=request["seed"],
                max_duration=request["duration"],
                force_duration=True,
            )
            workflow["9"]["inputs"].update(seed=request["seed"], steps=request["steps"])
            return workflow
        workflow["124"]["inputs"]["steps"] = request["steps"]
        workflow["129"]["inputs"]["noise_seed"] = request["seed"]
        conditioning = workflow["136"]["inputs"]
        conditioning.update(
            prompt=request["prompt"],
            width=32 if execution_mode == "tts" else request["width"],
            height=32 if execution_mode == "tts" else request["height"],
            length=request["num_frames"],
        )
        if execution_mode == "vdn-h3":
            # VDN-H3 supplies its own released adapters and hybrid attention.
            # It must remain separate from Sol-Attn and community turbo LoRAs.
            vdn_steps = int(request["steps"])
            vdn_checkpoint = "stage-dmd-step-250" if vdn_steps == 8 else "stage-b-step-2000"
            workflow["127"]["inputs"]["unet_name"] = (
                "minimax_h3_fl2va_pruned_fp8_scaled.safetensors"
                if variant == "fl2va-fp8"
                else "minimax_h3_ref2va_pruned_fp8_scaled.safetensors"
            )
            workflow["124"]["inputs"].update(
                model=["144", 0],
                scheduler="beta",
                steps=vdn_steps,
                denoise=1.0,
            )
            workflow["126"]["inputs"]["model"] = ["144", 0]
            workflow["123"]["inputs"]["sampler_name"] = "er_sde"
            workflow["144"]["inputs"].update(
                model=["127", 0],
                vdn_checkpoint=vdn_checkpoint,
                apply_turbo_adapter=vdn_steps == 8,
                strength=1.0,
                lora_mode="merge",
                branch_weights="stream",
                attention_backend="grouped",
                verbose=False,
            )
            if variant == "ref2va-fp8":
                self._build_h3_sa_references(workflow, request, input_names)
            else:
                if not input_names:
                    raise ValueError("VDN-H3 FL2VA 需要首帧图片")
                if "137" not in workflow:
                    raise ValueError("VDN-H3 FL2VA 工作流缺少首帧节点 137")
                workflow["137"]["inputs"]["image"] = input_names[0]
                conditioning["first_frame"] = ["137", 0]
            return workflow
        if execution_mode == "h3-sa":
            low_width = max(352, round(request["width"] * 2 / 3 / 32) * 32)
            low_height = max(352, round(request["height"] * 2 / 3 / 32) * 32)
            conditioning.update(
                width=low_width,
                height=low_height,
                length=request["num_frames"],
            )
            workflow["11"]["inputs"].update(
                width=request["width"],
                height=request["height"],
                length=request["num_frames"],
                prompt=request["prompt"],
                video_latent=["10", 0],
                apply_keyframes="disable",
            )
            workflow["127"]["inputs"]["unet_name"] = (
                "minimax_h3_fl2va_pruned_fp8_scaled.safetensors"
                if variant == "fl2va-fp8"
                else "minimax_h3_ref2va_pruned_fp8_scaled.safetensors"
            )
            workflow["142"]["inputs"].update(
                model=["127", 0],
                lora_name=(
                    "minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors"
                    if variant == "fl2va-fp8"
                    else "minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors"
                ),
                strength_model=1.0,
            )
            workflow["143"]["inputs"].update(
                model=["142", 0],
                shift_video=6.0,
                shift_audio=3.0,
            )
            workflow["124"]["inputs"].update(
                model=["143", 0],
                steps=8,
                denoise=1.0,
            )
            workflow["126"]["inputs"]["model"] = ["143", 0]
            workflow["144"]["inputs"].update(
                model=["143", 0],
                tau=float(request.get("sa_tau", 1.3)),
                start_percent=float(request.get("sa_start_percent", 0.2)),
                end_percent=float(request.get("sa_end_percent", 0.9)),
                min_tokens=int(request.get("sa_min_tokens", 4096)),
                int8_qk=bool(request.get("sa_int8_qk", True)),
                sink_conditioning=request.get("sa_sink_conditioning", "exact_kv_and_rows"),
                morton=bool(request.get("sa_morton", False)),
                morton_curve=request.get("sa_morton_curve", "2d_frame"),
                int8_pv=bool(request.get("sa_int8_pv", True)),
                dense_blocks=request.get("sa_dense_blocks", "0"),
            )
            workflow["145"]["inputs"]["model"] = ["144", 0]
            workflow["148"]["inputs"].update(
                model=["144", 0],
                steps=8,
                denoise=float(request.get("sa_stage2_denoise", 0.35)),
            )
            workflow["129"]["inputs"]["noise_seed"] = request["seed"]
            workflow["147"]["inputs"]["noise_seed"] = request["seed"]
            workflow["26"]["inputs"].update(
                model_name="minimax_h3_latent_upscaler_3d_fp16.safetensors",
                mode="target dimensions",
                **{
                    "mode.width": request["width"],
                    "mode.height": request["height"],
                },
                align=32,
                keep_proportion=True,
                device="cuda",
                precision="fp16",
            )
            if variant == "ref2va-fp8":
                self._build_h3_sa_references(workflow, request, input_names)
            elif context_video_name is None:
                if not input_names:
                    raise ValueError("H3 SA FL2VA 需要首帧图片")
                if "137" not in workflow:
                    raise ValueError("H3 SA FL2VA 工作流缺少首帧节点 137")
                workflow["137"]["inputs"]["image"] = input_names[0]
                conditioning["first_frame"] = ["137", 0]
            else:
                conditioning.pop("first_frame", None)

            if context_video_name is not None:
                workflow["9000"] = {
                    "class_type": "VHS_LoadVideo",
                    "inputs": {
                        "video": context_video_name,
                        "force_rate": 24,
                        "custom_width": 0,
                        "custom_height": 0,
                        "frame_load_cap": self.H3_MAX_SEGMENT_FRAMES,
                        "skip_first_frames": 0,
                        "select_every_nth": 1,
                    },
                    "_meta": {"title": "Context Loop previous segment"},
                }
                if not context_latent_path:
                    raise ValueError("H3 Context Loop 缺少上一段 latent checkpoint")
                workflow["9001"] = {
                    "class_type": "MiniMaxH3MotionContextLoadLatent",
                    "inputs": {
                        "latent_path": context_latent_path,
                        "clip_index": int(context_clip_index),
                    },
                    "_meta": {"title": "Context Loop load AV latent"},
                }
                workflow["9002"] = {
                    "class_type": "MiniMaxH3MotionContext",
                    "inputs": {
                        "conditioning": ["136", 0],
                        "vae": ["119", 0],
                        "latent": ["136", 1],
                        "context_frames": ["9000", 0],
                        "context_length": self.H3_CONTEXT_FRAMES,
                        "encode_mode": "video",
                        "anchor_mode": "head",
                        "crop": "disabled",
                        "audio_context_length": self.H3_CONTEXT_FRAMES,
                        "audio_mode": "timeline",
                        "context_latent": ["9001", 0],
                        "target_start": 0,
                    },
                    "_meta": {"title": "Context Loop seamless stitching"},
                }
                workflow["126"]["inputs"]["conditioning"] = ["9002", 0]
                # Motion Context returns CONDITIONING and trim_frames. The
                # sampler keeps the original H3 latent as its latent_image;
                # the loaded previous latent is consumed through the
                # conditioning node's context_latent input.
                workflow["125"]["inputs"]["latent_image"] = ["136", 1]

            if save_latent_prefix is not None:
                workflow["9005"] = {
                    "class_type": "MiniMaxH3MotionContextSaveLatent",
                    "inputs": {
                        "latent": ["125", 0],
                        "filename_prefix": save_latent_prefix,
                        "clip_index": int(save_latent_clip_index),
                    },
                    "_meta": {"title": "Context Loop save AV latent"},
                }

            if context_video_name is not None:
                workflow["9003"] = {
                    "class_type": "MiniMaxH3MotionContextTrim",
                    "inputs": {
                        "images": ["151", 0],
                        "audio": ["141", 0],
                        "trim_frames": self.H3_CONTEXT_FRAMES,
                        "fps": 24.0,
                        # H3's audio latent grid can differ from the exact
                        # 24-fps picture duration by one audio cell. The trim
                        # node's conformance path handles this deterministically.
                        "match_tail": True,
                        "video_crossfade_frames": self.H3_CONTEXT_FRAMES,
                    },
                    "_meta": {"title": "Context Loop trim overlap"},
                }
                workflow["9004"] = {
                    "class_type": "CreateVideo",
                    "inputs": {
                        "images": ["9003", 0],
                        "audio": ["9003", 1],
                        "fps": 24.0,
                        "bit_depth": 8,
                    },
                    "_meta": {"title": "Context Loop delivered segment"},
                }
                workflow["92"]["inputs"]["video"] = ["9004", 0]
            return workflow
        if execution_mode == "dual-sampling":
            # The public workflow uses a low-resolution pass, a learned latent
            # upscale, then a second low-noise refinement pass. The API form
            # keeps the same graph and exposes the request dimensions through
            # the resolution and upscale controls.
            low_width = max(352, round(request["width"] * 0.5 / 32) * 32)
            low_height = max(352, round(request["height"] * 0.5 / 32) * 32)
            workflow["136"]["inputs"].update(
                width=low_width,
                height=low_height,
                length=request["num_frames"],
            )
            workflow["11"]["inputs"].update(
                width=request["width"],
                height=request["height"],
                length=request["num_frames"],
                prompt=request["prompt"],
                video_latent=["10", 0],
                apply_keyframes="disable",
            )
            workflow["127"]["inputs"]["unet_name"] = "minimax_h3_ref2va_pruned_fp8_scaled.safetensors"
            workflow["143"]["inputs"].update(shift_video=12.0, shift_audio=3.0)
            workflow["124"]["inputs"]["steps"] = request["steps"]
            workflow["140"]["inputs"].update(extra_steps=1, start_at_sigma=0.7, end_at_sigma=0.0)
            workflow["142"]["inputs"].update(extra_steps=1, start_at_sigma=0.7, end_at_sigma=0.0)
            workflow["129"]["inputs"]["noise_seed"] = request["seed"]
            workflow["147"]["inputs"]["noise_seed"] = request["seed"]
            workflow["26"]["inputs"].update(
                model_name="minimax_h3_latent_upscaler_3d_fp16.safetensors",
                mode="target dimensions",
                **{
                    "mode.width": request["width"],
                    "mode.height": request["height"],
                },
                align=32,
                keep_proportion=True,
                device="cuda",
                precision="fp16",
            )
            workflow["144"]["inputs"].update(
                tau=1.3,
                start_percent=0.2,
                end_percent=0.9,
                min_tokens=4096,
                int8_qk=True,
                sink_conditioning="exact_kv_and_rows",
                morton=False,
                morton_curve="2d_frame",
                int8_pv=True,
                verbose=False,
                use_tma=False,
                tau_profile="",
                dense_blocks="",
            )
            return self._build_dual_sampling_references(workflow, request, input_names)
        if execution_mode == "digital-human":
            inputs_by_type = {
                item["type"]: input_name
                for item, input_name in zip(request["references"], input_names, strict=True)
            }
            workflow["137"]["inputs"]["image"] = inputs_by_type["image"]
            workflow["171"]["inputs"]["audio"] = inputs_by_type["audio"]
            conditioning["prompt"] = (
                "<Picture 1> is the sole character reference. "
                "The character speaks and lip-syncs exactly to <Audio 1>. "
                "Preserve the identity, facial structure, clothing, and source audio exactly.\n\n"
                f"{request['prompt']}"
            )
            conditioning["ref_images.ref_image_0"] = ["137", 0]
            conditioning["ref_audios.ref_audio_0"] = ["171", 0]
            return workflow
        if variant == "ref2va-fp8":
            conditioning["ref_image_size"] = request.get("ref_image_size", "match")
            for key in list(conditioning):
                if key.startswith(("ref_images.", "ref_videos.", "ref_video_audios.", "ref_audios.")):
                    conditioning.pop(key)
            counts = {"image": 0, "video": 0, "audio": 0}
            for offset, (item, input_name) in enumerate(
                zip(request["references"], input_names, strict=True), start=200
            ):
                kind = item["type"]
                index = counts[kind]
                counts[kind] += 1
                node_id = str(offset)
                if kind == "image":
                    workflow[node_id] = {
                        "class_type": "LoadImage",
                        "inputs": {"image": input_name},
                        "_meta": {"title": f"Load Picture {index + 1}"},
                    }
                    conditioning[f"ref_images.ref_image_{index}"] = [node_id, 0]
                elif kind == "video":
                    workflow[node_id] = {
                        "class_type": "VHS_LoadVideo",
                        "inputs": {
                            "video": input_name,
                            "force_rate": 24,
                            "custom_width": 0,
                            "custom_height": 0,
                            "frame_load_cap": 360,
                            "skip_first_frames": 0,
                            "select_every_nth": 1,
                        },
                        "_meta": {"title": f"Load Video {index + 1} at 24 fps"},
                    }
                    conditioning[f"ref_videos.ref_video_{index}"] = [node_id, 0]
                    if item.get("has_audio"):
                        conditioning[f"ref_video_audios.ref_video_audio_{index}"] = [
                            node_id,
                            2,
                        ]
                else:
                    workflow[node_id] = {
                        "class_type": "LoadAudio",
                        "inputs": {"audio": input_name},
                        "_meta": {"title": f"Load Audio {index + 1}"},
                    }
                    conditioning[f"ref_audios.ref_audio_{index}"] = [node_id, 0]
            return workflow

        conditioning["first_frame"] = ["137", 0]
        workflow["137"]["inputs"]["image"] = input_names[0]
        if len(input_names) == 2:
            if "139" not in workflow:
                raise ValueError("ComfyUI 工作流缺少尾帧节点 139")
            workflow["139"]["inputs"]["image"] = input_names[1]
            workflow["136"]["inputs"]["last_frame"] = ["139", 0]
        else:
            workflow["136"]["inputs"].pop("last_frame", None)
        return workflow

    @staticmethod
    def _build_dual_sampling_references(
        workflow: dict[str, Any], request: dict[str, Any], input_names: list[str]
    ) -> dict[str, Any]:
        conditioning = workflow["136"]["inputs"]
        for key in list(conditioning):
            if key.startswith(("ref_images.", "ref_videos.", "ref_video_audios.", "ref_audios.")):
                conditioning.pop(key)
        for index, input_name in enumerate(input_names):
            node_id = str(200 + index)
            workflow[node_id] = {
                "class_type": "LoadImage",
                "inputs": {"image": input_name},
                "_meta": {"title": f"Load Dual Sampling Picture {index + 1}"},
            }
            conditioning[f"ref_images.ref_image_{index}"] = [node_id, 0]
        return workflow

    @staticmethod
    def _build_h3_sa_references(
        workflow: dict[str, Any], request: dict[str, Any], input_names: list[str]
    ) -> dict[str, Any]:
        conditioning = workflow["136"]["inputs"]
        for key in list(conditioning):
            if key.startswith(("ref_images.", "ref_videos.", "ref_video_audios.", "ref_audios.")):
                conditioning.pop(key)
        counts = {"image": 0, "video": 0, "audio": 0}
        for offset, (item, input_name) in enumerate(
            zip(request["references"], input_names, strict=True), start=200
        ):
            kind = item["type"]
            index = counts[kind]
            counts[kind] += 1
            node_id = str(offset)
            if kind == "image":
                workflow[node_id] = {
                    "class_type": "LoadImage",
                    "inputs": {"image": input_name},
                    "_meta": {"title": f"Load H3 SA Picture {index + 1}"},
                }
                conditioning[f"ref_images.ref_image_{index}"] = [node_id, 0]
            elif kind == "video":
                workflow[node_id] = {
                    "class_type": "VHS_LoadVideo",
                    "inputs": {
                        "video": input_name,
                        "force_rate": 24,
                        "custom_width": 0,
                        "custom_height": 0,
                        "frame_load_cap": 360,
                        "skip_first_frames": 0,
                        "select_every_nth": 1,
                    },
                    "_meta": {"title": f"Load H3 SA Video {index + 1}"},
                }
                conditioning[f"ref_videos.ref_video_{index}"] = [node_id, 0]
                if item.get("has_audio"):
                    conditioning[f"ref_video_audios.ref_video_audio_{index}"] = [node_id, 2]
            elif kind == "audio":
                workflow[node_id] = {
                    "class_type": "LoadAudio",
                    "inputs": {"audio": input_name},
                    "_meta": {"title": f"Load H3 SA Audio {index + 1}"},
                }
                conditioning[f"ref_audios.ref_audio_{index}"] = [node_id, 0]
        return workflow

    @classmethod
    def _split_h3_frames(cls, total_frames: int) -> list[int]:
        """Choose legal H3 segment lengths whose delivered frames match the request."""
        target = max(5, int(total_frames))
        overlap = cls.H3_CONTEXT_FRAMES
        parts: list[int] = []
        delivered = 0
        while delivered < target:
            remaining = target - delivered
            if not parts:
                raw_frames = min(cls.H3_MAX_SEGMENT_FRAMES, remaining)
            else:
                raw_frames = min(cls.H3_MAX_SEGMENT_FRAMES, remaining + overlap)
            raw_frames = max(5, raw_frames)
            while raw_frames % 17 != 5:
                raw_frames += 1
            if raw_frames > cls.H3_MAX_SEGMENT_FRAMES:
                raw_frames = cls.H3_MAX_SEGMENT_FRAMES
            parts.append(raw_frames)
            delivered += raw_frames if not parts[:-1] else raw_frames - overlap
        return parts

    def _upload_context_video(self, client, path: Path, subfolder: str, filename: str) -> str:
        content_type = mimetypes.guess_type(path.name)[0] or "video/mp4"
        with path.open("rb") as handle:
            response = client.post(
                "/upload/image",
                data={"type": "input", "subfolder": subfolder, "overwrite": "true"},
                files={"image": (filename, handle, content_type)},
            )
        response.raise_for_status()
        result = response.json()
        stored_name = str(result.get("name") or filename)
        stored_folder = str(result.get("subfolder") or subfolder).strip("/")
        return f"{stored_folder}/{stored_name}" if stored_folder else stored_name

    @staticmethod
    def _merge_h3_segments(segment_paths: list[Path], output: Path) -> None:
        if not segment_paths:
            raise ValueError("H3 Context Loop 没有可合并的片段")
        if len(segment_paths) == 1:
            shutil.copy2(segment_paths[0], output)
            return
        concat_list = output.with_suffix(".concat.txt")
        concat_list.write_text(
            "".join(f"file '{path.resolve().as_posix().replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n" for path in segment_paths),
            encoding="utf-8",
        )
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", str(concat_list),
                    "-vsync", "0",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-movflags", "+faststart", str(output),
                ],
                check=True,
            )
        finally:
            concat_list.unlink(missing_ok=True)

    def _generate_once(
        self,
        job,
        progress,
        cancelled,
        checkpoint=None,
        checkpoint_callback=None,
        *,
        context_video_name: str | None = None,
        context_latent_path: str | None = None,
        context_clip_index: int = 0,
        save_latent_prefix: str | None = None,
        save_latent_clip_index: int = 0,
    ):
        """Run one ComfyUI request, optionally carrying Context Loop state."""
        import httpx
        from websockets.sync.client import connect

        prompt_id = _remote_checkpoint_id(
            checkpoint, "comfyui", str(self.node.id)
        )
        client_id = str((checkpoint or {}).get("client_id") or "")
        client_id = client_id or f"minimax-studio-webui-{uuid.uuid4().hex}"
        websocket_url = self.comfy_url.replace("http://", "ws://", 1).replace(
            "https://", "wss://", 1
        )
        try:
            music3 = self._variant(job) == "music3-int8"
            tts = self._execution_mode(job) == "tts"
            sa = self._execution_mode(job) == "h3-sa"
            vdn = self._execution_mode(job) == "vdn-h3"
            progress(2, "准备 ComfyUI Music3 工作流" if music3 else "准备 ComfyUI H3 TTS 工作流" if tts else "准备 ComfyUI H3 SA 工作流" if sa else "准备 ComfyUI VDN-H3 工作流" if vdn else "准备 ComfyUI FP8 工作流")
            timeout = httpx.Timeout(30, connect=10)
            with httpx.Client(
                base_url=self.comfy_url,
                headers=self.api_headers,
                timeout=timeout,
                trust_env=False,
            ) as client:
                if prompt_id:
                    progress(5, f"正在重新连接 ComfyUI 任务 {prompt_id[:8]}")
                    history = self._poll_until_finished(
                        client,
                        prompt_id,
                        progress,
                        cancelled,
                        tts,
                        recovering=True,
                    )
                    progress(98, "回传 ComfyUI 生成产物")
                    output = self._copy_result(job, history, client)
                    progress(99, "整理交付文件")
                    return output
                stats_response = client.get("/system_stats")
                stats_response.raise_for_status()
                input_names = [] if music3 else self._upload_inputs(client, job)
                music3_device = self._comfy_cuda_device(stats_response.json()) if music3 else None
                workflow = self._build_workflow(
                    job, input_names, music3_device,
                    context_video_name=context_video_name,
                    context_latent_path=context_latent_path,
                    context_clip_index=context_clip_index,
                    save_latent_prefix=save_latent_prefix,
                    save_latent_clip_index=save_latent_clip_index,
                )
                with connect(
                    f"{websocket_url}/ws?clientId={client_id}",
                    additional_headers=self.api_headers or None,
                    open_timeout=10,
                    max_size=None,
                ) as socket:
                    response = client.post("/prompt", json={"prompt": workflow, "client_id": client_id})
                    response.raise_for_status()
                    result = response.json()
                    prompt_id = result.get("prompt_id")
                    if not prompt_id:
                        raise RuntimeError(f"ComfyUI 未返回 prompt_id：{result}")
                    _write_remote_checkpoint(
                        checkpoint_callback,
                        provider="comfyui",
                        node_id=str(self.node.id),
                        remote_id=str(prompt_id),
                        client_id=client_id,
                    )
                    progress(4, f"已提交 ComfyUI 任务 {prompt_id[:8]}")
                    history = self._wait_for_finished(socket, client, prompt_id, progress, cancelled, tts)
                if cancelled():
                    self._cancel_prompt(client, prompt_id)
                    raise InterruptedError("generation cancelled")
                progress(98, "回传 ComfyUI 生成产物")
                output = self._copy_result(job, history, client)
            progress(99, "整理交付文件")
            return output
        finally:
            self._release_vram()

    @staticmethod
    def _prompt_ids(items: list[Any]) -> set[str]:
        ids = set()
        for item in items:
            if isinstance(item, list) and len(item) > 1 and isinstance(item[1], str):
                ids.add(item[1])
        return ids

    def _cancel_prompt(self, client, prompt_id: str) -> None:
        try:
            queue_data = client.get("/queue").json()
            running = self._prompt_ids(queue_data.get("queue_running", []))
            pending = self._prompt_ids(queue_data.get("queue_pending", []))
            if prompt_id in pending:
                client.post("/queue", json={"delete": [prompt_id]}).raise_for_status()
            elif prompt_id in running:
                client.post("/interrupt").raise_for_status()
        except Exception:
            pass

    def _release_vram(self) -> None:
        import httpx

        try:
            with httpx.Client(
                base_url=self.comfy_url,
                headers=self.api_headers,
                timeout=httpx.Timeout(10, connect=5),
                trust_env=False,
            ) as client:
                response = client.post(
                    "/free",
                    json={"unload_models": True, "free_memory": True},
                )
                response.raise_for_status()
        except Exception:
            logger.exception("ComfyUI VRAM 释放失败")

    def _history(self, client, prompt_id: str) -> dict[str, Any] | None:
        response = client.get(f"/history/{prompt_id}")
        response.raise_for_status()
        return response.json().get(prompt_id)

    def _poll_until_finished(
        self,
        client,
        prompt_id,
        progress,
        cancelled,
        audio_only=False,
        recovering=False,
    ):
        import httpx

        unavailable_since: float | None = None
        missing_since: float | None = None
        missing_grace_seconds = max(5.0, self.settings.comfy_poll_seconds * 3)
        while True:
            if cancelled():
                self._cancel_prompt(client, prompt_id)
                raise InterruptedError("generation cancelled")
            try:
                history = self._history(client, prompt_id)
                if history:
                    return history
                queue_response = client.get("/queue")
                queue_response.raise_for_status()
                queue_data = queue_response.json()
                unavailable_since = None
            except (httpx.HTTPError, ValueError) as exc:
                unavailable_since = unavailable_since or time.monotonic()
                missing_since = None
                if (
                    time.monotonic() - unavailable_since
                    >= max(1.0, self.settings.remote_reconnect_seconds)
                ):
                    raise RemoteTaskUnavailableError(
                        f"ComfyUI 任务 {prompt_id} 暂时无法查询"
                    ) from exc
                progress(5, "ComfyUI 连接中断，正在重新连接原任务")
                time.sleep(max(0.2, self.settings.comfy_poll_seconds))
                continue
            running = self._prompt_ids(queue_data.get("queue_running", []))
            pending = self._prompt_ids(queue_data.get("queue_pending", []))
            if prompt_id not in running and prompt_id not in pending:
                try:
                    history = self._history(client, prompt_id)
                except (httpx.HTTPError, ValueError) as exc:
                    unavailable_since = unavailable_since or time.monotonic()
                    missing_since = None
                    if (
                        time.monotonic() - unavailable_since
                        >= max(1.0, self.settings.remote_reconnect_seconds)
                    ):
                        raise RemoteTaskUnavailableError(
                            f"ComfyUI 任务 {prompt_id} 暂时无法查询"
                        ) from exc
                    progress(5, "ComfyUI 连接中断，正在重新连接原任务")
                    time.sleep(max(0.2, self.settings.comfy_poll_seconds))
                    continue
                if history:
                    return history
                missing_since = missing_since or time.monotonic()
                if time.monotonic() - missing_since >= missing_grace_seconds:
                    raise RemoteTaskNotFoundError(
                        f"ComfyUI 远端任务已失效，prompt_id={prompt_id}"
                    )
                progress(5, "ComfyUI 任务状态暂不可见，等待恢复")
                time.sleep(max(0.2, self.settings.comfy_poll_seconds))
                continue
            missing_since = None
            stage = (
                "ComfyUI H3 TTS 工作流执行中"
                if audio_only and prompt_id in running
                else "ComfyUI FP8 工作流执行中"
                if prompt_id in running
                else "等待 ComfyUI 执行"
            )
            progress(5, stage)
            time.sleep(self.settings.comfy_poll_seconds)

    def _wait_for_finished(
        self,
        socket,
        client,
        prompt_id,
        progress,
        cancelled,
        audio_only=False,
        recovering=False,
    ):
        while True:
            if cancelled():
                self._cancel_prompt(client, prompt_id)
                raise InterruptedError("generation cancelled")
            try:
                raw = socket.recv(timeout=self.settings.comfy_poll_seconds)
            except TimeoutError:
                try:
                    history = self._history(client, prompt_id)
                except Exception:
                    return self._poll_until_finished(
                        client,
                        prompt_id,
                        progress,
                        cancelled,
                        audio_only,
                        recovering=True,
                    )
                if history:
                    return history
                try:
                    queue_response = client.get("/queue")
                    queue_response.raise_for_status()
                    queue_data = queue_response.json()
                except Exception:
                    return self._poll_until_finished(
                        client,
                        prompt_id,
                        progress,
                        cancelled,
                        audio_only,
                        recovering=True,
                    )
                active = self._prompt_ids(queue_data.get("queue_running", []))
                active.update(self._prompt_ids(queue_data.get("queue_pending", [])))
                if prompt_id not in active:
                    return self._poll_until_finished(
                        client,
                        prompt_id,
                        progress,
                        cancelled,
                        audio_only,
                        recovering=True,
                    )
                continue
            except Exception:
                return self._poll_until_finished(
                    client,
                    prompt_id,
                    progress,
                    cancelled,
                    audio_only,
                    recovering=True,
                )
            if isinstance(raw, bytes):
                continue
            try:
                message = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            event_type = message.get("type")
            data = message.get("data") or {}
            if data.get("prompt_id") != prompt_id:
                continue
            if event_type == "execution_start":
                progress(5, "ComfyUI H3 TTS 工作流开始执行" if audio_only else "ComfyUI FP8 工作流开始执行")
            elif event_type == "executing":
                node = str(data.get("node"))
                if node in self.NODE_STAGES:
                    percent, stage = self.NODE_STAGES[node]
                    if audio_only and node == "92":
                        stage = "保存音频产物"
                    progress(percent, stage)
                elif node.isdigit() and int(node) >= 200:
                    progress(10, "加载 Ref2VA 参考素材")
                elif data.get("node") is None:
                    history = self._history(client, prompt_id)
                    if history:
                        return history
            elif event_type == "progress" and str(data.get("node")) == "125":
                value = int(data.get("value") or 0)
                total = max(1, int(data.get("max") or 1))
                percent = 15 + round(min(value, total) / total * 73)
                progress(percent, f"TTS 音频采样 {value}/{total}" if audio_only else f"联合音视频采样 {value}/{total}")
            elif event_type == "progress" and str(data.get("node")) == "9":
                value = int(data.get("value") or 0)
                total = max(1, int(data.get("max") or 1))
                percent = 15 + round(min(value, total) / total * 73)
                progress(percent, f"Music3 音频采样 {value}/{total}")
            elif event_type == "execution_success":
                for _ in range(10):
                    history = self._history(client, prompt_id)
                    if history:
                        return history
                    time.sleep(0.2)
            elif event_type == "execution_error":
                raise RuntimeError(data.get("exception_message") or "ComfyUI 工作流执行失败")
            elif event_type == "execution_interrupted":
                if cancelled():
                    raise InterruptedError("generation cancelled")
                raise RuntimeError("ComfyUI 工作流被中断")

    def _copy_result(self, job, history: dict[str, Any], client=None) -> Path:
        status = history.get("status") or {}
        if status.get("completed") is not True or status.get("status_str") != "success":
            messages = status.get("messages") or []
            raise RuntimeError(f"ComfyUI 未成功完成工作流：{messages[-1:]}")
        output_items = (history.get("outputs") or {}).get("92") or {}
        candidates = []
        for items in output_items.values():
            if isinstance(items, list):
                candidates.extend(item for item in items if isinstance(item, dict))
        audio_only = self._variant(job) == "music3-int8" or self._execution_mode(job) == "tts"
        expected_suffix = ".flac" if audio_only else ".mp4"
        result_item = next(
            (
                item
                for item in candidates
                if str(item.get("filename", "")).lower().endswith(expected_suffix)
            ),
            None,
        )
        if not result_item:
            media_name = "FLAC" if audio_only else "MP4"
            raise RuntimeError(f"ComfyUI 历史记录中没有找到节点 92 的 {media_name} 产物")
        output = self.settings.outputs_dir / output_file_name(job, expected_suffix)
        if client is None:
            output_root = self.settings.comfy_output_dir.resolve()
            source = (
                output_root
                / str(result_item.get("subfolder") or "")
                / result_item["filename"]
            ).resolve()
            try:
                source.relative_to(output_root)
            except ValueError as exc:
                raise RuntimeError("ComfyUI 返回了非法产物路径") from exc
            if not source.is_file():
                raise FileNotFoundError(f"ComfyUI 产物不存在：{source}")
            shutil.copy2(source, output)
            source.unlink(missing_ok=True)
        else:
            params = {
                "filename": result_item["filename"],
                "subfolder": str(result_item.get("subfolder") or ""),
                "type": str(result_item.get("type") or "output"),
            }
            with client.stream("GET", "/view", params=params) as response:
                response.raise_for_status()
                with output.open("wb") as target:
                    for chunk in response.iter_bytes():
                        target.write(chunk)
        output.with_suffix(".json").write_text(
            json.dumps(job["request"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output

    def _generate_h3_sa_long(self, job, progress, cancelled, checkpoint=None, checkpoint_callback=None):
        total_frames = int(job["request"]["num_frames"])
        segment_frames = self._split_h3_frames(total_frames)
        segment_outputs: list[Path] = []
        context_video_name = None
        context_latent_path = None
        context_subfolder = f"minimax-studio-webui/{job['id']}/context"
        latent_prefix = f"{context_subfolder}/h3_context"

        for segment_index, raw_frames in enumerate(segment_frames, start=1):
            if cancelled():
                raise InterruptedError("generation cancelled")
            segment_request = dict(job["request"])
            segment_request["duration"] = raw_frames / 24.0
            segment_request["num_frames"] = raw_frames
            segment_request["context_loop"] = True
            segment_job = dict(job)
            segment_job["id"] = f"{job['id']}-segment-{segment_index}"
            segment_job["output_stem"] = f"{job.get('output_stem') or job['id']}-segment-{segment_index:03d}"
            segment_job["request"] = segment_request
            def segment_progress(value, message, index=segment_index):
                overall = ((index - 1) + max(0, min(100, int(value))) / 100.0) / len(segment_frames)
                progress(min(98, max(2, round(overall * 96) + 2)), f"片段 {index}/{len(segment_frames)} · {message}")

            output = self._generate_once(
                segment_job,
                segment_progress,
                cancelled,
                checkpoint if segment_index == 1 else None,
                checkpoint_callback if segment_index == 1 else None,
                context_video_name=context_video_name,
                context_latent_path=context_latent_path,
                context_clip_index=segment_index - 1,
                save_latent_prefix=latent_prefix,
                save_latent_clip_index=segment_index,
            )
            segment_outputs.append(output)
            if segment_index < len(segment_frames):
                import httpx
                with httpx.Client(
                    base_url=self.comfy_url,
                    headers=self.api_headers,
                    timeout=httpx.Timeout(60, connect=10),
                    trust_env=False,
                ) as client:
                    context_video_name = self._upload_context_video(
                        client,
                        output,
                        context_subfolder,
                        f"segment_{segment_index:03d}.mp4",
                    )
                context_latent_path = context_subfolder

        progress(98, "合并 Context Loop 片段")
        output = self.settings.outputs_dir / output_file_name(job, ".mp4")
        self._merge_h3_segments(segment_outputs, output)
        output.with_suffix(".json").write_text(
            json.dumps(job["request"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        progress(100, f"Context Loop 完成，共 {len(segment_outputs)} 个片段")
        return output

    def generate(self, job, progress, cancelled, checkpoint=None, checkpoint_callback=None):
        request = job.get("request", {})
        if self._execution_mode(job) == "h3-sa" and float(request.get("duration", 0)) > 15:
            return self._generate_h3_sa_long(job, progress, cancelled, checkpoint, checkpoint_callback)
        return self._generate_once(job, progress, cancelled, checkpoint, checkpoint_callback)


class RunningHubH3Engine:
    MAX_UPLOAD_BYTES = 30 * 1024 * 1024
    MAX_POLL_SECONDS = 2 * 60 * 60

    def __init__(self, settings: Settings, node: ComfyNodeConfig):
        self.settings = settings
        self.node = node
        self.base_url = node.url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {node.api_key}"}
        self.last_billing: dict[str, Any] | None = None
        self.last_output_media_type = "file"

    @property
    def is_ai_app(self) -> bool:
        return self.node.runninghub_resource_type == "ai-app"

    @staticmethod
    def _json_response(response, action: str) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise RunningHubTransientResponseError(
                f"RunningHub {action}返回了无效 JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise RunningHubTransientResponseError(
                f"RunningHub {action}返回格式无效"
            )
        code = payload.get("code")
        if code not in {None, 0, "0", 200, "200"}:
            message = str(payload.get("msg") or payload.get("message") or code)
            raise RuntimeError(f"RunningHub {action}失败：{message[:500]}")
        return payload

    def _request_json(
        self,
        client,
        method: str,
        path: str,
        *,
        json_data: dict[str, Any],
        action: str,
    ) -> dict[str, Any]:
        import httpx

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = client.request(method, path, json=json_data)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                if response.is_error:
                    try:
                        detail = response.json()
                    except ValueError:
                        detail = None
                    message = (
                        detail.get("msg") or detail.get("message")
                        if isinstance(detail, dict)
                        else None
                    )
                    raise RuntimeError(
                        f"RunningHub {action}失败：{message or response.status_code}"
                    )
                return self._json_response(response, action)
            except (httpx.HTTPError, RunningHubTransientResponseError) as exc:
                last_error = exc
                if attempt == 2:
                    break
                time.sleep(2**attempt)
        raise RunningHubTransientResponseError(
            f"RunningHub {action}请求失败：{last_error}"
        ) from last_error

    def _upload_inputs(self, client, job: dict[str, Any]) -> list[str]:
        import httpx

        paths = [Path(path) for path in job.get("input_paths", [])]
        manifest = job.get("request", {}).get("references", [])
        if len(paths) != len(manifest):
            raise ValueError("参考素材清单与文件不一致")
        uploaded = []
        for source in paths:
            if source.stat().st_size > self.MAX_UPLOAD_BYTES:
                raise ValueError(f"RunningHub 单个上传文件不能超过 30 MB：{source.name}")
            content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            last_error: Exception | None = None
            for attempt in range(3):
                try:
                    with source.open("rb") as handle:
                        response = client.post(
                            "/openapi/v2/media/upload/binary",
                            files={"file": (source.name, handle, content_type)},
                        )
                    if response.status_code == 429 or response.status_code >= 500:
                        response.raise_for_status()
                    if response.is_error:
                        try:
                            detail = response.json()
                        except ValueError:
                            detail = None
                        message = (
                            detail.get("msg")
                            or detail.get("message")
                            or detail.get("errorMessage")
                            if isinstance(detail, dict)
                            else None
                        )
                        raise RuntimeError(
                            f"RunningHub 文件上传失败：{source.name}："
                            f"{message or response.status_code}"
                        )
                    response.raise_for_status()
                    payload = self._json_response(response, "文件上传")
                    data = payload.get("data")
                    if not isinstance(data, dict):
                        data = payload
                    file_name = str(
                        data.get("filename")
                        or data.get("fileName")
                        or data.get("download_url")
                        or ""
                    )
                    if not file_name:
                        raise RuntimeError("RunningHub 文件上传响应缺少 fileName")
                    uploaded.append(file_name)
                    break
                except (httpx.HTTPError, RunningHubTransientResponseError) as exc:
                    last_error = exc
                    if attempt == 2:
                        raise RuntimeError(
                            f"RunningHub 文件上传失败：{source.name}：{last_error}"
                        ) from last_error
                    time.sleep(2**attempt)
        return uploaded

    def _account_status(self, client) -> dict[str, Any]:
        payload = self._request_json(
            client,
            "POST",
            "/uc/openapi/accountStatus",
            json_data={"apikey": self.node.api_key},
            action="读取账户余额",
        )
        return runninghub_account_profile(payload)

    def _node_info_list(
        self,
        job: dict[str, Any],
        input_names: list[str],
    ) -> list[dict[str, Any]]:
        request = job.get("request", {})
        schema = request.get("runninghub_schema") or self.node.runninghub_schema
        if not isinstance(schema, dict):
            raise RuntimeError("RunningHub 工作流参数定义不可用")
        return build_runninghub_node_info_list(
            schema,
            request.get("runninghub_parameters") or {},
            request.get("references") or [],
            input_names,
        )

    def _cancel_task(self, client, task_id: str) -> None:
        if self.is_ai_app:
            logger.warning(
                "RunningHub AI App API 未配置取消端点，task_id=%s", task_id
            )
            return
        try:
            self._request_json(
                client,
                "POST",
                "/task/openapi/cancel",
                json_data={"apiKey": self.node.api_key, "taskId": task_id},
                action="取消任务",
            )
        except Exception:
            logger.exception("RunningHub 任务取消失败，task_id=%s", task_id)

    def _poll(self, client, task_id: str, progress, cancelled) -> dict[str, Any]:
        deadline = time.monotonic() + self.MAX_POLL_SECONDS
        last_status = ""
        unavailable_since: float | None = None
        while time.monotonic() < deadline:
            if cancelled():
                self._cancel_task(client, task_id)
                raise InterruptedError("generation cancelled")
            try:
                payload = self._request_json(
                    client,
                    "POST",
                    "/openapi/v2/query",
                    json_data={"taskId": task_id},
                    action="查询任务",
                )
                unavailable_since = None
            except RunningHubTransientResponseError as exc:
                unavailable_since = unavailable_since or time.monotonic()
                if (
                    time.monotonic() - unavailable_since
                    >= max(1.0, self.settings.remote_reconnect_seconds)
                ):
                    raise RemoteTaskUnavailableError(
                        f"RunningHub 任务 {task_id} 暂时无法查询"
                    ) from exc
                progress(5, "RunningHub 连接中断，正在重新连接原任务")
                time.sleep(max(0.2, self.settings.comfy_poll_seconds))
                continue
            except RuntimeError as exc:
                message = str(exc).casefold()
                missing_markers = (
                    "task_not_found",
                    "task not found",
                    "task_not_exist",
                    "task does not exist",
                    "任务不存在",
                )
                if any(marker in message for marker in missing_markers):
                    raise RemoteTaskNotFoundError(
                        f"RunningHub 远端任务已失效，taskId={task_id}"
                    ) from exc
                raise
            data = payload.get("data")
            if not isinstance(data, dict):
                data = payload
            status = str(data.get("status") or "").upper()
            if status != last_status:
                if status in {"CREATE", "CREATED", "PENDING", "QUEUED"}:
                    progress(5, "等待 RunningHub 调度")
                elif status == "RUNNING":
                    progress(15, "RunningHub 工作流执行中")
                last_status = status
            if status in {"SUCCESS", "COMPLETED"}:
                results = data.get("results") or []
                if not isinstance(results, list) or not results:
                    raise RuntimeError("RunningHub 任务成功但未返回生成结果")
                data["results"] = [item for item in results if isinstance(item, dict)]
                return data
            if status in {
                "ERROR",
                "FAILURE",
                "FAILED",
                "CANCEL",
                "CANCELED",
                "CANCELLED",
            }:
                message = data.get("errorMessage") or data.get("promptTips") or status
                raise RuntimeError(f"RunningHub 任务{status}：{str(message)[:500]}")
            time.sleep(max(2.0, self.settings.comfy_poll_seconds))
        raise RemoteTaskUnavailableError(
            f"RunningHub 任务仍未完成，将继续查询原任务，taskId={task_id}"
        )

    def _download_result(self, job: dict[str, Any], results: list[dict[str, Any]]) -> Path:
        import httpx

        media_type = str(job.get("request", {}).get("media_type") or "file")
        expected_extensions = {
            "video": {"mp4", "webm", "mov", "mkv"},
            "audio": {"flac", "wav", "mp3", "m4a", "ogg", "aac"},
            "image": {"png", "jpg", "jpeg", "webp", "gif"},
        }.get(media_type, set())
        candidates = []
        for item in results:
            url = str(
                item.get("url")
                or item.get("outputUrl")
                or item.get("fileUrl")
                or ""
            )
            if url:
                candidates.append((url, str(item.get("outputType") or item.get("fileType") or "")))
        selected = next(
            (
                url
                for url, output_type in candidates
                if urlsplit(url).path.lower().rsplit(".", 1)[-1]
                in expected_extensions
                or output_type.lower().lstrip(".") in expected_extensions
            ),
            candidates[0][0] if candidates else "",
        )
        if not selected:
            raise RuntimeError("RunningHub 生成结果中没有可下载文件")
        selected_item = next((item for item in candidates if item[0] == selected), None)
        suffix = Path(urlsplit(selected).path).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
            output_type = (selected_item or ("", ""))[1].lower().lstrip(".")
            suffix = f".{output_type}" if re.fullmatch(r"[a-z0-9]{1,8}", output_type) else ".bin"
        extension = suffix.lower().lstrip(".")
        if extension in {"mp4", "webm", "mov", "mkv"}:
            self.last_output_media_type = "video"
        elif extension in {"flac", "wav", "mp3", "m4a", "ogg", "aac", "opus"}:
            self.last_output_media_type = "audio"
        elif extension in {"png", "jpg", "jpeg", "webp", "gif", "bmp"}:
            self.last_output_media_type = "image"
        else:
            self.last_output_media_type = "file"
        output = self.settings.outputs_dir / output_file_name(job, suffix)
        with httpx.stream("GET", selected, timeout=600, follow_redirects=True, trust_env=False) as response:
            response.raise_for_status()
            with output.open("wb") as target:
                for chunk in response.iter_bytes():
                    target.write(chunk)
        if not output.stat().st_size:
            output.unlink(missing_ok=True)
            raise RuntimeError("RunningHub 返回了空的生成文件")
        output.with_suffix(".json").write_text(
            json.dumps(job["request"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output

    def generate(
        self,
        job,
        progress,
        cancelled,
        checkpoint=None,
        checkpoint_callback=None,
    ):
        import httpx

        progress(2, "准备 RunningHub AI 应用" if self.is_ai_app else "准备 RunningHub 工作流")
        self.last_billing = None
        self.last_output_media_type = output_media_type(
            job.get("request", {}).get("runninghub_schema") or {}
        )
        restored_task_id = _remote_checkpoint_id(
            checkpoint, "runninghub", str(self.node.id)
        )
        timeout = httpx.Timeout(60, connect=10)
        with httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout,
            follow_redirects=True,
            trust_env=False,
        ) as client:
            balance_before: dict[str, Any] | None = None
            task_id = restored_task_id
            usage: dict[str, Any] = {}
            try:
                try:
                    balance_before = self._account_status(client)
                except Exception:
                    logger.exception("RunningHub 调用前账户余额读取失败")
                if task_id:
                    progress(5, f"正在重新连接 RunningHub 任务 {task_id[:8]}")
                else:
                    input_names = self._upload_inputs(client, job)
                    node_info_list = self._node_info_list(job, input_names)
                    schema = (
                        job.get("request", {}).get("runninghub_schema")
                        or self.node.runninghub_schema
                        or {}
                    )
                    if self.is_ai_app:
                        submit_path = str(
                            schema.get("submit_path") or "/task/openapi/ai-app/run"
                        )
                        if submit_path.startswith("/openapi/v2/run/ai-app/"):
                            submit_body = {
                                "nodeInfoList": node_info_list,
                                "instanceType": "default",
                                "usePersonalQueue": False,
                            }
                        else:
                            submit_body = {
                                "apiKey": self.node.api_key,
                                "webappId": self.node.workflow_id,
                                "nodeInfoList": node_info_list,
                                "instanceType": "default",
                            }
                        payload = self._request_json(
                            client,
                            "POST",
                            submit_path,
                            json_data=submit_body,
                            action="提交 AI 应用任务",
                        )
                    else:
                        payload = self._request_json(
                            client,
                            "POST",
                            "/task/openapi/create",
                            json_data={
                                "apiKey": self.node.api_key,
                                "workflowId": self.node.workflow_id,
                                "nodeInfoList": node_info_list,
                            },
                            action="提交任务",
                        )
                    data = payload.get("data")
                    if not isinstance(data, dict):
                        data = payload
                    task_id = str(data.get("taskId") or payload.get("taskId") or "")
                    if not task_id:
                        raise RuntimeError("RunningHub 提交响应缺少 taskId")
                    if str(data.get("taskStatus") or "").upper() == "FAILED":
                        raise RuntimeError(
                            "RunningHub 工作流校验失败："
                            + str(
                                data.get("promptTips")
                                or payload.get("msg")
                                or "未知错误"
                            )[:500]
                        )
                    _write_remote_checkpoint(
                        checkpoint_callback,
                        provider="runninghub",
                        node_id=str(self.node.id),
                        remote_id=task_id,
                    )
                    progress(4, f"已提交 RunningHub 任务 {task_id[:8]}")
                final_result = self._poll(client, task_id, progress, cancelled)
                results = final_result["results"]
                usage = (
                    final_result.get("usage")
                    if isinstance(final_result.get("usage"), dict)
                    else {}
                )
            finally:
                if task_id:
                    if balance_before:
                        try:
                            balance_after = self._account_status(client)
                            self.last_billing = runninghub_billing_delta(
                                balance_before, balance_after
                            )
                        except Exception:
                            logger.exception(
                                "RunningHub 调用后账户余额读取失败，task_id=%s",
                                task_id,
                            )
                    consumed_coins = _runninghub_number(usage.get("consumeCoins"))
                    consumed_money = _runninghub_number(usage.get("consumeMoney"))
                    if consumed_coins is not None or consumed_money is not None:
                        self.last_billing = self.last_billing or {
                            **(balance_before or {}),
                            "measured_at": datetime.now(UTC).isoformat(),
                        }
                    if self.last_billing is not None:
                        if consumed_coins is not None:
                            self.last_billing["consumed_coins"] = consumed_coins
                        if consumed_money is not None:
                            self.last_billing["consumed_money"] = consumed_money
                        if usage:
                            self.last_billing["usage"] = usage
        progress(98, "下载 RunningHub 生成产物")
        output = self._download_result(job, results)
        progress(99, "整理交付文件")
        return output


class SGLangH3Engine:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _wait_for_server(self, progress, cancelled) -> None:
        import httpx

        with httpx.Client(timeout=5, trust_env=False) as client:
            while True:
                if cancelled():
                    raise InterruptedError("generation cancelled")
                try:
                    response = client.get(f"{self.settings.sglang_url}/health")
                    if response.is_success:
                        return
                except httpx.HTTPError:
                    pass
                progress(1, "等待空闲单卡推理引擎就绪")
                time.sleep(self.settings.sglang_poll_seconds)

    @staticmethod
    def _conditions(job: dict[str, Any]) -> list[dict[str, Any]]:
        conditions = []
        for item, path in zip(
            job["request"]["references"], job["input_paths"], strict=True
        ):
            conditions.append(
                {
                    "type": item["type"],
                    "uri": Path(path).resolve().as_uri(),
                    "role": "reference",
                }
            )
        return conditions

    def _payload(self, job: dict[str, Any]) -> dict[str, Any]:
        request = job["request"]
        divisor = math.gcd(request["width"], request["height"])
        aspect_ratio = (
            f"{request['width'] // divisor}:{request['height'] // divisor}"
        )
        return {
            "model": self.settings.sglang_model,
            "prompt": request["prompt"],
            "seconds": int(round(request["duration"])),
            "task": "ref2va",
            "conditions": self._conditions(job),
            "target": {
                "short_edge": min(request["width"], request["height"]),
                "aspect_ratio": aspect_ratio,
                "duration_seconds": float(request["duration"]),
            },
            "num_outputs_per_prompt": 1,
            "num_inference_steps": request["steps"],
            "flow_shift": 12.0,
            "audio_flow_shift": 3.0,
            "seed": request["seed"],
        }

    def generate(self, job, progress, cancelled):
        import httpx

        self._wait_for_server(progress, cancelled)
        progress(3, "提交至单卡推理引擎")
        with httpx.Client(timeout=30, trust_env=False) as client:
            response = client.post(
                f"{self.settings.sglang_url}/v1/videos",
                json=self._payload(job),
            )
            response.raise_for_status()
            remote_job = response.json()
            remote_id = remote_job["id"]
            cancel_requested = False
            while True:
                if cancelled():
                    cancel_requested = True
                response = client.get(
                    f"{self.settings.sglang_url}/v1/videos/{remote_id}"
                )
                response.raise_for_status()
                remote_job = response.json()
                remote_status = remote_job.get("status")
                remote_progress = int(remote_job.get("progress") or 0)
                if cancel_requested:
                    progress(max(3, min(98, remote_progress)), "等待当前单卡计算安全结束")
                elif remote_status == "queued":
                    progress(5, "单卡引擎排队中")
                else:
                    progress(
                        max(8, min(96, 8 + round(remote_progress * 0.88))),
                        "单卡联合音视频生成中",
                    )
                if remote_status == "completed":
                    break
                if remote_status in {"failed", "cancelled", "deleted"}:
                    error = remote_job.get("error") or {}
                    message = error.get("message") if isinstance(error, dict) else error
                    raise RuntimeError(message or f"SGLang task {remote_status}")
                time.sleep(self.settings.sglang_poll_seconds)

            if cancel_requested:
                raise InterruptedError("generation cancelled")

        progress(97, "下载单卡引擎生成结果")
        output = self.settings.outputs_dir / output_file_name(job, ".mp4")
        with httpx.stream(
            "GET",
            f"{self.settings.sglang_url}/v1/videos/{remote_id}/content",
            timeout=600,
            trust_env=False,
        ) as response:
            response.raise_for_status()
            with output.open("wb") as target:
                for chunk in response.iter_bytes():
                    target.write(chunk)
        output.with_suffix(".json").write_text(
            json.dumps(job["request"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        progress(99, "整理交付文件")
        return output


def probe_comfy_node(node: ComfyNodeConfig) -> None:
    import httpx

    with httpx.Client(
        base_url=node.url,
        headers=(
            {"Authorization": f"Bearer {node.api_key}"} if node.api_key else None
        ),
        timeout=httpx.Timeout(8, connect=4),
        trust_env=False,
    ) as client:
        response = client.get("/system_stats")
        response.raise_for_status()


def probe_runninghub_node(node: ComfyNodeConfig) -> dict[str, Any]:
    import httpx

    profile: dict[str, Any] = {}
    with httpx.Client(
        base_url=node.url,
        headers={"Authorization": f"Bearer {node.api_key}"},
        timeout=httpx.Timeout(10, connect=5),
        follow_redirects=True,
        trust_env=False,
    ) as client:
        try:
            response = client.post(
                "/uc/openapi/accountStatus",
                json={"apikey": node.api_key},
            )
            response.raise_for_status()
            payload = RunningHubH3Engine._json_response(response, "读取账户余额")
            profile.update(runninghub_account_profile(payload))
            profile["account_error"] = ""
        except Exception as exc:
            profile["account_error"] = str(exc)[:240]

        try:
            if node.runninghub_resource_type == "ai-app":
                detail_data: dict[str, Any] = {}
                demo_data: dict[str, Any] = {}
                detail_response = client.post(
                    "/api/webapp/detail", json={"webappId": node.workflow_id}
                )
                if detail_response.is_success:
                    detail_payload = RunningHubH3Engine._json_response(
                        detail_response, "读取 AI 应用详情"
                    )
                    if isinstance(detail_payload.get("data"), dict):
                        detail_data = detail_payload["data"]
                try:
                    demo_response = client.get(
                        "/api/webapp/apiCallDemo",
                        params={
                            "apiKey": node.api_key,
                            "webappId": node.workflow_id,
                        },
                    )
                    demo_response.raise_for_status()
                    demo_payload = RunningHubH3Engine._json_response(
                        demo_response, "读取 AI 应用 API 参数"
                    )
                    if isinstance(demo_payload.get("data"), dict):
                        demo_data = demo_payload["data"]
                except Exception:
                    if not detail_data:
                        raise
                schema = build_ai_app_schema(
                    node.workflow_id,
                    node.workflow_url,
                    demo_data,
                    detail_data,
                )
            else:
                response = client.post(
                    "/api/openapi/getJsonApiFormat",
                    json={"apiKey": node.api_key, "workflowId": node.workflow_id},
                )
                response.raise_for_status()
                workflow_payload = RunningHubH3Engine._json_response(
                    response, "读取工作流"
                )
                workflow_data = workflow_payload.get("data") or {}
                if not isinstance(workflow_data, dict):
                    raise RuntimeError("RunningHub 工作流响应缺少 data")
                prompt = workflow_data.get("prompt")
                if isinstance(prompt, str):
                    try:
                        prompt = json.loads(prompt)
                    except json.JSONDecodeError as exc:
                        raise RuntimeError("RunningHub 工作流 JSON 无法解析") from exc
                if not isinstance(prompt, dict):
                    raise RuntimeError("RunningHub 工作流响应缺少 prompt")
                workflow_name = str(
                    workflow_data.get("workflowName")
                    or workflow_data.get("name")
                    or workflow_data.get("title")
                    or node.workflow_name
                    or node.name
                )
                schema = build_workflow_schema(
                    node.workflow_id,
                    node.workflow_url,
                    prompt,
                    workflow_name,
                )
            profile.update(
                {
                    "workflow_name": schema["name"],
                    "runninghub_schema": schema,
                    "runninghub_schema_updated_at": schema["updated_at"],
                    "workflow_error": None,
                }
            )
        except Exception as exc:
            profile["workflow_error"] = str(exc)[:240]
    return profile


def probe_node(node: ComfyNodeConfig) -> dict[str, Any] | None:
    if node.provider == "runninghub":
        return probe_runninghub_node(node)
    probe_comfy_node(node)
    return None


def create_engine(settings: Settings, node: ComfyNodeConfig | None = None):
    if settings.fake_engine:
        return FakeEngine(settings)
    if node and node.provider == "runninghub":
        return RunningHubH3Engine(settings, node)
    if settings.engine_backend == "sglang":
        return SGLangH3Engine(settings)
    if settings.engine_backend == "comfyui":
        return ComfyUIH3Engine(settings, node)
    return MiniMaxH3Engine(settings)
