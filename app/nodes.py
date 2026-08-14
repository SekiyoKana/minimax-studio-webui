from __future__ import annotations

import re
import sqlite3
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .jobs import utc_now


@dataclass(frozen=True)
class ComfyNodeConfig:
    id: str
    name: str
    url: str


class NodeRegistry:
    HEALTH_KEY = "comfy_health_seconds"

    def __init__(self, database_path: Path):
        self.database_path = database_path
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
                    url TEXT NOT NULL UNIQUE,
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
            count = connection.execute("SELECT COUNT(*) FROM comfy_nodes").fetchone()[0]
            if count == 0:
                now = utc_now()
                connection.execute(
                    "INSERT INTO comfy_nodes (id, name, url, enabled, created_at, updated_at) "
                    "VALUES (?, ?, ?, 1, ?, ?)",
                    ("local", "Local ComfyUI", "http://127.0.0.1:8188", now, now),
                )
            connection.execute(
                "INSERT OR IGNORE INTO service_settings (key, value, updated_at) VALUES (?, ?, ?)",
                (self.HEALTH_KEY, "60", utc_now()),
            )

    @staticmethod
    def _validate(node_id: str, name: str, url: str) -> ComfyNodeConfig:
        node_id = node_id.strip()
        name = name.strip()
        url = url.strip().rstrip("/")
        parsed = urlsplit(url)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", node_id):
            raise ValueError("节点 ID 只能包含字母、数字、点、下划线和连字符")
        if node_id == "auto":
            raise ValueError("auto 是保留节点 ID")
        if not name or len(name) > 120:
            raise ValueError("节点名称长度必须为 1 至 120 个字符")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("ComfyUI API 地址必须是有效的 HTTP(S) URL")
        return ComfyNodeConfig(node_id, name, url)

    def list(self, enabled_only: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM comfy_nodes"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY created_at, id"
        with self._lock, self._connect() as connection:
            return [dict(row) for row in connection.execute(query).fetchall()]

    def configs(self) -> tuple[ComfyNodeConfig, ...]:
        return tuple(
            ComfyNodeConfig(row["id"], row["name"], row["url"])
            for row in self.list(enabled_only=True)
        )

    def get(self, node_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM comfy_nodes WHERE id = ?", (node_id,)
            ).fetchone()
            return dict(row) if row else None

    def create(self, node_id: str, name: str, url: str) -> dict[str, Any]:
        node = self._validate(node_id, name, url)
        now = utc_now()
        try:
            with self._lock, self._connect() as connection:
                connection.execute(
                    "INSERT INTO comfy_nodes (id, name, url, enabled, created_at, updated_at) "
                    "VALUES (?, ?, ?, 1, ?, ?)",
                    (node.id, node.name, node.url, now, now),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("节点 ID 或 API 地址已存在") from exc
        return self.get(node.id) or asdict(node)

    def update(self, node_id: str, name: str, url: str, enabled: bool = True) -> dict[str, Any]:
        node = self._validate(node_id, name, url)
        try:
            with self._lock, self._connect() as connection:
                cursor = connection.execute(
                    "UPDATE comfy_nodes SET name = ?, url = ?, enabled = ?, updated_at = ? "
                    "WHERE id = ?",
                    (node.name, node.url, int(enabled), utc_now(), node_id),
                )
                if cursor.rowcount == 0:
                    raise KeyError(node_id)
        except sqlite3.IntegrityError as exc:
            raise ValueError("ComfyUI API 地址已存在") from exc
        return self.get(node_id) or asdict(node)

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
