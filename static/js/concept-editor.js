(() => {
  const normalise = (value) => value.trim().replace(/[\u064A\u06CC]/g, "ی").replace(/[\u0643\u06A9]/g, "ک").replace(/\s+/g, " ").toLowerCase();
  const aceScript = document.querySelector("script[data-ace-base]");
  const editors = new WeakMap();

  function initTags(editor) {
    const hidden = editor.querySelector("input[name='tag_names']");
    const chips = editor.querySelector("[data-tag-chips]");
    const input = editor.querySelector("[data-tag-input]");
    if (!hidden || !chips || !input) return;
    let values;
    try { values = JSON.parse(hidden.value || "[]"); } catch (_) { values = []; }
    if (!Array.isArray(values)) values = [];
    const sync = () => { hidden.value = JSON.stringify(values); hidden.dispatchEvent(new Event("input", { bubbles: true })); };
    const render = () => {
      chips.replaceChildren();
      values.forEach((value, index) => {
        const chip = document.createElement("span"); chip.className = "tag-chip"; chip.dir = "auto";
        const name = document.createElement("span"); name.textContent = value;
        const remove = document.createElement("button"); remove.type = "button"; remove.setAttribute("aria-label", `Remove ${value}`); remove.textContent = "×";
        remove.addEventListener("click", () => { values.splice(index, 1); sync(); render(); input.focus(); });
        chip.append(name, remove); chips.append(chip);
      });
    };
    const add = () => { const value = input.value.trim().replace(/,$/, ""); if (!value) return; if (!values.some((item) => normalise(item) === normalise(value))) values.push(value); input.value = ""; sync(); render(); };
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === ",") { event.preventDefault(); add(); }
      if (event.key === "Backspace" && !input.value && values.length) { values.pop(); sync(); render(); }
    });
    input.addEventListener("blur", add); render();
  }

  function aceMode(language) {
    return { cpp: "c_cpp", csharp: "csharp", go: "golang", bash: "sh", shell: "sh", plaintext: "text" }[language] || language || "text";
  }
  function aceTheme() { return document.documentElement.dataset.theme === "dark" ? "ace/theme/monokai" : "ace/theme/chrome"; }
  function initAce(row) {
    if (!window.ace) return;
    row.querySelectorAll("textarea.code-source").forEach((textarea) => {
      if (editors.has(textarea)) return;
      const host = textarea.parentElement.querySelector("[data-ace-editor]"); if (!host) return;
      const scriptBase = aceScript?.dataset.aceBase;
      if (scriptBase) window.ace.config.set("basePath", scriptBase);
      const aceEditor = window.ace.edit(host);
      aceEditor.setTheme(aceTheme()); aceEditor.session.setUseWorker(false); aceEditor.session.setUseWrapMode(true);
      aceEditor.setValue(textarea.value || "", -1); aceEditor.session.setMode(`ace/mode/${aceMode(row.querySelector("select[name$='-language']")?.value)}`);
      aceEditor.on("change", () => { textarea.value = aceEditor.getValue(); textarea.dispatchEvent(new Event("input", { bubbles: true })); });
      row.querySelector("select[name$='-language']")?.addEventListener("change", (event) => aceEditor.session.setMode(`ace/mode/${aceMode(event.target.value)}`));
      editors.set(textarea, aceEditor);
    });
  }
  function refreshSort(container) { container.querySelectorAll("[data-formset-row]").forEach((row, index) => { const input = row.querySelector("input[name$='-sort_order']"); if (input) input.value = index; }); }
  function initFormset(formset) {
    const prefix = formset.dataset.prefix; const items = formset.querySelector("[data-formset-items]"); const total = formset.querySelector(`input[name='${prefix}-TOTAL_FORMS']`); const template = formset.querySelector("template[data-empty-form]");
    if (!items || !total || !template) return;
    const bind = (row) => {
      initAce(row);
      row.querySelector("[data-remove-row]")?.addEventListener("click", () => {
        const del = row.querySelector("input[name$='-DELETE']"); if (del && row.querySelector("input[name$='-id']")?.value) { del.value = "on"; row.hidden = true; } else { editors.get(row.querySelector("textarea.code-source"))?.destroy(); row.remove(); }
        refreshSort(items);
      });
      row.querySelector("[data-move-up]")?.addEventListener("click", () => { const previous = row.previousElementSibling; if (previous) { items.insertBefore(row, previous); refreshSort(items); } });
      row.querySelector("[data-move-down]")?.addEventListener("click", () => { const next = row.nextElementSibling; if (next) { items.insertBefore(next, row); refreshSort(items); } });
    };
    items.querySelectorAll("[data-formset-row]").forEach(bind); refreshSort(items);
    formset.querySelector("[data-add-row]")?.addEventListener("click", () => { const index = Number(total.value); const wrapper = document.createElement("div"); wrapper.innerHTML = template.innerHTML.replaceAll("__prefix__", String(index)); const row = wrapper.firstElementChild; items.querySelector("[data-empty-state]")?.remove(); items.append(row); total.value = index + 1; bind(row); refreshSort(items); row.querySelector("input,select,textarea")?.focus(); });
    if (formset.dataset.sortable === "true" && window.Sortable) new window.Sortable(items, { animation: 120, handle: ".drag-handle", onEnd: () => refreshSort(items) });
  }
  function initAttachments(editor) {
    const input = editor.querySelector("[data-attachment-input]"); const dropzone = editor.querySelector("[data-attachment-dropzone]"); const preview = editor.querySelector("[data-attachment-preview]"); const removed = editor.querySelector("[data-removed-attachments]"); if (!input || !dropzone || !preview) return;
    let files = [];
    const render = () => { preview.replaceChildren(); files.forEach((file, index) => { const card = document.createElement("article"); card.className = "attachment-card"; const visual = file.type.startsWith("image/") ? document.createElement("img") : document.createElement("span"); if (visual.tagName === "IMG") { visual.src = URL.createObjectURL(file); visual.onload = () => URL.revokeObjectURL(visual.src); visual.alt = ""; } else { visual.className = "attachment-file-icon"; visual.textContent = file.type === "application/pdf" ? "PDF" : "FILE"; } const text = document.createElement("div"); const title = document.createElement("strong"); title.textContent = file.name; const size = document.createElement("small"); size.textContent = `${Math.ceil(file.size / 1024)} KB`; text.append(title, size); const button = document.createElement("button"); button.type = "button"; button.className = "editor-icon-button"; button.textContent = "×"; button.setAttribute("aria-label", `Remove ${file.name}`); button.addEventListener("click", () => { files.splice(index, 1); setFiles(); render(); }); card.append(visual, text, button); preview.append(card); }); };
    const setFiles = () => { if (!window.DataTransfer) return; const data = new DataTransfer(); files.forEach((file) => data.items.add(file)); input.files = data.files; };
    const addFiles = (newFiles) => { files = files.concat([...newFiles]); setFiles(); render(); input.dispatchEvent(new Event("input", { bubbles: true })); };
    input.addEventListener("change", () => { files = [...input.files]; render(); });
    ["dragenter", "dragover"].forEach((type) => dropzone.addEventListener(type, (event) => { event.preventDefault(); dropzone.classList.add("is-dragging"); }));
    ["dragleave", "drop"].forEach((type) => dropzone.addEventListener(type, (event) => { event.preventDefault(); dropzone.classList.remove("is-dragging"); }));
    dropzone.addEventListener("drop", (event) => addFiles(event.dataTransfer.files));
    editor.querySelectorAll("[data-remove-attachment]").forEach((button) => button.addEventListener("click", () => { const card = button.closest("[data-existing-attachment]"); const hidden = document.createElement("input"); hidden.type = "hidden"; hidden.name = "remove_attachment_ids"; hidden.value = card.dataset.attachmentId; removed.append(hidden); card.remove(); }));
  }
  function initFieldHelp(editor) {
    const close = (except) => editor.querySelectorAll("[data-field-help-toggle]").forEach((trigger) => {
      if (trigger === except) return; trigger.setAttribute("aria-expanded", "false"); trigger.nextElementSibling.hidden = true;
    });
    editor.querySelectorAll("[data-field-help-toggle]").forEach((trigger) => {
      const panel = trigger.nextElementSibling;
      const toggle = () => { const open = trigger.getAttribute("aria-expanded") !== "true"; close(trigger); trigger.setAttribute("aria-expanded", String(open)); panel.hidden = !open; };
      trigger.addEventListener("click", toggle); trigger.addEventListener("focus", () => { close(trigger); trigger.setAttribute("aria-expanded", "true"); panel.hidden = false; });
    });
    document.addEventListener("click", (event) => { if (!event.target.closest(".field-help")) close(); });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") close(); });
    const guide = document.querySelector("[data-field-guide]");
    editor.querySelector("[data-open-field-guide]")?.addEventListener("click", () => guide?.showModal());
    guide?.querySelector("[data-close-field-guide]")?.addEventListener("click", () => guide.close());
  }
  function init(editor) {
    initTags(editor); initAttachments(editor); initFieldHelp(editor); editor.querySelectorAll("[data-formset]").forEach(initFormset);
    editor.querySelectorAll("[data-editor-section]").forEach((section) => section.querySelector(".editor-section__toggle")?.addEventListener("click", () => { const open = section.classList.toggle("is-open"); section.querySelector(".editor-section__toggle").setAttribute("aria-expanded", String(open)); }));
    let dirty = false; editor.addEventListener("input", () => { dirty = true; }); editor.addEventListener("change", () => { dirty = true; });
    editor.addEventListener("submit", () => { editor.querySelectorAll("textarea.code-source").forEach((textarea) => { const aceEditor = editors.get(textarea); if (aceEditor) textarea.value = aceEditor.getValue(); }); editor.querySelectorAll("textarea.markdown-source").forEach((textarea) => { if (textarea._toastEditor) textarea.value = textarea._toastEditor.getMarkdown(); }); dirty = false; const button = editor.querySelector("[data-save-button]"); if (button) { button.disabled = true; button.textContent = "Saving…"; } });
    window.addEventListener("beforeunload", (event) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
  }
  document.addEventListener("DOMContentLoaded", () => { document.querySelectorAll("[data-concept-editor]").forEach(init); new MutationObserver(() => document.querySelectorAll("textarea.code-source").forEach((textarea) => editors.get(textarea)?.setTheme(aceTheme()))).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] }); });
})();
