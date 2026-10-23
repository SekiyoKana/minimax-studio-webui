"""本地 ComfyUI 接管功能的单元测试。"""

import asyncio
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app import main as main_module
from app.local_comfy import (
    LocalComfySupervisor,
    _path_variants,
    resolve_launch_target,
    url_port,
    venv_python_candidates,
)

STUB_SERVER = (
    "import http.server, sys\n"
    "class Handler(http.server.BaseHTTPRequestHandler):\n"
    "    def do_GET(self):\n"
    "        body = b'{}'\n"
    "        self.send_response(200)\n"
    "        self.send_header('Content-Type', 'application/json')\n"
    "        self.send_header('Content-Length', str(len(body)))\n"
    "        self.end_headers()\n"
    "        self.wfile.write(body)\n"
    "    def log_message(self, *args):\n"
    "        pass\n"
    "port = int(sys.argv[sys.argv.index('--port') + 1])\n"
    "http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()\n"
)


class LaunchTargetTests(unittest.TestCase):
    def test_resolves_directory_with_main_py(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("print('comfy')\n", encoding="utf-8")
            script, workdir = resolve_launch_target(str(root))
            self.assertEqual(script, (root / "main.py").resolve())
            self.assertEqual(workdir, root.resolve())

    def test_resolves_main_py_file(self):
        with TemporaryDirectory() as temp:
            script_path = Path(temp) / "main.py"
            script_path.write_text("print('comfy')\n", encoding="utf-8")
            script, workdir = resolve_launch_target(str(script_path))
            self.assertEqual(script, script_path.resolve())
            self.assertEqual(workdir, script_path.resolve().parent)

    def test_accepts_path_without_py_suffix(self):
        with TemporaryDirectory() as temp:
            script_path = Path(temp) / "main.py"
            script_path.write_text("print('comfy')\n", encoding="utf-8")
            script, _ = resolve_launch_target(str(Path(temp) / "main"))
            self.assertEqual(script, script_path.resolve())

    def test_accepts_forward_slash_path(self):
        with TemporaryDirectory() as temp:
            script_path = Path(temp) / "main.py"
            script_path.write_text("print('comfy')\n", encoding="utf-8")
            forward = str(script_path).replace("\\", "/")
            script, workdir = resolve_launch_target(forward)
            self.assertEqual(script, script_path.resolve())
            self.assertEqual(workdir, script_path.resolve().parent)

    def test_path_variants_collapse_separators(self):
        variants = _path_variants("D:/ComfyUI")
        # normcase only folds case on Windows; compare case-insensitively so
        # the same assertion also covers macOS and Linux test runs.
        normalized = {
            os.path.normcase(os.path.normpath(str(item))).casefold()
            for item in variants
        }
        self.assertEqual(len(normalized), 1)
        self.assertTrue(normalized.pop().endswith("comfyui"))

    def test_path_variants_expand_user_home(self):
        home = str(Path.home())
        variants = _path_variants("~/ComfyUI")
        self.assertIn(os.path.normpath(os.path.join(home, "ComfyUI")), [os.path.normpath(str(item)) for item in variants])

    def test_rejects_empty_path(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_launch_target("   ")
        self.assertIn("未配置", str(ctx.exception))

    def test_rejects_missing_path(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_launch_target("Z:/definitely-missing-comfy")
        self.assertIn("不存在", str(ctx.exception))

    def test_rejects_directory_without_main_py(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(ValueError) as ctx:
                resolve_launch_target(temp)
            self.assertIn("main.py", str(ctx.exception))

    def test_url_port(self):
        self.assertEqual(url_port("http://127.0.0.1:8191"), 8191)
        self.assertEqual(url_port("http://127.0.0.1"), 8188)
        self.assertEqual(url_port(""), 8188)


class PythonEnvironmentTests(unittest.TestCase):
    def _supervisor(self, temp: str) -> LocalComfySupervisor:
        return LocalComfySupervisor(Path(temp) / "logs")

    def test_venv_candidates_put_node_directory_first(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "venv" / "Scripts").mkdir(parents=True)
            (root / "venv" / "Scripts" / "python.exe").write_text("", encoding="utf-8")
            candidates = [str(item) for item in venv_python_candidates(root)]
            self.assertTrue(candidates[0].endswith(str(Path("venv") / "Scripts" / "python.exe")))
            self.assertIn(str(Path(root.parent) / "venv" / "Scripts" / "python.exe"), candidates)

    def test_prefers_private_environment(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("", encoding="utf-8")
            venv_python = root / ".venv" / "Scripts" / "python.exe"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("", encoding="utf-8")
            supervisor = self._supervisor(temp)

            def works(command, timeout=10.0):
                return command[0] == str(venv_python)

            with patch("app.local_comfy._command_works", side_effect=works):
                command, source = supervisor._resolve_python(root)
            self.assertEqual(source, "私有环境")
            self.assertEqual(command, [str(venv_python)])

    def test_falls_back_to_global_python(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("", encoding="utf-8")
            supervisor = self._supervisor(temp)
            with patch("app.local_comfy._command_works", return_value=False), patch.object(
                supervisor, "_detect_global_python", return_value=["C:/Python/python.exe"]
            ):
                command, source = supervisor._resolve_python(root)
            self.assertEqual(source, "全局环境")
            self.assertEqual(command, ["C:/Python/python.exe"])

    def test_raises_when_no_python_found(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("", encoding="utf-8")
            supervisor = self._supervisor(temp)
            with patch("app.local_comfy._command_works", return_value=False), patch.object(
                supervisor, "_detect_global_python", return_value=[]
            ):
                with self.assertRaises(ValueError) as ctx:
                    supervisor._resolve_python(root)
            self.assertIn("Python", str(ctx.exception))


class StartFailureTests(unittest.TestCase):
    def test_start_failure_reports_original_error(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "main.py"
            script.write_text(
                "import sys\n"
                "sys.stderr.write('Traceback (most recent call last):\\nModuleNotFoundError: No module named torch\\n')\n"
                "sys.exit(2)\n",
                encoding="utf-8",
            )
            events: list[tuple[str, str]] = []
            supervisor = LocalComfySupervisor(
                root / "logs",
                event_sink=lambda message, level="info": events.append((message, level)),
                start_wait=30.0,
                ready_timeout=30.0,
                poll_interval=0.05,
            )
            with patch("app.local_comfy._probe", return_value=False), patch.object(
                supervisor, "_resolve_python", return_value=([sys.executable], "全局环境")
            ):
                with self.assertRaises(ValueError) as ctx:
                    supervisor.start("node-1", "本机 ComfyUI", "http://127.0.0.1:65530", str(root))
            message = str(ctx.exception)
            self.assertIn("原始报错", message)
            self.assertIn("No module named torch", message)
            state = supervisor.status("node-1")
            self.assertEqual(state["status"], "failed")
            log_path = Path(state["log_path"])
            self.assertTrue(log_path.exists())
            self.assertIn("No module named torch", log_path.read_text(encoding="utf-8", errors="replace"))
            self.assertTrue(any(level == "error" and "torch" in text for text, level in events))

    def test_stop_of_unmanaged_running_service_is_rejected(self):
        with TemporaryDirectory() as temp:
            supervisor = LocalComfySupervisor(Path(temp) / "logs")
            supervisor._states["node-1"] = {
                **supervisor.status("node-1"),
                "node_id": "node-1",
                "status": "running",
                "managed": False,
                "url": "http://127.0.0.1:8188",
            }
            with patch("app.local_comfy._probe", return_value=True):
                with self.assertRaises(ValueError) as ctx:
                    supervisor.stop("node-1")
            self.assertIn("手动关闭", str(ctx.exception))


class ShutdownTests(unittest.TestCase):
    """Studio 退出时应关闭由本应用启动的本地 ComfyUI。"""

    def _free_port(self) -> int:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            return int(probe.getsockname()[1])

    def _reachable(self, port: int) -> bool:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                return int(response.status) < 500
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def _supervisor(self, root: Path, events: list[tuple[str, str]]) -> LocalComfySupervisor:
        return LocalComfySupervisor(
            root / "logs",
            event_sink=lambda message, level="info": events.append((message, level)),
            start_wait=20.0,
            ready_timeout=20.0,
            poll_interval=0.05,
        )

    def test_shutdown_terminates_managed_process(self):
        port = self._free_port()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text(STUB_SERVER, encoding="utf-8")
            events: list[tuple[str, str]] = []
            supervisor = self._supervisor(root, events)
            with patch.object(supervisor, "_resolve_python", return_value=([sys.executable], "全局环境")):
                state = supervisor.start("node-1", "本机 ComfyUI", f"http://127.0.0.1:{port}", str(root))
            self.assertEqual(state["status"], "running")
            self.assertTrue(self._reachable(port))
            supervisor.shutdown()
            self.assertEqual(supervisor.status("node-1")["status"], "stopped")
            self.assertFalse(self._reachable(port))
            self.assertTrue(any("应用退出" in text for text, _ in events))

    def test_shutdown_without_managed_processes(self):
        with TemporaryDirectory() as temp:
            supervisor = LocalComfySupervisor(Path(temp) / "logs")
            supervisor.shutdown()  # 不应抛异常
            self.assertEqual(supervisor.status("node-1")["status"], "stopped")

    def test_shutdown_keeps_external_service_running(self):
        port = self._free_port()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "stub.py"
            script.write_text(STUB_SERVER, encoding="utf-8")
            external = subprocess.Popen(
                [sys.executable, str(script), "--port", str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                for _ in range(100):
                    if self._reachable(port):
                        break
                    time.sleep(0.1)
                events: list[tuple[str, str]] = []
                supervisor = self._supervisor(root, events)
                state = supervisor.start("node-1", "本机 ComfyUI", f"http://127.0.0.1:{port}", str(script))
                self.assertEqual(state["status"], "running")
                self.assertFalse(state["managed"])
                supervisor.shutdown()
                self.assertTrue(self._reachable(port))
            finally:
                external.terminate()
                external.wait(timeout=10)


class EndpointTests(unittest.TestCase):
    local_node = {
        "id": "node-1",
        "name": "本机 ComfyUI",
        "url": "http://127.0.0.1:8188",
        "provider": "comfyui",
        "launch_path": "D:/ComfyUI",
    }

    def _run(self, coro):
        return asyncio.run(coro)

    def _patch(self, *, bind: bool, node: dict | None = None, runtime=None, error: Exception | None = None):
        registry = SimpleNamespace(get=lambda node_id: (node if node is not None else dict(self.local_node)))

        def start(*args, **kwargs):
            if error is not None:
                raise error
            return runtime or {"status": "running", "pid": 1234, "node_id": "node-1"}

        supervisor = SimpleNamespace(start=start, stop=lambda node_id: runtime or {"status": "stopped", "node_id": node_id})
        return (
            patch.object(main_module, "node_registry", registry),
            patch.object(main_module, "local_state", SimpleNamespace(general_settings=lambda include_secret=False: {"bind_local_comfyui": bind})),
            patch.object(main_module, "local_comfy", supervisor),
        )

    def test_start_requires_feature_flag(self):
        for context in self._patch(bind=False):
            context.start()
        try:
            with self.assertRaises(HTTPException) as ctx:
                self._run(main_module.start_local_comfy_node("node-1"))
            self.assertEqual(ctx.exception.status_code, 422)
            self.assertIn("未开启", ctx.exception.detail)
        finally:
            for context in self._patch(bind=False):
                context.stop()

    def test_start_rejects_remote_node(self):
        node = dict(self.local_node, url="https://example.com")
        contexts = self._patch(bind=True, node=node)
        for context in contexts:
            context.start()
        try:
            with self.assertRaises(HTTPException) as ctx:
                self._run(main_module.start_local_comfy_node("node-1"))
            self.assertEqual(ctx.exception.status_code, 422)
            self.assertIn("本机", ctx.exception.detail)
        finally:
            for context in contexts:
                context.stop()

    def test_start_rejects_non_comfyui_node(self):
        node = dict(self.local_node, provider="runninghub")
        contexts = self._patch(bind=True, node=node)
        for context in contexts:
            context.start()
        try:
            with self.assertRaises(HTTPException) as ctx:
                self._run(main_module.start_local_comfy_node("node-1"))
            self.assertEqual(ctx.exception.status_code, 422)
            self.assertIn("ComfyUI", ctx.exception.detail)
        finally:
            for context in contexts:
                context.stop()

    def test_start_passes_launch_path_and_returns_runtime(self):
        calls: list[tuple] = []

        def start(*args, **kwargs):
            calls.append(args)
            return {"status": "starting", "pid": 4321, "node_id": "node-1"}

        contexts = self._patch(bind=True)
        registry, local_state, local_comfy = contexts
        registry.start()
        local_state.start()
        patch.object(main_module, "local_comfy", SimpleNamespace(start=start, stop=lambda node_id: {})).start()
        try:
            result = self._run(main_module.start_local_comfy_node("node-1"))
        finally:
            for context in contexts:
                context.stop()
        self.assertEqual(result["node_id"], "node-1")
        self.assertEqual(result["local_runtime"]["status"], "starting")
        self.assertEqual(calls, [("node-1", "本机 ComfyUI", "http://127.0.0.1:8188", "D:/ComfyUI")])

    def test_start_maps_value_error_to_422(self):
        contexts = self._patch(bind=True, error=ValueError("Python 环境不可用"))
        for context in contexts:
            context.start()
        try:
            with self.assertRaises(HTTPException) as ctx:
                self._run(main_module.start_local_comfy_node("node-1"))
            self.assertEqual(ctx.exception.status_code, 422)
            self.assertIn("Python 环境不可用", ctx.exception.detail)
        finally:
            for context in contexts:
                context.stop()

    def test_stop_returns_runtime(self):
        contexts = self._patch(bind=True, runtime={"status": "stopped", "node_id": "node-1"})
        for context in contexts:
            context.start()
        try:
            result = self._run(main_module.stop_local_comfy_node("node-1"))
        finally:
            for context in contexts:
                context.stop()
        self.assertEqual(result["local_runtime"]["status"], "stopped")

    def test_missing_node_returns_404(self):
        contexts = self._patch(bind=True, node=None)
        registry = SimpleNamespace(get=lambda node_id: None)
        patch.object(main_module, "node_registry", registry).start()
        try:
            with self.assertRaises(HTTPException) as ctx:
                self._run(main_module.start_local_comfy_node("missing"))
            self.assertEqual(ctx.exception.status_code, 404)
        finally:
            for context in contexts:
                context.stop()


if __name__ == "__main__":
    unittest.main()
