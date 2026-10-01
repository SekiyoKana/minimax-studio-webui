from __future__ import annotations

import json
import re
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .jobs import utc_now


@dataclass(frozen=True)
class DefaultWorkflowSpec:
    id: str
    name: str
    description: str
    path: Path
    model_variant: str
    execution_mode: str
    task_type: str = "generation"
    media_type: str = "video"


def default_workflow_specs(settings: Any) -> tuple[DefaultWorkflowSpec, ...]:
    return (
        DefaultWorkflowSpec(
            "builtin:fl2va-native",
            "H3 FL2VA FP8 · 原生",
            "MiniMax H3 FL2VA 原生 API 工作流",
            settings.comfy_workflow,
            "fl2va-fp8",
            "native",
        ),
        DefaultWorkflowSpec(
            "builtin:ref2va-native",
            "H3 Ref2VA FP8 · 原生",
            "MiniMax H3 Ref2VA 原生 API 工作流",
            settings.comfy_ref2va_workflow,
            "ref2va-fp8",
            "native",
        ),
        DefaultWorkflowSpec(
            "builtin:fl2va-turbo-lora",
            "H3 FL2VA · 8-step LoRA",
            "MiniMax H3 FL2VA 8-step LoRA API 工作流",
            settings.comfy_turbo_workflow,
            "fl2va-fp8",
            "turbo-lora",
        ),
        DefaultWorkflowSpec(
            "builtin:ref2va-turbo-lora",
            "H3 Ref2VA · 8-step LoRA",
            "MiniMax H3 Ref2VA 8-step LoRA API 工作流",
            settings.comfy_ref2va_turbo_workflow,
            "ref2va-fp8",
            "turbo-lora",
        ),
        DefaultWorkflowSpec(
            "builtin:ref2va-dual-sampling",
            "H3 Ref2VA · 双采放大",
            "MiniMax H3 Ref2VA 双采样与潜空间放大 API 工作流",
            settings.comfy_dual_sampling_workflow,
            "ref2va-fp8",
            "dual-sampling",
        ),
        DefaultWorkflowSpec(
            "builtin:fl2va-h3-sa",
            "H3 FL2VA · H3 SA",
            "MiniMax H3 FL2VA Sol-Attn API 工作流",
            settings.comfy_sa_workflow,
            "fl2va-fp8",
            "h3-sa",
        ),
        DefaultWorkflowSpec(
            "builtin:ref2va-h3-sa",
            "H3 Ref2VA · H3 SA",
            "MiniMax H3 Ref2VA Sol-Attn API 工作流",
            settings.comfy_ref2va_sa_workflow,
            "ref2va-fp8",
            "h3-sa",
        ),
        DefaultWorkflowSpec(
            "builtin:fl2va-vdn-h3",
            "H3 FL2VA · VDN-H3",
            "MiniMax H3 FL2VA VDN-H3 API 工作流",
            settings.comfy_vdn_workflow,
            "fl2va-fp8",
            "vdn-h3",
        ),
        DefaultWorkflowSpec(
            "builtin:ref2va-vdn-h3",
            "H3 Ref2VA · VDN-H3",
            "MiniMax H3 Ref2VA VDN-H3 API 工作流",
            settings.comfy_ref2va_vdn_workflow,
            "ref2va-fp8",
            "vdn-h3",
        ),
        DefaultWorkflowSpec(
            "builtin:ref2va-nsfw",
            "H3 Ref2VA · NSFW LoRA",
            "MiniMax H3 Ref2VA NaughtyTimes LoRA API 工作流",
            settings.comfy_nsfw_workflow,
            "ref2va-fp8",
            "h3-nsfw",
        ),
        DefaultWorkflowSpec(
            "builtin:ref2va-digital-human",
            "H3 Ref2VA · 数字人",
            "MiniMax H3 音频驱动数字人 API 工作流",
            settings.comfy_digital_human_workflow,
            "ref2va-fp8",
            "digital-human",
        ),
        DefaultWorkflowSpec(
            "builtin:ref2va-tts",
            "H3 Ref2VA · TTS",
            "MiniMax H3 TTS API 工作流",
            settings.comfy_tts_workflow,
            "ref2va-fp8",
            "tts",
            media_type="audio",
        ),
        DefaultWorkflowSpec(
            "builtin:music3",
            "Music3 INT8",
            "MiniMax Music3 INT8 API 工作流",
            settings.comfy_music3_workflow,
            "music3-int8",
            "music3",
            media_type="audio",
        ),
        DefaultWorkflowSpec(
            "builtin:upscale-image",
            "图像超分",
            "ComfyUI 图像超分 API 工作流",
            settings.comfy_upscale_image_workflow,
            "",
            "upscale",
            "upscale",
            "image",
        ),
        DefaultWorkflowSpec(
            "builtin:upscale-video",
            "视频超分",
            "ComfyUI 视频超分 API 工作流",
            settings.comfy_upscale_video_workflow,
            "",
            "upscale",
            "upscale",
            "video",
        ),
    )


WORKFLOW_MEDIA_TYPES = {"video", "audio", "image", "file"}


def infer_media_type(workflow: dict[str, Any], task_type: str = "generation") -> str:
    """Infer the artifact type from common ComfyUI output node classes."""
    classes = {
        str(node.get("class_type") or "").lower()
        for node in workflow.values()
        if isinstance(node, dict)
    }
    if any("saveaudio" in value or value in {"audiowriter", "saveaudio"} for value in classes):
        return "audio"
    if any(
        "savevideo" in value
        or "videocombine" in value
        or value in {"createvideo", "saveanimatedmp4"}
        for value in classes
    ):
        return "video"
    if any(
        value in {"saveimage", "previewimage", "saveanimatedwebp", "saveanimatedpng"}
        or value.startswith("saveimage")
        for value in classes
    ):
        return "image"
    return "image" if task_type == "upscale" else "video"


def validate_api_workflow(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise ValueError("工作流必须是非空的 ComfyUI API JSON 对象")
    normalized: dict[str, Any] = {}
    for raw_id, node in value.items():
        node_id = str(raw_id).strip()
        if not node_id:
            raise ValueError("ComfyUI API 工作流包含空节点 ID")
        if not isinstance(node, dict) or not isinstance(node.get("class_type"), str) or not node["class_type"].strip():
            raise ValueError(
                "工作流必须是 ComfyUI API 格式：每个节点都需要 class_type 和 inputs"
            )
        if "inputs" not in node or not isinstance(node["inputs"], dict):
            raise ValueError("工作流必须是 ComfyUI API 格式：节点 inputs 必须是对象")
        normalized[node_id] = deepcopy(node)
    return normalized


class WorkflowRegistry:
    """Persistent ComfyUI API workflow definitions shared by the UI and engine."""

    def __init__(self, database_path: Path, settings: Any | None = None):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize(settings)

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

    def _initialize(self, settings: Any | None) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS comfy_workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    workflow_json TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'imported',
                    is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
                    model_variant TEXT NOT NULL DEFAULT '',
                    execution_mode TEXT NOT NULL DEFAULT 'custom',
                    task_type TEXT NOT NULL DEFAULT 'generation',
                    media_type TEXT NOT NULL DEFAULT 'video',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(comfy_workflows)").fetchall()
            }
            if "media_type" not in columns:
                connection.execute(
                    "ALTER TABLE comfy_workflows ADD COLUMN media_type TEXT NOT NULL DEFAULT 'video'"
                )
        if settings is not None:
            self._seed_defaults(default_workflow_specs(settings))

    def _seed_defaults(self, specs: tuple[DefaultWorkflowSpec, ...]) -> None:
        now = utc_now()
        rows: list[tuple[Any, ...]] = []
        for spec in specs:
            if not spec.path.is_file():
                continue
            try:
                payload = validate_api_workflow(
                    json.loads(spec.path.read_text(encoding="utf-8"))
                )
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            rows.append(
                (
                    spec.id,
                    spec.name,
                    spec.description,
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    "builtin",
                    1,
                    spec.model_variant,
                    spec.execution_mode,
                    spec.task_type,
                    spec.media_type,
                    now,
                    now,
                )
            )
        if not rows:
            return
        with self._lock, self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO comfy_workflows
                (id, name, description, workflow_json, source, is_default,
                 model_variant, execution_mode, task_type, media_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    workflow_json = excluded.workflow_json,
                    source = excluded.source,
                    is_default = excluded.is_default,
                    model_variant = excluded.model_variant,
                    execution_mode = excluded.execution_mode,
                    task_type = excluded.task_type,
                    media_type = excluded.media_type,
                    updated_at = excluded.updated_at
                """,
                rows,
            )

    @staticmethod
    def _public(row: sqlite3.Row, *, include_workflow: bool = False) -> dict[str, Any]:
        value = {
            "id": str(row["id"]),
            "name": str(row["name"]),
            "description": str(row["description"] or ""),
            "source": str(row["source"] or "imported"),
            "is_default": bool(row["is_default"]),
            "model_variant": str(row["model_variant"] or ""),
            "execution_mode": str(row["execution_mode"] or "custom"),
            "task_type": str(row["task_type"] or "generation"),
            "media_type": str(row["media_type"] or "video"),
            "node_count": len(json.loads(str(row["workflow_json"]))),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }
        if include_workflow:
            value["workflow"] = json.loads(str(row["workflow_json"]))
        return value

    def list(self, *, include_workflow: bool = False) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM comfy_workflows ORDER BY is_default DESC, name COLLATE NOCASE, created_at"
            ).fetchall()
        return [self._public(row, include_workflow=include_workflow) for row in rows]

    def get(self, workflow_id: str, *, include_workflow: bool = True) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM comfy_workflows WHERE id = ?", (str(workflow_id),)
            ).fetchone()
        return self._public(row, include_workflow=include_workflow) if row else None

    def default_for(
        self,
        model_variant: str,
        execution_mode: str,
        task_type: str = "generation",
    ) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM comfy_workflows
                WHERE is_default = 1
                  AND (model_variant = ? OR (task_type = 'upscale' AND model_variant = ''))
                  AND execution_mode = ? AND task_type = ?
                ORDER BY created_at LIMIT 1
                """,
                (model_variant, execution_mode, task_type),
            ).fetchone()
        return self._public(row, include_workflow=False) if row else None

    def workflow_json(self, workflow_id: str) -> dict[str, Any] | None:
        item = self.get(workflow_id, include_workflow=True)
        return deepcopy(item["workflow"]) if item else None

    @staticmethod
    def _new_id(name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-").lower()
        return f"custom:{slug or 'workflow'}-{secrets.token_hex(4)}"

    def create(
        self,
        name: str,
        workflow: Any,
        *,
        description: str = "",
        model_variant: str = "",
        execution_mode: str = "custom",
        task_type: str = "generation",
        media_type: str | None = None,
        workflow_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_name = str(name or "").strip()
        if not 1 <= len(normalized_name) <= 120:
            raise ValueError("工作流名称长度必须为 1 至 120 个字符")
        normalized = validate_api_workflow(workflow)
        normalized_task_type = str(task_type or "").strip()
        if normalized_task_type not in {"generation", "upscale"}:
            raise ValueError("工作流任务类型只能是 generation 或 upscale")
        normalized_execution_mode = str(execution_mode or "").strip()
        if normalized_execution_mode == "" or len(normalized_execution_mode) > 80:
            raise ValueError("工作流执行方案无效")
        normalized_media_type = str(media_type or infer_media_type(normalized, normalized_task_type)).strip()
        if normalized_media_type not in WORKFLOW_MEDIA_TYPES:
            raise ValueError("工作流输出类型只能是 video、audio、image 或 file")
        identifier = str(workflow_id or self._new_id(normalized_name))
        if not re.fullmatch(r"[A-Za-z0-9:_-]{3,160}", identifier):
            raise ValueError("工作流 ID 格式无效")
        now = utc_now()
        with self._lock, self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO comfy_workflows
                    (id, name, description, workflow_json, source, is_default,
                     model_variant, execution_mode, task_type, media_type, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'imported', 0, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        identifier,
                        normalized_name,
                        str(description or "").strip()[:500],
                        json.dumps(normalized, ensure_ascii=False, separators=(",", ":")),
                        str(model_variant or "").strip(),
                        normalized_execution_mode,
                        normalized_task_type,
                        normalized_media_type,
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("工作流 ID 已存在") from exc
        return self.get(identifier, include_workflow=False) or {}

    def update(self, workflow_id: str, *, name: str, description: str = "") -> dict[str, Any]:
        item = self.get(workflow_id, include_workflow=False)
        if not item:
            raise KeyError(workflow_id)
        if item["is_default"]:
            raise ValueError("内置工作流只能使用，不能重命名")
        normalized_name = str(name or "").strip()
        if not 1 <= len(normalized_name) <= 120:
            raise ValueError("工作流名称长度必须为 1 至 120 个字符")
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE comfy_workflows SET name = ?, description = ?, updated_at = ? WHERE id = ?",
                (normalized_name, str(description or "").strip()[:500], utc_now(), workflow_id),
            )
        return self.get(workflow_id, include_workflow=False) or {}

    def delete(self, workflow_id: str) -> None:
        item = self.get(workflow_id, include_workflow=False)
        if not item:
            raise KeyError(workflow_id)
        if item["is_default"]:
            raise ValueError("内置工作流不能删除")
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM comfy_workflows WHERE id = ?", (workflow_id,))
