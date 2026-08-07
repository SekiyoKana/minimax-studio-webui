const state = {
  references: [],
  assets: [],
  assetPage: 1,
  assetPages: 1,
  assetPageSize: 16,
  conversations: [],
  conversationPage: 1,
  conversationPages: 1,
  conversationPageSize: 10,
  conversationLoading: false,
  conversationRefreshPending: false,
  editingJobId: null,
  lastRevision: -1,
  logFloor: 0,
  queue: [],
  logs: [],
  stream: null,
  incognito: false,
  incognitoCode: "",
  brandClicks: [],
  opsPosition: { x: 0, y: 0 },
};

const el = (id) => document.getElementById(id);
const form = el("generationForm");
const promptInput = el("prompt");
const referenceInput = el("referenceInput");

const STATUS_LABELS = {
  queued: "排队中",
  running: "生成中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

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
  return new Intl.DateTimeFormat("zh-CN", {
    month: includeDate ? "2-digit" : undefined,
    day: includeDate ? "2-digit" : undefined,
    hour: "2-digit",
    minute: "2-digit",
    second: includeDate ? "2-digit" : undefined,
    hour12: false,
  }).format(date);
}

function modelLabel(job) {
  return job.request?.model_variant === "ref2va-fp8" ? "Ref2VA FP8" : "FL2VA FP8";
}

function executionModeLabel(job) {
  if (job.request?.execution_mode === "h3-nsfw") return "H3 NSFW · NaughtyTimes LoRA";
  if (job.request?.execution_mode === "turbo-lora") return "Turbo LoRA · 双时间轴采样";
  if (job.request?.execution_mode === "speed-cache") return "Speed Cache（已停用）";
  return "普通流 · 原生 H3";
}

function executionModeClass(job) {
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
  if (hours) return `${hours} 小时 ${String(minutes).padStart(2, "0")} 分 ${String(remainingSeconds).padStart(2, "0")} 秒`;
  if (minutes) return `${minutes} 分 ${String(remainingSeconds).padStart(2, "0")} 秒`;
  return `${remainingSeconds} 秒`;
}

function shortTitle(job) {
  const value = job.title || job.request?.prompt || job.id;
  return String(value).replaceAll("\n", " ").slice(0, 42);
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

function jobScope() {
  return state.incognito ? "incognito" : "normal";
}

function isRef2VA(variant = selectedVariant()) {
  return variant === "ref2va-fp8";
}

function referenceLimits(variant = selectedVariant()) {
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

function referenceLabels(references = state.references, variant = selectedVariant()) {
  const counts = { image: 0, video: 0, audio: 0 };
  return references.map((item) => {
    const kind = item.kind || item.type;
    counts[kind] += 1;
    if (!isRef2VA(variant)) return counts.image === 1 ? "首帧" : "尾帧";
    return `<${{ image: "Picture", video: "Video", audio: "Audio" }[kind]} ${counts[kind]}>`;
  });
}

function validateReferenceSet(references = state.references, variant = selectedVariant()) {
  if (!references.length) return "请至少添加一份参考素材";
  const limits = referenceLimits(variant);
  const counts = { image: 0, video: 0, audio: 0 };
  references.forEach((item) => { counts[item.kind || item.type] += 1; });
  if (!isRef2VA(variant) && (counts.image !== references.length || counts.image > 2)) {
    return "FL2VA 仅支持 1 张首帧，或首帧和尾帧两张图片";
  }
  if (counts.image > limits.image || counts.video > limits.video || counts.audio > limits.audio) {
    return "Ref2VA 最多支持 9 张图片、3 段视频和 3 段音频";
  }
  return "";
}

function showError(message) {
  el("formError").textContent = message || "";
}

async function api(url, options = {}) {
  const response = await fetch(url, { cache: "no-store", ...options });
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  if (!response.ok) throw new Error(payload.detail || `请求失败 (${response.status})`);
  return payload;
}

function updateModelUi() {
  const nsfw = selectedExecutionMode() === "h3-nsfw";
  const fl2vaOption = el("modelVariant").querySelector('option[value="fl2va-fp8"]');
  fl2vaOption.disabled = nsfw;
  if (nsfw) el("modelVariant").value = "ref2va-fp8";
  const ref2va = isRef2VA();
  referenceInput.accept = ref2va ? "image/*,video/*,audio/*" : "image/*";
  el("addReference").title = ref2va ? "添加图片、视频或音频参考" : "添加首帧或尾帧";
  el("addReference").setAttribute("aria-label", el("addReference").title);
  renderReferences();
  const error = validateReferenceSet(state.references);
  showError(error === "请至少添加一份参考素材" ? "" : error);
}

function addFiles(files) {
  if (state.editingJobId) {
    showError("修改排队任务时不能更换参考素材");
    return;
  }
  let error = "";
  Array.from(files).forEach((file) => {
    const kind = kindFor(file);
    if (!kind) {
      error = `不支持的素材类型：${file.name}`;
      return;
    }
    const limits = referenceLimits();
    const current = state.references.filter((item) => (item.kind || item.type) === kind).length;
    if (!limits[kind]) {
      error = `FL2VA 仅支持图片：${file.name}`;
      return;
    }
    if (current >= limits[kind]) {
      error = isRef2VA()
        ? `${{ image: "图片", video: "视频", audio: "音频" }[kind]}最多添加 ${limits[kind]} 份`
        : "最多添加首帧和尾帧两张图片";
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
  refreshIcons();
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
    el("healthDot").className = "status-dot online";
    el("healthText").textContent = `${data.gpu} · 队列 ${data.queue_depth}`;
  } catch {
    el("healthDot").className = "status-dot offline";
    el("healthText").textContent = "服务离线";
  }
}

async function loadAssets() {
  const params = new URLSearchParams({ page: state.assetPage, page_size: state.assetPageSize, scope: jobScope() });
  const filter = el("assetStatusFilter").value;
  const query = el("assetSearch").value.trim();
  if (filter) params.set("status", filter);
  if (query) params.set("query", query);
  try {
    const payload = await api(`/api/v1/generations?${params}`);
    state.assets = payload.data;
    state.assetPages = payload.pages;
    if (state.assetPage > state.assetPages) {
      state.assetPage = state.assetPages;
      return loadAssets();
    }
    renderAssets(payload.total);
  } catch (error) {
    el("assetGrid").innerHTML = `<p class="list-error">${escapeHtml(error.message)}</p>`;
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

function renderAssets(total = state.assets.length) {
  el("assetTotal").textContent = total;
  el("assetGrid").innerHTML = state.assets.length ? state.assets.map((job) => {
    const preview = job.status === "completed" && job.result_url
      ? `<video src="${job.result_url}" muted playsinline preload="metadata" aria-label="${modelLabel(job)} 生成视频"></video><span class="asset-play">${icon("play")}</span>`
      : `<span class="asset-placeholder ${job.status}">${icon(job.status === "running" ? "loader-circle" : job.status === "queued" ? "clock-3" : job.status === "failed" ? "triangle-alert" : "circle-slash-2")}${job.status === "running" ? `<b>${job.progress || 0}%</b>` : ""}</span>`;
    return `<article class="asset-card" data-scroll-job="${job.id}" tabindex="0" aria-label="${executionModeLabel(job)}，${modelLabel(job)}，${STATUS_LABELS[job.status] || job.status}">
      <div class="asset-preview">${preview}${assetAction(job)}</div>
      <div class="asset-meta"><span class="task-status ${job.status}"></span><strong>${modelLabel(job)}</strong><small class="asset-plan ${executionModeClass(job)}">${executionModeLabel(job)}</small><time>总体耗时 ${formatElapsed(job.elapsed_seconds)}</time></div>
    </article>`;
  }).join("") : `<div class="library-empty">${icon("images")}<span>暂无素材</span></div>`;
  el("assetPageLabel").textContent = `${state.assetPage} / ${state.assetPages}`;
  el("previousAssetPage").disabled = state.assetPage <= 1;
  el("nextAssetPage").disabled = state.assetPage >= state.assetPages;
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
  const labels = referenceLabels(references, job.request?.model_variant || "fl2va-fp8");
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
  const buttons = [];
  if (job.status === "queued") {
    buttons.push(`<button type="button" data-job-action="edit" data-job-id="${job.id}">${icon("pencil")}<span>修改</span></button>`);
  }
  if (isActive(job)) {
    buttons.push(`<button type="button" class="cancel" data-job-action="cancel" data-job-id="${job.id}">${icon("square")}<span>取消</span></button>`);
  } else {
    buttons.push(`<button type="button" class="danger" data-job-action="delete" data-job-id="${job.id}">${icon("trash-2")}<span>删除</span></button>`);
  }
  return `<div class="message-actions">${buttons.join("")}</div>`;
}

function renderJobExchange(job) {
  const request = job.request || {};
  const active = isActive(job);
  const detail = job.error || (job.queue_position ? `队列位置 ${job.queue_position}` : job.stage);
  const incognito = request.incognito
    ? `<span class="message-mode">${icon("scan-eye")} 无痕${job.expires_at ? ` · ${formatTime(job.expires_at, true)} 销毁` : ""}</span>`
    : "";
  const executionMode = `<span class="message-plan ${executionModeClass(job)}">${executionModeLabel(job)}</span>`;
  const elapsed = `<span>总体耗时 ${formatElapsed(job.elapsed_seconds)}</span>`;
  let assistantBody = "";
  if (active) {
    assistantBody = `<div class="generation-progress">
      <div><span class="progress-stage"><i></i>${escapeHtml(job.stage || STATUS_LABELS[job.status])}</span><b>${job.progress || 0}%</b></div>
      <div class="progress-track"><span style="width:${Math.max(0, Math.min(100, job.progress || 0))}%"></span></div>
      <small>${escapeHtml(detail || STATUS_LABELS[job.status])}</small>
    </div>`;
  } else if (job.status === "completed") {
    assistantBody = `<p class="terminal-state completed">视频已生成</p>
      <div class="video-result"><video controls playsinline preload="metadata" src="${job.result_url}"></video><a href="${job.result_url}" download>${icon("download")}<span>下载 MP4</span></a></div>`;
  } else {
    assistantBody = `<p class="terminal-state ${job.status}">${escapeHtml(detail || STATUS_LABELS[job.status])}</p>`;
  }
  return `<section class="exchange" id="job-${job.id}" data-job-id="${job.id}">
    <article class="message user-message">
      <div class="message-avatar user-avatar">你</div>
      <div class="message-body">${referenceSummary(job)}<div class="message-text">${escapeHtml(request.prompt || "")}</div><div class="message-meta">${executionMode}<span>${modelLabel(job)}</span><span>${request.width} × ${request.height}</span><span>${request.duration}s</span><span>${request.steps} 步</span><span>seed ${request.seed}</span>${elapsed}${incognito}</div></div>
    </article>
    <article class="message assistant-message">
      <div class="message-avatar assistant-avatar">H3</div>
      <div class="message-body"><div class="assistant-heading"><strong>${STATUS_LABELS[job.status] || job.status}</strong><span>${formatTime(job.updated_at || job.created_at, true)}</span></div>${assistantBody}${messageActions(job)}</div>
    </article>
  </section>`;
}

function renderConversationFeed(mode = "preserve") {
  const feed = el("conversationFeed");
  const oldHeight = feed.scrollHeight;
  const oldTop = feed.scrollTop;
  const nearBottom = oldHeight - oldTop - feed.clientHeight < 160;
  const timeline = [...state.conversations]
    .reverse()
    .map((job) => ({ type: "job", at: job.created_at, data: job }))
    .sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
  const older = state.conversationPage < state.conversationPages
    ? `<button class="load-older" type="button" data-load-older>${icon("arrow-up")}<span>加载更早消息</span></button>`
    : "";
  const content = timeline.map((item) => renderJobExchange(item.data)).join("");
  feed.innerHTML = `${older}${content || `<div class="chat-empty"><span>H3</span><h2>开始创作</h2></div>`}`;
  refreshIcons();
  requestAnimationFrame(() => {
    if (mode === "bottom" || (mode === "preserve" && nearBottom)) {
      feed.scrollTop = feed.scrollHeight;
    } else if (mode === "prepend") {
      feed.scrollTop = oldTop + (feed.scrollHeight - oldHeight);
    } else {
      feed.scrollTop = oldTop;
    }
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

function resetComposer() {
  state.references.forEach((item) => { if (item.file && item.url) URL.revokeObjectURL(item.url); });
  state.references = [];
  state.editingJobId = null;
  promptInput.value = "";
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
    if (job.status !== "queued") throw new Error("只有排队中的任务可以修改");
    resetComposer();
    state.editingJobId = job.id;
    promptInput.value = job.request.prompt;
    el("modelVariant").value = job.request.model_variant || "fl2va-fp8";
    el("executionMode").value = job.request.execution_mode || "native";
    el("duration").value = String(job.request.duration);
    el("steps").value = String(job.request.steps);
    el("seed").value = String(job.request.seed);
    setDimensions(job.request.width, job.request.height);
    state.references = (job.request.references || []).map((item) => ({ ...item, kind: item.type, remote: true }));
    updateModelUi();
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
    await api(`/api/v1/generations/${jobId}/cancel`, { method: "POST" });
    await Promise.all([loadAssets(), refreshConversation()]);
  } catch (error) {
    showError(error.message);
  }
}

async function deleteJob(jobId) {
  if (!window.confirm("删除后将同时清理任务记录、上传素材和生成产物，确认继续？")) return;
  try {
    await api(`/api/v1/generations/${jobId}`, { method: "DELETE" });
    if (state.editingJobId === jobId) resetComposer();
    await Promise.all([loadAssets(), refreshConversation()]);
  } catch (error) {
    showError(error.message);
  }
}

async function handleJobAction(action, jobId) {
  if (action === "edit") return startEdit(jobId);
  if (action === "cancel") return cancelJob(jobId);
  if (action === "delete") return deleteJob(jobId);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  const prompt = promptInput.value.trim();
  if (prompt.length < 8) return showError("请填写至少 8 个字符的提示词");
  const steps = Number(el("steps").value);
  if (!Number.isInteger(steps) || steps < 4 || steps > 50) return showError("采样步数请输入 4–50 的整数");
  const [width, height] = getDimensions();
  const button = el("generateButton");
  button.disabled = true;
  try {
    let payload;
    if (state.editingJobId) {
      payload = await api(`/api/v1/generations/${state.editingJobId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(state.incognito ? { "X-H3-Incognito-Code": state.incognitoCode } : {}),
        },
        body: JSON.stringify({
          prompt,
          width,
          height,
          duration: Number(el("duration").value),
          steps,
          seed: el("seed").value === "" ? undefined : Number(el("seed").value),
          model_variant: selectedVariant(),
          execution_mode: selectedExecutionMode(),
        }),
      });
    } else {
      const referenceError = validateReferenceSet();
      if (referenceError) throw new Error(referenceError);
      const data = new FormData();
      data.append("prompt", prompt);
      data.append("width", String(width));
      data.append("height", String(height));
      data.append("duration", el("duration").value);
      data.append("steps", String(steps));
      data.append("seed", el("seed").value);
      data.append("model_variant", selectedVariant());
      data.append("execution_mode", selectedExecutionMode());
      data.append("incognito", state.incognito ? "true" : "false");
      data.append("reference_manifest", JSON.stringify(state.references.map((item) => ({ type: item.kind }))));
      state.references.forEach((item) => data.append("references", item.file, item.file.name));
      const headers = state.incognito ? { "X-H3-Incognito-Code": state.incognitoCode } : {};
      payload = await api("/api/v1/generations", { method: "POST", headers, body: data });
    }
    if (state.editingJobId) resetComposer();
    state.conversations = dedupeJobs([payload, ...state.conversations]);
    renderConversationFeed("bottom");
    await loadAssets();
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
});

function renderQueue(queue) {
  state.queue = queue;
  const running = queue.find((job) => job.status === "running");
  const anonymousRunning = running && isAnonymousQueueJob(running);
  const queuedCount = queue.filter((job) => job.status === "queued").length;
  el("queueCount").textContent = queue.length;
  el("launcherQueueCount").textContent = queuedCount;
  el("launcherQueueCount").hidden = queuedCount === 0;
  el("launcherTitle").textContent = running ? "正在生成" : "运行日志";
  el("launcherMeta").textContent = running
    ? anonymousRunning
      ? "有任务正在运行中"
      : `${executionModeLabel(running)} · ${running.progress || 0}% · ${formatElapsed(running.elapsed_seconds)}`
    : queuedCount ? `排队 ${queuedCount}` : "队列为空";
  el("activeTaskSummary").textContent = running
    ? anonymousRunning
      ? "有任务正在运行中"
      : `${shortTitle(running)} · ${executionModeLabel(running)} · ${running.progress || 0}% · 总体耗时 ${formatElapsed(running.elapsed_seconds)}`
    : `当前没有执行任务 · 排队 ${queuedCount}`;
  el("queueList").innerHTML = queue.length ? queue.map((job) => {
    if (isAnonymousQueueJob(job)) {
      return `<div class="queue-row">
        <span class="queue-position">${job.status === "running" ? icon("loader-circle") : job.queue_position}</span>
        <span><strong>${escapeHtml(job.stage || "有任务正在运行中")}</strong></span>
      </div>`;
    }
    return `<div class="queue-row" data-scroll-job="${job.id}">
      <span class="queue-position">${job.status === "running" ? icon("loader-circle") : job.queue_position}</span>
      <span><strong>${escapeHtml(shortTitle(job))}</strong><small>${escapeHtml(executionModeLabel(job))} · ${escapeHtml(job.stage || STATUS_LABELS[job.status])} · ${job.progress || 0}% · ${formatElapsed(job.elapsed_seconds)}</small></span>
      <button type="button" data-job-action="cancel" data-job-id="${job.id}" title="取消任务" aria-label="取消任务">${icon("square")}</button>
    </div>`;
  }).join("") : '<p class="quiet">队列为空</p>';
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
  }).join("") : '<p class="quiet">等待事件</p>';
  container.scrollTop = container.scrollHeight;
}

function connectEventStream() {
  state.stream?.close();
  state.stream = new EventSource("/api/v1/events");
  state.stream.addEventListener("snapshot", async (event) => {
    const payload = JSON.parse(event.data);
    renderQueue(payload.queue || []);
    renderLogs(payload.logs || []);
    if (payload.revision !== state.lastRevision) {
      state.lastRevision = payload.revision;
      await Promise.all([loadAssets(), refreshConversation(), checkHealth()]);
    }
  });
  state.stream.onerror = () => {
    el("healthDot").className = "status-dot reconnecting";
  };
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

async function optimizePrompt() {
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
  state.assetPage = 1;
  state.assetPages = 1;
  state.conversations = [];
  state.conversationPage = 1;
  state.conversationPages = 1;
  renderAssets(0);
  renderConversationFeed("bottom");
  await Promise.all([loadAssets(), refreshConversation(true)]);
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
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") form.requestSubmit();
});

el("assetGrid").addEventListener("click", (event) => {
  const action = event.target.closest("[data-job-action]");
  if (action) {
    event.stopPropagation();
    handleJobAction(action.dataset.jobAction, action.dataset.jobId);
    return;
  }
  const card = event.target.closest("[data-scroll-job]");
  if (card) scrollToJob(card.dataset.scrollJob);
});
el("assetGrid").addEventListener("keydown", (event) => {
  if (["Enter", " "].includes(event.key) && event.target.matches("[data-scroll-job]")) {
    event.preventDefault();
    scrollToJob(event.target.dataset.scrollJob);
  }
});

el("conversationFeed").addEventListener("click", (event) => {
  const action = event.target.closest("[data-job-action]");
  if (action) return handleJobAction(action.dataset.jobAction, action.dataset.jobId);
  if (event.target.closest("[data-load-older]")) loadOlderMessages();
});
el("conversationFeed").addEventListener("scroll", () => {
  if (el("conversationFeed").scrollTop < 72) loadOlderMessages();
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
el("previousAssetPage").addEventListener("click", () => { if (state.assetPage > 1) { state.assetPage -= 1; loadAssets(); } });
el("nextAssetPage").addEventListener("click", () => { if (state.assetPage < state.assetPages) { state.assetPage += 1; loadAssets(); } });
el("assetStatusFilter").addEventListener("change", () => { state.assetPage = 1; loadAssets(); });
let assetSearchTimer = null;
el("assetSearch").addEventListener("input", () => {
  clearTimeout(assetSearchTimer);
  assetSearchTimer = setTimeout(() => { state.assetPage = 1; loadAssets(); }, 250);
});

["aiEnabled", "aiBaseUrl", "aiModel", "aiApiKey"].forEach((id) => el(id).addEventListener("change", saveAiConfig));
el("optimizePrompt").addEventListener("click", optimizePrompt);
el("modelVariant").addEventListener("change", updateModelUi);
el("executionMode").addEventListener("change", updateModelUi);

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
  if (event.key === "Escape" && !el("secretOverlay").hidden) closeSecretDialog();
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
  loadAiConfig();
  updateModelUi();
  updateIncognitoUi();
  renderReferences();
  await Promise.all([checkHealth(), loadAssets(), refreshConversation(true)]);
  connectEventStream();
  refreshIcons();
}

initialize();
setInterval(checkHealth, 15000);
window.addEventListener("load", refreshIcons);
window.addEventListener("beforeunload", () => state.stream?.close());
