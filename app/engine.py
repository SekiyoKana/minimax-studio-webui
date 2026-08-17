from __future__ import annotations

import json
import logging
import math
import mimetypes
import os
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
from .settings import Settings


logger = logging.getLogger(__name__)


class RunningHubTransientResponseError(RuntimeError):
    pass


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


def runninghub_workflow_profile(workflow: dict[str, Any]) -> dict[str, str]:
    class_types = {
        str(node.get("class_type") or "")
        for node in workflow.values()
        if isinstance(node, dict)
    }
    workflow_text = json.dumps(workflow, ensure_ascii=False).lower()
    if {
        "MiniMaxMusic3TextEncode",
        "EmptyMiniMaxMusic3LatentAudio",
    }.intersection(class_types):
        return {
            "workflow_variant": "music3-int8",
            "workflow_execution_mode": "music3",
        }
    if "VRGDG_MiniMaxH3AudioDrive" in class_types:
        return {
            "workflow_variant": "ref2va-fp8",
            "workflow_execution_mode": "digital-human",
        }
    if "ref2va" in workflow_text:
        variant = "ref2va-fp8"
    elif "fl2va" in workflow_text or "fl2v" in workflow_text:
        variant = "fl2va-fp8"
    else:
        raise RuntimeError("无法识别 RunningHub 目标工作流的生成类型")
    if "naughtytimes" in workflow_text:
        execution_mode = "h3-nsfw"
    elif "8step" in workflow_text or "8-step" in workflow_text:
        execution_mode = "turbo-lora"
    else:
        execution_mode = "native"
    return {
        "workflow_variant": variant,
        "workflow_execution_mode": execution_mode,
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
        if job["request"].get("model_variant") == "music3-int8":
            import wave

            output = self.settings.outputs_dir / f"{job['id']}.wav"
            with wave.open(str(output), "wb") as target:
                target.setnchannels(2)
                target.setsampwidth(2)
                target.setframerate(32000)
                target.writeframes(b"\0\0\0\0" * 3200)
            return output
        source = Path(job["input_paths"][0])
        output = self.settings.outputs_dir / f"{job['id']}.jpg"
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

        output = self.settings.outputs_dir / f"{job['id']}.mp4"
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
    NODE_STAGES = {
        "3": (7, "加载 Music3 文本编码器"),
        "6": (5, "加载 Music3 INT8 DiT"),
        "7": (9, "加载 Music3 音频解码器"),
        "13": (12, "编码音乐描述与歌词"),
        "9": (15, "Music3 音频采样"),
        "42": (92, "分块解码 Music3 音频"),
        "127": (6, "加载 MiniMax H3 FP8 模型"),
        "128": (8, "加载 Qwen3-VL 文本编码器"),
        "141": (10, "加载 H3 NSFW LoRA"),
        "136": (12, "编码提示词与首尾帧"),
        "171": (10, "加载数字人驱动音频"),
        "172": (14, "编码并锁定数字人驱动音频"),
        "125": (15, "联合音视频采样"),
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
            ("ref2va-fp8", "h3-nsfw"): self.settings.comfy_nsfw_workflow,
            ("ref2va-fp8", "digital-human"): self.settings.comfy_digital_human_workflow,
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
        if execution_mode == "h3-nsfw":
            required.add("141")
        if execution_mode == "digital-human":
            required.update({"137", "171", "172"})
        missing = sorted(required.difference(workflow))
        if missing:
            raise ValueError(f"ComfyUI 工作流缺少节点：{', '.join(missing)}")
        return workflow

    def _prepare_inputs(self, job: dict[str, Any]) -> tuple[Path, list[str]]:
        paths = [Path(path) for path in job["input_paths"]]
        manifest = job["request"]["references"]
        if not paths or len(paths) != len(manifest):
            raise ValueError("参考素材清单与文件不一致")
        task_dir = self.settings.comfy_input_dir / "minimax-h3-api" / job["id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        relative_paths = []
        for index, (source, item) in enumerate(zip(paths, manifest, strict=True), start=1):
            suffix = source.suffix.lower() or ".png"
            target = task_dir / f"{index:02d}_{item['type']}{suffix}"
            shutil.copy2(source, target)
            relative_paths.append(target.relative_to(self.settings.comfy_input_dir).as_posix())
        return task_dir, relative_paths

    def _upload_inputs(self, client, job: dict[str, Any]) -> list[str]:
        paths = [Path(path) for path in job["input_paths"]]
        manifest = job["request"]["references"]
        if not paths or len(paths) != len(manifest):
            raise ValueError("参考素材清单与文件不一致")
        subfolder = f"minimax-h3-api/{job['id']}"
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
    ) -> dict[str, Any]:
        variant = self._variant(job)
        execution_mode = self._execution_mode(job)
        workflow = self._load_workflow(variant, execution_mode)
        request = job["request"]
        workflow["92"]["inputs"]["filename_prefix"] = f"minimax-h3-api/{job['id']}"
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
            width=request["width"],
            height=request["height"],
            length=request["num_frames"],
        )
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

    def _poll_until_finished(self, client, prompt_id, progress, cancelled):
        while True:
            if cancelled():
                self._cancel_prompt(client, prompt_id)
                raise InterruptedError("generation cancelled")
            history = self._history(client, prompt_id)
            if history:
                return history
            queue_data = client.get("/queue").json()
            running = self._prompt_ids(queue_data.get("queue_running", []))
            stage = "ComfyUI FP8 工作流执行中" if prompt_id in running else "等待 ComfyUI 执行"
            progress(5, stage)
            time.sleep(self.settings.comfy_poll_seconds)

    def _wait_for_finished(self, socket, client, prompt_id, progress, cancelled):
        while True:
            if cancelled():
                self._cancel_prompt(client, prompt_id)
                raise InterruptedError("generation cancelled")
            try:
                raw = socket.recv(timeout=self.settings.comfy_poll_seconds)
            except TimeoutError:
                history = self._history(client, prompt_id)
                if history:
                    return history
                continue
            except Exception:
                return self._poll_until_finished(client, prompt_id, progress, cancelled)
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
                progress(5, "ComfyUI FP8 工作流开始执行")
            elif event_type == "executing":
                node = str(data.get("node"))
                if node in self.NODE_STAGES:
                    percent, stage = self.NODE_STAGES[node]
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
                progress(percent, f"联合音视频采样 {value}/{total}")
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
        music3 = self._variant(job) == "music3-int8"
        expected_suffix = ".flac" if music3 else ".mp4"
        result_item = next(
            (
                item
                for item in candidates
                if str(item.get("filename", "")).lower().endswith(expected_suffix)
            ),
            None,
        )
        if not result_item:
            media_name = "FLAC" if music3 else "MP4"
            raise RuntimeError(f"ComfyUI 历史记录中没有找到节点 92 的 {media_name} 产物")
        output = self.settings.outputs_dir / f"{job['id']}{expected_suffix}"
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

    def generate(self, job, progress, cancelled):
        import httpx
        from websockets.sync.client import connect

        prompt_id = None
        client_id = f"minimax-h3-api-{uuid.uuid4().hex}"
        websocket_url = self.comfy_url.replace("http://", "ws://", 1).replace(
            "https://", "wss://", 1
        )
        try:
            music3 = self._variant(job) == "music3-int8"
            progress(2, "准备 ComfyUI Music3 工作流" if music3 else "准备 ComfyUI FP8 工作流")
            timeout = httpx.Timeout(30, connect=10)
            with httpx.Client(
                base_url=self.comfy_url,
                headers=self.api_headers,
                timeout=timeout,
                trust_env=False,
            ) as client:
                stats_response = client.get("/system_stats")
                stats_response.raise_for_status()
                input_names = [] if music3 else self._upload_inputs(client, job)
                music3_device = (
                    self._comfy_cuda_device(stats_response.json()) if music3 else None
                )
                workflow = self._build_workflow(job, input_names, music3_device)
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
                    progress(4, f"已提交 ComfyUI 任务 {prompt_id[:8]}")
                    history = self._wait_for_finished(
                        socket, client, prompt_id, progress, cancelled
                    )
                if cancelled():
                    self._cancel_prompt(client, prompt_id)
                    raise InterruptedError("generation cancelled")
                progress(98, "回传 ComfyUI 生成产物")
                output = self._copy_result(job, history, client)
            progress(99, "整理交付文件")
            return output
        finally:
            self._release_vram()


class RunningHubH3Engine:
    MAX_UPLOAD_BYTES = 30 * 1024 * 1024
    MAX_POLL_SECONDS = 2 * 60 * 60

    def __init__(self, settings: Settings, node: ComfyNodeConfig):
        self.settings = settings
        self.node = node
        self.base_url = node.url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {node.api_key}"}
        self.workflow_builder = ComfyUIH3Engine(settings)
        self._remote_workflow: dict[str, Any] | None = None
        self.last_billing: dict[str, Any] | None = None

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
        if code not in {None, 0, "0"}:
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
        raise RuntimeError(f"RunningHub {action}请求失败：{last_error}") from last_error

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
                            "/task/openapi/upload",
                            data={"apiKey": self.node.api_key, "fileType": "input"},
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
                            detail.get("msg") or detail.get("message")
                            if isinstance(detail, dict)
                            else None
                        )
                        raise RuntimeError(
                            f"RunningHub 文件上传失败：{source.name}："
                            f"{message or response.status_code}"
                        )
                    response.raise_for_status()
                    payload = self._json_response(response, "文件上传")
                    file_name = str((payload.get("data") or {}).get("fileName") or "")
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

    def _get_remote_workflow(self, client) -> dict[str, Any]:
        if self._remote_workflow is not None:
            return self._remote_workflow
        payload = self._request_json(
            client,
            "POST",
            "/api/openapi/getJsonApiFormat",
            json_data={
                "apiKey": self.node.api_key,
                "workflowId": self.node.workflow_id,
            },
            action="读取工作流",
        )
        prompt = (payload.get("data") or {}).get("prompt")
        if isinstance(prompt, str):
            try:
                prompt = json.loads(prompt)
            except json.JSONDecodeError as exc:
                raise RuntimeError("RunningHub 工作流 JSON 无法解析") from exc
        if not isinstance(prompt, dict):
            raise RuntimeError("RunningHub 工作流响应缺少 prompt")
        self._remote_workflow = prompt
        return prompt

    def _node_info_list(
        self,
        job: dict[str, Any],
        input_names: list[str],
        remote_workflow: dict[str, Any],
    ) -> list[dict[str, Any]]:
        variant = self.workflow_builder._variant(job)
        execution_mode = self.workflow_builder._execution_mode(job)
        base_workflow = self.workflow_builder._load_workflow(variant, execution_mode)
        built_workflow = self.workflow_builder._build_workflow(job, input_names)
        result = []
        changed_node_ids = set()
        for node_id, node in built_workflow.items():
            inputs = node.get("inputs") or {}
            base_inputs = (base_workflow.get(node_id) or {}).get("inputs") or {}
            for field_name, field_value in inputs.items():
                if node_id not in base_workflow or base_inputs.get(field_name) != field_value:
                    changed_node_ids.add(node_id)
                    result.append(
                        {
                            "nodeId": str(node_id),
                            "fieldName": str(field_name),
                            "fieldValue": field_value,
                        }
                    )

        missing = sorted(changed_node_ids.difference(remote_workflow))
        mismatched = sorted(
            node_id
            for node_id in changed_node_ids.intersection(remote_workflow)
            if (remote_workflow[node_id] or {}).get("class_type")
            != (built_workflow[node_id] or {}).get("class_type")
        )
        if missing or mismatched:
            details = []
            if missing:
                details.append("缺少节点 " + ", ".join(missing))
            if mismatched:
                details.append("节点类型不匹配 " + ", ".join(mismatched))
            raise RuntimeError(
                "RunningHub 目标工作流与当前生成方案不兼容：" + "；".join(details)
            )
        return result

    def _cancel_task(self, client, task_id: str) -> None:
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

    def _poll(self, client, task_id: str, progress, cancelled) -> list[dict[str, Any]]:
        deadline = time.monotonic() + self.MAX_POLL_SECONDS
        last_status = ""
        while time.monotonic() < deadline:
            if cancelled():
                self._cancel_task(client, task_id)
                raise InterruptedError("generation cancelled")
            payload = self._request_json(
                client,
                "POST",
                "/openapi/v2/query",
                json_data={"taskId": task_id},
                action="查询任务",
            )
            status = str(payload.get("status") or "").upper()
            if status != last_status:
                if status in {"CREATE", "QUEUED"}:
                    progress(5, "等待 RunningHub 调度")
                elif status == "RUNNING":
                    progress(15, "RunningHub 工作流执行中")
                last_status = status
            if status == "SUCCESS":
                results = payload.get("results") or []
                if not isinstance(results, list) or not results:
                    raise RuntimeError("RunningHub 任务成功但未返回生成结果")
                return [item for item in results if isinstance(item, dict)]
            if status in {"FAILED", "CANCEL"}:
                message = payload.get("errorMessage") or payload.get("promptTips") or status
                raise RuntimeError(f"RunningHub 任务{status}：{str(message)[:500]}")
            time.sleep(max(2.0, self.settings.comfy_poll_seconds))
        raise TimeoutError(f"RunningHub 任务轮询超时，taskId={task_id}")

    def _download_result(self, job: dict[str, Any], results: list[dict[str, Any]]) -> Path:
        import httpx

        music3 = self.workflow_builder._variant(job) == "music3-int8"
        expected_suffix = ".flac" if music3 else ".mp4"
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
                if urlsplit(url).path.lower().endswith(expected_suffix)
                or output_type.lower().lstrip(".") == expected_suffix.lstrip(".")
            ),
            candidates[0][0] if candidates else "",
        )
        if not selected:
            raise RuntimeError("RunningHub 生成结果中没有可下载文件")
        output = self.settings.outputs_dir / f"{job['id']}{expected_suffix}"
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

    def generate(self, job, progress, cancelled):
        import httpx

        progress(2, "准备 RunningHub 工作流")
        self.last_billing = None
        timeout = httpx.Timeout(60, connect=10)
        with httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout,
            follow_redirects=True,
            trust_env=False,
        ) as client:
            balance_before: dict[str, Any] | None = None
            task_id = ""
            try:
                try:
                    balance_before = self._account_status(client)
                except Exception:
                    logger.exception("RunningHub 调用前账户余额读取失败")
                input_names = self._upload_inputs(client, job)
                remote_workflow = self._get_remote_workflow(client)
                node_info_list = self._node_info_list(job, input_names, remote_workflow)
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
                data = payload.get("data") or {}
                task_id = str(data.get("taskId") or payload.get("taskId") or "")
                if not task_id:
                    raise RuntimeError("RunningHub 提交响应缺少 taskId")
                if str(data.get("taskStatus") or "").upper() == "FAILED":
                    raise RuntimeError(
                        "RunningHub 工作流校验失败："
                        + str(data.get("promptTips") or payload.get("msg") or "未知错误")[:500]
                    )
                progress(4, f"已提交 RunningHub 任务 {task_id[:8]}")
                results = self._poll(client, task_id, progress, cancelled)
            finally:
                if task_id and balance_before:
                    try:
                        balance_after = self._account_status(client)
                        self.last_billing = runninghub_billing_delta(
                            balance_before, balance_after
                        )
                    except Exception:
                        logger.exception(
                            "RunningHub 调用后账户余额读取失败，task_id=%s", task_id
                        )
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
        output = self.settings.outputs_dir / f"{job['id']}.mp4"
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

    with httpx.Client(
        base_url=node.url,
        headers={"Authorization": f"Bearer {node.api_key}"},
        timeout=httpx.Timeout(10, connect=5),
        follow_redirects=True,
        trust_env=False,
    ) as client:
        response = client.post(
            "/uc/openapi/accountStatus",
            json={"apikey": node.api_key},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("code") not in {0, "0"}:
            message = payload.get("msg") if isinstance(payload, dict) else None
            raise RuntimeError(f"RunningHub 账户余额读取失败：{message or '响应无效'}")
        account_profile = runninghub_account_profile(payload)
        response = client.post(
            "/api/openapi/getJsonApiFormat",
            json={"apiKey": node.api_key, "workflowId": node.workflow_id},
        )
        response.raise_for_status()
        payload = RunningHubH3Engine._json_response(response, "读取工作流")
        prompt = (payload.get("data") or {}).get("prompt")
        if isinstance(prompt, str):
            try:
                prompt = json.loads(prompt)
            except json.JSONDecodeError as exc:
                raise RuntimeError("RunningHub 工作流 JSON 无法解析") from exc
        if not isinstance(prompt, dict):
            raise RuntimeError("RunningHub 工作流响应缺少 prompt")
        return {**runninghub_workflow_profile(prompt), **account_profile}


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
