from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from .settings import Settings


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
        "127": (6, "加载 MiniMax H3 FP8 模型"),
        "128": (8, "加载 Qwen3-VL 文本编码器"),
        "141": (10, "加载 H3 NSFW LoRA"),
        "136": (12, "编码提示词与首尾帧"),
        "125": (15, "联合音视频采样"),
        "121": (90, "解码音频"),
        "122": (92, "解码视频"),
        "130": (95, "合成音视频"),
        "92": (97, "保存 MP4 产物"),
    }

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _variant(job: dict[str, Any]) -> str:
        # Jobs created before model selection was added are FL2VA jobs.
        return job["request"].get("model_variant") or "fl2va-fp8"

    @staticmethod
    def _execution_mode(job: dict[str, Any]) -> str:
        return job["request"].get("execution_mode") or "native"

    def _load_workflow(self, variant: str, execution_mode: str = "native") -> dict[str, Any]:
        workflow_paths = {
            ("fl2va-fp8", "native"): self.settings.comfy_workflow,
            ("fl2va-fp8", "turbo-lora"): self.settings.comfy_turbo_workflow,
            ("ref2va-fp8", "native"): self.settings.comfy_ref2va_workflow,
            ("ref2va-fp8", "turbo-lora"): self.settings.comfy_ref2va_turbo_workflow,
            ("ref2va-fp8", "h3-nsfw"): self.settings.comfy_nsfw_workflow,
        }
        try:
            workflow_path = workflow_paths[(variant, execution_mode)]
        except KeyError as exc:
            raise ValueError(f"不支持的执行方案：{variant}/{execution_mode}") from exc
        if not workflow_path.exists():
            raise FileNotFoundError(f"ComfyUI 工作流不存在：{workflow_path}")
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        required = {"92", "124", "125", "129", "136", "137"}
        if variant == "ref2va-fp8":
            required.discard("137")
        if execution_mode == "turbo-lora":
            required.add("142")
        if execution_mode == "h3-nsfw":
            required.add("141")
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

    def _build_workflow(self, job: dict[str, Any], input_names: list[str]) -> dict[str, Any]:
        variant = self._variant(job)
        execution_mode = self._execution_mode(job)
        workflow = self._load_workflow(variant, execution_mode)
        request = job["request"]
        workflow["92"]["inputs"]["filename_prefix"] = f"minimax-h3-api/{job['id']}"
        workflow["124"]["inputs"]["steps"] = request["steps"]
        workflow["129"]["inputs"]["noise_seed"] = request["seed"]
        conditioning = workflow["136"]["inputs"]
        conditioning.update(
            prompt=request["prompt"],
            width=request["width"],
            height=request["height"],
            length=request["num_frames"],
        )
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

    def _copy_result(self, job, history: dict[str, Any]) -> Path:
        status = history.get("status") or {}
        if status.get("completed") is not True or status.get("status_str") != "success":
            messages = status.get("messages") or []
            raise RuntimeError(f"ComfyUI 未成功完成工作流：{messages[-1:]}")
        output_items = (history.get("outputs") or {}).get("92") or {}
        candidates = []
        for items in output_items.values():
            if isinstance(items, list):
                candidates.extend(item for item in items if isinstance(item, dict))
        video = next(
            (item for item in candidates if str(item.get("filename", "")).lower().endswith(".mp4")),
            None,
        )
        if not video:
            raise RuntimeError("ComfyUI 历史记录中没有找到节点 92 的 MP4 产物")
        output_root = self.settings.comfy_output_dir.resolve()
        source = (output_root / str(video.get("subfolder") or "") / video["filename"]).resolve()
        try:
            source.relative_to(output_root)
        except ValueError as exc:
            raise RuntimeError("ComfyUI 返回了非法产物路径") from exc
        if not source.is_file():
            raise FileNotFoundError(f"ComfyUI 产物不存在：{source}")
        output = self.settings.outputs_dir / f"{job['id']}.mp4"
        shutil.copy2(source, output)
        output.with_suffix(".json").write_text(
            json.dumps(job["request"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        source.unlink(missing_ok=True)
        return output

    def generate(self, job, progress, cancelled):
        import httpx
        from websockets.sync.client import connect

        task_dir = None
        prompt_id = None
        client_id = f"minimax-h3-api-{uuid.uuid4().hex}"
        websocket_url = self.settings.comfy_url.rstrip("/").replace("http://", "ws://", 1).replace(
            "https://", "wss://", 1
        )
        try:
            progress(2, "准备 ComfyUI FP8 工作流")
            task_dir, input_names = self._prepare_inputs(job)
            workflow = self._build_workflow(job, input_names)
            timeout = httpx.Timeout(30, connect=10)
            with httpx.Client(base_url=self.settings.comfy_url, timeout=timeout, trust_env=False) as client:
                client.get("/system_stats").raise_for_status()
                with connect(f"{websocket_url}/ws?clientId={client_id}", open_timeout=10, max_size=None) as socket:
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
            output = self._copy_result(job, history)
            progress(99, "整理交付文件")
            return output
        finally:
            if task_dir:
                shutil.rmtree(task_dir, ignore_errors=True)


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


def create_engine(settings: Settings):
    if settings.fake_engine:
        return FakeEngine(settings)
    if settings.engine_backend == "sglang":
        return SGLangH3Engine(settings)
    if settings.engine_backend == "comfyui":
        return ComfyUIH3Engine(settings)
    return MiniMaxH3Engine(settings)
