from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "MiniMaxH3Studio"
VOLUME_NAME = "MiniMax H3 Studio"


def make_console_utf8() -> None:
    """让构建日志不再依赖控制台编码。

    Windows CI 运行器默认使用 cp1252 代码页，只要打印任何非 ASCII 字符，
    PyInstaller 打包成功后也会因为 UnicodeEncodeError 让整个构建失败。
    这里把标准输出/错误流尽量切换到 UTF-8，无法切换时退化为可转义输出。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            pass


def detach_stale_volume(volume_name: str) -> None:
    """清理遗留挂载，避免 hdiutil 因为 "Resource busy" 直接失败。"""
    mount_point = Path("/Volumes") / volume_name
    if not mount_point.exists():
        return
    subprocess.run(
        ["hdiutil", "detach", str(mount_point), "-force"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def build_macos_dmg(app_bundle: Path, attempts: int = 3) -> Path:
    """把 .app 打包成 dmg；hdiutil 偶发 "Resource busy" 时自动重试。"""
    dmg_path = ROOT / "dist" / f"{APP_NAME}.dmg"
    for attempt in range(1, attempts + 1):
        detach_stale_volume(VOLUME_NAME)
        dmg_path.unlink(missing_ok=True)
        with tempfile.TemporaryDirectory(prefix="minimax-h3-dmg-") as temp_dir:
            staging = Path(temp_dir)
            shutil.copytree(app_bundle, staging / app_bundle.name, symlinks=True)
            (staging / "Applications").symlink_to(
                "/Applications", target_is_directory=True
            )
            try:
                subprocess.run(
                    [
                        "hdiutil",
                        "create",
                        "-volname",
                        VOLUME_NAME,
                        "-srcfolder",
                        str(staging),
                        "-ov",
                        "-format",
                        "UDZO",
                        "-nospotlight",
                        str(dmg_path),
                    ],
                    check=True,
                )
            except subprocess.CalledProcessError:
                if attempt == attempts:
                    raise
                print(
                    f"hdiutil create failed (attempt {attempt}/{attempts}), "
                    "cleaning up and retrying...",
                    flush=True,
                )
                time.sleep(5 * attempt)
                continue
        return dmg_path
    raise RuntimeError("unreachable")


def main() -> None:
    make_console_utf8()
    try:
        import PyInstaller.__main__
    except ImportError as exc:
        raise SystemExit("Please install requirements-desktop.txt first.") from exc

    separator = ";" if os.name == "nt" else ":"
    icon = (
        ROOT / "assets" / "h3-studio.ico"
        if os.name == "nt"
        else ROOT / "assets" / "h3-studio.icns"
    )
    args = [
        str(ROOT / "desktop.py"),
        f"--name={APP_NAME}",
        "--windowed",
        "--onedir",
        "--noconfirm",
        "--clean",
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build' / 'desktop'}",
        f"--specpath={ROOT / 'build'}",
        f"--add-data={ROOT / 'static'}{separator}static",
        f"--add-data={ROOT / 'workflows'}{separator}workflows",
        "--collect-all=webview",
        "--hidden-import=websockets.sync.client",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--exclude-module=torch",
        "--exclude-module=diffsynth",
        "--exclude-module=app.diffsynth_compat",
    ]
    if icon.exists():
        args.append(f"--icon={icon}")
    if sys.platform == "darwin":
        args.append("--osx-bundle-identifier=com.sekiyo.minimaxh3studio")
    for directory in (ROOT / "build", ROOT / "dist"):
        if directory.exists() and directory.name == "build":
            shutil.rmtree(directory)
    PyInstaller.__main__.run(args)
    output = ROOT / "dist" / APP_NAME
    if not output.exists():
        raise SystemExit(f"Desktop build output is missing: {output}")
    print(f"Desktop app generated: {output}", flush=True)
    if sys.platform == "darwin":
        app_bundle = ROOT / "dist" / f"{APP_NAME}.app"
        if not app_bundle.exists():
            raise SystemExit(f"macOS app bundle is missing: {app_bundle}")
        dmg_path = build_macos_dmg(app_bundle)
        print(f"DMG generated: {dmg_path}", flush=True)


if __name__ == "__main__":
    main()
