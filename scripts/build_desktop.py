from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "MiniMaxH3Studio"
VOLUME_NAME = "MiniMax H3 Studio"


def build_macos_dmg(app_bundle: Path) -> Path:
    dmg_path = ROOT / "dist" / f"{APP_NAME}.dmg"
    with tempfile.TemporaryDirectory(prefix="minimax-h3-dmg-") as temp_dir:
        staging = Path(temp_dir)
        shutil.copytree(app_bundle, staging / app_bundle.name, symlinks=True)
        (staging / "Applications").symlink_to("/Applications", target_is_directory=True)
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
                str(dmg_path),
            ],
            check=True,
        )
    return dmg_path


def main() -> None:
    try:
        import PyInstaller.__main__
    except ImportError as exc:
        raise SystemExit("请先安装 requirements-desktop.txt") from exc

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
    print(f"桌面应用已生成：{output}")
    if sys.platform == "darwin":
        app_bundle = ROOT / "dist" / f"{APP_NAME}.app"
        dmg_path = build_macos_dmg(app_bundle)
        print(f"DMG 已生成：{dmg_path}")


if __name__ == "__main__":
    main()
