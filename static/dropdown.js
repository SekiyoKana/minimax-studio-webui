/*
 * Custom dropdown for MiniMax H3 Studio.
 * Replaces native select popups in the primary UI with a themed listbox.
 * The native select stays in the DOM as the value holder.
 */
(function () {
  if (window.__h3Dropdown) return;
  window.__h3Dropdown = true;

  const SAFE_SELECTOR = [
    ".library-tools select",
    ".compact-control select",
    ".settings-body select",
    ".auto-upscale-confirm-dialog select",
    ".video-upscale-dialog select",
  ].join(",");

  const instances = new WeakMap();
  const valueDescriptor = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value");
  const indexDescriptor = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "selectedIndex");
  let open = null;

  function notifySync(select) {
    select.dispatchEvent(new Event("cs:sync"));
  }

  try {
    Object.defineProperty(HTMLSelectElement.prototype, "value", {
      configurable: true,
      get() { return valueDescriptor.get.call(this); },
      set(value) {
        valueDescriptor.set.call(this, value);
        notifySync(this);
      },
    });
    Object.defineProperty(HTMLSelectElement.prototype, "selectedIndex", {
      configurable: true,
      get() { return indexDescriptor.get.call(this); },
      set(value) {
        indexDescriptor.set.call(this, value);
        notifySync(this);
      },
    });
  } catch (error) { /* older engines keep native behaviour */ }

  function optionLabel(option) {
    return (option?.textContent || "").replace(/\s+/g, " ").trim();
  }

  function sync(select) {
    const instance = instances.get(select);
    if (!instance) return;
    const option = select.selectedOptions[0];
    instance.value.textContent = optionLabel(option);
    instance.trigger.disabled = select.disabled;
    instance.wrapper.classList.toggle("is-disabled", select.disabled);
    instance.trigger.title = optionLabel(option);
  }

  function closeMenu({ restoreFocus = false } = {}) {
    if (!open) return;
    const { menu, trigger, wrapper, select } = open;
    open.trigger.setAttribute("aria-expanded", "false");
    open = null;
    wrapper.classList.remove("is-open");
    menu.remove();
    document.removeEventListener("pointerdown", onOutside, true);
    window.removeEventListener("resize", onViewportChange, true);
    window.removeEventListener("scroll", onScroll, true);
    if (restoreFocus) trigger.focus();
    if (select) sync(select);
  }

  function onOutside(event) {
    if (!open) return;
    if (open.menu.contains(event.target) || open.trigger.contains(event.target) || open.wrapper.contains(event.target)) return;
    closeMenu();
  }

  function onViewportChange() { closeMenu(); }
  function onScroll(event) {
    if (open && (open.menu.contains(event.target) || open.trigger.contains(event.target))) return;
    closeMenu();
  }

  const CHECK_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5L20 7"/></svg>';
  const CHEVRON_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';

  function openMenu(instance) {
    if (!instance || instance.select.disabled) return;
    if (open && open.wrapper === instance.wrapper) {
      closeMenu();
      return;
    }
    closeMenu();
    const { select, trigger, wrapper } = instance;
    const menu = document.createElement("div");
    menu.className = "cs-menu";
    menu.id = `cs-menu-${Math.random().toString(36).slice(2, 9)}`;
    menu.setAttribute("role", "listbox");
    menu.tabIndex = -1;

    const options = Array.from(select.options).filter((option) => !option.hidden);
    const items = [];
    options.forEach((option, index) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "cs-option";
      item.setAttribute("role", "option");
      item.id = `${menu.id}-opt-${index}`;
      item.dataset.index = String(index);
      item.disabled = option.disabled;
      const selected = option.index === select.selectedIndex;
      item.setAttribute("aria-selected", String(selected));
      item.innerHTML = `<span class="cs-option-label"></span><span class="cs-check">${CHECK_ICON}</span>`;
      item.querySelector(".cs-option-label").textContent = optionLabel(option);
      if (selected) item.classList.add("is-selected");
      item.addEventListener("click", () => choose(index));
      items.push(item);
      menu.appendChild(item);
    });

    let active = items.findIndex((item) => item.classList.contains("is-selected"));
    if (active < 0) active = items.findIndex((item) => !item.disabled);
    function setActive(next) {
      if (!items.length) return;
      active = Math.max(0, Math.min(items.length - 1, next));
      while (items[active].disabled && active < items.length - 1) active += 1;
      items.forEach((item, index) => item.classList.toggle("is-active", index === active));
      menu.setAttribute("aria-activedescendant", items[active]?.id || "");
      items[active]?.scrollIntoView({ block: "nearest" });
    }
    function choose(index) {
      const option = options[index];
      if (!option || option.disabled) return;
      select.selectedIndex = option.index;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      notifySync(select);
      closeMenu({ restoreFocus: true });
    }

    menu.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") { event.preventDefault(); setActive(active + 1); }
      else if (event.key === "ArrowUp") { event.preventDefault(); setActive(active - 1); }
      else if (event.key === "Home") { event.preventDefault(); setActive(0); }
      else if (event.key === "End") { event.preventDefault(); setActive(items.length - 1); }
      else if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(active); }
      else if (event.key === "Escape" || event.key === "Tab") { event.preventDefault(); closeMenu({ restoreFocus: true }); }
    });
    menu.addEventListener("click", (event) => {
      if (event.target === menu) closeMenu();
    });

    document.body.appendChild(menu);
    const rect = trigger.getBoundingClientRect();
    const width = Math.min(Math.max(rect.width, 176), Math.min(360, window.innerWidth - 16));
    menu.style.width = `${width}px`;
    menu.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - width - 8))}px`;
    const menuHeight = Math.min(menu.scrollHeight + 12, 300);
    const below = window.innerHeight - rect.bottom;
    const placeAbove = below < menuHeight + 12 && rect.top > below;
    menu.style.top = placeAbove ? `${Math.max(8, rect.top - menuHeight - 6)}px` : `${Math.min(window.innerHeight - menuHeight - 8, rect.bottom + 6)}px`;
    menu.style.maxHeight = `${Math.min(300, window.innerHeight - 24)}px`;

    open = { menu, trigger, wrapper, select };
    wrapper.classList.add("is-open");
    trigger.setAttribute("aria-expanded", "true");
    trigger.setAttribute("aria-controls", menu.id);
    setActive(active);
    menu.focus({ preventScroll: true });
    document.addEventListener("pointerdown", onOutside, true);
    window.addEventListener("resize", onViewportChange, true);
    window.addEventListener("scroll", onScroll, true);
  }

  function onTriggerKeydown(event) {
    const select = event.currentTarget.__csSelect;
    if (!select || select.disabled) return;
    if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
      event.preventDefault();
      openMenu(instances.get(select));
    }
  }

  function enhance(select) {
    if (!(select instanceof HTMLSelectElement)) return;
    if (select.multiple || select.size > 1 || select.dataset.csEnhanced === "true") return;
    if (!select.parentNode || !select.matches(SAFE_SELECTOR)) return;
    select.dataset.csEnhanced = "true";
    select.classList.add("cs-native");
    select.setAttribute("tabindex", "-1");

    const wrapper = document.createElement("span");
    wrapper.className = "cs";
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "cs-trigger";
    trigger.setAttribute("role", "combobox");
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    const value = document.createElement("span");
    value.className = "cs-value";
    const chevron = document.createElement("span");
    chevron.className = "cs-chevron";
    chevron.innerHTML = CHEVRON_ICON;
    trigger.append(value, chevron);
    trigger.__csSelect = select;

    const compact = Boolean(select.closest(".compact-control"));
    const computed = getComputedStyle(select);
    trigger.style.fontSize = computed.fontSize;
    trigger.style.fontFamily = computed.fontFamily;
    trigger.style.fontWeight = computed.fontWeight;
    trigger.style.paddingLeft = computed.paddingLeft;
    trigger.style.paddingRight = compact
      ? computed.paddingRight
      : `${Math.max(parseFloat(computed.paddingRight) || 0, 18)}px`;

    select.parentNode.insertBefore(wrapper, select);
    wrapper.append(select, trigger);
    instances.set(select, { wrapper, trigger, value, select });
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openMenu(instances.get(select));
    });
    trigger.addEventListener("keydown", onTriggerKeydown);
    select.addEventListener("change", () => sync(select));
    select.addEventListener("cs:sync", () => sync(select));
    sync(select);
  }

  function enhanceAll(root = document) {
    if (root instanceof HTMLSelectElement) enhance(root);
    root.querySelectorAll(SAFE_SELECTOR).forEach(enhance);
  }

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === "childList") {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1) enhanceAll(node);
        });
        if (mutation.target instanceof HTMLSelectElement) sync(mutation.target);
      }
    });
  });

  function start() {
    enhanceAll(document);
    observer.observe(document.body, { childList: true, subtree: true });
    document.addEventListener("change", (event) => {
      if (event.target instanceof HTMLSelectElement) sync(event.target);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
