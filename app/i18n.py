"""Locale-aware API error messages.

The backend historically raises Chinese ``HTTPException`` details directly.
This module keeps those messages as the source of truth and translates them
for clients that send ``Accept-Language: en``.
"""

from __future__ import annotations

import re

ENGLISH_ERRORS: dict[str, str] = {
    "8-step LoRA 加速模式固定使用 8 步": "8-step LoRA acceleration uses exactly 8 steps",
    "AGENT.md 暂不可用": "AGENT.md is temporarily unavailable",
    "Base URL 必须是有效的 HTTP(S) 地址": "Base URL must be a valid HTTP(S) address",
    "FL2VA 仅支持 1 张首帧，或首帧/尾帧两张图片": "FL2VA supports one first frame, or a first and last frame pair",
    "H3 NSFW 模式仅支持 Ref2VA FP8": "H3 NSFW mode only supports Ref2VA FP8",
    "H3 NSFW 模式仅限无痕模式": "H3 NSFW mode is only available in incognito mode",
    "H3 SA tau 范围为 0–4": "H3 SA tau must be between 0 and 4",
    "H3 SA 二阶段 denoise 范围为 0–1": "H3 SA stage-2 denoise must be between 0 and 1",
    "H3 SA 仅支持 FL2VA FP8 或 Ref2VA FP8": "H3 SA only supports FL2VA FP8 or Ref2VA FP8",
    "H3 SA 加速起止比例必须满足 0 ≤ start < end ≤ 1": "H3 SA acceleration must satisfy 0 ≤ start < end ≤ 1",
    "H3 SA 参数必须为有限数值": "H3 SA parameters must be finite numbers",
    "H3 SA 固定使用 8 步 LoRA 采样": "H3 SA uses exactly 8 LoRA sampling steps",
    "H3 SA 最小 token 数范围为 0–1048576": "H3 SA minimum tokens must be between 0 and 1048576",
    "H3 TTS 仅支持 0 至 3 段音频参考": "H3 TTS supports zero to three audio references",
    "H3 TTS 固定使用 32×32 画面尺寸": "H3 TTS uses a fixed 32×32 frame size",
    "H3 TTS 时长范围为 1–15 秒": "H3 TTS duration must be between 1 and 15 seconds",
    "H3 TTS 最多支持 3 段音频参考": "H3 TTS supports up to three audio references",
    "H3 TTS 模式仅支持 Ref2VA FP8": "H3 TTS mode only supports Ref2VA FP8",
    "H3 TTS 采样步数范围为 4–50": "H3 TTS steps must be between 4 and 50",
    "Music3 INT8 必须使用 Music3 执行方案": "Music3 INT8 requires the Music3 execution mode",
    "Music3 不使用参考素材": "Music3 does not use reference files",
    "Music3 固定使用 30 步": "Music3 uses exactly 30 steps",
    "Music3 执行方案仅支持 Music3 INT8": "The Music3 execution mode requires Music3 INT8",
    "Music3 时长范围为 1–300 秒": "Music3 duration must be between 1 and 300 seconds",
    "Ref2VA 最多支持 9 张图片、3 段视频和 3 段音频": "Ref2VA supports up to 9 images, 3 videos, and 3 audio files",
    "RunningHub 工作流参数定义不可用": "RunningHub workflow parameter definitions are unavailable",
    "RunningHub 工作流参数识别失败": "Could not identify the RunningHub workflow parameters",
    "RunningHub 工作流未返回参数定义": "The RunningHub workflow returned no parameter definitions",
    "RunningHub 端点工作流已关闭": "RunningHub endpoint workflows are disabled",
    "VDN-H3 仅支持 FL2VA FP8 或 Ref2VA FP8": "VDN-H3 only supports FL2VA FP8 or Ref2VA FP8",
    "VDN-H3 步数范围为 8–50": "VDN-H3 steps must be between 8 and 50",
    "reference_manifest 必须是数组": "reference_manifest must be an array",
    "reference_manifest 的每一项必须是对象": "Each reference_manifest item must be an object",
    "runninghub_parameters 必须是对象": "runninghub_parameters must be an object",
    "不支持的执行方案": "Unsupported execution mode",
    "互联设备不存在": "Paired device not found",
    "互联设备授权无效": "Invalid paired-device authorization",
    "仅已完成且存在产物的任务支持重命名": "Only completed tasks with outputs can be renamed",
    "任务不存在": "Task not found",
    "任务尚未完成": "The task has not finished",
    "任务已结束，无法取消": "The task has already ended and cannot be cancelled",
    "任务结束后才能重新生成": "Wait for the task to finish before regenerating",
    "共享产物已不存在": "The shared output no longer exists",
    "共享任务不存在": "Shared task not found",
    "共享素材不存在": "Shared asset not found",
    "内置预设不存在": "Built-in preset not found",
    "内置预设不能删除": "Built-in presets cannot be deleted",
    "内置预设仅允许修改生成区显示状态": "Only the composer visibility of a built-in preset can be changed",
    "内置预设无需同步": "Built-in presets do not need syncing",
    "加密产物文件已不存在": "The encrypted output file no longer exists",
    "加密产物格式无效": "Invalid encrypted output format",
    "加密素材不存在": "Encrypted asset not found",
    "原任务参考文件不完整": "The original task's reference files are incomplete",
    "原任务参考文件已不存在": "The original task's reference files no longer exist",
    "原任务参考文件路径无效": "The original task's reference file path is invalid",
    "原任务指定的推理节点不存在": "The original task's inference node no longer exists",
    "原任务指定节点的类型已变更": "The original task's node type has changed",
    "原任务的 RunningHub 工作流当前不可用": "The original task's RunningHub workflow is currently unavailable",
    "原任务目标节点不在工作流快照中": "The original task's target node is not in the workflow snapshot",
    "原任务绑定的 RunningHub 工作流已变更": "The RunningHub workflow bound to the original task has changed",
    "参数格式不正确": "Invalid parameter format",
    "参考素材不存在": "Reference file not found",
    "参考素材已不存在": "The reference file no longer exists",
    "双采工作流仅支持 Ref2VA FP8": "Dual sampling only supports Ref2VA FP8",
    "双采工作流时长范围为 1–15 秒": "Dual sampling duration must be between 1 and 15 seconds",
    "双采工作流最多支持 9 张图片参考": "Dual sampling supports up to 9 image references",
    "双采工作流采样步数范围为 4–50": "Dual sampling steps must be between 4 and 50",
    "双采工作流需要至少一张图片参考": "Dual sampling requires at least one image reference",
    "只有排队中的任务可以修改生成参数": "Only queued tasks can change generation parameters",
    "只能同步到工作流已配置的目标节点": "Sync only to the target nodes configured by the workflow",
    "同名文件已存在": "A file with the same name already exists",
    "图片超分预设需要一张图片": "The image upscale preset requires one image",
    "宽度和高度必须大于 0": "Width and height must be greater than 0",
    "宽高必须是 32 的倍数，且不低于 352×352": "Width and height must be multiples of 32 and at least 352×352",
    "工作流不存在": "Workflow not found",
    "工作流没有已同步且在线的 ComfyUI 节点": "The workflow has no synced online ComfyUI node",
    "工作流没有配置目标 ComfyUI 节点": "The workflow has no target ComfyUI node configured",
    "当前任务类型不支持生成后自动超分": "Automatic upscaling is not supported for this task type",
    "当前没有可用推理节点，请添加推理节点": "No inference node is available; add one first",
    "所属设备密钥已失效": "The device key is no longer valid",
    "所选节点尚未确认该工作流副本": "The selected node has not confirmed this workflow copy",
    "指定的推理节点不存在": "The specified inference node does not exist",
    "指定节点尚未同步该自定义工作流": "The selected node has not synced this custom workflow",
    "指定节点未包含在原工作流快照的目标节点中": "The selected node is not among the original workflow snapshot's target nodes",
    "授权码不正确": "Incorrect access code",
    "推理节点不存在": "Inference node not found",
    "提示词不能超过 12000 个字符": "Prompt cannot exceed 12,000 characters",
    "提示词优化的 H3 时长范围为 1–15 秒": "H3 prompt optimization duration must be between 1 and 15 seconds",
    "提示词至少需要 8 个字符": "Prompt must be at least 8 characters",
    "数字人模式仅支持 Ref2VA FP8": "Digital human mode only supports Ref2VA FP8",
    "数字人模式固定使用 20 步": "Digital human mode uses exactly 20 steps",
    "数字人模式需要上传 1 张人物图片和 1 段驱动音频": "Digital human mode requires one portrait and one driving audio file",
    "文件名不能为空": "File name cannot be empty",
    "文件名无有效字符": "File name contains no valid characters",
    "文件夹包含进行中任务，请先取消或等待任务结束": "The folder contains active tasks; cancel or wait for them first",
    "文件夹包含非本机创建的素材，无法删除": "The folder contains assets not created on this device and cannot be deleted",
    "文件被加密，请先输入所属设备密钥": "The file is encrypted; enter the owning device key first",
    "无效的 API Key": "Invalid API Key",
    "无权删除该共享任务": "You cannot delete this shared task",
    "无权操作该共享任务": "You cannot modify this shared task",
    "无痕任务不支持文件夹": "Incognito tasks do not support folders",
    "无痕模式授权已失效": "Incognito authorization has expired",
    "时长必须大于 0": "Duration must be greater than 0",
    "普通 H3 提示词优化的时长范围为 1–15 秒": "Standard H3 prompt optimization duration must be between 1 and 15 seconds",
    "本机互联功能未开启": "Device sharing is not enabled on this device",
    "本机互联密钥已失效": "The local pairing key has expired",
    "本机素材不存在": "Local asset not found",
    "歌词不能超过 12000 个字符": "Lyrics cannot exceed 12,000 characters",
    "步数必须大于 0": "Steps must be greater than 0",
    "生成产物不存在": "Generated output not found",
    "目标 ComfyUI 节点不能重复": "Target ComfyUI nodes cannot be duplicated",
    "素材数量与 reference_manifest 不一致": "Asset count does not match reference_manifest",
    "素材文件夹不存在": "Asset folder not found",
    "素材顺序或类型与 reference_manifest 不一致": "Asset order or type does not match reference_manifest",
    "结果文件已不存在": "The result file no longer exists",
    "自动调度已排除 RunningHub 节点，请手动选择 RunningHub 节点": "Auto scheduling excludes RunningHub nodes; select a RunningHub node manually",
    "自动超分参数无效": "Invalid automatic upscale parameters",
    "自动超分没有可用的 ComfyUI 节点": "Automatic upscale has no available ComfyUI node",
    "自动超分需要使用 ComfyUI 节点": "Automatic upscale requires a ComfyUI node",
    "自定义 ComfyUI 工作流不能提交到互联代理节点": "A custom ComfyUI workflow cannot be submitted to a paired proxy node",
    "自定义 ComfyUI 工作流需要 ComfyUI 节点": "A custom ComfyUI workflow requires a ComfyUI node",
    "自定义工作流不能用于超分任务": "A custom workflow cannot be used for upscaling",
    "自定义工作流暂不支持自动超分": "Custom workflows do not support automatic upscaling yet",
    "自定义工作流没有配置目标 ComfyUI 节点": "The custom workflow has no target ComfyUI node configured",
    "至少需要一份参考素材": "At least one reference file is required",
    "节点正在执行任务或存在定向排队任务": "The node is running a task or has a targeted queued task",
    "视频封面不存在": "Video cover not found",
    "视频超分预设需要一段视频": "The video upscale preset requires one video",
    "该工作流仅在私密模式中可用": "This workflow is only available in incognito mode",
    "该工作流仅能在私密模式中重新生成": "This workflow can only be regenerated in incognito mode",
    "该资产已删除": "This asset has been deleted",
    "请先取消任务，任务结束后再删除": "Cancel the task and wait for it to finish before deleting",
    "请先开启本机互联功能": "Enable device sharing first",
    "请选择与原任务工作流匹配的 RunningHub 节点": "Select a RunningHub node that matches the original task's workflow",
    "超分任务需要上传 1 张图片或 1 段视频": "Upscaling requires one image or one video",
    "超分任务需要使用 ComfyUI 节点": "Upscaling requires a ComfyUI node",
    "超分倍率必须为 2 或 4": "Upscale scale must be 2 or 4",
    "超分分类必须为 real、anime 或 3d": "Upscale category must be real, anime, or 3d",
    "远程代理节点不存在": "Remote proxy node not found",
    "远程代理节点标识缺失": "The remote proxy node identifier is missing",
    "远程代理记录已不存在": "The remote proxy record no longer exists",
    "远程任务无法取消": "A remote task cannot be cancelled",
    "远程记录密钥不匹配": "Remote records key does not match",
    "远端素材不存在": "Remote asset not found",
    "远端素材保持只读": "Remote assets are read-only",
    "远端设备未开启互联功能": "The remote device has not enabled sharing",
    "远端设备返回的互联信息无效": "The remote device returned invalid sharing information",
    "采样步数范围为 4–50": "Steps must be between 4 and 50",
    "随机种子超出范围": "Random seed is out of range",
}

DURATION_LABELS = {
    "Music3": "Music3",
    "H3 TTS": "H3 TTS",
    "双采工作流": "Dual sampling",
    "数字人模式": "Digital human mode",
    "普通 H3 提示词优化": "Standard H3 prompt optimization",
    "提示词优化": "Prompt optimization",
}

KIND_LABELS = {
    "image": "image",
    "video": "video",
    "audio": "audio",
    "file": "file",
}


def _kind(value: str) -> str:
    return KIND_LABELS.get(value, value)


def _translate_pattern(message: str) -> str | None:
    match = re.fullmatch(r"(.+) 时长范围为 1–([0-9.]+) 秒", message)
    if match:
        label = DURATION_LABELS.get(match.group(1), match.group(1))
        return f"{label} duration must be between 1 and {match.group(2)} seconds"
    match = re.fullmatch(r"不支持的素材类型：(.+)", message)
    if match:
        return f"Unsupported file type: {match.group(1)}"
    match = re.fullmatch(r"单个文件不能超过 ([0-9]+) MB", message)
    if match:
        return f"Each file must be at most {match.group(1)} MB"
    match = re.fullmatch(r"工作流没有配置第 ([0-9]+) 个 (\w+) 参考素材映射", message)
    if match:
        return f"The workflow has no reference mapping for {_kind(match.group(2))} #{match.group(1)}"
    match = re.fullmatch(r"提示词至少需要 ([0-9]+) 个字符", message)
    if match:
        return f"Prompt must be at least {match.group(1)} characters"
    match = re.fullmatch(r"无法读取媒体时长：(.+)", message)
    if match:
        return f"Could not read media duration: {match.group(1)}"
    match = re.fullmatch(r"无法读取远端素材：(.+)", message)
    if match:
        return f"Could not read the remote asset: {match.group(1)}"
    match = re.fullmatch(r"无法连接远端设备：(.+)", message)
    if match:
        return f"Could not connect to the remote device: {match.group(1)}"
    match = re.fullmatch(r"视频和音频素材时长必须为 1–15 秒：(.+)", message)
    if match:
        return f"Video and audio duration must be between 1 and 15 seconds: {match.group(1)}"
    match = re.fullmatch(r"请上传第 ([0-9]+) 个 (\w+) 参考素材", message)
    if match:
        return f"Upload reference {_kind(match.group(2))} #{match.group(1)}"
    match = re.fullmatch(r"远程产物下载失败：(.+)", message)
    if match:
        return f"Failed to download the remote output: {match.group(1)}"
    match = re.fullmatch(r"远程代理提交失败：(.+)", message)
    if match:
        return f"Remote proxy submission failed: {match.group(1)}"
    match = re.fullmatch(r"远程任务删除失败：(.+)", message)
    if match:
        return f"Failed to delete the remote task: {match.group(1)}"
    match = re.fullmatch(r"远程任务取消失败：(.+)", message)
    if match:
        return f"Failed to cancel the remote task: {match.group(1)}"
    return None


def wants_english(accept_language: str | None) -> bool:
    if not accept_language:
        return False
    for part in accept_language.split(","):
        language = part.split(";", 1)[0].strip().lower()
        if language.startswith("en"):
            return True
        if language.startswith("zh"):
            return False
    return False


def translate_api_detail(message: str, accept_language: str | None = None) -> str:
    if not wants_english(accept_language):
        return message
    translated = ENGLISH_ERRORS.get(message)
    if translated:
        return translated
    return _translate_pattern(message) or message
