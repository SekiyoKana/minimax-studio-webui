from __future__ import annotations

import json
import inspect
import logging
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
        self._changes: deque[dict[str, Any]] = deque(maxlen=2000)
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
                    stage="服务已恢复，等待推理节点执行",
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
        self._record_change(job, "upsert")
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

    def _record_change(self, job: dict[str, Any], action: str) -> None:
        self._changes.append(
            {
                "revision": self._revision,
                "job_id": job["id"],
                "action": action,
                "restricted": bool(job.get("request", {}).get("incognito")),
            }
        )

    def changes_since(self, revision: int) -> dict[str, Any]:
        with self._lock:
            current_revision = self._revision
            if revision > current_revision:
                return {
                    "revision": current_revision,
                    "jobs": [],
                    "deleted_job_ids": [],
                    "reset_required": True,
                }

            oldest_revision = self._changes[0]["revision"] if self._changes else current_revision
            reset_required = bool(self._changes and revision < oldest_revision - 1)
            selected: dict[str, dict[str, Any]] = {}
            for change in self._changes:
                if change["revision"] > revision:
                    selected[change["job_id"]] = change

            jobs = []
            deleted_job_ids = []
            for change in selected.values():
                if change["restricted"]:
                    continue
                job_id = change["job_id"]
                if change["action"] == "delete":
                    deleted_job_ids.append(job_id)
                    continue
                job = self.public(job_id, include_logs=False)
                if job:
                    jobs.append(job)

            return {
                "revision": current_revision,
                "jobs": jobs,
                "deleted_job_ids": deleted_job_ids,
                "reset_required": reset_required,
            }

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
            else:
                self._revision += 1
                self._record_change(job, "upsert")
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

    def list_with_revision(
        self,
        page: int,
        page_size: int,
        status: str | None = None,
        query: str | None = None,
        include_incognito: bool = False,
        scope: str | None = None,
    ) -> tuple[list[dict[str, Any]], int, int]:
        with self._lock:
            items, total = self.list(
                page,
                page_size,
                status,
                query,
                include_incognito,
                scope,
            )
            return items, total, self._revision

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
            self._record_change(job, "delete")
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
    def __init__(
        self,
        store: JobStore,
        engine_factory: Callable[..., Any],
        nodes: list[Any] | tuple[Any, ...] | None = None,
        health_probe: Callable[[Any], Any] | None = None,
        health_interval: float = 60,
    ):
        self.store = store
        self.engine_factory = engine_factory
        self.health_probe = health_probe
        self.health_interval = max(5.0, health_interval)
        configured_nodes = list(
            nodes
            or (
                {
                    "id": "default",
                    "name": "ComfyUI",
                    "url": "",
                    "provider": "comfyui",
                    "max_concurrency": 1,
                },
            )
        )
        self._nodes: dict[str, dict[str, Any]] = {}
        for item in configured_nodes:
            node_id = str(getattr(item, "id", None) or item.get("id"))
            provider = str(
                getattr(item, "provider", None) or item.get("provider") or "comfyui"
            )
            capacity = int(
                getattr(item, "max_concurrency", None)
                or item.get("max_concurrency")
                or 1
            )
            workflow_id = str(
                item.get("workflow_id", "")
                if isinstance(item, dict)
                else getattr(item, "workflow_id", "")
            )
            self._nodes[node_id] = {
                "id": node_id,
                "name": str(getattr(item, "name", None) or item.get("name") or node_id),
                "url": str(getattr(item, "url", None) or item.get("url") or ""),
                "provider": provider,
                "workflow_id": workflow_id,
                "workflow_variant": None,
                "workflow_execution_mode": None,
                "workflow_error": None,
                "account_balance_coins": None,
                "account_balance_money": None,
                "account_currency": "",
                "account_current_tasks": None,
                "last_call_consumed_coins": None,
                "last_call_consumed_money": None,
                "last_call_cost_at": None,
                "last_call_job_id": None,
                "capacity": 1 if provider == "comfyui" else max(1, capacity),
                "config": item,
                "healthy": health_probe is None,
                "last_checked": None,
                "error": None,
                "retired": False,
            }
        self._order: list[str] = []
        self._condition = threading.Condition(threading.RLock())
        self._threads: dict[tuple[str, int], threading.Thread] = {}
        self._health_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._health_wakeup = threading.Event()
        self._started = False
        self._engines: dict[tuple[str, int], Any] = {}
        self._running_job_ids: dict[tuple[str, int], str] = {}
        self._running_job_id: str | None = None
        self._revision = 0
        self._factory_accepts_node = bool(inspect.signature(engine_factory).parameters)
        self._expiry_timers: dict[str, threading.Timer] = {}
        self._expiry_lock = threading.Lock()

    @property
    def revision(self) -> int:
        with self._condition:
            return self._revision

    @property
    def node_ids(self) -> set[str]:
        with self._condition:
            return {
                node_id
                for node_id, node in self._nodes.items()
                if not node.get("retired")
            }

    def accepts_node(self, node_id: str) -> bool:
        return node_id == "auto" or node_id in self.node_ids

    def workflow_profile(self, node_id: str) -> dict[str, str] | None:
        with self._condition:
            if node_id == "auto":
                candidates = [
                    node
                    for node in self._nodes.values()
                    if not node.get("retired") and node["healthy"]
                ]
                if not candidates or any(
                    node["provider"] != "runninghub" for node in candidates
                ):
                    return None
                profiles = {
                    (
                        node.get("workflow_variant"),
                        node.get("workflow_execution_mode"),
                        node.get("workflow_id"),
                    )
                    for node in candidates
                }
                if len(profiles) != 1:
                    return None
                node = candidates[0]
            else:
                node = self._nodes.get(node_id)
                if not node or node.get("retired") or node["provider"] != "runninghub":
                    return None
            variant = node.get("workflow_variant")
            execution_mode = node.get("workflow_execution_mode")
            if not variant or not execution_mode:
                return None
            return {
                "model_variant": variant,
                "execution_mode": execution_mode,
            }

    def node_in_use(self, node_id: str) -> bool:
        with self._condition:
            if any(slot_node_id == node_id for slot_node_id, _ in self._running_job_ids):
                return True
            for job_id in self._order:
                job = self.store.get(job_id)
                if job and job.get("request", {}).get("comfy_node") == node_id:
                    return True
            return False

    def nodes_public(self) -> list[dict[str, Any]]:
        with self._condition:
            queued_jobs = [self.store.get(job_id) for job_id in self._order]
            result = []
            for node_id, node in self._nodes.items():
                if node.get("retired"):
                    continue
                running_job_ids = [
                    job_id
                    for (running_node_id, _), job_id in sorted(self._running_job_ids.items())
                    if running_node_id == node_id
                ]
                public_running_job_ids = []
                for running_job_id in running_job_ids:
                    running_job = self.store.get(running_job_id)
                    if not (
                        running_job
                        and running_job.get("request", {}).get("incognito")
                    ):
                        public_running_job_ids.append(running_job_id)
                manual_depth = sum(
                    1
                    for job in queued_jobs
                    if job and job.get("request", {}).get("comfy_node") == node_id
                )
                result.append(
                    {
                        "id": node_id,
                        "name": node["name"],
                        "provider": node["provider"],
                        "workflow_id": node["workflow_id"],
                        "workflow_name": node["name"]
                        if node["provider"] == "runninghub"
                        else None,
                        "workflow_variant": node.get("workflow_variant"),
                        "workflow_execution_mode": node.get(
                            "workflow_execution_mode"
                        ),
                        "workflow_error": node.get("workflow_error"),
                        "account_balance_coins": node.get("account_balance_coins"),
                        "account_balance_money": node.get("account_balance_money"),
                        "account_currency": node.get("account_currency") or "",
                        "account_current_tasks": node.get("account_current_tasks"),
                        "last_call_consumed_coins": node.get(
                            "last_call_consumed_coins"
                        ),
                        "last_call_consumed_money": node.get(
                            "last_call_consumed_money"
                        ),
                        "last_call_cost_at": node.get("last_call_cost_at"),
                        "last_call_job_id": node.get("last_call_job_id"),
                        "healthy": node["healthy"],
                        "last_checked": node["last_checked"],
                        "error": node["error"],
                        "busy": bool(running_job_ids),
                        "running_job_id": public_running_job_ids[0]
                        if public_running_job_ids
                        else None,
                        "running_job_ids": public_running_job_ids,
                        "running_count": len(running_job_ids),
                        "capacity": node["capacity"],
                        "queue_depth": manual_depth,
                    }
                )
            return result

    @property
    def parallel_capacity(self) -> int:
        with self._condition:
            return sum(
                node["capacity"]
                for node in self._nodes.values()
                if not node.get("retired") and node["healthy"]
            )

    def refresh_node_health(self) -> None:
        with self._condition:
            active_nodes = [
                (node_id, node)
                for node_id, node in self._nodes.items()
                if not node.get("retired")
            ]
        for node_id, node in active_nodes:
            healthy = True
            error = None
            profile: dict[str, Any] = {}
            if self.health_probe:
                try:
                    probe_result = self.health_probe(node["config"])
                    if isinstance(probe_result, dict):
                        profile = probe_result
                except Exception as exc:
                    healthy = node["provider"] == "runninghub"
                    error = str(exc)[:240]
            with self._condition:
                node["healthy"] = healthy
                node["error"] = error
                node["last_checked"] = utc_now()
                if "workflow_error" in profile:
                    node["workflow_error"] = profile["workflow_error"]
                for field in (
                    "workflow_variant",
                    "workflow_execution_mode",
                    "account_balance_coins",
                    "account_balance_money",
                    "account_currency",
                    "account_current_tasks",
                ):
                    if field in profile:
                        node[field] = profile[field]
                self._revision += 1
                self._condition.notify_all()

    def _health_worker(self) -> None:
        while not self._stop_event.is_set():
            self._health_wakeup.wait(self.health_interval)
            self._health_wakeup.clear()
            if self._stop_event.is_set():
                return
            self.refresh_node_health()

    def reconfigure(self, nodes: list[Any] | tuple[Any, ...], health_interval: float) -> None:
        configured = {
            str(getattr(item, "id")): item
            for item in nodes
        }
        if not configured:
            raise ValueError("至少需要一个启用的推理节点")
        threads_to_start: list[tuple[str, int]] = []
        with self._condition:
            for node_id, node in self._nodes.items():
                if node_id not in configured and not node.get("retired") and self.node_in_use(node_id):
                    raise RuntimeError(f"节点正在执行任务或存在定向排队任务：{node['name']}")
            for node_id, item in configured.items():
                current = self._nodes.get(node_id)
                if current and current["config"] != item and self.node_in_use(node_id):
                    raise RuntimeError(f"节点正在执行任务或存在定向排队任务：{current['name']}")
            for node_id, node in self._nodes.items():
                if node_id not in configured:
                    node["retired"] = True
                    for slot_key in [key for key in self._engines if key[0] == node_id]:
                        self._engines.pop(slot_key, None)
            for node_id, item in configured.items():
                name = str(getattr(item, "name"))
                url = str(getattr(item, "url"))
                provider = str(getattr(item, "provider", "comfyui"))
                workflow_id = str(getattr(item, "workflow_id", ""))
                capacity = (
                    1
                    if provider == "comfyui"
                    else max(1, int(getattr(item, "max_concurrency", 1)))
                )
                current = self._nodes.get(node_id)
                if current:
                    config_changed = current["config"] != item
                    current.update(
                        name=name,
                        url=url,
                        provider=provider,
                        workflow_id=workflow_id,
                        capacity=capacity,
                        config=item,
                        retired=False,
                    )
                    if config_changed:
                        current.update(
                            healthy=False,
                            error=None,
                            last_checked=None,
                            workflow_variant=None,
                            workflow_execution_mode=None,
                            workflow_error=None,
                            account_balance_coins=None,
                            account_balance_money=None,
                            account_currency="",
                            account_current_tasks=None,
                            last_call_consumed_coins=None,
                            last_call_consumed_money=None,
                            last_call_cost_at=None,
                            last_call_job_id=None,
                        )
                        for slot_key in [key for key in self._engines if key[0] == node_id]:
                            self._engines.pop(slot_key, None)
                else:
                    self._nodes[node_id] = {
                        "id": node_id,
                        "name": name,
                        "url": url,
                        "provider": provider,
                        "workflow_id": workflow_id,
                        "workflow_variant": None,
                        "workflow_execution_mode": None,
                        "workflow_error": None,
                        "account_balance_coins": None,
                        "account_balance_money": None,
                        "account_currency": "",
                        "account_current_tasks": None,
                        "last_call_consumed_coins": None,
                        "last_call_consumed_money": None,
                        "last_call_cost_at": None,
                        "last_call_job_id": None,
                        "capacity": capacity,
                        "config": item,
                        "healthy": self.health_probe is None,
                        "last_checked": None,
                        "error": None,
                        "retired": False,
                    }
                for slot_index in range(capacity):
                    slot_key = (node_id, slot_index)
                    thread = self._threads.get(slot_key)
                    if self._started and (not thread or not thread.is_alive()):
                        threads_to_start.append(slot_key)
            self.health_interval = max(5.0, min(3600.0, float(health_interval)))
            self._revision += 1
            self._condition.notify_all()
        for node_id, slot_index in threads_to_start:
            self._start_node_thread(node_id, slot_index)
        self._health_wakeup.set()

    def _start_node_thread(self, node_id: str, slot_index: int) -> None:
        slot_key = (node_id, slot_index)
        thread = threading.Thread(
            target=self._worker,
            args=(node_id, slot_index),
            name=f"h3-worker-{node_id}-{slot_index + 1}",
            daemon=True,
        )
        self._threads[slot_key] = thread
        thread.start()

    def start(self) -> None:
        if any(thread.is_alive() for thread in self._threads.values()):
            return
        self._stop_event.clear()
        self._health_wakeup.clear()
        self._started = True
        self.refresh_node_health()
        for node_id in self.node_ids:
            capacity = self._nodes[node_id]["capacity"]
            for slot_index in range(capacity):
                self._start_node_thread(node_id, slot_index)
        self._health_thread = threading.Thread(
            target=self._health_worker,
            name="h3-node-health",
            daemon=True,
        )
        self._health_thread.start()
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
        self._stop_event.set()
        self._health_wakeup.set()
        self._started = False
        with self._condition:
            self._condition.notify_all()
        for thread in self._threads.values():
            thread.join(timeout=10)
        if self._health_thread:
            self._health_thread.join(timeout=10)

    def submit(self, job_id: str) -> None:
        with self._condition:
            if job_id not in self._order:
                self._order.append(job_id)
                self._revision += 1
            self._condition.notify_all()

    @property
    def queue_depth(self) -> int:
        with self._condition:
            return len(self._order)

    def queue_position(self, job_id: str) -> int | None:
        with self._condition:
            try:
                return self._order.index(job_id) + 1
            except ValueError:
                return None

    def queue_snapshot(self) -> list[dict[str, Any]]:
        with self._condition:
            ids = list(self._order)
            running_ids = list(self._running_job_ids.values())
            if self._running_job_id and self._running_job_id not in running_ids:
                running_ids.append(self._running_job_id)
        snapshot = []
        for running_id in running_ids:
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
        with self._condition:
            if job_id in self._order:
                self._order.remove(job_id)
                self._revision += 1
            self._condition.notify_all()

    def _is_cancelled(self, job_id: str) -> bool:
        job = self.store.get(job_id)
        return bool(job and job.get("cancel_requested"))

    def _claim_job(
        self, node_id: str, slot_index: int
    ) -> tuple[str, dict[str, Any]] | None:
        slot_key = (node_id, slot_index)
        with self._condition:
            while not self._stop_event.is_set():
                node = self._nodes.get(node_id)
                if (
                    not node
                    or node.get("retired")
                    or slot_index >= node["capacity"]
                ):
                    return None
                if node["healthy"]:
                    for job_id in list(self._order):
                        job = self.store.get(job_id)
                        if not job or job.get("status") != "queued":
                            self._order.remove(job_id)
                            continue
                        target = job.get("request", {}).get("comfy_node") or "auto"
                        if target not in self._nodes:
                            target = "auto"
                        if target not in {"auto", node_id}:
                            continue
                        if target == "auto" and node["provider"] == "runninghub":
                            request = job.get("request", {})
                            if (
                                request.get("model_variant")
                                != node.get("workflow_variant")
                                or request.get("execution_mode")
                                != node.get("workflow_execution_mode")
                            ):
                                continue
                        self._order.remove(job_id)
                        self._running_job_ids[slot_key] = job_id
                        self._revision += 1
                        return job_id, job
                self._condition.wait(timeout=1)
        return None

    def _worker(self, node_id: str, slot_index: int) -> None:
        slot_key = (node_id, slot_index)
        while not self._stop_event.is_set():
            claimed = self._claim_job(node_id, slot_index)
            if not claimed:
                return
            node = self._nodes[node_id]
            job_id, job = claimed
            assigned_node = {
                "id": node_id,
                "name": node["name"],
                "provider": node["provider"],
                "workflow_id": node["workflow_id"],
                "workflow_name": node["name"]
                if node["provider"] == "runninghub"
                else None,
            }
            self.store.update(
                job_id,
                status="running",
                stage=f"准备 {node['name']} 推理环境",
                progress=1,
                started_at=utc_now(),
                assigned_node=assigned_node,
                event_message=f"任务已分配至 {node['name']}",
            )
            engine = None
            try:
                if slot_key not in self._engines:
                    self._engines[slot_key] = (
                        self.engine_factory(node["config"])
                        if self._factory_accepts_node
                        else self.engine_factory()
                    )
                engine = self._engines[slot_key]

                def progress(percent: int, stage: str) -> None:
                    self.store.update(job_id, progress=max(1, min(99, percent)), stage=stage)

                result = engine.generate(job, progress, lambda: self._is_cancelled(job_id))
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
                billing = getattr(engine, "last_billing", None)
                if isinstance(billing, dict):
                    self.store.update(job_id, runninghub_billing=billing)
                    with self._condition:
                        node["account_balance_coins"] = billing.get(
                            "account_balance_coins"
                        )
                        node["account_balance_money"] = billing.get(
                            "account_balance_money"
                        )
                        node["account_currency"] = billing.get("account_currency") or ""
                        node["account_current_tasks"] = billing.get(
                            "account_current_tasks"
                        )
                        node["last_call_consumed_coins"] = billing.get(
                            "consumed_coins"
                        )
                        node["last_call_consumed_money"] = billing.get(
                            "consumed_money"
                        )
                        node["last_call_cost_at"] = billing.get("measured_at")
                        node["last_call_job_id"] = job_id
                with self._condition:
                    self._running_job_ids.pop(slot_key, None)
                    self._revision += 1
                    self._condition.notify_all()

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
