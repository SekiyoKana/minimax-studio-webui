const state = {
  references: [],
  assets: [],
  sharedAssets: [],
  assetPage: 0,
  assetPages: 1,
  assetPageSize: 16,
  assetTotal: 0,
  assetRevision: 0,
  assetLoading: false,
  assetHasMore: true,
  assetLoadError: "",
  sharedAssetErrors: [],
  assetDetailJob: null,
  localAssets: [],
  localAssetPage: 0,
  localAssetPages: 1,
  localAssetTotal: 0,
  localAssetLoading: false,
  localAssetSelected: new Set(),
  localAssetChanged: false,
  unlockOwnerDeviceId: "",
  aiConfig: { enabled: false, base_url: "", model: "", has_api_key: false },
  aiSaveTimer: null,
  peeringRevision: 0,
  peeringTimer: null,
  peeringPollTimer: null,
  peeringPolling: false,
  peering: null,
  conversations: [],
  conversationPage: 1,
  conversationPages: 1,
  conversationPageSize: 10,
  conversationRevision: 0,
  conversationRevisionSignature: "",
  conversationDeviceIds: new Set(),
  conversationFilterOpen: false,
  conversationLoading: false,
  conversationRefreshPending: false,
  conversationRefreshResetPending: false,
  conversationReady: false,
  conversationScrollTop: 0,
  editingJobId: null,
  lastRevision: "",
  storeRevision: 0,
  logFloor: 0,
  queue: [],
  nodes: [],
  managedNodes: [],
  nodeEditingId: null,
  runningHubSchemaKey: "",
  runningHubRenderSignature: "",
  runningHubResourceId: "",
  runningHubParameters: {},
  pendingRunningHubMediaField: "",
  logs: [],
  runtimeRevision: "",
  localRuntime: { logs: [], queue: [], nodes: [] },
  peerRuntime: {},
  generalSettings: { show_runtime_logs: true, show_peering: true, backup_outputs: false, remote_disconnect_policy: "encrypt" },
  conversationDevices: [],
  stream: null,
  incognito: false,
  incognitoCode: "",
  brandClicks: [],
  opsPosition: { x: 0, y: 0 },
  opsPositionInitialized: false,
  launcherPosition: { x: 0, y: 0 },
  launcherPositionInitialized: false,
  mentionIndex: -1,
  locale: localStorage.getItem("h3-locale") === "en" ? "en" : "zh-CN",
};

const el = (id) => document.getElementById(id);
const form = el("generationForm");
const promptInput = el("prompt");
const referenceInput = el("referenceInput");
const MUSIC3_DURATIONS = [30, 60, 120, 180, 240, 300];
const RUNNINGHUB_TARGET_PREFIX = "rh:";

const COPY = {
  "zh-CN": {
    assetLibrary: "素材库", assetSearch: "搜索素材", allStatuses: "全部状态", queued: "排队中", running: "生成中", completed: "已完成", failed: "失败", cancelled: "已取消",
    conversation: "H3 对话", switchLanguage: "Switch to English", apiDocs: "API 文档", newGeneration: "新建生成", close: "关闭", assets: "素材库",
    connectEngine: "连接推理节点", offline: "服务离线", autoSchedule: "自动调度", nodePending: "节点待分配", online: "在线", available: "可用", nodeOffline: "离线", disabled: "已停用", busy: "执行中",
    balance: "余额", credits: "点数", recentCost: "最近调用消耗", accountUnavailable: "账户信息不可用", workflowUnavailable: "工作流信息不可用", balancePending: "余额读取中", accountTasks: "账户任务", balanceUpdated: "余额更新", balanceFailed: "余额读取失败",
    noAssets: "暂无素材", loading: "加载中", allLoaded: "已加载全部", loadFailed: "加载失败", startCreating: "开始创作", you: "你",
    native: "普通流 · 原生 H3", turbo: "8-step LoRA · 强度 1.0", dualSampling: "双采 · Sigma + 潜空间放大", h3Sa: "MiniMax H3 SA · Sol-Attn", vdnH3: "VDN-H3 · Video Delta Net", digitalHuman: "数字人 · 音频驱动", tts: "H3 TTS · 人物语音", music3: "Music3 · 30 步", nsfw: "H3 NSFW · NaughtyTimes LoRA", speedCache: "Speed Cache（已停用）",
    reuse: "回填到发送区", useAsInput: "作为输入", regenerate: "重新生成", edit: "修改", cancel: "取消", delete: "删除", deleteRecord: "删除记录", downloadVideo: "下载视频", downloadAudio: "下载音频", downloadImage: "下载图片", downloadFile: "下载文件", videoReady: "视频已生成", musicReady: "音频已生成", imageReady: "图片已生成", fileReady: "文件已生成", peering: "多端互联", peerConnected: "已连接设备", peerRevoked: "已撤销设备访问", peerConnectNotice: "设备已完成互联", localPeerKey: "本机互联密钥",
    aiKeySaved: "API Key 已保存到本机数据库", aiKeyEmpty: "尚未保存 API Key", aiKeyReplace: "输入新值可覆盖已保存密钥", noPeers: "暂无已连接设备", revokeAccess: "撤销访问", owner: "归属方", pairingRefresh: "秒后刷新", connectPeer: "建立互联",
    assetDetail: "素材详情", prompt: "关键词与提示词", lyrics: "歌词", sourceFiles: "使用的文件", parameters: "生成参数", noSourceFiles: "未使用参考文件", outputUnavailable: "当前没有可预览的生成产物", assetDeleted: "该资产已删除", deviceFilter: "设备筛选",
    deleteConfirm: "删除后将同时清理任务记录、上传素材和生成产物，确认继续？", regenerateConfirm: "将使用本条任务的参数和参考文件创建新的生成任务，确认继续？", fillLoading: "正在读取原始文件", fillDone: "已回填到发送区", fileUnavailable: "参考文件已不存在，无法完整回填",
    overallTime: "总体耗时", steps: "步", seed: "seed", seconds: "秒", queuePosition: "队列位置", incognito: "无痕", destroy: "销毁",
  },
  en: {
    assetLibrary: "Assets", assetSearch: "Search assets", allStatuses: "All statuses", queued: "Queued", running: "Running", completed: "Completed", failed: "Failed", cancelled: "Cancelled",
    conversation: "H3 Chat", switchLanguage: "切换为中文", apiDocs: "API documentation", newGeneration: "New generation", close: "Close", assets: "Assets",
    connectEngine: "Connecting to inference nodes", offline: "Service offline", autoSchedule: "Auto", nodePending: "Awaiting node", online: "Online", available: "available", nodeOffline: "Offline", disabled: "Disabled", busy: "Running",
    balance: "Balance", credits: "credits", recentCost: "Recent call cost", accountUnavailable: "Account unavailable", workflowUnavailable: "Workflow information unavailable", balancePending: "Loading balance", accountTasks: "Account tasks", balanceUpdated: "balance updated", balanceFailed: "balance read failed",
    noAssets: "No assets", loading: "Loading", allLoaded: "All assets loaded", loadFailed: "Load failed", startCreating: "Start creating", you: "You",
    native: "Native H3", turbo: "8-step LoRA · 1.0", dualSampling: "Dual sampling · Sigma + latent upscale", h3Sa: "MiniMax H3 SA · Sol-Attn", vdnH3: "VDN-H3 · Video Delta Net", digitalHuman: "Digital human · audio driven", tts: "H3 TTS · Character voice", music3: "Music3 · 30 steps", nsfw: "H3 NSFW · NaughtyTimes LoRA", speedCache: "Speed Cache (disabled)",
    reuse: "Fill composer", useAsInput: "Use as input", regenerate: "Regenerate", edit: "Edit", cancel: "Cancel", delete: "Delete", deleteRecord: "Delete record", downloadVideo: "Download video", downloadAudio: "Download audio", downloadImage: "Download image", downloadFile: "Download file", videoReady: "Video generated", musicReady: "Audio generated", imageReady: "Image generated", fileReady: "File generated", peering: "Device sharing", peerConnected: "Connected device", peerRevoked: "Device access revoked", peerConnectNotice: "Device pairing completed", localPeerKey: "Local pairing key",
    aiKeySaved: "API Key saved in the local database", aiKeyEmpty: "No API Key saved", aiKeyReplace: "Enter a new value to replace the saved key", noPeers: "No connected devices", revokeAccess: "Revoke access", owner: "Owner", pairingRefresh: "s until refresh", connectPeer: "Connect",
    assetDetail: "Asset details", prompt: "Keywords and prompt", lyrics: "Lyrics", sourceFiles: "Source files", parameters: "Parameters", noSourceFiles: "No reference files", outputUnavailable: "No generated output is available for preview", assetDeleted: "This asset has been deleted", deviceFilter: "Device filter",
    deleteConfirm: "This removes the record, uploaded files, and generated output. Continue?", regenerateConfirm: "Create a new generation with this task's parameters and reference files?", fillLoading: "Loading source files", fillDone: "Filled into the composer", fileUnavailable: "A source file is unavailable and cannot be restored",
    overallTime: "Elapsed", steps: "steps", seed: "seed", seconds: "s", queuePosition: "Queue position", incognito: "Incognito", destroy: "expires",
  },
};

function t(key) {
  return COPY[state.locale]?.[key] || COPY["zh-CN"][key] || key;
}

function localized(zh, en) {
  return state.locale === "en" ? en : zh;
}

function setText(selector, value) {
  const target = document.querySelector(selector);
  if (target) target.textContent = value;
}

function setTitle(selector, value) {
  const target = document.querySelector(selector);
  if (!target) return;
  target.title = value;
  target.setAttribute("aria-label", value);
}

function setLeadingText(selector, value) {
  const matched = document.querySelector(selector);
  const target = matched?.matches("input, textarea, select") ? matched.parentElement : matched;
  const textNode = target ? Array.from(target.childNodes).find((node) => node.nodeType === Node.TEXT_NODE) : null;
  if (textNode) textNode.nodeValue = value;
}

function setControlTitle(id, value) {
  const target = el(id);
  if (!target) return;
  target.title = value;
  target.setAttribute("aria-label", value);
  const control = target.closest("label.compact-control");
  if (control) {
    control.title = value;
    control.setAttribute("aria-label", value);
  }
}

function applyStaticLocale() {
  document.documentElement.lang = state.locale;
  setText(".library-heading h2", t("assetLibrary"));
  el("assetSearch").placeholder = t("assetSearch");
  setText('#assetStatusFilter option[value=""]', t("allStatuses"));
  ["queued", "running", "completed", "failed", "cancelled"].forEach((status) => setText(`#assetStatusFilter option[value="${status}"]`, t(status)));
  setText(".conversation-header h1", t("conversation"));
  setTitle("#newTaskButton", t("newGeneration"));
  setTitle("#openAssets", t("assets"));
  setTitle("#languageToggle", t("switchLanguage"));
  setTitle("#openPeering", t("peering"));
  setTitle("#closeAssetDetail", t("close"));
  setText("#assetDetailTitle", t("assetDetail"));
  setText("#deleteAssetDetail span", t("deleteRecord"));
  setText("#reuseOutputAssetDetail span", t("useAsInput"));
  setText("#regenerateAssetDetail span", t("regenerate"));
  setText("#reuseAssetDetail span", t("reuse"));
  el("apiDocsLink").title = t("apiDocs");
  el("apiDocsLink").setAttribute("aria-label", t("apiDocs"));
  syncNodeProviderFields();
  if (state.locale !== "en") return;
  setText(".skip-link", "Skip to chat");
  setText(".edit-banner span", "Editing queued task");
  setText("#exitEdit", "Stop editing");
  setText('#executionMode option[value="native"]', "Native H3");
  setText('#executionMode option[value="h3-sa"]', "MiniMax H3 SA · Sol-Attn");
  setText('#executionMode option[value="vdn-h3"]', "VDN-H3 · Video Delta Net");
  setText('#executionMode option[value="dual-sampling"]', "Dual sampling · Sigma + latent upscale");
  setText('#executionMode option[value="digital-human"]', "Digital human · audio driven");
  setText('#executionMode option[value="tts"]', "H3 TTS · character voice");
  setText("#music3ExecutionOption", "Music3 · 30 steps");
  setText("#durationHint", "Video length follows the driving audio");
  setText("#mentionQuickLabel", "Quick actions");
  setText("#mentionReferenceLabel", "Images");
  setText("#optimizePromptLabel", "Optimize prompt");
  setText("#writeLyrics span", "Optimize lyrics");
  setText("#launcherTitle", "Activity");
  setText("#launcherMeta", "Queue empty");
  setText(".ops-header h2", "Runtime status");
  setText("#activeTaskSummary", "No active tasks");
  setText(".queue-section .ops-section-title span", "Running and queued");
  setText(".queue-section .quiet", "Queue empty");
  setText(".log-section .ops-section-title span", "Live logs");
  setText("#clearVisibleLogs", "Clear");
  setText(".log-section .quiet", "Waiting for events");
  setText("#nodeDialogTitle", "Inference nodes");
  setText(".node-dialog-header p", "ComfyUI and RunningHub configuration");
  setText('label[for="nodeHealthInterval"]', "Node status refresh interval");
  setText(".node-settings-row span", "sec");
  setText("#saveNodeSettings", "Save");
  setText("#addNodeButton span", "Add node");
  setText('label[for="nodeProvider"]', "Node type");
  setText('label[for="nodeName"]', "Node name");
  setText('label[for="nodeUrl"]', "API URL");
  setText('label[for="nodeApiKey"]', "API Key");
  setText('label[for="nodeWorkflowUrl"]', "RunningHub workflow or AI app URL");
  setText('label[for="nodeMaxConcurrency"]', "Maximum API concurrency");
  setText(".node-enabled-row > span:first-child", "Enable node");
  setText("#cancelNodeEdit", "Cancel");
  setText("#nodeEditor button.primary", "Save node");
  setText(".secret-dialog h2", "Incognito access");
  setText('label[for="secretCode"]', "Access code");
  setText(".secret-submit", "Enter incognito mode");
  setText("#peeringTitle", "Device sharing");
  setText("#peeringSubtitle", "Share this device's asset library on the local network");
  setLeadingText("#machineName", "Device name");
  setText(".peering-settings .switch-row > span:first-child", "Enable sharing");
  setText(".peering-panel:first-child h3", "Local pairing key");
  setText(".peering-panel:first-child p", "Provide this address and code to the other device");
  setLeadingText("#peerAddress", "Local address");
  setText("#peerConnectForm h3", "Connect another device");
  setText("#peerConnectForm p", "Enter the address and current six-digit code from the other device");
  setLeadingText("#peerConnectAddress", "Remote address");
  setLeadingText("#peerConnectCode", "Remote code");
  setText("#peerConnectForm button span", "Connect");
  setText(".peering-connected h3", "Connected devices");
  setLeadingText("#seed", "Random seed");
  setText("#saSettingsTitle", "MiniMax H3 SA parameters");
  setLeadingText("#saTauControl", "Sol-Attn tau");
  setLeadingText("#saStartControl", "Acceleration start");
  setLeadingText("#saEndControl", "Acceleration end");
  setLeadingText("#saMinTokensControl", "Minimum tokens");
  setLeadingText("#saDenoiseControl", "Stage 2 denoise");
  setLeadingText("#saSinkControl", "Conditioning sink");
  setLeadingText("#saDenseControl", "Dense blocks");
  setLeadingText("#saMortonCurveControl", "Morton curve");
  setText("#saInt8QkControl > span:first-child", "INT8 QK");
  setText("#saInt8PvControl > span:first-child", "INT8 PV");
  setText("#saMortonControl > span:first-child", "Morton token order");
  setLeadingText("#aiBaseUrl", "OpenAI Base URL");
  setLeadingText("#aiModel", "Model");
  setLeadingText("#aiApiKey", "API Key");
  setText(".popover-panel > .switch-row > span:first-child", "Enable AI prompt assistance");
  el("seed").placeholder = "Auto";
  setTitle("#addReference", "Add reference files");
  setTitle("#advancedSettings summary", "More settings");
  setTitle("#mentionTrigger", "Insert image or use a quick action");
  setTitle("#optimizePrompt", "Optimize prompt");
  setTitle("#writeLyrics", "Optimize lyrics");
  setTitle("#reuseOutputAssetDetail", "Use generated output as input");
  setTitle("#generateButton", "Generate");
  setTitle("#closeAssets", "Close assets");
  setTitle("#assetSearch", "Search assets");
  setTitle("#assetStatusFilter", "Asset status filter");
  setTitle("#assetGrid", "Generated assets");
  setTitle("#openNodeManager", "Manage inference nodes");
  setTitle("#opsLauncher", "Open activity log");
  setTitle("#closeOps", "Close activity log");
  setControlTitle("modelVariant", "Model");
  setControlTitle("executionMode", "Workflow");
  setControlTitle("comfyNode", "Inference node");
  setControlTitle("aspectRatio", "Aspect ratio");
  setControlTitle("resolution", "Resolution");
  setControlTitle("duration", "Duration");
  setControlTitle("steps", "Sampling steps");
  el("lyrics").placeholder = "Enter lyrics using [Intro], [Verse], [Chorus], [Bridge], [Instrumental], and [Outro] sections";
}

function statusLabel(status) {
  return t(status) || status;
}

const RESOLUTION_PRESETS = [
  ["608x352", "0.2 MP · 608 × 352", 608, 352],
  ["736x416", "0.3 MP · 736 × 416", 736, 416],
  ["864x480", "0.4 MP · 864 × 480", 864, 480],
  ["960x544", "0.5 MP · 960 × 544", 960, 544],
  ["1056x608", "0.6 MP · 1056 × 608", 1056, 608],
  ["1152x640", "0.7 MP · 1152 × 640", 1152, 640],
  ["1216x672", "0.8 MP · 1216 × 672", 1216, 672],
  ["1280x736", "0.9 MP · 1280 × 736", 1280, 736],
  ["1344x768", "0.98 MP · 1344 × 768", 1344, 768],
  ["1376x768", "1.0 MP · 1376 × 768", 1376, 768],
  ["1504x832", "1.2 MP · 1504 × 832", 1504, 832],
  ["1664x928", "1.5 MP · 1664 × 928", 1664, 928],
  ["1824x1024", "1.8 MP · 1824 × 1024", 1824, 1024],
  ["1920x1088", "2.0 MP · 1920 × 1088", 1920, 1088],
].map(([value, label, width, height]) => ({ value, label, width, height }));

function icon(name) {
  return `<i data-lucide="${name}" aria-hidden="true"></i>`;
}

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons();
}

function togglePasswordField(inputId, buttonId) {
  const input = el(inputId);
  const button = el(buttonId);
  const visible = input.type === "text";
  input.type = visible ? "password" : "text";
  button.innerHTML = icon(visible ? "eye" : "eye-off");
  button.title = visible ? "显示密钥" : "隐藏密钥";
  button.setAttribute("aria-label", button.title);
  refreshIcons();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatBytes(bytes) {
  if (!bytes) return "";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatTime(value, includeDate = false) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(state.locale, {
    month: includeDate ? "2-digit" : undefined,
    day: includeDate ? "2-digit" : undefined,
    hour: "2-digit",
    minute: "2-digit",
    second: includeDate ? "2-digit" : undefined,
    hour12: false,
  }).format(date);
}

function modelLabel(job) {
  if (job.request?.provider === "runninghub" || job.assigned_node?.provider === "runninghub") {
    return job.request?.runninghub_workflow_name || job.assigned_node?.workflow_name || job.assigned_node?.name || "RunningHub";
  }
  if (job.request?.model_variant === "music3-int8") return "Music3 INT8";
  return job.request?.model_variant === "ref2va-fp8" ? "Ref2VA FP8" : "FL2VA FP8";
}

function jobMediaType(job) {
  const mediaType = job.request?.media_type;
  return ["audio", "video", "image", "file"].includes(mediaType) ? mediaType : "video";
}

function mediaReadyLabel(mediaType) {
  return mediaType === "audio" ? t("musicReady") : mediaType === "image" ? t("imageReady") : mediaType === "file" ? t("fileReady") : t("videoReady");
}

function mediaDownloadLabel(mediaType) {
  return mediaType === "audio" ? t("downloadAudio") : mediaType === "image" ? t("downloadImage") : mediaType === "file" ? t("downloadFile") : t("downloadVideo");
}

function executionModeLabel(job) {
  if (job.request?.provider === "runninghub" || job.assigned_node?.provider === "runninghub") return "RunningHub";
  if (job.request?.execution_mode === "music3") return t("music3");
  if (job.request?.execution_mode === "digital-human") return t("digitalHuman");
  if (job.request?.execution_mode === "tts") return t("tts");
  if (job.request?.execution_mode === "h3-nsfw") return t("nsfw");
  if (job.request?.execution_mode === "h3-sa") return t("h3Sa");
  if (job.request?.execution_mode === "vdn-h3") return t("vdnH3");
  if (job.request?.execution_mode === "turbo-lora") return t("turbo");
  if (job.request?.execution_mode === "dual-sampling") return t("dualSampling");
  if (job.request?.execution_mode === "speed-cache") return t("speedCache");
  return t("native");
}

function executionModeClass(job) {
  if (job.request?.execution_mode === "music3") return "music3";
  if (job.request?.execution_mode === "digital-human") return "digital-human";
  if (job.request?.execution_mode === "tts") return "tts";
  if (job.request?.execution_mode === "h3-nsfw") return "nsfw";
  if (job.request?.execution_mode === "h3-sa") return "h3-sa";
  if (job.request?.execution_mode === "vdn-h3") return "vdn-h3";
  if (job.request?.execution_mode === "turbo-lora") return "turbo";
  if (job.request?.execution_mode === "dual-sampling") return "dual-sampling";
  if (job.request?.execution_mode === "speed-cache") return "speed";
  return "native";
}

function formatElapsed(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remainingSeconds = total % 60;
  if (state.locale === "en") {
    if (hours) return `${hours}h ${String(minutes).padStart(2, "0")}m ${String(remainingSeconds).padStart(2, "0")}s`;
    if (minutes) return `${minutes}m ${String(remainingSeconds).padStart(2, "0")}s`;
    return `${remainingSeconds}s`;
  }
  if (hours) return `${hours} 小时 ${String(minutes).padStart(2, "0")} 分 ${String(remainingSeconds).padStart(2, "0")} 秒`;
  if (minutes) return `${minutes} 分 ${String(remainingSeconds).padStart(2, "0")} 秒`;
  return `${remainingSeconds} 秒`;
}

function shortTitle(job) {
  const value = job.title || job.request?.prompt || job.id;
  return String(value).replaceAll("\n", " ").slice(0, 42);
}

function nodeLabel(job) {
  const owner = job.assigned_node?.owner_name || job.owner_name;
  if (job.assigned_node?.name) return owner ? `${job.assigned_node.name} · ${t("owner")} ${owner}` : job.assigned_node.name;
  const requested = job.request?.comfy_node || "auto";
  if (requested === "auto") return job.status === "queued" ? t("autoSchedule") : t("nodePending");
  if (requested.startsWith(RUNNINGHUB_TARGET_PREFIX)) {
    return job.request?.runninghub_workflow_name || "RunningHub";
  }
  const selectedNode = state.nodes.find((node) => node.id === requested);
  const label = selectedNode?.name || requested;
  const selectedOwner = selectedNode?.owner_name || owner;
  return selectedOwner ? `${label} · ${t("owner")} ${selectedOwner}` : label;
}

function formatAccountNumber(value) {
  if (value == null || value === "" || !Number.isFinite(Number(value))) return "";
  return new Intl.NumberFormat(state.locale, { maximumFractionDigits: 4 }).format(Number(value));
}

function formatAccountMoney(value, currency) {
  if (value == null || value === "" || !Number.isFinite(Number(value))) return "";
  const code = String(currency || "").toUpperCase();
  if (/^[A-Z]{3}$/.test(code)) {
    try {
      return new Intl.NumberFormat(state.locale, {
        style: "currency",
        currency: code,
        maximumFractionDigits: 4,
      }).format(Number(value));
    } catch {
      return `${code} ${formatAccountNumber(value)}`;
    }
  }
  return formatAccountNumber(value);
}

function runningHubBalanceLabel(node) {
  const parts = [];
  const money = formatAccountMoney(node.account_balance_money, node.account_currency);
  if (money) parts.push(money);
  const coins = formatAccountNumber(node.account_balance_coins);
  if (coins) parts.push(`${coins} ${t("credits")}`);
  if (parts.length) return `${t("balance")} ${parts.join(" / ")}`;
  return node.account_error ? t("accountUnavailable") : t("balancePending");
}

function runningHubCostLabel(node) {
  const parts = [];
  if (Number(node.last_call_consumed_money) > 0) {
    parts.push(formatAccountMoney(node.last_call_consumed_money, node.account_currency));
  }
  if (Number(node.last_call_consumed_coins) > 0) {
    parts.push(`${formatAccountNumber(node.last_call_consumed_coins)} ${t("credits")}`);
  }
  const measured = node.last_call_consumed_money != null || node.last_call_consumed_coins != null;
  if (!parts.length && measured) parts.push("0");
  return parts.length ? `${t("recentCost")} ${parts.join(" / ")}` : "";
}

function renderNodeOptions(nodes = state.nodes) {
  state.nodes = Array.isArray(nodes) ? nodes : [];
  const select = el("comfyNode");
  const current = select.value || "auto";
  const healthyNodes = state.nodes.filter((node) => node.healthy);
  const comfyNodes = state.nodes.filter((node) => node.provider !== "runninghub");
  const healthyComfyNodes = comfyNodes.filter((node) => node.healthy);
  const legacyRunningHubAuto = healthyNodes.length > 0
    && healthyNodes.every((node) => node.provider === "runninghub")
    && new Set(healthyNodes.map((node) => node.workflow_id)).size === 1;
  const autoOnline = legacyRunningHubAuto ? healthyNodes.length : healthyComfyNodes.length;
  const autoTotal = legacyRunningHubAuto ? state.nodes.length : comfyNodes.length;
  const options = [`<option value="auto">${t("autoSchedule")} · ${autoOnline}/${autoTotal} ${t("available")}</option>`];
  const runningHubGroups = new Map();
  state.nodes.filter((node) => node.provider === "runninghub" && node.workflow_id && node.runninghub_schema).forEach((node) => {
    if (!runningHubGroups.has(node.workflow_id)) runningHubGroups.set(node.workflow_id, []);
    runningHubGroups.get(node.workflow_id).push(node);
  });
  runningHubGroups.forEach((group, resourceId) => {
    const available = group.filter((node) => node.healthy);
    const representative = available[0] || group[0];
    const running = group.reduce((total, node) => total + Number(node.running_count || 0), 0);
    const capacity = available.reduce((total, node) => total + Number(node.capacity || 1), 0);
    const stateLabel = running
      ? `${t("busy")} ${running}/${capacity}`
      : `${available.length}/${group.length} ${t("available")} · ${localized("并发", "capacity")} ${capacity}`;
    const label = `${t("autoSchedule")} · ${representative.workflow_name || representative.name}`;
    options.push(`<option value="${escapeHtml(`${RUNNINGHUB_TARGET_PREFIX}${resourceId}`)}"${available.length ? "" : " disabled"}>${escapeHtml(label)} · ${escapeHtml(stateLabel)}</option>`);
  });
  state.nodes.forEach((node) => {
    const running = Number(node.running_count || 0);
    const capacity = Number(node.capacity || 1);
    const stateLabel = node.provider === "runninghub"
      ? !node.healthy
        ? t("workflowUnavailable")
        : `${running ? `${t("busy")} ${running}/${capacity} · ` : ""}${runningHubBalanceLabel(node)}`
      : !node.healthy
        ? t("nodeOffline")
        : running
          ? `${t("busy")} ${running}/${capacity}`
          : `${t("online")} 0/${capacity}`;
    const label = node.provider === "runninghub"
      ? `${escapeHtml(node.workflow_name || node.name)} · ${node.runninghub_resource_type === "ai-app" ? "AI App" : "Workflow"}`
      : escapeHtml(node.name);
    const ownerLabel = node.owner_name ? ` · ${escapeHtml(t("owner"))} ${escapeHtml(node.owner_name)}` : "";
    options.push(`<option value="${escapeHtml(node.id)}"${node.healthy ? "" : " disabled"}>${label}${ownerLabel} · ${escapeHtml(stateLabel)}</option>`);
  });
  const markup = options.join("");
  if (select.innerHTML !== markup) select.innerHTML = markup;
  select.value = Array.from(select.options).some((option) => option.value === current) ? current : "auto";
  updateModelUi();
}

function renderHealthState(nodes = state.nodes, queueDepth = state.queue.length) {
  renderNodeOptions(nodes);
  const online = state.nodes.filter((node) => node.healthy).length;
  const capacity = state.nodes
    .filter((node) => node.healthy)
    .reduce((total, node) => total + Number(node.capacity || 1), 0);
  const message = state.locale === "en"
    ? `${online}/${state.nodes.length} nodes available · capacity ${capacity} · queue ${queueDepth}`
    : `${online}/${state.nodes.length} 节点可用 · 并发 ${capacity} · 队列 ${queueDepth}`;
  el("healthDot").className = `status-dot ${online > 0 ? "online" : "offline"}`;
  el("healthText").textContent = message;
  el("healthText").dataset.snapshot = message;
}

function nodeStatus(node) {
  if (!node.enabled) return { label: t("disabled"), className: "disabled" };
  if (node.provider === "runninghub") {
    if (!node.healthy) return { label: t("workflowUnavailable"), className: "offline" };
    if (node.busy) return { label: t("busy"), className: "busy" };
    return {
      label: runningHubBalanceLabel(node),
      className: "online",
    };
  }
  if (!node.healthy) return { label: t("nodeOffline"), className: "offline" };
  if (node.busy) return { label: t("busy"), className: "busy" };
  return { label: t("online"), className: "online" };
}

function syncNodeProviderFields() {
  const provider = el("nodeProvider")?.value || "comfyui";
  const runningHub = provider === "runninghub";
  if (runningHub && !el("nodeUrl").value.trim()) {
    el("nodeUrl").value = "https://www.runninghub.ai";
  }
  document.querySelectorAll('[data-node-provider="runninghub"]').forEach((field) => {
    field.hidden = !runningHub;
  });
  el("nodeUrlLabel").hidden = runningHub;
  el("nodeUrl").hidden = runningHub;
  el("nodeUrl").required = !runningHub;
  el("nodeWorkflowUrl").required = runningHub;
  el("nodeMaxConcurrency").required = runningHub;
  const editing = state.managedNodes.find((node) => node.id === state.nodeEditingId);
  el("nodeApiKey").required = runningHub && !editing?.has_api_key;
  el("nodeUrl").placeholder = runningHub ? "https://www.runninghub.ai" : "http://127.0.0.1:8188";
  el("nodeApiKey").placeholder = runningHub
    ? (editing?.has_api_key ? localized("留空以保留现有密钥", "Leave blank to keep the saved key") : localized("必填", "Required"))
    : localized("ComfyUI 可留空", "Optional for ComfyUI");
  el("nodeApiKeyHint").textContent = runningHub
    ? (editing?.has_api_key ? localized("已保存 API Key，留空不会修改", "An API Key is saved; leave blank to keep it") : localized("RunningHub API Key 仅保存在服务端数据库", "The RunningHub API Key is stored only in the server database"))
    : localized("ComfyUI 未启用鉴权时可留空", "Leave blank when ComfyUI authentication is disabled");
  el("nodeNameLabel").textContent = localized("节点名称", "Node name");
}

function renderManagedNodes() {
  const remoteCount = state.managedNodes.filter((node) => node.remote_proxy).length;
  const localCount = state.managedNodes.length - remoteCount;
  el("nodeManagerSummary").textContent = state.locale === "en"
    ? `${state.managedNodes.length} nodes · ${localCount} local · ${remoteCount} remote`
    : `${state.managedNodes.length} 个节点 · 本机 ${localCount} · 远程 ${remoteCount}`;
  el("nodeList").innerHTML = state.managedNodes.length ? state.managedNodes.map((node) => {
    const status = nodeStatus(node);
    const running = Number(node.running_count || 0);
    const capacity = Number(node.capacity || node.max_concurrency || 1);
    const activity = node.busy
      ? ` · ${localized("并发", "capacity")} ${running}/${capacity}`
      : node.queue_depth ? ` · 排队 ${node.queue_depth}` : "";
    if (node.remote_proxy) {
      const owner = node.owner_name || node.source?.name || "远程设备";
      return `<div class="node-row remote-node" data-node-id="${escapeHtml(node.id)}">
        <span class="node-state ${status.className}" aria-hidden="true"></span>
        <div class="node-row-copy"><div><strong>${escapeHtml(node.name || "远程推理节点")}</strong><span>${escapeHtml(status.label)}${activity}</span></div><small>${escapeHtml(localized("远程代理节点", "Remote proxy node"))} · ${escapeHtml(t("owner"))} ${escapeHtml(owner)}</small></div>
        <div class="node-row-actions" aria-hidden="true"></div>
      </div>`;
    }
    const provider = node.provider === "runninghub" ? "RunningHub API" : "ComfyUI API";
    const workflowType = node.runninghub_resource_type === "ai-app" ? "AI App" : "Workflow";
    const workflow = node.provider === "runninghub" ? ` · ${workflowType} ${escapeHtml(node.workflow_url || "-")}` : "";
    const keyState = node.has_api_key ? ` · ${localized("API Key 已保存", "API Key saved")}` : "";
    const accountTasks = node.provider === "runninghub" && node.account_current_tasks != null
      ? ` · ${t("accountTasks")} ${escapeHtml(String(node.account_current_tasks))}`
      : "";
    const recentCost = node.provider === "runninghub" ? runningHubCostLabel(node) : "";
    const accountingTitle = [
      localized("按调用前后余额差值计算；同一 API Key 并发使用时可能包含同期扣费", "Calculated from the balance difference before and after a call; concurrent use of the same API key can include other charges"),
      node.account_error || "",
      node.workflow_error || "",
    ].filter(Boolean).join(" · ");
    const accounting = node.provider === "runninghub"
      ? `<small class="node-accounting" title="${escapeHtml(accountingTitle)}">${escapeHtml(runningHubBalanceLabel(node))}${accountTasks}${recentCost ? ` · ${escapeHtml(recentCost)}` : ""}</small>`
      : "";
    const workflowIssue = node.provider === "runninghub" && node.workflow_error
      ? `<small class="node-accounting" title="${escapeHtml(node.workflow_error)}">${escapeHtml(t("workflowUnavailable"))}</small>`
      : "";
    const checkedLabel = node.provider === "runninghub"
      ? node.account_error ? t("balanceFailed") : t("balanceUpdated")
      : localized("检测", "checked");
    return `<div class="node-row" data-node-id="${escapeHtml(node.id)}">
      <span class="node-state ${status.className}" aria-hidden="true"></span>
      <div class="node-row-copy"><div><strong>${escapeHtml(node.provider === "runninghub" ? node.workflow_name || node.name : node.name)}</strong><span>${escapeHtml(status.label)}${activity}</span></div><code title="${escapeHtml(node.url)}">${escapeHtml(node.url)}</code>${accounting}${workflowIssue}<small>${provider}${workflow}${node.provider === "runninghub" && node.workflow_name && node.workflow_name !== node.name ? ` · ${escapeHtml(node.name)}` : ""}${keyState} · ID ${escapeHtml(node.id)}${node.last_checked ? ` · ${formatTime(node.last_checked, true)} ${checkedLabel}` : ""}</small></div>
      <div class="node-row-actions"><button type="button" data-node-action="edit" title="编辑节点" aria-label="编辑 ${escapeHtml(node.name)}">${icon("pencil")}</button><button type="button" data-node-action="delete" title="删除节点" aria-label="删除 ${escapeHtml(node.name)}">${icon("trash-2")}</button></div>
    </div>`;
  }).join("") : `<p class="quiet">${state.locale === "en" ? "No nodes" : "暂无节点"}</p>`;
  refreshIcons();
}

function syncManagedNodeStatuses(nodes) {
  const statuses = new Map(nodes.map((node) => [node.id, node]));
  const localNodes = state.managedNodes
    .filter((node) => !node.remote_proxy)
    .map((node) => ({ ...node, ...(statuses.get(node.id) || {}) }));
  const localIds = new Set(localNodes.map((node) => node.id));
  const remoteNodes = nodes
    .filter((node) => node.remote_proxy && !localIds.has(node.id))
    .map((node) => ({ ...node, enabled: true, managed_remote: true }));
  state.managedNodes = [...localNodes, ...remoteNodes];
  if (!el("nodeModal").hidden) renderManagedNodes();
}

async function loadManagedNodes() {
  const payload = await api("/api/v1/comfy/nodes");
  const statuses = new Map(state.nodes.map((node) => [node.id, node]));
  const localNodes = (payload.data || []).map((node) => ({
    ...node,
    ...(statuses.get(node.id) || {}),
  }));
  const localIds = new Set(localNodes.map((node) => node.id));
  const remoteNodes = state.nodes
    .filter((node) => node.remote_proxy && !localIds.has(node.id))
    .map((node) => ({ ...node, enabled: true, managed_remote: true }));
  state.managedNodes = [...localNodes, ...remoteNodes];
  if (el("nodeHealthInterval")) el("nodeHealthInterval").value = String(payload.health_interval_seconds || 60);
  renderManagedNodes();
}

function openNodeEditor(nodeId = null) {
  const node = nodeId ? state.managedNodes.find((item) => item.id === nodeId) : null;
  state.nodeEditingId = node?.id || null;
  el("nodeEditorTitle").textContent = node ? localized("编辑节点", "Edit node") : localized("新增节点", "Add node");
  el("nodeProvider").value = node?.provider || "comfyui";
  el("nodeName").value = node?.name || "";
  el("nodeUrl").value = node?.url || "";
  el("nodeApiKey").value = "";
  el("nodeWorkflowUrl").value = node?.workflow_url || "";
  el("nodeMaxConcurrency").value = String(node?.max_concurrency || 1);
  el("nodeEnabled").checked = node ? Boolean(node.enabled) : true;
  el("nodeEnabled").closest(".node-enabled-row").hidden = !node;
  el("nodeEditor").hidden = false;
  el("nodeManagerError").textContent = "";
  syncNodeProviderFields();
  requestAnimationFrame(() => el("nodeName").focus());
}

function closeNodeEditor() {
  state.nodeEditingId = null;
  el("nodeEditor").reset();
  el("nodeEditor").hidden = true;
  el("nodeManagerError").textContent = "";
}

async function openNodeManager() {
  el("nodeModal").hidden = false;
  document.body.classList.add("modal-open");
  el("nodeManagerError").textContent = "";
  refreshIcons();
  try {
    await loadManagedNodes();
  } catch (error) {
    el("nodeManagerError").textContent = error.message;
  }
}

function closeNodeManager() {
  closeNodeEditor();
  el("nodeModal").hidden = true;
  if (el("peeringModal").hidden && el("assetDetailModal").hidden) document.body.classList.remove("modal-open");
  el("openNodeManager").focus();
}

async function saveNodeSettings() {
  el("nodeManagerError").textContent = "";
  const seconds = Number(el("nodeHealthInterval").value);
  if (!Number.isFinite(seconds) || seconds < 5 || seconds > 3600) {
    el("nodeManagerError").textContent = localized("健康检查间隔必须为 5 至 3600 秒", "Health check interval must be between 5 and 3600 seconds");
    return;
  }
  const button = el("saveNodeSettings");
  button.disabled = true;
  try {
    const payload = await api("/api/v1/comfy/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ health_interval_seconds: seconds }),
    });
    el("nodeHealthInterval").value = String(payload.health_interval_seconds);
  } catch (error) {
    el("nodeManagerError").textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function saveNode(event) {
  event.preventDefault();
  el("nodeManagerError").textContent = "";
  const editing = state.nodeEditingId;
  const body = {
    name: el("nodeName").value.trim(),
    url: el("nodeUrl").value.trim(),
    provider: el("nodeProvider").value,
    api_key: el("nodeApiKey").value.trim(),
    workflow_url: el("nodeWorkflowUrl").value.trim(),
    max_concurrency: Number(el("nodeMaxConcurrency").value || 1),
  };
  let url = "/api/v1/comfy/nodes";
  let method = "POST";
  if (editing) {
    url += `/${encodeURIComponent(editing)}`;
    method = "PATCH";
    body.enabled = el("nodeEnabled").checked;
  }
  const submit = el("nodeEditor").querySelector('button[type="submit"]');
  submit.disabled = true;
  try {
    await api(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    closeNodeEditor();
    await Promise.all([loadManagedNodes(), checkHealth()]);
  } catch (error) {
    el("nodeManagerError").textContent = error.message;
  } finally {
    submit.disabled = false;
  }
}

async function deleteNode(nodeId) {
  const node = state.managedNodes.find((item) => item.id === nodeId);
  if (!node || !window.confirm(localized(`确认删除节点“${node.name}”？`, `Delete node "${node.name}"?`))) return;
  el("nodeManagerError").textContent = "";
  try {
    await api(`/api/v1/comfy/nodes/${encodeURIComponent(nodeId)}`, { method: "DELETE" });
    if (state.nodeEditingId === nodeId) closeNodeEditor();
    await Promise.all([loadManagedNodes(), checkHealth()]);
  } catch (error) {
    el("nodeManagerError").textContent = error.message;
  }
}

function isActive(job) {
  return ["queued", "running"].includes(job.status);
}

function isAnonymousQueueJob(job) {
  return !job.id;
}

function selectedVariant() {
  return el("modelVariant").value;
}

function selectedExecutionMode() {
  return el("executionMode").value;
}

const SA_DEFAULTS = {
  sa_tau: 1.3,
  sa_start_percent: 0.2,
  sa_end_percent: 0.9,
  sa_min_tokens: 4096,
  sa_int8_qk: true,
  sa_int8_pv: true,
  sa_sink_conditioning: "exact_kv_and_rows",
  sa_morton: false,
  sa_morton_curve: "2d_frame",
  sa_dense_blocks: "0",
  sa_stage2_denoise: 0.35,
};

function readSaParameters() {
  return {
    sa_tau: Number(el("saTau").value),
    sa_start_percent: Number(el("saStartPercent").value),
    sa_end_percent: Number(el("saEndPercent").value),
    sa_min_tokens: Number(el("saMinTokens").value),
    sa_int8_qk: el("saInt8Qk").checked,
    sa_int8_pv: el("saInt8Pv").checked,
    sa_sink_conditioning: el("saSinkConditioning").value,
    sa_morton: el("saMorton").checked,
    sa_morton_curve: el("saMortonCurve").value,
    sa_dense_blocks: el("saDenseBlocks").value,
    sa_stage2_denoise: Number(el("saStage2Denoise").value),
  };
}

function setSaParameters(values = {}) {
  const next = { ...SA_DEFAULTS, ...values };
  el("saTau").value = String(next.sa_tau);
  el("saStartPercent").value = String(next.sa_start_percent);
  el("saEndPercent").value = String(next.sa_end_percent);
  el("saMinTokens").value = String(next.sa_min_tokens);
  el("saInt8Qk").checked = Boolean(next.sa_int8_qk);
  el("saInt8Pv").checked = Boolean(next.sa_int8_pv);
  el("saSinkConditioning").value = next.sa_sink_conditioning;
  el("saMorton").checked = Boolean(next.sa_morton);
  el("saMortonCurve").value = next.sa_morton_curve;
  el("saDenseBlocks").value = String(next.sa_dense_blocks ?? "0");
  el("saStage2Denoise").value = String(next.sa_stage2_denoise);
}

function selectedInferenceNode() {
  const nodeId = el("comfyNode").value;
  return nodeId === "auto" ? null : state.nodes.find((node) => node.id === nodeId) || null;
}

function selectedRunningHubNode() {
  const selected = el("comfyNode").value;
  if (selected.startsWith(RUNNINGHUB_TARGET_PREFIX)) {
    const resourceId = selected.slice(RUNNINGHUB_TARGET_PREFIX.length);
    return state.nodes.find((node) => node.healthy && node.provider === "runninghub" && node.workflow_id === resourceId)
      || state.nodes.find((node) => node.provider === "runninghub" && node.workflow_id === resourceId)
      || null;
  }
  const node = selectedInferenceNode();
  if (node?.provider === "runninghub") return node;
  if (el("comfyNode").value !== "auto") return null;
  const candidates = state.nodes.filter((item) => item.healthy);
  if (!candidates.length || candidates.some((item) => item.provider !== "runninghub")) return null;
  const workflowIds = new Set(candidates.map((item) => item.workflow_id));
  return workflowIds.size === 1 ? candidates[0] : null;
}

function selectedRunningHubSchema() {
  const schema = selectedRunningHubNode()?.runninghub_schema;
  return schema && Array.isArray(schema.fields) ? schema : null;
}

function runningHubFieldLabel(field) {
  return state.locale === "en" ? field.label_en || field.label || field.key : field.label || field.label_en || field.key;
}

function runningHubSchemaKey(schema) {
  if (!schema) return "";
  const fields = (schema.fields || []).map((field) => [
    field.key, field.field_type, field.default, field.options, field.editable,
    field.media_kind, field.min, field.max, field.step, field.multiline,
    field.required, field.label, field.label_en,
  ]);
  return `${schema.resource_id || ""}:${JSON.stringify(fields)}`;
}

function runningHubDefaultParameters(schema) {
  return Object.fromEntries((schema?.fields || [])
    .filter((field) => field.editable !== false && !field.media_kind)
    .map((field) => [field.key, field.default ?? (field.field_type === "BOOLEAN" ? false : "")]));
}

function syncRunningHubSchema() {
  const schema = selectedRunningHubSchema();
  const key = runningHubSchemaKey(schema);
  const resourceId = String(schema?.resource_id || "");
  if (!schema) {
    state.runningHubSchemaKey = "";
    state.runningHubResourceId = "";
    state.runningHubParameters = {};
    state.pendingRunningHubMediaField = "";
    renderRunningHubParameters();
    return;
  }
  const schemaChanged = key !== state.runningHubSchemaKey;
  if (resourceId !== state.runningHubResourceId) {
    state.runningHubParameters = runningHubDefaultParameters(schema);
  } else if (schemaChanged) {
    state.runningHubParameters = {
      ...runningHubDefaultParameters(schema),
      ...state.runningHubParameters,
    };
  }
  state.runningHubSchemaKey = key;
  state.runningHubResourceId = resourceId;
  if (schemaChanged) renderRunningHubParameters();
}

function runningHubMediaFields(kind = "", schema = selectedRunningHubSchema()) {
  return (schema?.fields || []).filter((field) => (
    field.editable !== false && field.media_kind && (!kind || field.media_kind === kind)
  ));
}

function runningHubReferenceField(item, schema = selectedRunningHubSchema()) {
  return runningHubMediaFields("", schema).find((field) => field.key === item.field_key) || null;
}

function runningHubAvailableMediaField(kind, references = state.references) {
  const used = new Set(references.map((item) => item.field_key).filter(Boolean));
  return runningHubMediaFields(kind).find((field) => !used.has(field.key)) || null;
}

function runningHubParameterMarkup(field) {
  const key = escapeHtml(String(field.key || ""));
  const label = escapeHtml(runningHubFieldLabel(field));
  const value = state.runningHubParameters[field.key] ?? field.default ?? "";
  if (field.media_kind) {
    const reference = state.references.find((item) => item.field_key === field.key);
    const mediaIcon = field.media_kind === "video" ? "film" : field.media_kind === "audio" ? "audio-lines" : field.media_kind === "file" ? "file" : "image";
    return `<button class="runninghub-media-input" type="button" data-runninghub-media-key="${key}" data-runninghub-media-kind="${escapeHtml(field.media_kind)}">${icon(mediaIcon)}<span><b>${label}</b><small>${escapeHtml(reference?.name || localized("选择文件", "Choose file"))}</small></span></button>`;
  }
  if (field.key === selectedRunningHubSchema()?.primary_text_key) return "";
  if (field.field_type === "BOOLEAN") {
    const checked = value === true || String(value).toLowerCase() === "true";
    return `<label class="runninghub-parameter runninghub-boolean switch-row"><span title="${label}">${label}</span><input type="checkbox" data-runninghub-key="${key}"${checked ? " checked" : ""}><span class="switch"></span></label>`;
  }
  if (Array.isArray(field.options) && field.options.length) {
    const options = field.options.map((option) => `<option value="${escapeHtml(String(option.value))}"${String(option.value) === String(value) ? " selected" : ""}>${escapeHtml(option.label || String(option.value))}</option>`).join("");
    return `<label class="runninghub-parameter"><span title="${label}">${label}</span><select data-runninghub-key="${key}">${options}</select></label>`;
  }
  if (["INTEGER", "FLOAT"].includes(field.field_type)) {
    const min = field.min == null ? "" : ` min="${escapeHtml(String(field.min))}"`;
    const max = field.max == null ? "" : ` max="${escapeHtml(String(field.max))}"`;
    const step = field.step == null ? (field.field_type === "INTEGER" ? "1" : "any") : String(field.step);
    return `<label class="runninghub-parameter"><span title="${label}">${label}</span><input type="number" data-runninghub-key="${key}" value="${escapeHtml(String(value))}" step="${escapeHtml(step)}"${min}${max}></label>`;
  }
  if (field.multiline) {
    return `<label class="runninghub-parameter runninghub-parameter-wide"><span title="${label}">${label}</span><textarea data-runninghub-key="${key}" maxlength="12000">${escapeHtml(String(value))}</textarea></label>`;
  }
  return `<label class="runninghub-parameter"><span title="${label}">${label}</span><input type="text" data-runninghub-key="${key}" value="${escapeHtml(String(value))}" maxlength="12000"></label>`;
}

function runningHubParameterRenderSignature() {
  const schema = selectedRunningHubSchema();
  if (!schema) return "";
  const media = state.references.map((item) => [item.field_key, item.name]);
  return JSON.stringify([runningHubSchemaKey(schema), state.runningHubParameters, media, state.locale]);
}

function renderRunningHubParameters() {
  const container = el("runningHubParameters");
  const schema = selectedRunningHubSchema();
  if (!schema) {
    state.runningHubRenderSignature = "";
    container.hidden = true;
    container.innerHTML = "";
    return;
  }
  const signature = runningHubParameterRenderSignature();
  if (signature === state.runningHubRenderSignature) return;
  const fields = (schema.fields || []).filter((field) => field.editable !== false);
  const markup = fields.map(runningHubParameterMarkup).filter(Boolean).join("");
  container.innerHTML = markup;
  container.hidden = !markup;
  state.runningHubRenderSignature = signature;
  refreshIcons();
}

function collectRunningHubParameters() {
  const schema = selectedRunningHubSchema();
  if (!schema) return {};
  const values = {};
  (schema.fields || []).forEach((field) => {
    if (field.editable === false || field.media_kind || field.key === schema.primary_text_key) return;
    const input = Array.from(el("runningHubParameters").querySelectorAll("[data-runninghub-key]")).find((item) => item.dataset.runninghubKey === field.key);
    if (!input) return;
    values[field.key] = input.type === "checkbox" ? input.checked : input.value;
  });
  state.runningHubParameters = { ...state.runningHubParameters, ...values };
  return values;
}

function jobScope() {
  return state.incognito ? "incognito" : "normal";
}

function isRef2VA(variant = selectedVariant()) {
  return variant === "ref2va-fp8";
}

function isDigitalHuman(executionMode = selectedExecutionMode()) {
  return executionMode === "digital-human";
}

function isDualSampling(executionMode = selectedExecutionMode()) {
  return executionMode === "dual-sampling";
}

function isH3SA(executionMode = selectedExecutionMode()) {
  return executionMode === "h3-sa";
}

function isVDNH3(executionMode = selectedExecutionMode()) {
  return executionMode === "vdn-h3";
}

function isTTS(executionMode = selectedExecutionMode()) {
  return executionMode === "tts";
}

function isMusic3(variant = selectedVariant()) {
  return variant === "music3-int8";
}

function referenceLimits(variant = selectedVariant()) {
  const schema = selectedRunningHubSchema();
  if (schema) {
    const limits = { image: 0, video: 0, audio: 0, file: 0 };
    runningHubMediaFields("", schema).forEach((field) => { limits[field.media_kind] += 1; });
    return limits;
  }
  if (isMusic3(variant)) return { image: 0, video: 0, audio: 0 };
  if (isDigitalHuman()) return { image: 1, video: 0, audio: 1 };
  if (isDualSampling()) return { image: 9, video: 0, audio: 0 };
  if (isTTS()) return { image: 0, video: 0, audio: 3 };
  return isRef2VA(variant)
    ? { image: 9, video: 3, audio: 3 }
    : { image: 2, video: 0, audio: 0 };
}

function kindFor(file) {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("video/")) return "video";
  if (file.type.startsWith("audio/")) return "audio";
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (["jpg", "jpeg", "png", "webp", "bmp", "gif"].includes(extension)) return "image";
  if (["mp4", "mov", "mkv", "webm", "avi", "m4v"].includes(extension)) return "video";
  if (["mp3", "wav", "flac", "m4a", "aac", "ogg", "opus"].includes(extension)) return "audio";
  if (selectedRunningHubSchema() && runningHubMediaFields("file").length) return "file";
  return null;
}

function referenceLabels(
  references = state.references,
  variant = selectedVariant(),
  executionMode = selectedExecutionMode(),
  schema = selectedRunningHubSchema(),
) {
  const counts = { image: 0, video: 0, audio: 0, file: 0 };
  return references.map((item) => {
    const kind = item.kind || item.type;
    counts[kind] += 1;
    const runningHubField = runningHubReferenceField(item, schema);
    if (runningHubField) return runningHubFieldLabel(runningHubField);
    if (isDigitalHuman(executionMode)) return kind === "image" ? localized("人物图像", "Portrait") : localized("驱动音频", "Driving audio");
    if (!isRef2VA(variant)) return counts.image === 1 ? localized("首帧", "First frame") : localized("尾帧", "Last frame");
    return `<${{ image: "Picture", video: "Video", audio: "Audio" }[kind]} ${counts[kind]}>`;
  });
}

function validateReferenceSet(references = state.references, variant = selectedVariant()) {
  const schema = selectedRunningHubSchema();
  if (schema) {
    const available = new Map(runningHubMediaFields("", schema).map((field) => [field.key, field]));
    const used = new Set();
    for (const item of references) {
      const field = available.get(item.field_key);
      if (!field || field.media_kind !== (item.kind || item.type) || used.has(item.field_key)) {
        return localized("参考文件与 RunningHub 媒体字段不匹配", "A reference file does not match the RunningHub media field");
      }
      used.add(item.field_key);
    }
    const missing = runningHubMediaFields("", schema).find((field) => field.required && !used.has(field.key));
    return missing ? localized(`请填写 ${runningHubFieldLabel(missing)}`, `Provide ${runningHubFieldLabel(missing)}`) : "";
  }
  if (isMusic3(variant)) return references.length ? localized("Music3 不使用参考素材", "Music3 does not use reference files") : "";
  if (isTTS()) {
    const audioCount = references.filter((item) => (item.kind || item.type) === "audio").length;
    if (audioCount !== references.length || references.length > 3) {
      return localized("H3 TTS 支持 0 至 3 段人物音频参考", "H3 TTS supports zero to three character voice references");
    }
    return "";
  }
  if (!references.length) return localized("请至少添加一份参考素材", "Add at least one reference file");
  const limits = referenceLimits(variant);
  const counts = { image: 0, video: 0, audio: 0, file: 0 };
  references.forEach((item) => { counts[item.kind || item.type] += 1; });
  if (isDigitalHuman()) {
    if (references.length !== 2 || counts.image !== 1 || counts.audio !== 1) {
      return localized("数字人模式需要添加 1 张人物图片和 1 段驱动音频", "Digital human mode requires one portrait and one driving audio file");
    }
    return "";
  }
  if (!isRef2VA(variant) && (counts.image !== references.length || counts.image > 2)) {
    return localized("FL2VA 仅支持 1 张首帧，或首帧和尾帧两张图片", "FL2VA accepts one first frame or a first and last frame pair");
  }
  if (counts.image > limits.image || counts.video > limits.video || counts.audio > limits.audio) {
    return localized("Ref2VA 最多支持 9 张图片、3 段视频和 3 段音频", "Ref2VA accepts up to 9 images, 3 videos, and 3 audio files");
  }
  return "";
}

function showError(message) {
  el("formError").textContent = message || "";
}

function positionDurationTooltip() {
  if (!isDigitalHuman() && !(isH3SA() && Number(el("duration").value) > 15)) return;
  const control = el("duration").closest(".duration-control");
  const tooltip = el("durationHint");
  const bounds = control.getBoundingClientRect();
  tooltip.style.left = `${bounds.left + bounds.width / 2}px`;
  tooltip.style.bottom = `${window.innerHeight - bounds.top + 8}px`;
}

async function api(url, options = {}) {
  const response = await fetch(url, { cache: "no-store", ...options });
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  if (!response.ok) {
    const detail = payload.detail;
    if (Array.isArray(detail)) {
      const message = detail.map((item) => {
        const field = Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(".") : "";
        return field ? `${field}：${item.msg}` : item.msg;
      }).filter(Boolean).join("；");
      throw new Error(message || `请求失败 (${response.status})`);
    }
    throw new Error(typeof detail === "string" ? detail : `请求失败 (${response.status})`);
  }
  return payload;
}

function updateModelUi() {
  const runningHubNode = selectedRunningHubNode();
  const runningHub = Boolean(runningHubNode?.runninghub_schema);
  syncRunningHubSchema();
  el("modelControl").hidden = Boolean(runningHubNode);
  el("executionControl").hidden = Boolean(runningHubNode);
  el("runningHubWorkflowControl").hidden = !runningHubNode;
  el("runningHubWorkflowName").textContent = runningHubNode
    ? `${runningHubNode.workflow_name || runningHubNode.name} · ${runningHubNode.runninghub_resource_type === "ai-app" ? "AI App" : "Workflow"}`
    : "";
  const music3 = !runningHub && isMusic3();
  const music3ExecutionOption = el("music3ExecutionOption");
  music3ExecutionOption.hidden = !music3;
  if (music3) {
    el("executionMode").value = "music3";
  } else if (selectedExecutionMode() === "music3") {
    el("executionMode").value = "native";
  }
  el("executionMode").disabled = music3;
  const nsfw = selectedExecutionMode() === "h3-nsfw";
  const digitalHuman = isDigitalHuman();
  const dualSampling = isDualSampling();
  const h3Sa = isH3SA();
  const vdnH3 = isVDNH3();
  const tts = isTTS();
  const fl2vaOption = el("modelVariant").querySelector('option[value="fl2va-fp8"]');
  fl2vaOption.disabled = nsfw || digitalHuman || tts || dualSampling;
  if (nsfw || digitalHuman || tts || dualSampling) el("modelVariant").value = "ref2va-fp8";
  el("modelVariant").disabled = digitalHuman || tts || dualSampling;
  const ref2va = isRef2VA();
  const accelerated = selectedExecutionMode() === "turbo-lora";
  const stepsMode = el("steps").dataset.mode;
  const nextStepsMode = music3 ? "music3" : vdnH3 ? "vdn-h3" : "h3";
  if (stepsMode !== nextStepsMode) {
    el("steps").value = music3 ? "30" : vdnH3 ? "50" : "10";
    el("steps").dataset.mode = nextStepsMode;
  }
  el("steps").min = vdnH3 ? "8" : "4";
  el("steps").max = "50";
  el("steps").step = vdnH3 ? "1" : "1";
  const duration = el("duration");
  const maxDuration = music3 || h3Sa ? 300 : 15;
  const defaultDuration = music3 ? 60 : 5;
  const currentDuration = Number(duration.value);
  duration.min = "1";
  duration.max = String(maxDuration);
  duration.value = Number.isFinite(currentDuration) && currentDuration >= 1 && currentDuration <= maxDuration
    ? String(currentDuration)
    : String(defaultDuration);
  if (music3 || accelerated || digitalHuman || h3Sa) {
    el("steps").value = music3 ? "30" : accelerated ? "8" : digitalHuman ? "20" : "8";
  } else if (vdnH3) {
    const vdnSteps = Number(el("steps").value);
    if (!Number.isInteger(vdnSteps) || vdnSteps < 8 || vdnSteps > 50) el("steps").value = "50";
  }
  el("steps").disabled = music3 || accelerated || digitalHuman || h3Sa || runningHub;
  el("duration").disabled = digitalHuman;
  const durationControl = el("duration").closest(".duration-control");
  durationControl.classList.toggle("digital-human", digitalHuman);
  durationControl.classList.toggle("h3-sa", h3Sa && Number(duration.value) > 15);
  durationControl.title = state.locale === "en"
    ? digitalHuman ? "Video length follows the driving audio" : music3 ? "Maximum music duration" : h3Sa ? "H3 SA duration; longer videos are stitched automatically" : "Video duration"
    : digitalHuman ? "视频长度由驱动音频长度决定" : music3 ? "音乐最长时长" : h3Sa ? "H3 SA 时长，超过 15 秒时自动拼接" : "视频时长";
  el("durationHint").hidden = !digitalHuman;
  if (h3Sa && Number(el("duration").value) > 15) el("durationHint").hidden = false;
  el("durationHint").textContent = state.locale === "en"
    ? digitalHuman ? "Video length follows the driving audio" : h3Sa ? "Over 15 seconds is stitched automatically" : "Video duration"
    : digitalHuman ? "视频长度由驱动音频长度决定" : h3Sa ? "超过 15 秒时系统自动连续拼接" : "视频时长";
  const runningHubKinds = new Set(runningHubMediaFields().map((field) => field.media_kind));
  referenceInput.accept = runningHub
    ? [...runningHubKinds].map((kind) => kind === "file" ? "*/*" : `${kind}/*`).join(",")
    : music3 ? "" : tts ? "audio/*" : digitalHuman ? "image/*,audio/*" : dualSampling ? "image/*" : ref2va ? "image/*,video/*,audio/*" : "image/*";
  el("addReference").title = state.locale === "en"
    ? runningHub ? "Add a workflow input file" : tts ? "Add up to three character voice references" : digitalHuman ? "Add portrait and driving audio" : dualSampling ? "Add image references for dual sampling" : ref2va ? "Add image, video, or audio references" : "Add first or last frame"
    : runningHub ? "添加工作流输入文件" : tts ? "添加最多 3 段人物音频参考" : digitalHuman ? "添加人物图片和驱动音频" : dualSampling ? "添加双采图片参考" : ref2va ? "添加图片、视频或音频参考" : "添加首帧或尾帧";
  el("addReference").setAttribute("aria-label", el("addReference").title);
  el("addReference").hidden = music3 || (runningHub && runningHubKinds.size === 0);
  el("aspectControl").hidden = music3 || tts || runningHub;
  el("resolutionControl").hidden = music3 || tts || runningHub;
  el("duration").closest(".duration-control").hidden = runningHub;
  el("stepsControl").hidden = runningHub || h3Sa;
  el("lyrics").hidden = !music3;
  el("globalSeedControl").hidden = runningHub;
  // SA tuning uses the validated server defaults. Keep the controls in the
  // DOM for backward-compatible saved settings, but do not expose them.
  el("saSettings").hidden = true;
  el("stepsControl").title = state.locale === "en" ? music3 ? "Music3 uses 30 steps" : h3Sa ? "H3 SA uses 8 LoRA steps" : vdnH3 ? "VDN-H3 uses 8 to 50 steps; default 50" : "Sampling steps" : music3 ? "Music3 固定使用 30 步" : h3Sa ? "H3 SA 固定使用 8 步 LoRA" : vdnH3 ? "VDN-H3 可使用 8–50 步，默认 50 步" : "采样步数";
  el("optimizePrompt").hidden = runningHub;
  el("optimizePrompt").title = state.locale === "en" ? music3 ? "Optimize style" : tts ? "Optimize TTS dialogue prompt" : "Optimize prompt" : music3 ? "优化曲风" : tts ? "优化 TTS 对话提示词" : "优化提示词";
  el("optimizePrompt").setAttribute("aria-label", el("optimizePrompt").title);
  el("optimizePromptLabel").textContent = el("optimizePrompt").title;
  el("writeLyrics").hidden = !music3;
  el("writeLyrics").title = localized("优化歌词", "Optimize lyrics");
  el("writeLyrics").setAttribute("aria-label", el("writeLyrics").title);
  el("writeLyrics").querySelector("span").textContent = el("writeLyrics").title;
  const primaryText = selectedRunningHubSchema()?.fields?.find((field) => field.key === selectedRunningHubSchema()?.primary_text_key);
  promptInput.placeholder = runningHub
    ? primaryText
      ? runningHubFieldLabel(primaryText)
      : localized("该工作流没有主文本输入，可留空", "This workflow has no primary text input; this field may be empty")
    : state.locale === "en"
      ? music3 ? "Describe genre, mood, tempo, key, instruments, vocals, and arrangement..." : tts ? "Describe each speaker's age, personality, delivery, and exact dialogue..." : "Describe the scene, characters, action, camera, and sound..."
      : music3 ? "描述曲风、情绪、速度、调式、乐器、人声与编曲…" : tts ? "描述人物年龄、性格、说话方式和需要生成的完整对白…" : "输入自然语言，描述场景、人物、动作、镜头与声音…";
  el("dropZone").title = localized("可拖入本地文件或素材库生成产物", "Drop local files or generated assets from the library");
  renderReferences();
  const error = validateReferenceSet(state.references);
  showError(state.references.length ? error : "");
}

function addFiles(files, forcedFieldKey = "") {
  if (state.editingJobId) {
    showError(localized("修改排队任务时不能更换参考素材", "Reference files cannot be changed while editing a queued task"));
    return false;
  }
  let error = "";
  const runningHubSchema = selectedRunningHubSchema();
  Array.from(files).forEach((file, fileIndex) => {
    let kind = kindFor(file);
    if (runningHubSchema) {
      const requestedKey = fileIndex === 0 ? forcedFieldKey : "";
      const requestedField = requestedKey
        ? runningHubMediaFields("", runningHubSchema).find((field) => field.key === requestedKey)
        : null;
      if (requestedField?.media_kind === "file") kind = "file";
      if (!kind) {
        error = localized(`不支持的素材类型：${file.name}`, `Unsupported file type: ${file.name}`);
        return;
      }
      if (requestedField && requestedField.media_kind !== kind) {
        error = localized(`该字段需要${{ image: "图片", video: "视频", audio: "音频", file: "普通" }[requestedField.media_kind]}文件`, `This field requires a ${requestedField.media_kind} file`);
        return;
      }
      if (requestedField) {
        const existingIndex = state.references.findIndex((item) => item.field_key === requestedField.key);
        if (existingIndex >= 0) {
          const [existing] = state.references.splice(existingIndex, 1);
          if (existing?.url) URL.revokeObjectURL(existing.url);
        }
      }
      const field = requestedField || runningHubAvailableMediaField(kind) || runningHubAvailableMediaField("file");
      if (!field) {
        error = localized(`工作流没有可用的${{ image: "图片", video: "视频", audio: "音频", file: "普通文件" }[kind]}字段`, `The workflow has no available ${kind} field`);
        return;
      }
      kind = field.media_kind;
      state.references.push({
        file,
        kind,
        field_key: field.key,
        name: file.name,
        size: file.size,
        url: URL.createObjectURL(file),
      });
      return;
    }
    if (!kind) {
      error = localized(`不支持的素材类型：${file.name}`, `Unsupported file type: ${file.name}`);
      return;
    }
    const limits = referenceLimits();
    const current = state.references.filter((item) => (item.kind || item.type) === kind).length;
    if (!limits[kind]) {
      error = isTTS()
        ? localized(`H3 TTS 仅支持音频参考：${file.name}`, `H3 TTS accepts audio references only: ${file.name}`)
        : isDigitalHuman()
        ? localized(`数字人模式仅支持人物图片和驱动音频：${file.name}`, `Digital human mode only accepts a portrait and driving audio: ${file.name}`)
        : localized(`FL2VA 仅支持图片：${file.name}`, `FL2VA only accepts images: ${file.name}`);
      return;
    }
    if (current >= limits[kind]) {
      error = isTTS()
        ? localized("H3 TTS 最多添加 3 段人物音频参考", "H3 TTS accepts up to three character voice references")
        : isRef2VA()
        ? localized(`${{ image: "图片", video: "视频", audio: "音频" }[kind]}最多添加 ${limits[kind]} 份`, `Up to ${limits[kind]} ${kind} files are allowed`)
        : localized("最多添加首帧和尾帧两张图片", "Up to two images are allowed for the first and last frames");
      return;
    }
    state.references.push({
      file,
      kind,
      name: file.name,
      size: file.size,
      url: URL.createObjectURL(file),
    });
  });
  state.pendingRunningHubMediaField = "";
  showError(error);
  renderReferences();
  return !error;
}

function clipboardImageFile(event) {
  const items = Array.from(event.clipboardData?.items || []);
  const item = items.find((entry) => entry.kind === "file" && entry.type.startsWith("image/"));
  const blob = item?.getAsFile();
  if (!blob) return null;
  const mime = blob.type || item.type || "image/png";
  const extension = mime.split("/", 2)[1]?.replace("jpeg", "jpg") || "png";
  return new File([blob], `pasted-image-${Date.now()}.${extension}`, {
    type: mime,
    lastModified: Date.now(),
  });
}

function renderReferences() {
  const labels = referenceLabels();
  el("referenceList").innerHTML = state.references.map((item, index) => {
    const kind = item.kind || item.type;
    const name = item.name || item.file?.name || "reference";
    const media = item.url && kind === "image"
      ? `<img src="${escapeHtml(item.url)}" alt="${escapeHtml(name)}">`
      : item.url && kind === "video"
        ? `<video src="${escapeHtml(item.url)}" muted playsinline preload="metadata" aria-label="${escapeHtml(name)}"></video>`
        : `<span class="reference-type">${icon(kind === "video" ? "film" : kind === "audio" ? "audio-lines" : kind === "file" ? "file" : "image")}</span>`;
    const thumb = item.url
      ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer" class="reference-link" aria-label="查看${escapeHtml(name)}">${media}</a>`
      : media;
    return `<div class="reference-chip" title="${escapeHtml(name)}">
      <span class="reference-preview">${thumb}</span>
      <span class="reference-info"><b>${escapeHtml(labels[index])}</b><small>${escapeHtml(name)}${item.size ? ` · ${formatBytes(item.size)}` : ""}</small></span>
      ${item.remote ? "" : `<button type="button" data-remove-reference="${index}" title="移除素材" aria-label="移除素材">${icon("x")}</button>`}
    </div>`;
  }).join("");
  renderRunningHubParameters();
  renderMentionMenu();
  refreshIcons();
}

function renderMentionMenu() {
  const references = state.references
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => (item.kind || item.type) === "image");
  const section = el("mentionReferenceSection");
  section.hidden = (!selectedRunningHubSchema() && isMusic3()) || !references.length;
  el("mentionReferenceList").innerHTML = references.map(({ item, index }) => {
    const name = item.name || item.file?.name || localized("未命名图片", "Untitled image");
    const preview = item.url
      ? `<img src="${escapeHtml(item.url)}" alt="">`
      : icon("image");
    return `<button class="mention-menu-item mention-reference-item" id="mentionReference${index}" type="button" role="menuitem" data-mention-reference="${index}" title="${escapeHtml(name)}">
      <span class="mention-reference-thumb">${preview}</span>
      <span class="mention-reference-name">${escapeHtml(name)}</span>
    </button>`;
  }).join("");
  if (el("mentionMenu").dataset.open === "true") setMentionIndex(0);
}

function mentionMenuItems() {
  return Array.from(el("mentionMenu").querySelectorAll(".mention-menu-item"))
    .filter((item) => !item.disabled && item.getClientRects().length > 0);
}

function setMentionIndex(index, scroll = true) {
  const items = mentionMenuItems();
  if (!items.length) {
    state.mentionIndex = -1;
    promptInput.removeAttribute("aria-activedescendant");
    return;
  }
  state.mentionIndex = ((index % items.length) + items.length) % items.length;
  items.forEach((item, itemIndex) => item.classList.toggle("is-active", itemIndex === state.mentionIndex));
  const active = items[state.mentionIndex];
  promptInput.setAttribute("aria-activedescendant", active.id);
  if (scroll) active.scrollIntoView({ block: "nearest" });
}

function textareaCaretRect(textarea) {
  const style = window.getComputedStyle(textarea);
  const mirror = document.createElement("div");
  const copied = [
    "boxSizing", "width", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
    "borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth",
    "fontFamily", "fontSize", "fontStyle", "fontWeight", "lineHeight", "letterSpacing",
    "textTransform", "textIndent", "wordSpacing", "tabSize",
  ];
  copied.forEach((property) => { mirror.style[property] = style[property]; });
  const bounds = textarea.getBoundingClientRect();
  mirror.style.position = "fixed";
  mirror.style.top = `${bounds.top}px`;
  mirror.style.left = `${bounds.left}px`;
  mirror.style.height = "auto";
  mirror.style.minHeight = "0";
  mirror.style.maxHeight = "none";
  mirror.style.overflow = "hidden";
  mirror.style.visibility = "hidden";
  mirror.style.whiteSpace = "pre-wrap";
  mirror.style.overflowWrap = "break-word";
  mirror.style.pointerEvents = "none";
  mirror.textContent = textarea.value.slice(0, textarea.selectionStart ?? 0);
  const marker = document.createElement("span");
  marker.textContent = "\u200b";
  mirror.append(marker);
  document.body.append(mirror);
  const markerBounds = marker.getBoundingClientRect();
  const lineHeight = Number.parseFloat(style.lineHeight) || Number.parseFloat(style.fontSize) * 1.65;
  const result = {
    left: markerBounds.left - textarea.scrollLeft,
    top: markerBounds.top - textarea.scrollTop,
    bottom: markerBounds.top - textarea.scrollTop + lineHeight,
  };
  mirror.remove();
  return result;
}

function positionMentionMenu() {
  const menu = el("mentionMenu");
  if (menu.dataset.open !== "true") return;
  const caret = textareaCaretRect(promptInput);
  const margin = 7;
  const gap = 6;
  const bounds = menu.getBoundingClientRect();
  let left = caret.left;
  let top = caret.bottom + gap;
  if (top + bounds.height > window.innerHeight - margin) top = caret.top - bounds.height - gap;
  left = Math.max(margin, Math.min(left, window.innerWidth - bounds.width - margin));
  top = Math.max(margin, Math.min(top, window.innerHeight - bounds.height - margin));
  menu.style.left = `${Math.round(left)}px`;
  menu.style.top = `${Math.round(top)}px`;
}

function openMentionMenu({ focusPrompt = false } = {}) {
  if (focusPrompt) promptInput.focus();
  el("mentionControl").dataset.open = "true";
  el("mentionMenu").dataset.open = "true";
  el("mentionTrigger").setAttribute("aria-expanded", "true");
  promptInput.setAttribute("aria-expanded", "true");
  setMentionIndex(0, false);
  requestAnimationFrame(positionMentionMenu);
}

function closeMentionMenu() {
  delete el("mentionControl").dataset.open;
  delete el("mentionMenu").dataset.open;
  el("mentionTrigger").setAttribute("aria-expanded", "false");
  promptInput.setAttribute("aria-expanded", "false");
  promptInput.removeAttribute("aria-activedescendant");
  state.mentionIndex = -1;
  mentionMenuItems().forEach((item) => item.classList.remove("is-active"));
}

function handleMentionKeydown(event) {
  const open = el("mentionMenu").dataset.open === "true";
  if (event.key === "@" && !event.metaKey && !event.ctrlKey && !event.altKey) {
    setTimeout(() => openMentionMenu(), 0);
    return false;
  }
  if (!open) return false;
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    setMentionIndex(state.mentionIndex + (event.key === "ArrowDown" ? 1 : -1));
    return true;
  }
  if (event.key === "Enter") {
    event.preventDefault();
    mentionMenuItems()[state.mentionIndex]?.click();
    return true;
  }
  if (event.key === "Escape") {
    event.preventDefault();
    closeMentionMenu();
    return true;
  }
  return false;
}

function insertReferenceMention(index) {
  const item = state.references[index];
  if (!item || (item.kind || item.type) !== "image") return;
  const name = item.name || item.file?.name || localized("未命名图片", "Untitled image");
  const start = promptInput.selectionStart ?? promptInput.value.length;
  const end = promptInput.selectionEnd ?? start;
  const replaceStart = start > 0 && promptInput.value[start - 1] === "@" ? start - 1 : start;
  const leadingSpace = replaceStart > 0 && !/\s/.test(promptInput.value[replaceStart - 1]) ? " " : "";
  const trailingSpace = end < promptInput.value.length && !/\s/.test(promptInput.value[end]) ? " " : "";
  const insertion = `${leadingSpace}@${name}${trailingSpace || " "}`;
  promptInput.setRangeText(insertion, replaceStart, end, "end");
  promptInput.focus();
  closeMentionMenu();
}

function removePendingMentionTrigger() {
  const start = promptInput.selectionStart ?? promptInput.value.length;
  if (start > 0 && promptInput.value[start - 1] === "@") {
    promptInput.setRangeText("", start - 1, start, "end");
  }
}

function getDimensions() {
  const ratio = el("aspectRatio").value;
  const preset = RESOLUTION_PRESETS.find((item) => item.value === el("resolution").value) || RESOLUTION_PRESETS[2];
  if (ratio === "9:16") return [preset.height, preset.width];
  if (ratio === "1:1") {
    const edge = Math.max(352, Math.round(Math.sqrt(preset.width * preset.height) / 32) * 32);
    return [edge, edge];
  }
  return [preset.width, preset.height];
}

function setDimensions(width, height) {
  el("aspectRatio").value = width === height ? "1:1" : width > height ? "16:9" : "9:16";
  const landscapeWidth = Math.max(width, height);
  const landscapeHeight = Math.min(width, height);
  const targetArea = width * height;
  const preset = RESOLUTION_PRESETS.find((item) => item.width === landscapeWidth && item.height === landscapeHeight)
    || RESOLUTION_PRESETS.reduce((closest, item) => (
      Math.abs(item.width * item.height - targetArea) < Math.abs(closest.width * closest.height - targetArea)
        ? item
        : closest
    ));
  el("resolution").value = preset.value;
}

async function checkHealth() {
  try {
    const data = await api("/health");
    renderHealthState(data.nodes || [], data.queue_depth || 0);
  } catch {
    el("healthDot").className = "status-dot offline";
    el("healthText").textContent = t("offline");
  }
}

async function loadAssets({ reset = false } = {}) {
  if (state.assetLoading || (!reset && !state.assetHasMore)) return;
  const requestedPage = reset ? 1 : state.assetPage + 1;
  const params = new URLSearchParams({ page: requestedPage, page_size: state.assetPageSize, scope: jobScope() });
  const filter = el("assetStatusFilter").value;
  const query = el("assetSearch").value.trim();
  if (filter) params.set("status", filter);
  if (query) params.set("query", query);
  state.assetLoading = true;
  if (reset) {
    state.assets = [];
    state.assetTotal = 0;
    state.assetPage = 0;
    state.assetHasMore = true;
    state.assetLoadError = "";
    el("assetGrid").scrollTop = 0;
  }
  renderAssets();
  try {
    const endpoint = state.incognito ? "/api/v1/generations" : "/api/v1/peering/library";
    const payload = await api(`${endpoint}?${params}`);
    state.assets = reset ? payload.data : dedupeJobs([...state.assets, ...payload.data]);
    state.sharedAssetErrors = payload.peer_errors || [];
    state.assetRevision = payload.store_revision || state.assetRevision;
    state.assetPages = payload.pages;
    state.assetTotal = payload.total;
    state.assetPage = requestedPage;
    state.assetHasMore = requestedPage < payload.pages;
    state.assetLoadError = "";
    state.storeRevision = Math.max(state.storeRevision, payload.store_revision || 0);
    renderAssets(payload.total);
  } catch (error) {
    state.assetLoadError = error.message;
  } finally {
    state.assetLoading = false;
    renderAssets();
  }
}

function assetAction(job) {
  const jobId = escapeHtml(job.id);
  if (job.peer_asset) {
    const inputAction = job.status === "completed" && job.result_url
      ? `<button type="button" data-asset-input="${jobId}" title="${t("useAsInput")}" aria-label="${t("useAsInput")}">${icon("file-input")}</button>`
      : "";
    return inputAction ? `<span class="asset-actions">${inputAction}</span>` : "";
  }
  if (job.status === "queued") {
    return `<span class="asset-actions"><button type="button" data-job-action="edit" data-job-id="${jobId}" title="修改" aria-label="修改">${icon("pencil")}</button><button type="button" data-job-action="cancel" data-job-id="${jobId}" title="取消" aria-label="取消">${icon("square")}</button></span>`;
  }
  if (job.status === "running") {
    return `<span class="asset-actions"><button type="button" data-job-action="cancel" data-job-id="${jobId}" title="取消" aria-label="取消">${icon("square")}</button></span>`;
  }
  const inputAction = job.status === "completed" && job.result_url
    ? `<button type="button" data-asset-input="${jobId}" title="${t("useAsInput")}" aria-label="${t("useAsInput")}">${icon("file-input")}</button>`
    : "";
  return `<span class="asset-actions">${inputAction}<button type="button" data-job-action="delete" data-job-id="${jobId}" title="删除" aria-label="删除">${icon("trash-2")}</button></span>`;
}

function renderAssetCard(job) {
  const mediaType = jobMediaType(job);
  const audio = mediaType === "audio";
  const preview = job.asset_deleted
    ? `<span class="asset-placeholder deleted">${icon("file-x-2")}<b>${t("assetDeleted")}</b></span>`
    : job.status === "completed" && job.result_url
    ? audio
      ? `<span class="asset-audio-icon" aria-hidden="true">${icon("audio-lines")}</span>`
      : mediaType === "image"
        ? `<img src="${escapeHtml(job.result_url)}" alt="${escapeHtml(modelLabel(job))}" loading="lazy">`
        : mediaType === "file"
          ? `<span class="asset-audio-icon" aria-hidden="true">${icon("file")}</span>`
          : `<video src="${escapeHtml(job.result_url)}" muted playsinline preload="metadata" aria-label="${escapeHtml(modelLabel(job))} 生成视频"></video><span class="asset-play">${icon("play")}</span>`
    : `<span class="asset-placeholder ${job.status}">${icon(job.status === "running" ? "loader-circle" : job.status === "queued" ? "clock-3" : job.status === "failed" ? "triangle-alert" : "circle-slash-2")}${job.status === "running" ? `<b>${job.progress || 0}%</b>` : ""}</span>`;
  const draggable = job.status === "completed" && job.result_url ? "true" : "false";
  const owner = job.owner_name ? `<span class="asset-owner" title="${t("owner")}: ${escapeHtml(job.owner_name)}">${icon("tag")}<span>${escapeHtml(job.owner_name)}</span></span>` : "";
  return `<article class="asset-card" data-asset-job="${escapeHtml(job.id)}" data-asset-output="${draggable}" draggable="${draggable}" tabindex="0" aria-label="${escapeHtml(executionModeLabel(job))}, ${escapeHtml(modelLabel(job))}, ${escapeHtml(statusLabel(job.status))}">
    <div class="asset-preview${audio || mediaType === "file" ? " music" : ""}">${preview}${assetAction(job)}</div>
    <div class="asset-meta"><span class="task-status ${job.status}"></span><strong>${escapeHtml(modelLabel(job))}</strong><small class="asset-plan ${executionModeClass(job)}">${escapeHtml(executionModeLabel(job))}</small>${owner}<time>${escapeHtml(nodeLabel(job))}</time><time>${t("overallTime")} ${formatElapsed(job.elapsed_seconds)}</time></div>
  </article>`;
}

function updateAssetChrome() {
  el("assetTotal").textContent = state.assetTotal;
}

function renderAssets(total = state.assetTotal) {
  state.assetTotal = total;
  const cards = state.assets.map(renderAssetCard).join("");
  const empty = !state.assets.length && !state.assetLoading && !state.assetLoadError ? `<div class="library-empty">${icon("images")}<span>${t("noAssets")}</span></div>` : "";
  const error = state.assetLoadError ? `<p class="list-error">${escapeHtml(state.assetLoadError)}</p>` : "";
  const loadState = state.assetLoading
    ? `<div class="asset-load-state loading">${icon("loader-circle")}<span>${t("loading")}</span></div>`
    : state.assets.length && !state.assetHasMore
      ? `<div class="asset-load-state">${icon("check")}<span>${t("allLoaded")}</span></div>`
      : "";
  el("assetGrid").innerHTML = `${cards}${empty}${error}${loadState}`;
  updateAssetChrome();
  refreshIcons();
}

function dedupeJobs(jobs) {
  const seen = new Set();
  return jobs.filter((job) => {
    if (seen.has(job.id)) return false;
    seen.add(job.id);
    return true;
  });
}

function selectedConversationDeviceIds() {
  return Array.from(state.conversationDeviceIds).sort();
}

function conversationDeviceFilterSignature() {
  return selectedConversationDeviceIds().join(",");
}

async function refreshConversation(initial = false) {
  if (state.conversationLoading) {
    state.conversationRefreshPending = true;
    state.conversationRefreshResetPending ||= initial;
    return;
  }
  state.conversationLoading = true;
  try {
    const pageCount = initial ? 1 : Math.max(1, state.conversationPage);
    const selectedDevices = selectedConversationDeviceIds();
    const deviceFilterSignature = selectedDevices.join(",");
    const requests = Array.from({ length: pageCount }, (_, index) => {
      const params = new URLSearchParams({
        page: String(index + 1),
        page_size: String(state.conversationPageSize),
        scope: jobScope(),
      });
      if (selectedDevices.length && !state.incognito) params.set("device_ids", selectedDevices.join(","));
      const endpoint = state.incognito ? "/api/v1/generations" : "/api/v1/peering/conversations";
      return api(`${endpoint}?${params}`);
    });
    const payloads = await Promise.all(requests);
    if (deviceFilterSignature !== conversationDeviceFilterSignature()) {
      state.conversationRefreshPending = true;
      state.conversationRefreshResetPending = true;
      return;
    }
    const revisionSignature = `${payloads.map((payload) => payload.conversation_revision || payload.store_revision || 0).join("|")}|pages:${pageCount}|devices:${deviceFilterSignature}`;
    if (!initial && state.conversationRevisionSignature === revisionSignature) return;
    const revisions = payloads.map((payload) => payload.store_revision || 0).filter((revision) => revision > 0);
    state.conversationRevisionSignature = revisionSignature;
    state.conversationRevision = revisions.length ? Math.min(...revisions) : state.conversationRevision;
    state.storeRevision = Math.max(state.storeRevision, ...revisions, 0);
    state.conversationPages = payloads[0]?.pages || 1;
    updateConversationDevices(state.incognito ? [] : payloads[0]?.devices || []);
    state.conversationPage = Math.min(pageCount, state.conversationPages);
    state.conversations = dedupeJobs(payloads.flatMap((payload) => payload.data));
    renderConversationFeed(initial ? "bottom" : "preserve");
  } catch (error) {
    if (!state.conversations.length) {
      el("conversationFeed").innerHTML = `<p class="list-error">${escapeHtml(error.message)}</p>`;
    }
  } finally {
    state.conversationLoading = false;
    if (state.conversationRefreshPending) {
      const reset = state.conversationRefreshResetPending;
      state.conversationRefreshPending = false;
      state.conversationRefreshResetPending = false;
      queueMicrotask(() => refreshConversation(reset));
    }
  }
}

function elementFromHtml(markup) {
  const template = document.createElement("template");
  template.innerHTML = markup.trim();
  return template.content.firstElementChild;
}

function jobElement(container, attribute, jobId) {
  return Array.from(container.querySelectorAll(`[${attribute}]`)).find((item) => item.getAttribute(attribute) === jobId) || null;
}

function assetMatchesCurrentView(job) {
  if (Boolean(job.request?.incognito) !== state.incognito) return false;
  const filter = el("assetStatusFilter").value;
  if (filter && job.status !== filter) return false;
  const query = el("assetSearch").value.trim().toLocaleLowerCase();
  if (!query) return true;
  return [job.id, job.title, job.request?.prompt].some((value) => String(value || "").toLocaleLowerCase().includes(query));
}

function upsertAsset(job) {
  if (!job.peer_asset && state.peering) {
    job.owner_name = state.peering.machine_name;
    job.owner_device_id = state.peering.device_id;
  }
  const index = state.assets.findIndex((item) => item.id === job.id);
  const matches = assetMatchesCurrentView(job);
  const card = jobElement(el("assetGrid"), "data-asset-job", job.id);
  if (index >= 0 && !matches) {
    state.assets.splice(index, 1);
    state.assetTotal = Math.max(0, state.assetTotal - 1);
    card?.remove();
  } else if (index >= 0) {
    state.assets[index] = job;
    card?.replaceWith(elementFromHtml(renderAssetCard(job)));
  } else if (matches) {
    const newestTime = state.assets[0] ? new Date(state.assets[0].created_at).getTime() : 0;
    const jobTime = new Date(job.created_at).getTime();
    if (!state.assets.length || jobTime >= newestTime) {
      state.assets.unshift(job);
      state.assetTotal += 1;
      el("assetGrid").querySelector(".library-empty")?.remove();
      el("assetGrid").prepend(elementFromHtml(renderAssetCard(job)));
    }
  }
  if (!state.assets.length) el("assetGrid").innerHTML = `<div class="library-empty">${icon("images")}<span>${t("noAssets")}</span></div>`;
  state.assetPages = Math.max(1, Math.ceil(state.assetTotal / state.assetPageSize));
  updateAssetChrome();
  refreshIcons();
}

function upsertConversation(job) {
  const index = state.conversations.findIndex((item) => item.id === job.id);
  const current = jobElement(el("conversationFeed"), "data-job-id", job.id);
  const matches = conversationMatchesCurrentView(job);
  if (index >= 0 && !matches) {
    state.conversations.splice(index, 1);
    current?.remove();
  } else if (index >= 0) {
    state.conversations[index] = job;
    current?.replaceWith(elementFromHtml(renderJobExchange(job)));
  } else if (matches) {
    const newestTime = state.conversations[0] ? new Date(state.conversations[0].created_at).getTime() : 0;
    const jobTime = new Date(job.created_at).getTime();
    if (state.conversations.length && jobTime < newestTime) return;
    state.conversations.unshift(job);
    el("conversationFeed").querySelector(".chat-empty")?.remove();
    el("conversationFeed").append(elementFromHtml(renderJobExchange(job)));
    el("conversationFeed").scrollTop = el("conversationFeed").scrollHeight;
  }
  if (!state.conversations.length) el("conversationFeed").innerHTML = `<div class="chat-empty"><span>H3</span><h2>${t("startCreating")}</h2></div>`;
  refreshIcons();
}

function conversationMatchesCurrentView(job) {
  if (Boolean(job.request?.incognito) !== state.incognito) return false;
  if (state.incognito || state.conversationDeviceIds.size === 0) return true;
  const ownerDeviceId = String(job.owner_device_id || job.source?.device_id || "");
  return state.conversationDeviceIds.has(ownerDeviceId);
}

function applyJobUpsert(job) {
  upsertAsset(job);
  upsertConversation(job);
}

function applyJobDelete(jobId) {
  const assetIndex = state.assets.findIndex((item) => item.id === jobId);
  const conversationIndex = state.conversations.findIndex((item) => item.id === jobId);
  const knownJob = state.assets[assetIndex] || state.conversations[conversationIndex];
  if (assetIndex >= 0) state.assets.splice(assetIndex, 1);
  if (conversationIndex >= 0) state.conversations.splice(conversationIndex, 1);
  jobElement(el("assetGrid"), "data-asset-job", jobId)?.remove();
  jobElement(el("conversationFeed"), "data-job-id", jobId)?.remove();
  if (knownJob && assetMatchesCurrentView(knownJob)) state.assetTotal = Math.max(0, state.assetTotal - 1);
  if (!state.assets.length) el("assetGrid").innerHTML = `<div class="library-empty">${icon("images")}<span>${t("noAssets")}</span></div>`;
  if (!state.conversations.length) el("conversationFeed").innerHTML = `<div class="chat-empty"><span>H3</span><h2>${t("startCreating")}</h2></div>`;
  state.assetPages = Math.max(1, Math.ceil(state.assetTotal / state.assetPageSize));
  updateAssetChrome();
  refreshIcons();
}

async function loadOlderMessages() {
  if (state.conversationLoading || state.conversationPage >= state.conversationPages) return;
  state.conversationLoading = true;
  try {
    const nextPage = state.conversationPage + 1;
    const deviceFilterSignature = conversationDeviceFilterSignature();
    const params = new URLSearchParams({
      page: String(nextPage),
      page_size: String(state.conversationPageSize),
      scope: jobScope(),
    });
    const selectedDevices = selectedConversationDeviceIds();
    if (selectedDevices.length && !state.incognito) params.set("device_ids", selectedDevices.join(","));
    const endpoint = state.incognito ? "/api/v1/generations" : "/api/v1/peering/conversations";
    const payload = await api(`${endpoint}?${params}`);
    if (deviceFilterSignature !== conversationDeviceFilterSignature()) {
      state.conversationRefreshPending = true;
      state.conversationRefreshResetPending = true;
      return;
    }
    state.storeRevision = Math.max(state.storeRevision, payload.store_revision || 0);
    state.conversationPage = nextPage;
    state.conversationPages = payload.pages;
    state.conversations = dedupeJobs([...state.conversations, ...payload.data]);
    renderConversationFeed("prepend");
  } catch (error) {
    showError(error.message);
  } finally {
    state.conversationLoading = false;
    if (state.conversationRefreshPending) {
      const reset = state.conversationRefreshResetPending;
      state.conversationRefreshPending = false;
      state.conversationRefreshResetPending = false;
      queueMicrotask(() => refreshConversation(reset));
    }
  }
}

function updateConversationDevices(devices) {
  state.conversationDevices = devices;
  const select = el("conversationDeviceFilter");
  if (!select) return;
  select.innerHTML = devices.map((device) => `<option value="${escapeHtml(device.device_id)}">${escapeHtml(device.name)}${device.local ? " · 本机" : ""}</option>`).join("");
  Array.from(select.options).forEach((option) => { option.selected = state.conversationDeviceIds.has(option.value); });
  el("conversationFilters").hidden = devices.length < 2;
  if (devices.length < 2) {
    state.conversationFilterOpen = false;
    el("conversationFilterPanel").hidden = true;
    el("conversationFilterToggle").setAttribute("aria-expanded", "false");
  }
  updateConversationFilterChrome();
}

function updateConversationFilterChrome() {
  const select = el("conversationDeviceFilter");
  const count = el("conversationFilterCount");
  if (!select || !count) return;
  const selected = Array.from(select.selectedOptions);
  count.textContent = selected.length === 0
    ? "全部"
    : selected.length === 1
      ? selected[0].textContent
      : `${selected.length} 个设备`;
}

async function refreshSharedRuntime() {
  try {
    const payload = await api("/api/v1/peering/runtime");
    const localNodes = (payload.nodes || []).filter((node) => !node.remote_proxy);
    state.localRuntime = {
      nodes: localNodes,
      queue: payload.queue || [],
      logs: (payload.logs || []).filter((item) => !item.remote),
    };
    state.peerRuntime = {};
    (payload.logs || []).filter((item) => item.remote && item.owner_device_id).forEach((item) => {
      const runtime = state.peerRuntime[item.owner_device_id] || { nodes: [], queue: [], logs: [] };
      runtime.logs.push(item);
      state.peerRuntime[item.owner_device_id] = runtime;
    });
    (payload.nodes || []).filter((node) => node.remote_proxy && node.owner_device_id).forEach((node) => {
      const runtime = state.peerRuntime[node.owner_device_id] || { nodes: [], queue: [], logs: [] };
      runtime.nodes.push(node);
      state.peerRuntime[node.owner_device_id] = runtime;
    });
    renderCombinedRuntime();
    state.runtimeRevision = payload.revision || state.runtimeRevision;
  } catch (error) {
    if (!el("peeringModal").hidden) el("peeringError").textContent = error.message;
  }
}

async function refreshProxyJobs() {
  const active = state.conversations.filter((job) => job.request?.remote_proxy && isActive(job));
  const results = await Promise.allSettled(active.map((job) => api(`/api/v1/generations/${encodeURIComponent(job.id)}`)));
  results.forEach((result) => { if (result.status === "fulfilled") applyJobUpsert(result.value); });
}

function referenceSummary(job) {
  const references = job.request?.references || [];
  const labels = referenceLabels(
    references,
    job.request?.model_variant || "fl2va-fp8",
    job.request?.execution_mode || "native",
    job.request?.runninghub_schema || null,
  );
  if (!references.length) return "";
  return `<div class="message-assets">${references.map((item, index) => {
    const itemIcon = item.type === "image" ? "image" : item.type === "video" ? "film" : "audio-lines";
    const name = item.name || "参考素材";
    const url = item.url || `/api/v1/generations/${encodeURIComponent(job.id)}/references/${index}`;
    let preview = `<span class="message-asset-icon">${icon(itemIcon)}</span>`;
    if (item.type === "image") {
      preview = `<img src="${escapeHtml(url)}" alt="${escapeHtml(name)}" loading="lazy">`;
    } else if (item.type === "video") {
      preview = `<video src="${escapeHtml(url)}" controls playsinline preload="metadata" aria-label="${escapeHtml(name)}"></video>`;
    } else if (item.type === "audio") {
      preview = `<audio src="${escapeHtml(url)}" controls preload="metadata" aria-label="${escapeHtml(name)}"></audio>`;
    }
    return `<a class="message-asset" href="${escapeHtml(url)}" target="_blank" rel="noreferrer" title="查看${escapeHtml(name)}">${preview}<span class="message-asset-copy"><b>${escapeHtml(labels[index])}</b><small>${escapeHtml(name)}</small></span></a>`;
  }).join("")}</div>`;
}

function messageActions(job) {
  if (job.peer_asset) return job.status === "completed" && job.result_url
    ? `<div class="message-actions"><button type="button" data-job-action="input" data-job-id="${job.id}">${icon("file-input")}<span>${t("useAsInput")}</span></button></div>`
    : "";
  if (job.request?.remote_proxy) {
    const buttons = [];
    if (job.status === "completed" && job.result_url) {
      buttons.push(`<button type="button" data-job-action="input" data-job-id="${job.id}">${icon("file-input")}<span>${t("useAsInput")}</span></button>`);
    }
    if (isActive(job)) {
      buttons.push(`<button type="button" class="cancel" data-job-action="cancel" data-job-id="${job.id}">${icon("square")}<span>${t("cancel")}</span></button>`);
    } else {
      buttons.push(`<button type="button" class="danger" data-job-action="delete" data-job-id="${job.id}">${icon("trash-2")}<span>${t("delete")}</span></button>`);
    }
    return `<div class="message-actions">${buttons.join("")}</div>`;
  }
  const buttons = [`<button type="button" data-job-action="reuse" data-job-id="${job.id}">${icon("corner-down-left")}<span>${t("reuse")}</span></button>`];
  if (job.status === "completed" && job.result_url) {
    buttons.push(`<button type="button" data-job-action="input" data-job-id="${job.id}">${icon("file-input")}<span>${t("useAsInput")}</span></button>`);
  }
  if (job.status === "queued") {
    buttons.push(`<button type="button" data-job-action="edit" data-job-id="${job.id}">${icon("pencil")}<span>${t("edit")}</span></button>`);
  }
  if (isActive(job)) {
    buttons.push(`<button type="button" class="cancel" data-job-action="cancel" data-job-id="${job.id}">${icon("square")}<span>${t("cancel")}</span></button>`);
  } else {
    buttons.push(`<button type="button" class="regenerate" data-job-action="regenerate" data-job-id="${job.id}" title="${t("regenerate")}" aria-label="${t("regenerate")}">${icon("rotate-ccw")}<span>${t("regenerate")}</span></button>`);
    buttons.push(`<button type="button" class="danger" data-job-action="delete" data-job-id="${job.id}">${icon("trash-2")}<span>${t("delete")}</span></button>`);
  }
  return `<div class="message-actions">${buttons.join("")}</div>`;
}

function renderJobExchange(job) {
  const request = job.request || {};
  const mediaType = jobMediaType(job);
  const audio = mediaType === "audio";
  const runningHub = request.provider === "runninghub";
  const active = isActive(job);
  const detail = job.error || (job.queue_position ? `${t("queuePosition")} ${job.queue_position}` : job.stage);
  const sourceLabel = job.owner_name ? `<span class="message-source">${icon("tag")} ${escapeHtml(job.owner_name)}</span>` : "";
  const incognito = request.incognito
    ? `<span class="message-mode">${icon("scan-eye")} ${t("incognito")}${job.expires_at ? ` · ${formatTime(job.expires_at, true)} ${t("destroy")}` : ""}</span>`
    : "";
  const executionMode = `<span class="message-plan ${executionModeClass(job)}">${executionModeLabel(job)}</span>`;
  const elapsed = `<span>${t("overallTime")} ${formatElapsed(job.elapsed_seconds)}</span>`;
  let assistantBody = "";
  if (active) {
    assistantBody = `<div class="generation-progress">
      <div><span class="progress-stage"><i></i>${escapeHtml(job.stage || statusLabel(job.status))}</span><b>${job.progress || 0}%</b></div>
      <div class="progress-track"><span style="width:${Math.max(0, Math.min(100, job.progress || 0))}%"></span></div>
      <small>${escapeHtml(detail || statusLabel(job.status))}</small>
    </div>`;
  } else if (job.asset_deleted) {
    assistantBody = `<p class="terminal-state completed">${t("assetDeleted")}</p>`;
  } else if (job.status === "completed") {
    const result = audio
      ? `<div class="audio-result"><audio controls preload="metadata" src="${job.result_url}"></audio><a href="${job.result_url}" download>${icon("download")}<span>${mediaDownloadLabel(mediaType)}</span></a></div>`
      : mediaType === "image"
        ? `<div class="image-result"><img src="${job.result_url}" alt="${escapeHtml(shortTitle(job))}"><a href="${job.result_url}" download>${icon("download")}<span>${mediaDownloadLabel(mediaType)}</span></a></div>`
        : mediaType === "file"
          ? `<div class="file-result"><a href="${job.result_url}" download>${icon("download")}<span>${mediaDownloadLabel(mediaType)}</span></a></div>`
          : `<div class="video-result"><video controls playsinline preload="metadata" src="${job.result_url}"></video><a href="${job.result_url}" download>${icon("download")}<span>${mediaDownloadLabel(mediaType)}</span></a></div>`;
    assistantBody = `<p class="terminal-state completed">${mediaReadyLabel(mediaType)}</p>${result}`;
  } else {
    assistantBody = `<p class="terminal-state ${job.status}">${escapeHtml(detail || statusLabel(job.status))}</p>`;
  }
  return `<section class="exchange" id="job-${job.id}" data-job-id="${job.id}">
    <article class="message user-message">
      <div class="message-avatar user-avatar">${t("you")}</div>
      <div class="message-body">${referenceSummary(job)}<div class="message-text">${escapeHtml(request.prompt || request.runninghub_workflow_name || "")}${audio && request.lyrics ? `\n\n${escapeHtml(request.lyrics)}` : ""}</div><div class="message-meta">${sourceLabel}${executionMode}<span>${modelLabel(job)}</span><span>${escapeHtml(nodeLabel(job))}</span>${runningHub || audio ? "" : `<span>${request.width} × ${request.height}</span>`}${runningHub ? "" : `<span>${request.duration}${t("seconds")}</span><span>${request.steps} ${t("steps")}</span><span>${t("seed")} ${request.seed}</span>`}${elapsed}${incognito}</div></div>
    </article>
    <article class="message assistant-message">
      <div class="message-avatar assistant-avatar">H3</div>
      <div class="message-body"><div class="assistant-heading"><strong>${statusLabel(job.status)}</strong><span>${formatTime(job.updated_at || job.created_at, true)}</span></div>${assistantBody}${messageActions(job)}</div>
    </article>
  </section>`;
}

function renderConversationFeed(mode = "preserve") {
  const feed = el("conversationFeed");
  if (mode === "bottom") state.conversationReady = false;
  const oldHeight = feed.scrollHeight;
  const oldTop = feed.scrollTop;
  const nearBottom = oldHeight - oldTop - feed.clientHeight < 160;
  const timeline = [...state.conversations]
    .reverse()
    .map((job) => ({ type: "job", at: job.created_at, data: job }))
    .sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
  const content = timeline.map((item) => renderJobExchange(item.data)).join("");
  feed.innerHTML = content || `<div class="chat-empty"><span>H3</span><h2>${t("startCreating")}</h2></div>`;
  refreshIcons();
  requestAnimationFrame(() => {
    if (mode === "bottom" || (mode === "preserve" && nearBottom)) {
      feed.scrollTop = feed.scrollHeight;
    } else if (mode === "prepend") {
      feed.scrollTop = oldTop + (feed.scrollHeight - oldHeight);
    } else {
      feed.scrollTop = oldTop;
    }
    state.conversationScrollTop = feed.scrollTop;
    requestAnimationFrame(() => { state.conversationReady = true; });
  });
}

async function scrollToJob(jobId) {
  closeAssetDrawer();
  let target = el(`job-${jobId}`);
  while (!target && state.conversationPage < state.conversationPages) {
    const previousPage = state.conversationPage;
    await loadOlderMessages();
    target = el(`job-${jobId}`);
    if (state.conversationPage === previousPage) break;
  }
  target?.scrollIntoView({ behavior: "smooth", block: "center" });
}

function assetDetailFile(item, index, job) {
  const url = item.url || `/api/v1/generations/${encodeURIComponent(job.id)}/references/${index}`;
  const name = item.name || `${item.type || "file"}-${index + 1}`;
  let media = `<span class="asset-detail-file-media">${icon(item.type === "video" ? "film" : item.type === "audio" ? "audio-lines" : "image")}</span>`;
  if (item.type === "image") media = `<span class="asset-detail-file-media"><img src="${escapeHtml(url)}" alt="${escapeHtml(name)}" loading="lazy"></span>`;
  if (item.type === "video") media = `<span class="asset-detail-file-media"><video src="${escapeHtml(url)}" muted playsinline preload="metadata"></video></span>`;
  return `<a class="asset-detail-file" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${media}<div><b>${escapeHtml(name)}</b><small>${escapeHtml(item.type || "file")}${item.size ? ` · ${formatBytes(item.size)}` : ""}</small></div></a>`;
}

function runningHubParameterFacts(request) {
  const schema = request.runninghub_schema;
  const parameters = request.runninghub_parameters || {};
  if (!schema || !Array.isArray(schema.fields)) return [];
  return schema.fields
    .filter((field) => field.editable !== false && !field.media_kind && field.key !== schema.primary_text_key)
    .map((field) => {
      const raw = parameters[field.key];
      const option = (field.options || []).find((item) => String(item.value) === String(raw));
      const value = option?.label || (typeof raw === "boolean" ? localized(raw ? "开启" : "关闭", raw ? "On" : "Off") : String(raw ?? ""));
      return `${runningHubFieldLabel(field)}: ${value.slice(0, 160)}`;
    });
}

function renderAssetDetail(job) {
  const request = job.request || {};
  const peerAsset = Boolean(job.peer_asset);
  const localAsset = Boolean(job.local_asset);
  const mediaType = jobMediaType(job);
  const audio = mediaType === "audio";
  const runningHub = request.provider === "runninghub";
  const download = el("downloadAssetDetail");
  const downloadable = job.status === "completed" && Boolean(job.result_url);
  const references = request.references || [];
  const preview = job.asset_deleted
    ? `<div class="asset-detail-placeholder">${icon("file-x-2")}<span>${t("assetDeleted")}</span></div>`
    : job.status === "completed" && job.result_url
    ? audio
      ? `<audio controls preload="metadata" src="${escapeHtml(job.result_url)}"></audio>`
      : mediaType === "image"
        ? `<img src="${escapeHtml(job.result_url)}" alt="${escapeHtml(shortTitle(job))}">`
        : mediaType === "file"
          ? `<a class="detail-download" href="${escapeHtml(job.result_url)}" download>${icon("download")}<span>${mediaDownloadLabel(mediaType)}</span></a>`
          : `<video controls playsinline preload="metadata" src="${escapeHtml(job.result_url)}"></video>`
    : `<div class="asset-detail-placeholder">${icon(job.status === "running" ? "loader-circle" : "file-x-2")}<span>${t("outputUnavailable")}</span></div>`;
  const files = references.length
    ? `<div class="asset-detail-files">${references.map((item, index) => assetDetailFile(item, index, job)).join("")}</div>`
    : `<p class="quiet">${t("noSourceFiles")}</p>`;
  const facts = (localAsset
    ? [localAssetTypeLabel(mediaType), job.owner_name ? `${t("owner")} ${job.owner_name}` : null]
    : [
      executionModeLabel(job), modelLabel(job), nodeLabel(job),
      runningHub || audio ? null : `${request.width} × ${request.height}`,
      runningHub ? null : `${request.duration}${t("seconds")}`,
      runningHub ? null : `${request.steps} ${t("steps")}`,
      runningHub ? null : `${t("seed")} ${request.seed}`,
      ...runningHubParameterFacts(request),
      `${t("overallTime")} ${formatElapsed(job.elapsed_seconds)}`,
    ]).filter(Boolean).map((value) => `<span>${escapeHtml(value)}</span>`).join("");
  el("assetDetailTitle").textContent = shortTitle(job);
  const ownerMeta = job.owner_name ? ` · ${t("owner")} ${job.owner_name}` : "";
  el("assetDetailMeta").textContent = `${statusLabel(job.status)} · ${formatTime(job.created_at, true)}${ownerMeta} · ${job.source_job_id || job.id}`;
  el("assetDetailBody").innerHTML = `<div class="asset-detail-preview">${preview}</div><div class="asset-detail-info">
    <section class="asset-detail-section"><h3>${t("prompt")}</h3><pre>${escapeHtml(request.prompt || "")}</pre></section>
    ${request.lyrics ? `<section class="asset-detail-section"><h3>${t("lyrics")}</h3><pre>${escapeHtml(request.lyrics)}</pre></section>` : ""}
    <section class="asset-detail-section"><h3>${t("sourceFiles")}</h3>${files}</section>
    <section class="asset-detail-section"><h3>${t("parameters")}</h3><div class="asset-detail-facts">${facts}</div></section>
  </div>`;
  el("deleteAssetDetail").hidden = peerAsset || localAsset;
  el("deleteAssetDetail").disabled = peerAsset || localAsset || isActive(job);
  download.hidden = !downloadable;
  download.href = downloadable ? job.result_url : "#";
  download.download = job.source_job_id || job.id;
  download.querySelector("span").textContent = mediaDownloadLabel(mediaType);
  el("regenerateAssetDetail").hidden = peerAsset || localAsset;
  el("regenerateAssetDetail").disabled = peerAsset || localAsset || isActive(job);
  el("reuseAssetDetail").hidden = peerAsset || localAsset;
  el("reuseAssetDetail").disabled = peerAsset || localAsset;
  el("reuseOutputAssetDetail").hidden = localAsset;
  el("reuseOutputAssetDetail").disabled = localAsset || !downloadable;
  refreshIcons();
}

async function openAssetDetail(jobId) {
  el("assetDetailModal").hidden = false;
  document.body.classList.add("modal-open");
  el("assetDetailError").textContent = "";
  el("downloadAssetDetail").hidden = true;
  el("downloadAssetDetail").href = "#";
  el("deleteAssetDetail").hidden = false;
  el("regenerateAssetDetail").hidden = false;
  el("reuseAssetDetail").hidden = false;
  el("reuseOutputAssetDetail").hidden = false;
  el("regenerateAssetDetail").disabled = true;
  el("reuseOutputAssetDetail").disabled = true;
  el("assetDetailBody").innerHTML = `<div class="feed-loading"><span></span><span></span><span></span></div>`;
  refreshIcons();
  try {
    const job = await fetchAssetDetail(jobId);
    state.assetDetailJob = job;
    renderAssetDetail(job);
  } catch (error) {
    state.assetDetailJob = null;
    el("assetDetailBody").innerHTML = `<p class="list-error">${escapeHtml(error.message)}</p>`;
  }
}

function closeAssetDetail() {
  el("assetDetailBody").querySelectorAll("video, audio").forEach((item) => item.pause());
  state.assetDetailJob = null;
  el("assetDetailModal").hidden = true;
  el("assetDetailError").textContent = "";
  if (el("nodeModal").hidden && el("peeringModal").hidden && el("localAssetsModal").hidden && el("localAssetPreviewModal").hidden) document.body.classList.remove("modal-open");
}

function assetFromLibrary(jobId) {
  return state.assets.find((job) => job.id === jobId) || null;
}

async function fetchAssetDetail(jobId) {
  if (state.assetDetailJob?.id === jobId) return state.assetDetailJob;
  const known = assetFromLibrary(jobId);
  const url = known?.detail_url || `/api/v1/generations/${encodeURIComponent(jobId)}`;
  return api(url);
}

async function restoredReferences(job) {
  const references = job.request?.references || [];
  const restored = [];
  try {
    for (const [index, item] of references.entries()) {
      const url = item.url || `/api/v1/generations/${encodeURIComponent(job.id)}/references/${index}`;
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) throw new Error(t("fileUnavailable"));
      const blob = await response.blob();
      const fallbackTypes = { image: "image/png", video: "video/mp4", audio: "audio/mpeg" };
      const file = new File([blob], item.name || `${item.type}-${index + 1}`, { type: blob.type || fallbackTypes[item.type] || "application/octet-stream" });
      restored.push({ file, kind: item.type, field_key: item.field_key || "", name: file.name, size: file.size, url: URL.createObjectURL(file) });
    }
    return restored;
  } catch (error) {
    restored.forEach((item) => URL.revokeObjectURL(item.url));
    throw error;
  }
}

async function useGeneratedOutputAsInput(jobId) {
  const detailOpen = !el("assetDetailModal").hidden;
  const target = detailOpen ? el("assetDetailError") : el("formError");
  const job = await fetchAssetDetail(jobId);
  if (job.status !== "completed" || !job.result_url) {
    throw new Error(t("outputUnavailable"));
  }
  target.textContent = t("fillLoading");
  const response = await fetch(job.result_url, { cache: "no-store" });
  if (!response.ok) throw new Error(t("outputUnavailable"));
  const blob = await response.blob();
  const mediaType = jobMediaType(job);
  const extension = { audio: "flac", video: "mp4", image: "png", file: "bin" }[mediaType] || "bin";
  const basename = String(job.title || job.id).replace(/[^\w\u4e00-\u9fff.-]+/g, "_").slice(0, 64) || job.id;
  const file = new File([blob], `${basename}.${extension}`, {
    type: blob.type || ({ audio: "audio/flac", video: "video/mp4", image: "image/png" }[mediaType] || "application/octet-stream"),
  });
  if (!addFiles([file])) {
    throw new Error(el("formError").textContent || t("outputUnavailable"));
  }
  updateModelUi();
  target.textContent = "";
  if (detailOpen) closeAssetDetail();
}

function composerNodeForJob(job) {
  const requestedNode = job.request?.comfy_node || "auto";
  if (requestedNode !== "auto" && Array.from(el("comfyNode").options).some((option) => option.value === requestedNode && !option.disabled)) {
    return requestedNode;
  }
  if (job.request?.provider === "runninghub") {
    const replacement = state.nodes.find((node) => (
      node.healthy && node.provider === "runninghub" && node.workflow_id === job.request.runninghub_resource_id
    ));
    if (replacement) return replacement.id;
  }
  if (requestedNode === "auto") return "auto";
  return "auto";
}

async function backfillJob(jobId) {
  const detailOpen = !el("assetDetailModal").hidden;
  const reuseButton = el("reuseAssetDetail");
  if (detailOpen) el("assetDetailError").textContent = t("fillLoading");
  reuseButton.disabled = true;
  try {
    const job = await fetchAssetDetail(jobId);
    if (job.peer_asset) throw new Error(localized("远端素材仅支持下载或作为输入", "Remote assets support download or use as input"));
    const references = await restoredReferences(job);
    resetComposer();
    promptInput.value = job.request?.prompt || "";
    el("lyrics").value = job.request?.lyrics || "";
    el("modelVariant").value = job.request?.model_variant || "fl2va-fp8";
    el("executionMode").value = job.request?.execution_mode || "native";
    setSaParameters(job.request || {});
    el("comfyNode").value = composerNodeForJob(job);
    updateModelUi();
    if (job.request?.provider === "runninghub") {
      state.runningHubParameters = { ...runningHubDefaultParameters(selectedRunningHubSchema()), ...(job.request.runninghub_parameters || {}) };
      renderRunningHubParameters();
    }
    if (job.request?.width && job.request?.height) setDimensions(job.request.width, job.request.height);
    el("duration").value = String(job.request?.duration ?? el("duration").value);
    el("steps").value = String(job.request?.steps ?? el("steps").value);
    el("seed").value = job.request?.seed == null ? "" : String(job.request.seed);
    state.references = references;
    renderReferences();
    closeAssetDetail();
    closeAssetDrawer();
    el("conversationFeed").scrollTop = el("conversationFeed").scrollHeight;
    promptInput.focus();
    showError("");
  } catch (error) {
    if (detailOpen) el("assetDetailError").textContent = error.message;
    else showError(error.message);
  } finally {
    reuseButton.disabled = false;
  }
}

function resetComposer() {
  state.references.forEach((item) => { if (item.file && item.url) URL.revokeObjectURL(item.url); });
  state.references = [];
  state.editingJobId = null;
  promptInput.value = "";
  el("lyrics").value = "";
  el("seed").value = "";
  setSaParameters();
  state.runningHubParameters = runningHubDefaultParameters(selectedRunningHubSchema());
  state.pendingRunningHubMediaField = "";
  el("editBanner").hidden = true;
  el("addReference").disabled = false;
  el("generateButton").classList.remove("editing");
  renderReferences();
  showError("");
}

function newTask() {
  resetComposer();
  closeAssetDrawer();
  el("conversationFeed").scrollTo({ top: el("conversationFeed").scrollHeight, behavior: "smooth" });
  promptInput.focus();
}

async function startEdit(jobId) {
  try {
    const job = await api(`/api/v1/generations/${jobId}`);
    if (job.status !== "queued") throw new Error(localized("只有排队中的任务可以修改", "Only queued tasks can be edited"));
    resetComposer();
    state.editingJobId = job.id;
    promptInput.value = job.request.prompt;
    el("lyrics").value = job.request.lyrics || "";
    el("modelVariant").value = job.request.model_variant || "fl2va-fp8";
    el("executionMode").value = job.request.execution_mode || "native";
    setSaParameters(job.request || {});
    el("comfyNode").value = composerNodeForJob(job);
    el("seed").value = String(job.request.seed);
    setDimensions(job.request.width, job.request.height);
    state.references = (job.request.references || []).map((item) => ({ ...item, kind: item.type, remote: true }));
    updateModelUi();
    if (job.request?.provider === "runninghub") {
      state.runningHubParameters = { ...runningHubDefaultParameters(selectedRunningHubSchema()), ...(job.request.runninghub_parameters || {}) };
      renderRunningHubParameters();
    }
    el("duration").value = String(job.request.duration);
    el("steps").value = String(job.request.steps);
    el("editBanner").hidden = false;
    el("addReference").disabled = true;
    el("generateButton").classList.add("editing");
    renderReferences();
    closeAssetDrawer();
    promptInput.focus();
  } catch (error) {
    showError(error.message);
  }
}

async function cancelJob(jobId) {
  try {
    const job = await api(`/api/v1/generations/${jobId}/cancel`, { method: "POST" });
    applyJobUpsert(job);
  } catch (error) {
    showError(error.message);
  }
}

async function deleteJob(jobId) {
  if (!window.confirm(t("deleteConfirm"))) return false;
  try {
    await api(`/api/v1/generations/${jobId}`, { method: "DELETE" });
    if (state.editingJobId === jobId) resetComposer();
    applyJobDelete(jobId);
    return true;
  } catch (error) {
    showError(error.message);
    return false;
  }
}

async function regenerateJob(jobId) {
  if (!window.confirm(t("regenerateConfirm"))) return false;
  const detailOpen = !el("assetDetailModal").hidden && state.assetDetailJob?.id === jobId;
  const actionButtons = Array.from(document.querySelectorAll('[data-job-action="regenerate"]'))
    .filter((button) => button.dataset.jobId === jobId);
  if (detailOpen) {
    actionButtons.push(el("regenerateAssetDetail"));
    el("assetDetailError").textContent = localized("正在创建新的生成任务", "Creating a new generation");
  }
  actionButtons.forEach((button) => { button.disabled = true; });
  try {
    const headers = state.incognito ? { "X-H3-Incognito-Code": state.incognitoCode } : {};
    const job = await api(`/api/v1/generations/${encodeURIComponent(jobId)}/regenerate`, { method: "POST", headers });
    applyJobUpsert(job);
    if (detailOpen) closeAssetDetail();
    showError("");
    return true;
  } catch (error) {
    if (detailOpen) el("assetDetailError").textContent = error.message;
    else showError(error.message);
    return false;
  } finally {
    actionButtons.forEach((button) => { button.disabled = false; });
  }
}

async function handleJobAction(action, jobId) {
  if (action === "reuse") return backfillJob(jobId);
  if (action === "input") return useGeneratedOutputAsInput(jobId).catch((error) => showError(error.message));
  if (action === "regenerate") return regenerateJob(jobId);
  if (action === "edit") return startEdit(jobId);
  if (action === "cancel") return cancelJob(jobId);
  if (action === "delete") return deleteJob(jobId);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  const prompt = promptInput.value.trim();
  const runningHubNode = selectedRunningHubNode();
  const runningHub = Boolean(runningHubNode?.runninghub_schema);
  const minimumPromptLength = isMusic3() ? 2 : 8;
  if (!runningHub && prompt.length < minimumPromptLength) return showError(localized(`请填写至少 ${minimumPromptLength} 个字符的提示词`, `Enter a prompt with at least ${minimumPromptLength} characters`));
  const steps = isMusic3() ? 30 : selectedExecutionMode() === "turbo-lora" || isH3SA() ? 8 : isVDNH3() ? Number(el("steps").value) : isDigitalHuman() ? 20 : Number(el("steps").value);
  if (!runningHub && (!Number.isInteger(steps) || steps < 4 || steps > 50)) return showError(localized("采样步数请输入 4–50 的整数", "Sampling steps must be an integer from 4 to 50"));
  const [width, height] = isTTS() ? [32, 32] : getDimensions();
  const button = el("generateButton");
  button.disabled = true;
  try {
    let payload;
    if (state.editingJobId) {
      const requestBody = {
        prompt,
        comfy_node: el("comfyNode").value,
      };
      if (runningHub) {
        requestBody.runninghub_parameters = collectRunningHubParameters();
      } else {
        requestBody.lyrics = isMusic3() ? el("lyrics").value.trim() : "";
        requestBody.width = width;
        requestBody.height = height;
        requestBody.duration = Number(el("duration").value);
        requestBody.steps = steps;
        requestBody.seed = el("seed").value === "" ? undefined : Number(el("seed").value);
        requestBody.model_variant = selectedVariant();
        requestBody.execution_mode = selectedExecutionMode();
      }
      payload = await api(`/api/v1/generations/${state.editingJobId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(state.incognito ? { "X-H3-Incognito-Code": state.incognitoCode } : {}),
        },
        body: JSON.stringify(requestBody),
      });
    } else {
      const referenceError = validateReferenceSet();
      if (referenceError) throw new Error(referenceError);
      const data = new FormData();
      data.append("prompt", prompt);
      data.append("lyrics", isMusic3() ? el("lyrics").value.trim() : "");
      data.append("width", String(width));
      data.append("height", String(height));
      data.append("duration", el("duration").value);
      data.append("steps", String(steps));
      data.append("seed", el("seed").value);
      if (runningHub) {
        data.append("runninghub_parameters", JSON.stringify(collectRunningHubParameters()));
      } else {
        data.append("model_variant", selectedVariant());
        data.append("execution_mode", selectedExecutionMode());
      }
      data.append("comfy_node", el("comfyNode").value);
      data.append("incognito", state.incognito ? "true" : "false");
      data.append("reference_manifest", JSON.stringify(state.references.map((item) => ({ type: item.kind, ...(item.field_key ? { field_key: item.field_key } : {}) }))));
      state.references.forEach((item) => data.append("references", item.file, item.file.name));
      const headers = state.incognito ? { "X-H3-Incognito-Code": state.incognitoCode } : {};
      payload = await api("/api/v1/generations", { method: "POST", headers, body: data });
    }
    if (state.editingJobId) resetComposer();
    applyJobUpsert(payload);
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
});

function renderQueue(queue) {
  state.queue = queue;
  const runningJobs = queue.filter((job) => job.status === "running");
  const running = runningJobs[0];
  const anonymousRunning = running && isAnonymousQueueJob(running);
  const queuedCount = queue.filter((job) => job.status === "queued").length;
  el("queueCount").textContent = queue.length;
  el("launcherQueueCount").textContent = queuedCount;
  el("launcherQueueCount").hidden = queuedCount === 0;
  el("launcherTitle").textContent = running
    ? state.locale === "en" ? `Generating ${runningJobs.length}` : `正在生成 ${runningJobs.length}`
    : state.locale === "en" ? "Activity" : "运行日志";
  el("launcherMeta").textContent = running
    ? anonymousRunning
      ? state.locale === "en" ? "A task is running" : "有任务正在运行中"
      : `${nodeLabel(running)} · ${executionModeLabel(running)} · ${running.progress || 0}% · ${formatElapsed(running.elapsed_seconds)}`
    : queuedCount ? state.locale === "en" ? `${queuedCount} queued` : `排队 ${queuedCount}` : state.locale === "en" ? "Queue empty" : "队列为空";
  el("activeTaskSummary").textContent = running
    ? anonymousRunning
      ? state.locale === "en" ? "A task is running" : "有任务正在运行中"
      : state.locale === "en" ? `${runningJobs.length} tasks running · ${runningJobs.map((job) => nodeLabel(job)).join(", ")}` : `${runningJobs.length} 个任务执行中 · ${runningJobs.map((job) => nodeLabel(job)).join("、")}`
    : state.locale === "en" ? `No active tasks · ${queuedCount} queued` : `当前没有执行任务 · 排队 ${queuedCount}`;
  el("queueList").innerHTML = queue.length ? queue.map((job) => {
    if (isAnonymousQueueJob(job)) {
      return `<div class="queue-row">
        <span class="queue-position">${job.status === "running" ? icon("loader-circle") : job.queue_position}</span>
        <span><strong>${escapeHtml(job.stage || "有任务正在运行中")}</strong></span>
      </div>`;
    }
    return `<div class="queue-row" data-scroll-job="${job.id}">
      <span class="queue-position">${job.status === "running" ? icon("loader-circle") : job.queue_position}</span>
      <span><strong>${escapeHtml(shortTitle(job))}</strong><small>${escapeHtml(nodeLabel(job))} · ${escapeHtml(executionModeLabel(job))} · ${escapeHtml(job.stage || statusLabel(job.status))} · ${job.progress || 0}% · ${formatElapsed(job.elapsed_seconds)}</small></span>
      <button type="button" data-job-action="cancel" data-job-id="${job.id}" title="取消任务" aria-label="取消任务">${icon("square")}</button>
    </div>`;
  }).join("") : `<p class="quiet">${state.locale === "en" ? "Queue empty" : "队列为空"}</p>`;
  refreshIcons();
}

function renderLogs(logs) {
  state.logs = logs;
  const visible = logs.filter((item) => new Date(item.timestamp).getTime() >= state.logFloor);
  const container = el("logList");
  container.innerHTML = visible.length ? visible.map((item) => {
    const jobLink = item.job_id
      ? `<button type="button" data-scroll-job="${item.job_id}">${item.job_id.slice(0, 6)}</button>`
      : "<span></span>";
    const progress = item.progress == null ? "" : ` <b>${item.progress}%</b>`;
    const source = item.owner_name ? `<span class="log-source">${escapeHtml(item.owner_name)}</span>` : "";
    const node = item.node_name ? `<span class="log-node">${escapeHtml(item.node_name)}</span>` : "";
    return `<div class="log-row ${item.level === "error" ? "error" : ""}">
      <time>${formatTime(item.timestamp)}</time>
      ${jobLink}
      <p>${source}${node}${escapeHtml(item.message)}${progress}</p>
    </div>`;
  }).join("") : `<p class="quiet">${state.locale === "en" ? "Waiting for events" : "等待事件"}</p>`;
  container.scrollTop = container.scrollHeight;
}

function renderCombinedRuntime() {
  const remote = Object.values(state.peerRuntime);
  const nodes = [
    ...(state.localRuntime.nodes || []),
    ...remote.flatMap((payload) => payload.nodes || []),
  ];
  const queue = [
    ...(state.localRuntime.queue || []),
    ...remote.flatMap((payload) => payload.queue || []),
  ];
  const logs = [
    ...(state.localRuntime.logs || []),
    ...remote.flatMap((payload) => payload.logs || []),
  ].sort((left, right) => String(left.timestamp || "").localeCompare(String(right.timestamp || "")));
  renderHealthState(nodes, queue.filter((job) => job.status === "queued").length);
  syncManagedNodeStatuses(nodes);
  renderQueue(queue);
  renderLogs(logs.slice(-100));
}

function connectEventStream() {
  state.stream?.close();
  const initialRevisions = [state.assetRevision, state.conversationRevision].filter((revision) => revision > 0);
  const since = initialRevisions.length ? Math.min(...initialRevisions) : 0;
  state.stream = new EventSource(`/api/v1/events?since=${encodeURIComponent(since)}`);
  state.stream.addEventListener("snapshot", async (event) => {
    const payload = JSON.parse(event.data);
    state.localRuntime = {
      nodes: payload.nodes || [],
      queue: payload.queue || [],
      logs: payload.logs || [],
    };
    renderCombinedRuntime();
    if (payload.peering_status) applyPeeringStatus(payload.peering_status, Boolean(state.peering));
    if (payload.reset_required) {
      await Promise.all([loadAssets({ reset: true }), refreshConversation()]);
    } else if (!state.incognito) {
      (payload.jobs || []).forEach(applyJobUpsert);
      (payload.deleted_job_ids || []).forEach(applyJobDelete);
    } else if ((payload.store_revision || 0) > state.storeRevision) {
      await refreshActiveIncognitoJobs();
    }
    state.storeRevision = Math.max(state.storeRevision, payload.store_revision || 0);
    state.lastRevision = payload.revision;
  });
  state.stream.addEventListener("peer_snapshot", async (event) => {
    const payload = JSON.parse(event.data);
    if (!payload.peer_device_id) return;
    state.peerRuntime[payload.peer_device_id] = {
      nodes: payload.nodes || [],
      queue: payload.queue || [],
      logs: payload.logs || [],
    };
    renderCombinedRuntime();
    if (payload.reset_required) {
      await refreshConversation();
      return;
    }
    (payload.jobs || []).forEach(applyJobUpsert);
    (payload.deleted_job_ids || []).forEach(applyJobDelete);
  });
  state.stream.addEventListener("peer_removed", (event) => {
    const payload = JSON.parse(event.data);
    if (!payload.peer_device_id) return;
    delete state.peerRuntime[payload.peer_device_id];
    renderCombinedRuntime();
  });
  state.stream.onopen = () => {
    const snapshot = el("healthText").dataset.snapshot;
    if (snapshot) el("healthText").textContent = snapshot;
  };
  state.stream.onerror = () => {
    el("healthDot").className = "status-dot reconnecting";
    el("healthText").textContent = state.locale === "en" ? "Live connection lost, reconnecting" : "实时连接已断开，正在重连";
  };
}

async function refreshActiveIncognitoJobs() {
  const activeIds = state.conversations.filter(isActive).map((job) => job.id);
  const results = await Promise.allSettled(activeIds.map((jobId) => api(`/api/v1/generations/${jobId}`)));
  results.forEach((result) => {
    if (result.status === "fulfilled") applyJobUpsert(result.value);
  });
}

function renderAiConfig(config) {
  state.aiConfig = config;
  el("aiEnabled").checked = Boolean(config.enabled);
  el("aiBaseUrl").value = config.base_url || "";
  el("aiModel").value = config.model || "";
  el("aiApiKey").value = "";
  el("aiApiKey").placeholder = config.has_api_key ? t("aiKeyReplace") : "sk-…";
  el("aiApiKeyStatus").textContent = config.has_api_key ? t("aiKeySaved") : t("aiKeyEmpty");
}

async function loadAiConfig() {
  renderAiConfig(await api("/api/v1/settings/ai"));
}

async function saveAiConfig() {
  clearTimeout(state.aiSaveTimer);
  const apiKey = el("aiApiKey").value.trim();
  const payload = {
    enabled: el("aiEnabled").checked,
    base_url: el("aiBaseUrl").value.trim(),
    model: el("aiModel").value.trim(),
  };
  if (apiKey) payload.api_key = apiKey;
  const config = await api("/api/v1/settings/ai", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  renderAiConfig(config);
  return config;
}

async function loadGeneralSettings() {
  const payload = await api("/api/v1/settings/general");
  state.generalSettings = payload;
  el("globalHealthInterval").value = String(payload.health_interval_seconds || 60);
  el("showRuntimeLogs").checked = payload.show_runtime_logs !== false;
  el("showPeering").checked = payload.show_peering !== false;
  el("backupOutputs").checked = Boolean(payload.backup_outputs);
  el("remoteDisconnectPolicy").value = payload.remote_disconnect_policy || "encrypt";
  el("remoteRecordsKey").value = payload.remote_records_key || "";
  el("opsLauncher").hidden = payload.show_runtime_logs === false;
  el("openPeering").hidden = payload.show_peering === false;
  if (payload.show_runtime_logs === false) closeOpsWindow();
}

async function saveGeneralSettings(event) {
  event.preventDefault();
  const errorBox = el("globalSettingsError");
  errorBox.textContent = "";
  const seconds = Number(el("globalHealthInterval").value);
  const key = el("remoteRecordsKey").value;
  if (!Number.isInteger(seconds) || seconds < 5 || seconds > 3600) {
    errorBox.textContent = "节点状态查询周期必须为 5 至 3600 秒";
    return;
  }
  const keyLength = Array.from(key).length;
  if (keyLength < 8 || keyLength > 256) {
    errorBox.textContent = "远程记录密钥长度必须为 8 至 256 个字符";
    return;
  }
  try {
    const payload = await api("/api/v1/settings/general", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        show_runtime_logs: el("showRuntimeLogs").checked,
        show_peering: el("showPeering").checked,
        backup_outputs: el("backupOutputs").checked,
        remote_disconnect_policy: el("remoteDisconnectPolicy").value,
        remote_records_key: key,
      }),
    });
    await api("/api/v1/comfy/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ health_interval_seconds: seconds }),
    });
    state.generalSettings = payload;
    el("opsLauncher").hidden = !el("showRuntimeLogs").checked;
    el("openPeering").hidden = !el("showPeering").checked;
    if (!el("showRuntimeLogs").checked) closeOpsWindow();
    el("globalSettingsModal").hidden = true;
    document.body.classList.remove("modal-open");
    showToast("设置已保存");
  } catch (error) {
    errorBox.textContent = error.message;
  }
}

function openGlobalSettings() {
  el("globalSettingsModal").hidden = false;
  document.body.classList.add("modal-open");
  loadGeneralSettings().catch((error) => { el("globalSettingsError").textContent = error.message; });
  refreshIcons();
}

function closeGlobalSettings() {
  el("globalSettingsModal").hidden = true;
  if (el("peeringModal").hidden && el("nodeModal").hidden && el("assetDetailModal").hidden && el("localAssetsModal").hidden) document.body.classList.remove("modal-open");
}

function localAssetTypeLabel(mediaType) {
  return { video: "视频", audio: "音频", image: "图片", file: "文件" }[mediaType] || "文件";
}

function localAssetPreviewMarkup(asset) {
  if (asset.locked) {
    return `<button class="local-asset-locked" type="button" data-unlock-owner="${escapeHtml(asset.owner_device_id)}" data-unlock-name="${escapeHtml(asset.owner_name)}" title="输入所属设备密钥">${icon("lock-keyhole")}<b>文件被加密</b></button>`;
  }
  if (asset.asset_deleted) {
    return `<span class="asset-placeholder deleted">${icon("file-x-2")}<b>${t("assetDeleted")}</b></span>`;
  }
  if (asset.preview_url && asset.media_type === "image") {
    return `<img src="${escapeHtml(asset.preview_url)}" alt="${escapeHtml(asset.name)}" loading="lazy">`;
  }
  if (asset.preview_url && asset.media_type === "video") {
    return `<video src="${escapeHtml(asset.preview_url)}" muted playsinline preload="metadata" aria-label="${escapeHtml(asset.name)}"></video><span class="asset-play">${icon("play")}</span>`;
  }
  if (asset.media_type === "audio") {
    return `<span class="asset-audio-icon" aria-hidden="true">${icon("audio-lines")}</span>`;
  }
  return `<span class="asset-audio-icon" aria-hidden="true">${icon("file")}</span>`;
}

function openLocalAssetPreview(asset) {
  if (!asset.preview_url || asset.asset_deleted || asset.locked) return;
  const url = escapeHtml(asset.preview_url);
  const name = escapeHtml(asset.name || asset.file_name || "本地素材");
  const mediaType = asset.media_type || "file";
  const preview = mediaType === "image"
    ? `<img src="${url}" alt="${name}">`
    : mediaType === "video"
      ? `<video src="${url}" controls playsinline autoplay preload="metadata" aria-label="${name}"></video>`
      : mediaType === "audio"
        ? `<audio src="${url}" controls autoplay preload="metadata" aria-label="${name}"></audio>`
        : `<div class="local-asset-preview-unsupported">${icon("file")}<span>该文件无法直接预览</span></div>`;
  el("localAssetPreviewBody").innerHTML = preview;
  el("localAssetPreviewModal").hidden = false;
  document.body.classList.add("modal-open");
  refreshIcons();
}

function closeLocalAssetPreview() {
  const body = el("localAssetPreviewBody");
  body.querySelectorAll("video, audio").forEach((media) => {
    media.pause();
    media.removeAttribute("src");
    media.load();
  });
  body.innerHTML = "";
  el("localAssetPreviewModal").hidden = true;
  if (el("localAssetsModal").hidden && el("globalSettingsModal").hidden && el("peeringModal").hidden && el("nodeModal").hidden && el("assetDetailModal").hidden && el("unlockAssetsModal").hidden) document.body.classList.remove("modal-open");
}

function syncLocalAssetSelectAll() {
  const selectable = state.localAssets.filter((asset) => !asset.asset_deleted);
  const selectedCount = selectable.filter((asset) => state.localAssetSelected.has(asset.id)).length;
  el("localAssetsSelectAll").checked = selectable.length > 0 && selectedCount === selectable.length;
  el("localAssetsSelectAll").indeterminate = selectedCount > 0 && selectedCount < selectable.length;
}

function renderLocalAssetManager() {
  const list = el("localAssetsList");
  const cards = state.localAssets.map((asset) => {
    const encryptedMessage = asset.locked
      ? `文件被加密，所属设备：${asset.owner_name}`
      : asset.asset_deleted
        ? t("assetDeleted")
        : asset.file_name || formatTime(asset.created_at, true);
    const mediaType = asset.media_type || "file";
    const audioOrFile = mediaType === "audio" || mediaType === "file";
    return `<article class="asset-card local-asset-card" data-local-asset-id="${escapeHtml(asset.id)}" tabindex="0" aria-label="${escapeHtml(asset.name)}">
      <div class="asset-preview${audioOrFile ? " music" : ""}">
        <label class="local-asset-select" data-local-asset-select>
          <input type="checkbox" value="${escapeHtml(asset.id)}" aria-label="选择 ${escapeHtml(asset.name)}" ${state.localAssetSelected.has(asset.id) ? "checked" : ""} ${asset.asset_deleted ? "disabled" : ""}>
        </label>
        ${localAssetPreviewMarkup(asset)}
      </div>
      <div class="asset-meta"><span class="task-status completed"></span><strong title="${escapeHtml(asset.name)}">${escapeHtml(asset.name)}</strong><small class="asset-plan">${escapeHtml(localAssetTypeLabel(mediaType))}</small><span class="asset-owner" title="来源：${escapeHtml(asset.owner_name)}">${icon("tag")}<span>${escapeHtml(asset.owner_name)}</span></span><time title="${escapeHtml(encryptedMessage)}">${escapeHtml(encryptedMessage)}</time></div>
    </article>`;
  }).join("");
  const loading = state.localAssetLoading
    ? `<p class="local-assets-loading">${t("loading")}</p>`
    : state.localAssetPage >= state.localAssetPages && state.localAssets.length
      ? `<p class="local-assets-loading">${t("allLoaded")}</p>`
      : "";
  list.innerHTML = (cards || state.localAssetLoading) ? `${cards}${loading}` : `<p class="quiet">${t("noAssets")}</p>`;
  el("localAssetsCount").textContent = `${state.localAssetTotal} 项`;
  syncLocalAssetSelectAll();
  refreshIcons();
}

async function loadLocalAssets({ reset = false } = {}) {
  if (state.localAssetLoading) return;
  if (!reset && state.localAssetPage >= state.localAssetPages) return;
  if (reset) {
    state.localAssets = [];
    state.localAssetPage = 0;
    state.localAssetPages = 1;
    state.localAssetTotal = 0;
    state.localAssetSelected.clear();
  }
  state.localAssetLoading = true;
  renderLocalAssetManager();
  try {
    const page = state.localAssetPage + 1;
    const payload = await api(`/api/v1/assets/local?page=${page}&page_size=24`);
    state.localAssets.push(...(payload.data || []));
    state.localAssetPage = Number(payload.page || page);
    state.localAssetPages = Number(payload.pages || 1);
    state.localAssetTotal = Number(payload.total || state.localAssets.length);
    el("localAssetsError").textContent = "";
  } catch (error) {
    el("localAssetsError").textContent = error.message;
  } finally {
    state.localAssetLoading = false;
    renderLocalAssetManager();
  }
}

async function openLocalAssets() {
  el("localAssetsModal").hidden = false;
  el("localAssetsError").textContent = "";
  document.body.classList.add("modal-open");
  await loadLocalAssets({ reset: true });
}

function closeLocalAssets() {
  el("localAssetsModal").hidden = true;
  if (el("globalSettingsModal").hidden && el("peeringModal").hidden && el("nodeModal").hidden && el("assetDetailModal").hidden && el("unlockAssetsModal").hidden) document.body.classList.remove("modal-open");
}

async function deleteLocalArtifacts() {
  const ids = Array.from(state.localAssetSelected);
  if (!ids.length) return;
  if (!window.confirm(`确认删除选中的 ${ids.length} 项本地产物？任务与工作流记录会保留。`)) return;
  try {
    const result = await api("/api/v1/assets/local/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ asset_ids: ids }) });
    state.localAssetChanged = Boolean(result.deleted?.length);
    state.localAssetSelected.clear();
    await loadLocalAssets({ reset: true });
    if (state.localAssetChanged) await refreshSharedData();
    if (result.rejected?.length) el("localAssetsError").textContent = `${result.rejected.length} 项未能删除`;
  } catch (error) {
    el("localAssetsError").textContent = error.message;
  }
}

function openUnlockAssets(ownerDeviceId, ownerName) {
  state.unlockOwnerDeviceId = ownerDeviceId;
  el("unlockAssetsOwner").textContent = `所属设备：${ownerName || ownerDeviceId}`;
  el("unlockAssetsKey").value = "";
  el("unlockAssetsKey").type = "password";
  el("unlockAssetsError").textContent = "";
  el("unlockAssetsModal").hidden = false;
  document.body.classList.add("modal-open");
  refreshIcons();
  el("unlockAssetsKey").focus();
}

function closeUnlockAssets() {
  el("unlockAssetsModal").hidden = true;
  state.unlockOwnerDeviceId = "";
  if (el("localAssetsModal").hidden && el("globalSettingsModal").hidden && el("peeringModal").hidden && el("nodeModal").hidden && el("assetDetailModal").hidden) document.body.classList.remove("modal-open");
}

async function unlockLocalAssets(event) {
  event.preventDefault();
  const recordsKey = el("unlockAssetsKey").value;
  const keyLength = Array.from(recordsKey).length;
  if (keyLength < 8 || keyLength > 256) {
    el("unlockAssetsError").textContent = "密钥长度必须为 8 至 256 个字符";
    return;
  }
  try {
    await api("/api/v1/assets/local/unlock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ owner_device_id: state.unlockOwnerDeviceId, records_key: recordsKey }),
    });
    closeUnlockAssets();
    await loadLocalAssets({ reset: true });
    showToast("该设备的本地加密素材已解锁");
  } catch (error) {
    el("unlockAssetsError").textContent = error.message;
  }
}

async function parseSseResponse(response, onEvent) {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `请求失败 (${response.status})`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    blocks.forEach((block) => {
      let type = "message";
      let data = "{}";
      block.split("\n").forEach((line) => {
        if (line.startsWith("event:")) type = line.slice(6).trim();
        if (line.startsWith("data:")) data = line.slice(5).trim();
      });
      try { onEvent(type, JSON.parse(data)); } catch { /* ignore malformed upstream chunks */ }
    });
  }
}

async function assistMusic(task) {
  showError("");
  try {
    await saveAiConfig();
  } catch (error) {
    return showError(error.message);
  }
  const source = promptInput.value.trim();
  if (source.length < 2) return showError("请先输入歌曲主题、曲风或创作要求");
  if (!el("aiEnabled").checked) {
    el("advancedSettings").open = true;
    return showError("请在更多设置中启用 AI 提示词优化");
  }
  const baseUrl = el("aiBaseUrl").value.trim();
  const model = el("aiModel").value.trim();
  if (!baseUrl || !model) {
    el("advancedSettings").open = true;
    return showError("请填写 OpenAI Base URL 和模型名称");
  }
  const button = task === "lyrics" ? el("writeLyrics") : el("optimizePrompt");
  let output = "";
  button.disabled = true;
  let streamError = "";
  try {
    const response = await fetch("/api/v1/music/assist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task,
        prompt: source,
        lyrics: el("lyrics").value.trim(),
        duration: Number(el("duration").value),
        base_url: baseUrl,
        model,
      }),
    });
    await parseSseResponse(response, (type, data) => {
      if (type === "delta") output += data.text || "";
      if (type === "error") streamError = data.message || "AI 音乐辅助失败";
    });
    if (streamError) throw new Error(streamError);
    if (!output.trim()) throw new Error("AI 服务没有返回可用内容");
    if (task === "lyrics") el("lyrics").value = output.trim();
    else promptInput.value = output.trim();
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
}

async function optimizePrompt() {
  if (isMusic3()) return assistMusic("arrangement");
  showError("");
  try {
    await saveAiConfig();
  } catch (error) {
    return showError(error.message);
  }
  const source = promptInput.value.trim();
  if (source.length < 2) return showError("请先输入需要优化的自然语言描述");
  if (!el("aiEnabled").checked) {
    el("advancedSettings").open = true;
    return showError("请在更多设置中启用 AI 提示词优化");
  }
  const baseUrl = el("aiBaseUrl").value.trim();
  const model = el("aiModel").value.trim();
  if (!baseUrl || !model) {
    el("advancedSettings").open = true;
    return showError("请填写 OpenAI Base URL 和模型名称");
  }

  const button = el("optimizePrompt");
  let optimizedOutput = "";
  button.disabled = true;
  let streamError = "";
  try {
    const response = await fetch("/api/v1/prompts/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: source,
        base_url: baseUrl,
        model,
        duration: Number(el("duration").value),
        model_variant: selectedVariant(),
        execution_mode: isTTS() ? "tts" : isH3SA() ? "h3-sa" : isVDNH3() ? "vdn-h3" : "native",
        references: state.references.map((ref) => ({ type: ref.kind || ref.type, name: ref.name || ref.file?.name || "reference" })),
      }),
    });
    await parseSseResponse(response, (type, data) => {
      if (type === "delta") {
        optimizedOutput += data.text || "";
      } else if (type === "error") {
        streamError = data.message || "优化失败";
      }
    });
    if (streamError) throw new Error(streamError);
    if (!optimizedOutput.trim()) throw new Error("AI 服务没有返回可用内容");
    promptInput.value = optimizedOutput.trim();
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
}

function updateIncognitoUi() {
  const nsfwOption = el("nsfwExecutionOption");
  nsfwOption.hidden = !state.incognito;
  nsfwOption.disabled = !state.incognito;
  if (!state.incognito && selectedExecutionMode() === "h3-nsfw") {
    el("executionMode").value = "native";
  }
  el("incognitoStatus").hidden = !state.incognito;
  document.body.classList.toggle("incognito-active", state.incognito);
  updateModelUi();
  refreshIcons();
}

async function reloadModeData() {
  state.assets = [];
  state.assetPage = 0;
  state.assetPages = 1;
  state.assetHasMore = true;
  state.conversations = [];
  state.conversationPage = 1;
  state.conversationPages = 1;
  state.conversationReady = false;
  state.conversationScrollTop = 0;
  renderAssets(0);
  renderConversationFeed("bottom");
  await Promise.all([loadAssets({ reset: true }), refreshConversation(true)]);
}

async function requestIncognitoMode() {
  el("secretCode").value = "";
  el("secretError").textContent = "";
  el("secretOverlay").hidden = false;
  el("secretCode").focus();
  refreshIcons();
}

function closeSecretDialog() {
  el("secretOverlay").hidden = true;
  el("secretCode").value = "";
  el("secretError").textContent = "";
}

async function authorizeIncognitoMode(event) {
  event.preventDefault();
  const code = el("secretCode").value;
  try {
    await api("/api/v1/incognito/authorize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    state.incognito = true;
    state.incognitoCode = code;
    closeSecretDialog();
    updateIncognitoUi();
    await reloadModeData();
  } catch (error) {
    state.incognito = false;
    state.incognitoCode = "";
    updateIncognitoUi();
    el("secretError").textContent = error.message;
  }
}

function resetOpsPosition() {
  const windowNode = el("opsWindow");
  const rect = windowNode.getBoundingClientRect();
  state.opsPosition.x = 16;
  state.opsPosition.y = Math.max(24, Math.round(window.innerHeight * 0.08));
  applyOpsPosition();
}

function applyOpsPosition() {
  const windowNode = el("opsWindow");
  const rect = windowNode.getBoundingClientRect();
  const maxX = Math.max(8, window.innerWidth - rect.width - 8);
  const maxY = Math.max(8, window.innerHeight - rect.height - 8);
  state.opsPosition.x = Math.min(maxX, Math.max(8, state.opsPosition.x));
  state.opsPosition.y = Math.min(maxY, Math.max(8, state.opsPosition.y));
  windowNode.style.transform = `translate3d(${state.opsPosition.x}px, ${state.opsPosition.y}px, 0)`;
}

function openOpsWindow() {
  el("opsWindow").hidden = false;
  if (!state.opsPositionInitialized) {
    resetOpsPosition();
    state.opsPositionInitialized = true;
  } else {
    applyOpsPosition();
  }
  refreshIcons();
}

function closeOpsWindow() {
  el("opsWindow").hidden = true;
}

function openAssetDrawer() {
  el("assetSidebar").classList.add("mobile-open");
  el("mobileScrim").hidden = false;
}

function closeAssetDrawer() {
  el("assetSidebar").classList.remove("mobile-open");
  el("mobileScrim").hidden = true;
}

function showToast(message, type = "") {
  if (!message) return;
  const toast = document.createElement("div");
  toast.className = `toast${type ? ` ${type}` : ""}`;
  toast.textContent = message;
  el("toastRegion").append(toast);
  setTimeout(() => toast.remove(), 4500);
}

function peeringExpiresIn() {
  if (!state.peering) return 30;
  const elapsed = Math.floor((Date.now() - state.peering.received_at) / 1000);
  return Math.max(0, Number(state.peering.pairing_expires_in || 30) - elapsed);
}

function renderPeerList(peers) {
  el("peerList").innerHTML = peers.length
    ? peers.map((peer) => `<div class="peer-row">
        <span class="peer-row-copy"><strong>${escapeHtml(peer.name)}</strong><small>${escapeHtml(peer.base_url)}</small></span>
        <button type="button" data-revoke-peer="${escapeHtml(peer.device_id)}">${t("revokeAccess")}</button>
      </div>`).join("")
    : `<p class="quiet">${t("noPeers")}</p>`;
}

function renderPeeringStatus() {
  const status = state.peering;
  if (!status) return;
  const enabled = Boolean(status.sharing_enabled);
  if (document.activeElement !== el("machineName")) el("machineName").value = status.machine_name || "";
  el("peeringEnabled").checked = enabled;
  el("pairingCode").textContent = enabled ? status.pairing_code : "------";
  el("pairingExpiry").textContent = enabled ? `${peeringExpiresIn()} ${t("pairingRefresh")}` : localized("互联已关闭", "Sharing disabled");
  el("peerAddress").value = status.address || "";
  el("peerConnectAddress").disabled = !enabled;
  el("peerConnectCode").disabled = !enabled;
  el("peerConnectForm").querySelector("button[type=submit]").disabled = !enabled;
  renderPeerList(status.peers || []);
}

function applyPeeringStatus(payload, notifyEvents = false) {
  const previousRevision = state.peeringRevision;
  const events = (payload.events || []).filter((event) => Number(event.revision || 0) > previousRevision);
  state.peeringRevision = Number(payload.revision || previousRevision);
  state.peering = { ...payload, received_at: Date.now() };
  renderPeeringStatus();
  if (!notifyEvents || !events.length) return;
  let libraryChanged = false;
  events.forEach((event) => {
    if (event.type === "peer_connected") {
      showToast(`${event.peer_name || t("peerConnected")}：${t("peerConnectNotice")}`);
      libraryChanged = true;
    }
    if (event.type === "peer_revoked") {
      showToast(`${event.peer_name || t("peerConnected")}：${t("peerRevoked")}`);
      libraryChanged = true;
    }
  });
  if (libraryChanged && !state.incognito) refreshSharedData();
}

async function refreshSharedData() {
  if (state.incognito) return;
  await Promise.all([
    loadAssets({ reset: true }),
    refreshConversation(true),
    refreshSharedRuntime(),
  ]);
}

async function refreshPeeringStatus({ notifyEvents = true } = {}) {
  if (state.peeringPolling) return;
  state.peeringPolling = true;
  try {
    const since = state.peering ? state.peeringRevision : 0;
    const payload = await api(`/api/v1/peering/status?since=${since}`);
    applyPeeringStatus(payload, notifyEvents && Boolean(state.peering));
    el("peeringError").textContent = "";
  } catch (error) {
    if (!el("peeringModal").hidden) el("peeringError").textContent = error.message;
  } finally {
    state.peeringPolling = false;
  }
}

function startPeeringPolling() {
  clearInterval(state.peeringTimer);
  clearInterval(state.peeringPollTimer);
  state.peeringTimer = setInterval(() => {
    renderPeeringStatus();
  }, 1000);
}

async function openPeeringDialog() {
  el("peeringModal").hidden = false;
  document.body.classList.add("modal-open");
  el("peeringError").textContent = "";
  refreshIcons();
  await refreshPeeringStatus({ notifyEvents: false });
}

function closePeeringDialog() {
  el("peeringModal").hidden = true;
  el("peeringError").textContent = "";
  if (el("nodeModal").hidden && el("assetDetailModal").hidden) document.body.classList.remove("modal-open");
  el("openPeering").focus();
}

async function updatePeeringSettings(values) {
  try {
    const payload = await api("/api/v1/peering/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    applyPeeringStatus(payload, true);
    el("peeringError").textContent = "";
    if (Object.prototype.hasOwnProperty.call(values, "enabled") && !state.incognito) await refreshSharedData();
  } catch (error) {
    el("peeringError").textContent = error.message;
    await refreshPeeringStatus({ notifyEvents: false });
  }
}

async function connectPeer(event) {
  event.preventDefault();
  const address = el("peerConnectAddress").value.trim();
  const code = el("peerConnectCode").value.trim();
  if (!/^\d{6}$/.test(code)) {
    el("peeringError").textContent = localized("请输入 6 位数字验证码", "Enter a six-digit code");
    return;
  }
  const button = el("peerConnectForm").querySelector("button[type=submit]");
  button.disabled = true;
  el("peeringError").textContent = "";
  try {
    const result = await api("/api/v1/peering/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address, code }),
    });
    applyPeeringStatus(result.status, false);
    el("peerConnectAddress").value = "";
    el("peerConnectCode").value = "";
    showToast(`${result.peer?.name || t("peerConnected")}：${t("peerConnectNotice")}`);
    if (!state.incognito) await refreshSharedData();
  } catch (error) {
    el("peeringError").textContent = error.message;
  } finally {
    button.disabled = !state.peering?.sharing_enabled;
  }
}

async function revokePeer(deviceId) {
  if (!window.confirm(localized("确认撤销该设备的素材库访问授权？", "Revoke this device's library access?"))) return;
  try {
    const result = await api(`/api/v1/peering/peers/${encodeURIComponent(deviceId)}`, { method: "DELETE" });
    const peer = state.peering?.peers?.find((item) => item.device_id === deviceId);
    applyPeeringStatus(result.status, false);
    showToast(`${peer?.name || t("peerConnected")}：${t("peerRevoked")}`);
    if (!state.incognito) await refreshSharedData();
  } catch (error) {
    el("peeringError").textContent = error.message;
  }
}

el("referenceList").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-remove-reference]");
  if (!button) return;
  const index = Number(button.dataset.removeReference);
  const [removed] = state.references.splice(index, 1);
  if (removed?.url) URL.revokeObjectURL(removed.url);
  renderReferences();
});

el("addReference").addEventListener("click", () => {
  state.pendingRunningHubMediaField = "";
  referenceInput.click();
});

document.addEventListener("paste", (event) => {
  const file = clipboardImageFile(event);
  if (!file) return;
  event.preventDefault();
  const added = addFiles([file], state.pendingRunningHubMediaField);
  if (added) showToast(localized("已从剪贴板添加图片", "Image pasted from clipboard"));
  updateModelUi();
});

referenceInput.addEventListener("change", () => {
  addFiles(referenceInput.files, state.pendingRunningHubMediaField);
  referenceInput.value = "";
  updateModelUi();
});
el("runningHubParameters").addEventListener("input", (event) => {
  const input = event.target.closest("[data-runninghub-key]");
  if (!input) return;
  state.runningHubParameters[input.dataset.runninghubKey] = input.type === "checkbox" ? input.checked : input.value;
  state.runningHubRenderSignature = runningHubParameterRenderSignature();
});
el("runningHubParameters").addEventListener("click", (event) => {
  const button = event.target.closest("[data-runninghub-media-key]");
  if (!button) return;
  state.pendingRunningHubMediaField = button.dataset.runninghubMediaKey;
  referenceInput.accept = button.dataset.runninghubMediaKind === "file" ? "*/*" : `${button.dataset.runninghubMediaKind}/*`;
  referenceInput.click();
});

const composerBox = el("dropZone");
["dragenter", "dragover"].forEach((name) => composerBox.addEventListener(name, (event) => {
  event.preventDefault();
  composerBox.classList.add("dragging");
}));
["dragleave", "drop"].forEach((name) => composerBox.addEventListener(name, (event) => {
  event.preventDefault();
  composerBox.classList.remove("dragging");
}));
composerBox.addEventListener("drop", async (event) => {
  const jobId = event.dataTransfer.getData("application/x-h3-asset-job");
  if (!jobId) return addFiles(event.dataTransfer.files);
  try {
    await useGeneratedOutputAsInput(jobId);
  } catch (error) {
    showError(error.message);
  }
});

promptInput.addEventListener("keydown", (event) => {
  if (handleMentionKeydown(event)) return;
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") form.requestSubmit();
});
promptInput.addEventListener("input", () => {
  if (el("mentionMenu").dataset.open === "true") requestAnimationFrame(positionMentionMenu);
});
promptInput.addEventListener("click", () => {
  if (el("mentionMenu").dataset.open === "true") requestAnimationFrame(positionMentionMenu);
});
promptInput.addEventListener("scroll", positionMentionMenu, { passive: true });

el("assetGrid").addEventListener("click", (event) => {
  const inputAction = event.target.closest("[data-asset-input]");
  if (inputAction) {
    event.stopPropagation();
    useGeneratedOutputAsInput(inputAction.dataset.assetInput).catch((error) => showError(error.message));
    return;
  }
  const action = event.target.closest("[data-job-action]");
  if (action) {
    event.stopPropagation();
    handleJobAction(action.dataset.jobAction, action.dataset.jobId);
    return;
  }
  const card = event.target.closest("[data-asset-job]");
  if (card) openAssetDetail(card.dataset.assetJob);
});
el("assetGrid").addEventListener("dragstart", (event) => {
  const card = event.target.closest('[data-asset-output="true"]');
  if (!card) return;
  event.dataTransfer.effectAllowed = "copy";
  event.dataTransfer.setData("application/x-h3-asset-job", card.dataset.assetJob);
  event.dataTransfer.setData("text/plain", card.dataset.assetJob);
  card.classList.add("dragging");
});
el("assetGrid").addEventListener("dragend", (event) => {
  event.target.closest(".asset-card")?.classList.remove("dragging");
});
el("assetGrid").addEventListener("keydown", (event) => {
  if (["Enter", " "].includes(event.key) && event.target.matches("[data-asset-job]")) {
    event.preventDefault();
    openAssetDetail(event.target.dataset.assetJob);
  }
});
el("assetGrid").addEventListener("scroll", () => {
  const grid = el("assetGrid");
  if (grid.scrollHeight - grid.scrollTop - grid.clientHeight < 180) loadAssets();
}, { passive: true });

el("conversationFeed").addEventListener("click", (event) => {
  const action = event.target.closest("[data-job-action]");
  if (action) return handleJobAction(action.dataset.jobAction, action.dataset.jobId);
});
el("conversationFeed").addEventListener("scroll", () => {
  const currentTop = el("conversationFeed").scrollTop;
  const movingUp = currentTop < state.conversationScrollTop;
  state.conversationScrollTop = currentTop;
  if (state.conversationReady && movingUp && currentTop < 72) loadOlderMessages();
}, { passive: true });

el("queueList").addEventListener("click", (event) => {
  const action = event.target.closest("[data-job-action]");
  if (action) return handleJobAction(action.dataset.jobAction, action.dataset.jobId);
  const row = event.target.closest("[data-scroll-job]");
  if (row) scrollToJob(row.dataset.scrollJob);
});
el("logList").addEventListener("click", (event) => {
  const item = event.target.closest("[data-scroll-job]");
  if (item) scrollToJob(item.dataset.scrollJob);
});

el("newTaskButton").addEventListener("click", newTask);
el("exitEdit").addEventListener("click", resetComposer);
el("assetStatusFilter").addEventListener("change", () => loadAssets({ reset: true }));
el("refreshAssets").addEventListener("click", () => refreshSharedData());
let assetSearchTimer = null;
el("assetSearch").addEventListener("input", () => {
  clearTimeout(assetSearchTimer);
  assetSearchTimer = setTimeout(() => loadAssets({ reset: true }), 250);
});

el("closeAssetDetail").addEventListener("click", closeAssetDetail);
el("assetDetailModal").addEventListener("click", (event) => {
  if (event.target === el("assetDetailModal")) closeAssetDetail();
});
el("reuseAssetDetail").addEventListener("click", () => {
  if (state.assetDetailJob) backfillJob(state.assetDetailJob.id);
});
el("reuseOutputAssetDetail").addEventListener("click", () => {
  if (!state.assetDetailJob) return;
  useGeneratedOutputAsInput(state.assetDetailJob.id).catch((error) => {
    el("assetDetailError").textContent = error.message;
  });
});
el("regenerateAssetDetail").addEventListener("click", () => {
  if (state.assetDetailJob) regenerateJob(state.assetDetailJob.id);
});
el("deleteAssetDetail").addEventListener("click", async () => {
  if (!state.assetDetailJob) return;
  const deleted = await deleteJob(state.assetDetailJob.id);
  if (deleted) closeAssetDetail();
  else el("assetDetailError").textContent = el("formError").textContent;
});
el("languageToggle").addEventListener("click", () => {
  localStorage.setItem("h3-locale", state.locale === "en" ? "zh-CN" : "en");
  window.location.reload();
});

["aiEnabled", "aiBaseUrl", "aiModel", "aiApiKey"].forEach((id) => el(id).addEventListener("change", () => {
  saveAiConfig().catch((error) => showError(error.message));
}));
el("openPeering").addEventListener("click", openPeeringDialog);
el("closePeering").addEventListener("click", closePeeringDialog);
el("peeringModal").addEventListener("click", (event) => {
  if (event.target === el("peeringModal")) closePeeringDialog();
});
el("peeringEnabled").addEventListener("change", () => updatePeeringSettings({ enabled: el("peeringEnabled").checked }));
el("machineName").addEventListener("change", () => updatePeeringSettings({ machine_name: el("machineName").value.trim() }));
el("openGlobalSettings").addEventListener("click", openGlobalSettings);
el("closeGlobalSettings").addEventListener("click", closeGlobalSettings);
el("globalSettingsModal").addEventListener("click", (event) => { if (event.target === el("globalSettingsModal")) closeGlobalSettings(); });
el("globalSettingsForm").addEventListener("submit", saveGeneralSettings);
el("toggleRemoteRecordsKey").addEventListener("click", () => togglePasswordField("remoteRecordsKey", "toggleRemoteRecordsKey"));
el("manageLocalAssets").addEventListener("click", openLocalAssets);
el("closeLocalAssets").addEventListener("click", closeLocalAssets);
el("deleteLocalArtifacts").addEventListener("click", deleteLocalArtifacts);
el("localAssetsModal").addEventListener("click", (event) => { if (event.target === el("localAssetsModal")) closeLocalAssets(); });
el("closeLocalAssetPreview").addEventListener("click", closeLocalAssetPreview);
el("localAssetPreviewModal").addEventListener("click", (event) => { if (event.target === el("localAssetPreviewModal")) closeLocalAssetPreview(); });
el("localAssetsList").addEventListener("change", (event) => {
  const checkbox = event.target.closest('input[type="checkbox"]');
  if (!checkbox) return;
  if (checkbox.checked) state.localAssetSelected.add(checkbox.value);
  else state.localAssetSelected.delete(checkbox.value);
  syncLocalAssetSelectAll();
});
el("localAssetsList").addEventListener("click", (event) => {
  if (event.target.closest("[data-local-asset-select], input[type=checkbox]")) return;
  const button = event.target.closest("[data-unlock-owner]");
  if (button) {
    event.stopPropagation();
    openUnlockAssets(button.dataset.unlockOwner, button.dataset.unlockName);
    return;
  }
  const card = event.target.closest("[data-local-asset-id]");
  if (!card) return;
  const asset = state.localAssets.find((item) => item.id === card.dataset.localAssetId);
  if (!asset) return;
  if (asset.locked) openUnlockAssets(asset.owner_device_id, asset.owner_name);
  else openLocalAssetPreview(asset);
});
el("localAssetsList").addEventListener("keydown", (event) => {
  if (!["Enter", " "].includes(event.key) || !event.target.matches("[data-local-asset-id]")) return;
  event.preventDefault();
  const asset = state.localAssets.find((item) => item.id === event.target.dataset.localAssetId);
  if (!asset) return;
  if (asset.locked) openUnlockAssets(asset.owner_device_id, asset.owner_name);
  else openLocalAssetPreview(asset);
});
el("localAssetsList").addEventListener("scroll", () => {
  const list = el("localAssetsList");
  if (list.scrollHeight - list.scrollTop - list.clientHeight < 120) loadLocalAssets();
}, { passive: true });
el("localAssetsSelectAll").addEventListener("change", () => {
  state.localAssets.filter((asset) => !asset.asset_deleted).forEach((asset) => {
    if (el("localAssetsSelectAll").checked) state.localAssetSelected.add(asset.id);
    else state.localAssetSelected.delete(asset.id);
  });
  renderLocalAssetManager();
});
el("closeUnlockAssets").addEventListener("click", closeUnlockAssets);
el("unlockAssetsModal").addEventListener("click", (event) => { if (event.target === el("unlockAssetsModal")) closeUnlockAssets(); });
el("unlockAssetsForm").addEventListener("submit", unlockLocalAssets);
el("toggleUnlockAssetsKey").addEventListener("click", () => togglePasswordField("unlockAssetsKey", "toggleUnlockAssetsKey"));
el("conversationFilterToggle").addEventListener("click", (event) => {
  event.stopPropagation();
  state.conversationFilterOpen = !state.conversationFilterOpen;
  el("conversationFilterPanel").hidden = !state.conversationFilterOpen;
  el("conversationFilterToggle").setAttribute("aria-expanded", String(state.conversationFilterOpen));
});
el("conversationFilterPanel").addEventListener("click", (event) => event.stopPropagation());
el("conversationDeviceFilter").addEventListener("change", () => {
  state.conversationDeviceIds = new Set(Array.from(el("conversationDeviceFilter").selectedOptions).map((option) => option.value));
  updateConversationFilterChrome();
  state.conversationRevisionSignature = "";
  refreshConversation(true);
});
document.addEventListener("click", () => {
  if (!state.conversationFilterOpen) return;
  state.conversationFilterOpen = false;
  el("conversationFilterPanel").hidden = true;
  el("conversationFilterToggle").setAttribute("aria-expanded", "false");
});
el("peerConnectCode").addEventListener("input", () => {
  el("peerConnectCode").value = el("peerConnectCode").value.replace(/\D/g, "").slice(0, 6);
});
el("peerConnectForm").addEventListener("submit", connectPeer);
el("peerList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-revoke-peer]");
  if (button) revokePeer(button.dataset.revokePeer);
});
el("mentionTrigger").addEventListener("click", () => {
  if (el("mentionControl").dataset.open === "true") closeMentionMenu();
  else openMentionMenu({ focusPrompt: true });
});
el("mentionMenu").addEventListener("click", (event) => {
  const reference = event.target.closest("[data-mention-reference]");
  if (reference) insertReferenceMention(Number(reference.dataset.mentionReference));
});
el("mentionMenu").addEventListener("pointermove", (event) => {
  const item = event.target.closest(".mention-menu-item");
  if (!item) return;
  const index = mentionMenuItems().indexOf(item);
  if (index >= 0 && index !== state.mentionIndex) setMentionIndex(index, false);
});
document.addEventListener("pointerdown", (event) => {
  if (!event.target.closest("#mentionControl, #mentionMenu") && event.target !== promptInput) closeMentionMenu();
});
window.addEventListener("resize", positionMentionMenu);
window.addEventListener("scroll", positionMentionMenu, { passive: true, capture: true });
el("optimizePrompt").addEventListener("click", () => {
  closeMentionMenu();
  removePendingMentionTrigger();
  optimizePrompt();
});
el("writeLyrics").addEventListener("click", () => {
  closeMentionMenu();
  removePendingMentionTrigger();
  assistMusic("lyrics");
});
el("modelVariant").addEventListener("change", updateModelUi);
el("executionMode").addEventListener("change", updateModelUi);
el("comfyNode").addEventListener("change", updateModelUi);
el("duration").closest(".duration-control").addEventListener("mouseenter", positionDurationTooltip);
el("duration").closest(".duration-control").addEventListener("focusin", positionDurationTooltip);

el("openNodeManager").addEventListener("click", openNodeManager);
el("closeNodeManager").addEventListener("click", closeNodeManager);
el("addNodeButton").addEventListener("click", () => openNodeEditor());
el("cancelNodeEdit").addEventListener("click", closeNodeEditor);
el("cancelNodeEditIcon").addEventListener("click", closeNodeEditor);
if (el("saveNodeSettings")) el("saveNodeSettings").addEventListener("click", saveNodeSettings);
el("nodeEditor").addEventListener("submit", saveNode);
el("nodeProvider").addEventListener("change", syncNodeProviderFields);
el("nodeList").addEventListener("click", (event) => {
  const action = event.target.closest("[data-node-action]");
  const row = action?.closest("[data-node-id]");
  if (!action || !row) return;
  if (action.dataset.nodeAction === "edit") openNodeEditor(row.dataset.nodeId);
  if (action.dataset.nodeAction === "delete") deleteNode(row.dataset.nodeId);
});
el("nodeModal").addEventListener("click", (event) => {
  if (event.target === el("nodeModal")) closeNodeManager();
});

el("brandTrigger").addEventListener("click", () => {
  const now = Date.now();
  state.brandClicks = [...state.brandClicks.filter((time) => now - time < 1500), now];
  if (state.brandClicks.length >= 3) {
    state.brandClicks = [];
    requestIncognitoMode();
  }
});
el("incognitoStatus").addEventListener("click", async () => {
  state.incognito = false;
  state.incognitoCode = "";
  updateIncognitoUi();
  await reloadModeData();
});
el("secretForm").addEventListener("submit", authorizeIncognitoMode);
el("closeSecret").addEventListener("click", closeSecretDialog);
el("secretOverlay").addEventListener("click", (event) => {
  if (event.target === el("secretOverlay")) closeSecretDialog();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMentionMenu();
  if (event.key === "Escape" && !el("localAssetPreviewModal").hidden) {
    closeLocalAssetPreview();
    return;
  }
  if (event.key === "Escape" && !el("secretOverlay").hidden) closeSecretDialog();
  if (event.key === "Escape" && !el("peeringModal").hidden) closePeeringDialog();
  if (event.key === "Escape" && !el("nodeModal").hidden) closeNodeManager();
  if (event.key === "Escape" && !el("assetDetailModal").hidden) closeAssetDetail();
});

el("clearVisibleLogs").addEventListener("click", () => {
  state.logFloor = Date.now();
  renderLogs(state.logs);
});
let launcherClickSuppressed = false;
el("opsLauncher").addEventListener("click", (event) => {
  if (launcherClickSuppressed) {
    launcherClickSuppressed = false;
    event.preventDefault();
    return;
  }
  openOpsWindow();
});
el("closeOps").addEventListener("click", closeOpsWindow);
el("openAssets").addEventListener("click", openAssetDrawer);
el("closeAssets").addEventListener("click", closeAssetDrawer);
el("mobileScrim").addEventListener("click", closeAssetDrawer);

let dragState = null;
function startOpsDrag(clientX, clientY) {
  dragState = {
    startX: clientX,
    startY: clientY,
    originX: state.opsPosition.x,
    originY: state.opsPosition.y,
  };
  el("opsWindow").classList.add("dragging");
}
function moveOpsDrag(clientX, clientY) {
  if (!dragState) return;
  state.opsPosition.x = dragState.originX + clientX - dragState.startX;
  state.opsPosition.y = dragState.originY + clientY - dragState.startY;
  applyOpsPosition();
}
function stopOpsDrag() {
  if (!dragState) return;
  dragState = null;
  el("opsWindow").classList.remove("dragging");
}
el("opsDragHandle").addEventListener("mousedown", (event) => {
  if (event.button !== 0 || event.target.closest("button")) return;
  event.preventDefault();
  startOpsDrag(event.clientX, event.clientY);
});
window.addEventListener("mousemove", (event) => moveOpsDrag(event.clientX, event.clientY));
window.addEventListener("mouseup", stopOpsDrag);
el("opsDragHandle").addEventListener("pointerdown", (event) => {
  if (event.button !== 0 || event.target.closest("button")) return;
  event.preventDefault();
  startOpsDrag(event.clientX, event.clientY);
});
window.addEventListener("pointermove", (event) => moveOpsDrag(event.clientX, event.clientY));
window.addEventListener("pointerup", stopOpsDrag);
window.addEventListener("pointercancel", stopOpsDrag);
el("opsDragHandle").addEventListener("touchstart", (event) => {
  if (event.target.closest("button")) return;
  const touch = event.touches[0];
  if (!touch) return;
  event.preventDefault();
  startOpsDrag(touch.clientX, touch.clientY);
}, { passive: false });
window.addEventListener("touchmove", (event) => {
  const touch = event.touches[0];
  if (!dragState || !touch) return;
  event.preventDefault();
  moveOpsDrag(touch.clientX, touch.clientY);
}, { passive: false });
window.addEventListener("touchend", stopOpsDrag);
window.addEventListener("touchcancel", stopOpsDrag);

let launcherDragState = null;
function initializeLauncherPosition() {
  if (state.launcherPositionInitialized) return;
  const launcher = el("opsLauncher");
  const rect = launcher.getBoundingClientRect();
  state.launcherPosition = { x: rect.left, y: rect.top };
  state.launcherPositionInitialized = true;
  launcher.style.left = `${rect.left}px`;
  launcher.style.top = `${rect.top}px`;
  launcher.style.right = "auto";
}
function applyLauncherPosition() {
  if (!state.launcherPositionInitialized) return;
  const launcher = el("opsLauncher");
  const rect = launcher.getBoundingClientRect();
  const maxX = Math.max(8, window.innerWidth - rect.width - 8);
  const maxY = Math.max(8, window.innerHeight - rect.height - 8);
  state.launcherPosition.x = Math.min(maxX, Math.max(8, state.launcherPosition.x));
  state.launcherPosition.y = Math.min(maxY, Math.max(8, state.launcherPosition.y));
  launcher.style.left = `${state.launcherPosition.x}px`;
  launcher.style.top = `${state.launcherPosition.y}px`;
}
function startLauncherDrag(clientX, clientY) {
  initializeLauncherPosition();
  launcherDragState = {
    startX: clientX,
    startY: clientY,
    originX: state.launcherPosition.x,
    originY: state.launcherPosition.y,
    moved: false,
  };
  el("opsLauncher").classList.add("dragging");
}
function moveLauncherDrag(clientX, clientY) {
  if (!launcherDragState) return;
  const deltaX = clientX - launcherDragState.startX;
  const deltaY = clientY - launcherDragState.startY;
  if (Math.abs(deltaX) > 3 || Math.abs(deltaY) > 3) launcherDragState.moved = true;
  state.launcherPosition.x = launcherDragState.originX + deltaX;
  state.launcherPosition.y = launcherDragState.originY + deltaY;
  applyLauncherPosition();
}
function stopLauncherDrag() {
  if (!launcherDragState) return;
  launcherClickSuppressed = launcherDragState.moved;
  launcherDragState = null;
  el("opsLauncher").classList.remove("dragging");
}
el("opsLauncher").addEventListener("mousedown", (event) => {
  if (event.button !== 0) return;
  event.preventDefault();
  startLauncherDrag(event.clientX, event.clientY);
});
window.addEventListener("mousemove", (event) => moveLauncherDrag(event.clientX, event.clientY));
window.addEventListener("mouseup", stopLauncherDrag);
el("opsLauncher").addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  event.preventDefault();
  startLauncherDrag(event.clientX, event.clientY);
});
window.addEventListener("pointermove", (event) => moveLauncherDrag(event.clientX, event.clientY));
window.addEventListener("pointerup", stopLauncherDrag);
window.addEventListener("pointercancel", stopLauncherDrag);
el("opsLauncher").addEventListener("touchstart", (event) => {
  const touch = event.touches[0];
  if (!touch) return;
  event.preventDefault();
  startLauncherDrag(touch.clientX, touch.clientY);
}, { passive: false });
window.addEventListener("touchmove", (event) => {
  const touch = event.touches[0];
  if (!launcherDragState || !touch) return;
  event.preventDefault();
  moveLauncherDrag(touch.clientX, touch.clientY);
}, { passive: false });
window.addEventListener("touchend", stopLauncherDrag);
window.addEventListener("touchcancel", stopLauncherDrag);
window.addEventListener("resize", () => {
  if (!el("opsWindow").hidden) applyOpsPosition();
  applyLauncherPosition();
});

async function initialize() {
  applyStaticLocale();
  updateModelUi();
  updateIncognitoUi();
  renderReferences();
  refreshIcons();
  startPeeringPolling();
  connectEventStream();
  await Promise.allSettled([
    loadAiConfig().catch((error) => showError(error.message)),
    loadGeneralSettings().catch((error) => showError(error.message)),
    refreshPeeringStatus({ notifyEvents: false }),
    checkHealth(),
    refreshSharedData(),
  ]);
}

initialize();
el("lucideScript")?.addEventListener("load", refreshIcons);
window.addEventListener("load", refreshIcons);
window.addEventListener("beforeunload", () => {
  state.stream?.close();
  clearInterval(state.peeringTimer);
  clearInterval(state.peeringPollTimer);
});
