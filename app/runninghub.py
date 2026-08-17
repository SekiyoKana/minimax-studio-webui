from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any


MEDIA_TYPES = {
    "IMAGE": "image",
    "VIDEO": "video",
    "AUDIO": "audio",
    "FILE": "file",
}
MODEL_FIELD_NAMES = {
    "ckpt_name",
    "checkpoint",
    "checkpoint_name",
    "clip_name",
    "lora",
    "lora_name",
    "model",
    "model_name",
    "unet",
    "unet_name",
    "vae",
    "vae_name",
}
MODEL_FIELD_TYPES = {"CHECKPOINT", "CLIP", "LORA", "MODEL", "UNET", "VAE"}


def _json_data(value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _number(value: Any) -> int | float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return number


def _boolean(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _field_type(value: Any, fallback: Any = None) -> str:
    raw = str(value or fallback or "STRING").upper()
    aliases = {
        "BOOL": "BOOLEAN",
        "BOOLEAN": "BOOLEAN",
        "DOUBLE": "FLOAT",
        "NUMBER": "FLOAT",
        "INT": "INTEGER",
        "LONG": "INTEGER",
        "COMBO": "LIST",
        "SELECT": "LIST",
        "TEXT": "STRING",
        "IMAGEUPLOAD": "IMAGE",
        "VIDEOUPLOAD": "VIDEO",
        "AUDIOUPLOAD": "AUDIO",
        "FILEUPLOAD": "FILE",
        "DOCUMENT": "FILE",
    }
    return aliases.get(raw, raw)


def _options(field_data: Any) -> tuple[list[dict[str, str]], dict[str, Any]]:
    parsed = _json_data(field_data)
    metadata: dict[str, Any] = {}
    source: Any = None
    if (
        isinstance(parsed, list)
        and len(parsed) >= 2
        and isinstance(parsed[0], str)
        and isinstance(parsed[1], dict)
    ):
        metadata = dict(parsed[1])
        source = metadata.get("options")
    elif isinstance(parsed, list) and all(isinstance(item, dict) for item in parsed):
        source = parsed
    elif isinstance(parsed, dict):
        metadata = dict(parsed)
        source = metadata.get("options")
    elif isinstance(parsed, list) and all(
        isinstance(item, (str, int, float, bool)) for item in parsed
    ):
        source = parsed
    options = []
    if isinstance(source, list):
        for item in source:
            if isinstance(item, dict):
                if "default" in item and "index" not in item and "name" not in item:
                    metadata.setdefault("default", item.get("default"))
                    continue
                value = item.get("index", item.get("value", item.get("name")))
                if value is None:
                    continue
                options.append(
                    {
                        "value": str(value),
                        "label": str(item.get("name") or value),
                        "description": str(item.get("description") or ""),
                    }
                )
            else:
                options.append(
                    {"value": str(item), "label": str(item), "description": ""}
                )
    return options, metadata


def _primary_text_key(fields: list[dict[str, Any]]) -> str:
    best_key = ""
    best_score = 0
    for field in fields:
        if field.get("field_type") != "STRING" or not field.get("editable", True):
            continue
        text = " ".join(
            str(field.get(name) or "").lower()
            for name in ("field_name", "label", "label_en", "node_name")
        )
        score = 0
        if field.get("multiline"):
            score += 2
        if re.search(r"prompt|text|description|caption|lyrics|提示词|文本|描述|歌词", text):
            score += 8
        if str(field.get("field_name") or "").lower() in {"prompt", "text", "value"}:
            score += 3
        if score > best_score:
            best_key = str(field["key"])
            best_score = score
    return best_key


def _is_model_field(
    field_name: str,
    field_type: str,
    node_name: str,
    label: str,
    media_kind: str | None,
) -> bool:
    normalized_name = field_name.lower()
    if field_type in MODEL_FIELD_TYPES or normalized_name in MODEL_FIELD_NAMES:
        return True
    if normalized_name.endswith("_name") and media_kind is None:
        return normalized_name not in {"sampler_name", "scheduler_name"}
    text = f"{field_name} {node_name} {label}".lower()
    return bool(
        re.search(
            r"checkpoint|ckpt|diffusion model|lora|text encoder|unet|vae|模型|检查点",
            text,
        )
    )


def _output_types(labels: list[str]) -> list[str]:
    text = " ".join(labels).lower()
    if re.search(r"video|视频|animation|动画", text):
        return ["video"]
    if re.search(r"audio|music|speech|voice|音频|音乐|语音|声音", text):
        return ["audio"]
    if re.search(r"image|photo|picture|图像|图片|绘图", text):
        return ["image"]
    return ["file"]


def _schema(
    *,
    resource_type: str,
    resource_id: str,
    resource_url: str,
    name: str,
    fields: list[dict[str, Any]],
    output_types: list[str],
    source: str,
    submit_path: str,
) -> dict[str, Any]:
    return {
        "version": 1,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "resource_url": resource_url,
        "name": name,
        "fields": fields,
        "primary_text_key": _primary_text_key(fields),
        "output_types": output_types or ["file"],
        "source": source,
        "submit_path": submit_path,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def build_ai_app_schema(
    resource_id: str,
    resource_url: str,
    demo_data: dict[str, Any] | None,
    detail_data: dict[str, Any] | None,
) -> dict[str, Any]:
    demo_data = demo_data or {}
    detail_data = detail_data or {}
    items = demo_data.get("nodeInfoList") or detail_data.get("inputNodes") or []
    if not isinstance(items, list) or not items:
        raise RuntimeError("RunningHub AI 应用未返回输入参数定义")
    fields = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("nodeId") or "")
        field_name = str(item.get("fieldName") or "")
        if not node_id or not field_name:
            continue
        parsed_data = _json_data(item.get("fieldData"))
        native_type = parsed_data[0] if isinstance(parsed_data, list) and parsed_data else None
        field_type = _field_type(item.get("fieldType"), native_type)
        options, metadata = _options(item.get("fieldData"))
        if field_type == "STRING" and options:
            field_type = "LIST"
        default = item.get("fieldValue")
        if default is None and "default" in metadata:
            default = metadata["default"]
        media_kind = MEDIA_TYPES.get(field_type)
        label = str(
            item.get("descriptionCn")
            or item.get("description")
            or item.get("descriptionEn")
            or f"{node_id}.{field_name}"
        )
        node_name = str(item.get("nodeName") or "")
        fields.append(
            {
                "key": f"{node_id}.{field_name}",
                "order": index,
                "node_id": node_id,
                "node_name": node_name,
                "field_name": field_name,
                "field_type": field_type,
                "label": label,
                "label_en": str(item.get("descriptionEn") or label),
                "default": default,
                "options": options,
                "min": _number(metadata.get("min")),
                "max": _number(metadata.get("max")),
                "step": _number(metadata.get("step")),
                "multiline": _boolean(metadata.get("multiline")),
                "media_kind": media_kind,
                "editable": not _is_model_field(
                    field_name,
                    field_type,
                    node_name,
                    label,
                    media_kind,
                ),
                "required": _boolean(
                    item.get("required")
                    if item.get("required") is not None
                    else metadata.get("required")
                ),
            }
        )
    if not fields:
        raise RuntimeError("RunningHub AI 应用参数定义为空")

    name = str(
        demo_data.get("webappName")
        or detail_data.get("webappName")
        or detail_data.get("name")
        or detail_data.get("title")
        or f"RunningHub AI App {resource_id}"
    )
    labels = [name]
    for tag in detail_data.get("tags") or []:
        if isinstance(tag, dict):
            labels.extend(str(tag.get(key) or "") for key in ("name", "nameEn"))
    for source in (demo_data, detail_data):
        for key in (
            "outputNodes",
            "outputs",
            "outputType",
            "outputTypes",
            "resultNodes",
            "resultTypes",
        ):
            value = source.get(key)
            if value is not None:
                labels.append(
                    json.dumps(value, ensure_ascii=False)
                    if isinstance(value, (dict, list))
                    else str(value)
                )
    curl_example = str(demo_data.get("curl") or "")
    path_match = re.search(r"https?://[^/'\"\s]+(?P<path>/[^'\"\s]+)", curl_example)
    submit_path = (
        path_match.group("path") if path_match else "/task/openapi/ai-app/run"
    )
    return _schema(
        resource_type="ai-app",
        resource_id=resource_id,
        resource_url=resource_url,
        name=name,
        fields=fields,
        output_types=_output_types(labels),
        source="api-call-demo" if demo_data.get("nodeInfoList") else "webapp-detail",
        submit_path=submit_path,
    )


def _is_connection(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], int)
    )


def _workflow_field_type(class_type: str, field_name: str, value: Any) -> str:
    text = f"{class_type} {field_name}".lower()
    if "loadimage" in text and field_name.lower() in {"image", "url"}:
        return "IMAGE"
    if "loadvideo" in text and field_name.lower() in {"video", "url"}:
        return "VIDEO"
    if "loadaudio" in text and field_name.lower() in {"audio", "url"}:
        return "AUDIO"
    if "load" in text and field_name.lower() in {"file", "filename", "path"}:
        return "FILE"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "INTEGER"
    if isinstance(value, float):
        return "FLOAT"
    return "STRING"


def build_workflow_schema(
    resource_id: str,
    resource_url: str,
    workflow: dict[str, Any],
    name: str = "",
) -> dict[str, Any]:
    fields = []
    output_labels = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        class_type = str(node.get("class_type") or "")
        meta = node.get("_meta") if isinstance(node.get("_meta"), dict) else {}
        node_name = str(meta.get("title") or class_type or node_id)
        class_text = f"{class_type} {node_name}".lower()
        if re.search(r"save.*video|video.*combine|saveanimated|savewebm", class_text):
            output_labels.append("video")
        if re.search(r"save.*audio|audio.*save", class_text):
            output_labels.append("audio")
        if re.search(r"save.*image|previewimage", class_text):
            output_labels.append("image")
        inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
        for field_name, value in inputs.items():
            if _is_connection(value) or isinstance(value, (dict, list)):
                continue
            field_type = _workflow_field_type(class_type, str(field_name), value)
            media_kind = MEDIA_TYPES.get(field_type)
            normalized_name = str(field_name).lower()
            editable = not (
                normalized_name in MODEL_FIELD_NAMES
                or (
                    normalized_name.endswith("_name")
                    and media_kind is None
                    and "sampler" not in normalized_name
                    and "scheduler" not in normalized_name
                )
            )
            fields.append(
                {
                    "key": f"{node_id}.{field_name}",
                    "order": len(fields),
                    "node_id": str(node_id),
                    "node_name": node_name,
                    "field_name": str(field_name),
                    "field_type": field_type,
                    "label": f"{node_name} · {field_name}",
                    "label_en": f"{node_name} · {field_name}",
                    "default": value,
                    "options": [],
                    "min": None,
                    "max": None,
                    "step": 1 if field_type == "INTEGER" else None,
                    "multiline": field_type == "STRING" and normalized_name in {"text", "prompt", "lyrics"},
                    "media_kind": media_kind,
                    "editable": editable,
                    "required": False,
                }
            )
    if not fields:
        raise RuntimeError("RunningHub 工作流未包含可识别的输入参数")
    output_types = list(dict.fromkeys(output_labels)) or ["file"]
    return _schema(
        resource_type="workflow",
        resource_id=resource_id,
        resource_url=resource_url,
        name=name or f"RunningHub Workflow {resource_id}",
        fields=fields,
        output_types=output_types,
        source="workflow-api-format",
        submit_path="/task/openapi/create",
    )


def default_parameters(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        str(field["key"]): field.get("default")
        for field in schema.get("fields") or []
        if field.get("editable", True) and not field.get("media_kind")
    }


def normalize_parameters(
    schema: dict[str, Any], values: dict[str, Any] | None
) -> dict[str, Any]:
    if values is None:
        values = {}
    if not isinstance(values, dict):
        raise ValueError("RunningHub 参数必须是对象")
    fields = {
        str(field.get("key")): field
        for field in schema.get("fields") or []
        if field.get("editable", True) and not field.get("media_kind")
    }
    unknown = sorted(set(values).difference(fields))
    if unknown:
        raise ValueError("RunningHub 参数不存在：" + ", ".join(unknown[:8]))
    result = default_parameters(schema)
    for key, value in values.items():
        field = fields[key]
        field_type = field.get("field_type")
        if field_type == "BOOLEAN":
            if isinstance(value, str):
                value = value.strip().lower() in {"1", "true", "yes", "on"}
            else:
                value = bool(value)
        elif field_type == "INTEGER":
            value = int(value)
        elif field_type == "FLOAT":
            value = float(value)
        else:
            value = "" if value is None else str(value)
        options = field.get("options") or []
        if options and str(value) not in {str(item.get("value")) for item in options}:
            raise ValueError(f"RunningHub 参数 {key} 的取值无效")
        minimum = field.get("min")
        maximum = field.get("max")
        if isinstance(value, (int, float)):
            if minimum is not None and value < minimum:
                raise ValueError(f"RunningHub 参数 {key} 不能低于 {minimum}")
            if maximum is not None and value > maximum:
                raise ValueError(f"RunningHub 参数 {key} 不能高于 {maximum}")
        result[key] = value
    for key, field in fields.items():
        if not field.get("required"):
            continue
        value = result.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"RunningHub 参数 {key} 为必填项")
    return result


def assign_media_fields(
    schema: dict[str, Any], manifest: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    fields = {
        str(field.get("key")): field
        for field in schema.get("fields") or []
        if field.get("editable", True) and field.get("media_kind")
    }
    available: dict[str, list[str]] = {
        kind: [] for kind in set(MEDIA_TYPES.values())
    }
    for key, field in fields.items():
        available[str(field["media_kind"])].append(key)
    used = set()
    result = []
    for item in manifest:
        kind = str(item.get("type") or "")
        key = str(item.get("field_key") or "")
        if key:
            field = fields.get(key)
            if not field or field.get("media_kind") != kind:
                raise ValueError(f"RunningHub 素材字段无效：{key}")
        else:
            key = next((candidate for candidate in available.get(kind, []) if candidate not in used), "")
        if not key:
            raise ValueError(f"RunningHub 工作流没有可用的{kind}输入字段")
        if key in used:
            raise ValueError(f"RunningHub 素材字段重复：{key}")
        used.add(key)
        result.append({**item, "field_key": key})
    missing = next(
        (
            key
            for key, field in fields.items()
            if field.get("required") and key not in used
        ),
        "",
    )
    if missing:
        raise ValueError(f"RunningHub 素材字段 {missing} 为必填项")
    return result


def node_info_list(
    schema: dict[str, Any],
    parameters: dict[str, Any],
    manifest: list[dict[str, Any]],
    uploaded_names: list[str],
) -> list[dict[str, Any]]:
    if len(manifest) != len(uploaded_names):
        raise ValueError("RunningHub 素材清单与上传结果不一致")
    uploaded = {
        str(item.get("field_key")): name
        for item, name in zip(manifest, uploaded_names, strict=True)
    }
    result = []
    resource_type = schema.get("resource_type")
    for field in schema.get("fields") or []:
        key = str(field.get("key") or "")
        value: Any
        if field.get("media_kind"):
            if key not in uploaded:
                continue
            value = uploaded[key]
        elif field.get("editable", True):
            if key not in parameters:
                continue
            value = parameters[key]
        elif resource_type == "ai-app":
            value = field.get("default")
            if value is None:
                continue
        else:
            continue
        result.append(
            {
                "nodeId": str(field.get("node_id") or ""),
                "fieldName": str(field.get("field_name") or ""),
                "fieldValue": value,
                "description": field.get("label") or None,
            }
        )
    return result


def output_media_type(schema: dict[str, Any]) -> str:
    output_types = schema.get("output_types") or []
    media_type = str(output_types[0]) if output_types else "file"
    return media_type if media_type in {"audio", "video", "image", "file"} else "file"
