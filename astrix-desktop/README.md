# Astrix Desktop Wrapper

Unofficial layout wrapper for [Astrix by ELYNN](https://astrix.elynn.me/).

Astrix’s marketing homepage is fine on desktop, but app screens like `/auth`, onboarding, and chat stay locked to a phone-width column (`max-w-md` ≈ 448px). This project reflows that content for normal desktop screens.

## What you get

| Surface | Desktop behavior |
| --- | --- |
| `/auth` | Split layout: brand copy on the left, form on the right |
| `/intro`, `/onboarding`, `/value`, `/paywall`, `/checkout` | Wider readable column (~720–880px) |
| `/home`, `/chat/:id`, `/profile` | Expanded shells, wider chat bubbles, floating bottom nav pill |

Phone viewports (&lt;900px) are left unchanged.

## Install options

### 1. Chrome / Edge extension (recommended)

1. Open `chrome://extensions` (or `edge://extensions`)
2. Turn on **Developer mode**
3. **Load unpacked** → choose `astrix-desktop/extension`
4. Open https://astrix.elynn.me/auth and widen the window

### 2. Tampermonkey / Violentmonkey

1. Install the userscript manager
2. Create a new script from `astrix-desktop/userscript/astrix-desktop.user.js`
3. Reload Astrix

### 3. Local proxy

Injects the same CSS/JS by proxying the live site through localhost:

```bash
cd astrix-desktop/proxy
node server.mjs
# → http://127.0.0.1:3847/auth
```

## Preview demo

Static before/after mock (no live Astrix required):

```bash
cd astrix-desktop/preview
python3 -m http.server 3850
# → http://127.0.0.1:3850
```

## Project layout

```
astrix-desktop/
  shared/           # source of truth: desktop.css + desktop.js
  extension/        # Chrome MV3 extension (copies of shared)
  userscript/       # Tampermonkey script
  proxy/server.mjs  # localhost injector proxy
  preview/          # static before/after demo
```

## Notes

- This only restyles / lightly rearranges Astrix’s existing DOM. It does not fork their backend or scrape private readings.
- Astrix may change class names; if a page stops reforming, re-check `shared/desktop.css` selectors against the live DOM.
- Auth and paid features still run on Astrix’s servers — use the extension or userscript for the most reliable login cookies.
