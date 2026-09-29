// ==UserScript==
// @name         Astrix Desktop Layout
// @namespace    https://github.com/Env2202/black
// @version      1.0.0
// @description  Reflows Astrix phone-locked pages into a usable desktop layout
// @author       Astrix Desktop Wrapper
// @match        https://astrix.elynn.me/*
// @match        https://voice-connect-joy.lovable.app/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  const CSS = `
/* INLINE_DESKTOP_CSS_START */
@media (min-width: 900px) {
  html { scroll-behavior: smooth; }
  body { overflow-x: hidden !important; }

  .relative.z-10.w-full.max-w-md,
  .relative.z-10.w-full.max-w-md.mx-auto,
  .relative.z-10.w-full.max-w-md.mx-auto.px-4,
  .relative.z-10.w-full.max-w-md.px-4,
  .w-full.max-w-md,
  .stack.stack-lg.w-full.max-w-md,
  .p-4.md\\:p-6.max-w-lg.mx-auto.pb-24 {
    max-width: min(1120px, 92vw) !important;
    width: 100% !important;
  }

  body.astrix-desktop-auth #root > div.min-h-screen {
    display: grid !important;
    grid-template-columns: minmax(280px, 1.05fr) minmax(360px, 0.95fr) !important;
    align-items: stretch !important;
    min-height: 100dvh !important;
  }

  body.astrix-desktop-auth #root > div.min-h-screen > .absolute,
  body.astrix-desktop-auth #root > div.min-h-screen > [aria-hidden="true"] {
    grid-column: 1 / -1 !important;
    grid-row: 1 !important;
  }

  body.astrix-desktop-auth .astrix-desktop-brand-pane {
    position: relative;
    z-index: 5;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: clamp(2rem, 5vw, 4.5rem);
    min-height: 100dvh;
  }

  body.astrix-desktop-auth .astrix-desktop-brand-pane h1 {
    font-size: clamp(2.4rem, 4vw, 3.6rem);
    line-height: 1.1;
    letter-spacing: -0.02em;
    margin: 0 0 1rem;
    color: #f7f1ff;
  }

  body.astrix-desktop-auth .astrix-desktop-brand-pane p {
    font-size: 1.125rem;
    line-height: 1.55;
    color: rgba(247, 241, 255, 0.72);
    max-width: 28rem;
    margin: 0;
  }

  body.astrix-desktop-auth .astrix-desktop-brand-pane .astrix-desktop-mark {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.95rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: rgba(247, 241, 255, 0.55);
    margin-bottom: 1.5rem;
  }

  body.astrix-desktop-auth .relative.z-10.w-full.max-w-md,
  body.astrix-desktop-auth .relative.z-10.w-full.max-w-md.mx-auto.px-4 {
    position: relative !important;
    z-index: 10;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    max-width: 440px !important;
    width: 100% !important;
    margin: 0 auto !important;
    padding: clamp(1.5rem, 3vw, 2.5rem) !important;
    min-height: 100dvh;
  }

  body.astrix-desktop-auth .astrix-desktop-hide-mobile-hero {
    display: none !important;
  }

  body.astrix-desktop-flow .relative.z-10.w-full.max-w-md,
  body.astrix-desktop-flow .relative.z-10.w-full.max-w-md.px-4,
  body.astrix-desktop-flow .w-full.max-w-md {
    max-width: min(720px, 90vw) !important;
  }

  body.astrix-desktop-flow .stack.stack-lg.w-full.max-w-2xl,
  body.astrix-desktop-flow .flex-1.max-w-2xl.mx-auto.w-full {
    max-width: min(880px, 92vw) !important;
  }

  body.astrix-desktop-app .flex-1.w-full.max-w-6xl.mx-auto,
  body.astrix-desktop-app .p-4.md\\:p-6.max-w-lg.mx-auto.pb-24 {
    max-width: min(1180px, 94vw) !important;
  }

  body.astrix-desktop-app [class*="max-w-[80%]"],
  body.astrix-desktop-app [class*="max-w-[75%]"],
  body.astrix-desktop-app [class*="max-w-[85%]"] {
    max-width: min(42rem, 70%) !important;
  }

  body.astrix-desktop-app nav.fixed.bottom-0,
  body.astrix-desktop-app [class*="fixed bottom-0"] {
    left: 50% !important;
    right: auto !important;
    transform: translateX(-50%);
    width: min(420px, 90vw) !important;
    border-radius: 999px !important;
    margin-bottom: 1rem !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    backdrop-filter: blur(16px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
  }

  body.astrix-desktop-app .flex.flex-col.lg\\:flex-row {
    gap: 2rem !important;
  }

  #astrix-desktop-banner {
    position: fixed;
    top: 12px;
    right: 12px;
    z-index: 2147483646;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.45rem 0.75rem;
    border-radius: 999px;
    background: rgba(18, 10, 28, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #f4ecff;
    font: 500 12px/1.2 ui-sans-serif, system-ui, sans-serif;
    letter-spacing: 0.02em;
    backdrop-filter: blur(10px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    pointer-events: none;
  }

  #astrix-desktop-banner span.dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #7ddea2;
    box-shadow: 0 0 0 3px rgba(125, 222, 162, 0.2);
  }
}

@media (max-width: 899px) {
  #astrix-desktop-banner { display: none !important; }
}
/* INLINE_DESKTOP_CSS_END */
`;

  const style = document.createElement("style");
  style.id = "astrix-desktop-userscript-css";
  style.textContent = CSS;
  (document.head || document.documentElement).appendChild(style);

  // ---- desktop.js (same reformatter) ----
  const DESKTOP_MQ = window.matchMedia("(min-width: 900px)");
  const FLOW_PATHS = ["/intro", "/onboarding", "/value", "/paywall", "/checkout", "/thank-you"];
  const APP_PATHS = ["/home", "/profile"];
  const MARK_ATTR = "data-astrix-desktop-enhanced";

  function pathOf() {
    return location.pathname.replace(/\/$/, "") || "/";
  }

  function isChat(path) {
    return path.startsWith("/chat/");
  }

  function classify(path) {
    if (path === "/auth") return "auth";
    if (FLOW_PATHS.includes(path)) return "flow";
    if (APP_PATHS.includes(path) || isChat(path)) return "app";
    return "other";
  }

  function clearModeClasses() {
    document.body.classList.remove(
      "astrix-desktop-auth",
      "astrix-desktop-flow",
      "astrix-desktop-app",
      "astrix-desktop-active"
    );
  }

  function ensureBanner() {
    if (document.getElementById("astrix-desktop-banner")) return;
    const el = document.createElement("div");
    el.id = "astrix-desktop-banner";
    el.innerHTML = '<span class="dot" aria-hidden="true"></span> Desktop layout on';
    document.documentElement.appendChild(el);
  }

  function textOf(node) {
    return (node && node.textContent ? node.textContent : "").replace(/\s+/g, " ").trim();
  }

  function enhanceAuth() {
    const shell = document.querySelector("#root > div.min-h-screen");
    if (!shell) return;

    const content =
      shell.querySelector(".relative.z-10.w-full.max-w-md") ||
      shell.querySelector(".relative.z-10.w-full.max-w-md.mx-auto.px-4") ||
      shell.querySelector("[class*='max-w-md']");
    if (!content) return;

    const heroBlock =
      content.querySelector(".glass-panel .text-center.stack-sm") ||
      content.querySelector(".glass-panel .stack-sm.text-center") ||
      content.querySelector(".glass-panel h1")?.parentElement ||
      null;
    const logoStrip = content.querySelector(".text-center.mb-8");

    let title = "Your cosmic reading is ready";
    let subtitle = "Create a free account to see your personalized insights";
    if (heroBlock) {
      const h = heroBlock.matches("h1, h2") ? heroBlock : heroBlock.querySelector("h1, h2");
      const p = heroBlock.matches("h1, h2") ? null : heroBlock.querySelector("p");
      if (h && textOf(h)) title = textOf(h).replace(/✨/g, "").trim();
      if (p && textOf(p)) subtitle = textOf(p);
      heroBlock.classList.add("astrix-desktop-hide-mobile-hero");
    }
    if (logoStrip) logoStrip.classList.add("astrix-desktop-hide-mobile-hero");

    let brand = shell.querySelector(".astrix-desktop-brand-pane");
    if (!brand) {
      brand = document.createElement("aside");
      brand.className = "astrix-desktop-brand-pane";
      brand.innerHTML =
        '<div class="astrix-desktop-mark">✦ Astrix by ELYNN</div><h1></h1><p></p>';
      shell.insertBefore(brand, content);
    }

    const h1 = brand.querySelector("h1");
    const p = brand.querySelector("p");
    if (h1 && textOf(h1) !== title) h1.textContent = title;
    if (p && textOf(p) !== subtitle) p.textContent = subtitle;

    shell.setAttribute(MARK_ATTR, "1");
  }

  function apply() {
    if (!DESKTOP_MQ.matches) {
      clearModeClasses();
      const banner = document.getElementById("astrix-desktop-banner");
      if (banner) banner.remove();
      return;
    }

    const mode = classify(pathOf());
    clearModeClasses();
    document.body.classList.add("astrix-desktop-active");

    if (mode === "auth") {
      document.body.classList.add("astrix-desktop-auth");
      enhanceAuth();
    } else if (mode === "flow") {
      document.body.classList.add("astrix-desktop-flow");
    } else if (mode === "app") {
      document.body.classList.add("astrix-desktop-app");
    }

    ensureBanner();
  }

  let lastPath = pathOf();
  const notify = () => {
    const next = pathOf();
    if (next !== lastPath) {
      lastPath = next;
      requestAnimationFrame(() => requestAnimationFrame(apply));
    } else {
      apply();
    }
  };

  const wrapHistory = (method) => {
    const original = history[method];
    history[method] = function (...args) {
      const ret = original.apply(this, args);
      notify();
      return ret;
    };
  };
  wrapHistory("pushState");
  wrapHistory("replaceState");
  window.addEventListener("popstate", notify);
  DESKTOP_MQ.addEventListener("change", apply);

  const mo = new MutationObserver(() => {
    if (mo._t) return;
    mo._t = setTimeout(() => {
      mo._t = null;
      apply();
    }, 80);
  });

  function start() {
    apply();
    if (document.body) mo.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
