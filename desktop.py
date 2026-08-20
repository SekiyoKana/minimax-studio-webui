from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


APP_NAME = "MiniMax H3 Studio"
DEFAULT_PORT = 38193
DEFAULT_COMFY_URL = "http://100.77.224.102:8188"


def application_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if os.name == "nt":
        return Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / APP_NAME
    return Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "minimax-h3-studio"


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("0.0.0.0", port))
        except OSError:
            return False
    return True


def choose_port() -> int:
    requested = int(os.getenv("H3_DESKTOP_PORT", str(DEFAULT_PORT)))
    if not 1024 <= requested <= 65535:
        raise RuntimeError("H3_DESKTOP_PORT 必须为 1024 至 65535")
    if not port_available(requested):
        raise RuntimeError(f"本机端口 {requested} 已被占用，请设置 H3_DESKTOP_PORT")
    return requested


def wait_for_server(url: str, timeout: float = 20) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.15)
    raise RuntimeError("本地桌面服务启动超时")


def main() -> None:
    data_dir = application_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    port = choose_port()
    os.environ.setdefault("H3_ROOT", str(data_dir))
    os.environ.setdefault("H3_HOST", "0.0.0.0")
    os.environ.setdefault("H3_PORT", str(port))
    os.environ.setdefault("H3_DESKTOP_MODE", "1")
    os.environ.setdefault("H3_DEFAULT_COMFY_URL", DEFAULT_COMFY_URL)
    os.environ.setdefault("H3_DEFAULT_COMFY_NAME", "远端 ComfyUI · tapcash-llm")

    import uvicorn
    import webview
    from app.main import app as api_app

    local_url = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(
        uvicorn.Config(
            api_app,
            host="0.0.0.0",
            port=port,
            log_level="warning",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, name="minimax-studio-webui", daemon=True)
    thread.start()
    try:
        wait_for_server(local_url)
        webview.create_window(APP_NAME, local_url, width=1440, height=960, min_size=(960, 640))
        webview.start(debug=False)
    finally:
        server.should_exit = True
        thread.join(timeout=10)


if __name__ == "__main__":
    main()
