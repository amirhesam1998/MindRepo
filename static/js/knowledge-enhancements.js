(() => {
  const csrf = () => document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/)?.[1];
  const toolbar = [
    ["Heading", "heading", "Heading / عنوان"], ["Bold", "bold", "Bold / ضخیم"], ["Italic", "italic", "Italic / مورب"], ["Bullets", "bullets", "Bulleted list / لیست نقطه‌ای"],
    ["Numbered", "numbered", "Numbered list / لیست شماره‌ای"], ["Quote", "quote", "Quote / نقل‌قول"], ["Code", "code", "Inline code / کد درون‌خطی"], ["Block", "block", "Code block / بلوک کد"],
    ["Link", "link", "Link / لینک"], ["Table", "table", "Table / جدول"], ["Divider", "divider", "Divider / جداکننده"],
  ];
  const wrap = (textarea, before, after = before) => {
    const start = textarea.selectionStart, end = textarea.selectionEnd, selected = textarea.value.slice(start, end) || "text";
    textarea.setRangeText(`${before}${selected}${after}`, start, end, "end"); textarea.focus(); textarea.dispatchEvent(new Event("input", { bubbles: true }));
  };
  const insert = (textarea, value) => {
    const start = textarea.selectionStart; textarea.setRangeText(value, start, textarea.selectionEnd, "end"); textarea.focus(); textarea.dispatchEvent(new Event("input", { bubbles: true }));
  };
  const apply = (textarea, action) => {
    if (action === "bold") return wrap(textarea, "**"); if (action === "italic") return wrap(textarea, "_"); if (action === "code") return wrap(textarea, "`");
    if (action === "heading") return insert(textarea, "## Heading\n"); if (action === "bullets") return insert(textarea, "- Item\n"); if (action === "numbered") return insert(textarea, "1. Item\n");
    if (action === "quote") return insert(textarea, "> Quote\n"); if (action === "block") return insert(textarea, "```text\ncode\n```\n");
    if (action === "link") return insert(textarea, "[link text](https://example.com)"); if (action === "table") return insert(textarea, "| Column | Column |\n| --- | --- |\n| Value | Value |\n");
    if (action === "divider") insert(textarea, "\n---\n");
  };
  const preview = async (textarea, output, error) => {
    error.hidden = true; output.setAttribute("aria-busy", "true");
    try {
      const response = await fetch("/library/markdown-preview/", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/x-www-form-urlencoded", "X-CSRFToken": decodeURIComponent(csrf() || "") }, body: new URLSearchParams({ content: textarea.value }) });
      if (!response.ok) throw new Error("preview"); output.innerHTML = await response.text();
    } catch (_) { error.hidden = false; } finally { output.removeAttribute("aria-busy"); }
  };
  function initMarkdown(root = document) {
    root.querySelectorAll?.("textarea.markdown-source:not([data-markdown-ready])").forEach((textarea) => {
      textarea.dataset.markdownReady = "true";
      if (window.toastui?.Editor) {
        const host = document.createElement("div"); host.className = "toastui-host"; textarea.before(host); textarea.hidden = true;
        const editor = new window.toastui.Editor({ el: host, initialValue: textarea.value || "", initialEditType: "wysiwyg", previewStyle: "tab", height: textarea.rows > 6 ? "250px" : "180px", usageStatistics: false, hideModeSwitch: false, toolbarItems: [["heading", "bold", "italic", "strike"], ["hr", "quote"], ["ul", "ol"], ["table", "link"], ["code", "codeblock"], ["undo", "redo"]] });
        textarea._toastEditor = editor; editor.on("change", () => { textarea.value = editor.getMarkdown(); textarea.dispatchEvent(new Event("input", { bubbles: true })); });
        return;
      }
      const component = document.createElement("div"), controls = document.createElement("div"), edit = document.createElement("button"), previewButton = document.createElement("button"), output = document.createElement("div"), error = document.createElement("p"), helpText = document.createElement("p");
      component.className = "markdown-editor"; controls.className = "markdown-editor__toolbar"; controls.setAttribute("role", "toolbar");
      toolbar.forEach(([label, action, help]) => { const button = document.createElement("button"); button.type = "button"; button.className = "markdown-editor__action"; button.textContent = label; button.setAttribute("aria-label", help); button.title = help; button.addEventListener("click", () => apply(textarea, action)); controls.append(button); });
      const help = document.createElement("button"); help.type = "button"; help.className = "markdown-editor__action"; help.textContent = "ⓘ"; help.title = "Markdown help / راهنمای Markdown"; help.setAttribute("aria-label", "Markdown help / راهنمای Markdown"); help.addEventListener("click", () => { helpText.hidden = !helpText.hidden; }); controls.append(help);
      edit.type = "button"; edit.textContent = "Edit"; edit.setAttribute("aria-label", "Edit / ویرایش"); edit.className = "markdown-editor__mode is-active"; previewButton.type = "button"; previewButton.textContent = "Preview"; previewButton.setAttribute("aria-label", "Preview / پیش‌نمایش"); previewButton.className = "markdown-editor__mode";
      output.className = "markdown-content markdown-editor__preview"; output.hidden = true; error.className = "markdown-preview-error"; error.textContent = "Preview could not be loaded. Your text is unchanged."; error.hidden = true; helpText.className = "markdown-help-text"; helpText.textContent = "Markdown: headings, lists, links, tables, inline code, code blocks, and Preview. / Markdown: عنوان، فهرست، لینک، جدول، کد و پیش‌نمایش."; helpText.hidden = true;
      edit.addEventListener("click", () => { textarea.hidden = false; output.hidden = true; edit.classList.add("is-active"); previewButton.classList.remove("is-active"); });
      previewButton.addEventListener("click", async () => { await preview(textarea, output, error); textarea.hidden = true; output.hidden = false; previewButton.classList.add("is-active"); edit.classList.remove("is-active"); });
      textarea.before(component); component.append(controls, helpText, edit, previewButton, textarea, output, error);
    });
  }
  const mermaidTheme = () => document.documentElement.dataset.theme === "dark" ? "dark" : "default";
  async function renderDiagram(host) {
    if (!window.mermaid || host.dataset.rendering === "true") return; host.dataset.rendering = "true";
    const source = host.dataset.mermaidSource || ""; host.textContent = source; host.classList.add("mermaid");
    try { window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict", htmlLabels: false, theme: mermaidTheme() }); await window.mermaid.run({ nodes: [host] }); host.dataset.renderedTheme = mermaidTheme(); }
    catch (_) { host.classList.remove("mermaid"); host.textContent = source; host.dataset.mermaidFailed = "true"; host.closest(".diagram-shell")?.querySelector("[data-mermaid-error]")?.removeAttribute("hidden"); }
    finally { delete host.dataset.rendering; }
  }
  function initDiagramEditors(root = document) {
    root.querySelectorAll?.("select[name$='-section_type']:not([data-diagram-ready])").forEach((select) => {
      select.dataset.diagramReady = "true";
      const row = select.closest("[data-formset-row]"); const textarea = row?.querySelector("textarea.markdown-source"); if (!textarea) return;
      const controls = document.createElement("div"), button = document.createElement("button"), shell = document.createElement("div"), host = document.createElement("div"), error = document.createElement("p");
      controls.className = "diagram-editor-controls"; button.type = "button"; button.className = "btn btn-outline-secondary"; button.textContent = "Preview Diagram"; shell.className = "diagram-shell"; shell.hidden = true; host.className = "mermaid-diagram"; error.className = "mermaid-error"; error.dataset.mermaidError = ""; error.textContent = "Diagram could not be rendered."; error.hidden = true; shell.append(host, error); controls.append(button); textarea.after(controls, shell);
      const toggle = () => { const diagram = select.value === "diagram"; controls.hidden = !diagram; if (diagram) textarea.dir = "ltr"; shell.hidden = true; };
      button.addEventListener("click", async () => { host.dataset.mermaidSource = textarea.value; host.innerHTML = ""; error.hidden = true; delete host.dataset.mermaidFailed; shell.hidden = false; await renderDiagram(host); }); select.addEventListener("change", toggle); toggle();
    });
  }
  function initReviewCardArchive(root = document) {
    root.querySelectorAll?.("input[name$='-is_active']:not([data-card-archive-ready])").forEach((input) => {
      input.dataset.cardArchiveReady = "true"; input.classList.add("visually-hidden");
      const button = document.createElement("button"); button.type = "button"; button.className = "editor-text-button";
      const sync = () => { button.textContent = input.checked ? "Archive" : "Restore card"; button.closest("[data-formset-row]")?.classList.toggle("is-archived", !input.checked); };
      button.addEventListener("click", () => { input.checked = !input.checked; input.dispatchEvent(new Event("change", { bubbles: true })); sync(); }); input.after(button); sync();
    });
  }
  function initDiagrams(root = document) { root.querySelectorAll?.("[data-mermaid-source]").forEach(renderDiagram); }
  document.addEventListener("DOMContentLoaded", () => { initMarkdown(); initDiagrams(); initDiagramEditors(); initReviewCardArchive(); new MutationObserver((records) => records.forEach((record) => record.addedNodes.forEach((node) => { if (node.nodeType === 1) { initMarkdown(node); initDiagrams(node); initDiagramEditors(node); initReviewCardArchive(node); } }))).observe(document.body, { childList: true, subtree: true }); new MutationObserver(() => document.querySelectorAll("[data-mermaid-source]").forEach((host) => { if (host.dataset.renderedTheme !== mermaidTheme()) { host.innerHTML = ""; renderDiagram(host); } })).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] }); });
})();
