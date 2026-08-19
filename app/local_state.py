from __future__ import annotations

import json
import hashlib
import hmac
import secrets
import socket
import sqlite3
import threading
import time
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .jobs import utc_now


class LocalStateStore:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._events: deque[dict[str, Any]] = deque(maxlen=100)
        self._revision = 0
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS desktop_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS peer_devices (
                    device_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    access_token TEXT NOT NULL,
                    inbound_token_hash TEXT NOT NULL,
                    records_key TEXT NOT NULL DEFAULT '',
                    records_key_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS remote_records (
                    record_id TEXT PRIMARY KEY,
                    peer_device_id TEXT NOT NULL,
                    record_type TEXT NOT NULL,
                    payload BLOB NOT NULL,
                    nonce BLOB,
                    encrypted INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS remote_records_peer_idx
                    ON remote_records (peer_device_id, record_type);
                CREATE TABLE IF NOT EXISTS unlocked_peer_keys (
                    peer_device_id TEXT PRIMARY KEY,
                    key_id TEXT NOT NULL,
                    encrypted_key BLOB NOT NULL,
                    nonce BLOB NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(peer_devices)").fetchall()
            }
            if "records_key" not in columns:
                connection.execute(
                    "ALTER TABLE peer_devices ADD COLUMN records_key TEXT NOT NULL DEFAULT ''"
                )
            if "records_key_id" not in columns:
                connection.execute(
                    "ALTER TABLE peer_devices ADD COLUMN records_key_id TEXT NOT NULL DEFAULT ''"
                )
            defaults = {
                "device_id": secrets.token_hex(16),
                "machine_name": socket.gethostname().split(".", 1)[0] or "H3 Studio",
                "sharing_enabled": "0",
                "pairing_secret": secrets.token_hex(32),
                "ai_enabled": "0",
                "ai_base_url": "",
                "ai_model": "",
                "ai_api_key": "",
                "show_runtime_logs": "1",
                "show_peering": "1",
                "backup_outputs": "0",
                "remote_disconnect_policy": "encrypt",
                "remote_records_key": secrets.token_urlsafe(32),
            }
            now = utc_now()
            connection.executemany(
                "INSERT OR IGNORE INTO desktop_settings (key, value, updated_at) VALUES (?, ?, ?)",
                [(key, value, now) for key, value in defaults.items()],
            )

    def get_setting(self, key: str, default: str = "") -> str:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM desktop_settings WHERE key = ?", (key,)
            ).fetchone()
        return str(row["value"]) if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO desktop_settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, value, utc_now()),
            )

    @property
    def device_id(self) -> str:
        return self.get_setting("device_id")

    @property
    def machine_name(self) -> str:
        return self.get_setting("machine_name", "H3 Studio")

    @property
    def sharing_enabled(self) -> bool:
        return self.get_setting("sharing_enabled") == "1"

    def update_desktop_settings(
        self, *, machine_name: str | None = None, sharing_enabled: bool | None = None
    ) -> None:
        if machine_name is not None:
            name = machine_name.strip()
            if not name or len(name) > 80:
                raise ValueError("本机名称长度必须为 1 至 80 个字符")
            self.set_setting("machine_name", name)
        if sharing_enabled is not None:
            self.set_setting("sharing_enabled", "1" if sharing_enabled else "0")
        self.record_event("settings_updated")

    def general_settings(self, include_secret: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "show_runtime_logs": self.get_setting("show_runtime_logs", "1") == "1",
            "show_peering": self.get_setting("show_peering", "1") == "1",
            "backup_outputs": self.get_setting("backup_outputs", "0") == "1",
            "remote_disconnect_policy": self.get_setting(
                "remote_disconnect_policy", "encrypt"
            ),
        }
        if include_secret:
            result["remote_records_key"] = self.get_setting("remote_records_key")
        return result

    def update_general_settings(
        self,
        *,
        show_runtime_logs: bool | None = None,
        show_peering: bool | None = None,
        backup_outputs: bool | None = None,
        remote_disconnect_policy: str | None = None,
        remote_records_key: str | None = None,
    ) -> dict[str, Any]:
        bool_values = {
            "show_runtime_logs": show_runtime_logs,
            "show_peering": show_peering,
            "backup_outputs": backup_outputs,
        }
        for key, value in bool_values.items():
            if value is not None:
                self.set_setting(key, "1" if value else "0")
        if remote_disconnect_policy is not None:
            if remote_disconnect_policy not in {"encrypt", "delete"}:
                raise ValueError("互联断开策略无效")
            self.set_setting("remote_disconnect_policy", remote_disconnect_policy)
        if remote_records_key is not None:
            self.validate_remote_records_key(remote_records_key)
            self.set_setting("remote_records_key", remote_records_key)
        self.record_event("general_settings_updated")
        return self.general_settings()

    @staticmethod
    def validate_remote_records_key(value: str) -> None:
        if not 8 <= len(value) <= 256:
            raise ValueError("加密密钥长度必须为 8 至 256 个字符")

    @classmethod
    def records_key_id(cls, value: str) -> str:
        cls.validate_remote_records_key(value)
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

    def remote_disconnect_policy(self) -> str:
        value = self.get_setting("remote_disconnect_policy", "encrypt")
        return value if value in {"encrypt", "delete"} else "encrypt"

    def backup_outputs_enabled(self) -> bool:
        return self.get_setting("backup_outputs", "0") == "1"

    def opaque_node_id(self, node_id: str) -> str:
        secret = bytes.fromhex(self.get_setting("pairing_secret"))
        digest = hmac.new(secret, node_id.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest[:24]

    def _remote_records_key(self) -> bytes:
        value = self.get_setting("remote_records_key")
        self.validate_remote_records_key(value)
        return hashlib.scrypt(
            value.encode("utf-8"),
            salt=hashlib.sha256(self.device_id.encode("ascii")).digest()[:16],
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )

    def encrypt_bytes(self, payload: bytes) -> tuple[bytes, bytes]:
        nonce = secrets.token_bytes(12)
        encrypted = AESGCM(self._remote_records_key()).encrypt(nonce, payload, None)
        return encrypted, nonce

    def decrypt_bytes(self, payload: bytes, nonce: bytes) -> bytes:
        return AESGCM(self._remote_records_key()).decrypt(nonce, payload, None)

    @classmethod
    def _peer_records_key(cls, value: str, peer_device_id: str) -> bytes:
        cls.validate_remote_records_key(value)
        return hashlib.scrypt(
            value.encode("utf-8"),
            salt=hashlib.sha256(peer_device_id.encode("utf-8")).digest()[:16],
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )

    def encrypt_peer_bytes(
        self, payload: bytes, peer_device_id: str, records_key: str
    ) -> tuple[bytes, bytes]:
        nonce = secrets.token_bytes(12)
        encrypted = AESGCM(
            self._peer_records_key(records_key, peer_device_id)
        ).encrypt(nonce, payload, None)
        return encrypted, nonce

    def decrypt_peer_bytes(
        self, payload: bytes, nonce: bytes, peer_device_id: str, records_key: str
    ) -> bytes:
        return AESGCM(
            self._peer_records_key(records_key, peer_device_id)
        ).decrypt(nonce, payload, None)

    def put_remote_record(
        self,
        *,
        record_id: str,
        peer_device_id: str,
        record_type: str,
        value: dict[str, Any],
        encrypted: bool,
    ) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        nonce: bytes | None = None
        if encrypted:
            payload, nonce = self.encrypt_bytes(payload)
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO remote_records "
                "(record_id, peer_device_id, record_type, payload, nonce, encrypted, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(record_id) DO UPDATE SET peer_device_id = excluded.peer_device_id, "
                "record_type = excluded.record_type, payload = excluded.payload, nonce = excluded.nonce, "
                "encrypted = excluded.encrypted, updated_at = excluded.updated_at",
                (
                    record_id,
                    peer_device_id,
                    record_type,
                    payload,
                    nonce,
                    1 if encrypted else 0,
                    utc_now(),
                ),
            )

    def put_peer_encrypted_record(
        self,
        *,
        record_id: str,
        peer_device_id: str,
        record_type: str,
        value: dict[str, Any],
        records_key: str,
    ) -> None:
        payload, nonce = self.encrypt_peer_bytes(
            json.dumps(value, ensure_ascii=False).encode("utf-8"),
            peer_device_id,
            records_key,
        )
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO remote_records "
                "(record_id, peer_device_id, record_type, payload, nonce, encrypted, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 1, ?) "
                "ON CONFLICT(record_id) DO UPDATE SET peer_device_id = excluded.peer_device_id, "
                "record_type = excluded.record_type, payload = excluded.payload, nonce = excluded.nonce, "
                "encrypted = 1, updated_at = excluded.updated_at",
                (
                    record_id,
                    peer_device_id,
                    record_type,
                    payload,
                    nonce,
                    utc_now(),
                ),
            )

    def plain_remote_records(
        self, record_type: str, peer_device_id: str | None = None
    ) -> list[dict[str, Any]]:
        query = (
            "SELECT record_id, peer_device_id, payload, updated_at FROM remote_records "
            "WHERE record_type = ? AND encrypted = 0"
        )
        parameters: tuple[Any, ...] = (record_type,)
        if peer_device_id is not None:
            query += " AND peer_device_id = ?"
            parameters = (record_type, peer_device_id)
        query += " ORDER BY updated_at DESC"
        with self._lock, self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        values = []
        for row in rows:
            try:
                value = json.loads(bytes(row["payload"]).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            values.append(
                {
                    "record_id": str(row["record_id"]),
                    "peer_device_id": str(row["peer_device_id"]),
                    "updated_at": str(row["updated_at"]),
                    "value": value,
                }
            )
        return values

    def read_peer_encrypted_record(
        self, record_id: str, peer_device_id: str, records_key: str, *, delete: bool = False
    ) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload, nonce, encrypted FROM remote_records "
                "WHERE record_id = ? AND peer_device_id = ?",
                (record_id, peer_device_id),
            ).fetchone()
        if not row:
            return None
        payload = bytes(row["payload"])
        if row["encrypted"]:
            payload = self.decrypt_peer_bytes(
                payload,
                bytes(row["nonce"] or b""),
                peer_device_id,
                records_key,
            )
        value = json.loads(payload.decode("utf-8"))
        if delete:
            self.delete_remote_record(record_id)
        return value

    def delete_remote_record(self, record_id: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "DELETE FROM remote_records WHERE record_id = ?", (record_id,)
            )

    def _unlock_cache_key(self) -> bytes:
        secret = bytes.fromhex(self.get_setting("pairing_secret"))
        return hashlib.sha256(secret + b"h3-unlocked-peer-key").digest()

    def cache_unlocked_peer_key(
        self, peer_device_id: str, key_id: str, records_key: str
    ) -> None:
        self.validate_remote_records_key(records_key)
        if not secrets.compare_digest(self.records_key_id(records_key), key_id):
            raise ValueError("远程记录密钥不匹配")
        nonce = secrets.token_bytes(12)
        encrypted = AESGCM(self._unlock_cache_key()).encrypt(
            nonce, records_key.encode("utf-8"), peer_device_id.encode("utf-8")
        )
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO unlocked_peer_keys "
                "(peer_device_id, key_id, encrypted_key, nonce, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(peer_device_id) DO UPDATE SET key_id = excluded.key_id, "
                "encrypted_key = excluded.encrypted_key, nonce = excluded.nonce, updated_at = excluded.updated_at",
                (peer_device_id, key_id, encrypted, nonce, utc_now()),
            )

    def unlocked_peer_key(self, peer_device_id: str, key_id: str) -> str | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT key_id, encrypted_key, nonce FROM unlocked_peer_keys WHERE peer_device_id = ?",
                (peer_device_id,),
            ).fetchone()
        if not row or not secrets.compare_digest(str(row["key_id"]), key_id):
            return None
        try:
            value = AESGCM(self._unlock_cache_key()).decrypt(
                bytes(row["nonce"]),
                bytes(row["encrypted_key"]),
                peer_device_id.encode("utf-8"),
            ).decode("utf-8")
            if secrets.compare_digest(self.records_key_id(value), key_id):
                return value
        except (ValueError, UnicodeDecodeError):
            pass
        self.clear_unlocked_peer_key(peer_device_id)
        return None

    def clear_unlocked_peer_key(self, peer_device_id: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "DELETE FROM unlocked_peer_keys WHERE peer_device_id = ?",
                (peer_device_id,),
            )

    def consume_remote_records(
        self, peer_device_id: str, record_type: str = "job"
    ) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT record_id, payload, nonce, encrypted FROM remote_records "
                "WHERE peer_device_id = ? AND record_type = ? ORDER BY updated_at",
                (peer_device_id, record_type),
            ).fetchall()
        values: list[dict[str, Any]] = []
        record_ids: list[str] = []
        for row in rows:
            payload = bytes(row["payload"])
            if row["encrypted"]:
                nonce = bytes(row["nonce"] or b"")
                payload = self.decrypt_bytes(payload, nonce)
            values.append(json.loads(payload.decode("utf-8")))
            record_ids.append(str(row["record_id"]))
        if record_ids:
            with self._lock, self._connect() as connection:
                connection.executemany(
                    "DELETE FROM remote_records WHERE record_id = ?",
                    [(record_id,) for record_id in record_ids],
                )
        return values

    def delete_remote_records(self, peer_device_id: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "DELETE FROM remote_records WHERE peer_device_id = ?", (peer_device_id,)
            )

    def encrypt_remote_records(self, peer_device_id: str) -> None:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT record_id, payload, encrypted FROM remote_records "
                "WHERE peer_device_id = ? AND record_type <> 'job_snapshot_meta'",
                (peer_device_id,),
            ).fetchall()
            for row in rows:
                if row["encrypted"]:
                    continue
                encrypted, nonce = self.encrypt_bytes(bytes(row["payload"]))
                connection.execute(
                    "UPDATE remote_records SET payload = ?, nonce = ?, encrypted = 1, updated_at = ? WHERE record_id = ?",
                    (encrypted, nonce, utc_now(), row["record_id"]),
                )

    def protect_remote_records(self, peer_device_id: str) -> None:
        if self.remote_disconnect_policy() == "delete":
            self.delete_remote_records(peer_device_id)
        else:
            self.encrypt_remote_records(peer_device_id)

    def ai_config(self, include_secret: bool = False) -> dict[str, Any]:
        api_key = self.get_setting("ai_api_key")
        result: dict[str, Any] = {
            "enabled": self.get_setting("ai_enabled") == "1",
            "base_url": self.get_setting("ai_base_url"),
            "model": self.get_setting("ai_model"),
            "has_api_key": bool(api_key),
        }
        if include_secret:
            result["api_key"] = api_key
        return result

    def update_ai_config(
        self,
        *,
        enabled: bool,
        base_url: str,
        model: str,
        api_key: str | None = None,
        clear_api_key: bool = False,
    ) -> dict[str, Any]:
        base_url = base_url.strip()
        model = model.strip()
        if len(base_url) > 500 or len(model) > 200:
            raise ValueError("AI 服务配置长度超出限制")
        self.set_setting("ai_enabled", "1" if enabled else "0")
        self.set_setting("ai_base_url", base_url)
        self.set_setting("ai_model", model)
        if clear_api_key:
            self.set_setting("ai_api_key", "")
        elif api_key:
            value = api_key.strip()
            if len(value) > 2000:
                raise ValueError("API Key 长度不能超过 2000 个字符")
            self.set_setting("ai_api_key", value)
        return self.ai_config()

    def pairing_code(self, timestamp: float | None = None) -> str:
        counter = int((timestamp or time.time()) // 30)
        digest = hmac.new(
            bytes.fromhex(self.get_setting("pairing_secret")),
            counter.to_bytes(8, "big"),
            hashlib.sha256,
        ).digest()
        return f"{int.from_bytes(digest[-4:], 'big') % 1_000_000:06d}"

    def verify_pairing_code(self, code: str, timestamp: float | None = None) -> bool:
        if not code.isdigit() or len(code) != 6:
            return False
        now = timestamp or time.time()
        return any(
            secrets.compare_digest(code, self.pairing_code(now + offset))
            for offset in (-30, 0)
        )

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def upsert_peer(
        self,
        *,
        device_id: str,
        name: str,
        base_url: str,
        access_token: str,
        inbound_token: str,
        records_key: str = "",
    ) -> dict[str, Any]:
        if not device_id or device_id == self.device_id:
            raise ValueError("互联设备 ID 无效")
        records_key_id = ""
        if records_key:
            self.validate_remote_records_key(records_key)
            records_key_id = self.records_key_id(records_key)
            cached = self.unlocked_peer_key(device_id, records_key_id)
            if cached is None:
                self.clear_unlocked_peer_key(device_id)
        now = utc_now()
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO peer_devices "
                "(device_id, name, base_url, access_token, inbound_token_hash, records_key, records_key_id, created_at, updated_at, last_seen_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(device_id) DO UPDATE SET name = excluded.name, base_url = excluded.base_url, "
                "access_token = excluded.access_token, inbound_token_hash = excluded.inbound_token_hash, "
                "records_key = CASE WHEN excluded.records_key <> '' THEN excluded.records_key ELSE peer_devices.records_key END, "
                "records_key_id = CASE WHEN excluded.records_key_id <> '' THEN excluded.records_key_id ELSE peer_devices.records_key_id END, "
                "updated_at = excluded.updated_at, last_seen_at = excluded.last_seen_at",
                (
                    device_id,
                    name.strip()[:80] or "H3 Studio",
                    base_url,
                    access_token,
                    self.token_hash(inbound_token),
                    records_key,
                    records_key_id,
                    now,
                    now,
                    now,
                ),
            )
        peer = self.peer(device_id)
        self.record_event("peer_connected", peer_id=device_id, peer_name=name)
        return peer or {}

    def peers(self, include_secrets: bool = False) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM peer_devices ORDER BY name COLLATE NOCASE, device_id"
                ).fetchall()
            ]
        if include_secrets:
            return rows
        for row in rows:
            row.pop("access_token", None)
            row.pop("inbound_token_hash", None)
            row.pop("records_key", None)
        return rows

    def peer(self, device_id: str, include_secrets: bool = False) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM peer_devices WHERE device_id = ?", (device_id,)
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        if not include_secrets:
            result.pop("access_token", None)
            result.pop("inbound_token_hash", None)
            result.pop("records_key", None)
        return result

    def update_peer_records_key(self, device_id: str, records_key: str) -> None:
        self.validate_remote_records_key(records_key)
        key_id = self.records_key_id(records_key)
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT records_key_id FROM peer_devices WHERE device_id = ?",
                (device_id,),
            ).fetchone()
            if not row:
                raise ValueError("互联设备不存在")
            previous_id = str(row["records_key_id"] or "")
            connection.execute(
                "UPDATE peer_devices SET records_key = ?, records_key_id = ?, updated_at = ? WHERE device_id = ?",
                (records_key, key_id, utc_now(), device_id),
            )
        if not secrets.compare_digest(previous_id, key_id) and self.unlocked_peer_key(
            device_id, key_id
        ) is None:
            self.clear_unlocked_peer_key(device_id)

    def authenticate_peer(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        submitted = self.token_hash(token)
        for peer in self.peers(include_secrets=True):
            if secrets.compare_digest(submitted, peer["inbound_token_hash"]):
                self.mark_seen(peer["device_id"])
                peer.pop("access_token", None)
                peer.pop("inbound_token_hash", None)
                peer.pop("records_key", None)
                return peer
        return None

    def mark_seen(self, device_id: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE peer_devices SET last_seen_at = ? WHERE device_id = ?",
                (utc_now(), device_id),
            )

    def delete_peer(self, device_id: str) -> bool:
        peer = self.peer(device_id)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM peer_devices WHERE device_id = ?", (device_id,)
            )
        if cursor.rowcount:
            self.record_event(
                "peer_revoked",
                peer_id=device_id,
                peer_name=(peer or {}).get("name", ""),
            )
        return bool(cursor.rowcount)

    def record_event(self, event_type: str, **values: Any) -> None:
        with self._lock:
            self._revision += 1
            self._events.append(
                {
                    "revision": self._revision,
                    "type": event_type,
                    "created_at": utc_now(),
                    **values,
                }
            )

    def events_since(self, revision: int) -> tuple[int, list[dict[str, Any]]]:
        with self._lock:
            return self._revision, [dict(item) for item in self._events if item["revision"] > revision]
