from __future__ import annotations

import json
import logging
import queue
import shutil
import threading
import traceback
from collections import deque
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable


TERMINAL_STATES = {"completed", "failed", "cancelled"}
logger = logging.getLogger("uvicorn.error")


def generic_active_stage(status: str | None) -> str:
    if status == "running":
        return "有任务正在运行中"
    if status == "queued":
        return "有任务正在排队中"
    return "任务状态已更新"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class JobStore:
    def __init__(self, jobs_dir: Path):
        self.jobs_dir = jobs_dir
        self.data_dir = jobs_dir.parent.resolve()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._events: deque[dict[str, Any]] = deque(maxlen=1000)
        self._lock = threading.RLock()
        self._revision = 0
        self._restore()

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def _restore(self) -> None:
        for path in self.jobs_dir.glob("*.json"):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if self._incognito_expired(job):
                self._remove_job_files(job, path)
                continue
            job.setdefault("logs", [])
            restricted = bool(job.get("request", {}).get("incognito"))
            for event in job["logs"][-40:]:
                restored_event = deepcopy(event)
                restored_event["_restricted"] = restricted
                self._events.append(restored_event)
            if job.get("status") in {"queued", "running"}:
                job.update(
                    status="queued",
                    stage="服务已恢复，等待 ComfyUI FP8 执行",
                    progress=0,
                    cancel_requested=False,
                    updated_at=utc_now(),
                )
                self._append_event(job, "服务恢复，任务重新进入队列")
            self._jobs[job["id"]] = job
            self._persist(job)
        self._revision += 1

    @staticmethod
    def _incognito_expired(job: dict[str, Any]) -> bool:
        expires_at = job.get("expires_at")
        if not job.get("request", {}).get("incognito") or not expires_at:
            return False
        try:
            return datetime.fromisoformat(expires_at) <= datetime.now(UTC)
        except (TypeError, ValueError):
            return False

    def _persist(self, job: dict[str, Any]) -> None:
        path = self.jobs_dir / f"{job['id']}.json"
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def _append_event(
        self,
        job: dict[str, Any],
        message: str,
        level: str = "info",
    ) -> None:
        event = {
            "timestamp": utc_now(),
            "job_id": job["id"],
            "level": level,
            "status": job.get("status"),
            "progress": job.get("progress", 0),
            "message": message,
        }
        restricted = bool(job.get("request", {}).get("incognito"))
        logs = job.setdefault("logs", [])
        logs.append(event)
        if len(logs) > 200:
            del logs[:-200]
        stream_event = deepcopy(event)
        stream_event["_restricted"] = restricted
        self._events.append(stream_event)
        self._revision += 1
        log = logger.error if level == "error" else logger.info
        if restricted:
            log(
                "H3 status=%s message=%s",
                job.get("status"),
                generic_active_stage(job.get("status")),
            )
        else:
            log(
                "H3 job=%s status=%s progress=%s message=%s",
                job["id"],
                job.get("status"),
                job.get("progress", 0),
                message,
            )

    def create(self, job: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            job.setdefault("logs", [])
            self._jobs[job["id"]] = job
            self._append_event(job, "任务已创建并进入队列")
            self._persist(job)
            return deepcopy(job)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return deepcopy(job) if job else None

    def update(self, job_id: str, **changes: Any) -> dict[str, Any]:
        with self._lock:
            job = self._jobs[job_id]
            previous = {
                "status": job.get("status"),
                "stage": job.get("stage"),
                "progress": job.get("progress"),
            }
            event_message = changes.pop("event_message", None)
            event_level = changes.pop("event_level", "info")
            job.update(changes, updated_at=utc_now())
            changed = any(job.get(key) != value for key, value in previous.items())
            if event_message or changed:
                message = event_message or str(job.get("stage") or job.get("status") or "任务已更新")
                self._append_event(job, message, event_level)
            self._persist(job)
            return deepcopy(job)

    @staticmethod
    def _elapsed_seconds(job: dict[str, Any]) -> float | None:
        created_at = job.get("created_at")
        if not created_at:
            return None
        terminal_at = job.get("completed_at") or job.get("updated_at")
        end_at = terminal_at if job.get("status") in TERMINAL_STATES else utc_now()
        try:
            elapsed = datetime.fromisoformat(end_at) - datetime.fromisoformat(created_at)
        except (TypeError, ValueError):
            return None
        return round(max(0.0, elapsed.total_seconds()), 1)

    def _decorate_public_job(self, job: dict[str, Any]) -> dict[str, Any]:
        request = job.setdefault("request", {})
        request.setdefault("execution_mode", "native")
        job["elapsed_seconds"] = self._elapsed_seconds(job)
        return job

    def public(
        self,
        job_id: str,
        queue_position: int | None = None,
        include_logs: bool = True,
    ) -> dict[str, Any] | None:
        job = self.get(job_id)
        if not job:
            return None
        job.pop("input_paths", None)
        if not include_logs:
            job.pop("logs", None)
        self._decorate_public_job(job)
        for index, reference in enumerate(job.get("request", {}).get("references", [])):
            reference.setdefault(
                "url",
                f"/api/v1/generations/{job_id}/references/{index}",
            )
        if queue_position is not None and job["status"] == "queued":
            job["queue_position"] = queue_position
        return job

    def queue_public(
        self,
        job_id: str,
        queue_position: int | None = None,
    ) -> dict[str, Any] | None:
        job = self.get(job_id)
        if not job:
            return None
        if not job.get("request", {}).get("incognito"):
            return self.public(job_id, queue_position, include_logs=False)
        status = job.get("status")
        public_job: dict[str, Any] = {
            "status": status,
            "stage": generic_active_stage(status),
            "elapsed_seconds": self._elapsed_seconds(job),
        }
        if queue_position is not None and status == "queued":
            public_job["queue_position"] = queue_position
        return public_job

    def list(
        self,
        page: int,
        page_size: int,
        status: str | None = None,
        query: str | None = None,
        include_incognito: bool = False,
        scope: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        with self._lock:
            jobs = list(self._jobs.values())
            resolved_scope = scope or ("all" if include_incognito else "normal")
            if resolved_scope == "normal":
                jobs = [job for job in jobs if not job.get("request", {}).get("incognito")]
            elif resolved_scope == "incognito":
                jobs = [job for job in jobs if job.get("request", {}).get("incognito")]
            elif resolved_scope != "all":
                raise ValueError(f"unknown job scope: {resolved_scope}")
            if status:
                jobs = [job for job in jobs if job.get("status") == status]
            if query:
                needle = query.casefold()
                jobs = [
                    job
                    for job in jobs
                    if needle in job.get("id", "").casefold()
                    or needle in job.get("request", {}).get("prompt", "").casefold()
                    or needle in job.get("title", "").casefold()
                ]
            jobs.sort(key=lambda job: job.get("created_at", ""), reverse=True)
            total = len(jobs)
            start = (page - 1) * page_size
            items = []
            for job in jobs[start : start + page_size]:
                item = deepcopy(job)
                item.pop("input_paths", None)
                item.pop("logs", None)
                self._decorate_public_job(item)
                for index, reference in enumerate(item.get("request", {}).get("references", [])):
                    reference.setdefault(
                        "url",
                        f"/api/v1/generations/{item['id']}/references/{index}",
                    )
                items.append(item)
            return items, total

    def incognito_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                deepcopy(job)
                for job in self._jobs.values()
                if job.get("request", {}).get("incognito")
            ]

    def logs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            visible = []
            for stored_event in self._events:
                if stored_event.get("_restricted"):
                    continue
                event = deepcopy(stored_event)
                event.pop("_restricted", None)
                visible.append(event)

            active_restricted = [
                job
                for job in self._jobs.values()
                if job.get("request", {}).get("incognito")
                and job.get("status") in {"queued", "running"}
            ]
            if active_restricted:
                running = [job for job in active_restricted if job.get("status") == "running"]
                selected = max(
                    running or active_restricted,
                    key=lambda job: job.get("updated_at") or job.get("created_at") or "",
                )
                status = "running" if running else "queued"
                visible.append(
                    {
                        "timestamp": selected.get("updated_at")
                        or selected.get("created_at")
                        or utc_now(),
                        "level": "info",
                        "status": status,
                        "message": generic_active_stage(status),
                    }
                )
                visible.sort(key=lambda event: event.get("timestamp") or "")
            return deepcopy(visible[-limit:])

    def queued_ids(self) -> list[str]:
        with self._lock:
            queued = [job for job in self._jobs.values() if job.get("status") == "queued"]
            queued.sort(key=lambda job: job.get("created_at", ""))
            return [job["id"] for job in queued]

    def delete(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.pop(job_id, None)
            if not job:
                return False
            restricted = bool(job.get("request", {}).get("incognito"))
            self._remove_job_files(job, self.jobs_dir / f"{job_id}.json")
            self._revision += 1
            if not restricted:
                logger.info("H3 job=%s deleted", job_id)
            return True

    def _remove_job_files(self, job: dict[str, Any], job_path: Path) -> None:
        for raw_path in job.get("input_paths", []):
            self._delete_data_path(Path(raw_path))
        if job.get("input_paths"):
            upload_dir = Path(job["input_paths"][0]).parent
            self._delete_data_path(upload_dir, directory=True)
        self._delete_data_path(self.data_dir / "uploads" / job["id"], directory=True)
        if job.get("result_path"):
            result = Path(job["result_path"])
            self._delete_data_path(result)
            self._delete_data_path(result.with_suffix(".json"))
        self._delete_data_path(self.jobs_dir / f"{job['id']}.log")
        job_path.unlink(missing_ok=True)

    def _delete_data_path(self, path: Path, directory: bool = False) -> None:
        try:
            resolved = path.resolve()
            resolved.relative_to(self.data_dir)
        except (OSError, ValueError):
            logger.warning("Refused to delete path outside H3 data directory: %s", path)
            return
        if directory:
            shutil.rmtree(resolved, ignore_errors=True)
        else:
            resolved.unlink(missing_ok=True)


class JobManager:
    def __init__(self, store: JobStore, engine_factory: Callable[[], Any]):
        self.store = store
        self.engine_factory = engine_factory
        self.pending: queue.Queue[str | None] = queue.Queue()
        self._order: list[str] = []
        self._order_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._engine: Any = None
        self._running_job_id: str | None = None
        self._expiry_timers: dict[str, threading.Timer] = {}
        self._expiry_lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._worker, name="h3-worker", daemon=True)
        self._thread.start()
        for job in self.store.incognito_jobs():
            if job.get("expires_at"):
                self._schedule_incognito_expiry(job["id"], job["expires_at"])
            elif job.get("status") in TERMINAL_STATES:
                self._set_incognito_expiry(job["id"])
        for job_id in self.store.queued_ids():
            self.submit(job_id)

    def stop(self) -> None:
        with self._expiry_lock:
            timers = list(self._expiry_timers.values())
            self._expiry_timers.clear()
        for timer in timers:
            timer.cancel()
        self.pending.put(None)
        if self._thread:
            self._thread.join(timeout=10)

    def submit(self, job_id: str) -> None:
        with self._order_lock:
            if job_id not in self._order:
                self._order.append(job_id)
        self.pending.put(job_id)

    @property
    def queue_depth(self) -> int:
        with self._order_lock:
            return len(self._order)

    def queue_position(self, job_id: str) -> int | None:
        with self._order_lock:
            try:
                return self._order.index(job_id) + 1
            except ValueError:
                return None

    def queue_snapshot(self) -> list[dict[str, Any]]:
        with self._order_lock:
            ids = list(self._order)
            running_id = self._running_job_id
        snapshot = []
        if running_id:
            running = self.store.queue_public(running_id)
            if running:
                running["queue_position"] = 0
                snapshot.append(running)
        for position, job_id in enumerate(ids, start=1):
            job = self.store.queue_public(job_id, position)
            if job:
                snapshot.append(job)
        return snapshot

    def cancel(self, job_id: str) -> bool:
        job = self.store.get(job_id)
        if not job or job["status"] in TERMINAL_STATES:
            return False
        self.store.update(job_id, cancel_requested=True, stage="正在取消")
        if job["status"] == "queued":
            self.store.update(job_id, status="cancelled", stage="已取消", progress=0)
            self.remove(job_id)
            self._set_incognito_expiry(job_id)
        return True

    def remove(self, job_id: str) -> None:
        with self._order_lock:
            if job_id in self._order:
                self._order.remove(job_id)

    def _is_cancelled(self, job_id: str) -> bool:
        job = self.store.get(job_id)
        return bool(job and job.get("cancel_requested"))

    def _worker(self) -> None:
        while True:
            job_id = self.pending.get()
            if job_id is None:
                return
            job = self.store.get(job_id)
            if not job or job["status"] == "cancelled":
                continue
            self.remove(job_id)
            with self._order_lock:
                self._running_job_id = job_id
            self.store.update(
                job_id,
                status="running",
                stage="准备推理环境",
                progress=1,
                started_at=utc_now(),
            )
            try:
                if self._engine is None:
                    self._engine = self.engine_factory()

                def progress(percent: int, stage: str) -> None:
                    self.store.update(job_id, progress=max(1, min(99, percent)), stage=stage)

                result = self._engine.generate(job, progress, lambda: self._is_cancelled(job_id))
                if self._is_cancelled(job_id):
                    self.store.update(job_id, status="cancelled", stage="已取消", progress=0)
                    self._set_incognito_expiry(job_id)
                else:
                    self.store.update(
                        job_id,
                        status="completed",
                        stage="生成完成",
                        progress=100,
                        result_path=str(result),
                        result_url=f"/api/v1/generations/{job_id}/result",
                        completed_at=utc_now(),
                    )
                    self._set_incognito_expiry(job_id)
            except InterruptedError:
                self.store.update(job_id, status="cancelled", stage="已取消", progress=0)
                self._set_incognito_expiry(job_id)
            except Exception as exc:
                error_log = self.store.jobs_dir / f"{job_id}.log"
                error_log.write_text(traceback.format_exc(), encoding="utf-8")
                self.store.update(
                    job_id,
                    status="failed",
                    stage="生成失败",
                    error=str(exc)[:800],
                    progress=0,
                    event_level="error",
                )
                self._set_incognito_expiry(job_id)
            finally:
                with self._order_lock:
                    self._running_job_id = None

    def _schedule_incognito_expiry(self, job_id: str, expires_at: str) -> None:
        try:
            delay = max(
                0.0,
                (datetime.fromisoformat(expires_at) - datetime.now(UTC)).total_seconds(),
            )
        except (TypeError, ValueError):
            return
        timer: threading.Timer

        def expire() -> None:
            self._expire_incognito(job_id, timer)

        timer = threading.Timer(delay, expire)
        timer.daemon = True
        with self._expiry_lock:
            previous = self._expiry_timers.get(job_id)
            if previous:
                previous.cancel()
            self._expiry_timers[job_id] = timer
        timer.start()

    def _set_incognito_expiry(self, job_id: str) -> None:
        job = self.store.get(job_id)
        if not job or not job.get("request", {}).get("incognito"):
            return
        expires_at = (datetime.now(UTC) + timedelta(minutes=30)).isoformat()
        self.store.update(job_id, expires_at=expires_at)
        self._schedule_incognito_expiry(job_id, expires_at)

    def _expire_incognito(self, job_id: str, source_timer: threading.Timer) -> None:
        try:
            job = self.store.get(job_id)
            if not job or not job.get("request", {}).get("incognito"):
                return
            expires_at = job.get("expires_at")
            if expires_at and JobStore._incognito_expired(job):
                self.remove(job_id)
                self.store.delete(job_id)
            elif expires_at:
                self._schedule_incognito_expiry(job_id, expires_at)
        finally:
            with self._expiry_lock:
                if self._expiry_timers.get(job_id) is source_timer:
                    self._expiry_timers.pop(job_id, None)
