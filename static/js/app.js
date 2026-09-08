(() => {
  const storageKey = "mindrepo-theme";
  const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  const selectors = "[data-theme-select]";

  function applyTheme(preference) {
    const resolved = preference === "system" ? (mediaQuery.matches ? "dark" : "light") : preference;
    document.documentElement.dataset.theme = resolved;
    document.documentElement.dataset.themePreference = preference;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", resolved === "dark" ? "#111816" : "#f8fafc");
  }

  function copyText(value) {
    if (navigator.clipboard) return navigator.clipboard.writeText(value);
    const input = document.createElement("textarea");
    input.value = value;
    input.setAttribute("readonly", "");
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.append(input);
    input.select();
    const copied = document.execCommand("copy");
    input.remove();
    return copied ? Promise.resolve() : Promise.reject(new Error("Copy unavailable"));
  }

  function setConnectivity() {
    const indicator = document.querySelector("[data-connectivity]");
    if (indicator) indicator.hidden = navigator.onLine;
  }

  const preference = localStorage.getItem(storageKey) || "system";
  applyTheme(preference);
  document.querySelectorAll(selectors).forEach((select) => { select.value = preference; });
  setConnectivity();

  document.addEventListener("change", (event) => {
    if (!event.target.matches(selectors)) return;
    localStorage.setItem(storageKey, event.target.value);
    applyTheme(event.target.value);
    document.querySelectorAll(selectors).forEach((select) => { select.value = event.target.value; });
  });
  mediaQuery.addEventListener("change", () => { if ((localStorage.getItem(storageKey) || "system") === "system") applyTheme("system"); });
  window.addEventListener("online", setConnectivity);
  window.addEventListener("offline", setConnectivity);

  document.body.addEventListener("htmx:configRequest", (event) => {
    const token = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/)?.[1];
    if (token) event.detail.headers["X-CSRFToken"] = decodeURIComponent(token);
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-retry]")) location.reload();
    const button = event.target.closest("[data-add-form]");
    if (button) {
      const container = button.closest("[data-formset]");
      const total = container.querySelector('input[name$="-TOTAL_FORMS"]');
      const template = container.querySelector("template[data-empty-form]");
      container.querySelector("[data-formset-body]").insertAdjacentHTML("beforeend", template.innerHTML.replace(/__prefix__/g, total.value));
      total.value = Number(total.value) + 1;
    }
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-copy-target]");
    if (!button) return;
    const code = document.getElementById(button.dataset.copyTarget)?.innerText;
    if (!code) return;
    copyText(code).then(() => {
      const label = button.textContent;
      button.textContent = "Copied";
      setTimeout(() => { button.textContent = label; }, 1500);
    }).catch(() => { button.textContent = "Copy unavailable"; });
  });

  document.addEventListener("submit", (event) => {
    const form = event.target.closest("form[data-submit-state]");
    const button = form?.querySelector("[data-save-button]");
    if (!button) return;
    button.dataset.saving = "true";
    button.disabled = true;
    button.textContent = "Saving…";
  });

  document.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-rating-form], [data-review-reveal]");
    if (!form) return;
    if (!navigator.onLine) {
      event.preventDefault();
      document.querySelector("[data-review-error]")?.removeAttribute("hidden");
      return;
    }
    form.querySelectorAll("button").forEach((button) => { button.disabled = true; });
  });

  document.addEventListener("keydown", (event) => {
    if (event.target.matches("input, textarea, select, [contenteditable='true']")) return;
    const reveal = document.querySelector("[data-reveal-button]");
    if (reveal && (event.key === " " || event.key === "Enter")) {
      event.preventDefault();
      reveal.click();
      return;
    }
    const ratings = { "1": "again", "2": "hard", "3": "good", "4": "easy" };
    const button = ratings[event.key] && document.querySelector(`[data-rating="${ratings[event.key]}"]`);
    if (button) button.click();
  });

  window.addEventListener("load", () => {
    document.querySelector("[data-review-heading]")?.focus();
  });

  if (document.documentElement.dataset.pwaEnabled === "true" && "serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/service-worker.js").catch(() => {});
    });
  }
})();

(() => {
  const palette = document.querySelector("[data-command-palette]");
  if (!palette) return;
  const input = palette.querySelector("[data-command-palette-input]");
  let previousFocus = null;
  let activeIndex = 0;

  function results() { return [...palette.querySelectorAll("[data-palette-result]")]; }
  function setActive(index) {
    const items = results();
    if (!items.length) return;
    activeIndex = (index + items.length) % items.length;
    items.forEach((item, itemIndex) => {
      const active = itemIndex === activeIndex;
      item.classList.toggle("is-active", active);
      item.setAttribute("aria-selected", active ? "true" : "false");
    });
  }
  function openPalette() {
    if (window.matchMedia("(max-width: 767px)").matches) {
      window.location.assign("/search/");
      return;
    }
    if (palette.open) return;
    previousFocus = document.activeElement;
    palette.showModal();
    input.focus();
  }
  function closePalette() {
    if (!palette.open) return;
    palette.close();
    previousFocus?.focus();
  }

  document.addEventListener("keydown", (event) => {
    const typing = event.target.matches("textarea, [contenteditable='true']");
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k" && !typing) {
      event.preventDefault();
      openPalette();
      return;
    }
    if (!palette.open) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closePalette();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive(activeIndex + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive(activeIndex - 1);
    } else if (event.key === "Enter" && document.activeElement === input) {
      const item = results()[activeIndex];
      if (item) {
        event.preventDefault();
        window.location.assign(item.href);
      }
    }
  });
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-command-palette-close]")) closePalette();
  });
  palette.addEventListener("close", () => { activeIndex = 0; });
  document.body.addEventListener("htmx:afterSwap", (event) => {
    if (event.target.matches("[data-palette-results], #palette-results")) setActive(0);
    if (event.target.matches("#random-card")) event.target.querySelector("[data-random-heading], .random-reveal")?.focus();
  });
  document.body.addEventListener("htmx:responseError", (event) => {
    if (event.target === input) document.querySelector("[data-palette-results]").innerHTML = '<p class="palette-empty">Search unavailable. Try again.</p>';
  });
})();
