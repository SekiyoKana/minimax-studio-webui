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

from cryptography.exceptions import InvalidTag


TERMINAL_STATES = {"completed", "failed", "cancelled"}
RUNNINGHUB_TARGET_PREFIX = "rh:"
MAX_FRESH_REMOTE_RETRIES = 3
logger = logging.getLogger("uvicorn.error")


def generic_active_stage(status: str | None) -> str:
    if status == "running":
        return "有任务正在运行中"
    if status == "queued":
        return "有任务正在排队中"
    return "任务状态已更新"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def runninghub_target(resource_id: str) -> str:
    return f"{RUNNINGHUB_TARGET_PREFIX}{resource_id}"


def runninghub_target_resource_id(target: str) -> str:
    if not target.startswith(RUNNINGHUB_TARGET_PREFIX):
        return ""
    return target.removeprefix(RUNNINGHUB_TARGET_PREFIX).strip()


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
                checkpoint = job.get("remote_checkpoint")
                if isinstance(checkpoint, dict) and checkpoint.get("remote_id"):
                    job.update(
                        status="queued",
                        stage="服务已恢复，正在重新连接远端任务",
                        progress=max(1, min(99, int(job.get("progress") or 1))),
                        cancel_requested=False,
                        updated_at=utc_now(),
                    )
                    self._append_event(job, "服务恢复，正在重新连接原远端任务")
                else:
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
        job.pop("remote_checkpoint", None)
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
            jobs = [job for job in jobs if not job.get("remote_record_hidden")]
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
                item.pop("remote_checkpoint", None)
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
                if stored_event.get("remote_record_hidden"):
                    continue
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

    def jobs_for_peer(self, peer_device_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [
                deepcopy(job)
                for job in self._jobs.values()
                if job.get("proxy_peer_id") == peer_device_id
                or job.get("request", {}).get("proxy_source_device_id") == peer_device_id
            ]

    def local_asset_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                deepcopy(job)
                for job in self._jobs.values()
                if job.get("status") == "completed"
                and (job.get("result_path") or job.get("asset_deleted"))
                and not job.get("request", {}).get("incognito")
            ]

    def protect_peer_jobs(
        self,
        peer_device_id: str,
        *,
        delete: bool,
        encrypt_bytes: Callable[[bytes], tuple[bytes, bytes]] | None = None,
    ) -> list[dict[str, Any]]:
        """Remove peer-owned jobs from the live store and return encrypted snapshots."""
        with self._lock:
            jobs = [
                deepcopy(job)
                for job in self._jobs.values()
                if job.get("proxy_peer_id") == peer_device_id
                or job.get("request", {}).get("proxy_source_device_id") == peer_device_id
            ]
            snapshots: list[dict[str, Any]] = []
            for job in jobs:
                job_id = str(job["id"])
                current = self._jobs.pop(job_id, None)
                if not current:
                    continue
                self._remove_job_record_file(job_id)
                if delete:
                    self._remove_job_files(job, self.jobs_dir / f"{job_id}.json")
                else:
                    if encrypt_bytes is None:
                        raise ValueError("加密快照缺少加密函数")
                    snapshot = deepcopy(job)
                    snapshot["_protected_files"] = self._encrypt_job_files(
                        job, encrypt_bytes
                    )
                    snapshot["remote_record_hidden"] = True
                    snapshots.append(snapshot)
                self._revision += 1
                self._record_change(job, "delete")
            return snapshots

    def restore_protected_job(
        self,
        snapshot: dict[str, Any],
        decrypt_bytes: Callable[[bytes, bytes], bytes],
    ) -> dict[str, Any]:
        """Decrypt a peer snapshot and put it back into the live job store."""
        restored = deepcopy(snapshot)
        for item in restored.pop("_protected_files", []) or []:
            encrypted_path = Path(str(item.get("encrypted_path") or ""))
            original_path = Path(str(item.get("original_path") or ""))
            try:
                encrypted_path.resolve().relative_to(self.data_dir)
                original_path.resolve().relative_to(self.data_dir)
                packed = encrypted_path.read_bytes()
                if not packed.startswith(b"H3E1") or len(packed) < 16:
                    raise ValueError("受保护文件格式无效")
                nonce = packed[4:16]
                plaintext = decrypt_bytes(packed[16:], nonce)
                original_path.parent.mkdir(parents=True, exist_ok=True)
                temp = original_path.with_suffix(original_path.suffix + ".restore.tmp")
                temp.write_bytes(plaintext)
                temp.replace(original_path)
                encrypted_path.unlink(missing_ok=True)
            except (InvalidTag, OSError, ValueError):
                logger.warning("无法恢复互联任务文件: %s", encrypted_path)
        restored.pop("remote_record_hidden", None)
        with self._lock:
            self._jobs[restored["id"]] = restored
            self._persist(restored)
            self._revision += 1
            self._record_change(restored, "upsert")
            return deepcopy(restored)

    def active_proxy_job_ids(self) -> list[str]:
        with self._lock:
            return [
                job["id"]
                for job in self._jobs.values()
                if job.get("status") not in TERMINAL_STATES
                and job.get("request", {}).get("remote_proxy")
            ]

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

    def _remove_job_record_file(self, job_id: str) -> None:
        (self.jobs_dir / f"{job_id}.json").unlink(missing_ok=True)

    def _encrypt_job_files(
        self,
        job: dict[str, Any],
        encrypt_bytes: Callable[[bytes], tuple[bytes, bytes]],
    ) -> list[dict[str, str]]:
        candidates: list[tuple[Path, str]] = []
        for raw_path in job.get("input_paths", []):
            candidates.append((Path(str(raw_path)), "input"))
        if job.get("result_path"):
            result_path = Path(str(job["result_path"]))
            candidates.extend(
                (
                    (result_path, "result"),
                    (result_path.with_suffix(".json"), "sidecar"),
                )
            )
        entries: list[dict[str, str]] = []
        seen: set[Path] = set()
        for path, kind in candidates:
            try:
                resolved = path.resolve()
                resolved.relative_to(self.data_dir)
            except (OSError, ValueError):
                logger.warning("Refused to protect path outside H3 data directory: %s", path)
                continue
            if resolved in seen or not resolved.is_file():
                continue
            seen.add(resolved)
            encrypted_path = resolved.with_name(resolved.name + ".h3enc")
            payload, nonce = encrypt_bytes(resolved.read_bytes())
            temp = encrypted_path.with_suffix(encrypted_path.suffix + ".tmp")
            temp.write_bytes(b"H3E1" + nonce + payload)
            temp.replace(encrypted_path)
            resolved.unlink(missing_ok=True)
            entries.append(
                {
                    "original_path": str(resolved),
                    "encrypted_path": str(encrypted_path),
                    "kind": kind,
                }
            )
        return entries

    def replace(self, job: dict[str, Any]) -> dict[str, Any]:
        """Replace a persisted job after remote-record protection or restoration."""
        with self._lock:
            self._jobs[job["id"]] = deepcopy(job)
            self._persist(self._jobs[job["id"]])
            self._revision += 1
            self._record_change(self._jobs[job["id"]], "upsert")
            return deepcopy(self._jobs[job["id"]])

    def delete_artifacts(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.get("request", {}).get("incognito"):
                return False
            raw_result_path = job.get("result_path")
            result_path = Path(raw_result_path) if raw_result_path else None
            if result_path:
                self._delete_data_path(result_path)
                self._delete_data_path(result_path.with_suffix(".json"))
            job["result_path"] = None
            job["result_url"] = None
            job["asset_deleted"] = True
            job["asset_deleted_at"] = utc_now()
            self._append_event(job, "生成产物已删除")
            self._persist(job)
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
        node_runtime_update: Callable[[str, dict[str, Any]], None] | None = None,
    ):
        self.store = store
        self.engine_factory = engine_factory
        self.health_probe = health_probe
        self.health_interval = max(5.0, health_interval)
        self.node_runtime_update = node_runtime_update
        configured_nodes = list(
            nodes
            if nodes is not None
            else (
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
            workflow_url = str(
                item.get("workflow_url", "")
                if isinstance(item, dict)
                else getattr(item, "workflow_url", "")
            )
            runninghub_resource_type = str(
                item.get("runninghub_resource_type", "workflow")
                if isinstance(item, dict)
                else getattr(item, "runninghub_resource_type", "workflow")
            )
            workflow_name = str(
                item.get("workflow_name", "")
                if isinstance(item, dict)
                else getattr(item, "workflow_name", "")
            )
            runninghub_schema = (
                item.get("runninghub_schema")
                if isinstance(item, dict)
                else getattr(item, "runninghub_schema", None)
            )
            persisted = lambda key, default=None: (
                item.get(key, default)
                if isinstance(item, dict)
                else getattr(item, key, default)
            )
            self._nodes[node_id] = {
                "id": node_id,
                "name": str(getattr(item, "name", None) or item.get("name") or node_id),
                "url": str(getattr(item, "url", None) or item.get("url") or ""),
                "provider": provider,
                "workflow_id": workflow_id,
                "workflow_url": workflow_url,
                "runninghub_resource_type": runninghub_resource_type,
                "workflow_name": workflow_name,
                "runninghub_schema": runninghub_schema,
                "workflow_error": None,
                "account_balance_coins": persisted("account_balance_coins"),
                "account_balance_money": persisted("account_balance_money"),
                "account_currency": persisted("account_currency", ""),
                "account_current_tasks": persisted("account_current_tasks"),
                "account_api_type": persisted("account_api_type", ""),
                "account_error": persisted("account_error", ""),
                "last_call_consumed_coins": persisted("last_call_consumed_coins"),
                "last_call_consumed_money": persisted("last_call_consumed_money"),
                "last_call_cost_at": persisted("last_call_cost_at", ""),
                "last_call_job_id": persisted("last_call_job_id", ""),
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
        if node_id == "auto" or node_id in self.node_ids:
            return True
        resource_id = runninghub_target_resource_id(node_id)
        if not resource_id:
            return False
        with self._condition:
            return any(
                not node.get("retired")
                and node["provider"] == "runninghub"
                and node.get("workflow_id") == resource_id
                for node in self._nodes.values()
            )

    def node_provider(self, node_id: str) -> str | None:
        if node_id == "auto":
            return None
        resource_id = runninghub_target_resource_id(node_id)
        if resource_id:
            return "runninghub" if self.accepts_node(node_id) else None
        with self._condition:
            node = self._nodes.get(node_id)
            if not node or node.get("retired"):
                return None
            return str(node.get("provider") or "comfyui")

    def workflow_profile(self, node_id: str) -> dict[str, Any] | None:
        with self._condition:
            resource_id = runninghub_target_resource_id(node_id)
            if resource_id:
                candidates = [
                    node
                    for node in self._nodes.values()
                    if not node.get("retired")
                    and node["provider"] == "runninghub"
                    and node.get("workflow_id") == resource_id
                    and isinstance(node.get("runninghub_schema"), dict)
                ]
                if not candidates:
                    return None
                node = next(
                    (candidate for candidate in candidates if candidate["healthy"]),
                    candidates[0],
                )
            elif node_id == "auto":
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
                        node.get("workflow_id"),
                        node.get("runninghub_resource_type"),
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
            schema = node.get("runninghub_schema")
            if not isinstance(schema, dict):
                return None
            return {
                "provider": "runninghub",
                "runninghub_resource_type": node.get(
                    "runninghub_resource_type", "workflow"
                ),
                "workflow_id": node.get("workflow_id", ""),
                "workflow_url": node.get("workflow_url", ""),
                "workflow_name": node.get("workflow_name") or node.get("name", ""),
                "runninghub_schema": deepcopy(schema),
            }

    def node_in_use(self, node_id: str) -> bool:
        with self._condition:
            if any(slot_node_id == node_id for slot_node_id, _ in self._running_job_ids):
                return True
            node = self._nodes.get(node_id)
            workflow_id = str(node.get("workflow_id") or "") if node else ""
            for job_id in self._order:
                job = self.store.get(job_id)
                if not job:
                    continue
                target = str(job.get("request", {}).get("comfy_node") or "auto")
                if target == node_id:
                    return True
                if workflow_id and runninghub_target_resource_id(target) == workflow_id:
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
                        "workflow_url": node["workflow_url"],
                        "runninghub_resource_type": node[
                            "runninghub_resource_type"
                        ],
                        "workflow_name": node.get("workflow_name") or node["name"]
                        if node["provider"] == "runninghub"
                        else None,
                        "runninghub_schema": deepcopy(node.get("runninghub_schema"))
                        if node["provider"] == "runninghub"
                        else None,
                        "workflow_error": node.get("workflow_error"),
                        "account_balance_coins": node.get("account_balance_coins"),
                        "account_balance_money": node.get("account_balance_money"),
                        "account_currency": node.get("account_currency") or "",
                        "account_current_tasks": node.get("account_current_tasks"),
                        "account_api_type": node.get("account_api_type") or "",
                        "account_error": node.get("account_error") or "",
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
                    if node["provider"] == "runninghub":
                        healthy = isinstance(node.get("runninghub_schema"), dict)
                        profile["account_error"] = str(exc)[:240]
                    else:
                        healthy = False
                        error = str(exc)[:240]
            if node["provider"] == "runninghub":
                healthy = isinstance(
                    profile.get("runninghub_schema") or node.get("runninghub_schema"),
                    dict,
                )
            runtime_values: dict[str, Any] = {}
            with self._condition:
                node["healthy"] = healthy
                node["error"] = error
                node["last_checked"] = utc_now()
                if "workflow_error" in profile:
                    node["workflow_error"] = profile["workflow_error"]
                for field in (
                    "workflow_name",
                    "runninghub_schema",
                    "account_balance_coins",
                    "account_balance_money",
                    "account_currency",
                    "account_current_tasks",
                    "account_api_type",
                    "account_error",
                ):
                    if field in profile:
                        node[field] = profile[field]
                        runtime_values[field] = profile[field]
                if "runninghub_schema_updated_at" in profile:
                    runtime_values["runninghub_schema_updated_at"] = profile[
                        "runninghub_schema_updated_at"
                    ]
                self._revision += 1
                self._condition.notify_all()
            if self.node_runtime_update and runtime_values:
                try:
                    self.node_runtime_update(node_id, runtime_values)
                except Exception:
                    logger.exception("推理节点运行状态写入失败，node_id=%s", node_id)

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
                workflow_url = str(getattr(item, "workflow_url", ""))
                runninghub_resource_type = str(
                    getattr(item, "runninghub_resource_type", "workflow")
                )
                workflow_name = str(getattr(item, "workflow_name", ""))
                runninghub_schema = getattr(item, "runninghub_schema", None)
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
                        workflow_url=workflow_url,
                        runninghub_resource_type=runninghub_resource_type,
                        workflow_name=workflow_name,
                        runninghub_schema=runninghub_schema,
                        capacity=capacity,
                        config=item,
                        retired=False,
                    )
                    if config_changed:
                        current.update(
                            healthy=(
                                provider == "runninghub"
                                and isinstance(runninghub_schema, dict)
                            ),
                            error=None,
                            last_checked=None,
                            workflow_error=None,
                            account_balance_coins=getattr(
                                item, "account_balance_coins", None
                            ),
                            account_balance_money=getattr(
                                item, "account_balance_money", None
                            ),
                            account_currency=getattr(item, "account_currency", ""),
                            account_current_tasks=getattr(
                                item, "account_current_tasks", None
                            ),
                            account_api_type=getattr(item, "account_api_type", ""),
                            account_error=getattr(item, "account_error", ""),
                            last_call_consumed_coins=getattr(
                                item, "last_call_consumed_coins", None
                            ),
                            last_call_consumed_money=getattr(
                                item, "last_call_consumed_money", None
                            ),
                            last_call_cost_at=getattr(item, "last_call_cost_at", ""),
                            last_call_job_id=getattr(item, "last_call_job_id", ""),
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
                        "workflow_url": workflow_url,
                        "runninghub_resource_type": runninghub_resource_type,
                        "workflow_name": workflow_name,
                        "runninghub_schema": runninghub_schema,
                        "workflow_error": None,
                        "account_balance_coins": getattr(
                            item, "account_balance_coins", None
                        ),
                        "account_balance_money": getattr(
                            item, "account_balance_money", None
                        ),
                        "account_currency": getattr(item, "account_currency", ""),
                        "account_current_tasks": getattr(
                            item, "account_current_tasks", None
                        ),
                        "account_api_type": getattr(item, "account_api_type", ""),
                        "account_error": getattr(item, "account_error", ""),
                        "last_call_consumed_coins": getattr(
                            item, "last_call_consumed_coins", None
                        ),
                        "last_call_consumed_money": getattr(
                            item, "last_call_consumed_money", None
                        ),
                        "last_call_cost_at": getattr(item, "last_call_cost_at", ""),
                        "last_call_job_id": getattr(item, "last_call_job_id", ""),
                        "capacity": capacity,
                        "config": item,
                        "healthy": self.health_probe is None
                        or (
                            provider == "runninghub"
                            and isinstance(runninghub_schema, dict)
                        ),
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
            self.store.update(
                job_id,
                status="cancelled",
                stage="已取消",
                progress=0,
                remote_checkpoint=None,
            )
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
                        if job_id in self._running_job_ids.values():
                            continue
                        job = self.store.get(job_id)
                        if not job or job.get("status") != "queued":
                            self._order.remove(job_id)
                            continue
                        checkpoint = job.get("remote_checkpoint")
                        if isinstance(checkpoint, dict) and checkpoint.get("remote_id"):
                            checkpoint_node_id = str(checkpoint.get("node_id") or "")
                            if not checkpoint_node_id or checkpoint_node_id != node_id:
                                continue
                            if str(checkpoint.get("provider") or "") != node["provider"]:
                                continue
                        target = job.get("request", {}).get("comfy_node") or "auto"
                        target_resource_id = runninghub_target_resource_id(target)
                        if not target_resource_id and target not in self._nodes:
                            target = "auto"
                        if target_resource_id:
                            request_resource_id = str(
                                job.get("request", {}).get("runninghub_resource_id") or ""
                            )
                            if (
                                node["provider"] != "runninghub"
                                or node.get("workflow_id") != target_resource_id
                                or (
                                    request_resource_id
                                    and request_resource_id != target_resource_id
                                )
                            ):
                                continue
                        elif target not in {"auto", node_id}:
                            continue
                        if target == "auto":
                            request = job.get("request", {})
                            resource_id = str(
                                request.get("runninghub_resource_id") or ""
                            )
                            if resource_id:
                                if (
                                    node["provider"] != "runninghub"
                                    or node.get("workflow_id") != resource_id
                                ):
                                    continue
                            elif node["provider"] == "runninghub":
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
                "workflow_url": node["workflow_url"],
                "runninghub_resource_type": node["runninghub_resource_type"],
                "workflow_name": node.get("workflow_name") or node["name"]
                if node["provider"] == "runninghub"
                else None,
            }
            self.store.update(
                job_id,
                status="running",
                stage=(
                    f"正在通过 {node['name']} 重新连接远端任务"
                    if job.get("remote_checkpoint")
                    else f"准备 {node['name']} 推理环境"
                ),
                progress=(
                    max(1, min(99, int(job.get("progress") or 1)))
                    if job.get("remote_checkpoint")
                    else 1
                ),
                started_at=job.get("started_at") or utc_now(),
                assigned_node=assigned_node,
                event_message=(
                    f"任务已由 {node['name']} 接管恢复"
                    if job.get("remote_checkpoint")
                    else f"任务已分配至 {node['name']}"
                ),
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
                    current = self.store.get(job_id) or {}
                    progress_floor = (
                        int(current.get("progress") or 1)
                        if current.get("remote_checkpoint")
                        else 1
                    )
                    self.store.update(
                        job_id,
                        progress=max(progress_floor, min(99, percent)),
                        stage=stage,
                    )

                def checkpoint_callback(checkpoint: dict[str, Any] | None) -> None:
                    self.store.update(
                        job_id,
                        remote_checkpoint=deepcopy(checkpoint),
                        remote_retry_count=0,
                    )

                generate_parameters = inspect.signature(engine.generate).parameters
                generate_kwargs: dict[str, Any] = {}
                if "checkpoint" in generate_parameters:
                    generate_kwargs["checkpoint"] = deepcopy(job.get("remote_checkpoint"))
                if "checkpoint_callback" in generate_parameters:
                    generate_kwargs["checkpoint_callback"] = checkpoint_callback
                result = engine.generate(
                    job,
                    progress,
                    lambda: self._is_cancelled(job_id),
                    **generate_kwargs,
                )
                if self._is_cancelled(job_id):
                    self.store.update(
                        job_id,
                        status="cancelled",
                        stage="已取消",
                        progress=0,
                        remote_checkpoint=None,
                    )
                    self._set_incognito_expiry(job_id)
                else:
                    request_update = None
                    output_media_type = getattr(engine, "last_output_media_type", None)
                    if output_media_type and job.get("request", {}).get("provider") == "runninghub":
                        request_update = deepcopy(job["request"])
                        request_update["media_type"] = output_media_type
                    self.store.update(
                        job_id,
                        status="completed",
                        stage="生成完成",
                        progress=100,
                        result_path=str(result),
                        result_url=f"/api/v1/generations/{job_id}/result",
                        completed_at=utc_now(),
                        remote_checkpoint=None,
                        **({"request": request_update} if request_update else {}),
                    )
                    self._set_incognito_expiry(job_id)
            except InterruptedError:
                self.store.update(
                    job_id,
                    status="cancelled",
                    stage="已取消",
                    progress=0,
                    remote_checkpoint=None,
                )
                self._set_incognito_expiry(job_id)
            except Exception as exc:
                current = self.store.get(job_id) or {}
                checkpoint = current.get("remote_checkpoint")
                if (
                    checkpoint
                    and str(checkpoint.get("provider") or "") == "comfyui"
                    and getattr(exc, "retry_fresh_task", False)
                ):
                    retry_count = int(current.get("remote_retry_count") or 0)
                    if retry_count < MAX_FRESH_REMOTE_RETRIES:
                        request_update = deepcopy(current.get("request") or {})
                        with self._condition:
                            original_node = self._nodes.get(node_id)
                            original_node_healthy = bool(
                                original_node and original_node.get("healthy")
                            )
                        if (
                            request_update.get("comfy_node") == node_id
                            and not original_node_healthy
                        ):
                            request_update["comfy_node"] = "auto"
                        self.store.update(
                            job_id,
                            status="queued",
                            stage="远端任务已丢失，重新提交任务",
                            progress=0,
                            remote_checkpoint=None,
                            remote_retry_count=retry_count + 1,
                            cancel_requested=False,
                            request=request_update,
                            event_message=(
                                "ComfyUI 远端任务已丢失，重新提交新任务"
                                + (
                                    "，原节点不可用，改用自动调度"
                                    if request_update.get("comfy_node") == "auto"
                                    and current.get("request", {}).get("comfy_node")
                                    == node_id
                                    else ""
                                )
                            ),
                        )
                        self.submit(job_id)
                        continue
                    error_log = self.store.jobs_dir / f"{job_id}.log"
                    error_log.write_text(traceback.format_exc(), encoding="utf-8")
                    self.store.update(
                        job_id,
                        status="failed",
                        stage="生成失败",
                        error="ComfyUI 远端任务连续丢失，已达到重新提交次数上限",
                        progress=0,
                        remote_checkpoint=None,
                        event_level="error",
                    )
                    self._set_incognito_expiry(job_id)
                    continue
                if checkpoint and getattr(exc, "retry_remote_checkpoint", False):
                    self.store.update(
                        job_id,
                        status="queued",
                        stage="远端服务暂时不可达，等待重新连接",
                        progress=max(1, min(99, int(current.get("progress") or 1))),
                        cancel_requested=False,
                        event_message="远端服务暂时不可达，任务将在原节点继续恢复",
                    )
                    self.submit(job_id)
                    continue
                error_log = self.store.jobs_dir / f"{job_id}.log"
                error_log.write_text(traceback.format_exc(), encoding="utf-8")
                self.store.update(
                    job_id,
                    status="failed",
                    stage="生成失败",
                    error=str(exc)[:800],
                    progress=0,
                    remote_checkpoint=None,
                    event_level="error",
                )
                self._set_incognito_expiry(job_id)
            finally:
                billing = getattr(engine, "last_billing", None)
                if isinstance(billing, dict):
                    self.store.update(job_id, runninghub_billing=billing)
                    account_fields = (
                        "account_balance_coins",
                        "account_balance_money",
                        "account_currency",
                        "account_current_tasks",
                        "account_api_type",
                    )
                    runtime_values = {
                        field: billing[field]
                        for field in account_fields
                        if field in billing
                    }
                    runtime_values.update(
                        {
                            "last_call_consumed_coins": billing.get("consumed_coins"),
                            "last_call_consumed_money": billing.get("consumed_money"),
                            "last_call_cost_at": billing.get("measured_at") or "",
                            "last_call_job_id": job_id,
                        }
                    )
                    with self._condition:
                        node.update(runtime_values)
                    if self.node_runtime_update:
                        try:
                            self.node_runtime_update(node_id, runtime_values)
                        except Exception:
                            logger.exception(
                                "RunningHub 调用费用写入失败，node_id=%s", node_id
                            )
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
