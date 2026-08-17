const state = {
  references: [],
  assets: [],
  assetPage: 0,
  assetPages: 1,
  assetPageSize: 16,
  assetTotal: 0,
  assetRevision: 0,
  assetLoading: false,
  assetHasMore: true,
  assetLoadError: "",
  assetDetailJob: null,
  conversations: [],
  conversationPage: 1,
  conversationPages: 1,
  conversationPageSize: 10,
  conversationRevision: 0,
  conversationLoading: false,
  conversationRefreshPending: false,
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
  logs: [],
  stream: null,
  incognito: false,
  incognitoCode: "",
  brandClicks: [],
  opsPosition: { x: 0, y: 0 },
  mentionIndex: -1,
  locale: localStorage.getItem("h3-locale") === "en" ? "en" : "zh-CN",
};

const el = (id) => document.getElementById(id);
const form = el("generationForm");
const promptInput = el("prompt");
const referenceInput = el("referenceInput");
const H3_DURATIONS = Array.from({ length: 15 }, (_, index) => index + 1);
const MUSIC3_DURATIONS = [30, 60, 120, 180, 240, 300];

const COPY = {
  "zh-CN": {
    assetLibrary: "素材库", assetSearch: "搜索素材", allStatuses: "全部状态", queued: "排队中", running: "生成中", completed: "已完成", failed: "失败", cancelled: "已取消",
    conversation: "H3 对话", switchLanguage: "Switch to English", apiDocs: "API 文档", newGeneration: "新建生成", close: "关闭", assets: "素材库",
    connectEngine: "连接推理节点", offline: "服务离线", autoSchedule: "自动调度", nodePending: "节点待分配", online: "在线", available: "可用", nodeOffline: "离线", disabled: "已停用", busy: "执行中",
    balance: "余额", credits: "点数", recentCost: "最近调用消耗", accountUnavailable: "账户信息不可用", balancePending: "余额读取中", accountTasks: "账户任务", balanceUpdated: "余额更新", balanceFailed: "余额读取失败",
    noAssets: "暂无素材", loading: "加载中", allLoaded: "已加载全部", loadFailed: "加载失败", startCreating: "开始创作", you: "你",
    native: "普通流 · 原生 H3", turbo: "8-step LoRA · 强度 1.0", digitalHuman: "数字人 · 音频驱动", music3: "Music3 · 30 步", nsfw: "H3 NSFW · NaughtyTimes LoRA", speedCache: "Speed Cache（已停用）",
    reuse: "回填到发送区", regenerate: "重新生成", edit: "修改", cancel: "取消", delete: "删除", deleteRecord: "删除记录", downloadVideo: "下载 MP4", downloadAudio: "下载 FLAC", videoReady: "视频已生成", musicReady: "音乐已生成",
    assetDetail: "素材详情", prompt: "关键词与提示词", lyrics: "歌词", sourceFiles: "使用的文件", parameters: "生成参数", noSourceFiles: "未使用参考文件", outputUnavailable: "当前没有可预览的生成产物",
    deleteConfirm: "删除后将同时清理任务记录、上传素材和生成产物，确认继续？", regenerateConfirm: "将使用本条任务的参数和参考文件创建新的生成任务，确认继续？", fillLoading: "正在读取原始文件", fillDone: "已回填到发送区", fileUnavailable: "参考文件已不存在，无法完整回填",
    overallTime: "总体耗时", steps: "步", seed: "seed", seconds: "秒", queuePosition: "队列位置", incognito: "无痕", destroy: "销毁",
  },
  en: {
    assetLibrary: "Assets", assetSearch: "Search assets", allStatuses: "All statuses", queued: "Queued", running: "Running", completed: "Completed", failed: "Failed", cancelled: "Cancelled",
    conversation: "H3 Chat", switchLanguage: "切换为中文", apiDocs: "API documentation", newGeneration: "New generation", close: "Close", assets: "Assets",
    connectEngine: "Connecting to inference nodes", offline: "Service offline", autoSchedule: "Auto", nodePending: "Awaiting node", online: "Online", available: "available", nodeOffline: "Offline", disabled: "Disabled", busy: "Running",
    balance: "Balance", credits: "credits", recentCost: "Recent call cost", accountUnavailable: "Account unavailable", balancePending: "Loading balance", accountTasks: "Account tasks", balanceUpdated: "balance updated", balanceFailed: "balance read failed",
    noAssets: "No assets", loading: "Loading", allLoaded: "All assets loaded", loadFailed: "Load failed", startCreating: "Start creating", you: "You",
    native: "Native H3", turbo: "8-step LoRA · 1.0", digitalHuman: "Digital human · audio driven", music3: "Music3 · 30 steps", nsfw: "H3 NSFW · NaughtyTimes LoRA", speedCache: "Speed Cache (disabled)",
    reuse: "Fill composer", regenerate: "Regenerate", edit: "Edit", cancel: "Cancel", delete: "Delete", deleteRecord: "Delete record", downloadVideo: "Download MP4", downloadAudio: "Download FLAC", videoReady: "Video generated", musicReady: "Music generated",
    assetDetail: "Asset details", prompt: "Keywords and prompt", lyrics: "Lyrics", sourceFiles: "Source files", parameters: "Parameters", noSourceFiles: "No reference files", outputUnavailable: "No generated output is available for preview",
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
  setTitle("#apiDocsLink", t("apiDocs"));
  setTitle("#closeAssetDetail", t("close"));
  setText("#assetDetailTitle", t("assetDetail"));
  setText("#deleteAssetDetail span", t("deleteRecord"));
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
  setText('#executionMode option[value="digital-human"]', "Digital human · audio driven");
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
  setText('label[for="nodeWorkflowId"]', "Target workflow ID");
  setText('label[for="nodeMaxConcurrency"]', "Maximum API concurrency");
  setText(".node-enabled-row > span:first-child", "Enable node");
  setText("#cancelNodeEdit", "Cancel");
  setText("#nodeEditor button.primary", "Save node");
  setText(".secret-dialog h2", "Incognito access");
  setText('label[for="secretCode"]', "Access code");
  setText(".secret-submit", "Enter incognito mode");
  setLeadingText("#seed", "Random seed");
  setLeadingText("#aiBaseUrl", "OpenAI Base URL");
  setLeadingText("#aiModel", "Model");
  setLeadingText("#aiApiKey", "API Key");
  setText(".popover-panel .switch-row > span:first-child", "Enable AI prompt assistance");
  el("seed").placeholder = "Auto";
  setTitle("#addReference", "Add reference files");
  setTitle("#advancedSettings summary", "More settings");
  setTitle("#mentionTrigger", "Insert image or use a quick action");
  setTitle("#optimizePrompt", "Optimize prompt");
  setTitle("#writeLyrics", "Optimize lyrics");
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
  if (job.assigned_node?.provider === "runninghub") {
    return job.assigned_node.workflow_name || job.assigned_node.name || "RunningHub";
  }
  if (job.request?.model_variant === "music3-int8") return "Music3 INT8";
  return job.request?.model_variant === "ref2va-fp8" ? "Ref2VA FP8" : "FL2VA FP8";
}

function executionModeLabel(job) {
  if (job.assigned_node?.provider === "runninghub") return "RunningHub";
  if (job.request?.execution_mode === "music3") return t("music3");
  if (job.request?.execution_mode === "digital-human") return t("digitalHuman");
  if (job.request?.execution_mode === "h3-nsfw") return t("nsfw");
  if (job.request?.execution_mode === "turbo-lora") return t("turbo");
  if (job.request?.execution_mode === "speed-cache") return t("speedCache");
  return t("native");
}

function executionModeClass(job) {
  if (job.request?.execution_mode === "music3") return "music3";
  if (job.request?.execution_mode === "digital-human") return "digital-human";
  if (job.request?.execution_mode === "h3-nsfw") return "nsfw";
  if (job.request?.execution_mode === "turbo-lora") return "turbo";
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
  if (job.assigned_node?.name) return job.assigned_node.name;
  const requested = job.request?.comfy_node || "auto";
  if (requested === "auto") return job.status === "queued" ? t("autoSchedule") : t("nodePending");
  return state.nodes.find((node) => node.id === requested)?.name || requested;
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
  return node.error ? t("accountUnavailable") : t("balancePending");
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
  const online = state.nodes.filter((node) => node.healthy).length;
  const options = [`<option value="auto">${t("autoSchedule")} · ${online}/${state.nodes.length} ${t("available")}</option>`];
  state.nodes.forEach((node) => {
    const running = Number(node.running_count || 0);
    const capacity = Number(node.capacity || 1);
    const stateLabel = node.provider === "runninghub"
      ? `${running ? `${t("busy")} ${running}/${capacity} · ` : ""}${runningHubBalanceLabel(node)}`
      : !node.healthy
        ? t("nodeOffline")
        : running
          ? `${t("busy")} ${running}/${capacity}`
          : `${t("online")} 0/${capacity}`;
    const label = node.provider === "runninghub"
      ? `${escapeHtml(node.workflow_name || node.name)} · ID ${escapeHtml(node.workflow_id || "-")}`
      : escapeHtml(node.name);
    options.push(`<option value="${escapeHtml(node.id)}"${node.healthy ? "" : " disabled"}>${label} · ${escapeHtml(stateLabel)}</option>`);
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
    if (node.busy) return { label: t("busy"), className: "busy" };
    return {
      label: runningHubBalanceLabel(node),
      className: node.error ? "disabled" : "online",
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
  el("nodeWorkflowId").required = runningHub;
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
  el("nodeNameLabel").textContent = runningHub
    ? localized("工作流名称", "Workflow name")
    : localized("节点名称", "Node name");
}

function renderManagedNodes() {
  el("nodeManagerSummary").textContent = state.locale === "en" ? `${state.managedNodes.length} nodes` : `${state.managedNodes.length} 个节点`;
  el("nodeList").innerHTML = state.managedNodes.length ? state.managedNodes.map((node) => {
    const status = nodeStatus(node);
    const running = Number(node.running_count || 0);
    const capacity = Number(node.capacity || node.max_concurrency || 1);
    const activity = node.busy
      ? ` · ${localized("并发", "capacity")} ${running}/${capacity}`
      : node.queue_depth ? ` · 排队 ${node.queue_depth}` : "";
    const provider = node.provider === "runninghub" ? "RunningHub API" : "ComfyUI API";
    const workflow = node.provider === "runninghub" ? ` · Workflow ${escapeHtml(node.workflow_id || "-")}` : "";
    const keyState = node.has_api_key ? ` · ${localized("API Key 已保存", "API Key saved")}` : "";
    const accountTasks = node.provider === "runninghub" && node.account_current_tasks != null
      ? ` · ${t("accountTasks")} ${escapeHtml(String(node.account_current_tasks))}`
      : "";
    const recentCost = node.provider === "runninghub" ? runningHubCostLabel(node) : "";
    const accountingTitle = [
      localized("按调用前后余额差值计算；同一 API Key 并发使用时可能包含同期扣费", "Calculated from the balance difference before and after a call; concurrent use of the same API key can include other charges"),
      node.error || "",
    ].filter(Boolean).join(" · ");
    const accounting = node.provider === "runninghub"
      ? `<small class="node-accounting" title="${escapeHtml(accountingTitle)}">${escapeHtml(runningHubBalanceLabel(node))}${accountTasks}${recentCost ? ` · ${escapeHtml(recentCost)}` : ""}</small>`
      : "";
    const checkedLabel = node.provider === "runninghub"
      ? node.error ? t("balanceFailed") : t("balanceUpdated")
      : localized("检测", "checked");
    return `<div class="node-row" data-node-id="${escapeHtml(node.id)}">
      <span class="node-state ${status.className}" aria-hidden="true"></span>
      <div class="node-row-copy"><div><strong>${escapeHtml(node.name)}</strong><span>${escapeHtml(status.label)}${activity}</span></div><code title="${escapeHtml(node.url)}">${escapeHtml(node.url)}</code>${accounting}<small>${provider}${workflow}${keyState} · ID ${escapeHtml(node.id)}${node.last_checked ? ` · ${formatTime(node.last_checked, true)} ${checkedLabel}` : ""}</small></div>
      <div class="node-row-actions"><button type="button" data-node-action="edit" title="编辑节点" aria-label="编辑 ${escapeHtml(node.name)}">${icon("pencil")}</button><button type="button" data-node-action="delete" title="删除节点" aria-label="删除 ${escapeHtml(node.name)}">${icon("trash-2")}</button></div>
    </div>`;
  }).join("") : `<p class="quiet">${state.locale === "en" ? "No nodes" : "暂无节点"}</p>`;
  refreshIcons();
}

function syncManagedNodeStatuses(nodes) {
  if (!state.managedNodes.length) return;
  const statuses = new Map(nodes.map((node) => [node.id, node]));
  state.managedNodes = state.managedNodes.map((node) => ({ ...node, ...(statuses.get(node.id) || {}) }));
  if (!el("nodeModal").hidden) renderManagedNodes();
}

async function loadManagedNodes() {
  const payload = await api("/api/v1/comfy/nodes");
  const statuses = new Map(state.nodes.map((node) => [node.id, node]));
  state.managedNodes = (payload.data || []).map((node) => ({
    ...node,
    ...(statuses.get(node.id) || {}),
  }));
  el("nodeHealthInterval").value = String(payload.health_interval_seconds || 60);
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
  el("nodeWorkflowId").value = node?.workflow_id || "";
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
  document.body.classList.remove("modal-open");
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
    workflow_id: el("nodeWorkflowId").value.trim(),
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

function selectedInferenceNode() {
  const nodeId = el("comfyNode").value;
  return nodeId === "auto" ? null : state.nodes.find((node) => node.id === nodeId) || null;
}

function selectedRunningHubNode() {
  const node = selectedInferenceNode();
  if (node?.provider === "runninghub") return node;
  if (el("comfyNode").value !== "auto") return null;
  const candidates = state.nodes.filter((item) => item.healthy);
  if (!candidates.length || candidates.some((item) => item.provider !== "runninghub")) return null;
  const workflowIds = new Set(candidates.map((item) => item.workflow_id));
  const variants = new Set(candidates.map((item) => item.workflow_variant));
  const modes = new Set(candidates.map((item) => item.workflow_execution_mode));
  return workflowIds.size === 1 && variants.size === 1 && modes.size === 1 ? candidates[0] : null;
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

function isMusic3(variant = selectedVariant()) {
  return variant === "music3-int8";
}

function referenceLimits(variant = selectedVariant()) {
  if (isMusic3(variant)) return { image: 0, video: 0, audio: 0 };
  if (isDigitalHuman()) return { image: 1, video: 0, audio: 1 };
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
  return null;
}

function referenceLabels(
  references = state.references,
  variant = selectedVariant(),
  executionMode = selectedExecutionMode(),
) {
  const counts = { image: 0, video: 0, audio: 0 };
  return references.map((item) => {
    const kind = item.kind || item.type;
    counts[kind] += 1;
    if (isDigitalHuman(executionMode)) return kind === "image" ? localized("人物图像", "Portrait") : localized("驱动音频", "Driving audio");
    if (!isRef2VA(variant)) return counts.image === 1 ? localized("首帧", "First frame") : localized("尾帧", "Last frame");
    return `<${{ image: "Picture", video: "Video", audio: "Audio" }[kind]} ${counts[kind]}>`;
  });
}

function validateReferenceSet(references = state.references, variant = selectedVariant()) {
  if (isMusic3(variant)) return references.length ? localized("Music3 不使用参考素材", "Music3 does not use reference files") : "";
  if (!references.length) return localized("请至少添加一份参考素材", "Add at least one reference file");
  const limits = referenceLimits(variant);
  const counts = { image: 0, video: 0, audio: 0 };
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
  if (!isDigitalHuman()) return;
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
  if (runningHubNode?.workflow_variant) {
    el("modelVariant").value = runningHubNode.workflow_variant;
  }
  if (runningHubNode?.workflow_execution_mode) {
    el("executionMode").value = runningHubNode.workflow_execution_mode;
  }
  el("modelControl").hidden = Boolean(runningHubNode);
  el("executionControl").hidden = Boolean(runningHubNode);
  el("runningHubWorkflowControl").hidden = !runningHubNode;
  el("runningHubWorkflowName").textContent = runningHubNode
    ? `${runningHubNode.workflow_name || runningHubNode.name} · ID ${runningHubNode.workflow_id || "-"}`
    : "";
  const music3 = isMusic3();
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
  const fl2vaOption = el("modelVariant").querySelector('option[value="fl2va-fp8"]');
  fl2vaOption.disabled = nsfw || digitalHuman;
  if (nsfw || digitalHuman) el("modelVariant").value = "ref2va-fp8";
  const ref2va = isRef2VA();
  const accelerated = selectedExecutionMode() === "turbo-lora";
  const stepsMode = el("steps").dataset.mode;
  if (stepsMode !== (music3 ? "music3" : "h3")) {
    el("steps").value = music3 ? "30" : "10";
    el("steps").dataset.mode = music3 ? "music3" : "h3";
  }
  const durationMode = el("duration").dataset.mode;
  if (durationMode !== (music3 ? "music3" : "h3")) {
    const durations = music3 ? MUSIC3_DURATIONS : H3_DURATIONS;
    el("duration").innerHTML = durations.map((seconds) => `<option value="${seconds}">${seconds}s</option>`).join("");
    el("duration").value = music3 ? "60" : "5";
    el("duration").dataset.mode = music3 ? "music3" : "h3";
  }
  el("steps").value = music3 ? "30" : accelerated ? "8" : digitalHuman ? "20" : el("steps").value;
  el("steps").disabled = music3 || accelerated || digitalHuman;
  el("duration").disabled = digitalHuman;
  const durationControl = el("duration").closest(".duration-control");
  durationControl.classList.toggle("digital-human", digitalHuman);
  durationControl.title = state.locale === "en"
    ? digitalHuman ? "Video length follows the driving audio" : music3 ? "Maximum music duration" : "Video duration"
    : digitalHuman ? "视频长度由驱动音频长度决定" : music3 ? "音乐最长时长" : "视频时长";
  el("durationHint").hidden = !digitalHuman;
  referenceInput.accept = music3 ? "" : digitalHuman ? "image/*,audio/*" : ref2va ? "image/*,video/*,audio/*" : "image/*";
  el("addReference").title = state.locale === "en"
    ? digitalHuman ? "Add portrait and driving audio" : ref2va ? "Add image, video, or audio references" : "Add first or last frame"
    : digitalHuman ? "添加人物图片和驱动音频" : ref2va ? "添加图片、视频或音频参考" : "添加首帧或尾帧";
  el("addReference").setAttribute("aria-label", el("addReference").title);
  el("addReference").hidden = music3;
  el("aspectControl").hidden = music3;
  el("resolutionControl").hidden = music3;
  el("lyrics").hidden = !music3;
  el("stepsControl").title = state.locale === "en" ? music3 ? "Music3 uses 30 steps" : "Sampling steps" : music3 ? "Music3 固定使用 30 步" : "采样步数";
  el("optimizePrompt").hidden = false;
  el("optimizePrompt").title = state.locale === "en" ? music3 ? "Optimize style" : "Optimize prompt" : music3 ? "优化曲风" : "优化提示词";
  el("optimizePrompt").setAttribute("aria-label", el("optimizePrompt").title);
  el("optimizePromptLabel").textContent = el("optimizePrompt").title;
  el("writeLyrics").hidden = !music3;
  el("writeLyrics").title = localized("优化歌词", "Optimize lyrics");
  el("writeLyrics").setAttribute("aria-label", el("writeLyrics").title);
  el("writeLyrics").querySelector("span").textContent = el("writeLyrics").title;
  promptInput.placeholder = state.locale === "en"
    ? music3 ? "Describe genre, mood, tempo, key, instruments, vocals, and arrangement..." : "Describe the scene, characters, action, camera, and sound..."
    : music3 ? "描述曲风、情绪、速度、调式、乐器、人声与编曲…" : "输入自然语言，描述场景、人物、动作、镜头与声音…";
  renderReferences();
  const error = validateReferenceSet(state.references);
  showError(state.references.length ? error : "");
}

function addFiles(files) {
  if (state.editingJobId) {
    showError(localized("修改排队任务时不能更换参考素材", "Reference files cannot be changed while editing a queued task"));
    return;
  }
  let error = "";
  Array.from(files).forEach((file) => {
    const kind = kindFor(file);
    if (!kind) {
      error = localized(`不支持的素材类型：${file.name}`, `Unsupported file type: ${file.name}`);
      return;
    }
    const limits = referenceLimits();
    const current = state.references.filter((item) => (item.kind || item.type) === kind).length;
    if (!limits[kind]) {
      error = isDigitalHuman()
        ? localized(`数字人模式仅支持人物图片和驱动音频：${file.name}`, `Digital human mode only accepts a portrait and driving audio: ${file.name}`)
        : localized(`FL2VA 仅支持图片：${file.name}`, `FL2VA only accepts images: ${file.name}`);
      return;
    }
    if (current >= limits[kind]) {
      error = isRef2VA()
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
  showError(error);
  renderReferences();
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
        : `<span class="reference-type">${icon(kind === "video" ? "film" : kind === "audio" ? "audio-lines" : "image")}</span>`;
    const thumb = item.url
      ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer" class="reference-link" aria-label="查看${escapeHtml(name)}">${media}</a>`
      : media;
    return `<div class="reference-chip" title="${escapeHtml(name)}">
      <span class="reference-preview">${thumb}</span>
      <span class="reference-info"><b>${escapeHtml(labels[index])}</b><small>${escapeHtml(name)}${item.size ? ` · ${formatBytes(item.size)}` : ""}</small></span>
      ${item.remote ? "" : `<button type="button" data-remove-reference="${index}" title="移除素材" aria-label="移除素材">${icon("x")}</button>`}
    </div>`;
  }).join("");
  renderMentionMenu();
  refreshIcons();
}

function renderMentionMenu() {
  const references = state.references
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => (item.kind || item.type) === "image");
  const section = el("mentionReferenceSection");
  section.hidden = isMusic3() || !references.length;
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
    const payload = await api(`/api/v1/generations?${params}`);
    state.assets = reset ? payload.data : dedupeJobs([...state.assets, ...payload.data]);
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
  if (job.status === "queued") {
    return `<span class="asset-actions"><button type="button" data-job-action="edit" data-job-id="${job.id}" title="修改" aria-label="修改">${icon("pencil")}</button><button type="button" data-job-action="cancel" data-job-id="${job.id}" title="取消" aria-label="取消">${icon("square")}</button></span>`;
  }
  if (job.status === "running") {
    return `<span class="asset-actions"><button type="button" data-job-action="cancel" data-job-id="${job.id}" title="取消" aria-label="取消">${icon("square")}</button></span>`;
  }
  return `<span class="asset-actions"><button type="button" data-job-action="delete" data-job-id="${job.id}" title="删除" aria-label="删除">${icon("trash-2")}</button></span>`;
}

function renderAssetCard(job) {
  const music3 = job.request?.media_type === "audio";
  const preview = job.status === "completed" && job.result_url
    ? music3
      ? `<span class="asset-audio-icon" aria-hidden="true">${icon("audio-lines")}</span>`
      : `<video src="${job.result_url}" muted playsinline preload="metadata" aria-label="${modelLabel(job)} 生成视频"></video><span class="asset-play">${icon("play")}</span>`
    : `<span class="asset-placeholder ${job.status}">${icon(job.status === "running" ? "loader-circle" : job.status === "queued" ? "clock-3" : job.status === "failed" ? "triangle-alert" : "circle-slash-2")}${job.status === "running" ? `<b>${job.progress || 0}%</b>` : ""}</span>`;
  return `<article class="asset-card" data-asset-job="${job.id}" tabindex="0" aria-label="${executionModeLabel(job)}, ${modelLabel(job)}, ${statusLabel(job.status)}">
    <div class="asset-preview${music3 ? " music" : ""}">${preview}${assetAction(job)}</div>
    <div class="asset-meta"><span class="task-status ${job.status}"></span><strong>${modelLabel(job)}</strong><small class="asset-plan ${executionModeClass(job)}">${executionModeLabel(job)}</small><time>${escapeHtml(nodeLabel(job))}</time><time>${t("overallTime")} ${formatElapsed(job.elapsed_seconds)}</time></div>
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

async function refreshConversation(initial = false) {
  if (state.conversationLoading) {
    state.conversationRefreshPending = true;
    return;
  }
  state.conversationLoading = true;
  try {
    const pageCount = initial ? 1 : Math.max(1, state.conversationPage);
    const requests = Array.from({ length: pageCount }, (_, index) => {
      const params = new URLSearchParams({
        page: String(index + 1),
        page_size: String(state.conversationPageSize),
        scope: jobScope(),
      });
      return api(`/api/v1/generations?${params}`);
    });
    const payloads = await Promise.all(requests);
    const revisions = payloads.map((payload) => payload.store_revision || 0).filter((revision) => revision > 0);
    state.conversationRevision = revisions.length ? Math.min(...revisions) : state.conversationRevision;
    state.storeRevision = Math.max(state.storeRevision, ...revisions, 0);
    state.conversationPages = payloads[0]?.pages || 1;
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
      state.conversationRefreshPending = false;
      queueMicrotask(() => refreshConversation());
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
  if (Boolean(job.request?.incognito) !== state.incognito) return;
  const index = state.conversations.findIndex((item) => item.id === job.id);
  const current = jobElement(el("conversationFeed"), "data-job-id", job.id);
  if (index >= 0) {
    state.conversations[index] = job;
    current?.replaceWith(elementFromHtml(renderJobExchange(job)));
  } else {
    const newestTime = state.conversations[0] ? new Date(state.conversations[0].created_at).getTime() : 0;
    const jobTime = new Date(job.created_at).getTime();
    if (state.conversations.length && jobTime < newestTime) return;
    state.conversations.unshift(job);
    el("conversationFeed").querySelector(".chat-empty")?.remove();
    el("conversationFeed").append(elementFromHtml(renderJobExchange(job)));
    el("conversationFeed").scrollTop = el("conversationFeed").scrollHeight;
  }
  refreshIcons();
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
    const params = new URLSearchParams({
      page: String(nextPage),
      page_size: String(state.conversationPageSize),
      scope: jobScope(),
    });
    const payload = await api(`/api/v1/generations?${params}`);
    state.storeRevision = Math.max(state.storeRevision, payload.store_revision || 0);
    state.conversationPage = nextPage;
    state.conversationPages = payload.pages;
    state.conversations = dedupeJobs([...state.conversations, ...payload.data]);
    renderConversationFeed("prepend");
  } catch (error) {
    showError(error.message);
  } finally {
    state.conversationLoading = false;
  }
}

function referenceSummary(job) {
  const references = job.request?.references || [];
  const labels = referenceLabels(
    references,
    job.request?.model_variant || "fl2va-fp8",
    job.request?.execution_mode || "native",
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
  const buttons = [`<button type="button" data-job-action="reuse" data-job-id="${job.id}">${icon("corner-down-left")}<span>${t("reuse")}</span></button>`];
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
  const music3 = request.media_type === "audio" || request.model_variant === "music3-int8";
  const active = isActive(job);
  const detail = job.error || (job.queue_position ? `${t("queuePosition")} ${job.queue_position}` : job.stage);
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
  } else if (job.status === "completed") {
    assistantBody = music3
      ? `<p class="terminal-state completed">${t("musicReady")}</p><div class="audio-result"><audio controls preload="metadata" src="${job.result_url}"></audio><a href="${job.result_url}" download>${icon("download")}<span>${t("downloadAudio")}</span></a></div>`
      : `<p class="terminal-state completed">${t("videoReady")}</p><div class="video-result"><video controls playsinline preload="metadata" src="${job.result_url}"></video><a href="${job.result_url}" download>${icon("download")}<span>${t("downloadVideo")}</span></a></div>`;
  } else {
    assistantBody = `<p class="terminal-state ${job.status}">${escapeHtml(detail || statusLabel(job.status))}</p>`;
  }
  return `<section class="exchange" id="job-${job.id}" data-job-id="${job.id}">
    <article class="message user-message">
      <div class="message-avatar user-avatar">${t("you")}</div>
      <div class="message-body">${referenceSummary(job)}<div class="message-text">${escapeHtml(request.prompt || "")}${music3 && request.lyrics ? `\n\n${escapeHtml(request.lyrics)}` : ""}</div><div class="message-meta">${executionMode}<span>${modelLabel(job)}</span><span>${escapeHtml(nodeLabel(job))}</span>${music3 ? "" : `<span>${request.width} × ${request.height}</span>`}<span>${request.duration}${t("seconds")}</span><span>${request.steps} ${t("steps")}</span><span>${t("seed")} ${request.seed}</span>${elapsed}${incognito}</div></div>
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

function renderAssetDetail(job) {
  const request = job.request || {};
  const music3 = request.media_type === "audio" || request.model_variant === "music3-int8";
  const download = el("downloadAssetDetail");
  const downloadable = job.status === "completed" && Boolean(job.result_url);
  const references = request.references || [];
  const preview = job.status === "completed" && job.result_url
    ? music3
      ? `<audio controls preload="metadata" src="${escapeHtml(job.result_url)}"></audio>`
      : `<video controls playsinline preload="metadata" src="${escapeHtml(job.result_url)}"></video>`
    : `<div class="asset-detail-placeholder">${icon(job.status === "running" ? "loader-circle" : "file-x-2")}<span>${t("outputUnavailable")}</span></div>`;
  const files = references.length
    ? `<div class="asset-detail-files">${references.map((item, index) => assetDetailFile(item, index, job)).join("")}</div>`
    : `<p class="quiet">${t("noSourceFiles")}</p>`;
  const facts = [
    executionModeLabel(job), modelLabel(job), nodeLabel(job),
    music3 ? null : `${request.width} × ${request.height}`,
    `${request.duration}${t("seconds")}`, `${request.steps} ${t("steps")}`,
    `${t("seed")} ${request.seed}`, `${t("overallTime")} ${formatElapsed(job.elapsed_seconds)}`,
  ].filter(Boolean).map((value) => `<span>${escapeHtml(value)}</span>`).join("");
  el("assetDetailTitle").textContent = shortTitle(job);
  el("assetDetailMeta").textContent = `${statusLabel(job.status)} · ${formatTime(job.created_at, true)} · ${job.id}`;
  el("assetDetailBody").innerHTML = `<div class="asset-detail-preview">${preview}</div><div class="asset-detail-info">
    <section class="asset-detail-section"><h3>${t("prompt")}</h3><pre>${escapeHtml(request.prompt || "")}</pre></section>
    ${request.lyrics ? `<section class="asset-detail-section"><h3>${t("lyrics")}</h3><pre>${escapeHtml(request.lyrics)}</pre></section>` : ""}
    <section class="asset-detail-section"><h3>${t("sourceFiles")}</h3>${files}</section>
    <section class="asset-detail-section"><h3>${t("parameters")}</h3><div class="asset-detail-facts">${facts}</div></section>
  </div>`;
  el("deleteAssetDetail").disabled = isActive(job);
  download.hidden = !downloadable;
  download.href = downloadable ? job.result_url : "#";
  download.download = music3 ? `${job.id}.flac` : `${job.id}.mp4`;
  download.querySelector("span").textContent = music3 ? t("downloadAudio") : t("downloadVideo");
  el("regenerateAssetDetail").disabled = isActive(job);
  el("reuseAssetDetail").disabled = false;
  refreshIcons();
}

async function openAssetDetail(jobId) {
  el("assetDetailModal").hidden = false;
  document.body.classList.add("modal-open");
  el("assetDetailError").textContent = "";
  el("downloadAssetDetail").hidden = true;
  el("downloadAssetDetail").href = "#";
  el("regenerateAssetDetail").disabled = true;
  el("assetDetailBody").innerHTML = `<div class="feed-loading"><span></span><span></span><span></span></div>`;
  refreshIcons();
  try {
    const job = await api(`/api/v1/generations/${encodeURIComponent(jobId)}`);
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
  if (el("nodeModal").hidden) document.body.classList.remove("modal-open");
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
      restored.push({ file, kind: item.type, name: file.name, size: file.size, url: URL.createObjectURL(file) });
    }
    return restored;
  } catch (error) {
    restored.forEach((item) => URL.revokeObjectURL(item.url));
    throw error;
  }
}

async function backfillJob(jobId) {
  const detailOpen = !el("assetDetailModal").hidden;
  const reuseButton = el("reuseAssetDetail");
  if (detailOpen) el("assetDetailError").textContent = t("fillLoading");
  reuseButton.disabled = true;
  try {
    const job = state.assetDetailJob?.id === jobId ? state.assetDetailJob : await api(`/api/v1/generations/${encodeURIComponent(jobId)}`);
    const references = await restoredReferences(job);
    resetComposer();
    promptInput.value = job.request?.prompt || "";
    el("lyrics").value = job.request?.lyrics || "";
    el("modelVariant").value = job.request?.model_variant || "fl2va-fp8";
    el("executionMode").value = job.request?.execution_mode || "native";
    const requestedNode = job.request?.comfy_node || "auto";
    el("comfyNode").value = Array.from(el("comfyNode").options).some((option) => option.value === requestedNode) ? requestedNode : "auto";
    updateModelUi();
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
    el("comfyNode").value = job.request.comfy_node || "auto";
    el("seed").value = String(job.request.seed);
    setDimensions(job.request.width, job.request.height);
    state.references = (job.request.references || []).map((item) => ({ ...item, kind: item.type, remote: true }));
    updateModelUi();
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
  if (action === "regenerate") return regenerateJob(jobId);
  if (action === "edit") return startEdit(jobId);
  if (action === "cancel") return cancelJob(jobId);
  if (action === "delete") return deleteJob(jobId);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  const prompt = promptInput.value.trim();
  const minimumPromptLength = isMusic3() ? 2 : 8;
  if (prompt.length < minimumPromptLength) return showError(localized(`请填写至少 ${minimumPromptLength} 个字符的提示词`, `Enter a prompt with at least ${minimumPromptLength} characters`));
  const steps = isMusic3() ? 30 : selectedExecutionMode() === "turbo-lora" ? 8 : isDigitalHuman() ? 20 : Number(el("steps").value);
  if (!Number.isInteger(steps) || steps < 4 || steps > 50) return showError(localized("采样步数请输入 4–50 的整数", "Sampling steps must be an integer from 4 to 50"));
  const [width, height] = getDimensions();
  const button = el("generateButton");
  button.disabled = true;
  try {
    const runningHubNode = selectedRunningHubNode();
    let payload;
    if (state.editingJobId) {
      const requestBody = {
        prompt,
        lyrics: isMusic3() ? el("lyrics").value.trim() : "",
        width,
        height,
        duration: Number(el("duration").value),
        steps,
        seed: el("seed").value === "" ? undefined : Number(el("seed").value),
        comfy_node: el("comfyNode").value,
      };
      if (!runningHubNode) {
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
      if (!runningHubNode) {
        data.append("model_variant", selectedVariant());
        data.append("execution_mode", selectedExecutionMode());
      }
      data.append("comfy_node", el("comfyNode").value);
      data.append("incognito", state.incognito ? "true" : "false");
      data.append("reference_manifest", JSON.stringify(state.references.map((item) => ({ type: item.kind }))));
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
    return `<div class="log-row ${item.level === "error" ? "error" : ""}">
      <time>${formatTime(item.timestamp)}</time>
      ${jobLink}
      <p>${escapeHtml(item.message)}${progress}</p>
    </div>`;
  }).join("") : `<p class="quiet">${state.locale === "en" ? "Waiting for events" : "等待事件"}</p>`;
  container.scrollTop = container.scrollHeight;
}

function connectEventStream() {
  state.stream?.close();
  const initialRevisions = [state.assetRevision, state.conversationRevision].filter((revision) => revision > 0);
  const since = initialRevisions.length ? Math.min(...initialRevisions) : 0;
  state.stream = new EventSource(`/api/v1/events?since=${encodeURIComponent(since)}`);
  state.stream.addEventListener("snapshot", async (event) => {
    const payload = JSON.parse(event.data);
    const nodes = payload.nodes || state.nodes;
    renderHealthState(nodes, (payload.queue || []).filter((job) => job.status === "queued").length);
    syncManagedNodeStatuses(nodes);
    renderQueue(payload.queue || []);
    renderLogs(payload.logs || []);
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

function loadAiConfig() {
  el("aiEnabled").checked = localStorage.getItem("h3-ai-enabled") === "1";
  el("aiBaseUrl").value = localStorage.getItem("h3-ai-base-url") || "";
  el("aiModel").value = localStorage.getItem("h3-ai-model") || "";
  el("aiApiKey").value = sessionStorage.getItem("h3-ai-api-key") || "";
}

function saveAiConfig() {
  localStorage.setItem("h3-ai-enabled", el("aiEnabled").checked ? "1" : "0");
  localStorage.setItem("h3-ai-base-url", el("aiBaseUrl").value.trim());
  localStorage.setItem("h3-ai-model", el("aiModel").value.trim());
  sessionStorage.setItem("h3-ai-api-key", el("aiApiKey").value);
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
  saveAiConfig();
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
        api_key: el("aiApiKey").value,
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
  saveAiConfig();
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
        api_key: el("aiApiKey").value,
        model,
        duration: Number(el("duration").value),
        model_variant: selectedVariant(),
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
  state.opsPosition.x = Math.max(8, Math.round((window.innerWidth - rect.width) / 2));
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
  resetOpsPosition();
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

el("referenceList").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-remove-reference]");
  if (!button) return;
  const index = Number(button.dataset.removeReference);
  const [removed] = state.references.splice(index, 1);
  if (removed?.url) URL.revokeObjectURL(removed.url);
  renderReferences();
});

el("addReference").addEventListener("click", () => referenceInput.click());
referenceInput.addEventListener("change", () => {
  addFiles(referenceInput.files);
  referenceInput.value = "";
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
composerBox.addEventListener("drop", (event) => addFiles(event.dataTransfer.files));

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
  const action = event.target.closest("[data-job-action]");
  if (action) {
    event.stopPropagation();
    handleJobAction(action.dataset.jobAction, action.dataset.jobId);
    return;
  }
  const card = event.target.closest("[data-asset-job]");
  if (card) openAssetDetail(card.dataset.assetJob);
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

["aiEnabled", "aiBaseUrl", "aiModel", "aiApiKey"].forEach((id) => el(id).addEventListener("change", saveAiConfig));
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
el("saveNodeSettings").addEventListener("click", saveNodeSettings);
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
  if (event.key === "Escape" && !el("secretOverlay").hidden) closeSecretDialog();
  if (event.key === "Escape" && !el("nodeModal").hidden) closeNodeManager();
  if (event.key === "Escape" && !el("assetDetailModal").hidden) closeAssetDetail();
});

el("clearVisibleLogs").addEventListener("click", () => {
  state.logFloor = Date.now();
  renderLogs(state.logs);
});
el("opsLauncher").addEventListener("click", openOpsWindow);
el("closeOps").addEventListener("click", closeOpsWindow);
el("openAssets").addEventListener("click", openAssetDrawer);
el("closeAssets").addEventListener("click", closeAssetDrawer);
el("mobileScrim").addEventListener("click", closeAssetDrawer);

let dragState = null;
el("opsDragHandle").addEventListener("pointerdown", (event) => {
  if (event.target.closest("button")) return;
  dragState = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: state.opsPosition.x,
    originY: state.opsPosition.y,
  };
  el("opsDragHandle").setPointerCapture(event.pointerId);
  el("opsWindow").classList.add("dragging");
});
el("opsDragHandle").addEventListener("pointermove", (event) => {
  if (!dragState || dragState.pointerId !== event.pointerId) return;
  state.opsPosition.x = dragState.originX + event.clientX - dragState.startX;
  state.opsPosition.y = dragState.originY + event.clientY - dragState.startY;
  applyOpsPosition();
});
function stopOpsDrag(event) {
  if (!dragState || dragState.pointerId !== event.pointerId) return;
  dragState = null;
  el("opsWindow").classList.remove("dragging");
}
el("opsDragHandle").addEventListener("pointerup", stopOpsDrag);
el("opsDragHandle").addEventListener("pointercancel", stopOpsDrag);
window.addEventListener("resize", () => { if (!el("opsWindow").hidden) applyOpsPosition(); });

async function initialize() {
  applyStaticLocale();
  loadAiConfig();
  updateModelUi();
  updateIncognitoUi();
  renderReferences();
  await Promise.all([checkHealth(), loadAssets({ reset: true }), refreshConversation(true)]);
  connectEventStream();
  refreshIcons();
}

initialize();
window.addEventListener("load", refreshIcons);
window.addEventListener("beforeunload", () => state.stream?.close());
