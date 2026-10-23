from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote

import httpx

from .jobs import utc_now
from .nodes import ComfyNodeConfig


PRESETS: tuple[dict[str, Any], ...] = (
    {"id": "preset-fl2va-native", "name": "普通流 · 原生 H3", "name_en": "Native H3", "description": "FL2VA 原生采样，适用于常规文生视频任务。", "description_en": "Native FL2VA sampling for standard text-to-video generation.", "model_variant": "fl2va-fp8", "execution_mode": "native", "workflow_file": "H3Studio_minimax_h3_fl2va_fp8_720p_15s_api.json"},
    {"id": "preset-fl2va-turbo", "name": "FL2VA · 8-step LoRA", "name_en": "FL2VA · 8-step LoRA", "description": "使用 8 步 LoRA 加速 FL2VA 视频生成。", "description_en": "Accelerated FL2VA video generation with an 8-step LoRA.", "model_variant": "fl2va-fp8", "execution_mode": "turbo-lora", "workflow_file": "H3Studio_minimax_h3_fl2va_fp8_turbo_lora_api.json"},
    {"id": "preset-ref2va-native", "name": "Ref2VA · 原生 H3", "name_en": "Ref2VA · Native H3", "description": "使用多模态参考素材进行原生 Ref2VA 视频生成。", "description_en": "Native Ref2VA video generation with multimodal references.", "model_variant": "ref2va-fp8", "execution_mode": "native", "workflow_file": "H3Studio_minimax_h3_ref2va_fp8_scaled_api.json"},
    {"id": "preset-ref2va-turbo", "name": "Ref2VA · 8-step LoRA", "name_en": "Ref2VA · 8-step LoRA", "description": "使用多模态参考素材和 8 步 LoRA 加速生成。", "description_en": "Accelerated multimodal Ref2VA generation with an 8-step LoRA.", "model_variant": "ref2va-fp8", "execution_mode": "turbo-lora", "workflow_file": "H3Studio_minimax_h3_ref2va_fp8_turbo_lora_api.json"},
    {"id": "preset-ref2va-dual", "name": "双采 · Sigma + 潜空间放大", "name_en": "Dual sampling · Sigma + latent upscale", "description": "采用 Sigma 双阶段采样并在潜空间放大画面。", "description_en": "Uses two-stage Sigma sampling with latent-space upscaling.", "model_variant": "ref2va-fp8", "execution_mode": "dual-sampling", "workflow_file": "H3Studio_minimax_h3_ref2va_fp8_dual_sampling_upscale_api.json"},
    {"id": "preset-fl2va-h3-sa", "name": "FL2VA · H3 SA", "name_en": "FL2VA · H3 SA", "description": "使用 Sol-Attn 加速参数执行 FL2VA 视频生成。", "description_en": "FL2VA video generation using Sol-Attn acceleration settings.", "model_variant": "fl2va-fp8", "execution_mode": "h3-sa", "workflow_file": "H3Studio_minimax_h3_fl2va_fp8_sa_api.json"},
    {"id": "preset-ref2va-h3-sa", "name": "Ref2VA · H3 SA", "name_en": "Ref2VA · H3 SA", "description": "使用参考素材和 Sol-Attn 加速参数执行生成。", "description_en": "Reference-guided generation using Sol-Attn acceleration settings.", "model_variant": "ref2va-fp8", "execution_mode": "h3-sa", "workflow_file": "H3Studio_minimax_h3_ref2va_fp8_sa_api.json"},
    {"id": "preset-fl2va-vdn", "name": "FL2VA · VDN-H3", "name_en": "FL2VA · VDN-H3", "description": "使用 Video Delta Net 采样器执行 FL2VA 视频生成。", "description_en": "FL2VA video generation using the Video Delta Net sampler.", "model_variant": "fl2va-fp8", "execution_mode": "vdn-h3", "workflow_file": "H3Studio_minimax_h3_fl2va_vdn_api.json"},
    {"id": "preset-ref2va-vdn", "name": "Ref2VA · VDN-H3", "name_en": "Ref2VA · VDN-H3", "description": "使用参考素材和 Video Delta Net 采样器执行生成。", "description_en": "Reference-guided generation using the Video Delta Net sampler.", "model_variant": "ref2va-fp8", "execution_mode": "vdn-h3", "workflow_file": "H3Studio_minimax_h3_ref2va_vdn_api.json"},
    {"id": "preset-ref2va-nsfw", "name": "H3 NSFW · NaughtyTimes LoRA", "name_en": "H3 NSFW · NaughtyTimes LoRA", "description": "使用 NaughtyTimes LoRA，仅在私密模式中显示和运行。", "description_en": "Uses the NaughtyTimes LoRA and runs only in private mode.", "model_variant": "ref2va-fp8", "execution_mode": "h3-nsfw", "workflow_file": "H3Studio_minimax_h3_ref2va_fp8_nsfw_lora_api.json", "visible": True, "incognito_only": True},
    {"id": "preset-digital-human", "name": "数字人 · 音频驱动", "name_en": "Digital human · Audio-driven", "description": "根据人物图像和驱动音频生成数字人视频。", "description_en": "Generates a digital-human video from a portrait and driving audio.", "model_variant": "ref2va-fp8", "execution_mode": "digital-human", "workflow_file": "H3Studio_minimax_h3_ref2va_fp8_digital_human_api.json"},
    {"id": "preset-tts", "name": "H3 TTS · 人物语音", "name_en": "H3 TTS · Voice", "description": "根据文本生成 H3 人物语音音频。", "description_en": "Generates H3 character-voice audio from text.", "model_variant": "ref2va-fp8", "execution_mode": "tts", "workflow_file": "H3Studio_minimax_h3_ref2va_fp8_tts_api.json", "media_type": "audio"},
    {"id": "preset-music3", "name": "Music3 INT8", "name_en": "Music3 INT8", "description": "根据风格提示词和歌词生成 Music3 音频。", "description_en": "Generates Music3 audio from a style prompt and lyrics.", "model_variant": "music3-int8", "execution_mode": "music3", "workflow_file": "H3Studio_minimax_music3_int8_api.json", "media_type": "audio"},
    {"id": "preset-upscale-image", "name": "图片超分", "name_en": "Image upscale", "description": "提升输入图片的分辨率与细节。", "description_en": "Increases the resolution and detail of an input image.", "model_variant": "fl2va-fp8", "execution_mode": "native", "workflow_file": "H3Studio_comfy_upscale_image_api.json", "media_type": "image", "task_type": "upscale"},
    {"id": "preset-upscale-video", "name": "视频超分", "name_en": "Video upscale", "description": "提升输入视频的分辨率与画面细节。", "description_en": "Increases the resolution and visual detail of an input video.", "model_variant": "fl2va-fp8", "execution_mode": "native", "workflow_file": "H3Studio_comfy_upscale_video_api.json", "media_type": "video", "task_type": "upscale"},
)
FIELD_NAMES = {"prompt", "lyrics", "width", "height", "duration", "num_frames", "steps", "seed"}
MEDIA_TYPES = {"image", "video", "audio"}
REFERENCE_TYPES = MEDIA_TYPES
# Link-style reference inputs on conditioning nodes, e.g. "ref_images.ref_image_0".
# A mapping flagged with "slot": true targets one of these families, so the engine
# can create a fresh loader node and rewire the link for a variable number of files.
REFERENCE_SLOT_FAMILIES = {
    "ref_images": ("image", "ref_image"),
    "ref_videos": ("video", "ref_video"),
    "ref_audios": ("audio", "ref_audio"),
}

# Official H3 conditioning limits for one generation.
REFERENCE_LIMITS = {
    "image": 9,
    "video": 3,
    "audio": 3,
}
MAX_WORKFLOW_BYTES = 5 * 1024 * 1024


def serialize_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, separators=(",", ": "))


def workflow_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _has_link(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], int)


def validate_workflow_config(
    *,
    name: str,
    workflow_json: dict[str, Any],
    field_mappings: dict[str, dict[str, str]],
    reference_mappings: list[dict[str, Any]],
    static_inputs: dict[str, dict[str, Any]],
    result_node_id: str,
    media_type: str,
    description: str = "",
) -> dict[str, Any]:
    normalized_name = name.strip()
    if not 1 <= len(normalized_name) <= 120:
        raise ValueError("工作流名称长度必须为 1 至 120 个字符")
    if not isinstance(workflow_json, dict) or not workflow_json:
        raise ValueError("工作流 JSON 必须是非空 ComfyUI API 格式对象")
    try:
        encoded = serialize_json(workflow_json).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("工作流 JSON 包含无法保存的值") from exc
    if len(encoded) > MAX_WORKFLOW_BYTES:
        raise ValueError("工作流 JSON 不能超过 5 MB")
    for node_id, node in workflow_json.items():
        if not isinstance(node_id, str) or not isinstance(node, dict):
            raise ValueError("工作流节点格式无效")
        if not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs"), dict):
            raise ValueError(f"节点 {node_id} 缺少 class_type 或 inputs")

    if not isinstance(field_mappings, dict) or set(field_mappings) - FIELD_NAMES:
        raise ValueError("通用字段映射包含不支持的字段")
    occupied: set[tuple[str, str]] = set()

    def target(node_id: Any, input_name: Any) -> tuple[str, str]:
        key = (str(node_id or ""), str(input_name or ""))
        node = workflow_json.get(key[0])
        if not node or key[1] not in node["inputs"]:
            raise ValueError(f"节点输入不存在：{key[0]}.{key[1]}")
        if _has_link(node["inputs"][key[1]]):
            raise ValueError(f"不能覆盖已连接的节点输入：{key[0]}.{key[1]}")
        if key in occupied:
            raise ValueError(f"多个配置映射到同一节点输入：{key[0]}.{key[1]}")
        occupied.add(key)
        return key

    normalized_fields: dict[str, dict[str, str]] = {}
    for field_name, binding in field_mappings.items():
        if not isinstance(binding, dict):
            raise ValueError(f"字段映射格式无效：{field_name}")
        node_id, input_name = target(binding.get("node_id"), binding.get("input"))
        normalized_fields[field_name] = {"node_id": node_id, "input": input_name}

    if not isinstance(static_inputs, dict):
        raise ValueError("静态输入必须是节点 ID 到 inputs 的对象")
    normalized_static: dict[str, dict[str, Any]] = {}
    for node_id, inputs in static_inputs.items():
        node = workflow_json.get(str(node_id))
        if not node or not isinstance(inputs, dict):
            raise ValueError(f"静态输入节点无效：{node_id}")
        normalized_static[str(node_id)] = {}
        for input_name, value in inputs.items():
            target_node, target_input = target(node_id, input_name)
            normalized_static[target_node][target_input] = value

    if not isinstance(reference_mappings, list) or len(reference_mappings) > 45:
        raise ValueError("参考素材映射最多支持 45 项")
    normalized_references: list[dict[str, Any]] = []
    reference_keys: set[tuple[str, int]] = set()
    for mapping in reference_mappings:
        if not isinstance(mapping, dict):
            raise ValueError("参考素材映射格式无效")
        kind = str(mapping.get("type") or "")
        index = mapping.get("index")
        if kind not in REFERENCE_TYPES or not isinstance(index, int) or not 1 <= index <= 15:
            raise ValueError("参考素材映射需要 image、video 或 audio 类型及 1 至 15 的序号")
        reference_key = (kind, index)
        if reference_key in reference_keys:
            raise ValueError(f"参考素材映射重复：{kind} {index}")
        reference_keys.add(reference_key)
        if mapping.get("slot"):
            family = str(mapping.get("input") or "")
            if family not in REFERENCE_SLOT_FAMILIES:
                raise ValueError(f"参考素材槽位无效：{family}")
            slot_kind, _ = REFERENCE_SLOT_FAMILIES[family]
            if slot_kind != kind:
                raise ValueError(f"槽位 {family} 只接受 {slot_kind} 类型的参考素材")
            slot_node_id = str(mapping.get("node_id") or "")
            if not workflow_json.get(slot_node_id):
                raise ValueError(f"参考素材槽位节点不存在：{slot_node_id}")
            normalized_references.append({
                "type": kind,
                "index": index,
                "node_id": slot_node_id,
                "input": family,
                "slot": True,
                "required": bool(mapping.get("required", True)),
            })
            continue
        node_id, input_name = target(mapping.get("node_id"), mapping.get("input"))
        normalized_references.append({
            "type": kind,
            "index": index,
            "node_id": node_id,
            "input": input_name,
            "required": bool(mapping.get("required", True)),
        })
    for kind in REFERENCE_TYPES:
        indexes = sorted(index for reference_type, index in reference_keys if reference_type == kind)
        if indexes and indexes != list(range(1, indexes[-1] + 1)):
            raise ValueError(f"{kind} 参考素材映射序号必须从 1 连续递增")

    result_node = workflow_json.get(str(result_node_id))
    if not result_node:
        raise ValueError("结果节点不存在")
    if media_type not in MEDIA_TYPES:
        raise ValueError("结果媒体类型必须为 image、video 或 audio")
    if "filename_prefix" not in result_node["inputs"]:
        raise ValueError("结果节点需要包含 filename_prefix 输入")
    if _has_link(result_node["inputs"]["filename_prefix"]):
        raise ValueError("结果节点 filename_prefix 不能使用连接输入")
    if (str(result_node_id), "filename_prefix") in occupied:
        raise ValueError("filename_prefix 由系统生成，不能配置其他映射")

    return {
        "name": normalized_name,
        "description": str(description),
        "workflow_json": workflow_json,
        "field_mappings": normalized_fields,
        "reference_mappings": normalized_references,
        "static_inputs": normalized_static,
        "result_node_id": str(result_node_id),
        "media_type": media_type,
    }


class WorkflowRegistry:
    def __init__(self, database_path: Path, workflow_dir: Path):
        self.database_path = database_path
        self.workflow_dir = workflow_dir
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()
        self._seed_presets()

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
                CREATE TABLE IF NOT EXISTS workflow_configs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_en TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    description_en TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL CHECK (source IN ('preset', 'custom')),
                    incognito_only INTEGER NOT NULL DEFAULT 0 CHECK (incognito_only IN (0, 1)),
                    preset_key TEXT NOT NULL DEFAULT '',
                    model_variant TEXT NOT NULL DEFAULT '',
                    execution_mode TEXT NOT NULL DEFAULT '',
                    task_type TEXT NOT NULL DEFAULT 'generation',
                    workflow_json TEXT NOT NULL,
                    field_mappings TEXT NOT NULL DEFAULT '{}',
                    reference_mappings TEXT NOT NULL DEFAULT '[]',
                    static_inputs TEXT NOT NULL DEFAULT '{}',
                    result_node_id TEXT NOT NULL DEFAULT '',
                    media_type TEXT NOT NULL DEFAULT 'video',
                    target_node_ids TEXT NOT NULL DEFAULT '[]',
                    visible_in_composer INTEGER NOT NULL DEFAULT 1 CHECK (visible_in_composer IN (0, 1)),
                    version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_node_sync (
                    workflow_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    remote_filename TEXT NOT NULL DEFAULT '',
                    sha256 TEXT NOT NULL DEFAULT '',
                    synced_at TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (workflow_id, node_id)
                );
                CREATE INDEX IF NOT EXISTS workflow_configs_source_idx
                    ON workflow_configs (source, name);
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(workflow_configs)").fetchall()
            }
            if "description" not in columns:
                connection.execute("ALTER TABLE workflow_configs ADD COLUMN description TEXT NOT NULL DEFAULT ''")
            if "description_en" not in columns:
                connection.execute("ALTER TABLE workflow_configs ADD COLUMN description_en TEXT NOT NULL DEFAULT ''")
            if "incognito_only" not in columns:
                connection.execute(
                    "ALTER TABLE workflow_configs ADD COLUMN incognito_only INTEGER NOT NULL DEFAULT 0"
                )
                connection.execute(
                    "UPDATE workflow_configs SET incognito_only = 1, visible_in_composer = 1 "
                    "WHERE id = 'preset-ref2va-nsfw' AND source = 'preset'"
                )

    def _seed_presets(self) -> None:
        now = utc_now()
        with self._lock, self._connect() as connection:
            for preset in PRESETS:
                path = self.workflow_dir / preset["workflow_file"]
                try:
                    workflow = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    workflow = {}
                connection.execute(
                    "INSERT OR IGNORE INTO workflow_configs "
                    "(id, name, name_en, description, description_en, source, incognito_only, preset_key, model_variant, execution_mode, "
                    "task_type, workflow_json, field_mappings, reference_mappings, static_inputs, "
                    "result_node_id, media_type, target_node_ids, visible_in_composer, version, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, 'preset', ?, ?, ?, ?, ?, ?, '{}', '[]', '{}', '', ?, '[]', ?, 1, ?, ?)",
                    (
                        preset["id"],
                        preset["name"],
                        preset["name_en"],
                        preset.get("description", ""),
                        preset.get("description_en", ""),
                        int(preset.get("incognito_only", False)),
                        preset["id"],
                        preset["model_variant"],
                        preset["execution_mode"],
                        preset.get("task_type", "generation"),
                        serialize_json(workflow),
                        preset.get("media_type", "video"),
                        int(preset.get("visible", True)),
                        now,
                        now,
                    ),
                )
                connection.execute(
                    "UPDATE workflow_configs SET name = ?, name_en = ?, description = ?, description_en = ?, "
                    "incognito_only = ? WHERE id = ? AND source = 'preset'",
                    (
                        preset["name"],
                        preset["name_en"],
                        preset.get("description", ""),
                        preset.get("description_en", ""),
                        int(preset.get("incognito_only", False)),
                        preset["id"],
                    ),
                )
                # Older databases may have been seeded while a workflow file was
                # missing. Fill only empty preset graphs; never overwrite data.
                connection.execute(
                    "UPDATE workflow_configs SET workflow_json = ?, updated_at = ? "
                    "WHERE id = ? AND source = 'preset' AND (workflow_json = '' OR workflow_json = '{}')",
                    (serialize_json(workflow), now, preset["id"]),
                )

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        for key in ("workflow_json", "field_mappings", "reference_mappings", "static_inputs", "target_node_ids"):
            try:
                item[key] = json.loads(item[key])
            except (TypeError, json.JSONDecodeError):
                item[key] = {} if key in {"workflow_json", "field_mappings", "static_inputs"} else []
        item["visible_in_composer"] = bool(item["visible_in_composer"])
        item["incognito_only"] = bool(item.get("incognito_only", False))
        item["custom"] = item["source"] == "custom"
        return item

    def get(self, workflow_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM workflow_configs WHERE id = ?", (workflow_id,)).fetchone()
        return self._decode(row) if row else None

    def list(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM workflow_configs ORDER BY source, name COLLATE NOCASE, id"
            ).fetchall()
            sync_rows = connection.execute(
                "SELECT workflow_id, node_id, status, remote_filename, sha256, synced_at, error, updated_at "
                "FROM workflow_node_sync ORDER BY node_id"
            ).fetchall()
        sync_by_workflow: dict[str, list[dict[str, Any]]] = {}
        for sync in sync_rows:
            sync_by_workflow.setdefault(str(sync["workflow_id"]), []).append(dict(sync))
        result = []
        for row in rows:
            item = self._decode(row)
            item.pop("workflow_json", None)
            item["sync"] = sync_by_workflow.get(item["id"], [])
            result.append(item)
        return result

    def create(
        self,
        config: dict[str, Any],
        target_node_ids: list[str],
        visible: bool,
        *,
        incognito_only: bool = False,
    ) -> dict[str, Any]:
        workflow_id = f"wf-{secrets.token_hex(8)}"
        now = utc_now()
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO workflow_configs "
                "(id, name, description, source, incognito_only, workflow_json, field_mappings, reference_mappings, static_inputs, "
                "result_node_id, media_type, target_node_ids, visible_in_composer, created_at, updated_at) "
                "VALUES (?, ?, ?, 'custom', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    workflow_id,
                    config["name"],
                    config.get("description", ""),
                    int(incognito_only),
                    serialize_json(config["workflow_json"]),
                    serialize_json(config["field_mappings"]),
                    serialize_json(config["reference_mappings"]),
                    serialize_json(config["static_inputs"]),
                    config["result_node_id"],
                    config["media_type"],
                    serialize_json(target_node_ids),
                    int(visible),
                    now,
                    now,
                ),
            )
            for node_id in target_node_ids:
                connection.execute(
                    "INSERT INTO workflow_node_sync (workflow_id, node_id, status, updated_at) VALUES (?, ?, 'pending', ?)",
                    (workflow_id, node_id, now),
                )
        return self.get(workflow_id) or {}

    def update(self, workflow_id: str, config: dict[str, Any], target_node_ids: list[str], visible: bool) -> dict[str, Any] | None:
        now = utc_now()
        with self._lock, self._connect() as connection:
            current = connection.execute("SELECT source FROM workflow_configs WHERE id = ?", (workflow_id,)).fetchone()
            if not current:
                return None
            if current["source"] != "custom":
                raise ValueError("內置预设仅允许修改生成区显示状态")
            connection.execute(
                "UPDATE workflow_configs SET name = ?, workflow_json = ?, field_mappings = ?, "
                "description = ?, reference_mappings = ?, static_inputs = ?, result_node_id = ?, media_type = ?, "
                "target_node_ids = ?, visible_in_composer = ?, version = version + 1, updated_at = ? WHERE id = ?",
                (
                    config["name"],
                    serialize_json(config["workflow_json"]),
                    serialize_json(config["field_mappings"]),
                    config.get("description", ""),
                    serialize_json(config["reference_mappings"]),
                    serialize_json(config["static_inputs"]),
                    config["result_node_id"],
                    config["media_type"],
                    serialize_json(target_node_ids),
                    int(visible),
                    now,
                    workflow_id,
                ),
            )
            connection.execute("DELETE FROM workflow_node_sync WHERE workflow_id = ?", (workflow_id,))
            connection.executemany(
                "INSERT INTO workflow_node_sync (workflow_id, node_id, status, updated_at) VALUES (?, ?, 'pending', ?)",
                [(workflow_id, node_id, now) for node_id in target_node_ids],
            )
        return self.get(workflow_id)

    def set_preset_visibility(self, workflow_id: str, visible: bool) -> dict[str, Any] | None:
        now = utc_now()
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "UPDATE workflow_configs SET visible_in_composer = ?, updated_at = ? WHERE id = ? AND source = 'preset'",
                (int(visible), now, workflow_id),
            )
            if not cursor.rowcount:
                return None
        return self.get(workflow_id)

    def delete(self, workflow_id: str) -> bool:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT source FROM workflow_configs WHERE id = ?", (workflow_id,)).fetchone()
            if not row:
                return False
            if row["source"] != "custom":
                raise ValueError("内置预设不能删除")
            connection.execute("DELETE FROM workflow_node_sync WHERE workflow_id = ?", (workflow_id,))
            connection.execute("DELETE FROM workflow_configs WHERE id = ?", (workflow_id,))
        return True

    def preset_for(self, model_variant: str, execution_mode: str, task_type: str = "generation") -> dict[str, Any] | None:
        if task_type == "upscale":
            return None
        preset = next((item for item in PRESETS if item.get("model_variant") == model_variant and item.get("execution_mode") == execution_mode and item.get("task_type", "generation") == "generation"), None)
        return self.get(preset["id"]) if preset else None

    def set_sync(self, workflow_id: str, node_id: str, *, status: str, remote_filename: str = "", sha256: str = "", error: str = "", synced_at: str | None = None) -> dict[str, Any]:
        now = utc_now()
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO workflow_node_sync (workflow_id, node_id, status, remote_filename, sha256, synced_at, error, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(workflow_id, node_id) DO UPDATE SET "
                "status = excluded.status, remote_filename = excluded.remote_filename, sha256 = excluded.sha256, "
                "synced_at = excluded.synced_at, error = excluded.error, updated_at = excluded.updated_at",
                (workflow_id, node_id, status, remote_filename, sha256, synced_at or "", error[:500], now),
            )
        return {"workflow_id": workflow_id, "node_id": node_id, "status": status, "remote_filename": remote_filename, "sha256": sha256, "synced_at": synced_at or "", "error": error[:500], "updated_at": now}

    def invalidate_node_sync(self, node_id: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE workflow_node_sync SET status = 'pending', synced_at = '', error = '推理节点配置已变更', updated_at = ? WHERE node_id = ?",
                (utc_now(), node_id),
            )

    def sync_rows(self, workflow_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT workflow_id, node_id, status, remote_filename, sha256, synced_at, error, updated_at "
                "FROM workflow_node_sync WHERE workflow_id = ? ORDER BY node_id",
                (workflow_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def remote_filename(workflow_id: str) -> str:
        if not re.fullmatch(r"wf-[a-f0-9]{16}", workflow_id):
            raise ValueError("自定义工作流 ID 格式无效")
        return f"H3Studio_{workflow_id}.json"

    @staticmethod
    def workflow_bytes(workflow: dict[str, Any]) -> bytes:
        return serialize_json(workflow["workflow_json"]).encode("utf-8")

    def synchronize(self, workflow_id: str, node: ComfyNodeConfig, *, confirm: bool = False) -> dict[str, Any]:
        workflow = self.get(workflow_id)
        if not workflow or workflow["source"] != "custom":
            raise ValueError("仅支持同步自定义工作流")
        if node.provider != "comfyui":
            raise ValueError("自定义 ComfyUI 工作流不能同步到 RunningHub 节点")
        remote_filename = self.remote_filename(workflow_id)
        relative_path = f"workflows/{remote_filename}"
        # ComfyUI 的 /userdata/{file} 只匹配单个路径段，目录分隔符必须编码成 %2F 才能写到
        # user/.../workflows/ 下；直接带斜杠会得到 405（POST）或 404（GET）。
        url = f"{node.url.rstrip('/')}/userdata/{quote(relative_path, safe='')}"
        expected = self.workflow_bytes(workflow)
        digest = workflow_digest(expected)
        headers = {"Authorization": f"Bearer {node.api_key}"} if node.api_key else {}
        timeout = httpx.Timeout(30, connect=10)
        try:
            with httpx.Client(headers=headers, timeout=timeout, trust_env=False, follow_redirects=False) as client:
                if not confirm:
                    response = client.post(f"{url}?overwrite=true", content=expected, headers={**headers, "Content-Type": "application/json"})
                    response.raise_for_status()
                response = client.get(url)
                response.raise_for_status()
                actual = response.content
            if workflow_digest(actual) != digest:
                raise ValueError("ComfyUI 服务器副本校验失败，内容哈希不一致")
            return self.set_sync(workflow_id, node.id, status="synced", remote_filename=relative_path, sha256=digest, synced_at=utc_now())
        except (httpx.HTTPError, OSError, ValueError) as exc:
            return self.set_sync(workflow_id, node.id, status="failed", remote_filename=relative_path, sha256=digest, error=str(exc))

    def remove_remote_copy(self, workflow_id: str, node: ComfyNodeConfig) -> str | None:
        filename = self.remote_filename(workflow_id)
        relative_path = f"workflows/{filename}"
        url = f"{node.url.rstrip('/')}/userdata/{quote(relative_path, safe='')}"
        headers = {"Authorization": f"Bearer {node.api_key}"} if node.api_key else {}
        try:
            with httpx.Client(headers=headers, timeout=httpx.Timeout(20, connect=8), trust_env=False, follow_redirects=False) as client:
                response = client.delete(url)
                if response.status_code not in {200, 204, 404}:
                    response.raise_for_status()
            return None
        except (httpx.HTTPError, OSError) as exc:
            return str(exc)[:500]


def eligible_node_ids(workflow: dict[str, Any], nodes: list[dict[str, Any]], sync_rows: list[dict[str, Any]]) -> list[str]:
    synced = {str(item["node_id"]) for item in sync_rows if item.get("status") == "synced"}
    if workflow["source"] == "preset":
        return [str(item["id"]) for item in nodes if item.get("provider") == "comfyui" and item.get("healthy")]
    configured = {str(node_id) for node_id in workflow.get("target_node_ids", [])}
    return [str(item["id"]) for item in nodes if str(item.get("id")) in configured & synced and item.get("provider") == "comfyui" and item.get("healthy")]

