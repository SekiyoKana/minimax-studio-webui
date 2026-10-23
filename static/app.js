const state = {
  references: [],
  assets: [],
  assetFolders: [],
  assetUnfiledFolder: { id: "__unfiled__", name: "未分组", count: 0 },
  assetFolderId: "",
  assetEditMode: false,
  assetSelectedIds: new Set(),
  assetFolderNameEditId: null,
  assetFolderPickerResolve: null,
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
  assetDetailWindows: new Map(),
  assetDetailWindowOrder: [],
  assetDetailActiveWindowId: null,
  assetDetailDrag: null,
  messageStyle: "default",
  optimizeMarkdown: true,
  localAssets: [],
  localAssetPage: 0,
  localAssetPages: 1,
  localAssetTotal: 0,
  localAssetSize: 0,
  localAssetLibrarySize: 0,
  localAssetFolderId: "__root__",
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
  workflows: [],
  workflowEditingId: null,
  workflowDraftJson: null,
  workflowEditorReturnFocus: null,
  referenceProcessing: false,
  nodeEditingId: null,
  bindLocalComfyui: false,
  localComfyTimer: null,
  runningHubSchemaKey: "",
  runningHubRenderSignature: "",
  runningHubResourceId: "",
  runningHubParameters: {},
  pendingRunningHubMediaField: "",
  logs: [],
  logFollowTail: true,
  runtimeRevision: "",
  localRuntime: { logs: [], queue: [], nodes: [] },
  peerRuntime: {},
  generalSettings: { show_runtime_logs: true, show_peering: true, backup_outputs: false, auto_compress_large_images: true, remote_disconnect_policy: "encrypt" },
  conversationDevices: [],
  stream: null,
  incognito: false,
  incognitoCode: "",
  brandClicks: [],
  opsPosition: { x: 0, y: 0 },
  opsPositionInitialized: false,
  mentionIndex: -1,
  locale: localStorage.getItem("h3-locale") === "en" ? "en" : "zh-CN",
};

const el = (id) => document.getElementById(id);
const form = el("generationForm");
const promptInput = el("prompt");
const referenceInput = el("referenceInput");
const MUSIC3_DURATIONS = [30, 60, 120, 180, 240, 300];
const RUNNINGHUB_TARGET_PREFIX = "rh:";
const SIDEBAR_WIDTH_STORAGE_KEY = "h3-asset-sidebar-width";
const SIDEBAR_WIDTH_MIN = 260;
const SIDEBAR_WIDTH_MAX_RATIO = 0.5;
const ANDROID_CLIENT = new URLSearchParams(window.location.search).get("h3_client") === "android";

const COPY = {
  "zh-CN": {
    assetLibrary: "素材库", assetSearch: "搜索素材", allStatuses: "全部状态", queued: "排队中", running: "生成中", completed: "已完成", failed: "失败", cancelled: "已取消",
    conversation: "对话消息", switchLanguage: "Switch to English", apiDocs: "API 文档", newGeneration: "新建生成", close: "关闭", assets: "素材库",
    connectEngine: "连接推理节点", offline: "服务离线", autoSchedule: "自动调度", nodePending: "节点待分配", online: "在线", available: "可用", nodeOffline: "离线", disabled: "已停用", busy: "执行中",
    balance: "余额", credits: "点数", recentCost: "最近调用消耗", accountUnavailable: "账户信息不可用", workflowUnavailable: "工作流信息不可用", balancePending: "余额读取中", accountTasks: "账户任务", balanceUpdated: "余额更新", balanceFailed: "余额读取失败",
    noAssets: "暂无素材", loading: "加载中", allLoaded: "已加载全部", loadFailed: "加载失败", startCreating: "开始创作", you: "你", allAssets: "全部素材", unfiled: "未分组", folders: "文件夹", editAssets: "编辑素材", exitAssetEdit: "退出编辑", selectedAssets: "已选择", newFolder: "新建文件夹", renameFolder: "重命名文件夹", deleteFolder: "删除文件夹", moveTo: "移动到", noSelection: "未选择素材", folderName: "文件夹名称", folderPurpose: "用于归类短剧生成任务", folderDeleteConfirm: "删除文件夹后，其中的任务记录、参考文件和生成产物都会被删除。确认继续？", activeFolderDelete: "文件夹包含进行中任务，请先取消或等待任务结束", regenerateFolder: "选择重新生成任务的文件夹",
    native: "普通流 · 原生 H3", turbo: "8-step LoRA · 强度 1.0", turbo4: "4-step LoRA", dualSampling: "双采 · Sigma + 潜空间放大", h3Sa: "MiniMax H3 SA · Sol-Attn", vdnH3: "VDN-H3 · Video Delta Net", digitalHuman: "数字人 · 音频驱动", tts: "H3 TTS · 人物语音", videoUpscale: "视频超分", upscale2x: "2x 超分", upscale4x: "4x 超分", music3: "Music3 · 30 步", nsfw: "H3 NSFW · NaughtyTimes LoRA", speedCache: "Speed Cache（已停用）",
    reuse: "回填到发送区", useAsInput: "作为输入", regenerate: "重新生成", edit: "修改", cancel: "取消", delete: "删除", deleteRecord: "删除记录", downloadVideo: "下载视频", downloadAudio: "下载音频", downloadImage: "下载图片", downloadFile: "下载文件", videoReady: "视频已生成", musicReady: "音频已生成", imageReady: "图片已生成", fileReady: "文件已生成", peering: "多端互联", peerConnected: "已连接设备", peerRevoked: "已撤销设备访问", peerConnectNotice: "设备已完成互联", localPeerKey: "本机互联密钥",
    aiKeySaved: "API Key 已保存到本机数据库", aiKeyEmpty: "尚未保存 API Key", aiKeyReplace: "输入新值可覆盖已保存密钥", noPeers: "暂无已连接设备", revokeAccess: "撤销访问", owner: "归属方", pairingRefresh: "秒后刷新", connectPeer: "建立互联",
    assetDetail: "素材详情", prompt: "关键词与提示词", lyrics: "歌词", sourceFiles: "使用的文件", parameters: "生成参数", noSourceFiles: "未使用参考文件", outputUnavailable: "当前没有可预览的生成产物", assetDeleted: "该资产已删除", deviceFilter: "设备筛选",
    deleteConfirm: "删除后将同时清理任务记录、上传素材和生成产物，确认继续？", regenerateConfirm: "将使用本条任务的参数和参考文件创建新的生成任务，确认继续？", fillLoading: "正在读取原始文件", fillDone: "已回填到发送区", fileUnavailable: "参考文件已不存在，无法完整回填",
    overallTime: "总体耗时", steps: "步", seed: "seed", seconds: "秒", queuePosition: "队列位置", incognito: "无痕", destroy: "销毁",
  },
  en: {
    assetLibrary: "Assets", assetSearch: "Search assets", allStatuses: "All statuses", queued: "Queued", running: "Running", completed: "Completed", failed: "Failed", cancelled: "Cancelled",
    conversation: "Messages", switchLanguage: "Switch to Chinese", apiDocs: "API documentation", newGeneration: "New generation", close: "Close", assets: "Assets",
    connectEngine: "Connecting to inference nodes", offline: "Service offline", autoSchedule: "Auto", nodePending: "Awaiting node", online: "Online", available: "available", nodeOffline: "Offline", disabled: "Disabled", busy: "Running",
    balance: "Balance", credits: "credits", recentCost: "Recent call cost", accountUnavailable: "Account unavailable", workflowUnavailable: "Workflow information unavailable", balancePending: "Loading balance", accountTasks: "Account tasks", balanceUpdated: "balance updated", balanceFailed: "balance read failed",
    noAssets: "No assets", loading: "Loading", allLoaded: "All assets loaded", loadFailed: "Load failed", startCreating: "Start creating", you: "You", allAssets: "All assets", unfiled: "Unfiled", folders: "Folders", editAssets: "Edit assets", exitAssetEdit: "Exit editing", selectedAssets: "Selected", newFolder: "New folder", renameFolder: "Rename folder", deleteFolder: "Delete folder", moveTo: "Move to", noSelection: "No assets selected", folderName: "Folder name", folderPurpose: "Organize short-drama generation tasks", folderDeleteConfirm: "Deleting this folder also deletes its task records, source files, and generated outputs. Continue?", activeFolderDelete: "This folder contains active tasks. Cancel or wait for them first.", regenerateFolder: "Choose a folder for the regenerated task",
    native: "Native H3", turbo: "8-step LoRA · 1.0", turbo4: "4-step LoRA", dualSampling: "Dual sampling · Sigma + latent upscale", h3Sa: "MiniMax H3 SA · Sol-Attn", vdnH3: "VDN-H3 · Video Delta Net", digitalHuman: "Digital human · audio driven", tts: "H3 TTS · Character voice", videoUpscale: "Video super-resolution", upscale2x: "2x super-resolution", upscale4x: "4x super-resolution", music3: "Music3 · 30 steps", nsfw: "H3 NSFW · NaughtyTimes LoRA", speedCache: "Speed Cache (disabled)",
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
  target.dataset.tip = value;
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

const HEADER_TIP_DELAY = 2000;
let headerTipBubble = null;

function syncHeaderTips() {
  document.querySelectorAll(".header-actions > .icon-button").forEach((target) => {
    const label = (target.dataset.tip || target.getAttribute("aria-label") || target.getAttribute("title") || "").trim();
    if (label) target.dataset.tip = label;
    if (target.hasAttribute("title")) target.removeAttribute("title");
  });
}

function initHeaderTooltips() {
  const bar = document.querySelector(".header-actions");
  if (!bar || headerTipBubble) return;
  const bubble = document.createElement("div");
  bubble.className = "header-tip";
  bubble.setAttribute("role", "tooltip");
  document.body.appendChild(bubble);
  headerTipBubble = bubble;
  let timer = 0;
  let active = null;

  const hideTip = () => {
    window.clearTimeout(timer);
    timer = 0;
    active = null;
    bubble.classList.remove("show");
  };
  const showTip = () => {
    if (!active || !active.isConnected) return hideTip();
    const label = (active.dataset.tip || "").trim();
    if (!label) return hideTip();
    bubble.textContent = label;
    bubble.classList.add("show");
    const rect = active.getBoundingClientRect();
    const width = bubble.offsetWidth;
    const left = rect.left + rect.width / 2 - width / 2;
    const clamped = Math.min(Math.max(8, left), Math.max(8, window.innerWidth - width - 8));
    bubble.style.left = `${Math.round(clamped)}px`;
    bubble.style.top = `${Math.round(rect.bottom + 10)}px`;
  };
  const targetFrom = (node) => (node instanceof Element ? node.closest(".header-actions > .icon-button") : null);

  bar.addEventListener("pointerover", (event) => {
    const target = targetFrom(event.target);
    if (!target || target.hidden || target === active) return;
    hideTip();
    active = target;
    timer = window.setTimeout(showTip, HEADER_TIP_DELAY);
  });
  bar.addEventListener("pointerout", (event) => {
    const target = targetFrom(event.target);
    if (!target || target !== active) return;
    const next = event.relatedTarget;
    if (next instanceof Node && target.contains(next)) return;
    hideTip();
  });
  bar.addEventListener("focusin", (event) => {
    const target = targetFrom(event.target);
    if (!target || target.hidden) return;
    active = target;
    window.clearTimeout(timer);
    showTip();
  });
  bar.addEventListener("focusout", hideTip);
  document.addEventListener("pointerdown", hideTip, true);
  window.addEventListener("scroll", hideTip, true);
  window.addEventListener("resize", hideTip);
}

const THEMES = [
  { id: "light", name: "日间", nameEn: "Light", note: "浅色外观", noteEn: "Light appearance" },
  { id: "dark", name: "夜间", nameEn: "Dark", note: "深色外观", noteEn: "Dark appearance" },
  { id: "system", name: "跟随系统", nameEn: "System", note: "随系统自动切换", noteEn: "Match system appearance" },
];
const THEME_STORAGE_KEY = "h3-theme";
const LEGACY_SKIN_STORAGE_KEY = "h3-skin";
const SKIN_THEME_COLORS = { default: "#f5f5f7", aurora: "#070b12" };
const DARK_SCHEME_QUERY = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

function normalizeTheme(id) {
  return THEMES.some((theme) => theme.id === id) ? id : "system";
}

function storedTheme() {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    if (value) return value;
    const legacy = localStorage.getItem(LEGACY_SKIN_STORAGE_KEY);
    if (legacy === "aurora") return "dark";
    if (legacy === "default") return "light";
  } catch (error) { /* storage disabled */ }
  return "";
}

function currentTheme() {
  return normalizeTheme(document.documentElement.dataset.theme || storedTheme() || "system");
}

function systemPrefersDark() {
  return Boolean(DARK_SCHEME_QUERY && DARK_SCHEME_QUERY.matches);
}

function resolveThemeSkin(mode) {
  const theme = normalizeTheme(mode);
  if (theme === "light") return "default";
  if (theme === "dark") return "aurora";
  return systemPrefersDark() ? "aurora" : "default";
}

function applyTheme(mode, { persist = true } = {}) {
  const theme = normalizeTheme(mode);
  const skin = resolveThemeSkin(theme);
  if (skin === "default") delete document.documentElement.dataset.skin;
  else document.documentElement.dataset.skin = skin;
  document.documentElement.dataset.theme = theme;
  if (persist) {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
      localStorage.removeItem(LEGACY_SKIN_STORAGE_KEY);
    } catch (error) { /* storage disabled */ }
  }
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.content = SKIN_THEME_COLORS[skin] || SKIN_THEME_COLORS.default;
  document.dispatchEvent(new CustomEvent("h3:themechange", { detail: { theme, skin, systemDark: systemPrefersDark() } }));
  document.dispatchEvent(new CustomEvent("h3:skinchange", { detail: { skin, theme } }));
  renderThemeOptions();
  return theme;
}

function applySkin(id, options) {
  const mode = id === "aurora" ? "dark" : id === "default" ? "light" : "system";
  return applyTheme(mode, options);
}

function currentSkin() {
  return resolveThemeSkin(currentTheme());
}

function renderThemeOptions() {
  const active = currentTheme();
  document.querySelectorAll("[data-theme-option]").forEach((card) => {
    const theme = THEMES.find((item) => item.id === card.dataset.themeOption);
    if (!theme) return;
    const isActive = theme.id === active;
    card.classList.toggle("is-active", isActive);
    card.setAttribute("aria-checked", String(isActive));
    card.tabIndex = isActive ? 0 : -1;
    const name = card.querySelector(".skin-card-copy strong");
    const note = card.querySelector(".skin-card-copy small");
    if (name) name.textContent = localized(theme.name, theme.nameEn);
    if (note) note.textContent = localized(theme.note, theme.noteEn);
  });
  const help = el("skinHelp");
  if (help) {
    help.textContent = localized(
      "显示设置只改变界面样式，不影响生成、队列、数据与接口。跟随系统时会随系统深浅色自动切换。",
      "Display settings only change the interface; generation, queue, data and APIs are unaffected. System mode follows your OS light/dark setting."
    );
  }
  setText("#markdownOptimizeRow span:first-child", localized("在对话流中优化 Markdown 显示", "Optimize Markdown in the conversation"));
  setText("#markdownOptimizeHelp", localized("关闭后提示词按原始纯文本显示，不再解析标题、列表、代码块和链接等 Markdown 语法。", "When disabled, prompts are shown as raw plain text without parsing headings, lists, code blocks or links."));
  setText("#themeTitle", localized("界面主题", "Theme"));
  setText("#messageStyleTitle", localized("对话消息样式", "Conversation style"));
  setText("#messageStyleHelp", localized("选择对话流的展示方式。默认保留完整预览，极简压缩为横幅，宫格使用瀑布流封面。", "Choose how the conversation feed is displayed. Default keeps full previews, minimal uses compact banners, and grid uses a masonry cover layout."));
  document.querySelectorAll("[data-message-style]").forEach((button) => {
    const style = MESSAGE_STYLES.find((item) => item.id === button.dataset.messageStyle);
    if (!style) return;
    button.querySelector("strong").textContent = localized(style.name, style.nameEn);
    button.querySelector("small").textContent = localized(style.note, style.noteEn);
  });
  renderMessageStyleOptions();
}

function watchSystemTheme() {
  if (!DARK_SCHEME_QUERY) return;
  const handler = () => {
    if (currentTheme() === "system") applyTheme("system", { persist: false });
  };
  if (DARK_SCHEME_QUERY.addEventListener) DARK_SCHEME_QUERY.addEventListener("change", handler);
  else if (DARK_SCHEME_QUERY.addListener) DARK_SCHEME_QUERY.addListener(handler);
}

function applyStaticLocale() {
  document.documentElement.lang = state.locale;
  setText(".library-heading h2", t("assetLibrary"));
  setText(".asset-folders-header > span", t("folders"));
  el("assetSearch").placeholder = t("assetSearch");
  setText('#assetStatusFilter option[value=""]', t("allStatuses"));
  ["queued", "running", "completed", "failed", "cancelled"].forEach((status) => setText(`#assetStatusFilter option[value="${status}"]`, t(status)));
  setText(".conversation-header h1", t("conversation"));
  setTitle("#editAssetsButton", state.assetEditMode ? t("exitAssetEdit") : t("editAssets"));
  setTitle("#newAssetFolder", t("newFolder"));
  setTitle("#openAssets", t("assets"));
  setTitle("#languageToggle", t("switchLanguage"));
  setTitle("#openPeering", t("peering"));
  setTitle("#openNodeManager", localized("管理推理节点", "Manage inference nodes"));
  setTitle("#openWorkflowManager", localized("管理工作流", "Manage workflows"));
  setTitle("#openGlobalSettings", localized("设置", "Settings"));
  setTitle("#androidServerSettings", localized("服务器连接", "Server connection"));
    setTitle("#closeAssetDetail", t("close"));
  setText("#deleteAssetDetail span", t("deleteRecord"));
  setText("#reuseOutputAssetDetail span", t("useAsInput"));
  setText("#regenerateAssetDetail span", t("regenerate"));
  setText("#reuseAssetDetail span", t("reuse"));
  setText("#assetFolderNameTitle", state.assetFolderNameEditId ? t("renameFolder") : t("newFolder"));
  setText("#assetFolderNameHint", t("folderPurpose"));
  setLeadingText(".asset-folder-name-field", t("folderName"));
  setText("#moveSelectedAssets span", t("moveTo"));
  el("apiDocsLink").title = t("apiDocs");
  el("apiDocsLink").setAttribute("aria-label", t("apiDocs"));
  el("apiDocsLink").dataset.tip = t("apiDocs");
  syncNodeProviderFields();
  renderThemeOptions();
  if (state.locale !== "en") return;
  setText(".skip-link", "Skip to chat");
  setText(".edit-banner span", "Editing queued task");
  setText("#exitEdit", "Stop editing");
  setText("#durationHint", "Video length follows the driving audio");
  setText("#mentionQuickLabel", "Quick actions");
  setText("#mentionReferenceLabel", "Images");
  setText("#optimizePromptLabel", "Optimize prompt");
  setText("#writeLyrics span", "Optimize lyrics");
  setText(".ops-header h2", "Runtime status");
  setText("#activeTaskSummary", "No active tasks");
  setText(".queue-section .ops-section-title span", "Running and queued");
  setText(".queue-section .quiet", "Queue empty");
  setText(".log-section .ops-section-title span", "Live logs");
  setText("#clearVisibleLogs", "Clear");
  setText(".log-section .quiet", "Waiting for events");
  setText("#nodeDialogTitle", "Inference nodes");
  setText("#nodeDialogSubtitle", "ComfyUI and RunningHub node configuration");
  setText("#nodeEditorSubtitle", "Configure a ComfyUI or RunningHub endpoint");
  setText("#globalSettingsTitle", "Settings");
  setText("#globalSettingsSubtitle", "Model, appearance, system, and upload preferences");
  setText("#settingsTabModel", "Model");
  setText("#settingsTabAppearance", "Display");
  setText("#settingsTabSystem", "System");
  setText("#settingsTabUpload", "Upload");
  setText("#settingsTabExperimental", "Experimental");
  setText("#bindLocalComfyuiHelp", "When enabled, ComfyUI nodes on this machine show a Manageable badge; fill in a launch path in the node editor to start and stop that ComfyUI from the inference node panel.");
  setText("#localComfyCommandLabel", "ComfyUI launch command");
  setText("#localComfyCommandHelp", "Placeholders: {python}, {script}, {workdir}, {host}, {port}. The default mirrors the current ComfyUI launch.");
  setText("#bindLocalComfyuiEnvHelp", "Launching prefers the node directory's private environment (venv, .venv, env) and falls back to the global Python environment. Failures are logged with the original error in Live logs.");
  setText("#videoUpscaleTitle", "Video upscale");
  setText("#videoUpscaleSubtitle", "Choose the upscale type and scale. This runs an independent upscale workflow without changing your current selection.");
  setLeadingText("#videoUpscaleCategoryField", "Upscale type");
  setLeadingText("#videoUpscaleScaleField", "Upscale scale");
  setText("#cancelVideoUpscale", "Cancel");
  setText("#submitVideoUpscale span", "Start upscale");
  document.querySelector(".settings-tabs")?.setAttribute("aria-label", "Settings categories");
  setText("#settingsPanelUpload .switch-row > span:first-child", "Compress large reference images");
  setText("#settingsUploadHelp", "Images over 1 MB are compressed locally before upload.");
  setLeadingText("#globalHealthInterval", "Node health check interval (seconds)");
  setText("#settingsPanelSystem label:nth-child(2) > span:first-child", "Show runtime logs");
  setText("#settingsPanelSystem label:nth-child(3) > span:first-child", "Show device sharing entry");
  setText("#settingsPanelSystem label:nth-child(4) > span:first-child", "Back up generated outputs locally");
  setText("#settingsPanelSystem label:nth-child(5) > span:first-child", "Enable RunningHub endpoint workflows");
  setText("#settingsPanelSystem label:nth-child(7) > span:first-child", "Exclude RunningHub nodes from auto scheduling");
  setText("#runninghubHelp", "When disabled, RunningHub nodes cannot be added or edited; existing nodes are kept.");
  setText("#excludeRunningHubHelp", "When enabled, jobs using auto scheduling never run on RunningHub API nodes; select a RunningHub node manually instead.");
  setLeadingText("#remoteDisconnectPolicy", "Handle remote records when disconnected");
  setLeadingText("#settingsPanelSystem label:nth-of-type(8)", "Remote records key");
  setTitle("#manageLocalAssets", "Manage local assets");
  setText("#globalSettingsForm .settings-form-actions button span", "Save settings");
  setText("#settingsPanelUpload .settings-help", "Images over 1 MB are compressed locally before upload.");
  setLeadingText("#globalSeedControl", "Random seed");
  setText("#autoUpscaleControl > span:first-child", "Upscale after generation");
  setText("#workflowDialogTitle", "Workflows");
  setText("#workflowModal .node-dialog-header p", "ComfyUI API format · built-in presets and custom workflows");
  setText("#addWorkflowButton span", "Add workflow");
  setText("#workflowEditorModal .workflow-editor-header p", "Configure the API graph, field mappings, and target nodes");
  setText("#workflowEditorTitle", state.workflowEditingId ? "Edit workflow" : "Add workflow");
  setText('label[for="workflowName"]', "Workflow name");
  setText('label[for="workflowDescription"]', "Workflow description (optional)");
  el("workflowDescription").placeholder = "Displayed as entered";
  setText('label[for="workflowJsonFile"]', "API workflow JSON");
  setText(".workflow-config-section:first-of-type h4", "Common field mappings");
  setText(".workflow-config-section:nth-of-type(2) h4", "Reference mappings");
  setText("#workflowReferenceHint", "Slot mappings create a loader for every file. Official limits apply: 9 images, 3 videos, and 3 audio clips.");
  setText('label[for="workflowStaticInputs"]', "Static inputs JSON");
  setText('label[for="workflowResultNode"]', "Result node");
  setText('label[for="workflowMediaType"]', "Media type");
  setText("#workflowMediaType option[value=video]", "Video");
  setText("#workflowMediaType option[value=audio]", "Audio");
  setText("#workflowMediaType option[value=image]", "Image");
  setText(".workflow-targets legend", "Target ComfyUI nodes");
  setText(".workflow-visible-row > span:first-child", "Show in composer");
  setText("#cancelWorkflowEdit", "Cancel");
  setText("#workflowEditor button.primary", "Save and sync");
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
  setTitle("#closeNodeManager", "Close node manager");
  setTitle("#cancelNodeEditIcon", "Close node editor");
  setTitle("#closeWorkflowManager", "Close workflow manager");
  setTitle("#addWorkflowButton", "Add workflow");
  setTitle("#cancelWorkflowEditIcon", "Close workflow editor");
  setTitle("#refreshAssets", "Refresh assets");
  document.querySelector("#assetFoldersPanel")?.setAttribute("aria-label", "Asset folders");
  document.querySelector("#sidebarResizer")?.setAttribute("aria-label", "Resize asset library");
  setTitle("#workflowControl", "Workflow");
  setTitle("#nodeControl", "Inference node");
  document.querySelector("#mentionMenu")?.setAttribute("aria-label", "Quick actions and images");
  document.querySelector("#opsWindow")?.setAttribute("aria-label", "Runtime status and logs");
  setText("#aiPromptSwitch > span:first-child", "Enable AI prompt assistance");
  el("autoUpscale").setAttribute("aria-label", "Upscale after generation");
  setText("#remoteDisconnectLabel", "Handle remote records when disconnected");
  setText('#remoteDisconnectPolicy option[value="encrypt"]', "Encrypt");
  setText('#remoteDisconnectPolicy option[value="delete"]', "Delete");
  setText("#remoteRecordsKeyLabel", "Remote records key");
  setText("#remoteRecordsKeyHelp", "At least 8 and at most 256 characters");
  setTitle("#toggleRemoteRecordsKey", "Show key");
  setText("#workflowEditorSubtitle", "Configure the API graph, field mappings, and target nodes");
  setText("#workflowFileStatus", "Choose a ComfyUI API-format workflow");
  setText("#workflowFileHelp", "If syncing fails, download the JSON, place it in ComfyUI's user workflows folder, then validate.");
  setTitle("#addWorkflowFieldMapping", "Add field mapping");
  setTitle("#addWorkflowReferenceMapping", "Add reference mapping");
  setTitle("#closePeering", "Close device sharing");
  setTitle("#closeGlobalSettings", "Close settings");
  setTitle("#closeVideoUpscale", "Close");
  setTitle("#cancelAutoUpscaleConfirm", "Close");
  setTitle("#closeLocalAssets", "Close");
  setTitle("#closeOldVideoCleanup", "Close");
  setTitle("#closeLocalAssetPreview", "Close preview");
  setTitle("#closeUnlockAssets", "Close");
  setTitle("#closeAssetDetail", "Close asset details");
  setTitle("#closeAssetFolderName", "Close");
  setTitle("#closeAssetFolderPicker", "Close");
  setText("#autoUpscaleConfirmSubtitle", "Choose the upscale plan to run after generation");
  setLeadingText("#autoUpscaleCategoryLabel", "Upscale type");
  setLeadingText("#autoUpscaleScaleLabel", "Upscale scale");
  setText("#confirmAutoUpscaleLabel", "Confirm");
  setText('#videoUpscaleCategory option[value="real"]', "Live action");
  setText('#videoUpscaleCategory option[value="anime"]', "Animation");
  setText('#videoUpscaleCategory option[value="3d"]', "3D");
  setText('#autoUpscaleConfirmCategory option[value="real"]', "Live action");
  setText('#autoUpscaleConfirmCategory option[value="anime"]', "Animation");
  setText('#autoUpscaleConfirmCategory option[value="3d"]', "3D");
  setText("#localAssetsSubtitle", "Delete output files while keeping task and workflow records");
  setText("#localAssetsSelectAllLabel", "Select all loaded assets");
  setTitle("#clearOldVideos", "Delete video assets older than 30 days");
  setText("#clearOldVideos span", "Clear videos older than 30 days");
  setText("#deleteLocalArtifactsLabel", "Delete selected outputs");
  setText("#oldVideoCleanupSubtitle", "The following items will be deleted after confirmation; task records are kept");
  setText("#cancelOldVideoCleanup", "Cancel");
  setText("#confirmOldVideoCleanup span", "Delete");
  setText("#unlockAssetsTitle", "Unlock encrypted assets");
  setText("#unlockAssetsKeyLabel", "Device key");
  setTitle("#toggleUnlockAssetsKey", "Show key");
  setText("#unlockAssetsSubmitLabel", "Unlock this device's assets");
  setText("#assetFolderPickerTitle", "Choose a folder");
  setText("#assetFolderPickerHint", "Choose the destination folder for the selected assets");
  setText("#cancelAssetFolderName", "Cancel");
  setText("#assetFolderNameForm button.primary", "Save");
  setText("#incognitoStatus span", t("incognito"));
  setTitle("#incognitoStatus", "Exit incognito mode");
  setTitle("#closeSecret", "Close");
  setText("#localAssetsTitle", "Manage local assets");
  setText("#oldVideoCleanupTitle", "Clear videos older than 30 days");
  setText("#autoUpscaleConfirmTitle", "Confirm auto upscale");
  setTitle("#assetStatusFilter", "Asset status filter");
  setTitle("#conversationDeviceFilter", "Conversation device filter");
  setText("#conversationFilters span", "Device filter");
  setText("#conversationFilterPanel label > span", "Show devices");
  el("themeGrid").setAttribute("aria-label", "Display");
  setText("#themeTitle", "Theme");
  document.querySelector(".local-asset-preview-dialog")?.setAttribute("aria-label", "Local asset preview");
  el("workflowSelect").setAttribute("aria-label", "Workflow");
  document.querySelectorAll("select").forEach((select) => select.dispatchEvent(new Event("cs:sync")));
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
  setText("#settingsPanelModel > .switch-row > span:first-child", "Enable AI prompt assistance");
  el("seed").placeholder = "Auto";
  setTitle("#addReference", "Add reference files");
  setText("#settingsTabModel", localized("模型", "Model"));
  setText("#settingsTabSystem", localized("系统", "System"));
  setText("#settingsTabUpload", localized("上传", "Upload"));
  setText("#settingsTabExperimental", localized("实验性功能", "Experimental"));
  setText("#settingsPanelExperimental .switch-row > span:first-child", localized("绑定本地 ComfyUI 服务", "Bind local ComfyUI service"));
  setText(
    "#bindLocalComfyuiHelp",
    localized(
      "开启后，本机环境的 ComfyUI 节点会显示「可接管」（黄色）标签；在节点编辑中填写启动路径后，可在推理节点面板直接开启或关闭该 ComfyUI 服务，服务运行时标签变为绿色的「已接管」。",
      "When enabled, ComfyUI nodes on this machine show a yellow Manageable badge; fill in a launch path in the node editor to start and stop that ComfyUI from the inference node panel. While the service runs the badge turns green and reads Managed."
    )
  );
  setText(
    "#bindLocalComfyuiEnvHelp",
    localized(
      "启动时优先使用节点目录中的私有环境（如 venv、.venv、env），找不到时回退到全局 Python 环境。启动失败会在「实时日志」中记录失败原因和原始报错。",
      "Launching prefers the node directory's private environment (venv, .venv, env) and falls back to the global Python environment. Failures are logged with the original error in Live logs."
    )
  );
  document.querySelector(".settings-tabs")?.setAttribute("aria-label", localized("设置分类", "Settings categories"));
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
  setTitle("#openOps", "Activity log");
  setTitle("#closeOps", "Close activity log");
  setControlTitle("comfyNode", "Inference node");
  setControlTitle("aspectRatio", "Aspect ratio");
  setControlTitle("resolution", "Resolution");
  setControlTitle("duration", "Duration");
  setControlTitle("steps", "Sampling steps");
  el("lyrics").placeholder = "Enter lyrics using [Intro], [Verse], [Chorus], [Bridge], [Instrumental], and [Outro] sections";
  syncHeaderTips();
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
  button.title = visible ? localized("显示密钥", "Hide key") : localized("隐藏密钥", "Show key");
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
  if (job.request?.workflow_id?.startsWith("wf-")) return localized("自定义工作流", "Custom workflow");
  if (job.request?.model_variant === "music3-int8") return "Music3 INT8";
  if (job.request?.task_type === "upscale") {
    const category = { real: localized("真人", "Live action"), anime: localized("动画", "Animation"), "3d": "3D" }[job.request?.upscale_category] || localized("超分", "Upscale");
  return `${category} · ${job.request?.upscale_scale || 2}x`;
  }
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
  if (job.request?.workflow_id?.startsWith("wf-") && job.request?.workflow_name) return job.request.workflow_name;
  if (job.request?.task_type === "upscale") return t("videoUpscale");
  if (job.request?.execution_mode === "music3") return t("music3");
  if (job.request?.execution_mode === "digital-human") return t("digitalHuman");
  if (job.request?.execution_mode === "tts") return t("tts");
  if (job.request?.execution_mode === "h3-nsfw") return t("nsfw");
  if (job.request?.execution_mode === "h3-sa") return t("h3Sa");
  if (job.request?.execution_mode === "vdn-h3") return t("vdnH3");
  if (job.request?.execution_mode === "turbo-lora") {
    return String(job.request?.workflow_id || "").includes("4step") ? t("turbo4") : t("turbo");
  }
  if (job.request?.execution_mode === "dual-sampling") return t("dualSampling");
  if (job.request?.execution_mode === "speed-cache") return t("speedCache");
  return t("native");
}

function executionModeClass(job) {
  if (job.request?.task_type === "upscale") return "upscale";
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

function assetNodeLabel(job) {
  const label = nodeLabel(job);
  const owner = job.assigned_node?.owner_name || job.owner_name;
  if (!owner) return label;
  const suffix = ` · ${t("owner")} ${owner}`;
  return label.endsWith(suffix) ? label.slice(0, -suffix.length) : label;
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
  const selectedWorkflow = selectedWorkflowRecord();
  const customTargets = selectedWorkflow?.source === "custom"
    ? new Set((selectedWorkflow.sync || []).filter((item) => item.status === "synced").map((item) => item.node_id))
    : null;
  const availableNodes = state.nodes.filter((node) => (
    !customTargets || (customTargets.has(node.id) && node.provider === "comfyui")
  ));
  const healthyNodes = availableNodes.filter((node) => node.healthy);
  const comfyNodes = availableNodes.filter((node) => node.provider !== "runninghub");
  const healthyComfyNodes = comfyNodes.filter((node) => node.healthy);
  const legacyRunningHubAuto = healthyNodes.length > 0
    && healthyNodes.every((node) => node.provider === "runninghub")
    && new Set(healthyNodes.map((node) => node.workflow_id)).size === 1;
  const autoOnline = legacyRunningHubAuto ? healthyNodes.length : healthyComfyNodes.length;
  const autoTotal = legacyRunningHubAuto ? state.nodes.length : comfyNodes.length;
  const options = [`<option value="auto">${t("autoSchedule")} · ${autoOnline}/${autoTotal} ${t("available")}</option>`];
  const runningHubGroups = new Map();
  availableNodes.filter((node) => node.provider === "runninghub" && node.workflow_id && node.runninghub_schema).forEach((node) => {
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
  availableNodes.forEach((node) => {
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

function selectedWorkflowRecord() {
  const id = el("workflowSelect")?.value;
  return state.workflows.find((item) => item.id === id) || null;
}

function workflowReadyNodeIds(workflow) {
  const synced = new Set((workflow.sync || []).filter((item) => item.status === "synced").map((item) => item.node_id));
  return (workflow.target_node_ids || []).filter((nodeId) => (
    synced.has(nodeId) && state.nodes.some((node) => node.id === nodeId && node.provider === "comfyui" && node.healthy)
  ));
}

function workflowSelectable(workflow) {
  if (workflow.incognito_only && !state.incognito) return false;
  if (workflow.source === "preset") return true;
  const ready = workflowReadyNodeIds(workflow);
  return el("comfyNode").value === "auto" ? ready.length > 0 : ready.includes(el("comfyNode").value);
}

function renderWorkflowOptions() {
  const select = el("workflowSelect");
  if (!select) return;
  const current = select.value;
  const visibleWorkflows = state.workflows.filter((item) => (
    item.visible_in_composer && (!item.incognito_only || state.incognito)
  ));
  const options = visibleWorkflows.map((workflow) => {
    const selectable = workflowSelectable(workflow);
    const label = state.locale === "en" ? (workflow.name_en || workflow.name) : workflow.name;
    const unavailable = workflow.source === "custom" && !selectable;
    return `<option value="${escapeHtml(workflow.id)}"${selectable ? "" : " disabled"}>${escapeHtml(label)}${unavailable ? ` · ${localized("未同步或节点离线", "No synced online node")}` : ""}</option>`;
  });
  select.innerHTML = options.length ? options.join("") : `<option value="">${localized("没有可显示的工作流", "No visible workflows")}</option>`;
  const currentWorkflow = visibleWorkflows.find((item) => item.id === current);
  select.value = currentWorkflow?.id || visibleWorkflows.find(workflowSelectable)?.id || visibleWorkflows[0]?.id || "";
  const workflow = selectedWorkflowRecord();
  if (workflow?.source === "preset") {
    el("modelVariant").value = workflow.model_variant;
    el("executionMode").value = workflow.task_type === "upscale" ? "video-upscale" : workflow.execution_mode;
  } else {
    el("modelVariant").value = "fl2va-fp8";
    el("executionMode").value = "native";
  }
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
  if (state.runninghubEnabled === false && el("nodeProvider")?.value === "runninghub") {
    el("nodeProvider").value = "comfyui";
  }
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
  syncLocalComfyFields();
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

function platformKind() {
  if (state.platform) return state.platform;
  const agent = navigator.userAgent || "";
  if (/Mac OS X|Macintosh/i.test(agent)) return "macos";
  if (/Linux/i.test(agent)) return "linux";
  return "windows";
}

function launchPathPlaceholder() {
  const platform = platformKind();
  if (platform === "macos") return "/Users/you/ComfyUI 或 /Users/you/ComfyUI/main.py";
  if (platform === "linux") return "~/ComfyUI 或 ~/ComfyUI/main.py";
  return "D:\\ComfyUI 或 D:\\ComfyUI\\main.py";
}

function syncLocalComfyFields() {
  const enabled = state.bindLocalComfyui === true;
  if (el("localComfyCommandField")) el("localComfyCommandField").hidden = !enabled;
  if (el("localComfyCommandHelp")) el("localComfyCommandHelp").hidden = !enabled;
  const field = el("nodeLaunchPathField");
  if (!field) return;
  const runningHub = el("nodeProvider")?.value === "runninghub";
  field.hidden = runningHub || state.bindLocalComfyui !== true;
  if (el("nodeLaunchPathLabel")) {
    el("nodeLaunchPathLabel").textContent = localized("ComfyUI 启动路径", "ComfyUI launch path");
  }
  if (el("nodeLaunchPath")) {
    el("nodeLaunchPath").placeholder = launchPathPlaceholder();
  }
  if (el("nodeLaunchPathHint")) {
    el("nodeLaunchPathHint").textContent = localized(
      "填写 ComfyUI 目录或 main.py 路径（Windows 与 macOS 写法均可），用于在本机接管启动与关闭",
      "Directory or main.py path (Windows and macOS styles both work) used to start and stop this ComfyUI on the current machine"
    );
  }
}

function localComfyStatusLabel(runtime) {
  const status = runtime?.status || "stopped";
  if (status === "starting") return localized("启动中…", "Starting…");
  if (status === "running") return runtime?.managed === false ? localized("运行中（外部）", "Running (external)") : localized("运行中", "Running");
  if (status === "stopping") return localized("关闭中…", "Stopping…");
  if (status === "failed") return localized("启动失败", "Failed");
  return localized("已关闭", "Stopped");
}

const localComfyPending = new Set();

function scheduleLocalComfyRefresh() {
  clearTimeout(state.localComfyTimer);
  state.localComfyTimer = null;
  if (localComfyPending.size) return;
  if (el("nodeModal")?.hidden) return;
  const transitioning = state.managedNodes.some((node) => {
    const status = node.local_runtime?.status;
    return status === "starting" || status === "stopping";
  });
  if (!transitioning) return;
  state.localComfyTimer = setTimeout(() => {
    loadManagedNodes().catch(() => {}).finally(() => scheduleLocalComfyRefresh());
  }, 2000);
}

function applyLocalRuntime(nodeId, runtime) {
  const target = state.managedNodes.find((item) => item.id === nodeId);
  if (!target) return;
  if (runtime) target.local_runtime = runtime;
  else delete target.local_runtime;
  renderManagedNodes();
}

async function toggleLocalComfy(nodeId, start) {
  const node = state.managedNodes.find((item) => item.id === nodeId);
  if (!node) return;
  el("nodeManagerError").textContent = "";
  const action = start ? "start" : "stop";
  localComfyPending.add(nodeId);
  applyLocalRuntime(nodeId, { ...(node.local_runtime || {}), status: start ? "starting" : "stopping", error: "" });
  scheduleLocalComfyRefresh();
  try {
    const payload = await api(`/api/v1/comfy/nodes/${encodeURIComponent(nodeId)}/local-comfy/${action}`, { method: "POST" });
    applyLocalRuntime(nodeId, payload?.local_runtime || null);
    checkHealth().catch(() => {});
  } catch (error) {
    const current = state.managedNodes.find((item) => item.id === nodeId);
    applyLocalRuntime(nodeId, {
      ...(current?.local_runtime || {}),
      status: start ? "failed" : "stopped",
      error: error.message,
    });
    el("nodeManagerError").textContent = error.message;
  } finally {
    localComfyPending.delete(nodeId);
    scheduleLocalComfyRefresh();
  }
}

function renderManagedNodes() {
  const remoteCount = state.managedNodes.filter((node) => node.remote_proxy || node.local === false).length;
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
      : node.queue_depth ? ` · ${localized("排队", "queued")} ${node.queue_depth}` : "";
    const restricted = node.provider === "runninghub" && state.runninghubEnabled === false;
    const statusDot = `<i class="node-status-dot ${status.className}" title="${escapeHtml(status.label)}${escapeHtml(activity)}"></i>`;
    if (node.remote_proxy) {
      const owner = node.owner_name || node.source?.name || localized("远程设备", "Remote device");
      return `<div class="node-banner remote-node" data-node-id="${escapeHtml(node.id)}">
        <div class="node-banner-body"><div class="node-banner-head"><strong>${escapeHtml(node.name || localized("远程推理节点", "Remote inference node"))}</strong>${statusDot}</div><small>${escapeHtml(localized("远程代理节点", "Remote proxy node"))} · ${escapeHtml(t("owner"))} ${escapeHtml(owner)}${escapeHtml(activity)}</small></div>
        <div class="node-banner-side"><div class="node-row-actions" aria-hidden="true"></div></div>
      </div>`;
    }
    const provider = node.provider === "runninghub" ? "RunningHub API" : "ComfyUI API";
    const location = node.local === false ? `${localized("远程节点", "Remote node")} · ` : "";
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
    const takeover = node.takeover === true;
    const runtime = node.local_runtime || null;
    const supervised = ["running", "starting", "stopping"].includes(String(runtime?.status || ""));
    const badge = takeover
      ? supervised
        ? `<span class="node-badge is-supervised" title="${escapeHtml(localized("本地 ComfyUI 服务由 Studio 接管运行", "The local ComfyUI service is managed by Studio"))}">${escapeHtml(localized("已接管", "Managed"))}</span>`
        : `<span class="node-badge is-manageable" title="${escapeHtml(localized("填写启动路径后可由 Studio 接管运行", "Add a launch path so Studio can manage this service"))}">${escapeHtml(localized("可接管", "Manageable"))}</span>`
      : "";
    const transition = runtime?.status === "starting" || runtime?.status === "stopping";
    const powerLabel = localComfyStatusLabel(runtime);
    const power = takeover && String(node.launch_path || "").trim()
      ? `<label class="node-power" title="${escapeHtml(runtime?.status === "running" ? localized("关闭本机 ComfyUI 服务", "Stop the local ComfyUI service") : localized("启动本机 ComfyUI 服务", "Start the local ComfyUI service"))}">${runtime && runtime.status !== "stopped" ? `<span class="node-power-text">${escapeHtml(powerLabel)}</span>` : ""}<input type="checkbox" data-node-action="power" ${runtime?.status === "running" || runtime?.status === "starting" ? "checked" : ""} ${transition ? "disabled" : ""} aria-label="${escapeHtml(powerLabel)}"><span class="switch"></span></label>`
      : "";
    const powerError = takeover && runtime?.status === "failed" && runtime.error
      ? `<small class="node-power-error" title="${escapeHtml(runtime.error)}">${escapeHtml(String(runtime.error).split("\n")[0])}</small>`
      : "";
    return `<div class="node-banner${restricted ? " is-restricted" : ""}" data-node-id="${escapeHtml(node.id)}">
      <div class="node-banner-body">
        <div class="node-banner-head"><strong>${escapeHtml(node.provider === "runninghub" ? node.workflow_name || node.name : node.name)}</strong>${badge}${statusDot}</div>
        <code title="${escapeHtml(node.url)}">${escapeHtml(node.url)}</code>
        ${accounting}${workflowIssue}
        <small>${location}${provider}${workflow}${node.provider === "runninghub" && node.workflow_name && node.workflow_name !== node.name ? ` · ${escapeHtml(node.name)}` : ""}${keyState} · ID ${escapeHtml(node.id)}${node.last_checked ? ` · ${formatTime(node.last_checked, true)} ${checkedLabel}` : ""}${escapeHtml(activity)}</small>
        ${restricted ? `<small class="node-restricted">${localized("RunningHub 端点工作流已关闭", "RunningHub endpoint workflows are disabled")}</small>` : ""}
        ${powerError}
      </div>
      <div class="node-banner-side">
        ${power}
        <div class="node-row-actions"><button type="button" data-node-action="edit" title="${localized("编辑节点", "Edit node")}" aria-label="${localized("编辑节点", "Edit node")} ${escapeHtml(node.name)}">${icon("pencil")}</button><button type="button" data-node-action="delete" title="${localized("删除节点", "Delete node")}" aria-label="${localized("删除节点", "Delete node")} ${escapeHtml(node.name)}">${icon("trash-2")}</button></div>
      </div>
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
  const localNodes = (payload.data || []).map((node) => {
    const merged = { ...node, ...(statuses.get(node.id) || {}) };
    if (localComfyPending.has(node.id)) {
      const previous = state.managedNodes.find((item) => item.id === node.id);
      if (previous?.local_runtime) merged.local_runtime = previous.local_runtime;
    }
    return merged;
  });
  const localIds = new Set(localNodes.map((node) => node.id));
  const remoteNodes = state.nodes
    .filter((node) => node.remote_proxy && !localIds.has(node.id))
    .map((node) => ({ ...node, enabled: true, managed_remote: true }));
  state.managedNodes = [...localNodes, ...remoteNodes];
  if (el("nodeHealthInterval")) el("nodeHealthInterval").value = String(payload.health_interval_seconds || 60);
  state.bindLocalComfyui = payload.bind_local_comfyui === true;
  renderManagedNodes();
  syncLocalComfyFields();
  scheduleLocalComfyRefresh();
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
  el("nodeLaunchPath").value = node?.launch_path || "";
  el("nodeEnabled").checked = node ? Boolean(node.enabled) : true;
  el("nodeEnabled").closest(".node-enabled-row").hidden = !node;
  el("nodeEditorModal").hidden = false;
  document.body.classList.add("modal-open");
  el("nodeManagerError").textContent = "";
  applyRunningHubAvailability();
  syncNodeProviderFields();
  refreshIcons();
  requestAnimationFrame(() => el("nodeName").focus());
}

function closeNodeEditor() {
  state.nodeEditingId = null;
  el("nodeEditor").reset();
  el("nodeEditorModal").hidden = true;
  el("nodeManagerError").textContent = "";
}

function applyRunningHubAvailability() {
  const enabled = state.runninghubEnabled !== false;
  const option = el("nodeProvider")?.querySelector('option[value="runninghub"]');
  if (option) option.disabled = !enabled;
  if (!enabled && el("nodeProvider")?.value === "runninghub" && !state.nodeEditingId) {
    el("nodeProvider").value = "comfyui";
  }
}

async function openNodeManager() {
  el("nodeModal").hidden = false;
  document.body.classList.add("modal-open");
  el("nodeManagerError").textContent = "";
  applyRunningHubAvailability();
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
  if (el("nodeProvider").value === "runninghub" && state.runninghubEnabled === false) {
    el("nodeManagerError").textContent = localized("RunningHub 端点工作流已关闭", "RunningHub endpoint workflows are disabled");
    return;
  }
  const editing = state.nodeEditingId;
  const body = {
    name: el("nodeName").value.trim(),
    url: el("nodeUrl").value.trim(),
    provider: el("nodeProvider").value,
    api_key: el("nodeApiKey").value.trim(),
    workflow_url: el("nodeWorkflowUrl").value.trim(),
    max_concurrency: Number(el("nodeMaxConcurrency").value || 1),
  };
  if (el("nodeLaunchPathField") && !el("nodeLaunchPathField").hidden) {
    body.launch_path = el("nodeLaunchPath").value.trim();
  } else if (!editing) {
    body.launch_path = "";
  }
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
    await Promise.all([loadManagedNodes(), checkHealth(), loadWorkflows()]);
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
    await Promise.all([loadManagedNodes(), checkHealth(), loadWorkflows()]);
  } catch (error) {
    el("nodeManagerError").textContent = error.message;
  }
}

const WORKFLOW_FIELDS = [
  ["prompt", "提示词"], ["lyrics", "歌词"], ["width", "宽度"], ["height", "高度"],
  ["ratio", "画面比例"], ["megapixels", "像素（MP）"],
  ["duration", "时长"], ["num_frames", "帧数"], ["steps", "步数"], ["seed", "随机种子"],
];

// Conditioning nodes expose link-style reference inputs such as
// "ref_images.ref_image_0". Binding one of these families lets the engine create
// a matching loader node on the fly, so a workflow can take any number of files.
const REFERENCE_SLOT_FAMILIES = {
  ref_images: { kind: "image", suffix: "ref_image" },
  ref_videos: { kind: "video", suffix: "ref_video" },
  ref_audios: { kind: "audio", suffix: "ref_audio" },
};
// Official H3 conditioning limits for one generation.
const REFERENCE_LIMITS = { image: 9, video: 3, audio: 3 };

function workflowSlotTargets(graph) {
  const found = new Map();
  Object.entries(graph || {}).forEach(([nodeId, node]) => {
    Object.keys(node?.inputs || {}).forEach((key) => {
      const match = /^(ref_images|ref_videos|ref_audios)\.ref_(image|video|audio)_(\d+)$/.exec(key);
      if (!match) return;
      const id = `${nodeId}:${match[1]}`;
      const entry = found.get(id) || { nodeId, family: match[1], indexes: [] };
      entry.indexes.push(Number(match[3]) + 1);
      found.set(id, entry);
    });
  });
  return [...found.values()].map((entry) => ({
    ...entry,
    kind: REFERENCE_SLOT_FAMILIES[entry.family].kind,
    indexes: [...new Set(entry.indexes)].sort((a, b) => a - b),
  }));
}

function referenceSlotFamiliesForNode(nodeId, node) {
  const families = new Set();
  Object.keys(node?.inputs || {}).forEach((key) => {
    const match = /^(ref_images|ref_videos|ref_audios)\./.exec(key);
    if (match) families.add(match[1]);
  });
  if (/Reference/i.test(String(node?.class_type || ""))) {
    Object.keys(REFERENCE_SLOT_FAMILIES).forEach((family) => families.add(family));
  }
  return [...families].map((family) => ({ family, kind: REFERENCE_SLOT_FAMILIES[family].kind }));
}

function referenceSlotLabel(family) {
  const kind = REFERENCE_SLOT_FAMILIES[family].kind;
  const text = { image: ["图片槽位", "image slot"], video: ["视频槽位", "video slot"], audio: ["音频槽位", "audio slot"] }[kind];
  return `${family} · ${localized(text[0], text[1])}`;
}

function autoFillWorkflowReferenceMappings() {
  if (el("workflowReferenceMappings").children.length) return 0;
  const rows = [];
  const seenFamilies = new Set();
  workflowSlotTargets(state.workflowDraftJson).forEach((slot) => {
    // One slot binding is enough for the whole family: the engine creates a
    // loader per uploaded file and only needs the family target once.
    const familyKey = `${slot.nodeId}:${slot.family}`;
    if (seenFamilies.has(familyKey)) return;
    seenFamilies.add(familyKey);
    rows.push({ type: slot.kind, index: 1, node_id: slot.nodeId, input: slot.family, slot: true, required: true });
  });
  if (!rows.length) return 0;
  el("workflowReferenceMappings").replaceChildren(...rows.map((row) => renderWorkflowReferenceMapping(row)));
  refreshIcons();
  return rows.length;
}

function workflowNodeSelect(graph, selected = "", className = "workflow-node-select") {
  const options = Object.entries(graph || {}).map(([nodeId, node]) => (
    `<option value="${escapeHtml(nodeId)}"${nodeId === selected ? " selected" : ""}>${escapeHtml(`${nodeId} · ${node.class_type || "Node"}`)}</option>`
  )).join("");
  return `<select class="${className}" aria-label="${localized("工作流节点", "Workflow node")}">${options}</select>`;
}

function updateWorkflowMappingInputOptions(row, { reference = false } = {}) {
  const graph = state.workflowDraftJson || {};
  const nodeSelect = row.querySelector("[data-workflow-node]");
  const inputSelect = row.querySelector("[data-workflow-input]");
  if (!nodeSelect || !inputSelect) return;
  const previous = inputSelect.value;
  const node = graph[nodeSelect.value];
  const inputs = Object.entries(node?.inputs || {}).filter(([, value]) => !(
    Array.isArray(value) && value.length === 2 && typeof value[0] === "string" && Number.isInteger(value[1])
  ));
  const options = inputs.map(([name]) => (
    `<option value="${escapeHtml(JSON.stringify([nodeSelect.value, name]))}">${escapeHtml(name)}</option>`
  ));
  if (reference) {
    referenceSlotFamiliesForNode(nodeSelect.value, node).forEach(({ family }) => {
      options.push(`<option value="${escapeHtml(JSON.stringify([nodeSelect.value, family]))}">${escapeHtml(referenceSlotLabel(family))}</option>`);
    });
  }
  inputSelect.innerHTML = options.join("");
  if (previous && [...inputSelect.options].some((option) => option.value === previous)) inputSelect.value = previous;
}

function renderWorkflowFieldMapping(mapping = {}) {
  const nodeId = mapping.node_id || Object.keys(state.workflowDraftJson || {})[0] || "";
  const fieldOptions = WORKFLOW_FIELDS.map(([value, label]) => `<option value="${value}"${mapping.field === value ? " selected" : ""}>${state.locale === "en" ? value : label}</option>`).join("");
  const row = document.createElement("div");
  row.className = "workflow-mapping-row";
  row.innerHTML = `<select data-workflow-field aria-label="${localized("生成字段", "Field")}">${fieldOptions}</select>${workflowNodeSelect(state.workflowDraftJson, nodeId, "workflow-node-select")}<select data-workflow-input aria-label="${localized("节点输入", "Node input")}"></select><button type="button" data-remove-mapping title="${localized("移除映射", "Remove mapping")}" aria-label="${localized("移除映射", "Remove mapping")}">${icon("trash-2")}</button>`;
  row.querySelector(".workflow-node-select").dataset.workflowNode = "";
  row.querySelector(".workflow-node-select").classList.remove("workflow-node-select");
  row.querySelector("[data-workflow-node]").addEventListener("change", () => updateWorkflowMappingInputOptions(row));
  row.querySelector("[data-remove-mapping]").addEventListener("click", () => row.remove());
  updateWorkflowMappingInputOptions(row);
  if (mapping.input) row.querySelector("[data-workflow-input]").value = JSON.stringify([nodeId, mapping.input]);
  return row;
}

function defaultReferenceNodeId() {
  const graph = state.workflowDraftJson || {};
  const slot = workflowSlotTargets(graph)[0];
  if (slot) return slot.nodeId;
  const keys = Object.keys(graph);
  return keys.find((key) => /Reference/i.test(String(graph[key]?.class_type || ""))) || keys[0] || "";
}

function nextReferenceIndex(type, excludeRow = null) {
  const used = new Set(
    Array.from(el("workflowReferenceMappings").children).filter((row) => row !== excludeRow).map((row) => {
      const rowType = row.querySelector("[data-ref-type]")?.value || "image";
      const rowIndex = Number(row.querySelector("[data-ref-index]")?.value || 0);
      return `${rowType}:${rowIndex}`;
    }),
  );
  let index = 1;
  while (used.has(`${type}:${index}`)) index += 1;
  return index;
}

function renderWorkflowReferenceMapping(mapping = {}) {
  const nodeId = mapping.node_id || defaultReferenceNodeId();
  const row = document.createElement("div");
  row.className = "workflow-mapping-row reference-row";
  const type = mapping.type || "image";
  const typeOptions = ["image", "video", "audio"].map((value) => `<option value="${value}"${type === value ? " selected" : ""}>${value}</option>`).join("");
  const index = mapping.index || nextReferenceIndex(type);
  row.innerHTML = `<select data-ref-type aria-label="${localized("素材类型", "Reference type")}">${typeOptions}</select><input data-ref-index type="number" min="1" max="15" value="${Number(index)}" aria-label="${localized("同类型序号", "Reference index")}">${workflowNodeSelect(state.workflowDraftJson, nodeId, "workflow-node-select")}<select data-workflow-input aria-label="${localized("节点输入", "Node input")}"></select><label class="workflow-required-option"><input data-ref-required type="checkbox"${mapping.required === false ? "" : " checked"}><span>${localized("必需", "Required")}</span></label><button type="button" data-remove-mapping title="${localized("移除映射", "Remove mapping")}" aria-label="${localized("移除映射", "Remove mapping")}">${icon("trash-2")}</button>`;
  row.querySelector(".workflow-node-select").dataset.workflowNode = "";
  row.querySelector(".workflow-node-select").classList.remove("workflow-node-select");
  row.querySelector("[data-workflow-node]").addEventListener("change", () => updateWorkflowMappingInputOptions(row, { reference: true }));
  row.querySelector("[data-ref-type]").addEventListener("change", (event) => {
    const indexInput = row.querySelector("[data-ref-index]");
    if (indexInput) indexInput.value = String(nextReferenceIndex(event.target.value, row));
  });
  row.querySelector("[data-remove-mapping]").addEventListener("click", () => {
    row.remove();
    autoFillWorkflowReferenceMappings();
  });
  updateWorkflowMappingInputOptions(row, { reference: true });
  if (mapping.input) row.querySelector("[data-workflow-input]").value = JSON.stringify([nodeId, mapping.input]);
  return row;
}

function renderWorkflowMappingRows(workflow = null) {
  const fields = workflow?.field_mappings || {};
  el("workflowFieldMappings").replaceChildren(...Object.entries(fields).map(([field, binding]) => renderWorkflowFieldMapping({ field, ...binding })));
  el("workflowReferenceMappings").replaceChildren(...(workflow?.reference_mappings || []).map(renderWorkflowReferenceMapping));
  autoFillWorkflowReferenceMappings();
  refreshIcons();
}

function renderWorkflowTargets(targetIds = []) {
  const nodes = state.managedNodes.filter((node) => node.provider === "comfyui" && node.enabled);
  el("workflowTargetNodes").innerHTML = nodes.length
    ? nodes.map((node) => `<label class="workflow-target-option"><input type="checkbox" value="${escapeHtml(node.id)}"${targetIds.includes(node.id) ? " checked" : ""}><span>${escapeHtml(node.name)}</span></label>`).join("")
    : `<span class="quiet">${localized("请先添加 ComfyUI 节点", "Add a ComfyUI node first")}</span>`;
}

function renderWorkflowResultNodes(selectedId = "") {
  const graph = state.workflowDraftJson || {};
  const nodes = Object.entries(graph).filter(([, node]) => Object.hasOwn(node?.inputs || {}, "filename_prefix"));
  el("workflowResultNode").innerHTML = nodes.map(([nodeId, node]) => (
    `<option value="${escapeHtml(nodeId)}"${String(nodeId) === String(selectedId) ? " selected" : ""}>${escapeHtml(`${nodeId} · ${node.class_type || "Save"}`)}</option>`
  )).join("");
}

function workflowSyncLabel(workflow) {
  if (workflow.source === "preset") return localized("内置预设", "Built-in preset");
  const sync = workflow.sync || [];
  if (!sync.length) return localized("未配置节点", "No target nodes");
  return sync.map((item) => {
    const node = state.managedNodes.find((entry) => entry.id === item.node_id);
    const label = node?.name || item.node_id;
    if (item.status === "synced") return `${label}: ${localized("已同步", "synced")}`;
    if (item.status === "failed") return `${label}: ${localized("同步失败", "sync failed")}${item.error ? ` · ${item.error}` : ""}`;
    return `${label}: ${localized("待同步", "pending")}`;
  }).join("\n");
}

function renderWorkflowList() {
  const list = el("workflowList");
  const count = state.workflows.length;
  const summary = el("workflowManagerSummary");
  summary.textContent = String(count);
  const summaryLabel = state.locale === "en" ? `${count} workflows` : `${count} 个工作流`;
  summary.title = summaryLabel;
  summary.setAttribute("aria-label", summaryLabel);
  list.innerHTML = state.workflows.map((workflow) => {
    const custom = workflow.source === "custom";
    const syncText = workflowSyncLabel(workflow);
    const syncClass = custom && (workflow.sync || []).some((item) => item.status === "failed") ? "workflow-sync-failed" : custom && workflowReadyNodeIds(workflow).length ? "workflow-sync-ready" : "";
    const title = state.locale === "en" ? workflow.name_en || workflow.name : workflow.name;
    const description = custom
      ? String(workflow.description || "")
      : String(state.locale === "en" ? workflow.description_en || workflow.description : workflow.description || "");
    const scope = workflow.incognito_only
      ? `<span class="workflow-scope">${localized("私密", "Private")}</span>`
      : "";
    const toggle = `<label class="workflow-visibility" title="${localized("显示在生成区", "Show in composer")}"><input type="checkbox" role="switch" data-workflow-action="visibility"${workflow.visible_in_composer ? " checked" : ""} aria-label="${localized("显示工作流", "Show workflow")}"><span class="switch"></span></label>`;
    const actions = custom
      ? `<button type="button" data-workflow-action="edit" title="${localized("编辑工作流", "Edit workflow")}" aria-label="${localized("编辑工作流", "Edit workflow")}">${icon("pencil")}</button><button type="button" data-workflow-action="download" title="${localized("下载 API JSON", "Download API JSON")}" aria-label="${localized("下载 API JSON", "Download API JSON")}">${icon("download")}</button><button type="button" data-workflow-action="sync" title="${localized("重试同步", "Retry sync")}" aria-label="${localized("重试同步", "Retry sync")}">${icon("refresh-cw")}</button><button type="button" data-workflow-action="verify" title="${localized("验证手动上传副本", "Verify manual upload")}" aria-label="${localized("验证手动上传副本", "Verify manual upload")}">${icon("badge-check")}</button><button type="button" data-workflow-action="delete" title="${t("delete")}" aria-label="${t("delete")}">${icon("trash-2")}</button>`
      : "";
    const status = custom ? `<small class="workflow-status ${syncClass}" title="${escapeHtml(syncText)}">${escapeHtml(syncText.replaceAll("\n", " · "))}</small>` : "";
    return `<article class="workflow-row" data-workflow-id="${escapeHtml(workflow.id)}"><div class="workflow-row-copy"><div class="workflow-row-title"><strong title="${escapeHtml(title)}">${escapeHtml(title)}</strong>${scope}</div>${description ? `<small class="workflow-description" title="${escapeHtml(description)}">${escapeHtml(description)}</small>` : ""}${status}</div><div class="workflow-row-side">${toggle}<div class="workflow-row-actions">${actions}</div></div></article>`;
  }).join("") || `<p class="quiet">${localized("暂无工作流", "No workflows")}</p>`;
  refreshIcons();
}

async function loadWorkflows() {
  const payload = await api("/api/v1/workflows");
  state.workflows = payload.data || [];
  renderWorkflowOptions();
  renderWorkflowList();
  updateModelUi();
}

function closeWorkflowEditor({ restoreFocus = true } = {}) {
  const returnFocus = state.workflowEditorReturnFocus;
  state.workflowEditingId = null;
  state.workflowDraftJson = null;
  state.workflowEditorReturnFocus = null;
  el("workflowEditor").reset();
  el("workflowEditorModal").hidden = true;
  el("workflowModal").setAttribute("aria-modal", "true");
  el("workflowEditorError").textContent = "";
  el("workflowFieldMappings").replaceChildren();
  el("workflowReferenceMappings").replaceChildren();
  el("workflowFileStatus").textContent = localized("选择 ComfyUI 的 API 格式工作流", "Choose a ComfyUI API-format workflow");
  if (restoreFocus && returnFocus?.isConnected) returnFocus.focus();
}

function openNewWorkflowEditor() {
  const returnFocus = document.activeElement;
  closeWorkflowEditor({ restoreFocus: false });
  state.workflowEditorReturnFocus = returnFocus;
  el("workflowEditor").reset();
  state.workflowDraftJson = null;
  el("workflowEditorTitle").textContent = localized("新增工作流", "Add workflow");
  el("workflowStaticInputs").value = "{}";
  renderWorkflowTargets([]);
  renderWorkflowResultNodes();
  el("workflowEditorModal").hidden = false;
  el("workflowModal").setAttribute("aria-modal", "false");
  document.body.classList.add("modal-open");
  requestAnimationFrame(() => el("workflowName").focus());
}

async function openWorkflowEditor(workflowId) {
  const returnFocus = document.activeElement;
  closeWorkflowEditor({ restoreFocus: false });
  state.workflowEditorReturnFocus = returnFocus;
  el("workflowEditorError").textContent = "";
  try {
    const workflow = await api(`/api/v1/workflows/${encodeURIComponent(workflowId)}`);
    if (workflow.source !== "custom") return;
    state.workflowEditingId = workflow.id;
    state.workflowDraftJson = workflow.workflow_json;
    el("workflowName").value = workflow.name;
    el("workflowDescription").value = workflow.description || "";
    el("workflowStaticInputs").value = JSON.stringify(workflow.static_inputs || {}, null, 2);
    el("workflowMediaType").value = workflow.media_type || "video";
    el("workflowVisible").checked = Boolean(workflow.visible_in_composer);
    el("workflowFileStatus").textContent = localized("已载入数据库中的工作流图", "Loaded workflow graph from the database");
    renderWorkflowMappingRows(workflow);
    renderWorkflowResultNodes(workflow.result_node_id);
    renderWorkflowTargets(workflow.target_node_ids || []);
    el("workflowEditorTitle").textContent = localized("编辑工作流", "Edit workflow");
    el("workflowEditorModal").hidden = false;
    el("workflowModal").setAttribute("aria-modal", "false");
    document.body.classList.add("modal-open");
    requestAnimationFrame(() => el("workflowName").focus());
  } catch (error) {
    setWorkflowManagerError(error.message);
  }
}

function workflowPayloadFromEditor() {
  if (!state.workflowDraftJson) throw new Error(localized("请先选择有效的 API 工作流 JSON", "Choose a valid API workflow JSON first"));
  let staticInputs;
  try {
    staticInputs = JSON.parse(el("workflowStaticInputs").value || "{}");
  } catch {
    throw new Error(localized("静态输入 JSON 格式无效", "Static inputs JSON is invalid"));
  }
  if (!staticInputs || typeof staticInputs !== "object" || Array.isArray(staticInputs)) throw new Error(localized("静态输入必须是 JSON 对象", "Static inputs must be a JSON object"));
  const fieldMappings = {};
  el("workflowFieldMappings").querySelectorAll(".workflow-mapping-row").forEach((row) => {
    const field = row.querySelector("[data-workflow-field]").value;
    const selectedTarget = row.querySelector("[data-workflow-input]").value;
    if (!selectedTarget) return;
    const [node_id, input] = JSON.parse(selectedTarget);
    fieldMappings[field] = { node_id, input };
  });
  const referenceMappings = Array.from(el("workflowReferenceMappings").querySelectorAll(".workflow-mapping-row")).map((row) => {
    const selectedTarget = row.querySelector("[data-workflow-input]").value;
    const [node_id, input] = JSON.parse(selectedTarget);
    const type = row.querySelector("[data-ref-type]").value;
    const slot = Object.hasOwn(REFERENCE_SLOT_FAMILIES, input);
    if (slot && REFERENCE_SLOT_FAMILIES[input].kind !== type) {
      throw new Error(localized(
        `“${input}”槽位只能映射 ${REFERENCE_SLOT_FAMILIES[input].kind} 素材`,
        `Slot "${input}" only accepts ${REFERENCE_SLOT_FAMILIES[input].kind} media`,
      ));
    }
    return {
      type,
      index: Number(row.querySelector("[data-ref-index]").value),
      node_id,
      input,
      slot,
      required: row.querySelector("[data-ref-required]").checked,
    };
  });
  const target_node_ids = Array.from(el("workflowTargetNodes").querySelectorAll("input:checked")).map((input) => input.value);
  return {
    name: el("workflowName").value.trim(),
    description: el("workflowDescription").value,
    workflow_json: state.workflowDraftJson,
    field_mappings: fieldMappings,
    reference_mappings: referenceMappings,
    static_inputs: staticInputs,
    result_node_id: el("workflowResultNode").value,
    media_type: el("workflowMediaType").value,
    target_node_ids,
    visible_in_composer: el("workflowVisible").checked,
  };
}

async function saveWorkflow(event) {
  event.preventDefault();
  const submit = el("workflowEditor").querySelector('button[type="submit"]');
  submit.disabled = true;
  el("workflowEditorError").textContent = "";
  try {
    const payload = workflowPayloadFromEditor();
    const editing = state.workflowEditingId;
    await api(editing ? `/api/v1/workflows/${encodeURIComponent(editing)}` : "/api/v1/workflows", {
      method: editing ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    closeWorkflowEditor();
    await loadWorkflows();
    await checkHealth();
  } catch (error) {
    el("workflowEditorError").textContent = error.message;
  } finally {
    submit.disabled = false;
  }
}

async function setWorkflowVisibility(workflow, visible) {
  try {
    await api(`/api/v1/workflows/${encodeURIComponent(workflow.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visible_in_composer: visible }),
    });
    await loadWorkflows();
  } catch (error) {
    setWorkflowManagerError(error.message);
    renderWorkflowList();
  }
}

async function syncWorkflow(workflowId, manualConfirm = false) {
  try {
    const result = await api(`/api/v1/workflows/${encodeURIComponent(workflowId)}/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ manual_confirm: manualConfirm }),
    });
    const failures = (result.data || []).filter((item) => item.status === "failed");
    setWorkflowManagerError(failures.length
      ? failures.map((item) => `${item.node_id}: ${item.error}`).join(" · ")
      : manualConfirm ? localized("远端副本已校验", "Remote copies verified") : "");
    await loadWorkflows();
  } catch (error) {
    setWorkflowManagerError(error.message);
  }
}

async function downloadWorkflow(workflowId) {
  try {
    const workflow = await api(`/api/v1/workflows/${encodeURIComponent(workflowId)}`);
    const blob = new Blob([JSON.stringify(workflow.workflow_json, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `H3Studio_${workflow.id}.json`;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    setWorkflowManagerError(error.message);
  }
}

async function deleteWorkflow(workflowId) {
  const workflow = state.workflows.find((item) => item.id === workflowId);
  if (!workflow || !window.confirm(localized(`确认删除工作流“${workflow.name}”？`, `Delete workflow "${workflow.name}"?`))) return;
  try {
    const result = await api(`/api/v1/workflows/${encodeURIComponent(workflowId)}`, { method: "DELETE" });
    if (result.remote_cleanup_errors?.length) setWorkflowManagerError(result.remote_cleanup_errors.map((item) => `${item.node_id}: ${item.error}`).join(" · "));
    await loadWorkflows();
  } catch (error) {
    setWorkflowManagerError(error.message);
  }
}

async function openWorkflowManager() {
  el("workflowModal").hidden = false;
  document.body.classList.add("modal-open");
  setWorkflowManagerError("");
  refreshIcons();
  try {
    await Promise.all([loadWorkflows(), loadManagedNodes()]);
    renderWorkflowList();
  } catch (error) {
    setWorkflowManagerError(error.message);
  }
}

function closeWorkflowManager() {
  closeWorkflowEditor({ restoreFocus: false });
  el("workflowModal").hidden = true;
  if (el("nodeModal").hidden && el("peeringModal").hidden && el("assetDetailModal").hidden) document.body.classList.remove("modal-open");
  el("openWorkflowManager").focus();
}

async function handleWorkflowJsonFile(file) {
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) {
    el("workflowEditorError").textContent = localized("工作流 JSON 不能超过 5 MB", "Workflow JSON cannot exceed 5 MB");
    return;
  }
  try {
    const graph = JSON.parse(await file.text());
    if (!graph || typeof graph !== "object" || Array.isArray(graph) || !Object.keys(graph).length) throw new Error(localized("JSON 顶层必须是非空节点对象", "The JSON root must be a non-empty node object"));
    state.workflowDraftJson = graph;
    renderWorkflowMappingRows();
    const slots = el("workflowReferenceMappings").querySelectorAll(".workflow-mapping-row").length;
    renderWorkflowResultNodes();
    renderWorkflowTargets(Array.from(el("workflowTargetNodes").querySelectorAll("input:checked")).map((input) => input.value));
    el("workflowFileStatus").textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB${slots ? ` · ${localized(`已识别 ${slots} 个参考素材槽位`, `${slots} reference slots detected`)}` : ""}`;
    el("workflowEditorError").textContent = "";
  } catch (error) {
    el("workflowEditorError").textContent = localized(`无法读取工作流 JSON：${error.message}`, `Cannot read workflow JSON: ${error.message}`);
  }
}

function isActive(job) {
  return ["queued", "running"].includes(job.status);
}

function isAnonymousQueueJob(job) {
  return !job.id;
}

function selectedVariant() {
  return ANDROID_CLIENT ? "fl2va-fp8" : el("modelVariant").value;
}

function selectedExecutionMode() {
  return ANDROID_CLIENT ? "turbo-lora" : el("executionMode").value;
}

function selectedTurboSteps() {
  const id = selectedWorkflowRecord()?.id || "";
  return id.includes("4step") ? 4 : 8;
}

function isUpscale(executionMode = selectedExecutionMode()) {
  return executionMode === "video-upscale" || Boolean(selectedWorkflowRecord()?.id?.startsWith("preset-upscale-"));
}

function upscaleMediaType() {
  const id = selectedWorkflowRecord()?.id;
  return id === "preset-upscale-image" ? "image" : id === "preset-upscale-video" ? "video" : "";
}

function selectedUpscaleScale() {
  return Number(el("upscaleScale").value) === 4 ? 4 : 2;
}

function autoUpscaleParameters() {
  return {
    auto_upscale: Boolean(el("autoUpscale")?.checked),
    auto_upscale_category: el("upscaleCategory")?.value || "real",
    auto_upscale_scale: Number(el("upscaleScale")?.value) === 4 ? 4 : 2,
  };
}

function confirmAutoUpscale() {
  return !el("autoUpscale")?.checked || isUpscale();
}

let autoUpscaleConfirmResolve = null;

function closeAutoUpscaleConfirm(result = false) {
  el("autoUpscaleConfirmModal").hidden = true;
  if (document.activeElement?.closest("#autoUpscaleConfirmModal")) document.activeElement.blur();
  if (autoUpscaleConfirmResolve) {
    const resolve = autoUpscaleConfirmResolve;
    autoUpscaleConfirmResolve = null;
    resolve(result);
  }
}

function requestAutoUpscaleConfirmation() {
  if (!el("autoUpscale")?.checked || isUpscale()) return Promise.resolve(true);
  el("autoUpscaleConfirmCategory").value = el("upscaleCategory").value || "real";
  el("autoUpscaleConfirmScale").value = el("upscaleScale").value || "2";
  el("autoUpscaleConfirmModal").hidden = false;
  refreshIcons();
  return new Promise((resolve) => { autoUpscaleConfirmResolve = resolve; });
}

function backendExecutionMode() {
  return isUpscale() ? "native" : selectedExecutionMode();
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
  const workflow = selectedWorkflowRecord();
  if (workflow?.source === "custom") {
    const limits = { image: 0, video: 0, audio: 0 };
    const mappings = workflow.reference_mappings || [];
    const slotKinds = new Set(mappings.filter((mapping) => mapping.slot).map((mapping) => mapping.type));
    mappings.forEach((mapping) => {
      limits[mapping.type] = Math.max(limits[mapping.type] || 0, Number(mapping.index) || 0);
    });
    Object.keys(limits).forEach((kind) => {
      limits[kind] = Math.min(limits[kind], REFERENCE_LIMITS[kind] || 15);
    });
    // A slot family materialises loaders on demand, but the model still has
    // official per-media caps: 9 images, 3 videos and 3 audio clips.
    slotKinds.forEach((kind) => { limits[kind] = REFERENCE_LIMITS[kind] || 15; });
    return limits;
  }
  if (isMusic3(variant)) return { image: 0, video: 0, audio: 0 };
  if (isUpscale()) return { image: 1, video: 1, audio: 0 };
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
    if (selectedWorkflowRecord()?.source === "custom") return localized(`${kind} ${counts[kind]}`, `${kind} ${counts[kind]}`);
    if (isUpscale(executionMode)) return kind === "video" ? localized("输入视频", "Input video") : localized("输入图片", "Input image");
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
  const workflow = selectedWorkflowRecord();
  if (workflow?.source === "custom") {
    const counts = { image: 0, video: 0, audio: 0 };
    references.forEach((item) => { counts[item.kind || item.type] = (counts[item.kind || item.type] || 0) + 1; });
    const mappings = new Map((workflow.reference_mappings || []).map((item) => [`${item.type}:${item.index}`, item]));
    const slotKinds = new Set((workflow.reference_mappings || []).filter((item) => item.slot).map((item) => item.type));
    for (const [key, mapping] of mappings) {
      if (!mapping.required) continue;
      // A slot binding covers the whole family; only one file of that kind is
      // required, regardless of which index the binding uses.
      if (mapping.slot && (counts[mapping.type] || 0) >= 1) continue;
      if (!mapping.slot && counts[mapping.type] < mapping.index) {
        return localized(`请添加第 ${mapping.index} 个 ${mapping.type} 参考素材`, `Add reference ${mapping.index} for ${mapping.type}`);
      }
      if (mapping.slot) {
        return localized(`请添加至少 1 个 ${mapping.type} 参考素材`, `Add at least one ${mapping.type} reference`);
      }
    }
    for (const [kind, count] of Object.entries(counts)) {
      const limit = REFERENCE_LIMITS[kind] || 15;
      if (count > limit) {
        const kindName = { image: localized("图片", "images"), video: localized("视频", "videos"), audio: localized("音频", "audio") }[kind] || kind;
        return localized(`${kindName}参考素材最多添加 ${limit} 份`, `This workflow accepts up to ${limit} ${kindName}`);
      }
      for (let index = 1; index <= count; index += 1) {
        if (!mappings.has(`${kind}:${index}`) && !slotKinds.has(kind)) {
          return localized(`${kind} ${index} 没有配置到工作流输入`, `${kind} reference ${index} is not mapped`);
        }
      }
    }
    return "";
  }
  if (isMusic3(variant)) return references.length ? localized("Music3 不使用参考素材", "Music3 does not use reference files") : "";
  if (isUpscale()) {
    const expectedType = upscaleMediaType();
    if (references.length !== 1 || !["image", "video"].includes(references[0]?.kind || references[0]?.type) || (expectedType && (references[0]?.kind || references[0]?.type) !== expectedType)) {
      return localized("超分任务需要添加 1 张图片或 1 段视频", "Super-resolution requires one image or one video");
    }
    return "";
  }
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
  const headers = new Headers(options.headers || {});
  headers.set("Accept-Language", state.locale === "en" ? "en-US,en;q=0.9" : "zh-CN");
  if (state.incognito && !headers.has("X-H3-Incognito-Code")) headers.set("X-H3-Incognito-Code", state.incognitoCode);
  const response = await fetch(url, { cache: "no-store", ...options, headers });
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  if (!response.ok) {
    const detail = payload.detail;
    if (Array.isArray(detail)) {
      const fieldSeparator = state.locale === "en" ? ": " : "：";
      const messageSeparator = state.locale === "en" ? "; " : "；";
      const message = detail.map((item) => {
        const field = Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(".") : "";
        return field ? `${field}${fieldSeparator}${item.msg}` : item.msg;
      }).filter(Boolean).join(messageSeparator);
      throw new Error(message || localized(`请求失败 (${response.status})`, `Request failed (${response.status})`));
    }
    throw new Error(typeof detail === "string" ? detail : localized(`请求失败 (${response.status})`, `Request failed (${response.status})`));
  }
  return payload;
}

function updateModelUi() {
  renderWorkflowOptions();
  const runningHubNode = selectedRunningHubNode();
  const runningHub = Boolean(runningHubNode?.runninghub_schema);
  const selectedWorkflow = selectedWorkflowRecord();
  const customWorkflow = selectedWorkflow?.source === "custom" && !runningHubNode;
  const upscale = !runningHub && isUpscale();
  syncRunningHubSchema();
  el("workflowControl").hidden = Boolean(runningHubNode);
  el("workflowSelect").required = !runningHubNode;
  el("runningHubWorkflowControl").hidden = !runningHubNode;
  promptInput.hidden = false;
  if (customWorkflow) {
    const mappings = selectedWorkflow.field_mappings || {};
    const fields = new Set(Object.keys(mappings));
    const references = selectedWorkflow.reference_mappings || [];
    const kinds = [...new Set(references.map((item) => item.type))];
    promptInput.hidden = !fields.has("prompt");
    el("lyrics").hidden = !fields.has("lyrics");
    el("addReference").hidden = references.length === 0;
    referenceInput.accept = kinds.map((kind) => `${kind}/*`).join(",");
    el("addReference").title = state.locale === "en" ? `Add ${kinds.join(", ") || ""} references` : `添加${kinds.join("、") || ""}参考素材`;
    el("addReference").setAttribute("aria-label", el("addReference").title);
    const showAspect = fields.has("width") || fields.has("height") || fields.has("ratio");
    const showResolution = fields.has("width") || fields.has("height") || fields.has("megapixels");
    el("aspectControl").hidden = !showAspect;
    el("resolutionControl").hidden = !showResolution;
    el("duration").closest(".duration-control").hidden = !(fields.has("duration") || fields.has("num_frames"));
    el("duration").disabled = false;
    el("duration").min = "1";
    el("duration").max = "300";
    el("stepsControl").hidden = !fields.has("steps");
    el("steps").disabled = false;
    el("steps").min = "1";
    el("steps").max = "1000";
    el("stepsControl").title = localized("采样步数", "Sampling steps");
    const customDurationControl = el("duration").closest(".duration-control");
    customDurationControl.classList.remove("digital-human", "h3-sa");
    customDurationControl.title = localized("视频时长", "Video duration");
    el("durationHint").hidden = true;
    el("globalSeedControl").hidden = !fields.has("seed");
    el("autoUpscaleControl").hidden = true;
    el("autoUpscale").checked = false;
    el("autoUpscale").disabled = true;
    el("upscaleCategoryControl").hidden = true;
    el("upscaleScaleControl").hidden = true;
    el("saSettings").hidden = true;
    el("optimizePrompt").hidden = !fields.has("prompt");
    el("optimizePrompt").title = localized("优化提示词", "Optimize prompt");
    el("optimizePrompt").setAttribute("aria-label", el("optimizePrompt").title);
    el("optimizePromptLabel").textContent = el("optimizePrompt").title;
    el("writeLyrics").hidden = true;
    el("lyrics").placeholder = localized(
      "输入该工作流需要的歌词或文本…",
      "Enter the lyrics or text this workflow needs...",
    );
  el("dropZone").classList.remove("music3-mode");
    el("prompt").placeholder = state.locale === "en" ? "Enter a prompt for this workflow..." : "输入工作流提示词…";
    el("dropZone").title = "";
    renderReferences();
    showError(state.references.length ? validateReferenceSet(state.references) : "");
    return;
  }
  el("lyrics").hidden = !isMusic3();
  if (isMusic3()) {
    el("lyrics").placeholder = localized(
      "输入歌词，使用 [Intro]、[Verse]、[Chorus]、[Bridge]、[Instrumental]、[Outro] 等段落标签",
      "Enter lyrics using [Intro], [Verse], [Chorus], [Bridge], [Instrumental], and [Outro] sections",
    );
  }
  el("dropZone").classList.toggle("music3-mode", isMusic3() && !upscale && !runningHub);
  el("upscaleCategoryControl").hidden = !upscale;
  el("upscaleScaleControl").hidden = !upscale;
  el("runningHubWorkflowName").textContent = runningHubNode
    ? `${runningHubNode.workflow_name || runningHubNode.name} · ${runningHubNode.runninghub_resource_type === "ai-app" ? "AI App" : "Workflow"}`
    : "";
  const music3 = !runningHub && isMusic3() && !upscale;
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
  const autoUpscaleAllowed = !runningHub && !upscale && !music3 && !tts;
  el("autoUpscaleControl").hidden = !autoUpscaleAllowed;
  el("autoUpscale").disabled = !autoUpscaleAllowed;
  if (!autoUpscaleAllowed) el("autoUpscale").checked = false;
  const fl2vaOption = el("modelVariant").querySelector('option[value="fl2va-fp8"]');
  fl2vaOption.disabled = nsfw || digitalHuman || tts || dualSampling;
  if (nsfw || digitalHuman || tts || dualSampling) el("modelVariant").value = "ref2va-fp8";
  el("modelVariant").disabled = digitalHuman || tts || dualSampling;
  const ref2va = isRef2VA();
  const accelerated = selectedExecutionMode() === "turbo-lora";
  const turboSteps = selectedTurboSteps();
  const stepsMode = el("steps").dataset.mode;
  const nextStepsMode = upscale ? "upscale" : music3 ? "music3" : vdnH3 ? "vdn-h3" : accelerated ? `turbo-${turboSteps}` : "h3";
  if (stepsMode !== nextStepsMode) {
    el("steps").value = upscale ? "1" : music3 ? "30" : vdnH3 ? "50" : accelerated ? String(turboSteps) : "10";
    el("steps").dataset.mode = nextStepsMode;
  }
  el("steps").min = upscale ? "1" : vdnH3 ? "8" : "4";
  el("steps").max = upscale ? "1" : "50";
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
  if (upscale || music3 || digitalHuman || h3Sa) {
    el("steps").value = upscale ? "1" : music3 ? "30" : digitalHuman ? "20" : "8";
  } else if (vdnH3) {
    const vdnSteps = Number(el("steps").value);
    if (!Number.isInteger(vdnSteps) || vdnSteps < 8 || vdnSteps > 50) el("steps").value = "50";
  }
  el("steps").disabled = upscale || music3 || digitalHuman || h3Sa || runningHub;
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
    : music3 ? "" : upscale ? upscaleMediaType() === "image" ? "image/*" : upscaleMediaType() === "video" ? "video/*" : "image/*,video/*" : tts ? "audio/*" : digitalHuman ? "image/*,audio/*" : dualSampling ? "image/*" : ref2va ? "image/*,video/*,audio/*" : "image/*";
  el("addReference").title = state.locale === "en"
    ? runningHub ? "Add a workflow input file" : upscale ? "Add one image or video" : tts ? "Add up to three character voice references" : digitalHuman ? "Add portrait and driving audio" : dualSampling ? "Add image references for dual sampling" : ref2va ? "Add image, video, or audio references" : "Add first or last frame"
    : runningHub ? "添加工作流输入文件" : upscale ? "添加一张图片或一段视频" : tts ? "添加最多 3 段人物音频参考" : digitalHuman ? "添加人物图片和驱动音频" : dualSampling ? "添加双采图片参考" : ref2va ? "添加图片、视频或音频参考" : "添加首帧或尾帧";
  el("addReference").setAttribute("aria-label", el("addReference").title);
  el("addReference").hidden = music3 || (runningHub && runningHubKinds.size === 0);
  el("aspectControl").hidden = upscale || music3 || tts || runningHub;
  el("resolutionControl").hidden = upscale || music3 || tts || runningHub;
  el("duration").closest(".duration-control").hidden = runningHub || upscale;
  el("stepsControl").hidden = runningHub || h3Sa || upscale;
  el("lyrics").hidden = !music3;
  el("globalSeedControl").hidden = runningHub || upscale;
  // SA tuning uses the validated server defaults. Keep the controls in the
  // DOM for backward-compatible saved settings, but do not expose them.
  el("saSettings").hidden = true;
  el("stepsControl").title = state.locale === "en" ? music3 ? "Music3 uses 30 steps" : h3Sa ? "H3 SA uses 8 LoRA steps" : vdnH3 ? "VDN-H3 uses 8 to 50 steps; default 50" : "Sampling steps" : music3 ? "Music3 固定使用 30 步" : h3Sa ? "H3 SA 固定使用 8 步 LoRA" : vdnH3 ? "VDN-H3 可使用 8–50 步，默认 50 步" : "采样步数";
  el("optimizePrompt").hidden = runningHub || upscale;
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
      ? upscale ? "Optional note for the super-resolution task..." : music3 ? "Describe genre, mood, tempo, key, instruments, vocals, and arrangement..." : tts ? "Describe each speaker's age, personality, delivery, and exact dialogue..." : "Describe the scene, characters, action, camera, and sound..."
      : upscale ? "可选，填写超分任务说明…" : music3 ? "描述曲风、情绪、速度、调式、乐器、人声与编曲…" : tts ? "描述人物年龄、性格、说话方式和需要生成的完整对白…" : "输入自然语言，描述场景、人物、动作、镜头与声音…";
  el("dropZone").title = localized("可拖入本地文件或素材库生成产物", "Drop local files or generated assets from the library");
  renderReferences();
  const error = validateReferenceSet(state.references);
  showError(state.references.length ? error : "");
}

const REFERENCE_IMAGE_LIMIT = 1024 * 1024;
const REFERENCE_IMAGE_MAX_EDGE = 2560;

function canvasToBlob(canvas, type, quality) {
  return new Promise((resolve) => canvas.toBlob(resolve, type, quality));
}

function fileNameWithExtension(fileName, extension) {
  const base = String(fileName || "reference").replace(/\.[^.]+$/, "") || "reference";
  return `${base}.${extension}`;
}

function updateReferenceProcessingUi() {
  const status = el("referenceProcessingStatus");
  status.hidden = !state.referenceProcessing;
  status.textContent = state.referenceProcessing
    ? localized("正在压缩大尺寸图片…", "Compressing large reference images…")
    : "";
  el("addReference").disabled = state.referenceProcessing || Boolean(state.editingJobId);
  renderReferences();
}

async function compressLargeReferenceImage(file) {
  const extension = file.name.split(".").pop()?.toLowerCase();
  const inputType = file.type || ({ jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", webp: "image/webp", bmp: "image/bmp" }[extension] || "");
  if (
    !state.generalSettings.auto_compress_large_images
    || file.size <= REFERENCE_IMAGE_LIMIT
    || !["image/jpeg", "image/png", "image/webp", "image/bmp"].includes(inputType)
    || typeof createImageBitmap !== "function"
  ) return { file, compressed: false };

  let bitmap;
  try {
    bitmap = await createImageBitmap(file);
    let scale = Math.min(1, REFERENCE_IMAGE_MAX_EDGE / Math.max(bitmap.width, bitmap.height));
    let quality = 0.9;
    let bestBlob = null;
    const outputType = inputType === "image/jpeg" ? "image/jpeg" : "image/webp";
    for (let attempt = 0; attempt < 14; attempt += 1) {
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(bitmap.width * scale));
      canvas.height = Math.max(1, Math.round(bitmap.height * scale));
      const context = canvas.getContext("2d", { alpha: outputType !== "image/jpeg" });
      if (!context) break;
      context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      const blob = await canvasToBlob(canvas, outputType, quality);
      if (blob && (!bestBlob || blob.size < bestBlob.size)) bestBlob = blob;
      if (blob && blob.size <= REFERENCE_IMAGE_LIMIT) {
        const resultType = blob.type || outputType;
        const outputExtension = resultType === "image/jpeg" ? "jpg" : resultType === "image/png" ? "png" : "webp";
        return {
          file: new File([blob], fileNameWithExtension(file.name, outputExtension), {
            type: resultType,
            lastModified: file.lastModified,
          }),
          compressed: true,
          originalSize: file.size,
        };
      }
      if (quality > 0.7) quality = Math.max(0.7, quality - 0.08);
      else {
        scale *= 0.82;
        quality = 0.88;
      }
      if (scale < 0.18) break;
    }
    if (bestBlob && bestBlob.size < file.size && bestBlob.size <= REFERENCE_IMAGE_LIMIT) {
      const resultType = bestBlob.type || outputType;
      const outputExtension = resultType === "image/jpeg" ? "jpg" : resultType === "image/png" ? "png" : "webp";
      return {
        file: new File([bestBlob], fileNameWithExtension(file.name, outputExtension), {
          type: resultType,
          lastModified: file.lastModified,
        }),
        compressed: true,
        originalSize: file.size,
      };
    }
    return { file, compressed: false, warning: true };
  } catch {
    return { file, compressed: false, warning: true };
  } finally {
    bitmap?.close();
  }
}

async function addFiles(files, forcedFieldKey = "") {
  const selectedFiles = Array.from(files || []);
  if (state.editingJobId) {
    showError(localized("修改排队任务时不能更换参考素材", "Reference files cannot be changed while editing a queued task"));
    return false;
  }
  if (state.referenceProcessing) return false;
  const largeImages = selectedFiles.some((file) => (
    kindFor(file) === "image" && file.size > REFERENCE_IMAGE_LIMIT
    && state.generalSettings.auto_compress_large_images
  ));
  if (!largeImages) return addPreparedFiles(selectedFiles, forcedFieldKey);

  const generateWasDisabled = el("generateButton").disabled;
  el("generateButton").disabled = true;
  state.referenceProcessing = true;
  updateReferenceProcessingUi();
  const prepared = [];
  const compressed = [];
  let compressionWarning = false;
  try {
    for (const file of selectedFiles) {
      const result = await compressLargeReferenceImage(file);
      prepared.push(result.file);
      if (result.compressed) compressed.push(result);
      compressionWarning ||= Boolean(result.warning);
    }
  } finally {
    state.referenceProcessing = false;
    updateReferenceProcessingUi();
    el("generateButton").disabled = generateWasDisabled;
  }
  const added = addPreparedFiles(prepared, forcedFieldKey);
  if (added && compressed.length) {
    const details = compressed.map((item) => `${formatBytes(item.originalSize)} → ${formatBytes(item.file.size)}`);
    showToast(localized(
      `已压缩 ${compressed.length} 张参考图片：${details.join("，")}`,
      `Compressed ${compressed.length} reference image${compressed.length === 1 ? "" : "s"}: ${details.join(", ")}`,
    ));
  }
  if (compressionWarning) {
    showToast(localized("部分图片未能压缩，已保留原文件", "Some images could not be compressed; original files were kept"));
  }
  return added;
}

function addPreparedFiles(files, forcedFieldKey = "") {
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
      error = selectedWorkflowRecord()?.source === "custom"
        ? localized(`工作流没有配置 ${kind} 参考素材`, `This workflow has no ${kind} reference mapping`)
        : isTTS()
        ? localized(`H3 TTS 仅支持音频参考：${file.name}`, `H3 TTS accepts audio references only: ${file.name}`)
        : isDigitalHuman()
        ? localized(`数字人模式仅支持人物图片和驱动音频：${file.name}`, `Digital human mode only accepts a portrait and driving audio: ${file.name}`)
        : localized(`FL2VA 仅支持图片：${file.name}`, `FL2VA only accepts images: ${file.name}`);
      return;
    }
    if (current >= limits[kind]) {
      error = selectedWorkflowRecord()?.source === "custom"
        ? localized(`${kind} 参考素材最多添加 ${limits[kind]} 份`, `This workflow accepts up to ${limits[kind]} ${kind} references`)
        : isTTS()
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
  const processingStatus = el("referenceProcessingStatus");
  if (processingStatus) {
    processingStatus.hidden = !state.referenceProcessing;
    processingStatus.textContent = state.referenceProcessing
      ? localized("正在压缩大尺寸图片…", "Compressing large reference images…")
      : "";
  }
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
      ? `<a href="${escapeHtml(item.url)}" class="reference-link" data-preview-url="${escapeHtml(item.url)}" data-preview-name="${escapeHtml(name)}" data-preview-type="${escapeHtml(kind)}" aria-label="${localized("预览", "Preview")} ${escapeHtml(name)}">${media}</a>`
      : media;
    return `<div class="reference-chip" title="${escapeHtml(name)}">
      <span class="reference-preview">${thumb}</span>
      <span class="reference-info"><b>${escapeHtml(labels[index])}</b><small>${escapeHtml(name)}${item.size ? ` · ${formatBytes(item.size)}` : ""}</small></span>
      ${item.remote ? "" : `<button type="button" data-remove-reference="${index}" title="${localized("移除素材", "Remove file")}" aria-label="${localized("移除素材", "Remove file")}">${icon("x")}</button>`}
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

function currentMegapixels() {
  const preset = RESOLUTION_PRESETS.find((item) => item.value === el("resolution").value) || RESOLUTION_PRESETS[2];
  const labelled = Number((preset.label.match(/^([0-9.]+) MP/) || [])[1]);
  if (Number.isFinite(labelled)) return labelled;
  return Number((preset.width * preset.height / 1_000_000).toFixed(2));
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
    if (data.platform) state.platform = data.platform;
    renderHealthState(data.nodes || [], data.queue_depth || 0);
  } catch {
    el("healthDot").className = "status-dot offline";
    el("healthText").textContent = t("offline");
  }
}

function renderAssetFolders() {
  el("assetEditToolbar").hidden = !state.assetEditMode;
  updateAssetSelectionChrome();
  renderAssets();
  refreshIcons();
}

function folderGlyph(kind = "folder") {
  return `<span class="folder-glyph ${escapeHtml(kind)}" aria-hidden="true"></span>`;
}

function folderBackGlyph() {
  return `<span class="folder-back-glyph" aria-hidden="true">${icon("corner-up-left")}</span>`;
}

function renderAssetFolderCard(folder) {
  const actions = `<span class="asset-actions asset-folder-actions"><button type="button" data-folder-action="rename" data-folder-id="${escapeHtml(folder.id)}" title="${t("renameFolder")}" aria-label="${t("renameFolder")}">${icon("pencil")}</button><button type="button" data-folder-action="delete" data-folder-id="${escapeHtml(folder.id)}" title="${t("deleteFolder")}" aria-label="${t("deleteFolder")}">${icon("trash-2")}</button></span>`;
  return `<article class="asset-card asset-folder-card${state.assetFolderId === folder.id ? " active" : ""}" data-asset-folder-card="${escapeHtml(folder.id)}" data-folder-drop-id="${escapeHtml(folder.id)}" tabindex="0" role="button" aria-label="${escapeHtml(folder.name)}">
    <div class="asset-folder-preview">${folderGlyph("folder")}</div>
    <div class="asset-folder-meta"><strong title="${escapeHtml(folder.name)}">${escapeHtml(folder.name)}</strong><small>${Number(folder.count || 0)} ${localized("项素材", Number(folder.count || 0) === 1 ? "asset" : "assets")}</small>${actions}</div>
  </article>`;
}

function renderAssetFolderCards() {
  if (state.assetFolderId) {
    return `<article class="asset-folder-card back" data-asset-folder-back="true" tabindex="0" role="button" aria-label="${localized("返回上一级", "Back")}">
      ${folderBackGlyph()}<span>${localized("返回上一级", "Back")}</span>
    </article>`;
  }
  return state.assetFolders.map(renderAssetFolderCard).join("");
}

async function loadAssetFolders() {
  if (state.incognito) {
    state.assetFolders = [];
    state.assetUnfiledFolder = { id: "__unfiled__", name: t("unfiled"), count: 0 };
    state.assetFolderId = "";
    renderAssetFolders();
    return;
  }
  const payload = await api("/api/v1/asset-folders");
  state.assetFolders = payload.data || [];
  state.assetUnfiledFolder = payload.unfiled || { id: "__unfiled__", name: t("unfiled"), count: 0 };
  if (state.assetFolderId && state.assetFolderId !== "__unfiled__" && !state.assetFolders.some((folder) => folder.id === state.assetFolderId)) {
    state.assetFolderId = "";
  }
  renderAssetFolders();
}

function updateAssetSelectionChrome() {
  const count = state.assetSelectedIds.size;
  const label = count ? `${t("selectedAssets")} ${count}` : t("noSelection");
  if (el("assetSelectionCount")) el("assetSelectionCount").textContent = label;
  if (el("moveSelectedAssets")) el("moveSelectedAssets").disabled = count === 0;
  if (el("editAssetsButton")) {
    el("editAssetsButton").setAttribute("aria-pressed", String(state.assetEditMode));
    el("editAssetsButton").title = state.assetEditMode ? t("exitAssetEdit") : t("editAssets");
    el("editAssetsButton").setAttribute("aria-label", el("editAssetsButton").title);
  }
}

function setAssetEditMode(enabled) {
  state.assetEditMode = Boolean(enabled);
  if (!state.assetEditMode) state.assetSelectedIds.clear();
  renderAssetFolders();
  renderAssets();
}

function selectAssetFolder(folderId) {
  if (state.assetFolderId === folderId) return;
  state.assetFolderId = folderId;
  state.assetSelectedIds.clear();
  renderAssetFolders();
  loadAssets({ reset: true }).catch((error) => showError(error.message));
}

function openAssetFolderName(folderId = null) {
  state.assetFolderNameEditId = folderId;
  const folder = folderId ? state.assetFolders.find((item) => item.id === folderId) : null;
  el("assetFolderNameTitle").textContent = folder ? t("renameFolder") : t("newFolder");
  el("assetFolderNameHint").textContent = t("folderPurpose");
  el("assetFolderName").value = folder?.name || "";
  el("assetFolderNameError").textContent = "";
  el("assetFolderNameModal").hidden = false;
  document.body.classList.add("modal-open");
  refreshIcons();
  requestAnimationFrame(() => el("assetFolderName").focus());
}

function closeAssetFolderName() {
  el("assetFolderNameModal").hidden = true;
  state.assetFolderNameEditId = null;
  if (el("assetFolderPickerModal").hidden && el("assetDetailModal").hidden) document.body.classList.remove("modal-open");
}

function renderAssetFolderPicker() {
  const folders = [{ id: "__unfiled__", name: t("unfiled"), icon: "inbox" }, ...state.assetFolders.map((folder) => ({ ...folder, icon: "folder" }))];
  el("assetFolderPickerList").innerHTML = folders.map((folder) => `<button type="button" class="asset-folder-picker-row" data-picker-folder-id="${escapeHtml(folder.id)}">${folderGlyph(folder.id === "__unfiled__" ? "unfiled" : "folder")}<span>${escapeHtml(folder.name)}</span></button>`).join("");
  refreshIcons();
}

function pickAssetFolder(title = t("moveTo"), hint = "") {
  el("assetFolderPickerTitle").textContent = title;
  el("assetFolderPickerHint").textContent = hint || localized("选择素材的目标文件夹", "Choose the destination folder");
  el("assetFolderPickerError").textContent = "";
  renderAssetFolderPicker();
  el("assetFolderPickerModal").hidden = false;
  document.body.classList.add("modal-open");
  return new Promise((resolve) => {
    state.assetFolderPickerResolve = resolve;
  });
}

function resolveAssetFolderPicker(value) {
  const resolve = state.assetFolderPickerResolve;
  state.assetFolderPickerResolve = null;
  el("assetFolderPickerModal").hidden = true;
  if (el("assetFolderNameModal").hidden && el("assetDetailModal").hidden) document.body.classList.remove("modal-open");
  if (resolve) resolve(value);
}

function closeAssetFolderPicker() {
  if (!el("assetFolderPickerModal").hidden) resolveAssetFolderPicker(undefined);
}

async function moveSelectedAssets() {
  const jobIds = Array.from(state.assetSelectedIds);
  if (!jobIds.length) return;
  const folderId = await pickAssetFolder(t("moveTo"));
  if (folderId === undefined) return;
  await moveJobsToFolder(jobIds, folderId === "__unfiled__" ? null : folderId);
}

async function moveJobsToFolder(jobIds, folderId) {
  try {
    await api("/api/v1/asset-folders/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_ids: jobIds, folder_id: folderId || null }),
    });
    state.assetSelectedIds.clear();
    await Promise.all([loadAssetFolders(), loadAssets({ reset: true })]);
  } catch (error) {
    showError(error.message);
  }
}

async function deleteAssetFolder(folderId) {
  if (!window.confirm(t("folderDeleteConfirm"))) return;
  try {
    await api(`/api/v1/asset-folders/${encodeURIComponent(folderId)}`, { method: "DELETE" });
    if (state.assetFolderId === folderId) state.assetFolderId = "";
    if (state.localAssetFolderId === folderId) state.localAssetFolderId = "__root__";
    await Promise.all([loadAssetFolders(), loadAssets({ reset: true }), refreshConversation(true)]);
  } catch (error) {
    if (el("localAssetsError")) el("localAssetsError").textContent = error.message;
    showToast(error.message, "error");
  }
}

async function loadAssets({ reset = false } = {}) {
  if (state.assetLoading || (!reset && !state.assetHasMore)) return;
  const requestedPage = reset ? 1 : state.assetPage + 1;
  const params = new URLSearchParams({ page: requestedPage, page_size: state.assetPageSize, scope: jobScope() });
  if (state.assetFolderId) params.set("folder_id", state.assetFolderId);
  else if (!state.incognito) params.set("folder_id", "__root__");
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
    const filteredData = (payload.data || []).filter(assetMatchesCurrentView);
    state.assets = reset ? filteredData : dedupeJobs([...state.assets, ...filteredData]);
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

async function ensureAssetGridFilled() {
  const grid = el("assetGrid");
  if (!grid || state.assetLoading || !state.assetHasMore) return;
  if (grid.scrollHeight - grid.scrollTop - grid.clientHeight >= 180) return;
  await loadAssets();
}

function canVideoUpscale(job) {
  return job.status === "completed" && Boolean(job.result_url) && jobMediaType(job) === "video";
}

function videoUpscaleAction(job) {
  if (!canVideoUpscale(job)) return "";
  const jobId = escapeHtml(job.id);
  return `<button type="button" data-job-action="video-upscale" data-job-id="${jobId}" title="${t("videoUpscale")}" aria-label="${t("videoUpscale")}">${icon("expand")}</button>`;
}

function videoUpscaleMessageAction(job) {
  if (!canVideoUpscale(job)) return "";
  return `<button type="button" data-job-action="video-upscale" data-job-id="${escapeHtml(job.id)}">${icon("expand")}<span>${t("videoUpscale")}</span></button>`;
}

function assetAction(job) {
  const jobId = escapeHtml(job.id);
  if (job.peer_asset) {
    const inputAction = job.status === "completed" && job.result_url
      ? `<button type="button" data-asset-input="${jobId}" title="${t("useAsInput")}" aria-label="${t("useAsInput")}">${icon("file-input")}</button>`
      : "";
    const upscaleAction = videoUpscaleAction(job);
    return inputAction || upscaleAction ? `<span class="asset-actions">${inputAction}${upscaleAction}</span>` : "";
  }
  if (job.status === "queued") {
    return `<span class="asset-actions"><button type="button" data-job-action="edit" data-job-id="${jobId}" title="${localized("修改", "Edit")}" aria-label="${localized("修改", "Edit")}">${icon("pencil")}</button><button type="button" data-job-action="cancel" data-job-id="${jobId}" title="${localized("取消", "Cancel")}" aria-label="${localized("取消", "Cancel")}">${icon("square")}</button></span>`;
  }
  if (job.status === "running") {
    return `<span class="asset-actions"><button type="button" data-job-action="cancel" data-job-id="${jobId}" title="${localized("取消", "Cancel")}" aria-label="${localized("取消", "Cancel")}">${icon("square")}</button></span>`;
  }
  const inputAction = job.status === "completed" && job.result_url
    ? `<button type="button" data-asset-input="${jobId}" title="${t("useAsInput")}" aria-label="${t("useAsInput")}">${icon("file-input")}</button>`
    : "";
  return `<span class="asset-actions">${inputAction}${videoUpscaleAction(job)}<button type="button" data-job-action="delete" data-job-id="${jobId}" title="${t("delete")}" aria-label="${t("delete")}">${icon("trash-2")}</button></span>`;
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
        : `<video src="${escapeHtml(job.preview_url || job.result_url)}" muted playsinline preload="none" aria-label="${escapeHtml(modelLabel(job))} ${localized("生成视频", "generated video")}"></video><span class="asset-play">${icon("play")}</span>`
    : `<span class="asset-placeholder ${job.status}">${icon(job.status === "running" ? "loader-circle" : job.status === "queued" ? "clock-3" : job.status === "failed" ? "triangle-alert" : "circle-slash-2")}${job.status === "running" ? `<b>${job.progress || 0}%</b>` : ""}</span>`;
  const editable = state.assetEditMode && !job.peer_asset && !job.request?.incognito;
  const draggable = editable ? "true" : job.status === "completed" && job.result_url ? "true" : "false";
  const selected = state.assetSelectedIds.has(job.id);
  const select = editable
    ? `<label class="asset-select" data-asset-select><input type="checkbox" value="${escapeHtml(job.id)}" aria-label="${localized("选择", "Select")} ${escapeHtml(shortTitle(job))}" ${selected ? "checked" : ""}></label>`
    : "";
  const owner = job.owner_name ? `<span class="asset-owner" title="${t("owner")}: ${escapeHtml(job.owner_name)}">${icon("tag")}<span>${escapeHtml(job.owner_name)}</span></span>` : "";
  const renameAction = !job.peer_asset && job.status === "completed" && job.result_url
    ? `<button type="button" data-job-action="rename" data-job-id="${escapeHtml(job.id)}" title="${localized("重命名生成文件", "Rename generated file")}" aria-label="${localized("重命名生成文件", "Rename generated file")}">${icon("pencil")}</button>`
    : "";
  return `<article class="asset-card${editable ? " editable" : ""}${selected ? " selected" : ""}" data-asset-job="${escapeHtml(job.id)}" data-asset-output="${editable ? "false" : draggable}" data-asset-editable="${editable}" draggable="${draggable}" tabindex="0" aria-label="${escapeHtml(executionModeLabel(job))}, ${escapeHtml(modelLabel(job))}, ${escapeHtml(statusLabel(job.status))}">
    <div class="asset-preview${audio || mediaType === "file" ? " music" : ""}">${select}${preview}${assetAction(job)}</div>
    <div class="asset-meta${renameAction ? " has-rename" : ""}"><span class="task-status ${job.status}"></span><strong title="${escapeHtml(job.title || modelLabel(job))}">${escapeHtml(shortTitle(job))}</strong><small class="asset-plan ${executionModeClass(job)}">${escapeHtml(executionModeLabel(job))}</small>${owner}<time>${escapeHtml(assetNodeLabel(job))}</time><time>${t("overallTime")} ${formatElapsed(job.elapsed_seconds)}</time>${renameAction}</div>
  </article>`;
}

function updateAssetChrome() {
  el("assetTotal").textContent = state.assetTotal;
}

function renderAssetDirectoryHeader() {
  if (!state.assetFolderId) return "";
  const folder = state.assetFolderId === "__unfiled__"
    ? state.assetUnfiledFolder
    : state.assetFolders.find((item) => item.id === state.assetFolderId);
  if (!folder) return "";
  const kind = state.assetFolderId === "__unfiled__" ? "unfiled" : "folder";
  return `<div class="asset-directory-header" data-directory-folder-id="${escapeHtml(state.assetFolderId)}">${folderGlyph(kind)}<span class="asset-directory-copy"><strong>${escapeHtml(folder.name)}</strong><small>${Number(folder.count || state.assetTotal)} ${localized("项素材", "assets")}</small></span></div>`;
}

function renderAssets(total = state.assetTotal) {
  state.assetTotal = total;
  const folderCards = renderAssetFolderCards();
  const cards = state.assets.map(renderAssetCard).join("");
  const empty = !state.assets.length && !state.assetLoading && !state.assetLoadError ? `<div class="library-empty">${icon("images")}<span>${t("noAssets")}</span></div>` : "";
  const error = state.assetLoadError ? `<p class="list-error">${escapeHtml(state.assetLoadError)}</p>` : "";
  const loadState = state.assetLoading
    ? `<div class="asset-load-state loading">${icon("loader-circle")}<span>${t("loading")}</span></div>`
    : state.assets.length && !state.assetHasMore
      ? `<div class="asset-load-state">${icon("check")}<span>${t("allLoaded")}</span></div>`
      : "";
  el("assetGrid").innerHTML = `${folderCards}${renderAssetDirectoryHeader()}${cards}${empty}${error}${loadState}`;
  updateAssetChrome();
  updateAssetSelectionChrome();
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
  if (!state.assetFolderId && job.peer_asset) return false;
  if (!state.assetFolderId && !job.peer_asset && job.folder_id) return false;
  if (state.assetFolderId === "__unfiled__" && (job.peer_asset || job.folder_id)) return false;
  if (state.assetFolderId && state.assetFolderId !== "__unfiled__" && (job.peer_asset || job.folder_id !== state.assetFolderId)) return false;
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
    const card = elementFromHtml(renderJobExchange(job));
    if (currentMessageStyle() === "grid") {
      el("conversationFeed").prepend(card);
      if (state.conversationScrollTop <= 24) el("conversationFeed").scrollTop = 0;
    } else {
      el("conversationFeed").append(card);
      el("conversationFeed").scrollTop = el("conversationFeed").scrollHeight;
    }
  }
  if (!state.conversations.length) el("conversationFeed").innerHTML = `${chatEmptyMarkup()}`;
  refreshIcons();
}

function conversationMatchesCurrentView(job) {
  if (Boolean(job.request?.incognito) !== state.incognito) return false;
  if (state.incognito || state.conversationDeviceIds.size === 0) return true;
  const ownerDeviceId = String(job.owner_device_id || job.source?.device_id || "");
  return state.conversationDeviceIds.has(ownerDeviceId);
}

function applyJobUpsert(job) {
  state.assetDetailWindows.forEach((record) => {
    if (record.jobId !== job.id || !record.node) return;
    record.job = job;
    renderAssetDetail(job, record.node);
  });
  if (!state.assetFolderId && !job.peer_asset && job.folder_id) {
    const staleIndex = state.assets.findIndex((item) => item.id === job.id);
    if (staleIndex >= 0) state.assets.splice(staleIndex, 1);
    jobElement(el("assetGrid"), "data-asset-job", job.id)?.remove();
    return upsertConversation(job);
  }
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
  if (!state.conversations.length) el("conversationFeed").innerHTML = `${chatEmptyMarkup()}`;
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
  select.innerHTML = devices.map((device) => `<option value="${escapeHtml(device.device_id)}">${escapeHtml(device.name)}${device.local ? ` · ${localized("本机", "This device")}` : ""}</option>`).join("");
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
    ? localized("全部", "All")
    : selected.length === 1
      ? selected[0].textContent
      : `${selected.length} ${localized("个设备", "devices")}`;
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
  const summaryExecutionMode = job.request?.task_type === "upscale"
    ? "video-upscale"
    : job.request?.execution_mode || "native";
  const labels = referenceLabels(
    references,
    job.request?.model_variant || "fl2va-fp8",
    summaryExecutionMode,
    job.request?.runninghub_schema || null,
  );
  if (!references.length) return "";
  return `<div class="message-assets">${references.map((item, index) => {
    const itemIcon = item.type === "image" ? "image" : item.type === "video" ? "film" : "audio-lines";
    const name = item.name || localized("参考素材", "Reference file");
    const url = item.url || `/api/v1/generations/${encodeURIComponent(job.id)}/references/${index}`;
    let preview = `<span class="message-asset-icon">${icon(itemIcon)}</span>`;
    if (item.type === "image") {
      preview = `<img src="${escapeHtml(url)}" alt="${escapeHtml(name)}" loading="lazy">`;
    } else if (item.type === "video") {
      preview = `<video src="${escapeHtml(url)}" controls playsinline preload="metadata" aria-label="${escapeHtml(name)}"></video>`;
    } else if (item.type === "audio") {
      preview = `<audio src="${escapeHtml(url)}" controls preload="metadata" aria-label="${escapeHtml(name)}"></audio>`;
    }
    return `<a class="message-asset" href="${escapeHtml(url)}" data-preview-url="${escapeHtml(url)}" data-preview-name="${escapeHtml(name)}" data-preview-type="${escapeHtml(item.type || "")}" rel="noreferrer" title="${localized("预览", "Preview")} ${escapeHtml(name)}">${preview}<span class="message-asset-copy"><b>${escapeHtml(labels[index])}</b><small>${escapeHtml(name)}</small></span></a>`;
  }).join("")}</div>`;
}

function messageDownloadAction(job) {
  if (job.status !== "completed" || !job.result_url) return "";
  const mediaType = jobMediaType(job);
  return `<a class="message-action-download" href="${escapeHtml(job.result_url)}" download>${icon("download")}<span>${mediaDownloadLabel(mediaType)}</span></a>`;
}

function messageActions(job) {
  if (job.peer_asset) return job.status === "completed" && job.result_url
    ? `<div class="message-actions">${messageDownloadAction(job)}<button type="button" data-job-action="input" data-job-id="${job.id}">${icon("file-input")}<span>${t("useAsInput")}</span></button>${videoUpscaleMessageAction(job)}</div>`
    : "";
  if (job.request?.remote_proxy) {
    const buttons = [messageDownloadAction(job)];
    if (job.status === "completed" && job.result_url) {
      buttons.push(`<button type="button" data-job-action="input" data-job-id="${job.id}">${icon("file-input")}<span>${t("useAsInput")}</span></button>`);
      if (canVideoUpscale(job)) buttons.push(videoUpscaleMessageAction(job));
    }
    if (isActive(job)) {
      buttons.push(`<button type="button" class="cancel" data-job-action="cancel" data-job-id="${job.id}">${icon("square")}<span>${t("cancel")}</span></button>`);
    } else {
      buttons.push(`<button type="button" class="danger" data-job-action="delete" data-job-id="${job.id}">${icon("trash-2")}<span>${t("delete")}</span></button>`);
    }
    return `<div class="message-actions">${buttons.join("")}</div>`;
  }
  const buttons = [messageDownloadAction(job), `<button type="button" data-job-action="reuse" data-job-id="${job.id}">${icon("corner-down-left")}<span>${t("reuse")}</span></button>`];
  if (job.status === "completed" && job.result_url) {
    buttons.push(`<button type="button" data-job-action="input" data-job-id="${job.id}">${icon("file-input")}<span>${t("useAsInput")}</span></button>`);
    if (canVideoUpscale(job)) buttons.push(videoUpscaleMessageAction(job));
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

function markdownInline(value) {
  let text = escapeHtml(value);
  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
  text = text.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  text = text.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/__([^_\n]+)__/g, "<strong>$1</strong>");
  text = text.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
  return text;
}

function markdownPlainText(value) {
  return String(value || "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/[*_`>#]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function renderMarkdown(value) {
  const lines = String(value || "").replace(/\r\n?/g, "\n").split("\n");
  const output = [];
  let paragraph = [];
  let listType = "";
  let quote = [];
  let code = null;
  const flushParagraph = () => {
    if (!paragraph.length) return;
    output.push(`<p>${paragraph.map(markdownInline).join("<br>")}</p>`);
    paragraph = [];
  };
  const closeList = () => {
    if (!listType) return;
    output.push(`</${listType}>`);
    listType = "";
  };
  const flushQuote = () => {
    if (!quote.length) return;
    output.push(`<blockquote>${quote.map(markdownInline).join("<br>")}</blockquote>`);
    quote = [];
  };
  const flushAll = () => {
    flushParagraph();
    closeList();
    flushQuote();
  };
  for (const line of lines) {
    if (code) {
      if (/^```/.test(line.trim())) {
        output.push(`<pre><code>${code.map(escapeHtml).join("\n")}</code></pre>`);
        code = null;
      } else {
        code.push(line);
      }
      continue;
    }
    if (/^```/.test(line.trim())) {
      flushAll();
      code = [];
      continue;
    }
    if (!line.trim()) {
      flushAll();
      continue;
    }
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      flushAll();
      const level = Math.min(4, heading[1].length);
      output.push(`<h${level}>${markdownInline(heading[2])}</h${level}>`);
      continue;
    }
    const quoteLine = line.match(/^>\s?(.*)$/);
    if (quoteLine) {
      flushParagraph();
      closeList();
      quote.push(quoteLine[1]);
      continue;
    }
    if (quote.length) flushQuote();
    const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+\.\s+(.+)$/);
    if (unordered || ordered) {
      flushParagraph();
      flushQuote();
      const type = ordered ? "ol" : "ul";
      if (listType !== type) {
        closeList();
        listType = type;
        output.push(`<${type}>`);
      }
      output.push(`<li>${markdownInline((ordered || unordered)[1])}</li>`);
      continue;
    }
    if (listType) closeList();
    paragraph.push(line);
  }
  if (code) output.push(`<pre><code>${code.map(escapeHtml).join("\n")}</code></pre>`);
  flushAll();
  return output.join("");
}

const MESSAGE_STYLE_STORAGE_KEY = "h3-message-style";
const MESSAGE_STYLES = [
  { id: "default", name: "默认", nameEn: "Default", note: "完整的对话与视频预览", noteEn: "Full conversation and media preview" },
  { id: "minimal", name: "极简", nameEn: "Minimal", note: "用紧凑横幅展示产出", noteEn: "Compact output banners" },
  { id: "grid", name: "宫格", nameEn: "Grid", note: "瀑布流封面与进度环", noteEn: "Masonry covers and progress rings" },
];

function normalizeMessageStyle(value) {
  return MESSAGE_STYLES.some((style) => style.id === value) ? value : "default";
}

function storedMessageStyle() {
  try {
    return normalizeMessageStyle(localStorage.getItem(MESSAGE_STYLE_STORAGE_KEY));
  } catch (error) {
    return "default";
  }
}

function currentMessageStyle() {
  return normalizeMessageStyle(state.messageStyle);
}

function renderMessageStyleOptions() {
  document.querySelectorAll("[data-message-style]").forEach((button) => {
    const active = button.dataset.messageStyle === currentMessageStyle();
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-checked", String(active));
  });
}

function applyMessageStyle(style, { persist = true, render = true } = {}) {
  state.messageStyle = normalizeMessageStyle(style);
  document.body.dataset.messageStyle = state.messageStyle;
  if (persist) {
    try { localStorage.setItem(MESSAGE_STYLE_STORAGE_KEY, state.messageStyle); } catch (error) { /* storage disabled */ }
  }
  renderMessageStyleOptions();
  if (render) renderConversationFeed(state.messageStyle === "grid" ? "bottom" : "preserve");
  return state.messageStyle;
}

function gridProgressRing(job) {
  const percent = Math.max(0, Math.min(100, Math.round(Number(job.progress) || 0)));
  return `<span class="grid-progress-ring" style="--progress:${percent * 3.6}deg"><span>${percent}%</span></span>`;
}

function jobCoverMarkup(job, { grid = false } = {}) {
  const mediaType = jobMediaType(job);
  const request = job.request || {};
  const completed = job.status === "completed" && job.result_url;
  if (completed) {
    if (mediaType === "image") {
      return `<img src="${escapeHtml(job.result_url)}" alt="${escapeHtml(shortTitle(job))}" loading="lazy">`;
    }
    if (mediaType === "video") {
      return `<video src="${escapeHtml(job.result_url)}#t=0.1" muted playsinline preload="metadata" aria-label="${escapeHtml(shortTitle(job))}"></video>`;
    }
    if (mediaType === "audio") return `<span class="grid-cover-audio">${icon("audio-lines")}</span>`;
  }
  const reference = (request.references || []).find((item) => item.type === "image");
  if (reference) {
    const index = request.references.indexOf(reference);
    const url = reference.url || `/api/v1/generations/${encodeURIComponent(job.id)}/references/${index}`;
    return `<img src="${escapeHtml(url)}" alt="${escapeHtml(reference.name || "reference")}" loading="lazy">`;
  }
  const iconName = mediaType === "audio" ? "audio-lines" : mediaType === "image" ? "image" : "sparkles";
  return `<span class="grid-cover-placeholder">${icon(iconName)}<b>H3</b></span>`;
}

function renderGridJobCard(job) {
  const request = job.request || {};
  const active = isActive(job);
  const progress = Math.max(0, Math.min(100, Math.round(Number(job.progress) || 0)));
  const title = job.error || job.stage || statusLabel(job.status);
  return `<article class="grid-job-card${active ? " is-loading" : ""}" data-job-id="${escapeHtml(job.id)}" data-grid-job="${escapeHtml(job.id)}" data-output-job-id="${escapeHtml(job.id)}" tabindex="0" role="button" aria-label="${escapeHtml(shortTitle(job))}">
    <div class="grid-job-cover">
      ${jobCoverMarkup(job, { grid: true })}
      ${active ? `<div class="grid-loading-mask"><span class="grid-progress-ring" style="--progress:${progress * 3.6}deg"><span>${progress}%</span></span><b>${escapeHtml(title)}</b></div>` : ""}
      <span class="grid-job-status ${escapeHtml(job.status)}">${escapeHtml(statusLabel(job.status))}</span>
    </div>
    <div class="grid-job-copy">
      <p>${escapeHtml(markdownPlainText(request.prompt || request.runninghub_workflow_name || shortTitle(job)))}</p>
      <small>${escapeHtml(executionModeLabel(job))}${job.status === "completed" ? ` · ${formatTime(job.created_at, true)}` : ""}</small>
    </div>
  </article>`;
}

function minimalOutputBanner(job, detail) {
  const mediaType = jobMediaType(job);
  const active = isActive(job);
  const completed = job.status === "completed" && job.result_url;
  const thumb = completed
    ? mediaType === "image"
      ? `<img src="${escapeHtml(job.result_url)}" alt="" loading="lazy">`
      : mediaType === "video"
        ? `<video src="${escapeHtml(job.result_url)}#t=0.1" muted playsinline preload="metadata"></video>`
        : `<span class="message-output-icon">${icon("audio-lines")}</span>`
    : `<span class="message-output-icon">${icon(active ? "loader-circle" : "file-question")}</span>`;
  const progress = active
    ? `<span class="minimal-progress-track"><span style="width:${Math.max(0, Math.min(100, job.progress || 0))}%"></span></span>`
    : "";
  return `<button type="button" class="message-output-banner${active ? " is-loading" : ""}" data-output-detail="${escapeHtml(job.id)}">
    <span class="message-output-thumb">${thumb}</span>
    <span class="message-output-copy"><b>${escapeHtml(statusLabel(job.status))}</b><small>${escapeHtml(detail || executionModeLabel(job))}</small>${progress}</span>
    <span class="message-output-open">${icon("chevron-right")}</span>
  </button>`;
}

const OPTIMIZE_MARKDOWN_STORAGE_KEY = "h3-optimize-markdown";

function renderMessageText(value) {
  const text = String(value || "");
  if (state.optimizeMarkdown !== false) return renderMarkdown(text);
  return `<p>${escapeHtml(text).replace(/\n/g, "<br>")}</p>`;
}

function applyMarkdownOptimization(enabled, { persist = true, render = true } = {}) {
  state.optimizeMarkdown = enabled !== false;
  const checkbox = el("optimizeMarkdown");
  if (checkbox) checkbox.checked = state.optimizeMarkdown;
  document.body.dataset.optimizeMarkdown = state.optimizeMarkdown ? "on" : "off";
  if (persist) {
    try { localStorage.setItem(OPTIMIZE_MARKDOWN_STORAGE_KEY, state.optimizeMarkdown ? "1" : "0"); } catch (error) { /* storage disabled */ }
  }
  if (render) renderConversationFeed("preserve");
}

function renderJobExchange(job) {
  if (currentMessageStyle() === "grid") return renderGridJobCard(job);
  const minimal = currentMessageStyle() === "minimal";
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
  if (minimal) {
    assistantBody = minimalOutputBanner(job, detail);
  } else if (active) {
    assistantBody = `<div class="generation-progress">
      <div><span class="progress-stage"><i></i>${escapeHtml(job.stage || statusLabel(job.status))}</span><b>${job.progress || 0}%</b></div>
      <div class="progress-track"><span style="width:${Math.max(0, Math.min(100, job.progress || 0))}%"></span></div>
      <small>${escapeHtml(detail || statusLabel(job.status))}</small>
    </div>`;
  } else if (job.asset_deleted) {
    assistantBody = `<p class="terminal-state completed">${t("assetDeleted")}</p>`;
  } else if (job.status === "completed") {
    const result = audio
      ? `<div class="audio-result"><audio controls preload="metadata" src="${job.result_url}"></audio></div>`
      : mediaType === "image"
        ? `<div class="image-result"><img src="${job.result_url}" alt="${escapeHtml(shortTitle(job))}"></div>`
        : mediaType === "file"
          ? ""
          : `<div class="video-result"><video controls playsinline preload="metadata" src="${job.result_url}"></video></div>`;
    assistantBody = `<p class="terminal-state completed">${mediaReadyLabel(mediaType)}</p>${result}`;
  } else {
    assistantBody = `<p class="terminal-state ${job.status}">${escapeHtml(detail || statusLabel(job.status))}</p>`;
  }
  return `<section class="exchange${minimal ? " minimal-exchange" : ""}" id="job-${job.id}" data-job-id="${job.id}">
    <article class="message user-message">
      <div class="message-avatar user-avatar">${t("you")}</div>
      <div class="message-body">${referenceSummary(job)}<div class="message-text ${state.optimizeMarkdown !== false ? "markdown" : "plain-text"}">${renderMessageText(request.prompt || request.runninghub_workflow_name || "")}${audio && request.lyrics ? renderMessageText(request.lyrics) : ""}</div><div class="message-meta">${sourceLabel}${executionMode}<span>${modelLabel(job)}</span><span>${escapeHtml(nodeLabel(job))}</span>${runningHub || audio || request.task_type === "upscale" ? "" : `<span>${request.width} × ${request.height}</span>`}${runningHub || request.task_type === "upscale" ? "" : `<span>${request.duration}${t("seconds")}</span><span>${request.steps} ${t("steps")}</span><span>${t("seed")} ${request.seed}</span>`}${elapsed}${incognito}</div></div>
    </article>
    <article class="message assistant-message" data-output-job-id="${escapeHtml(job.id)}">
      <div class="message-avatar assistant-avatar">H3</div>
      <div class="message-body"><div class="assistant-heading"><strong>${statusLabel(job.status)}</strong><span>${formatTime(job.updated_at || job.created_at, true)}</span></div>${assistantBody}${messageActions(job)}</div>
    </article>
  </section>`;
}

function chatEmptyMarkup() {
  return `<div class="chat-empty"><span>H3</span><h2>${t("startCreating")}</h2><p>${localized("用一句话描述画面，或从素材库选择参考图开始。", "Describe a shot in one line, or start from a reference in the library.")}</p></div>`;
}

function renderConversationFeed(mode = "preserve") {
  const feed = el("conversationFeed");
  const messageStyle = currentMessageStyle();
  feed.classList.toggle("is-message-grid", messageStyle === "grid");
  feed.classList.toggle("is-message-minimal", messageStyle === "minimal");
  if (mode === "bottom") state.conversationReady = false;
  const oldHeight = feed.scrollHeight;
  const oldTop = feed.scrollTop;
  const nearBottom = oldHeight - oldTop - feed.clientHeight < 160;
  const timeline = [...state.conversations]
    .reverse()
    .map((job) => ({ type: "job", at: job.created_at, data: job }))
    .sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
  const orderedTimeline = messageStyle === "grid" ? [...timeline].reverse() : timeline;
  const content = orderedTimeline.map((item) => renderJobExchange(item.data)).join("");
  feed.innerHTML = content || `${chatEmptyMarkup()}`;
  refreshIcons();
  requestAnimationFrame(() => {
    if (messageStyle === "grid") {
      feed.scrollTop = mode === "bottom" ? 0 : oldTop;
    } else if (mode === "bottom" || (mode === "preserve" && nearBottom)) {
      feed.scrollTop = feed.scrollHeight;
    } else if (mode === "prepend") {
      feed.scrollTop = oldTop + (feed.scrollHeight - oldHeight);
    } else {
      feed.scrollTop = oldTop;
    }
    state.conversationScrollTop = feed.scrollTop;
    requestAnimationFrame(() => {
      state.conversationReady = true;
      if (messageStyle === "grid" && feed.scrollHeight <= feed.clientHeight + 8) {
        loadOlderMessages();
      }
    });
  });
}

async function scrollToGeneratedOutput(jobId) {
  closeAssetDrawer();
  let target = jobElement(el("conversationFeed"), "data-output-job-id", jobId);
  while (!target && state.conversationPage < state.conversationPages) {
    const previousPage = state.conversationPage;
    await loadOlderMessages();
    target = jobElement(el("conversationFeed"), "data-output-job-id", jobId);
    if (state.conversationPage === previousPage) break;
  }
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "center" });
  target.classList.add("output-focus");
  setTimeout(() => target.classList.remove("output-focus"), 1800);
}

function assetDetailFile(item, index, job) {
  const url = item.url || `/api/v1/generations/${encodeURIComponent(job.id)}/references/${index}`;
  const name = item.name || `${item.type || "file"}-${index + 1}`;
  let media = `<span class="asset-detail-file-media">${icon(item.type === "video" ? "film" : item.type === "audio" ? "audio-lines" : "image")}</span>`;
  if (item.type === "image") media = `<span class="asset-detail-file-media"><img src="${escapeHtml(url)}" alt="${escapeHtml(name)}" loading="lazy"></span>`;
  if (item.type === "video") media = `<span class="asset-detail-file-media"><video src="${escapeHtml(url)}" muted playsinline preload="metadata"></video></span>`;
  return `<a class="asset-detail-file" href="${escapeHtml(url)}" data-preview-url="${escapeHtml(url)}" data-preview-name="${escapeHtml(name)}" data-preview-type="${escapeHtml(item.type || "file")}">${media}<div><b>${escapeHtml(name)}</b><small>${escapeHtml(item.type || "file")}${item.size ? ` · ${formatBytes(item.size)}` : ""}</small></div></a>`;
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

function renderAssetDetail(job, windowNode = el("assetDetailModal")) {
  const request = job.request || {};
  const peerAsset = Boolean(job.peer_asset);
  const localAsset = Boolean(job.local_asset);
  const mediaType = jobMediaType(job);
  const audio = mediaType === "audio";
  const runningHub = request.provider === "runninghub";
  const get = (id) => windowNode.querySelector(`#${id}`);
  const body = get("assetDetailBody");
  const download = get("downloadAssetDetail");
  const downloadable = job.status === "completed" && Boolean(job.result_url);
  const references = request.references || [];
  const active = isActive(job);
  const progress = Math.max(0, Math.min(100, Math.round(Number(job.progress) || 0)));
  const preview = active
    ? `<div class="asset-detail-progress">
        <span class="grid-progress-ring" style="--progress:${progress * 3.6}deg"><span>${progress}%</span></span>
        <div><strong>${escapeHtml(job.stage || statusLabel(job.status))}</strong><p>${escapeHtml(job.queue_position ? `${t("queuePosition")} ${job.queue_position}` : statusLabel(job.status))}</p></div>
      </div>`
    : job.asset_deleted
    ? `<div class="asset-detail-placeholder">${icon("file-x-2")}<span>${t("assetDeleted")}</span></div>`
    : job.status === "completed" && job.result_url
    ? audio
      ? `<audio controls preload="metadata" src="${escapeHtml(job.result_url)}"></audio>`
      : mediaType === "image"
        ? `<img src="${escapeHtml(job.result_url)}" alt="${escapeHtml(shortTitle(job))}">`
        : mediaType === "file"
          ? `<div class="asset-detail-placeholder">${icon("file-question")}<span>${localized("该文件无法预览", "This file cannot be previewed")}</span></div>`
          : `<video controls playsinline preload="metadata" src="${escapeHtml(job.result_url)}"></video>`
    : `<div class="asset-detail-placeholder">${icon(job.status === "running" ? "loader-circle" : "file-x-2")}<span>${t("outputUnavailable")}</span></div>`;
  const files = references.length
    ? `<div class="asset-detail-files">${references.map((item, index) => assetDetailFile(item, index, job)).join("")}</div>`
    : `<p class="quiet">${t("noSourceFiles")}</p>`;
  const facts = (localAsset
    ? [localAssetTypeLabel(mediaType), job.owner_name ? `${t("owner")} ${job.owner_name}` : null]
    : [
      executionModeLabel(job), modelLabel(job), nodeLabel(job),
      runningHub || audio || request.task_type === "upscale" ? null : `${request.width} × ${request.height}`,
      runningHub || request.task_type === "upscale" ? null : `${request.duration}${t("seconds")}`,
      runningHub || request.task_type === "upscale" ? null : `${request.steps} ${t("steps")}`,
      runningHub || request.task_type === "upscale" ? null : `${t("seed")} ${request.seed}`,
      ...runningHubParameterFacts(request),
      `${t("overallTime")} ${formatElapsed(job.elapsed_seconds)}`,
    ]).filter(Boolean).map((value) => `<span>${escapeHtml(value)}</span>`).join("");
  get("assetDetailTitle").textContent = shortTitle(job);
  const ownerMeta = job.owner_name ? ` · ${t("owner")} ${job.owner_name}` : "";
  get("assetDetailMeta").textContent = `${statusLabel(job.status)} · ${formatTime(job.created_at, true)}${ownerMeta} · ${job.source_job_id || job.id}`;
  body.innerHTML = `<div class="asset-detail-preview">${preview}</div><aside class="asset-detail-info">
    <section class="asset-detail-section"><h3>${t("prompt")}</h3><pre>${escapeHtml(request.prompt || "")}</pre></section>
    ${request.lyrics ? `<section class="asset-detail-section"><h3>${t("lyrics")}</h3><pre>${escapeHtml(request.lyrics)}</pre></section>` : ""}
    <section class="asset-detail-section"><h3>${t("sourceFiles")}</h3>${files}</section>
    <section class="asset-detail-section"><h3>${t("parameters")}</h3><div class="asset-detail-facts">${facts}</div></section>
  </div>`;
  const footer = windowNode.querySelector(".asset-detail-footer");
  if (footer) footer.hidden = active;
  get("deleteAssetDetail").hidden = peerAsset || localAsset;
  get("deleteAssetDetail").disabled = peerAsset || localAsset || isActive(job);
  get("renameAssetDetail").hidden = peerAsset || localAsset || job.status !== "completed" || !downloadable;
  get("renameAssetDetail").disabled = peerAsset || localAsset || job.status !== "completed" || !downloadable;
  download.hidden = !downloadable;
  download.href = downloadable ? job.result_url : "#";
  download.download = job.source_job_id || job.id;
  download.querySelector("span").textContent = mediaDownloadLabel(mediaType);
  get("regenerateAssetDetail").hidden = peerAsset || localAsset;
  get("regenerateAssetDetail").disabled = peerAsset || localAsset || isActive(job);
  get("reuseAssetDetail").hidden = peerAsset || localAsset;
  get("reuseAssetDetail").disabled = peerAsset || localAsset;
  get("reuseOutputAssetDetail").hidden = localAsset;
  get("reuseOutputAssetDetail").disabled = localAsset || !downloadable;
  const videoUpscaleButton = get("upscaleVideoAssetDetail");
  if (videoUpscaleButton) {
    videoUpscaleButton.hidden = !canVideoUpscale(job);
    videoUpscaleButton.disabled = !canVideoUpscale(job);
  }
  refreshIcons();
}

function activeAssetDetailRecord() {
  return state.assetDetailActiveWindowId
    ? state.assetDetailWindows.get(state.assetDetailActiveWindowId) || null
    : null;
}

function detailElement(record, id) {
  return record?.node?.querySelector(`#${id}`) || null;
}

async function openAssetDetail(jobId) {
  const windowId = `asset-detail-${jobId}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const layer = el("assetDetailModal");
  const windowNode = el("assetDetailTemplate").content.cloneNode(true).firstElementChild;
  const cascade = Math.min(state.assetDetailWindowOrder.length * 28, 168);
  windowNode.querySelector("#assetDetailTitle").textContent = t("assetDetail");
  const detailClose = windowNode.querySelector("#closeAssetDetail");
  if (detailClose) {
    detailClose.title = localized("关闭素材详情", "Close asset details");
    detailClose.setAttribute("aria-label", localized("关闭素材详情", "Close asset details"));
  }
  windowNode.querySelector("[data-detail-toggle] span").textContent = localized("详情", "Details");
  windowNode.querySelector("[data-detail-toggle]").title = localized("显示详情", "Show details");
  windowNode.querySelector("[data-detail-toggle]").setAttribute("aria-label", localized("显示详情", "Show details"));
  windowNode.querySelector("#deleteAssetDetail span").textContent = t("deleteRecord");
  windowNode.querySelector("#renameAssetDetail span").textContent = localized("重命名文件", "Rename file");
  windowNode.querySelector("#reuseOutputAssetDetail span").textContent = t("useAsInput");
  windowNode.querySelector("#upscaleVideoAssetDetail span").textContent = t("videoUpscale");
  windowNode.querySelector("#regenerateAssetDetail span").textContent = t("regenerate");
  windowNode.querySelector("#reuseAssetDetail span").textContent = t("reuse");
  windowNode.dataset.detailWindowId = windowId;
  windowNode.dataset.detailJobId = jobId;
  windowNode.style.setProperty("--detail-window-index", String(state.assetDetailWindowOrder.length));
  windowNode.style.left = `calc(50% + ${cascade}px)`;
  windowNode.style.top = `calc(50% + ${cascade}px)`;
  layer.hidden = false;
  layer.append(windowNode);
  state.assetDetailWindows.set(windowId, { id: windowId, jobId, node: windowNode, job: null, expanded: false });
  state.assetDetailWindowOrder.push(windowId);
  state.assetDetailActiveWindowId = windowId;
  bringAssetDetailToFront(windowId);
  document.body.classList.add("modal-open");
  const get = (id) => windowNode.querySelector(`#${id}`);
  get("assetDetailError").textContent = "";
  get("downloadAssetDetail").hidden = true;
  get("downloadAssetDetail").href = "#";
  get("deleteAssetDetail").hidden = false;
  get("regenerateAssetDetail").hidden = false;
  get("reuseAssetDetail").hidden = false;
  get("reuseOutputAssetDetail").hidden = false;
  get("upscaleVideoAssetDetail").hidden = true;
  get("regenerateAssetDetail").disabled = true;
  get("reuseOutputAssetDetail").disabled = true;
  get("assetDetailBody").innerHTML = `<div class="feed-loading"><span></span><span></span><span></span></div>`;
  refreshIcons();
  try {
    const job = await fetchAssetDetail(jobId);
    const record = state.assetDetailWindows.get(windowId);
    if (!record) return;
    record.job = job;
    state.assetDetailJob = job;
    renderAssetDetail(job, windowNode);
  } catch (error) {
    const record = state.assetDetailWindows.get(windowId);
    if (!record) return;
    get("assetDetailBody").innerHTML = `<p class="list-error">${escapeHtml(error.message)}</p>`;
  }
}

function bringAssetDetailToFront(windowId) {
  const record = state.assetDetailWindows.get(windowId);
  if (!record) return;
  state.assetDetailWindowOrder = state.assetDetailWindowOrder.filter((id) => id !== windowId);
  state.assetDetailWindowOrder.push(windowId);
  state.assetDetailActiveWindowId = windowId;
  state.assetDetailWindowOrder.forEach((id, index) => {
    const item = state.assetDetailWindows.get(id);
    if (item) item.node.style.zIndex = String(101 + index);
  });
}

function closeAssetDetail(windowId) {
  const id = windowId || state.assetDetailWindowOrder.at(-1);
  const record = id ? state.assetDetailWindows.get(id) : null;
  if (!record) return;
  record.node.querySelectorAll("video, audio").forEach((item) => { item.pause(); item.removeAttribute("src"); item.load(); });
  record.node.remove();
  state.assetDetailWindows.delete(id);
  state.assetDetailWindowOrder = state.assetDetailWindowOrder.filter((item) => item !== id);
  state.assetDetailActiveWindowId = state.assetDetailWindowOrder.at(-1) || null;
  state.assetDetailJob = state.assetDetailWindows.size ? state.assetDetailWindows.get(state.assetDetailWindowOrder.at(-1))?.job || null : null;
  if (!state.assetDetailWindows.size) {
    el("assetDetailModal").hidden = true;
    if (el("nodeModal").hidden && el("peeringModal").hidden && el("localAssetsModal").hidden && el("localAssetPreviewModal").hidden) document.body.classList.remove("modal-open");
  }
}

function toggleAssetDetailInfo(windowId) {
  const record = state.assetDetailWindows.get(windowId);
  if (!record) return;
  record.expanded = !record.expanded;
  record.node.classList.toggle("details-expanded", record.expanded);
  const button = record.node.querySelector("[data-detail-toggle]");
  button.setAttribute("aria-expanded", String(record.expanded));
  button.title = record.expanded ? localized("隐藏详情", "Hide details") : localized("显示详情", "Show details");
  button.setAttribute("aria-label", button.title);
  button.querySelector("span").textContent = record.expanded ? localized("收起", "Hide") : localized("详情", "Details");
  button.querySelector("svg")?.replaceWith(document.createRange().createContextualFragment(icon(record.expanded ? "panel-right-close" : "panel-right-open")));
  refreshIcons();
}

function startAssetDetailDrag(event, windowId) {
  if (event.button !== undefined && event.button !== 0) return;
  const record = state.assetDetailWindows.get(windowId);
  if (!record) return;
  bringAssetDetailToFront(windowId);
  const rect = record.node.getBoundingClientRect();
  state.assetDetailDrag = { windowId, startX: event.clientX, startY: event.clientY, originX: rect.left, originY: rect.top };
  record.node.classList.add("dragging");
  event.preventDefault();
}

function moveAssetDetailDrag(event) {
  const drag = state.assetDetailDrag;
  if (!drag) return;
  const record = state.assetDetailWindows.get(drag.windowId);
  if (!record) return;
  const maxX = Math.max(8, window.innerWidth - record.node.offsetWidth - 8);
  const maxY = Math.max(8, window.innerHeight - record.node.offsetHeight - 8);
  const x = Math.min(maxX, Math.max(8, drag.originX + event.clientX - drag.startX));
  const y = Math.min(maxY, Math.max(8, drag.originY + event.clientY - drag.startY));
  record.node.style.left = `${x}px`;
  record.node.style.top = `${y}px`;
  record.node.style.transform = "none";
}

function stopAssetDetailDrag() {
  if (!state.assetDetailDrag) return;
  const record = state.assetDetailWindows.get(state.assetDetailDrag.windowId);
  record?.node.classList.remove("dragging");
  state.assetDetailDrag = null;
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
  const detailRecord = activeAssetDetailRecord();
  const detailOpen = Boolean(detailRecord);
  const target = detailOpen ? detailElement(detailRecord, "assetDetailError") : el("formError");
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
  if (!(await addFiles([file]))) {
    throw new Error(el("formError").textContent || t("outputUnavailable"));
  }
  updateModelUi();
  target.textContent = "";
  if (detailOpen) closeAssetDetail(detailRecord.id);
}

function openVideoUpscaleDialog(jobId) {
  const form = el("videoUpscaleForm");
  form.dataset.jobId = jobId;
  el("videoUpscaleCategory").value = "real";
  el("videoUpscaleScale").value = "2";
  el("videoUpscaleError").textContent = "";
  el("videoUpscaleModal").hidden = false;
  document.body.classList.add("modal-open");
  refreshIcons();
  setTimeout(() => el("videoUpscaleCategory")?.focus(), 0);
}

function closeVideoUpscaleDialog() {
  el("videoUpscaleModal").hidden = true;
  el("videoUpscaleForm").dataset.jobId = "";
  if (document.activeElement?.closest("#videoUpscaleModal")) document.activeElement.blur();
  if (el("assetDetailModal").hidden) document.body.classList.remove("modal-open");
}

async function submitVideoUpscale(event) {
  event.preventDefault();
  const form = el("videoUpscaleForm");
  const jobId = form.dataset.jobId;
  if (!jobId) return;
  const errorTarget = el("videoUpscaleError");
  const button = el("submitVideoUpscale");
  errorTarget.textContent = "";
  button.disabled = true;
  try {
    const job = await fetchAssetDetail(jobId);
    if (!canVideoUpscale(job)) throw new Error(t("outputUnavailable"));
    const response = await fetch(job.result_url, { cache: "no-store" });
    if (!response.ok) throw new Error(t("outputUnavailable"));
    const blob = await response.blob();
    const basename = String(job.title || job.id).replace(/[^\w\u4e00-\u9fff.-]+/g, "_").slice(0, 64) || job.id;
    const file = new File([blob], `${basename}.mp4`, { type: blob.type || "video/mp4" });
    const request = job.request || {};
    const category = el("videoUpscaleCategory").value;
    const scale = Number(el("videoUpscaleScale").value) === 4 ? 4 : 2;
    const data = new FormData();
    data.append("prompt", "");
    data.append("lyrics", "");
    data.append("width", String(request.width || 864));
    data.append("height", String(request.height || 480));
    data.append("duration", String(request.duration || 5));
    data.append("steps", "1");
    data.append("seed", "");
    data.append("model_variant", "fl2va-fp8");
    data.append("execution_mode", "native");
    data.append("workflow_id", "preset-upscale-video");
    data.append("task_type", "upscale");
    data.append("upscale_category", category);
    data.append("upscale_scale", String(scale));
    data.append("auto_upscale", "false");
    data.append("comfy_node", "auto");
    if (job.folder_id) data.append("folder_id", job.folder_id);
    data.append("incognito", state.incognito ? "true" : "false");
    data.append("reference_manifest", JSON.stringify([{ type: "video" }]));
    data.append("references", file, file.name);
    const headers = state.incognito ? { "X-H3-Incognito-Code": state.incognitoCode } : {};
    const created = await api("/api/v1/generations", { method: "POST", headers, body: data });
    applyJobUpsert(created);
    closeVideoUpscaleDialog();
    showToast(`${t("videoUpscale")} · ${localized("任务已提交", "job submitted")}`);
    el("conversationFeed").scrollTop = el("conversationFeed").scrollHeight;
  } catch (error) {
    errorTarget.textContent = error.message;
  } finally {
    button.disabled = false;
  }
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

function workflowIdForJob(job) {
  if (job.request?.workflow_id) return job.request.workflow_id;
  if (job.request?.task_type === "upscale") return job.request?.media_type === "video" ? "preset-upscale-video" : "preset-upscale-image";
  return state.workflows.find((workflow) => (
    workflow.source === "preset"
    && workflow.model_variant === (job.request?.model_variant || "fl2va-fp8")
    && workflow.execution_mode === (job.request?.execution_mode || "native")
    && workflow.task_type === "generation"
  ))?.id || "";
}

async function backfillJob(jobId) {
  const detailRecord = activeAssetDetailRecord();
  const detailOpen = Boolean(detailRecord);
  const reuseButton = detailElement(detailRecord, "reuseAssetDetail") || el("reuseAssetDetail");
  if (detailOpen) detailElement(detailRecord, "assetDetailError").textContent = t("fillLoading");
  reuseButton.disabled = true;
  try {
    const job = await fetchAssetDetail(jobId);
    if (job.peer_asset) throw new Error(localized("远端素材仅支持下载或作为输入", "Remote assets support download or use as input"));
    const references = await restoredReferences(job);
    resetComposer();
    promptInput.value = job.request?.prompt || "";
    el("lyrics").value = job.request?.lyrics || "";
    el("modelVariant").value = job.request?.model_variant || "fl2va-fp8";
    el("executionMode").value = job.request?.task_type === "upscale"
      ? "video-upscale"
      : job.request?.execution_mode || "native";
    el("workflowSelect").value = workflowIdForJob(job);
    renderWorkflowOptions();
    el("upscaleCategory").value = job.request?.upscale_category || "real";
    el("upscaleScale").value = String(job.request?.upscale_scale === 4 ? 4 : 2);
    el("autoUpscale").checked = Boolean(job.request?.auto_upscale);
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
    if (detailOpen) closeAssetDetail(detailRecord.id);
    closeAssetDrawer();
    el("conversationFeed").scrollTop = el("conversationFeed").scrollHeight;
    promptInput.focus();
    showError("");
  } catch (error) {
    if (detailOpen) detailElement(detailRecord, "assetDetailError").textContent = error.message;
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

async function startEdit(jobId) {
  try {
    const job = await api(`/api/v1/generations/${jobId}`);
    if (job.status !== "queued") throw new Error(localized("只有排队中的任务可以修改", "Only queued tasks can be edited"));
    resetComposer();
    state.editingJobId = job.id;
    promptInput.value = job.request.prompt;
    el("lyrics").value = job.request.lyrics || "";
    el("modelVariant").value = job.request.model_variant || "fl2va-fp8";
    el("executionMode").value = job.request?.task_type === "upscale"
      ? "video-upscale"
      : job.request.execution_mode || "native";
    el("workflowSelect").value = workflowIdForJob(job);
    renderWorkflowOptions();
    el("upscaleCategory").value = job.request?.upscale_category || "real";
    el("upscaleScale").value = String(job.request?.upscale_scale === 4 ? 4 : 2);
    el("autoUpscale").checked = Boolean(job.request?.auto_upscale);
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
    loadAssetFolders().catch(() => {});
    return true;
  } catch (error) {
    showError(error.message);
    return false;
  }
}

async function renameJobOutput(jobId) {
  const job = assetFromLibrary(jobId) || state.assetDetailJob;
  const current = job?.title || "";
  const name = window.prompt(localized("输入生成文件名", "Enter output file name"), current);
  if (name === null || !name.trim()) return false;
  try {
    const renamed = await api(`/api/v1/generations/${encodeURIComponent(jobId)}/name`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() }),
    });
    applyJobUpsert(renamed);
    const detailRecord = [...state.assetDetailWindows.values()].find((item) => item.jobId === jobId);
    if (detailRecord) {
      detailRecord.job = renamed;
      if (state.assetDetailActiveWindowId === detailRecord.id) state.assetDetailJob = renamed;
      renderAssetDetail(renamed, detailRecord.node);
    }
    return true;
  } catch (error) {
    showError(error.message);
    return false;
  }
}

async function regenerateJob(jobId) {
  if (!window.confirm(t("regenerateConfirm"))) return false;
  const folderId = await pickAssetFolder(t("regenerate"), t("regenerateFolder"));
  if (folderId === undefined) return false;
  const detailRecord = [...state.assetDetailWindows.values()].find((item) => item.jobId === jobId);
  const detailOpen = Boolean(detailRecord);
  const actionButtons = Array.from(document.querySelectorAll('[data-job-action="regenerate"]'))
    .filter((button) => button.dataset.jobId === jobId);
  if (detailOpen) {
    actionButtons.push(detailElement(detailRecord, "regenerateAssetDetail"));
    detailElement(detailRecord, "assetDetailError").textContent = localized("正在创建新的生成任务", "Creating a new generation");
  }
  actionButtons.forEach((button) => { button.disabled = true; });
  try {
    const headers = {
      "Content-Type": "application/json",
      ...(state.incognito ? { "X-H3-Incognito-Code": state.incognitoCode } : {}),
    };
    const job = await api(`/api/v1/generations/${encodeURIComponent(jobId)}/regenerate`, {
      method: "POST",
      headers,
      body: JSON.stringify({ folder_id: folderId === "__unfiled__" ? null : folderId }),
    });
    applyJobUpsert(job);
    loadAssetFolders().catch(() => {});
    if (detailOpen) closeAssetDetail(detailRecord.id);
    showError("");
    return true;
  } catch (error) {
    if (detailOpen) detailElement(detailRecord, "assetDetailError").textContent = error.message;
    else showError(error.message);
    return false;
  } finally {
    actionButtons.forEach((button) => { button.disabled = false; });
  }
}

async function handleJobAction(action, jobId) {
  if (action === "reuse") return backfillJob(jobId);
  if (action === "input") return useGeneratedOutputAsInput(jobId).catch((error) => showError(error.message));
  if (action === "video-upscale") return openVideoUpscaleDialog(jobId);
  if (action === "regenerate") return regenerateJob(jobId);
  if (action === "edit") return startEdit(jobId);
  if (action === "cancel") return cancelJob(jobId);
  if (action === "delete") return deleteJob(jobId);
  if (action === "rename") return renameJobOutput(jobId);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.referenceProcessing) {
    showError(localized("请等待参考图片压缩完成", "Wait for reference image compression to finish"));
    return;
  }
  showError("");
  if (!confirmAutoUpscale()) return;
  if (!(await requestAutoUpscaleConfirmation())) return;
  if (el("autoUpscale")?.checked) {
    el("upscaleCategory").value = el("autoUpscaleConfirmCategory").value;
    el("upscaleScale").value = el("autoUpscaleConfirmScale").value;
  }
  const prompt = promptInput.value.trim();
  const runningHubNode = selectedRunningHubNode();
  const runningHub = Boolean(runningHubNode?.runninghub_schema);
  const upscale = isUpscale();
  const minimumPromptLength = upscale ? 0 : isMusic3() ? 2 : 8;
  if (!runningHub && prompt.length < minimumPromptLength) return showError(localized(`请填写至少 ${minimumPromptLength} 个字符的提示词`, `Enter a prompt with at least ${minimumPromptLength} characters`));
  const steps = upscale ? 1 : isMusic3() ? 30 : isH3SA() ? 8 : isDigitalHuman() ? 20 : Number(el("steps").value);
  if (!runningHub && !upscale && (!Number.isInteger(steps) || steps < 4 || steps > 50)) return showError(localized("采样步数请输入 4–50 的整数", "Sampling steps must be an integer from 4 to 50"));
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
        requestBody.lyrics = isMusic3() || selectedWorkflowRecord()?.source === "custom" ? el("lyrics").value.trim() : "";
        requestBody.width = width;
        requestBody.height = height;
        requestBody.ratio = el("aspectRatio").value;
        requestBody.megapixels = currentMegapixels();
        requestBody.duration = Number(el("duration").value);
        requestBody.steps = steps;
        requestBody.seed = el("seed").value === "" ? undefined : Number(el("seed").value);
        requestBody.model_variant = selectedVariant();
        requestBody.execution_mode = backendExecutionMode();
        Object.assign(requestBody, autoUpscaleParameters());
        requestBody.task_type = upscale ? "upscale" : "generation";
        if (upscale) {
          requestBody.upscale_category = el("upscaleCategory").value;
          requestBody.upscale_scale = selectedUpscaleScale();
        }
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
      data.append("lyrics", isMusic3() || selectedWorkflowRecord()?.source === "custom" ? el("lyrics").value.trim() : "");
      data.append("width", String(width));
      data.append("height", String(height));
      data.append("ratio", el("aspectRatio").value);
      data.append("megapixels", String(currentMegapixels()));
      data.append("duration", el("duration").value);
      data.append("steps", String(steps));
      data.append("seed", el("seed").value);
      if (runningHub) {
        data.append("runninghub_parameters", JSON.stringify(collectRunningHubParameters()));
      } else {
        data.append("model_variant", selectedVariant());
        data.append("execution_mode", backendExecutionMode());
        const selectedWorkflow = selectedWorkflowRecord();
        if (selectedWorkflow?.id) data.append("workflow_id", selectedWorkflow.id);
        const autoUpscale = autoUpscaleParameters();
        data.append("auto_upscale", autoUpscale.auto_upscale ? "true" : "false");
        data.append("auto_upscale_category", autoUpscale.auto_upscale_category);
        data.append("auto_upscale_scale", String(autoUpscale.auto_upscale_scale));
        data.append("task_type", upscale ? "upscale" : "generation");
        if (upscale) {
          data.append("upscale_category", el("upscaleCategory").value);
          data.append("upscale_scale", String(selectedUpscaleScale()));
        }
      }
      data.append("comfy_node", el("comfyNode").value);
      if (state.assetFolderId && state.assetFolderId !== "__unfiled__") data.append("folder_id", state.assetFolderId);
      data.append("incognito", state.incognito ? "true" : "false");
      data.append("reference_manifest", JSON.stringify(state.references.map((item) => ({ type: item.kind, ...(item.field_key ? { field_key: item.field_key } : {}) }))));
      state.references.forEach((item) => data.append("references", item.file, item.file.name));
      const headers = state.incognito ? { "X-H3-Incognito-Code": state.incognitoCode } : {};
      payload = await api("/api/v1/generations", { method: "POST", headers, body: data });
    }
    if (state.editingJobId) resetComposer();
    applyJobUpsert(payload);
    loadAssetFolders().catch(() => {});
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
  el("opsQueueBadge").textContent = queuedCount;
  el("opsQueueBadge").hidden = queuedCount === 0;
  const opsTip = queuedCount
    ? localized(`运行日志 · ${queuedCount} 个排队`, `Activity log · ${queuedCount} queued`)
    : localized("运行日志", "Activity log");
  el("openOps").dataset.tip = opsTip;
  el("openOps").setAttribute("aria-label", opsTip);
  el("activeTaskSummary").textContent = running
    ? anonymousRunning
      ? state.locale === "en" ? "A task is running" : "有任务正在运行中"
      : state.locale === "en" ? `${runningJobs.length} tasks running · ${runningJobs.map((job) => nodeLabel(job)).join(", ")}` : `${runningJobs.length} 个任务执行中 · ${runningJobs.map((job) => nodeLabel(job)).join("、")}`
    : state.locale === "en" ? `No active tasks · ${queuedCount} queued` : `当前没有执行任务 · 排队 ${queuedCount}`;
  el("queueList").innerHTML = queue.length ? queue.map((job) => {
    if (isAnonymousQueueJob(job)) {
      return `<div class="queue-row">
        <span class="queue-position">${job.status === "running" ? icon("loader-circle") : job.queue_position}</span>
        <span><strong>${escapeHtml(job.stage || localized("有任务正在运行中", "A task is running"))}</strong></span>
      </div>`;
    }
    return `<div class="queue-row" data-scroll-job="${job.id}">
      <span class="queue-position">${job.status === "running" ? icon("loader-circle") : job.queue_position}</span>
      <span><strong>${escapeHtml(shortTitle(job))}</strong><small>${escapeHtml(nodeLabel(job))} · ${escapeHtml(executionModeLabel(job))} · ${escapeHtml(job.stage || statusLabel(job.status))} · ${job.progress || 0}% · ${formatElapsed(job.elapsed_seconds)}</small></span>
      <button type="button" data-job-action="cancel" data-job-id="${job.id}" title="${localized("取消任务", "Cancel task")}" aria-label="${localized("取消任务", "Cancel task")}">${icon("square")}</button>
    </div>`;
  }).join("") : `<p class="quiet">${state.locale === "en" ? "Queue empty" : "队列为空"}</p>`;
  refreshIcons();
}

function renderLogs(logs) {
  state.logs = logs;
  const merged = [...logs, ...(state.workflowIssues || [])];
  merged.sort((left, right) => String(left.timestamp || "").localeCompare(String(right.timestamp || "")));
  const visible = merged.filter((item) => new Date(item.timestamp).getTime() >= state.logFloor);
  const container = el("logList");
  const previousTop = container.scrollTop;
  const followTail = state.logFollowTail;
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
  requestAnimationFrame(() => {
    container.scrollTop = followTail ? container.scrollHeight : previousTop;
  });
}

function reportWorkflowIssue(message, { level = "error", reveal = true } = {}) {
  const text = String(message ?? "").trim();
  if (!text) return;
  const entry = {
    timestamp: new Date().toISOString(),
    level,
    message: localized(`工作流：${text}`, `Workflow: ${text}`),
  };
  state.workflowIssues = [...(state.workflowIssues || []), entry].slice(-20);
  renderLogs(state.logs || []);
  if (reveal) openOpsWindow();
}

// Workflow failures belong to the runtime log window; the inline banner above
// the workflow grid stays hidden so node cards keep their full height.
function setWorkflowManagerError(message) {
  const node = el("workflowManagerError");
  if (node) node.textContent = message || "";
  reportWorkflowIssue(message);
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
  el("autoCompressLargeImages").checked = payload.auto_compress_large_images !== false;
  state.runninghubEnabled = payload.runninghub_enabled !== false;
  el("runninghubEnabled").checked = state.runninghubEnabled;
  state.excludeRunningHubAuto = payload.exclude_runninghub_auto === true;
  el("excludeRunningHubAuto").checked = state.excludeRunningHubAuto;
  state.bindLocalComfyui = payload.bind_local_comfyui === true;
  el("bindLocalComfyui").checked = state.bindLocalComfyui;
  el("localComfyCommand").value = payload.local_comfy_command || "{python} {script} --listen {host} --port {port}";
  syncLocalComfyFields();
  applyRunningHubAvailability();
  el("remoteDisconnectPolicy").value = payload.remote_disconnect_policy || "encrypt";
  el("remoteRecordsKey").value = payload.remote_records_key || "";
  el("openOps").hidden = payload.show_runtime_logs === false;
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
    errorBox.textContent = localized("节点状态查询周期必须为 5 至 3600 秒", "Node status interval must be between 5 and 3600 seconds");
    return;
  }
  const keyLength = Array.from(key).length;
  if (keyLength < 8 || keyLength > 256) {
    errorBox.textContent = localized("远程记录密钥长度必须为 8 至 256 个字符", "Remote records key must be 8 to 256 characters");
    return;
  }
  if (el("bindLocalComfyui").checked && !el("localComfyCommand").value.trim()) {
    errorBox.textContent = localized("请填写 ComfyUI 启动命令", "Enter the ComfyUI launch command");
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
        auto_compress_large_images: el("autoCompressLargeImages").checked,
        runninghub_enabled: el("runninghubEnabled").checked,
        exclude_runninghub_auto: el("excludeRunningHubAuto").checked,
        bind_local_comfyui: el("bindLocalComfyui").checked,
        local_comfy_command: el("localComfyCommand").value,
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
    el("openOps").hidden = !el("showRuntimeLogs").checked;
    el("openPeering").hidden = !el("showPeering").checked;
    state.generalSettings.auto_compress_large_images = el("autoCompressLargeImages").checked;
    state.runninghubEnabled = el("runninghubEnabled").checked;
    state.excludeRunningHubAuto = el("excludeRunningHubAuto").checked;
    state.bindLocalComfyui = el("bindLocalComfyui").checked;
    syncLocalComfyFields();
    applyRunningHubAvailability();
    renderManagedNodes();
    if (!el("showRuntimeLogs").checked) closeOpsWindow();
    el("globalSettingsModal").hidden = true;
    document.body.classList.remove("modal-open");
    showToast(localized("设置已保存", "Settings saved"));
  } catch (error) {
    errorBox.textContent = error.message;
  }
}

function setSettingsTab(name) {
  document.querySelectorAll("[data-settings-tab]").forEach((button) => {
    const active = button.dataset.settingsTab === name;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
    button.tabIndex = active ? 0 : -1;
  });
  document.querySelectorAll("[data-settings-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.settingsPanel !== name;
  });
}

function openGlobalSettings(tab = "system") {
  el("globalSettingsModal").hidden = false;
  document.body.classList.add("modal-open");
  setSettingsTab(tab);
  loadGeneralSettings().catch((error) => { el("globalSettingsError").textContent = error.message; });
  refreshIcons();
}

function closeGlobalSettings() {
  el("globalSettingsModal").hidden = true;
  if (el("peeringModal").hidden && el("nodeModal").hidden && el("assetDetailModal").hidden && el("localAssetsModal").hidden) document.body.classList.remove("modal-open");
}

function localAssetTypeLabel(mediaType) {
  const labels = {
    video: localized("视频", "Video"),
    audio: localized("音频", "Audio"),
    image: localized("图片", "Image"),
    file: localized("文件", "File"),
  };
  return labels[mediaType] || labels.file;
}

function localAssetPreviewMarkup(asset) {
  if (asset.locked) {
    return `<button class="local-asset-locked" type="button" data-unlock-owner="${escapeHtml(asset.owner_device_id)}" data-unlock-name="${escapeHtml(asset.owner_name)}" title="${localized("输入所属设备密钥", "Enter the device key")}">${icon("lock-keyhole")}<b>${localized("文件被加密", "File encrypted")}</b></button>`;
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

const ASSET_PREVIEW_PATTERNS = [
  ["image", /\.(png|jpe?g|gif|webp|bmp|avif|svg|heic|heif)$/i],
  ["video", /\.(mp4|webm|mov|m4v|ogv|mkv)$/i],
  ["audio", /\.(mp3|wav|ogg|m4a|flac|aac|opus|wma|amr)$/i],
];

function assetPreviewKind(url, declaredType) {
  const type = String(declaredType || "").toLowerCase();
  if (["image", "video", "audio"].includes(type)) return type;
  if (type.startsWith("image/")) return "image";
  if (type.startsWith("video/")) return "video";
  if (type.startsWith("audio/")) return "audio";
  const path = String(url || "").split("?")[0].split("#")[0];
  for (const [kind, pattern] of ASSET_PREVIEW_PATTERNS) {
    if (pattern.test(path)) return kind;
  }
  return "file";
}

function assetPreviewMarkup(asset) {
  const url = String(asset.url || "");
  const name = asset.name || localized("素材", "Asset");
  const kind = assetPreviewKind(url, asset.type);
  const safeUrl = escapeHtml(url);
  const safeName = escapeHtml(name);
  if (kind === "image" && url) {
    return `<div class="asset-preview-image-stage" data-preview-stage style="--preview-zoom:100%"><img src="${safeUrl}" alt="${safeName}" data-preview-image></div>
      <div class="asset-preview-zoom-controls" aria-label="${localized("图片缩放", "Image zoom")}">
        <button type="button" data-preview-zoom="out" aria-label="${localized("缩小", "Zoom out")}" title="${localized("缩小", "Zoom out")}">${icon("minus")}</button>
        <button type="button" data-preview-zoom="reset" aria-label="${localized("适应窗口", "Fit to window")}" title="${localized("适应窗口", "Fit to window")}">${icon("maximize-2")}</button>
        <button type="button" data-preview-zoom="in" aria-label="${localized("放大", "Zoom in")}" title="${localized("放大", "Zoom in")}">${icon("plus")}</button>
      </div>`;
  }
  if (kind === "video" && url) return `<video src="${safeUrl}" controls playsinline autoplay preload="metadata" aria-label="${safeName}"></video>`;
  if (kind === "audio" && url) {
    return `<div class="asset-preview-audio"><div class="asset-preview-audio-name">${icon("audio-lines")}<b>${safeName}</b></div><audio src="${safeUrl}" controls autoplay preload="metadata" aria-label="${safeName}"></audio></div>`;
  }
  return `<div class="local-asset-preview-unsupported">${icon("file-question")}<b>${safeName}</b><span>${localized("该文件无法预览", "This file cannot be previewed")}</span></div>`;
}

let assetPreviewZoom = 1;

function setAssetPreviewZoom(value) {
  const stage = el("localAssetPreviewBody")?.querySelector("[data-preview-stage]");
  if (!stage) return;
  assetPreviewZoom = Math.max(1, Math.min(4, value));
  stage.style.setProperty("--preview-zoom", `${assetPreviewZoom * 100}%`);
  stage.classList.toggle("is-zoomed", assetPreviewZoom > 1.001);
}

function openAssetPreview(asset) {
  const body = el("localAssetPreviewBody");
  if (!body) return;
  const kind = assetPreviewKind(asset.url, asset.type);
  assetPreviewZoom = 1;
  body.innerHTML = assetPreviewMarkup(asset);
  const dialog = document.querySelector(".local-asset-preview-dialog");
  if (dialog) dialog.setAttribute("aria-label", asset.name || localized("素材预览", "Asset preview"));
  const modal = el("localAssetPreviewModal");
  modal.classList.toggle("is-compact", kind === "audio" || kind === "file");
  modal.hidden = false;
  document.body.classList.add("modal-open");
  refreshIcons();
}

function openLocalAssetPreview(asset) {
  if (asset.asset_deleted) {
    openAssetPreview({ url: "", name: asset.name || asset.file_name || "", type: "file" });
    return;
  }
  openAssetPreview({
    url: asset.locked ? "" : asset.preview_url || "",
    name: asset.name || asset.file_name || localized("本地素材", "Local asset"),
    type: asset.locked ? "file" : asset.media_type || "file",
  });
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
  const selectable = state.localAssets.filter((asset) => !asset.asset_deleted && asset.can_delete);
  const selectedCount = selectable.filter((asset) => state.localAssetSelected.has(asset.id)).length;
  el("localAssetsSelectAll").checked = selectable.length > 0 && selectedCount === selectable.length;
  el("localAssetsSelectAll").indeterminate = selectedCount > 0 && selectedCount < selectable.length;
}

async function loadLocalAssetFolders() {
  const payload = await api("/api/v1/asset-folders");
  state.assetFolders = payload.data || [];
  renderLocalAssetManager();
}

function selectLocalAssetFolder(folderId) {
  state.localAssetFolderId = folderId;
  state.localAssetSelected.clear();
  renderLocalAssetManager();
  loadLocalAssets({ reset: true }).catch((error) => { el("localAssetsError").textContent = error.message; });
}

function renderLocalAssetManager() {
  const list = el("localAssetsList");
  const folderCards = state.localAssetFolderId === "__root__"
    ? state.assetFolders.map((folder) => `<article class="asset-card local-asset-folder-card" data-local-folder-card="${escapeHtml(folder.id)}" tabindex="0" role="button" aria-label="${escapeHtml(folder.name)}"><div class="asset-folder-preview">${folderGlyph("folder")}</div><div class="asset-folder-meta"><strong>${escapeHtml(folder.name)}</strong><small>${Number(folder.count || 0)} ${localized("项素材", Number(folder.count || 0) === 1 ? "asset" : "assets")}</small><button type="button" data-local-folder-delete="${escapeHtml(folder.id)}" title="${localized("删除文件夹", "Delete folder")}" aria-label="${localized("删除文件夹", "Delete folder")}">${icon("trash-2")}</button></div></article>`).join("")
    : `<article class="asset-card local-asset-folder-card back" data-local-folder-back="true" tabindex="0" role="button" aria-label="${localized("返回根目录", "Back to root")}"><div class="asset-folder-preview">${folderBackGlyph()}</div><div class="asset-folder-meta"><strong>${localized("返回根目录", "Back to root")}</strong></div></article>`;
  const cards = state.localAssets.map((asset) => {
    const encryptedMessage = asset.locked
      ? `${localized("文件被加密，所属设备：", "File encrypted; device: ")}${asset.owner_name}`
      : asset.asset_deleted
        ? t("assetDeleted")
        : asset.file_name || formatTime(asset.created_at, true);
    const mediaType = asset.media_type || "file";
    const audioOrFile = mediaType === "audio" || mediaType === "file";
    return `<article class="asset-card local-asset-card" data-local-asset-id="${escapeHtml(asset.id)}" tabindex="0" aria-label="${escapeHtml(asset.name)}">
      <div class="asset-preview${audioOrFile ? " music" : ""}">
        ${asset.can_delete ? `<label class="local-asset-select" data-local-asset-select><input type="checkbox" value="${escapeHtml(asset.id)}" aria-label="${localized("选择", "Select")} ${escapeHtml(asset.name)}" ${state.localAssetSelected.has(asset.id) ? "checked" : ""}></label>` : ""}
        ${localAssetPreviewMarkup(asset)}
      </div>
      <div class="asset-meta"><span class="task-status completed"></span><strong title="${escapeHtml(asset.name)}">${escapeHtml(asset.name)}</strong><small class="asset-plan">${escapeHtml(localAssetTypeLabel(mediaType))}</small><span class="asset-owner" title="${localized("来源：", "Source: ")}${escapeHtml(asset.owner_name)}">${icon("tag")}<span>${escapeHtml(asset.owner_name)}</span></span><time title="${escapeHtml(encryptedMessage)}">${escapeHtml(encryptedMessage)}</time></div>
    </article>`;
  }).join("");
  const loading = state.localAssetLoading
    ? `<p class="local-assets-loading">${t("loading")}</p>`
    : state.localAssetPage >= state.localAssetPages && state.localAssets.length
      ? `<p class="local-assets-loading">${t("allLoaded")}</p>`
      : "";
  list.innerHTML = (folderCards || cards || state.localAssetLoading) ? `${folderCards}${cards}${loading}` : `<p class="quiet">${t("noAssets")}</p>`;
  const localCount = Number(state.localAssetTotal || 0);
  el("localAssetsCount").textContent = `${localCount} ${localized("项", localCount === 1 ? "item" : "items")}`;
  el("localAssetsSize").textContent = formatBytes(state.localAssetLibrarySize || state.localAssetSize);
  syncLocalAssetSelectAll();
  refreshIcons();
}

function localAssetCanDelete(asset) {
  return Boolean(asset.can_delete);
}

async function loadLocalAssets({ reset = false } = {}) {
  if (state.localAssetLoading) return;
  if (!reset && state.localAssetPage >= state.localAssetPages) return;
  if (reset) {
    state.localAssets = [];
    state.localAssetPage = 0;
    state.localAssetPages = 1;
    state.localAssetTotal = 0;
    state.localAssetSize = 0;
    state.localAssetLibrarySize = 0;
    state.localAssetSelected.clear();
  }
  state.localAssetLoading = true;
  renderLocalAssetManager();
  try {
    const page = state.localAssetPage + 1;
    const params = new URLSearchParams({ page, page_size: 24 });
    if (state.localAssetFolderId) params.set("folder_id", state.localAssetFolderId);
    const payload = await api(`/api/v1/assets/local?${params}`);
    state.localAssets.push(...(payload.data || []));
    state.localAssetPage = Number(payload.page || page);
    state.localAssetPages = Number(payload.pages || 1);
    state.localAssetTotal = Number(payload.total || state.localAssets.length);
    state.localAssetSize = Number(payload.total_size || state.localAssetSize || 0);
    state.localAssetLibrarySize = Number(payload.library_total_size || state.localAssetLibrarySize || state.localAssetSize);
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
  await loadLocalAssetFolders();
  await loadLocalAssets({ reset: true });
}

function closeLocalAssets() {
  el("localAssetsModal").hidden = true;
  if (el("globalSettingsModal").hidden && el("peeringModal").hidden && el("nodeModal").hidden && el("assetDetailModal").hidden && el("unlockAssetsModal").hidden) document.body.classList.remove("modal-open");
}

async function deleteLocalArtifacts() {
  const ids = Array.from(state.localAssetSelected).filter((assetId) => localAssetCanDelete(state.localAssets.find((asset) => asset.id === assetId) || {}));
  if (!ids.length) return;
  if (!window.confirm(localized(`确认删除选中的 ${ids.length} 项本地产物？任务与工作流记录会保留。`, `Delete the selected ${ids.length} local outputs? Task and workflow records are kept.`))) return;
  try {
    const result = await api("/api/v1/assets/local/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ asset_ids: ids }) });
    state.localAssetChanged = Boolean(result.deleted?.length);
    state.localAssetSelected.clear();
    await loadLocalAssets({ reset: true });
    if (state.localAssetChanged) await refreshSharedData();
    if (result.rejected?.length) el("localAssetsError").textContent = localized(`${result.rejected.length} 项未能删除`, `${result.rejected.length} items could not be deleted`);
  } catch (error) {
    el("localAssetsError").textContent = error.message;
  }
}

async function clearOldVideos() {
  try {
    const preview = await api("/api/v1/assets/local/clear-old-video/preview");
    renderOldVideoCleanupPreview(preview);
    el("oldVideoCleanupModal").hidden = false;
    document.body.classList.add("modal-open");
    refreshIcons();
  } catch (error) {
    el("localAssetsError").textContent = error.message;
  }
}

function renderOldVideoCleanupPreview(payload) {
  const items = payload.items || [];
  el("oldVideoCleanupSummary").textContent = `${items.length} ${localized("项", items.length === 1 ? "item" : "items")} · ${formatBytes(payload.total_size || 0)}`;
  el("oldVideoCleanupList").innerHTML = items.length
    ? items.map((item) => `<div class="old-video-cleanup-row"><span><strong>${escapeHtml(item.name || item.file_name)}</strong><small>${escapeHtml(item.file_name || "")} · ${formatTime(item.created_at, true)}</small></span><b>${formatBytes(item.size || 0)}</b></div>`).join("")
    : `<p class="quiet">${localized("没有符合条件的视频素材", "No video assets match the cleanup rule")}</p>`;
  el("confirmOldVideoCleanup").disabled = items.length === 0;
}

async function confirmOldVideoCleanup() {
  const summary = el("oldVideoCleanupSummary").textContent;
  const confirmMessage = state.locale === "en"
    ? `Delete the following ${summary} of video assets? Task records will be kept.`
    : `确认清除以下 ${summary} 的视频素材？任务记录会保留。`;
  if (!window.confirm(confirmMessage)) return;
  try {
    const result = await api("/api/v1/assets/local/clear-old-video", { method: "POST" });
    closeOldVideoCleanup();
    showToast(localized(`已清除 ${result.count || 0} 项视频素材`, `Cleared ${result.count || 0} video assets`));
    await loadLocalAssets({ reset: true });
    await refreshSharedData();
  } catch (error) {
    el("localAssetsError").textContent = error.message;
  }
}

function closeOldVideoCleanup() {
  el("oldVideoCleanupModal").hidden = true;
  if (el("localAssetsModal").hidden) document.body.classList.remove("modal-open");
}

function openUnlockAssets(ownerDeviceId, ownerName) {
  state.unlockOwnerDeviceId = ownerDeviceId;
  el("unlockAssetsOwner").textContent = `${localized("所属设备：", "Device: ")}${ownerName || ownerDeviceId}`;
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
    el("unlockAssetsError").textContent = localized("密钥长度必须为 8 至 256 个字符", "The key must be 8 to 256 characters");
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
    showToast(localized("该设备的本地加密素材已解锁", "Encrypted assets for this device are unlocked"));
  } catch (error) {
    el("unlockAssetsError").textContent = error.message;
  }
}

async function parseSseResponse(response, onEvent) {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || localized(`请求失败 (${response.status})`, `Request failed (${response.status})`));
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
  if (source.length < 2) return showError(localized("请先输入歌曲主题、曲风或创作要求", "Enter a song theme, style, or brief first"));
  if (!el("aiEnabled").checked) {
    openGlobalSettings("model");
    return showError(localized("请在右上角设置的模型页签启用 AI 提示词优化", "Enable AI prompt assistance in the Model tab of Settings"));
  }
  const baseUrl = el("aiBaseUrl").value.trim();
  const model = el("aiModel").value.trim();
  if (!baseUrl || !model) {
    openGlobalSettings("model");
    return showError(localized("请在模型页签填写 OpenAI Base URL 和模型名称", "Enter an OpenAI Base URL and model in the Model tab of Settings"));
  }
  const button = task === "lyrics" ? el("writeLyrics") : el("optimizePrompt");
  let output = "";
  button.disabled = true;
  let streamError = "";
  try {
    const response = await fetch("/api/v1/music/assist", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept-Language": state.locale === "en" ? "en-US,en;q=0.9" : "zh-CN" },
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
      if (type === "error") streamError = data.message || localized("AI 音乐辅助失败", "AI music assistance failed");
    });
    if (streamError) throw new Error(streamError);
    if (!output.trim()) throw new Error(localized("AI 服务没有返回可用内容", "The AI service returned no usable content"));
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
  if (source.length < 2) return showError(localized("请先输入需要优化的自然语言描述", "Enter a prompt to optimize first"));
  if (!el("aiEnabled").checked) {
    openGlobalSettings("model");
    return showError(localized("请在右上角设置的模型页签启用 AI 提示词优化", "Enable AI prompt assistance in the Model tab of Settings"));
  }
  const baseUrl = el("aiBaseUrl").value.trim();
  const model = el("aiModel").value.trim();
  if (!baseUrl || !model) {
    openGlobalSettings("model");
    return showError(localized("请在模型页签填写 OpenAI Base URL 和模型名称", "Enter an OpenAI Base URL and model in the Model tab of Settings"));
  }

  const button = el("optimizePrompt");
  let optimizedOutput = "";
  button.disabled = true;
  let streamError = "";
  try {
    const response = await fetch("/api/v1/prompts/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept-Language": state.locale === "en" ? "en-US,en;q=0.9" : "zh-CN" },
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
        streamError = data.message || localized("优化失败", "Optimization failed");
      }
    });
    if (streamError) throw new Error(streamError);
    if (!optimizedOutput.trim()) throw new Error(localized("AI 服务没有返回可用内容", "The AI service returned no usable content"));
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
  el("assetFoldersPanel").hidden = state.incognito;
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
  state.assetSelectedIds.clear();
  state.assetEditMode = false;
  if (state.incognito) state.assetFolderId = "";
  renderAssets(0);
  renderAssetFolders();
  renderConversationFeed("bottom");
  await Promise.all([loadAssetFolders(), loadAssets({ reset: true }), refreshConversation(true), loadWorkflows()]);
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
  state.opsPosition.x = 0;
  state.opsPosition.y = 0;
  applyOpsPosition();
}

function applyOpsPosition() {
  const windowNode = el("opsWindow");
  const rect = windowNode.getBoundingClientRect();
  const maxX = Math.max(0, (window.innerWidth - rect.width) / 2 - 12);
  const maxY = Math.max(0, (window.innerHeight - rect.height) / 2 - 12);
  state.opsPosition.x = Math.min(maxX, Math.max(-maxX, state.opsPosition.x));
  state.opsPosition.y = Math.min(maxY, Math.max(-maxY, state.opsPosition.y));
  windowNode.style.transform = `translate3d(${state.opsPosition.x}px, ${state.opsPosition.y}px, 0)`;
}

function openOpsWindow() {
  if (el("openOps").hidden) return;
  el("opsModal").hidden = false;
  el("openOps").classList.add("is-active");
  el("openOps").setAttribute("aria-pressed", "true");
  if (!state.opsPositionInitialized) {
    resetOpsPosition();
    state.opsPositionInitialized = true;
  } else {
    applyOpsPosition();
  }
  refreshIcons();
}

function closeOpsWindow() {
  el("opsModal").hidden = true;
  el("openOps").classList.remove("is-active");
  el("openOps").setAttribute("aria-pressed", "false");
}

function openAssetDrawer() {
  el("assetSidebar").classList.add("mobile-open");
  el("mobileScrim").hidden = false;
}

function closeAssetDrawer() {
  el("assetSidebar").classList.remove("mobile-open");
  el("mobileScrim").hidden = true;
}

function sidebarWidthLimit() {
  return Math.max(SIDEBAR_WIDTH_MIN, Math.floor(window.innerWidth * SIDEBAR_WIDTH_MAX_RATIO));
}

function setSidebarWidth(value, persist = false) {
  const shell = document.querySelector(".app-shell");
  const resizer = el("sidebarResizer");
  if (!shell || window.innerWidth <= 860) return;
  const width = Math.round(Math.min(sidebarWidthLimit(), Math.max(SIDEBAR_WIDTH_MIN, Number(value) || 470)));
  shell.style.setProperty("--asset-sidebar-width", `${width}px`);
  resizer?.setAttribute("aria-valuemax", String(sidebarWidthLimit()));
  resizer?.setAttribute("aria-valuenow", String(width));
  if (persist) localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(width));
}

function restoreSidebarWidth() {
  const stored = Number(localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY));
  setSidebarWidth(Number.isFinite(stored) && stored > 0 ? stored : 470);
}

let sidebarResizeState = null;
function startSidebarResize(event) {
  if (window.innerWidth <= 860 || event.button !== 0) return;
  event.preventDefault();
  const shell = document.querySelector(".app-shell");
  const width = shell?.getBoundingClientRect().width ? el("assetSidebar").getBoundingClientRect().width : 320;
  sidebarResizeState = { startX: event.clientX, startWidth: width };
  document.body.classList.add("sidebar-resizing");
}

function moveSidebarResize(event) {
  if (!sidebarResizeState) return;
  setSidebarWidth(sidebarResizeState.startWidth + event.clientX - sidebarResizeState.startX);
}

function stopSidebarResize() {
  if (!sidebarResizeState) return;
  const width = el("assetSidebar").getBoundingClientRect().width;
  setSidebarWidth(width, true);
  sidebarResizeState = null;
  document.body.classList.remove("sidebar-resizing");
  ensureAssetGridFilled().catch((error) => showError(error.message));
}

function dismissToast(toast) {
  if (!toast || toast.dataset.leaving === "true") return;
  toast.dataset.leaving = "true";
  clearTimeout(Number(toast.dataset.timer || 0));
  toast.classList.add("is-leaving");
  window.setTimeout(() => {
    const region = toast.parentElement;
    if (!region) return;
    const siblings = [...region.children].filter(
      (item) => item !== toast && !item.classList.contains("is-leaving")
    );
    const positions = new Map(siblings.map((item) => [item, item.getBoundingClientRect().top]));
    toast.remove();
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    siblings.forEach((item) => {
      const delta = positions.get(item) - item.getBoundingClientRect().top;
      if (Math.abs(delta) < 0.5) return;
      item.animate(
        [{ transform: `translateY(${delta}px)` }, { transform: "translateY(0)" }],
        { duration: 220, easing: "cubic-bezier(.22, 1, .36, 1)" }
      );
    });
  }, 240);
}

function showToast(message, type = "") {
  if (!message) return;
  const region = el("toastRegion");
  if (!region) return;
  const toast = document.createElement("div");
  toast.className = `toast${type ? ` ${type}` : ""}`;
  toast.setAttribute("role", type === "error" ? "alert" : "status");
  toast.innerHTML = `<span class="toast-icon" aria-hidden="true">${icon(type === "error" ? "circle-alert" : "check")}</span><span class="toast-copy">${escapeHtml(message)}</span>`;
  toast.addEventListener("click", () => dismissToast(toast), { once: true });
  region.append(toast);
  refreshIcons();
  const timer = window.setTimeout(() => dismissToast(toast), 4200);
  toast.dataset.timer = String(timer);
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
    loadAssetFolders(),
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

document.addEventListener("paste", async (event) => {
  const file = clipboardImageFile(event);
  if (!file) return;
  event.preventDefault();
  const added = await addFiles([file], state.pendingRunningHubMediaField);
  if (added) showToast(localized("已从剪贴板添加图片", "Image pasted from clipboard"));
  updateModelUi();
});

referenceInput.addEventListener("change", async () => {
  await addFiles(referenceInput.files, state.pendingRunningHubMediaField);
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
  if (!jobId) return await addFiles(event.dataTransfer.files);
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

document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-preview-url]");
  if (!trigger) return;
  const media = event.target.closest("audio, video");
  if (media && media.hasAttribute("controls")) return;
  event.preventDefault();
  event.stopPropagation();
  openAssetPreview({
    url: trigger.dataset.previewUrl,
    name: trigger.dataset.previewName || "",
    type: trigger.dataset.previewType || "",
  });
});

el("assetGrid").addEventListener("click", (event) => {
  const folderAction = event.target.closest("[data-folder-action]");
  if (folderAction) {
    event.stopPropagation();
    if (folderAction.dataset.folderAction === "rename") openAssetFolderName(folderAction.dataset.folderId);
    if (folderAction.dataset.folderAction === "delete") deleteAssetFolder(folderAction.dataset.folderId);
    return;
  }
  const back = event.target.closest("[data-asset-folder-back]");
  if (back) {
    selectAssetFolder("");
    return;
  }
  const folderCard = event.target.closest("[data-asset-folder-card]");
  if (folderCard) {
    folderCard.focus();
    return;
  }
  const selection = event.target.closest("[data-asset-select]");
  if (selection) return;
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
  if (!card) return;
  if (state.assetEditMode && card.dataset.assetEditable === "true") {
    if (state.assetSelectedIds.has(card.dataset.assetJob)) state.assetSelectedIds.delete(card.dataset.assetJob);
    else state.assetSelectedIds.add(card.dataset.assetJob);
    renderAssets();
    return;
  }
  openAssetDetail(card.dataset.assetJob);
});
el("assetGrid").addEventListener("dblclick", (event) => {
  if (event.target.closest("[data-folder-action]")) return;
  const folderCard = event.target.closest("[data-asset-folder-card]");
  if (folderCard) selectAssetFolder(folderCard.dataset.assetFolderCard);
});
el("assetGrid").addEventListener("change", (event) => {
  const checkbox = event.target.closest("[data-asset-select] input");
  if (!checkbox) return;
  if (checkbox.checked) state.assetSelectedIds.add(checkbox.value);
  else state.assetSelectedIds.delete(checkbox.value);
  renderAssets();
});
el("assetGrid").addEventListener("dragstart", (event) => {
  const sourceCard = event.target.closest("[data-asset-job]");
  if (state.assetEditMode) {
    if (!sourceCard || sourceCard.dataset.assetEditable !== "true") {
      event.preventDefault();
      return;
    }
    const jobId = sourceCard.dataset.assetJob;
    if (!state.assetSelectedIds.has(jobId)) {
      state.assetSelectedIds.clear();
      state.assetSelectedIds.add(jobId);
      renderAssets();
    }
    const jobIds = Array.from(state.assetSelectedIds);
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("application/x-h3-asset-jobs", JSON.stringify(jobIds));
    event.dataTransfer.setData("text/plain", jobIds.join(","));
    sourceCard.classList.add("dragging");
    return;
  }
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
  const folderCard = event.target.closest("[data-asset-folder-card]");
  if (folderCard && ["Enter", " "].includes(event.key)) {
    event.preventDefault();
    selectAssetFolder(folderCard.dataset.assetFolderCard);
    return;
  }
  if (event.target.closest("[data-asset-folder-back]") && ["Enter", " "].includes(event.key)) {
    event.preventDefault();
    selectAssetFolder("");
    return;
  }
  if (["Enter", " "].includes(event.key) && event.target.matches("[data-asset-job]")) {
    event.preventDefault();
    if (state.assetEditMode && event.target.dataset.assetEditable === "true") {
      const jobId = event.target.dataset.assetJob;
      if (state.assetSelectedIds.has(jobId)) state.assetSelectedIds.delete(jobId);
      else state.assetSelectedIds.add(jobId);
      renderAssets();
      return;
    }
    openAssetDetail(event.target.dataset.assetJob);
  }
});
el("assetGrid").addEventListener("dragover", (event) => {
  if (!state.assetEditMode) return;
  const folderCard = event.target.closest("[data-folder-drop-id]");
  if (!folderCard) return;
  event.preventDefault();
  folderCard.classList.add("drag-over");
});
el("assetGrid").addEventListener("dragleave", (event) => {
  event.target.closest("[data-folder-drop-id]")?.classList.remove("drag-over");
});
el("assetGrid").addEventListener("drop", (event) => {
  if (!state.assetEditMode) return;
  const folderCard = event.target.closest("[data-folder-drop-id]");
  if (!folderCard) return;
  event.preventDefault();
  folderCard.classList.remove("drag-over");
  let jobIds = [];
  try { jobIds = JSON.parse(event.dataTransfer.getData("application/x-h3-asset-jobs") || "[]"); } catch { jobIds = []; }
  if (jobIds.length) moveJobsToFolder(jobIds, folderCard.dataset.folderDropId);
});
el("assetGrid").addEventListener("scroll", () => {
  const grid = el("assetGrid");
  if (grid.scrollHeight - grid.scrollTop - grid.clientHeight < 180) loadAssets();
}, { passive: true });

el("conversationFeed").addEventListener("click", (event) => {
  const action = event.target.closest("[data-job-action]");
  if (action) return handleJobAction(action.dataset.jobAction, action.dataset.jobId);
  const outputDetail = event.target.closest("[data-output-detail]");
  if (outputDetail) return openAssetDetail(outputDetail.dataset.outputDetail);
  const gridCard = event.target.closest("[data-grid-job]");
  if (gridCard) return openAssetDetail(gridCard.dataset.gridJob);
});
el("conversationFeed").addEventListener("keydown", (event) => {
  const gridCard = event.target.closest("[data-grid-job]");
  if (!gridCard || !["Enter", " "].includes(event.key)) return;
  event.preventDefault();
  openAssetDetail(gridCard.dataset.gridJob);
});
el("conversationFeed").addEventListener("scroll", () => {
  const feed = el("conversationFeed");
  const currentTop = feed.scrollTop;
  const movingUp = currentTop < state.conversationScrollTop;
  state.conversationScrollTop = currentTop;
  if (!state.conversationReady) return;
  if (currentMessageStyle() === "grid") {
    if (feed.scrollHeight - currentTop - feed.clientHeight < 240) loadOlderMessages();
    return;
  }
  if (movingUp && currentTop < 72) loadOlderMessages();
}, { passive: true });

el("queueList").addEventListener("click", (event) => {
  const action = event.target.closest("[data-job-action]");
  if (action) return handleJobAction(action.dataset.jobAction, action.dataset.jobId);
  const row = event.target.closest("[data-scroll-job]");
  if (row) scrollToGeneratedOutput(row.dataset.scrollJob);
});
el("logList").addEventListener("click", (event) => {
  const item = event.target.closest("[data-scroll-job]");
  if (item) scrollToGeneratedOutput(item.dataset.scrollJob);
});
el("logList").addEventListener("scroll", () => {
  const container = el("logList");
  state.logFollowTail = container.scrollHeight - container.scrollTop - container.clientHeight < 24;
});

el("exitEdit").addEventListener("click", resetComposer);
el("editAssetsButton").addEventListener("click", () => setAssetEditMode(!state.assetEditMode));
el("newAssetFolder").addEventListener("click", () => openAssetFolderName());
el("moveSelectedAssets").addEventListener("click", moveSelectedAssets);
el("assetStatusFilter").addEventListener("change", () => loadAssets({ reset: true }));
el("refreshAssets").addEventListener("click", () => refreshSharedData());
let assetSearchTimer = null;
el("assetSearch").addEventListener("input", () => {
  clearTimeout(assetSearchTimer);
  assetSearchTimer = setTimeout(() => loadAssets({ reset: true }), 250);
});

el("assetFolderNameForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = el("assetFolderName").value.trim();
  if (!name) return;
  const editingId = state.assetFolderNameEditId;
  try {
    await api(editingId ? `/api/v1/asset-folders/${encodeURIComponent(editingId)}` : "/api/v1/asset-folders", {
      method: editingId ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    closeAssetFolderName();
    await loadAssetFolders();
    if (!editingId) selectAssetFolder(state.assetFolders[state.assetFolders.length - 1]?.id || "");
  } catch (error) {
    el("assetFolderNameError").textContent = error.message;
  }
});
el("closeAssetFolderName").addEventListener("click", closeAssetFolderName);
el("cancelAssetFolderName").addEventListener("click", closeAssetFolderName);
el("assetFolderNameModal").addEventListener("click", (event) => { if (event.target === el("assetFolderNameModal")) closeAssetFolderName(); });
el("assetFolderPickerList").addEventListener("click", (event) => {
  const row = event.target.closest("[data-picker-folder-id]");
  if (row) resolveAssetFolderPicker(row.dataset.pickerFolderId);
});
el("closeAssetFolderPicker").addEventListener("click", closeAssetFolderPicker);
el("assetFolderPickerModal").addEventListener("click", (event) => { if (event.target === el("assetFolderPickerModal")) closeAssetFolderPicker(); });

el("assetDetailModal").addEventListener("pointerdown", (event) => {
  const windowNode = event.target.closest(".asset-detail-dialog");
  if (!windowNode) return;
  const record = state.assetDetailWindows.get(windowNode.dataset.detailWindowId);
  if (record) {
    state.assetDetailActiveWindowId = record.id;
    state.assetDetailJob = record.job;
    bringAssetDetailToFront(record.id);
  }
});
el("assetDetailModal").addEventListener("click", (event) => {
  const windowNode = event.target.closest(".asset-detail-dialog");
  if (!windowNode) return;
  const record = state.assetDetailWindows.get(windowNode.dataset.detailWindowId);
  if (!record) return;
  if (event.target.closest("[data-detail-close]")) {
    closeAssetDetail(record.id);
    return;
  }
  if (event.target.closest("[data-detail-toggle]")) {
    toggleAssetDetailInfo(record.id);
    return;
  }
  const action = event.target.closest("[data-detail-action]");
  if (!action || !record.job) return;
  state.assetDetailActiveWindowId = record.id;
  state.assetDetailJob = record.job;
  const jobId = record.job.id;
  if (action.dataset.detailAction === "reuse") backfillJob(jobId);
  if (action.dataset.detailAction === "input") useGeneratedOutputAsInput(jobId).catch((error) => { detailElement(record, "assetDetailError").textContent = error.message; });
  if (action.dataset.detailAction === "video-upscale") openVideoUpscaleDialog(jobId);
  if (action.dataset.detailAction === "regenerate") regenerateJob(jobId);
  if (action.dataset.detailAction === "rename") renameJobOutput(jobId);
  if (action.dataset.detailAction === "delete") deleteJob(jobId).then((deleted) => {
    if (deleted) closeAssetDetail(record.id);
    else detailElement(record, "assetDetailError").textContent = el("formError").textContent;
  });
});
el("assetDetailModal").addEventListener("pointerdown", (event) => {
  const handle = event.target.closest("[data-detail-drag-handle]");
  const windowNode = event.target.closest(".asset-detail-dialog");
  if (!handle || !windowNode || event.target.closest("button, a")) return;
  startAssetDetailDrag(event, windowNode.dataset.detailWindowId);
});
window.addEventListener("pointermove", moveAssetDetailDrag);
window.addEventListener("pointerup", stopAssetDetailDrag);
window.addEventListener("pointercancel", stopAssetDetailDrag);
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
el("openGlobalSettings").addEventListener("click", () => openGlobalSettings("system"));
document.querySelectorAll("[data-settings-tab]").forEach((button) => {
  button.addEventListener("click", () => setSettingsTab(button.dataset.settingsTab));
});
document.querySelectorAll("[data-message-style]").forEach((button) => {
  button.addEventListener("click", () => applyMessageStyle(button.dataset.messageStyle));
});
el("optimizeMarkdown").addEventListener("change", () => applyMarkdownOptimization(el("optimizeMarkdown").checked));
el("themeGrid")?.addEventListener("click", (event) => {
  const card = event.target.closest("[data-theme-option]");
  if (!card) return;
  applyTheme(card.dataset.themeOption);
  card.focus();
});
el("themeGrid")?.addEventListener("keydown", (event) => {
  if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
  const cards = Array.from(document.querySelectorAll("[data-theme-option]"));
  const index = cards.indexOf(document.activeElement);
  if (index < 0) return;
  event.preventDefault();
  const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1;
  const next = cards[(index + step + cards.length) % cards.length];
  applyTheme(next.dataset.themeOption);
  next.focus();
});
el("closeGlobalSettings").addEventListener("click", closeGlobalSettings);
el("globalSettingsModal").addEventListener("click", (event) => { if (event.target === el("globalSettingsModal")) closeGlobalSettings(); });
el("globalSettingsForm").addEventListener("submit", saveGeneralSettings);
el("bindLocalComfyui").addEventListener("change", () => {
  state.bindLocalComfyui = el("bindLocalComfyui").checked;
  syncLocalComfyFields();
});
el("toggleRemoteRecordsKey").addEventListener("click", () => togglePasswordField("remoteRecordsKey", "toggleRemoteRecordsKey"));
el("manageLocalAssets").addEventListener("click", openLocalAssets);
el("closeLocalAssets").addEventListener("click", closeLocalAssets);
el("deleteLocalArtifacts").addEventListener("click", deleteLocalArtifacts);
el("clearOldVideos").addEventListener("click", clearOldVideos);
el("closeOldVideoCleanup").addEventListener("click", closeOldVideoCleanup);
el("cancelOldVideoCleanup").addEventListener("click", closeOldVideoCleanup);
el("confirmOldVideoCleanup").addEventListener("click", confirmOldVideoCleanup);
el("oldVideoCleanupModal").addEventListener("click", (event) => { if (event.target === el("oldVideoCleanupModal")) closeOldVideoCleanup(); });
el("localAssetsModal").addEventListener("click", (event) => { if (event.target === el("localAssetsModal")) closeLocalAssets(); });
el("closeLocalAssetPreview").addEventListener("click", closeLocalAssetPreview);
el("localAssetPreviewBody").addEventListener("click", (event) => {
  const control = event.target.closest("[data-preview-zoom]");
  if (control) {
    if (control.dataset.previewZoom === "in") setAssetPreviewZoom(assetPreviewZoom * 1.25);
    if (control.dataset.previewZoom === "out") setAssetPreviewZoom(assetPreviewZoom / 1.25);
    if (control.dataset.previewZoom === "reset") setAssetPreviewZoom(1);
    return;
  }
  if (event.target.closest("[data-preview-image]")) {
    setAssetPreviewZoom(assetPreviewZoom > 1.001 ? 1 : 2);
  }
});
el("localAssetPreviewBody").addEventListener("wheel", (event) => {
  if (!event.ctrlKey && !event.metaKey) return;
  event.preventDefault();
  setAssetPreviewZoom(assetPreviewZoom * (event.deltaY < 0 ? 1.1 : 0.9));
}, { passive: false });
el("localAssetPreviewModal").addEventListener("click", (event) => { if (event.target === el("localAssetPreviewModal")) closeLocalAssetPreview(); });
el("localAssetsList").addEventListener("change", (event) => {
  const checkbox = event.target.closest('input[type="checkbox"]');
  if (!checkbox) return;
  if (checkbox.checked) state.localAssetSelected.add(checkbox.value);
  else state.localAssetSelected.delete(checkbox.value);
  syncLocalAssetSelectAll();
});
el("localAssetsList").addEventListener("click", (event) => {
  const remove = event.target.closest("[data-local-folder-delete]");
  if (remove) {
    event.stopPropagation();
    deleteAssetFolder(remove.dataset.localFolderDelete).then(() => loadLocalAssetFolders()).catch(() => {});
    return;
  }
  const folder = event.target.closest("[data-local-folder-card]");
  if (folder) {
    folder.focus();
    return;
  }
  const back = event.target.closest("[data-local-folder-back]");
  if (back) {
    selectLocalAssetFolder("__root__");
    return;
  }
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
el("localAssetsList").addEventListener("dblclick", (event) => {
  if (event.target.closest("[data-local-folder-delete]")) return;
  const folder = event.target.closest("[data-local-folder-card]");
  if (folder) selectLocalAssetFolder(folder.dataset.localFolderCard);
});
el("localAssetsList").addEventListener("keydown", (event) => {
  const folder = event.target.closest("[data-local-folder-card]");
  if (folder && ["Enter", " "].includes(event.key)) {
    event.preventDefault();
    selectLocalAssetFolder(folder.dataset.localFolderCard);
    return;
  }
  const back = event.target.closest("[data-local-folder-back]");
  if (back && ["Enter", " "].includes(event.key)) {
    event.preventDefault();
    selectLocalAssetFolder("__root__");
    return;
  }
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
  state.localAssets.filter((asset) => !asset.asset_deleted && asset.can_delete).forEach((asset) => {
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
el("workflowSelect").addEventListener("change", () => renderNodeOptions(state.nodes));
el("upscaleCategory").addEventListener("change", updateModelUi);
el("upscaleScale").addEventListener("change", updateModelUi);
el("comfyNode").addEventListener("change", updateModelUi);
el("cancelAutoUpscaleConfirm").addEventListener("click", () => closeAutoUpscaleConfirm(false));
el("cancelAutoUpscaleConfirmButton").addEventListener("click", () => closeAutoUpscaleConfirm(false));
el("autoUpscaleConfirmModal").addEventListener("click", (event) => {
  if (event.target === el("autoUpscaleConfirmModal")) closeAutoUpscaleConfirm(false);
});
el("autoUpscaleConfirmForm").addEventListener("submit", (event) => {
  event.preventDefault();
  el("upscaleCategory").value = el("autoUpscaleConfirmCategory").value;
  el("upscaleScale").value = el("autoUpscaleConfirmScale").value;
  closeAutoUpscaleConfirm(true);
});
el("closeVideoUpscale").addEventListener("click", closeVideoUpscaleDialog);
el("cancelVideoUpscale").addEventListener("click", closeVideoUpscaleDialog);
el("videoUpscaleModal").addEventListener("click", (event) => {
  if (event.target === el("videoUpscaleModal")) closeVideoUpscaleDialog();
});
el("videoUpscaleForm").addEventListener("submit", submitVideoUpscale);
el("duration").closest(".duration-control").addEventListener("mouseenter", positionDurationTooltip);
el("duration").closest(".duration-control").addEventListener("focusin", positionDurationTooltip);

el("openNodeManager").addEventListener("click", openNodeManager);
el("closeNodeManager").addEventListener("click", closeNodeManager);
el("addNodeButton").addEventListener("click", () => openNodeEditor());
el("cancelNodeEdit").addEventListener("click", closeNodeEditor);
el("cancelNodeEditIcon").addEventListener("click", closeNodeEditor);
el("nodeEditorModal").addEventListener("click", (event) => {
  if (event.target === el("nodeEditorModal")) closeNodeEditor();
});
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
el("nodeList").addEventListener("change", (event) => {
  const input = event.target.closest('[data-node-action="power"]');
  if (!input) return;
  const row = input.closest("[data-node-id]");
  if (!row) return;
  toggleLocalComfy(row.dataset.nodeId, input.checked);
});
el("nodeModal").addEventListener("click", (event) => {
  if (event.target === el("nodeModal")) closeNodeManager();
});
el("openWorkflowManager").addEventListener("click", openWorkflowManager);
el("closeWorkflowManager").addEventListener("click", closeWorkflowManager);
el("addWorkflowButton").addEventListener("click", openNewWorkflowEditor);
el("cancelWorkflowEdit").addEventListener("click", closeWorkflowEditor);
el("cancelWorkflowEditIcon").addEventListener("click", closeWorkflowEditor);
el("workflowEditor").addEventListener("submit", saveWorkflow);
el("workflowJsonFile").addEventListener("change", (event) => handleWorkflowJsonFile(event.target.files?.[0]));
el("addWorkflowFieldMapping").addEventListener("click", () => {
  el("workflowFieldMappings").append(renderWorkflowFieldMapping());
  refreshIcons();
});
el("addWorkflowReferenceMapping").addEventListener("click", () => {
  el("workflowReferenceMappings").append(renderWorkflowReferenceMapping());
  refreshIcons();
});
el("workflowList").addEventListener("change", (event) => {
  const input = event.target.closest('[data-workflow-action="visibility"]');
  if (!input) return;
  const workflow = state.workflows.find((item) => item.id === input.closest("[data-workflow-id]")?.dataset.workflowId);
  if (workflow) setWorkflowVisibility(workflow, input.checked);
});
el("workflowList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-workflow-action]");
  const workflowId = button?.closest("[data-workflow-id]")?.dataset.workflowId;
  if (!button || !workflowId || button.matches('input[type="checkbox"]')) return;
  const action = button.dataset.workflowAction;
  if (action === "edit") openWorkflowEditor(workflowId);
  if (action === "download") downloadWorkflow(workflowId);
  if (action === "sync") syncWorkflow(workflowId, false);
  if (action === "verify") {
    setWorkflowManagerError(localized("上传同名 JSON 到目标 ComfyUI 的 workflows 用户目录后执行校验", "Upload the JSON with the same filename to the target ComfyUI workflows user directory, then verify"));
    syncWorkflow(workflowId, true);
  }
  if (action === "delete") deleteWorkflow(workflowId);
});
el("workflowModal").addEventListener("click", (event) => {
  if (event.target === el("workflowModal")) closeWorkflowManager();
});
el("workflowEditorModal").addEventListener("click", (event) => {
  if (event.target === el("workflowEditorModal")) closeWorkflowEditor();
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
  if (event.key === "Escape" && !el("workflowEditorModal").hidden) {
    closeWorkflowEditor();
    return;
  }
  if (event.key === "Escape" && !el("workflowModal").hidden) {
    closeWorkflowManager();
    return;
  }
  if (event.key === "Escape" && !el("localAssetPreviewModal").hidden) {
    closeLocalAssetPreview();
    return;
  }
  if (event.key === "Escape" && !el("opsModal").hidden) {
    closeOpsWindow();
    return;
  }
  if (event.key === "Escape" && !el("videoUpscaleModal").hidden) {
    closeVideoUpscaleDialog();
    return;
  }
  if (event.key === "Escape" && !el("secretOverlay").hidden) closeSecretDialog();
  if (event.key === "Escape" && !el("peeringModal").hidden) closePeeringDialog();
  if (event.key === "Escape" && !el("nodeEditorModal").hidden) {
    closeNodeEditor();
    return;
  }
  if (event.key === "Escape" && !el("nodeModal").hidden) closeNodeManager();
  if (event.key === "Escape" && !el("assetDetailModal").hidden) closeAssetDetail();
});

el("clearVisibleLogs").addEventListener("click", () => {
  state.logFloor = Date.now();
  renderLogs(state.logs);
});
el("openOps").addEventListener("click", () => {
  if (el("opsModal").hidden) openOpsWindow();
  else closeOpsWindow();
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

el("sidebarResizer").addEventListener("pointerdown", startSidebarResize);
window.addEventListener("pointermove", moveSidebarResize);
window.addEventListener("pointerup", stopSidebarResize);
window.addEventListener("pointercancel", stopSidebarResize);
el("sidebarResizer").addEventListener("keydown", (event) => {
  const current = el("assetSidebar").getBoundingClientRect().width;
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    event.preventDefault();
    setSidebarWidth(current + (event.key === "ArrowRight" ? 16 : -16), true);
  }
  if (event.key === "Home") {
    event.preventDefault();
    setSidebarWidth(SIDEBAR_WIDTH_MIN, true);
  }
  if (event.key === "End") {
    event.preventDefault();
    setSidebarWidth(sidebarWidthLimit(), true);
  }
});
window.addEventListener("resize", () => {
  if (!el("opsModal").hidden) applyOpsPosition();
  applyLauncherPosition();
  if (window.innerWidth > 860) setSidebarWidth(el("assetSidebar").getBoundingClientRect().width, false);
});

async function initialize() {
  applyTheme(currentTheme(), { persist: false });
  applyMessageStyle(storedMessageStyle(), { persist: false, render: false });
  let markdownEnabled = true;
  try { markdownEnabled = localStorage.getItem(OPTIMIZE_MARKDOWN_STORAGE_KEY) !== "0"; } catch (error) { /* storage disabled */ }
  applyMarkdownOptimization(markdownEnabled, { persist: false, render: false });
  watchSystemTheme();
  if (ANDROID_CLIENT) {
    document.body.classList.add("android-client");
    el("androidServerSettings").hidden = false;
    el("openGlobalSettings").hidden = true;
    el("languageToggle").hidden = true;
    el("apiDocsLink").hidden = true;
    el("androidServerSettings").addEventListener("click", () => window.AndroidApp?.openServerSettings());
  }
  restoreSidebarWidth();
  applyStaticLocale();
  initHeaderTooltips();
  syncHeaderTips();
  updateModelUi();
  updateIncognitoUi();
  renderReferences();
  refreshIcons();
  startPeeringPolling();
  connectEventStream();
  await Promise.allSettled([
    loadAiConfig().catch((error) => showError(error.message)),
    loadGeneralSettings().catch((error) => showError(error.message)),
    loadWorkflows().catch((error) => showError(error.message)),
    refreshPeeringStatus({ notifyEvents: false }),
    checkHealth(),
    refreshSharedData(),
  ]);
  if (ANDROID_CLIENT) {
    const select = el("workflowSelect");
    if (select && Array.from(select.options).some((option) => option.value === "preset-fl2va-turbo")) {
      select.value = "preset-fl2va-turbo";
    }
    el("steps").value = "8";
    el("autoUpscale").checked = false;
    updateModelUi();
  }
}

initialize();
el("lucideScript")?.addEventListener("load", refreshIcons);
window.addEventListener("load", refreshIcons);
window.addEventListener("beforeunload", () => {
  state.stream?.close();
  clearInterval(state.peeringTimer);
  clearInterval(state.peeringPollTimer);
});
