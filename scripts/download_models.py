#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(16 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def is_valid(path: Path, expected_size: int, expected_sha256: str) -> bool:
    if not path.is_file() or path.stat().st_size != expected_size:
        return False
    return file_sha256(path) == expected_sha256


def backup_invalid(path: Path) -> None:
    if not path.exists():
        return
    control = path.with_name(f"{path.name}.aria2")
    if control.exists():
        print(f"发现未完成下载，保留控制文件并继续: {path}")
        return
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.invalid-{timestamp}")
    path.replace(backup)
    print(f"校验失败的旧文件已移动到 {backup}")


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    connections = "8" if "modelscope.cn" in url else "1"
    command = [
        "aria2c",
        "--continue=true",
        "--allow-overwrite=false",
        "--auto-file-renaming=false",
        "--file-allocation=none",
        "--max-tries=0",
        "--retry-wait=5",
        "--timeout=60",
        f"--max-connection-per-server={connections}",
        f"--split={connections}",
        "--min-split-size=64M",
        f"--dir={destination.parent}",
        f"--out={destination.name}",
        url,
    ]
    subprocess.run(command, check=True)


def select_source(model: dict, provider: str) -> str | None:
    sources = model.get("sources") or {}
    return sources.get(provider) or sources.get("modelscope") or sources.get("huggingface")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and verify MiniMax H3 model files.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--comfy-root", type=Path, required=True)
    parser.add_argument("--provider", choices=("modelscope", "huggingface"), default="modelscope")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--include-nsfw", action="store_true")
    parser.add_argument("--nsfw-file", type=Path)
    parser.add_argument("--nsfw-url")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    failures = []
    for model in manifest["models"]:
        optional = not model["required"]
        if optional and not args.include_nsfw:
            continue
        destination = args.comfy_root / "models" / model["target"]
        expected_size = int(model["size_bytes"])
        expected_sha256 = model["sha256"]
        print(f"检查 {model['id']}: {destination}", flush=True)
        if is_valid(destination, expected_size, expected_sha256):
            print("  SHA-256 已通过", flush=True)
            continue
        if args.verify_only:
            failures.append(model["id"])
            continue

        backup_invalid(destination)
        if model["id"] == "naughtytimes-lora" and args.nsfw_file:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(args.nsfw_file.expanduser(), destination)
        else:
            source_url = args.nsfw_url if model["id"] == "naughtytimes-lora" else None
            source_url = source_url or select_source(model, args.provider)
            if not source_url:
                raise SystemExit(
                    "NaughtyTimes LoRA 当前没有公开稳定下载地址。"
                    "请使用 --nsfw-file 或 --nsfw-url 提供已获授权的文件。"
                )
            download(source_url, destination)

        if not is_valid(destination, expected_size, expected_sha256):
            failures.append(model["id"])
            print(f"  校验失败: {destination}", file=sys.stderr)
        else:
            print("  下载完成且 SHA-256 已通过", flush=True)

    if failures:
        print("模型校验失败: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
