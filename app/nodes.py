from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .jobs import utc_now


@dataclass(frozen=True)
class ComfyNodeConfig:
    id: str
    name: str
    url: str
    provider: str = "comfyui"
    api_key: str = ""
    workflow_id: str = ""
    max_concurrency: int = 1
    workflow_url: str = ""
    runninghub_resource_type: str = "workflow"
    workflow_name: str = ""
    runninghub_schema: dict[str, Any] | None = None
    runninghub_schema_updated_at: str = ""
    account_balance_coins: float | None = None
    account_balance_money: float | None = None
    account_currency: str = ""
    account_current_tasks: int | None = None
    account_api_type: str = ""
    account_error: str = ""
    last_call_consumed_coins: float | None = None
    last_call_consumed_money: float | None = None
    last_call_cost_at: str = ""
    last_call_job_id: str = ""


def parse_runninghub_resource_url(value: str) -> tuple[str, str, str]:
    raw_url = value.strip()
    parsed = urlsplit(raw_url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or hostname not in {
        "runninghub.ai",
        "www.runninghub.ai",
        "runninghub.cn",
        "www.runninghub.cn",
    }:
        raise ValueError("必须填写 RunningHub 官方 HTTPS 地址")
    path = parsed.path.rstrip("/")
    app_match = re.search(r"/ai-detail/(\d+)$", path, re.IGNORECASE)
    workflow_match = re.search(
        r"/(?:workflow|workflow-detail|post)/(\d+)$", path, re.IGNORECASE
    )
    match = app_match or workflow_match
    if not match:
        raise ValueError("RunningHub 地址中未找到可识别的工作流或 AI 应用 ID")
    resource_type = "ai-app" if app_match else "workflow"
    normalized_url = urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
    return normalized_url, match.group(1), resource_type


class NodeRegistry:
    HEALTH_KEY = "comfy_health_seconds"

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.default_url = os.getenv("H3_DEFAULT_COMFY_URL", "http://127.0.0.1:8188").strip().rstrip("/")
        self.default_name = os.getenv("H3_DEFAULT_COMFY_NAME", "Local ComfyUI").strip() or "Local ComfyUI"
        self.default_api_key = os.getenv("H3_DEFAULT_COMFY_API_KEY", "").strip()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS comfy_nodes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT 'comfyui'
                        CHECK (provider IN ('comfyui', 'runninghub')),
                    api_key TEXT NOT NULL DEFAULT '',
                    workflow_id TEXT NOT NULL DEFAULT '',
                    workflow_url TEXT NOT NULL DEFAULT '',
                    runninghub_resource_type TEXT NOT NULL DEFAULT 'workflow',
                    workflow_name TEXT NOT NULL DEFAULT '',
                    runninghub_schema TEXT NOT NULL DEFAULT '',
                    runninghub_schema_updated_at TEXT NOT NULL DEFAULT '',
                    account_balance_coins REAL,
                    account_balance_money REAL,
                    account_currency TEXT NOT NULL DEFAULT '',
                    account_current_tasks INTEGER,
                    account_api_type TEXT NOT NULL DEFAULT '',
                    account_error TEXT NOT NULL DEFAULT '',
                    last_call_consumed_coins REAL,
                    last_call_consumed_money REAL,
                    last_call_cost_at TEXT NOT NULL DEFAULT '',
                    last_call_job_id TEXT NOT NULL DEFAULT '',
                    max_concurrency INTEGER NOT NULL DEFAULT 1
                        CHECK (max_concurrency BETWEEN 1 AND 64),
                    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS service_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(comfy_nodes)")
            }
            migrations = {
                "provider": "TEXT NOT NULL DEFAULT 'comfyui'",
                "api_key": "TEXT NOT NULL DEFAULT ''",
                "workflow_id": "TEXT NOT NULL DEFAULT ''",
                "workflow_url": "TEXT NOT NULL DEFAULT ''",
                "runninghub_resource_type": "TEXT NOT NULL DEFAULT 'workflow'",
                "workflow_name": "TEXT NOT NULL DEFAULT ''",
                "runninghub_schema": "TEXT NOT NULL DEFAULT ''",
                "runninghub_schema_updated_at": "TEXT NOT NULL DEFAULT ''",
                "account_balance_coins": "REAL",
                "account_balance_money": "REAL",
                "account_currency": "TEXT NOT NULL DEFAULT ''",
                "account_current_tasks": "INTEGER",
                "account_api_type": "TEXT NOT NULL DEFAULT ''",
                "account_error": "TEXT NOT NULL DEFAULT ''",
                "last_call_consumed_coins": "REAL",
                "last_call_consumed_money": "REAL",
                "last_call_cost_at": "TEXT NOT NULL DEFAULT ''",
                "last_call_job_id": "TEXT NOT NULL DEFAULT ''",
                "max_concurrency": "INTEGER NOT NULL DEFAULT 1",
            }
            for name, definition in migrations.items():
                if name not in columns:
                    connection.execute(
                        f"ALTER TABLE comfy_nodes ADD COLUMN {name} {definition}"
                    )

            table_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'comfy_nodes'"
            ).fetchone()["sql"]
            if (
                re.search(r"url\s+TEXT\s+NOT\s+NULL\s+UNIQUE", table_sql, re.IGNORECASE)
                or "runninghub" not in table_sql.lower()
            ):
                connection.executescript(
                    """
                    CREATE TABLE comfy_nodes_migrated (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        url TEXT NOT NULL,
                        provider TEXT NOT NULL DEFAULT 'comfyui'
                            CHECK (provider IN ('comfyui', 'runninghub')),
                        api_key TEXT NOT NULL DEFAULT '',
                        workflow_id TEXT NOT NULL DEFAULT '',
                        workflow_url TEXT NOT NULL DEFAULT '',
                        runninghub_resource_type TEXT NOT NULL DEFAULT 'workflow',
                        workflow_name TEXT NOT NULL DEFAULT '',
                        runninghub_schema TEXT NOT NULL DEFAULT '',
                        runninghub_schema_updated_at TEXT NOT NULL DEFAULT '',
                        account_balance_coins REAL,
                        account_balance_money REAL,
                        account_currency TEXT NOT NULL DEFAULT '',
                        account_current_tasks INTEGER,
                        account_api_type TEXT NOT NULL DEFAULT '',
                        account_error TEXT NOT NULL DEFAULT '',
                        last_call_consumed_coins REAL,
                        last_call_consumed_money REAL,
                        last_call_cost_at TEXT NOT NULL DEFAULT '',
                        last_call_job_id TEXT NOT NULL DEFAULT '',
                        max_concurrency INTEGER NOT NULL DEFAULT 1
                            CHECK (max_concurrency BETWEEN 1 AND 64),
                        enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    INSERT INTO comfy_nodes_migrated (
                        id, name, url, provider, api_key, workflow_id, workflow_url,
                        runninghub_resource_type, workflow_name, runninghub_schema,
                        runninghub_schema_updated_at, account_balance_coins,
                        account_balance_money, account_currency, account_current_tasks,
                        account_api_type, account_error, last_call_consumed_coins,
                        last_call_consumed_money, last_call_cost_at, last_call_job_id,
                        max_concurrency, enabled, created_at, updated_at
                    )
                    SELECT
                        id, name, url, provider, api_key, workflow_id, workflow_url,
                        runninghub_resource_type, workflow_name, runninghub_schema,
                        runninghub_schema_updated_at, account_balance_coins,
                        account_balance_money, account_currency, account_current_tasks,
                        account_api_type, account_error, last_call_consumed_coins,
                        last_call_consumed_money, last_call_cost_at, last_call_job_id,
                        max_concurrency, enabled, created_at, updated_at
                    FROM comfy_nodes;
                    DROP TABLE comfy_nodes;
                    ALTER TABLE comfy_nodes_migrated RENAME TO comfy_nodes;
                    """
                )
            count = connection.execute("SELECT COUNT(*) FROM comfy_nodes").fetchone()[0]
            initialized = connection.execute(
                "SELECT value FROM service_settings WHERE key = ?",
                ("comfy_nodes_initialized",),
            ).fetchone()
            if count == 0 and initialized is None:
                now = utc_now()
                connection.execute(
                    "INSERT INTO comfy_nodes "
                    "(id, name, url, provider, api_key, workflow_id, workflow_url, "
                    "runninghub_resource_type, workflow_name, runninghub_schema, "
                    "runninghub_schema_updated_at, max_concurrency, enabled, created_at, "
                    "updated_at) VALUES (?, ?, ?, 'comfyui', ?, '', '', 'workflow', "
                    "'', '', '', 1, 1, ?, ?)",
                    (
                        "local",
                        self.default_name,
                        self.default_url,
                        self.default_api_key,
                        now,
                        now,
                    ),
                )
            connection.execute(
                "INSERT OR IGNORE INTO service_settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("comfy_nodes_initialized", "1", utc_now()),
            )
            connection.execute(
                "INSERT OR IGNORE INTO service_settings (key, value, updated_at) VALUES (?, ?, ?)",
                (self.HEALTH_KEY, "60", utc_now()),
            )

    @staticmethod
    def _validate(
        node_id: str,
        name: str,
        url: str,
        provider: str = "comfyui",
        api_key: str = "",
        workflow_url: str = "",
        max_concurrency: int = 1,
        workflow_name: str = "",
        runninghub_schema: dict[str, Any] | None = None,
    ) -> ComfyNodeConfig:
        node_id = node_id.strip()
        name = name.strip()
        url = url.strip().rstrip("/")
        provider = provider.strip().lower()
        api_key = api_key.strip()
        workflow_url = workflow_url.strip()
        workflow_name = workflow_name.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", node_id):
            raise ValueError("节点 ID 只能包含字母、数字、点、下划线和连字符")
        if node_id == "auto":
            raise ValueError("auto 是保留节点 ID")
        if not name or len(name) > 120:
            raise ValueError("节点名称长度必须为 1 至 120 个字符")
        if provider not in {"comfyui", "runninghub"}:
            raise ValueError("节点类型必须为 comfyui 或 runninghub")
        if len(api_key) > 2000:
            raise ValueError("API Key 长度不能超过 2000 个字符")
        if provider == "runninghub":
            if not api_key:
                raise ValueError("RunningHub API 节点必须填写 API Key")
            if not workflow_url or len(workflow_url) > 500:
                raise ValueError("RunningHub API 节点必须填写工作流或 AI 应用地址")
            workflow_url, workflow_id, resource_type = parse_runninghub_resource_url(
                workflow_url
            )
            resource_url = urlsplit(workflow_url)
            url = urlunsplit((resource_url.scheme, resource_url.netloc, "", "", "")).rstrip("/")
            if not 1 <= int(max_concurrency) <= 64:
                raise ValueError("RunningHub API 最大并发数必须为 1 至 64")
        else:
            workflow_url = ""
            workflow_id = ""
            resource_type = "workflow"
            max_concurrency = 1
            workflow_name = ""
            runninghub_schema = None
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("API 地址必须是有效的 HTTP(S) URL")
        return ComfyNodeConfig(
            id=node_id,
            name=name,
            url=url,
            provider=provider,
            api_key=api_key,
            workflow_id=workflow_id,
            max_concurrency=int(max_concurrency),
            workflow_url=workflow_url,
            runninghub_resource_type=resource_type,
            workflow_name=workflow_name,
            runninghub_schema=runninghub_schema,
            runninghub_schema_updated_at=str(
                (runninghub_schema or {}).get("updated_at") or ""
            ),
        )

    def build_config(
        self,
        node_id: str,
        name: str,
        url: str,
        provider: str = "comfyui",
        api_key: str = "",
        workflow_url: str = "",
        max_concurrency: int = 1,
        workflow_name: str = "",
        runninghub_schema: dict[str, Any] | None = None,
    ) -> ComfyNodeConfig:
        return self._validate(
            node_id,
            name,
            url,
            provider,
            api_key,
            workflow_url,
            max_concurrency,
            workflow_name,
            runninghub_schema,
        )

    @staticmethod
    def _public(row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        result["has_api_key"] = bool(result.pop("api_key", ""))
        raw_schema = result.get("runninghub_schema")
        if isinstance(raw_schema, str):
            try:
                result["runninghub_schema"] = json.loads(raw_schema) if raw_schema else None
            except json.JSONDecodeError:
                result["runninghub_schema"] = None
        return result

    def list(
        self, enabled_only: bool = True, include_secrets: bool = False
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM comfy_nodes"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY created_at, id"
        with self._lock, self._connect() as connection:
            rows = [dict(row) for row in connection.execute(query).fetchall()]
        return rows if include_secrets else [self._public(row) for row in rows]

    def configs(self) -> tuple[ComfyNodeConfig, ...]:
        return tuple(
            ComfyNodeConfig(
                id=row["id"],
                name=row["name"],
                url=row["url"],
                provider=row["provider"],
                api_key=row["api_key"],
                workflow_id=row["workflow_id"],
                max_concurrency=int(row["max_concurrency"]),
                workflow_url=row["workflow_url"],
                runninghub_resource_type=row["runninghub_resource_type"],
                workflow_name=row["workflow_name"],
                runninghub_schema=json.loads(row["runninghub_schema"] or "null"),
                runninghub_schema_updated_at=row["runninghub_schema_updated_at"],
                account_balance_coins=row["account_balance_coins"],
                account_balance_money=row["account_balance_money"],
                account_currency=row["account_currency"],
                account_current_tasks=row["account_current_tasks"],
                account_api_type=row["account_api_type"],
                account_error=row["account_error"],
                last_call_consumed_coins=row["last_call_consumed_coins"],
                last_call_consumed_money=row["last_call_consumed_money"],
                last_call_cost_at=row["last_call_cost_at"],
                last_call_job_id=row["last_call_job_id"],
            )
            for row in self.list(enabled_only=True, include_secrets=True)
        )

    def _get_raw(self, node_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM comfy_nodes WHERE id = ?", (node_id,)
            ).fetchone()
            return dict(row) if row else None

    def get(self, node_id: str) -> dict[str, Any] | None:
        row = self._get_raw(node_id)
        return self._public(row) if row else None

    def create(
        self,
        node_id: str,
        name: str,
        url: str,
        provider: str = "comfyui",
        api_key: str = "",
        workflow_url: str = "",
        max_concurrency: int = 1,
        workflow_name: str = "",
        runninghub_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        node = self._validate(
            node_id,
            name,
            url,
            provider,
            api_key,
            workflow_url,
            max_concurrency,
            workflow_name,
            runninghub_schema,
        )
        now = utc_now()
        try:
            with self._lock, self._connect() as connection:
                connection.execute(
                    "INSERT INTO comfy_nodes "
                    "(id, name, url, provider, api_key, workflow_id, workflow_url, "
                    "runninghub_resource_type, workflow_name, runninghub_schema, "
                    "runninghub_schema_updated_at, max_concurrency, enabled, created_at, "
                    "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
                    (
                        node.id,
                        node.name,
                        node.url,
                        node.provider,
                        node.api_key,
                        node.workflow_id,
                        node.workflow_url,
                        node.runninghub_resource_type,
                        node.workflow_name,
                        json.dumps(node.runninghub_schema, ensure_ascii=False)
                        if node.runninghub_schema
                        else "",
                        node.runninghub_schema_updated_at,
                        node.max_concurrency,
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("节点 ID 已存在") from exc
        return self.get(node.id) or self._public(asdict(node))

    def update(
        self,
        node_id: str,
        name: str,
        url: str,
        enabled: bool = True,
        provider: str = "comfyui",
        api_key: str | None = None,
        workflow_url: str = "",
        max_concurrency: int = 1,
        workflow_name: str = "",
        runninghub_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = self._get_raw(node_id)
        if not existing:
            raise KeyError(node_id)
        submitted_api_key = (api_key or "").strip()
        effective_api_key = (
            submitted_api_key or existing["api_key"]
            if provider == existing["provider"]
            else submitted_api_key
        )
        node = self._validate(
            node_id,
            name,
            url,
            provider,
            effective_api_key,
            workflow_url,
            max_concurrency,
            workflow_name,
            runninghub_schema,
        )
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE comfy_nodes SET name = ?, url = ?, provider = ?, api_key = ?, "
                "workflow_id = ?, workflow_url = ?, runninghub_resource_type = ?, "
                "workflow_name = ?, runninghub_schema = ?, "
                "runninghub_schema_updated_at = ?, max_concurrency = ?, enabled = ?, "
                "updated_at = ? "
                "WHERE id = ?",
                (
                    node.name,
                    node.url,
                    node.provider,
                    node.api_key,
                    node.workflow_id,
                    node.workflow_url,
                    node.runninghub_resource_type,
                    node.workflow_name,
                    json.dumps(node.runninghub_schema, ensure_ascii=False)
                    if node.runninghub_schema
                    else "",
                    node.runninghub_schema_updated_at,
                    node.max_concurrency,
                    int(enabled),
                    utc_now(),
                    node_id,
                ),
            )
        return self.get(node_id) or self._public(asdict(node))

    def config(self, node_id: str) -> ComfyNodeConfig | None:
        row = self._get_raw(node_id)
        if not row:
            return None
        return ComfyNodeConfig(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            provider=row["provider"],
            api_key=row["api_key"],
            workflow_id=row["workflow_id"],
            max_concurrency=int(row["max_concurrency"]),
            workflow_url=row["workflow_url"],
            runninghub_resource_type=row["runninghub_resource_type"],
            workflow_name=row["workflow_name"],
            runninghub_schema=json.loads(row["runninghub_schema"] or "null"),
            runninghub_schema_updated_at=row["runninghub_schema_updated_at"],
            account_balance_coins=row["account_balance_coins"],
            account_balance_money=row["account_balance_money"],
            account_currency=row["account_currency"],
            account_current_tasks=row["account_current_tasks"],
            account_api_type=row["account_api_type"],
            account_error=row["account_error"],
            last_call_consumed_coins=row["last_call_consumed_coins"],
            last_call_consumed_money=row["last_call_consumed_money"],
            last_call_cost_at=row["last_call_cost_at"],
            last_call_job_id=row["last_call_job_id"],
        )

    def update_runtime(self, node_id: str, values: dict[str, Any]) -> None:
        allowed = {
            "workflow_name",
            "runninghub_schema",
            "runninghub_schema_updated_at",
            "account_balance_coins",
            "account_balance_money",
            "account_currency",
            "account_current_tasks",
            "account_api_type",
            "account_error",
            "last_call_consumed_coins",
            "last_call_consumed_money",
            "last_call_cost_at",
            "last_call_job_id",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        if not updates:
            return
        if "runninghub_schema" in updates:
            schema = updates["runninghub_schema"]
            updates["runninghub_schema"] = (
                json.dumps(schema, ensure_ascii=False) if isinstance(schema, dict) else ""
            )
            if isinstance(schema, dict):
                updates.setdefault(
                    "runninghub_schema_updated_at", str(schema.get("updated_at") or "")
                )
        assignments = ", ".join(f"{key} = ?" for key in updates)
        with self._lock, self._connect() as connection:
            connection.execute(
                f"UPDATE comfy_nodes SET {assignments} WHERE id = ?",
                (*updates.values(), node_id),
            )

    def delete(self, node_id: str) -> bool:
        with self._lock, self._connect() as connection:
            cursor = connection.execute("DELETE FROM comfy_nodes WHERE id = ?", (node_id,))
            return cursor.rowcount > 0

    def health_interval(self) -> float:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM service_settings WHERE key = ?", (self.HEALTH_KEY,)
            ).fetchone()
        try:
            return max(5.0, min(3600.0, float(row["value"] if row else 60)))
        except (TypeError, ValueError):
            return 60.0

    def set_health_interval(self, seconds: float) -> float:
        seconds = max(5.0, min(3600.0, float(seconds)))
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO service_settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (self.HEALTH_KEY, f"{seconds:g}", utc_now()),
            )
        return seconds
