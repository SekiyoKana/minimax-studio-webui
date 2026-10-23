"""本机 ComfyUI 服务的启动与关闭托管。

只负责本机环境 ComfyUI 节点的进程托管：优先使用节点目录中的私有
Python 环境（venv/.venv/env），找不到时回退到全局 Python 环境。
启动失败时把失败原因和原始报错写入节点日志文件与运行日志。
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .jobs import utc_now

logger = logging.getLogger("minimax_h3.local_comfy")

LAUNCH_SCRIPT_NAMES = ("main.py", "ComfyUI/main.py")
VENV_DIR_NAMES = ("venv", ".venv", "env", ".env", "python_env")
EMBEDDED_PYTHON_DIRS = ("python_embeded", "python_embedded")
LOG_TAIL_LINES = 40
LOG_MAX_BYTES = 5 * 1024 * 1024
SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")
SHUTDOWN_TIMEOUT = 6.0

if os.name == "nt":  # pragma: no cover - 平台相关
    import ctypes
    from ctypes import wintypes

    _HANDLE = wintypes.HANDLE
    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000

    class _IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class _JobBasicLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    class _JobLimits(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JobBasicLimits),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

else:  # pragma: no cover - 平台相关
    ctypes = None  # type: ignore[assignment]
    _HANDLE = None  # type: ignore[assignment]
    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0
    _JobLimits = None  # type: ignore[assignment,misc]


def _no_window_flags() -> int:
    """Windows 下隐藏子进程控制台窗口。"""
    if os.name != "nt":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _stopped_state() -> dict[str, Any]:
    return {
        "node_id": "",
        "status": "stopped",
        "managed": False,
        "pid": 0,
        "started_at": "",
        "ready_at": "",
        "error": "",
        "python": "",
        "launch_dir": "",
        "log_path": "",
        "url": "",
        "name": "",
    }


def url_port(url: str, default: int = 8188) -> int:
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return default
    try:
        return parsed.port or default
    except ValueError:
        return default


def url_host(url: str, default: str = "127.0.0.1") -> str:
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return default
    return parsed.hostname or default


def _path_variants(raw: str) -> list[Path]:
    """把用户填写的路径展开为可尝试的候选（兼容 Windows 与 macOS 写法）。"""
    text = (raw or "").strip().strip('"').strip("'")
    if text.lower().startswith("file://"):
        text = text[7:]
    variants: list[str] = [text]
    if "\\" in text:
        variants.append(text.replace("\\", "/"))
    if "/" in text and os.name == "nt":
        variants.append(text.replace("/", "\\"))
    expanded: list[str] = []
    for value in variants:
        if not value:
            continue
        value = os.path.expandvars(os.path.expanduser(value))
        if value not in expanded:
            expanded.append(value)
    return [Path(value) for value in expanded]


def resolve_launch_target(launch_path: str) -> tuple[Path, Path]:
    """把用户填写的启动路径解析为 (启动脚本, 工作目录)，兼容 Windows 与 macOS 路径。"""
    raw = (launch_path or "").strip().strip('"').strip("'")
    if not raw:
        raise ValueError("未配置 ComfyUI 启动路径，请先在节点编辑中填写 ComfyUI 目录或 main.py 路径")
    path: Path | None = None
    for candidate in _path_variants(raw):
        if candidate.exists():
            path = candidate
            break
        if candidate.suffix.lower() != ".py":
            script = candidate.with_name(candidate.name + ".py")
            if script.exists():
                path = script
                break
    if path is None:
        raise ValueError(f"ComfyUI 启动路径不存在：{raw}")
    if path.is_file():
        if path.suffix.lower() != ".py":
            raise ValueError(f"启动路径需要是 ComfyUI 目录或 main.py 文件：{path}")
        return path.resolve(), path.resolve().parent
    for name in LAUNCH_SCRIPT_NAMES:
        candidate = path / name
        if candidate.is_file():
            return candidate.resolve(), candidate.resolve().parent
    raise ValueError(f"目录中没有找到 ComfyUI 的 main.py：{path}")


def venv_python_candidates(launch_dir: Path) -> list[Path]:
    """列出节点目录及其父目录中可能存在的私有 Python 环境。"""
    candidates: list[Path] = []
    roots = [launch_dir, launch_dir.parent]
    for root in roots:
        for name in VENV_DIR_NAMES:
            venv = root / name
            candidates.extend(
                (
                    venv / "Scripts" / "python.exe",
                    venv / "Scripts" / "python",
                    venv / "bin" / "python",
                    venv / "bin" / "python3",
                )
            )
        for name in EMBEDDED_PYTHON_DIRS:
            candidates.append(root / name / "python.exe")
    for root in roots:
        candidates.extend((root / "python.exe", root / "python", root / "python3"))
    unique: list[Path] = []
    seen: set[str] = set()
    for item in candidates:
        # normcase only folds case on Windows; casefold keeps the dedupe
        # behaviour consistent on macOS and Linux as well.
        key = os.path.normcase(str(item)).casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _command_works(command: list[str], timeout: float = 10.0) -> bool:
    try:
        result = subprocess.run(
            [*command, "-c", "import sys; print(sys.version_info[0])"],
            capture_output=True,
            timeout=timeout,
            creationflags=_no_window_flags(),
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _probe(url: str, timeout: float = 2.0) -> bool:
    """探测地址上是否已有可用的 ComfyUI 服务。"""
    base = (url or "").strip().rstrip("/")
    if not base:
        return False
    for path in ("/system_stats", "/"):
        try:
            with urllib.request.urlopen(f"{base}{path}", timeout=timeout) as response:
                if 200 <= int(response.status) < 500:
                    return True
        except urllib.error.HTTPError as exc:
            if int(exc.code) < 500:
                return True
        except (urllib.error.URLError, OSError, ValueError):
            continue
    return False


class _ProcessTreeGuard:
    """把托管的 ComfyUI 进程放进 kill-on-close 的 Job 对象。

    正常退出时由 ``shutdown()`` 主动结束进程；当 Studio 进程被强制结束
    （崩溃、任务管理器）时，Windows 会在作业句柄关闭时一并结束这些进程，
    避免留下孤儿 ComfyUI。非 Windows 平台不做处理。
    """

    def __init__(self) -> None:
        self._kernel32: Any | None = None
        self._handle: int | None = None
        self._disabled = os.name != "nt"

    def attach(self, process: subprocess.Popen[bytes]) -> None:
        if self._disabled:
            return
        handle = self._job_handle()
        if handle is None:
            return
        raw = getattr(process, "_handle", None)
        if not raw:
            return
        try:
            if not self._kernel32.AssignProcessToJobObject(handle, _HANDLE(int(raw))):
                raise ctypes.WinError(ctypes.get_last_error())
        except Exception:  # noqa: BLE001 - 托管失败不应影响启动
            self._disabled = True
            logger.warning("无法把本地 ComfyUI 进程加入托管作业，Studio 异常退出时可能残留进程", exc_info=True)

    def release(self) -> None:
        handle, self._handle = self._handle, None
        if not handle:
            return
        try:
            self._kernel32.CloseHandle(_HANDLE(handle))
        except Exception:  # noqa: BLE001 - 释放失败无关紧要
            pass

    def _job_handle(self) -> int | None:
        if self._handle is not None:
            return self._handle
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateJobObjectW.restype = _HANDLE
            kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p)
            kernel32.SetInformationJobObject.argtypes = (
                _HANDLE,
                ctypes.c_int,
                ctypes.c_void_p,
                ctypes.c_uint32,
            )
            kernel32.AssignProcessToJobObject.argtypes = (_HANDLE, _HANDLE)
            kernel32.CloseHandle.argtypes = (_HANDLE,)
            handle = kernel32.CreateJobObjectW(None, None)
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            limits = _JobLimits()
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not kernel32.SetInformationJobObject(
                handle,
                JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(limits),
                ctypes.sizeof(limits),
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            self._kernel32 = kernel32
            self._handle = handle
            return handle
        except Exception:  # noqa: BLE001 - 无 Job 时仍可正常托管
            self._disabled = True
            logger.warning("创建托管作业失败，Studio 异常退出时可能残留本地 ComfyUI 进程", exc_info=True)
            return None


class LocalComfySupervisor:
    """托管本机 ComfyUI 进程：启动、就绪探测、关闭与日志收集。"""

    def __init__(
        self,
        log_dir: Path,
        *,
        event_sink: Callable[..., None] | None = None,
        start_wait: float = 5.0,
        ready_timeout: float = 180.0,
        poll_interval: float = 1.0,
    ) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._event_sink = event_sink
        self.start_wait = max(0.0, float(start_wait))
        self.ready_timeout = max(self.start_wait, float(ready_timeout))
        self.poll_interval = max(0.05, float(poll_interval))
        self._lock = threading.RLock()
        self._states: dict[str, dict[str, Any]] = {}
        self._procs: dict[str, subprocess.Popen[bytes]] = {}
        self._guard = _ProcessTreeGuard()
        self._shutting_down = False

    # ------------------------------------------------------------------ 状态
    def status(self, node_id: str) -> dict[str, Any]:
        with self._lock:
            state = self._states.get(str(node_id))
            return dict(state) if state else _stopped_state()

    def statuses(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {key: dict(value) for key, value in self._states.items()}

    # ------------------------------------------------------------------ 启动
    def start(
        self,
        node_id: str,
        name: str,
        url: str,
        launch_path: str,
        *,
        wait: float | None = None,
    ) -> dict[str, Any]:
        key = str(node_id)
        with self._lock:
            running = self._procs.get(key)
            state = dict(self._states.get(key) or _stopped_state())
            if running is not None and running.poll() is not None:
                self._procs.pop(key, None)
                running = None
        if running is not None:
            if state.get("status") in {"starting", "running", "stopping"}:
                return state
            # 进程仍存活，但上次等待就绪已超时（状态为 failed）：重新开始监控
            with self._lock:
                state["status"] = "starting"
                state["error"] = ""
                self._states[key] = state
            target_url = url or str(state.get("url") or "")
            threading.Thread(
                target=self._monitor,
                args=(key, running, target_url),
                name=f"local-comfy-{key}",
                daemon=True,
            ).start()
            self._emit(f"重新检测本地 ComfyUI 就绪状态：{state.get('name') or key}（{key}）")
            deadline = time.monotonic() + self.start_wait
            while time.monotonic() < deadline:
                current = self.status(key)
                if current["status"] in {"running", "failed", "stopped"}:
                    break
                time.sleep(min(0.1, self.poll_interval))
            return self.status(key)

        # 先记录 starting，避免启动准备阶段的轮询把状态读成 stopped
        pending = _stopped_state()
        pending.update(
            node_id=key,
            name=name,
            url=url,
            status="starting",
            managed=True,
            started_at=utc_now(),
        )
        with self._lock:
            self._states[key] = pending
        if _probe(url):
            state = _stopped_state()
            state.update(
                node_id=key,
                name=name,
                url=url,
                status="running",
                managed=False,
                python="",
                error="",
            )
            with self._lock:
                self._states[key] = state
            self._emit(f"本地 ComfyUI 已在运行（{name} · {key}），无需重复启动")
            return dict(state)

        try:
            script, workdir = resolve_launch_target(launch_path)
            python_command, python_source = self._resolve_python(workdir)
        except ValueError:
            with self._lock:
                self._states.pop(key, None)
            raise
        log_path = self._log_path(key)
        self._rotate_log(log_path)
        offset = log_path.stat().st_size if log_path.exists() else 0
        port = url_port(url)
        host = url_host(url)
        listen = "127.0.0.1" if host in {"localhost", "::1", "0.0.0.0"} else host
        command = [*python_command, str(script), "--listen", listen, "--port", str(port)]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        flags = _no_window_flags()
        if os.name == "nt":
            flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        header = (
            f"\n===== 启动 {name}（{key}） {utc_now()} =====\n"
            f"命令: {subprocess.list2cmdline(command)}\n"
            f"工作目录: {workdir}\n"
            f"Python: {' '.join(python_command)}（{python_source}）\n"
        )
        state = _stopped_state()
        state.update(
            node_id=key,
            name=name,
            url=url,
            status="starting",
            managed=True,
            started_at=utc_now(),
            python=" ".join(python_command),
            launch_dir=str(workdir),
            log_path=str(log_path),
        )
        try:
            with log_path.open("a", encoding="utf-8", errors="replace") as log_file:
                log_file.write(header)
                log_file.flush()
                process = subprocess.Popen(
                    command,
                    cwd=str(workdir),
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    env=env,
                    creationflags=flags,
                )
        except OSError as exc:
            message = f"启动本地 ComfyUI 失败（{name} · {key}）：{exc}"
            self._record_failure(key, state, offset, message)
            raise ValueError(message) from exc

        state["pid"] = int(process.pid)
        self._guard.attach(process)
        with self._lock:
            self._states[key] = state
            self._procs[key] = process
        if self._shutting_down:
            try:
                process.terminate()
            except OSError:
                pass
            self._finalize(key, process, process.returncode, stopping=True)
            raise ValueError("应用正在退出，已取消启动本地 ComfyUI")
        self._emit(f"正在启动本地 ComfyUI：{name}（{key}）")
        threading.Thread(
            target=self._monitor,
            args=(key, process, url),
            name=f"local-comfy-{key}",
            daemon=True,
        ).start()

        budget = self.start_wait if wait is None else max(0.0, float(wait))
        deadline = time.monotonic() + budget
        while time.monotonic() < deadline:
            current = self.status(key)
            if current["status"] in {"running", "failed", "stopped"}:
                break
            time.sleep(min(0.1, self.poll_interval))
        current = self.status(key)
        if current["status"] == "failed":
            tail = self._tail(key, offset)
            message = current.get("error") or f"本地 ComfyUI 启动失败（{name} · {key}）"
            raise ValueError(f"{message}\n原始报错:\n{tail}" if tail else message)
        return current

    # ------------------------------------------------------------------ 关闭
    def stop(self, node_id: str) -> dict[str, Any]:
        key = str(node_id)
        with self._lock:
            state = self._states.get(key)
            process = self._procs.get(key)
        if not state:
            return _stopped_state()
        name = state.get("name") or key
        if not state.get("managed") or process is None:
            if _probe(state.get("url") or ""):
                raise ValueError("该 ComfyUI 不是由本应用启动的，无法从应用内关闭，请手动关闭后重试")
            with self._lock:
                state["status"] = "stopped"
                state["pid"] = 0
            return dict(state)
        if process.poll() is not None:
            self._finalize(key, process, process.returncode, stopping=True)
            return self.status(key)
        with self._lock:
            state["status"] = "stopping"
        self._emit(f"正在关闭本地 ComfyUI：{name}（{key}）")
        try:
            process.terminate()
        except OSError:
            pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        self._finalize(key, process, process.returncode, stopping=True)
        return self.status(key)

    def forget(self, node_id: str) -> None:
        """推理节点被删除后清除托管状态（不会终止进程）。"""
        key = str(node_id)
        with self._lock:
            self._states.pop(key, None)
            self._procs.pop(key, None)

    def shutdown(self, *, timeout: float = SHUTDOWN_TIMEOUT) -> None:
        """应用退出时关闭由本应用启动的本地 ComfyUI 进程。"""
        with self._lock:
            self._shutting_down = True
            items = [(key, process) for key, process in self._procs.items() if process.poll() is None]
            states = {key: dict(value) for key, value in self._states.items()}
        if not items:
            logger.info("应用退出：没有需要关闭的本地 ComfyUI 进程")
            self._guard.release()
            return
        for key, process in items:
            name = states.get(key, {}).get("name") or key
            logger.info("应用退出，正在关闭本地 ComfyUI：%s（%s）pid=%s", name, key, process.pid)
            self._emit(f"应用退出，正在关闭本地 ComfyUI：{name}（{key}）")
            try:
                process.terminate()
            except OSError:
                continue
        deadline = time.monotonic() + max(0.0, float(timeout))
        for key, process in items:
            remaining = max(0.1, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                    process.wait(timeout=3)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            self._finalize(key, process, process.returncode, stopping=True)
        self._guard.release()

    # ------------------------------------------------------------------ 内部
    def _monitor(self, key: str, process: subprocess.Popen[bytes], url: str) -> None:
        started = time.monotonic()
        while True:
            code = process.poll()
            if code is not None:
                if not self._shutting_down:
                    self._finalize(key, process, code)
                return
            state = self.status(key)
            status = state.get("status")
            if status == "starting":
                if _probe(url, 1.0):
                    with self._lock:
                        state = self._states.get(key) or {}
                        state["status"] = "running"
                        state["ready_at"] = utc_now()
                    self._emit(f"本地 ComfyUI 已就绪：{state.get('name') or key}（{key}）")
                elif time.monotonic() - started > self.ready_timeout:
                    with self._lock:
                        state = self._states.get(key) or {}
                        state["status"] = "failed"
                        state["error"] = (
                            f"等待就绪超时（{int(self.ready_timeout)} 秒），进程仍在运行，"
                            f"请查看日志：{state.get('log_path', '')}"
                        )
                    self._emit(
                        f"本地 ComfyUI 启动超时（{key}）：进程仍在运行，请查看日志 {state.get('log_path', '')}",
                        "warning",
                    )
                    return
            if status in {"stopping", "stopped", "failed"}:
                return
            time.sleep(self.poll_interval)

    def _finalize(
        self,
        key: str,
        process: subprocess.Popen[bytes],
        code: int | None,
        *,
        stopping: bool = False,
    ) -> None:
        with self._lock:
            state = self._states.get(key)
            if state is None:
                return
            was_starting = state.get("status") == "starting"
            state["pid"] = 0
            if stopping:
                state["status"] = "stopped"
                state["error"] = ""
            elif was_starting:
                state["status"] = "failed"
                state["error"] = (
                    f"ComfyUI 进程启动后退出（退出码 {code}），日志：{state.get('log_path', '')}"
                )
            else:
                state["status"] = "stopped"
                state["error"] = ""
            self._procs.pop(key, None)
            offset = 0
            log_path = state.get("log_path") or ""
        name = state.get("name") or key
        if stopping:
            self._emit(f"本地 ComfyUI 已关闭：{name}（{key}）")
            return
        tail = self._tail_file(log_path, offset)
        if was_starting:
            message = (
                f"本地 ComfyUI 启动失败：{name}（{key}），退出码 {code}\n"
                f"日志文件：{log_path}\n原始报错:\n{tail or '(日志为空)'}"
            )
            logger.error(message)
            self._emit(message, "error")
        else:
            self._emit(f"本地 ComfyUI 进程已退出：{name}（{key}），退出码 {code}", "warning")
            if tail:
                logger.info("本地 ComfyUI 退出输出（%s）:\n%s", key, tail)

    def _record_failure(
        self, key: str, state: dict[str, Any], offset: int, message: str
    ) -> None:
        state = dict(state)
        state["status"] = "failed"
        state["pid"] = 0
        state["error"] = message
        with self._lock:
            self._states[key] = state
            self._procs.pop(key, None)
        tail = self._tail(key, offset)
        logger.error("%s\n原始报错:\n%s", message, tail or "(无输出)")
        self._emit(f"{message}\n原始报错:\n{tail or '(无输出)'}", "error")

    def _resolve_python(self, launch_dir: Path) -> tuple[list[str], str]:
        for candidate in venv_python_candidates(launch_dir):
            if not candidate.is_file():
                continue
            if _command_works([str(candidate)]):
                return [str(candidate)], "私有环境"
            logger.warning("私有 Python 环境不可用，尝试下一个：%s", candidate)
        global_command = self._detect_global_python()
        if global_command:
            return global_command, "全局环境"
        raise ValueError(
            "没有找到可用的 Python 环境：节点目录下未发现私有环境（venv/.venv/env），"
            "也没有找到全局 Python。请安装 Python 或在节点目录创建虚拟环境"
        )

    def _detect_global_python(self) -> list[str]:
        candidates: list[list[str]] = []
        override = os.environ.get("H3_COMFY_PYTHON", "").strip()
        if override:
            candidates.append([override])
        if not getattr(sys, "frozen", False) and sys.executable:
            candidates.append([sys.executable])
        for name in ("python", "python3"):
            found = shutil.which(name)
            if found:
                candidates.append([found])
        launcher = shutil.which("py")
        if launcher:
            candidates.append([launcher, "-3"])
        for command in candidates:
            if _command_works(command):
                return command
        return []

    def _log_path(self, key: str) -> Path:
        safe = SAFE_ID.sub("_", key) or "node"
        return self.log_dir / f"{safe}.log"

    def _rotate_log(self, log_path: Path) -> None:
        try:
            if log_path.exists() and log_path.stat().st_size > LOG_MAX_BYTES:
                backup = log_path.with_suffix(log_path.suffix + ".1")
                if backup.exists():
                    backup.unlink()
                log_path.replace(backup)
        except OSError:
            logger.warning("无法轮转本地 ComfyUI 日志：%s", log_path)

    def _tail(self, key: str, offset: int = 0) -> str:
        state = self.status(key)
        return self._tail_file(state.get("log_path") or "", offset)

    def _tail_file(self, log_path: str, offset: int = 0) -> str:
        if not log_path:
            return ""
        path = Path(log_path)
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(max(0, int(offset)))
                text = handle.read()
        except OSError:
            return ""
        rows = [row.rstrip() for row in text.splitlines() if row.strip()]
        return "\n".join(rows[-LOG_TAIL_LINES:])

    def _emit(self, message: str, level: str = "info") -> None:
        if not self._event_sink:
            return
        try:
            self._event_sink(message, level=level)
        except Exception:  # pragma: no cover - 日志通道失败不应影响托管
            logger.exception("写入运行日志失败")
