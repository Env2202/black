/**
 * Astrix Desktop Wrapper — DOM reformatter
 * Detects phone-shell routes and rearranges key pages for desktop.
 */
(function () {
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

    // Prefer the existing centered content column
    const content =
      shell.querySelector(".relative.z-10.w-full.max-w-md") ||
      shell.querySelector(".relative.z-10.w-full.max-w-md.mx-auto.px-4") ||
      shell.querySelector("[class*='max-w-md']");

    if (!content) return;

    // Real headline lives inside the glass panel, not the top logo strip
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
    if (logoStrip) {
      logoStrip.classList.add("astrix-desktop-hide-mobile-hero");
    }

    let brand = shell.querySelector(".astrix-desktop-brand-pane");
    if (!brand) {
      brand = document.createElement("aside");
      brand.className = "astrix-desktop-brand-pane";
      brand.innerHTML =
        '<div class="astrix-desktop-mark">✦ Astrix by ELYNN</div>' +
        "<h1></h1><p></p>";
      shell.insertBefore(brand, content);
    }

    const h1 = brand.querySelector("h1");
    const p = brand.querySelector("p");
    if (h1 && textOf(h1) !== title) h1.textContent = title;
    if (p && textOf(p) !== subtitle) p.textContent = subtitle;

    shell.setAttribute(MARK_ATTR, "1");
  }

  function widenNarrowShells() {
    // Defensive: some shells use inline styles or late-mounted classes
    document.querySelectorAll("[class*='max-w-md']").forEach((el) => {
      if (el.closest("[role='dialog'], [data-radix-portal], [data-sidebar]")) return;
      const rect = el.getBoundingClientRect();
      if (rect.width > 0 && rect.width < 520 && el.clientWidth < 520) {
        el.style.maxWidth = "";
      }
    });
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
    widenNarrowShells();
  }

  // SPA route changes: patch history + observe DOM
  let lastPath = pathOf();
  const notify = () => {
    const next = pathOf();
    if (next !== lastPath) {
      lastPath = next;
      // Allow React to paint the new route before enhancing
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
    // Throttle: React remounts often during auth/onboarding
    if (mo._t) return;
    mo._t = setTimeout(() => {
      mo._t = null;
      apply();
    }, 80);
  });

  function start() {
    apply();
    if (document.body) {
      mo.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
