/* Apple-like motion for dialogs. The real dialog is hidden immediately and a
 * short-lived visual clone fades out, so close handlers may reset their forms
 * without flashing empty content. */
(function () {
  if (window.__h3Motion) return;
  window.__h3Motion = true;
  const descriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "hidden");
  if (!descriptor || !descriptor.configurable) return;
  const clones = new WeakMap();
  const overlaySelector = ".modal-overlay, .secret-overlay, .asset-detail-layer";
  const isOverlay = (node) =>
    node instanceof HTMLElement &&
    typeof node.matches === "function" &&
    node.matches(overlaySelector);
  const setHidden = (node, value) => descriptor.set.call(node, value);
  const readHidden = (node) => descriptor.get.call(node);

  const removeClone = (node) => {
    const clone = clones.get(node);
    if (!clone) return;
    clone.remove();
    clones.delete(node);
  };

  const cloneForExit = (node) => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    removeClone(node);
    const clone = node.cloneNode(true);
    clone.removeAttribute("id");
    clone.querySelectorAll("[id]").forEach((item) => item.removeAttribute("id"));
    clone.removeAttribute("hidden");
    clone.removeAttribute("aria-modal");
    clone.setAttribute("aria-hidden", "true");
    clone.classList.remove("is-open", "is-closing");
    const sourceFields = node.querySelectorAll("input, textarea, select");
    const cloneFields = clone.querySelectorAll("input, textarea, select");
    sourceFields.forEach((field, index) => {
      const copy = cloneFields[index];
      if (!copy) return;
      if (field.type === "checkbox" || field.type === "radio") copy.checked = field.checked;
      else if (field.tagName === "SELECT") copy.selectedIndex = field.selectedIndex;
      else copy.value = field.value;
    });
    clone.style.pointerEvents = "none";
    document.body.append(clone);
    void clone.offsetWidth;
    clone.classList.add("is-closing");
    clones.set(node, clone);
    window.setTimeout(() => {
      if (clones.get(node) === clone) clones.delete(node);
      clone.remove();
    }, 230);
  };

  Object.defineProperty(HTMLElement.prototype, "hidden", {
    configurable: true,
    enumerable: descriptor.enumerable,
    get() { return readHidden(this); },
    set(value) {
      if (!isOverlay(this)) {
        setHidden(this, value);
        return;
      }
      const next = Boolean(value);
      if (next) {
        if (readHidden(this)) return;
        cloneForExit(this);
        setHidden(this, true);
        return;
      }
      removeClone(this);
      document
        .querySelectorAll(".modal-overlay.is-closing, .secret-overlay.is-closing, .asset-detail-layer.is-closing")
        .forEach((clone) => clone.remove());
      setHidden(this, false);
      this.classList.remove("is-open");
      // Force a new animation frame so reopening always replays the entrance.
      void this.offsetWidth;
      this.classList.add("is-open");
    },
  });
})();
