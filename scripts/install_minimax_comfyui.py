#!/usr/bin/env python3
"""Install the MiniMax H3 Studio ComfyUI workflows, nodes, and model files."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
from urllib.parse import urlparse
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


RESOURCE_ARCHIVE_NAME = "MiniMaxH3-ComfyUI-Resources.zip"
USER_AGENT = "MiniMax-H3-Studio-ComfyUI-Installer/1.0"
CHUNK_SIZE = 8 * 1024 * 1024
PROBE_BYTES = 1024 * 1024

WORKFLOW_SHA256 = {
    "minimax_h3_fl2va_fp8_720p_15s_api.json": "c714b477a13072388d6fa7098b4d49d2336464904c005e00cc30a7226ad2c853",
    "minimax_h3_fl2va_fp8_sa_api.json": "851333a7c07ca39c5094cadbd14d0b15e8609eef4b12ae71e664974f2650dcc0",
    "minimax_h3_fl2va_fp8_turbo_lora_api.json": "4c513b996438c89e77bebdfbf4bceb492d98ef2658e88ec787e3b5609bf5a67d",
    "minimax_h3_ref2va_fp8_digital_human_api.json": "aba8e1859dd57f8948c1d6da2be35daf198e15f6d2633da84e75a371fc471745",
    "minimax_h3_ref2va_fp8_dual_sampling_upscale_api.json": "dc2f8dbf18414d393daeaf895187c142df8633e4d1282bb8eb94133ad58e9b54",
    "minimax_h3_ref2va_fp8_sa_api.json": "204eb6a760d28e4f592a0537ceda864bba02ac8b9f73a64e56f25b32800381e0",
    "minimax_h3_ref2va_fp8_scaled_api.json": "f8d78113fbfc7175aaefd8f79dec060c508c05a78aec943135d7de0f43101892",
    "minimax_h3_ref2va_fp8_tts_api.json": "7269c83bb995fdadb38ef3678be167e238de152cdd8586e33dc4ba384104bc98",
    "minimax_h3_ref2va_fp8_turbo_lora_api.json": "1dab7ff0962e76cf8736f7637522644775b8ab9745b7d7db7afdb7610bbd4c5b",
    "minimax_music3_int8_api.json": "87a5521ecb4f42abed454c1ee6caa674654e1fa716679e311271a0365503dd67",
}

PROFILE_MODEL_IDS = {
    "h3-fl2va": {"fl2va-fp8", "qwen3vl-text-encoder", "audio-vae", "video-vae", "turbo-lora"},
    "h3-ref2va": {"ref2va-fp8", "qwen3vl-text-encoder", "audio-vae", "video-vae", "ref2va-turbo-lora"},
    "music3": {"music3-dit-int8", "music3-text-encoder-int8", "music3-dav"},
}

NODE_DIRS = {
    "ComfyUI-VideoHelperSuite-993082e.zip": "ComfyUI-VideoHelperSuite",
    "ComfyUI-MultiGPU-62f98ed.zip": "comfyui-multigpu",
    "comfyui-minimax-h3-audio-drive-de65ec5.zip": "comfyui-minimax-h3-audio-drive",
    "ComfyUI-YCNodes-MiniMax-H3-ba2ec50.zip": "ComfyUI-YCNodes-MiniMax-H3",
    "Comfyui_Minimax_h3_latent_Upscaler-52a48af.zip": "Comfyui_Minimax_h3_latent_Upscaler",
    "ComfyUI-SolAttn_triton-842c4ea.zip": "ComfyUI-SolAttn_triton",
}


class InstallError(RuntimeError):
    pass


def configure_console_encoding() -> None:
    if os.name == "nt":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")


def say(message: str = "") -> None:
    print(message, flush=True)


def run(command: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except OSError as exc:
        raise InstallError(f"无法运行命令 {command[0]}: {exc}") from exc
    if check and result.returncode:
        details = (result.stderr or result.stdout or "").strip() if capture else ""
        raise InstallError(f"命令失败 ({result.returncode}): {' '.join(command)}\n{details}")
    return result


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Assets:
    def __init__(self, archive_path: Path):
        if not archive_path.is_file():
            raise InstallError(f"缺少资源包，请将 {RESOURCE_ARCHIVE_NAME} 与安装脚本放在同一目录。")
        try:
            self.bundle = zipfile.ZipFile(archive_path)
        except (OSError, zipfile.BadZipFile) as exc:
            raise InstallError(f"资源包无法打开: {archive_path}\n{exc}") from exc
        self.members = set(self.bundle.namelist())

    def validate(self) -> tuple[dict[str, Any], dict[str, Any]]:
        damaged = self.bundle.testzip()
        if damaged:
            raise InstallError(f"资源 ZIP 校验失败，损坏条目: {damaged}")
        required = {
            "model-manifest.json",
            "comfyui_nodes/manifest.json",
            "patches/comfyui-music3-force-duration.patch",
            *(f"workflows/{name}" for name in WORKFLOW_SHA256),
        }
        missing = sorted(required - self.members)
        if missing:
            raise InstallError("资源 ZIP 缺少必需文件: " + ", ".join(missing))
        model_manifest = self.get_json("model-manifest.json")
        node_manifest = self.get_json("comfyui_nodes/manifest.json")
        packages = {package["file"]: package for package in node_manifest.get("packages", [])}
        expected_packages = {"ComfyUI-core-7fe8a61.zip", *NODE_DIRS}
        missing_packages = sorted(expected_packages - packages.keys())
        if missing_packages:
            raise InstallError("节点清单缺少必需压缩包: " + ", ".join(missing_packages))
        for filename, package in packages.items():
            relative = f"comfyui_nodes/{filename}"
            if relative not in self.members:
                raise InstallError(f"资源 ZIP 缺少节点包: {relative}")
            if self.member_sha256(relative) != package["sha256"]:
                raise InstallError(f"资源 ZIP 中的节点包 SHA-256 不匹配: {filename}")
        for filename, expected in WORKFLOW_SHA256.items():
            relative = f"workflows/{filename}"
            if self.member_sha256(relative) != expected:
                raise InstallError(f"资源 ZIP 中的工作流 SHA-256 不匹配: {filename}")
        return model_manifest, node_manifest

    def member_sha256(self, relative: str) -> str:
        digest = hashlib.sha256()
        try:
            with self.bundle.open(relative) as source:
                while chunk := source.read(CHUNK_SIZE):
                    digest.update(chunk)
        except KeyError as exc:
            raise InstallError(f"资源 ZIP 缺少文件: {relative}") from exc
        return digest.hexdigest()

    def get_bytes(self, relative: str, expected_sha256: str | None = None) -> bytes:
        try:
            data = self.bundle.read(relative)
        except KeyError as exc:
            raise InstallError(f"资源 ZIP 缺少文件: {relative}") from exc
        if expected_sha256 and bytes_sha256(data) != expected_sha256:
            raise InstallError(f"资源 SHA-256 不匹配: {relative}")
        return data

    def get_json(self, relative: str) -> dict[str, Any]:
        try:
            return json.loads(self.get_bytes(relative).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InstallError(f"JSON 资源无效: {relative}") from exc

    def get_package(self, relative: str, expected_sha256: str) -> Path:
        cache_dir = Path(tempfile.gettempdir()) / "minimax-h3-studio-installer"
        cache_dir.mkdir(parents=True, exist_ok=True)
        destination = cache_dir / Path(relative).name
        if destination.is_file() and file_sha256(destination) == expected_sha256:
            return destination
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        digest = hashlib.sha256()
        with self.bundle.open(relative) as source, temporary.open("wb") as output:
            while chunk := source.read(CHUNK_SIZE):
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != expected_sha256:
            temporary.unlink(missing_ok=True)
            raise InstallError(f"节点包 SHA-256 不匹配: {relative}")
        temporary.replace(destination)
        return destination


def find_nvidia_smi() -> str | None:
    path = shutil.which("nvidia-smi")
    if path:
        return path
    if os.name == "nt":
        candidates = [
            Path(os.getenv("ProgramW6432", "C:/Program Files")) / "NVIDIA Corporation/NVSMI/nvidia-smi.exe",
            Path(os.getenv("ProgramFiles", "C:/Program Files")) / "NVIDIA Corporation/NVSMI/nvidia-smi.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    return None


def detect_gpus() -> list[dict[str, Any]]:
    nvidia_smi = find_nvidia_smi()
    if not nvidia_smi:
        return []
    result = run(
        [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
        check=False,
        capture=True,
    )
    gpus: list[dict[str, Any]] = []
    if result.returncode:
        return gpus
    for index, line in enumerate(result.stdout.splitlines()):
        parts = [item.strip() for item in line.split(",", 1)]
        if len(parts) != 2:
            continue
        try:
            memory_mib = int(parts[1])
        except ValueError:
            continue
        gpus.append({"index": index, "name": parts[0], "memory_mib": memory_mib})
    visible = os.getenv("CUDA_VISIBLE_DEVICES")
    selected_gpu = os.getenv("GPU_ID")
    if visible is not None:
        if visible.strip() in {"", "-1"}:
            return []
        try:
            visible_indexes = {int(value.strip()) for value in visible.split(",")}
            gpus = [gpu for gpu in gpus if gpu["index"] in visible_indexes]
        except ValueError:
            pass
    elif selected_gpu and selected_gpu.isdigit():
        selected_index = int(selected_gpu)
        gpus = [gpu for gpu in gpus if gpu["index"] == selected_index]
    return gpus


def recommended_profile(gpus: list[dict[str, Any]]) -> tuple[str, str]:
    memory_mib = max((gpu["memory_mib"] for gpu in gpus), default=0)
    if memory_mib >= 23000:
        return "h3-fl2va", "检测到 24 GB 级 NVIDIA GPU；选择项目已验证的 H3 FL2VA 8 步方案。"
    if memory_mib >= 15000:
        return "music3", "检测到 16 GB 级 NVIDIA GPU；选择体积更小的 Music3 INT8。该显存建议未在本项目基线上验证。"
    return "none", "未检测到 NVIDIA GPU，或显存低于 16 GB；只安装 ComfyUI、节点和工作流，不自动下载模型。"


def profile_models(profile: str, model_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    selected_ids = PROFILE_MODEL_IDS.get(profile)
    if profile == "full":
        return [model for model in model_manifest["models"] if model.get("required")]
    if profile == "none":
        return []
    return [model for model in model_manifest["models"] if model["id"] in (selected_ids or set())]


def benchmark_url(url: str) -> tuple[bool, float, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Range": f"bytes=0-{PROBE_BYTES - 1}"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            received = 0
            while received < PROBE_BYTES:
                chunk = response.read(min(128 * 1024, PROBE_BYTES - received))
                if not chunk:
                    break
                received += len(chunk)
            elapsed = max(time.perf_counter() - started, 0.001)
            final_host = urlparse(response.geturl()).hostname or ""
            if response.status not in (200, 206) or received < 16 * 1024:
                return False, 0.0, f"HTTP {response.status}, 仅收到 {received} bytes"
            return True, received / elapsed / (1024 * 1024), final_host
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return False, 0.0, str(exc).splitlines()[0][:160]


def provider_url(provider: str, model: dict[str, Any]) -> str | None:
    sources = model.get("sources") or {}
    if provider == "hf-mirror":
        url = sources.get("huggingface")
        return url.replace("https://huggingface.co/", "https://hf-mirror.com/", 1) if url else None
    return sources.get(provider)


def benchmark_providers(models: list[dict[str, Any]]) -> tuple[list[str], dict[str, tuple[bool, float, str]]]:
    probe_model = next(
        (model for model in models if model["id"] in {"fl2va-fp8", "ref2va-fp8", "music3-dit-int8"}),
        None,
    )
    if not probe_model:
        return [], {}
    urls = {provider: provider_url(provider, probe_model) for provider in ("modelscope", "huggingface", "hf-mirror")}
    results: dict[str, tuple[bool, float, str]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(benchmark_url, url): provider
            for provider, url in urls.items()
            if url
        }
        for future in concurrent.futures.as_completed(futures):
            results[futures[future]] = future.result()
    order = sorted(
        (provider for provider, result in results.items() if result[0]),
        key=lambda provider: results[provider][1],
        reverse=True,
    )
    order.extend(provider for provider in ("modelscope", "hf-mirror", "huggingface") if provider not in order)
    return order, results


def print_network_results(results: dict[str, tuple[bool, float, str]], order: list[str]) -> None:
    say("模型源连通性与速度 (1 MiB Range 探测):")
    for provider in ("modelscope", "hf-mirror", "huggingface"):
        result = results.get(provider)
        if not result:
            say(f"  {provider}: 当前模型没有此源")
        elif result[0]:
            say(f"  {provider}: 可连接，约 {result[1] * 8:.1f} Mbit/s，经 {result[2]}")
        else:
            say(f"  {provider}: 不可连接 ({result[2]})")
    if order:
        say("下载优先级: " + " > ".join(order))


def candidate_urls(model: dict[str, Any], provider_order: list[str], forced_provider: str) -> list[str]:
    providers = [forced_provider] if forced_provider != "auto" else provider_order
    providers.extend(provider for provider in ("modelscope", "hf-mirror", "huggingface") if provider not in providers)
    urls: list[str] = []
    for provider in providers:
        url = provider_url(provider, model)
        if url and url not in urls:
            urls.append(url)
    for url in (model.get("sources") or {}).values():
        if url not in urls:
            urls.append(url)
    return urls


def request_for(url: str, offset: int = 0) -> urllib.request.Request:
    headers = {"User-Agent": USER_AGENT}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    return urllib.request.Request(url, headers=headers)


def download_model(model: dict[str, Any], destination: Path, urls: list[str]) -> None:
    expected_size = int(model["size_bytes"])
    expected_hash = model["sha256"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size == expected_size and file_sha256(destination) == expected_hash:
        say(f"已存在且校验通过: {model['id']}")
        return
    if destination.exists():
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup = destination.with_name(f"{destination.name}.invalid-{stamp}")
        destination.replace(backup)
        say(f"已有文件校验失败，保留备份: {backup}")

    part = destination.with_name(destination.name + ".part")
    last_error = "没有可用下载源"
    for url in urls:
        offset = part.stat().st_size if part.is_file() else 0
        if offset > expected_size:
            part.unlink()
            offset = 0
        try:
            say(f"下载 {model['id']} ({expected_size / (1024**3):.2f} GiB): {urlparse(url).hostname}")
            request = request_for(url, offset)
            with urllib.request.urlopen(request, timeout=90) as response:
                append = offset > 0 and response.status == 206
                mode = "ab" if append else "wb"
                received = offset if append else 0
                with part.open(mode) as output:
                    last_report = time.monotonic()
                    while chunk := response.read(CHUNK_SIZE):
                        output.write(chunk)
                        received += len(chunk)
                        if time.monotonic() - last_report >= 20:
                            percent = min(100.0, received * 100.0 / max(expected_size, 1))
                            say(f"  {percent:.1f}% ({received / (1024**3):.2f}/{expected_size / (1024**3):.2f} GiB)")
                            last_report = time.monotonic()
            if part.stat().st_size == expected_size and file_sha256(part) == expected_hash:
                part.replace(destination)
                say(f"  下载完成，SHA-256 已通过: {model['id']}")
                return
            last_error = f"大小或 SHA-256 不匹配 ({part.stat().st_size} bytes)"
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            invalid = part.with_name(f"{part.name}.invalid-{stamp}")
            part.replace(invalid)
            say(f"  {last_error}，保留临时文件: {invalid}")
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            last_error = str(exc).splitlines()[0][:300]
            say(f"  当前源失败，尝试备用源: {last_error}")
    raise InstallError(f"模型 {model['id']} 下载失败。可重新运行继续下载。最后错误: {last_error}")


def safe_member_path(root: Path, name: str) -> Path:
    normalized = PurePosixPath(name.replace("\\", "/"))
    if normalized.is_absolute() or any(part in ("..", "") for part in normalized.parts):
        raise InstallError(f"压缩包包含不安全路径: {name}")
    destination = root.joinpath(*normalized.parts)
    try:
        destination.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise InstallError(f"压缩包路径越界: {name}") from exc
    return destination


def extract_archive(archive: Path, destination: Path, *, strip_first: bool) -> None:
    with zipfile.ZipFile(archive) as bundle:
        files = [entry for entry in bundle.infolist() if not entry.is_dir()]
        if strip_first:
            roots = {PurePosixPath(entry.filename.replace("\\", "/")).parts[0] for entry in files}
            if len(roots) != 1:
                raise InstallError(f"ComfyUI 核心压缩包目录结构异常: {archive.name}")
            prefix = next(iter(roots)) + "/"
        else:
            prefixes = [entry.filename.replace("\\", "/").split("/", 1)[0] for entry in files]
            counts = {prefix: prefixes.count(prefix) for prefix in set(prefixes)}
            prefix = max(counts, key=counts.get) + "/" if counts else ""
        staged: list[tuple[zipfile.ZipInfo, Path]] = []
        for entry in files:
            normalized = entry.filename.replace("\\", "/")
            if prefix and not normalized.startswith(prefix):
                continue
            relative = normalized[len(prefix):] if prefix else normalized
            if not relative:
                continue
            output = safe_member_path(destination, relative)
            staged.append((entry, output))
        for entry, output in staged:
            if output.exists():
                raise InstallError(f"为保护已有文件，拒绝覆盖: {output}")
        for entry, output in staged:
            output.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as source, output.open("wb") as target:
                shutil.copyfileobj(source, target, CHUNK_SIZE)


def inspect_comfy_root(path: Path) -> tuple[Path, bool]:
    try:
        comfy_root = path.expanduser().resolve()
    except OSError as exc:
        raise InstallError(f"无法解析目录: {path}\n{exc}") from exc
    if comfy_root.exists():
        if not comfy_root.is_dir():
            raise InstallError("输入路径不是目录。")
        if (comfy_root / "main.py").is_file() and (comfy_root / "comfy").is_dir():
            if not os.access(comfy_root, os.W_OK):
                raise InstallError(f"ComfyUI 目录不可写: {comfy_root}")
            return comfy_root, True
        try:
            has_contents = next(comfy_root.iterdir(), None) is not None
        except OSError as exc:
            raise InstallError(f"无法读取目标目录: {comfy_root}\n{exc}") from exc
        if has_contents:
            raise InstallError("目录中已有文件，但未检测到有效的 ComfyUI (需要 main.py 和 comfy/)。请重新输入空目录或 ComfyUI 根目录。")
        if not os.access(comfy_root, os.W_OK):
            raise InstallError(f"目标目录不可写: {comfy_root}")
        return comfy_root, False
    parent = comfy_root.parent
    if not parent.is_dir():
        raise InstallError(f"父目录不存在: {parent}")
    if not os.access(parent, os.W_OK):
        raise InstallError(f"父目录不可写: {parent}")
    return comfy_root, False


def prompt_comfy_root() -> tuple[Path, bool]:
    while True:
        answer = input("请输入 ComfyUI 安装目录 (已存在的目录需包含 main.py 和 comfy/): ").strip()
        answer = answer.strip("\"'")
        if not answer:
            say("目录不能为空，请重新输入。")
            continue
        try:
            return inspect_comfy_root(Path(answer))
        except InstallError as exc:
            say(f"目录检查未通过: {exc}")


def find_comfy_python(comfy_root: Path, is_new: bool) -> tuple[Path, bool]:
    if is_new:
        if sys.version_info[:2] != (3, 11):
            raise InstallError(f"新建 ComfyUI 环境需要 Python 3.11；当前安装器由 {platform.python_version()} 运行。请用 Python 3.11 启动。")
        venv_path = comfy_root / ".venv"
        run([sys.executable, "-m", "venv", str(venv_path)])
        python_path = venv_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not python_path.is_file():
            raise InstallError(f"虚拟环境创建失败: {python_path}")
        return python_path, True

    candidates = [
        comfy_root / "python_embeded" / "python.exe",
        comfy_root / ".venv" / "Scripts" / "python.exe",
        comfy_root / "venv" / "Scripts" / "python.exe",
        comfy_root / ".venv" / "bin" / "python",
        comfy_root / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate, False
    return Path(sys.executable), False


def query_torch(python_path: Path) -> tuple[bool, bool, str]:
    code = "import torch; print(torch.cuda.is_available()); print(torch.__version__)"
    result = run([str(python_path), "-c", code], check=False, capture=True)
    if result.returncode:
        return False, False, ""
    lines = result.stdout.strip().splitlines()
    return True, bool(lines and lines[0].strip() == "True"), lines[1].strip() if len(lines) > 1 else "unknown"


def install_runtime(python_path: Path, comfy_root: Path, model_ids: set[str], gpu_present: bool, new_comfy: bool) -> None:
    has_torch, cuda_available, torch_version = query_torch(python_path)
    if gpu_present and (not has_torch or not cuda_available):
        say("安装与已验证环境对齐的 PyTorch 2.6.0 + CUDA 12.4...")
        run([
            str(python_path), "-m", "pip", "install",
            "torch==2.6.0", "torchvision==0.21.0", "torchaudio==2.6.0",
            "--index-url", "https://download.pytorch.org/whl/cu124",
        ])
        has_torch, cuda_available, torch_version = query_torch(python_path)
        if not cuda_available:
            raise InstallError("已检测到 NVIDIA GPU，但安装后的 PyTorch 未检测到 CUDA。请检查驱动是否至少为 550.54.14。")
    elif not has_torch:
        say("未检测到可用的 NVIDIA PyTorch，安装 CPU 版 PyTorch；MiniMax 推理不能使用 GPU。")
        command = [str(python_path), "-m", "pip", "install", "torch", "torchvision", "torchaudio"]
        if sys.platform != "darwin":
            command.extend(["--index-url", "https://download.pytorch.org/whl/cpu"])
        run(command)

    requirements = comfy_root / "requirements.txt"
    if requirements.is_file():
        say("安装 ComfyUI Python 依赖...")
        run([str(python_path), "-m", "pip", "install", "-r", str(requirements)])
    if model_ids & {"fl2va-fp8", "ref2va-fp8"}:
        has_torchao = run([str(python_path), "-c", "import torchao"], check=False, capture=True).returncode == 0
        if has_torch and cuda_available and not has_torchao:
            if torch_version.startswith("2.6"):
                say("安装 MiniMax H3 NVFP4 文本编码器依赖 torchao 0.9.0...")
                run([str(python_path), "-m", "pip", "install", "torchao==0.9.0"])
            else:
                say(f"注意: 当前 PyTorch 为 {torch_version}，未自动更换 torchao；请按该 PyTorch 版本安装兼容的 torchao。")
    if new_comfy:
        say(f"ComfyUI Python 环境: {python_path}")


def install_custom_nodes(assets: Assets, node_manifest: dict[str, Any], comfy_root: Path, python_path: Path, node_names: set[str]) -> None:
    custom_root = comfy_root / "custom_nodes"
    custom_root.mkdir(parents=True, exist_ok=True)
    requirements_files: list[Path] = []
    for package in node_manifest["packages"]:
        filename = package["file"]
        destination_name = NODE_DIRS.get(filename)
        if not destination_name or filename not in node_names:
            continue
        destination = custom_root / destination_name
        if destination.exists():
            say(f"节点目录已存在，保留现状: {destination_name}")
        else:
            archive = assets.get_package(f"comfyui_nodes/{filename}", package["sha256"])
            extract_archive(archive, destination, strip_first=False)
            say(f"已导入节点: {destination_name}")
        requirements_files.extend(destination.rglob("requirements.txt"))
    unique_requirements = list(dict.fromkeys(requirements_files))
    for requirements in unique_requirements:
        if requirements.is_file() and any(line.strip() and not line.lstrip().startswith("#") for line in requirements.read_text(encoding="utf-8", errors="replace").splitlines()):
            say(f"安装节点依赖: {requirements.relative_to(comfy_root)}")
            run([str(python_path), "-m", "pip", "install", "-r", str(requirements)])


def apply_unified_patch(patch_text: str, root: Path) -> None:
    file_blocks: list[tuple[str, list[list[str]]]] = []
    current_hunk: list[str] | None = None
    for line in patch_text.splitlines(keepends=True):
        if line.startswith("diff --git ") or line.startswith("--- a/"):
            current_hunk = None
        elif line.startswith("+++ b/"):
            file_blocks.append((line[6:].strip(), []))
            current_hunk = None
        elif line.startswith("@@") and file_blocks:
            current_hunk = []
            file_blocks[-1][1].append(current_hunk)
        elif current_hunk is not None and line[:1] in {" ", "+", "-", "\\"}:
            current_hunk.append(line)

    updates: list[tuple[Path, str]] = []
    for relative, hunks in file_blocks:
        target = safe_member_path(root, relative)
        if not target.is_file():
            raise InstallError(f"Music3 补丁目标文件不存在: {target}")
        original = target.read_text(encoding="utf-8")
        if "force_duration" in original:
            continue
        lines = original.splitlines(keepends=True)
        output: list[str] = []
        cursor = 0
        for hunk in hunks:
            old_lines = [line[1:] for line in hunk if line[:1] in {" ", "-"}]
            new_lines = [line[1:] for line in hunk if line[:1] in {" ", "+"}]
            if not old_lines:
                continue
            found = next((index for index in range(cursor, len(lines) - len(old_lines) + 1) if lines[index:index + len(old_lines)] == old_lines), None)
            if found is None:
                raise InstallError(f"Music3 补丁与 {relative} 当前版本不兼容；未写入该文件。")
            output.extend(lines[cursor:found])
            output.extend(new_lines)
            cursor = found + len(old_lines)
        output.extend(lines[cursor:])
        updates.append((target, "".join(output)))
    for target, updated in updates:
        target.write_text(updated, encoding="utf-8", newline="")


def apply_music3_patch(assets: Assets, comfy_root: Path) -> None:
    nodes_file = comfy_root / "comfy_extras" / "nodes_minimax_music.py"
    ar_file = comfy_root / "comfy" / "ldm" / "minimax_music" / "ar.py"
    encoder_file = comfy_root / "comfy" / "text_encoders" / "minimax_music.py"
    if all(path.is_file() for path in (nodes_file, ar_file, encoder_file)) and all(
        marker in path.read_text(encoding="utf-8", errors="replace")
        for path, marker in (
            (nodes_file, "force_duration"),
            (ar_file, "min_audio_frames"),
            (encoder_file, "min_audio_frames"),
        )
    ):
        say("Music3 强制时长补丁已存在。")
        return
    patch = assets.get_bytes("patches/comfyui-music3-force-duration.patch").decode("utf-8")
    apply_unified_patch(patch, comfy_root)
    say("已应用 Music3 强制时长补丁。")


def selected_workflows(profile: str, linux_cuda: bool) -> list[str]:
    fl2va = [
        "minimax_h3_fl2va_fp8_720p_15s_api.json",
        "minimax_h3_fl2va_fp8_turbo_lora_api.json",
    ]
    ref2va = [
        "minimax_h3_ref2va_fp8_scaled_api.json",
        "minimax_h3_ref2va_fp8_turbo_lora_api.json",
        "minimax_h3_ref2va_fp8_digital_human_api.json",
        "minimax_h3_ref2va_fp8_tts_api.json",
        "minimax_h3_ref2va_fp8_dual_sampling_upscale_api.json",
    ]
    if linux_cuda:
        fl2va.append("minimax_h3_fl2va_fp8_sa_api.json")
        ref2va.append("minimax_h3_ref2va_fp8_sa_api.json")
    if profile == "h3-fl2va":
        return fl2va
    if profile == "h3-ref2va":
        return ref2va
    if profile == "music3":
        return ["minimax_music3_int8_api.json"]
    if profile in {"full", "none"}:
        return fl2va + ref2va + ["minimax_music3_int8_api.json"]
    return []


def selected_nodes(profile: str, linux_cuda: bool) -> set[str]:
    nodes: set[str] = set()
    if profile in {"h3-ref2va", "full", "none"}:
        nodes.update({"ComfyUI-VideoHelperSuite-993082e.zip", "comfyui-minimax-h3-audio-drive-de65ec5.zip", "ComfyUI-YCNodes-MiniMax-H3-ba2ec50.zip", "Comfyui_Minimax_h3_latent_Upscaler-52a48af.zip"})
    if profile in {"music3", "full", "none"}:
        nodes.add("ComfyUI-MultiGPU-62f98ed.zip")
    if linux_cuda and profile in {"h3-fl2va", "h3-ref2va", "full", "none"}:
        nodes.update({"ComfyUI-YCNodes-MiniMax-H3-ba2ec50.zip", "Comfyui_Minimax_h3_latent_Upscaler-52a48af.zip", "ComfyUI-SolAttn_triton-842c4ea.zip"})
    return nodes


def import_workflows(assets: Assets, comfy_root: Path, workflows: list[str]) -> None:
    destination_root = comfy_root / "user" / "default" / "workflows"
    destination_root.mkdir(parents=True, exist_ok=True)
    for filename in workflows:
        digest = WORKFLOW_SHA256[filename]
        data = assets.get_bytes(f"workflows/{filename}", digest)
        destination = destination_root / filename
        if destination.is_file() and file_sha256(destination) == digest:
            say(f"工作流已存在且校验通过: {filename}")
            continue
        if destination.exists():
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            backup = destination.with_name(f"{destination.name}.backup-{stamp}")
            destination.replace(backup)
            say(f"工作流备份: {backup}")
        destination.write_bytes(data)
        say(f"已导入工作流: {destination}")


def human_size(size: int) -> str:
    return f"{size / (1024 ** 3):.2f} GiB"


def plan_model_downloads(models: list[dict[str, Any]], comfy_root: Path) -> tuple[list[dict[str, Any]], int]:
    pending: list[dict[str, Any]] = []
    download_bytes = 0
    for model in models:
        destination = comfy_root / "models" / model["target"]
        expected_size = int(model["size_bytes"])
        if destination.is_file() and destination.stat().st_size == expected_size:
            say(f"校验已有模型: {model['id']}")
            if file_sha256(destination) == model["sha256"]:
                say(f"  已有模型 SHA-256 通过: {model['id']}")
                continue
        partial = destination.with_name(destination.name + ".part")
        partial_size = partial.stat().st_size if partial.is_file() else 0
        download_bytes += max(0, expected_size - min(expected_size, partial_size))
        pending.append(model)
    return pending, download_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="在 Windows 或 Linux 安装 MiniMax H3 Studio 的 ComfyUI 资源。")
    parser.add_argument("--comfy-root", type=Path, help="ComfyUI 根目录；省略时交互输入")
    parser.add_argument("--model-profile", choices=("auto", "h3-fl2va", "h3-ref2va", "music3", "full", "none"), default="auto")
    parser.add_argument("--model-provider", choices=("auto", "modelscope", "huggingface", "hf-mirror"), default="auto")
    parser.add_argument("--resource-archive", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--yes", action="store_true", help="兼容旧命令；安装过程默认直接执行")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    if args.comfy_root is None:
        if args.yes:
            raise InstallError("非交互运行请通过 --comfy-root 指定目标目录。")
        comfy_root, existing_comfy = prompt_comfy_root()
    else:
        comfy_root, existing_comfy = inspect_comfy_root(args.comfy_root)
    if not existing_comfy and sys.version_info[:2] != (3, 11):
        raise InstallError(f"新建 ComfyUI 环境需要 Python 3.11；当前安装器由 {platform.python_version()} 运行。请用 Python 3.11 启动。")
    resource_archive = args.resource_archive or (script_path.parent / RESOURCE_ARCHIVE_NAME)
    assets = Assets(resource_archive.expanduser().resolve())
    model_manifest, node_manifest = assets.validate()
    gpus = detect_gpus()
    recommended, reason = recommended_profile(gpus)

    say("MiniMax H3 Studio · ComfyUI 一键安装")
    say(f"系统: {platform.system()} {platform.release()} | Python: {platform.python_version()}")
    say(f"ComfyUI 目录: {comfy_root} ({'已检测到现有 ComfyUI' if existing_comfy else '将安装 ComfyUI 本体'})")
    if gpus:
        say("NVIDIA GPU: " + "; ".join(f"GPU {gpu['index']} {gpu['name']} {gpu['memory_mib'] / 1024:.1f} GiB" for gpu in gpus))
    else:
        say("NVIDIA GPU: 未检测到")
    say("自动建议: " + reason)

    profile = recommended if args.model_profile == "auto" else args.model_profile
    if profile != recommended:
        say(f"模型方案由命令行指定: {profile}")
    models = profile_models(profile, model_manifest)
    model_ids = {model["id"] for model in models}
    if profile == "full":
        say("完整方案不会下载需要授权的 NaughtyTimes LoRA，也不会下载清单外的 VDN/超分检查点。")
    pending_models, total_bytes = plan_model_downloads(models, comfy_root)

    provider_order: list[str] = []
    network_results: dict[str, tuple[bool, float, str]] = {}
    if pending_models:
        provider_order, network_results = benchmark_providers(models)
        print_network_results(network_results, provider_order)
        if args.model_provider != "auto":
            provider_order = [args.model_provider] + [provider for provider in provider_order if provider != args.model_provider]

    linux_cuda = sys.platform.startswith("linux") and bool(gpus)
    workflows = selected_workflows(profile, linux_cuda)
    nodes = selected_nodes(profile, linux_cuda)
    need_music_patch = "music3" in model_ids or profile in {"full", "none"}
    say(f"模型方案: {profile} | 需要下载 {human_size(total_bytes)}")
    say(f"导入工作流: {len(workflows)} 个 | 安装自定义节点: {len(nodes)} 个")
    if "h3-fl2va" == profile:
        say("注意: H3 FP8 + NVFP4 文本编码器的项目最低验证配置为 24 GB 显存、64 GB 内存、100 GB SSD 可用空间。")
    if profile == "music3" and (not gpus or max(gpu["memory_mib"] for gpu in gpus) < 23000):
        say("注意: Music3 INT8 方案的 16 GB 显存门槛是基于模型文件体积的建议值，未在本项目最低配置中单独验证。")
    if os.name == "nt" and profile in {"h3-fl2va", "h3-ref2va", "full"}:
        say("Windows 不导入依赖 Triton 的 H3 SA 工作流；其余选定工作流使用跨平台节点。")
    if profile == "none":
        say("当前只导入平台兼容的节点和工作流模板，不下载模型；下载对应权重后才能运行生成。")

    reserve_space = 8 * 1024**3 if not existing_comfy else (2 * 1024**3 if pending_models else 0)
    required_space = total_bytes + reserve_space
    if required_space and comfy_root.parent.exists():
        free_space = shutil.disk_usage(comfy_root.parent).free
        say(f"目标磁盘剩余: {human_size(free_space)}")
        if free_space < required_space:
            raise InstallError(f"可用空间不足，至少需要约 {human_size(required_space)}；请更换 --comfy-root 或选择更小模型方案。")

    say("\n安装计划:")
    say(f"  ComfyUI: {'复用现有目录' if existing_comfy else '从项目固定版本安装'}")
    say(f"  模型: {', '.join(model_ids) if model_ids else '不下载'}")
    say(f"  模型来源优先级: {' > '.join(provider_order) if provider_order else '不适用'}")
    say(f"  工作流: {', '.join(workflows) if workflows else '无'}")
    say(f"  自定义节点包: {', '.join(sorted(nodes)) if nodes else '无'}")
    comfy_root.mkdir(parents=True, exist_ok=True)
    if not existing_comfy:
        core = next(package for package in node_manifest["packages"] if package["file"] == "ComfyUI-core-7fe8a61.zip")
        archive = assets.get_package(f"comfyui_nodes/{core['file']}", core["sha256"])
        say(f"安装固定版本 ComfyUI: {core['commit']}")
        extract_archive(archive, comfy_root, strip_first=True)
        if not (comfy_root / "main.py").is_file():
            raise InstallError("ComfyUI 主程序解压后未找到 main.py。")

    has_h3_workflows = any(name.startswith("minimax_h3_") for name in workflows)
    if has_h3_workflows:
        core_nodes = comfy_root / "comfy_api_nodes" / "nodes_minimax.py"
        if not core_nodes.is_file():
            raise InstallError("现有 ComfyUI 缺少 MiniMax H3 核心节点 (comfy_api_nodes/nodes_minimax.py)。为避免覆盖用户安装，请用空目录安装固定版 ComfyUI，或先升级现有 ComfyUI。")
    if need_music_patch:
        apply_music3_patch(assets, comfy_root)

    is_new = not existing_comfy
    python_path, _ = find_comfy_python(comfy_root, is_new)
    install_runtime(python_path, comfy_root, model_ids, bool(gpus), is_new)
    install_custom_nodes(assets, node_manifest, comfy_root, python_path, nodes)

    for folder in ("diffusion_models", "text_encoders", "vae", "loras", "checkpoints", "upscale_models"):
        (comfy_root / "models" / folder).mkdir(parents=True, exist_ok=True)
    for model in pending_models:
        destination = comfy_root / "models" / model["target"]
        download_model(model, destination, candidate_urls(model, provider_order, args.model_provider))

    import_workflows(assets, comfy_root, workflows)
    say("\n安装完成。")
    say(f"ComfyUI: {comfy_root}")
    say(f"工作流目录: {comfy_root / 'user' / 'default' / 'workflows'}")
    say("工作流 API JSON 已保存到 user/default/workflows；这些模板可提交到 ComfyUI /prompt API。")
    say("默认启动命令: " + (f'"{python_path}" "{comfy_root / "main.py"}" --listen 127.0.0.1 --port 8188' if os.name == "nt" else f'"{python_path}" "{comfy_root / "main.py"}" --listen 127.0.0.1 --port 8188'))
    if profile != "full":
        say("只下载了所选模型方案；其他 MiniMax 工作流需要对应模型文件后才能运行。")
    return 0


if __name__ == "__main__":
    configure_console_encoding()
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        say("\n已中断。已完成文件会保留，模型下载的 .part 文件可在下次运行时续传。")
        raise SystemExit(130)
    except InstallError as exc:
        say(f"\n安装失败: {exc}")
        raise SystemExit(1)
