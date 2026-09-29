#!/usr/bin/env node
/**
 * Astrix Desktop Proxy
 * Serves Astrix through localhost and injects the desktop reformatter.
 *
 * Usage:
 *   node server.mjs
 *   open http://127.0.0.1:3847/auth
 */
import http from "node:http";
import https from "node:https";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { URL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 3847);
const UPSTREAM = process.env.ASTRIX_ORIGIN || "https://astrix.elynn.me";
const SHARED = path.join(__dirname, "..", "shared");

const desktopCss = fs.readFileSync(path.join(SHARED, "desktop.css"), "utf8");
const desktopJs = fs.readFileSync(path.join(SHARED, "desktop.js"), "utf8");

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "content-encoding",
  "content-length",
]);

function fetchUpstream(targetUrl, reqHeaders) {
  return new Promise((resolve, reject) => {
    const u = new URL(targetUrl);
    const lib = u.protocol === "https:" ? https : http;
    const headers = { ...reqHeaders };
    // Upstream host
    headers.host = u.host;
    // Avoid compressed bodies so we can rewrite HTML
    delete headers["accept-encoding"];
    headers["accept-encoding"] = "identity";
    // Don't send localhost origin as-is in a confusing way
    if (headers.origin) headers.origin = UPSTREAM;
    if (headers.referer) {
      try {
        const r = new URL(headers.referer);
        headers.referer = UPSTREAM + r.pathname + r.search;
      } catch {
        headers.referer = UPSTREAM + "/";
      }
    }

    const request = lib.request(
      {
        protocol: u.protocol,
        hostname: u.hostname,
        port: u.port || (u.protocol === "https:" ? 443 : 80),
        path: u.pathname + u.search,
        method: "GET",
        headers,
      },
      (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => {
          resolve({
            status: res.statusCode || 502,
            headers: res.headers,
            body: Buffer.concat(chunks),
          });
        });
      }
    );
    request.on("error", reject);
    request.end();
  });
}

function rewriteHtml(html) {
  const inject =
    `\n<link rel="stylesheet" href="/__astrix_desktop/desktop.css" />\n` +
    `<script src="/__astrix_desktop/desktop.js" defer></script>\n`;

  if (html.includes("</head>")) {
    return html.replace("</head>", inject + "</head>");
  }
  return inject + html;
}

function rewriteSetCookie(value) {
  // Drop Domain= so cookies bind to localhost proxy
  return value
    .split(/,(?=\s*[^;]+=[^;]+)/)
    .map((c) =>
      c
        .replace(/;\s*Domain=[^;]*/gi, "")
        .replace(/;\s*Secure/gi, "")
        .replace(/;\s*SameSite=None/gi, "; SameSite=Lax")
    )
    .join(",");
}

function send(res, status, headers, body) {
  res.writeHead(status, headers);
  res.end(body);
}

const server = http.createServer(async (req, res) => {
  try {
    const reqUrl = new URL(req.url || "/", `http://${req.headers.host}`);

    // Local reformatter assets
    if (reqUrl.pathname === "/__astrix_desktop/desktop.css") {
      return send(res, 200, { "content-type": "text/css; charset=utf-8", "cache-control": "no-store" }, desktopCss);
    }
    if (reqUrl.pathname === "/__astrix_desktop/desktop.js") {
      return send(
        res,
        200,
        { "content-type": "application/javascript; charset=utf-8", "cache-control": "no-store" },
        desktopJs
      );
    }

    // Only proxy safe methods for the HTML shell + static assets.
    // For POST/auth APIs, forward to upstream with rewritten host.
    const upstreamUrl = UPSTREAM + reqUrl.pathname + reqUrl.search;
    const method = (req.method || "GET").toUpperCase();

    if (method !== "GET" && method !== "HEAD" && method !== "OPTIONS") {
      // Stream non-GET through (login, APIs)
      return proxyStream(req, res, upstreamUrl);
    }

    if (method === "OPTIONS") {
      res.writeHead(204, {
        "access-control-allow-origin": "*",
        "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        "access-control-allow-headers": req.headers["access-control-request-headers"] || "*",
      });
      return res.end();
    }

    const upstream = await fetchUpstream(upstreamUrl, req.headers);
    const contentType = String(upstream.headers["content-type"] || "");
    const outHeaders = {};
    for (const [k, v] of Object.entries(upstream.headers)) {
      if (HOP_BY_HOP.has(k.toLowerCase())) continue;
      if (k.toLowerCase() === "set-cookie") {
        const cookies = Array.isArray(v) ? v : [v];
        outHeaders["set-cookie"] = cookies.map(rewriteSetCookie);
        continue;
      }
      // Avoid framing / CSP blocking our inject on proxy
      if (["content-security-policy", "x-frame-options"].includes(k.toLowerCase())) continue;
      outHeaders[k] = v;
    }

    let body = upstream.body;
    if (contentType.includes("text/html")) {
      const html = rewriteHtml(body.toString("utf8"));
      body = Buffer.from(html, "utf8");
      outHeaders["content-type"] = "text/html; charset=utf-8";
    }

    // Fix absolute redirects back onto the proxy
    if (outHeaders.location && String(outHeaders.location).startsWith(UPSTREAM)) {
      outHeaders.location = String(outHeaders.location).replace(UPSTREAM, `http://127.0.0.1:${PORT}`);
    }

    outHeaders["content-length"] = Buffer.byteLength(body);
    outHeaders["cache-control"] = "no-store";
    send(res, upstream.status, outHeaders, method === "HEAD" ? undefined : body);
  } catch (err) {
    console.error(err);
    send(res, 502, { "content-type": "text/plain" }, "Bad gateway: " + err.message);
  }
});

function proxyStream(req, res, upstreamUrl) {
  const u = new URL(upstreamUrl);
  const lib = u.protocol === "https:" ? https : http;
  const headers = { ...req.headers, host: u.host };
  if (headers.origin) headers.origin = UPSTREAM;

  const proxyReq = lib.request(
    {
      protocol: u.protocol,
      hostname: u.hostname,
      port: u.port || 443,
      path: u.pathname + u.search,
      method: req.method,
      headers,
    },
    (proxyRes) => {
      const out = { ...proxyRes.headers };
      delete out["content-security-policy"];
      delete out["x-frame-options"];
      if (out["set-cookie"]) {
        const cookies = Array.isArray(out["set-cookie"]) ? out["set-cookie"] : [out["set-cookie"]];
        out["set-cookie"] = cookies.map(rewriteSetCookie);
      }
      res.writeHead(proxyRes.statusCode || 502, out);
      proxyRes.pipe(res);
    }
  );
  proxyReq.on("error", (err) => {
    res.writeHead(502, { "content-type": "text/plain" });
    res.end("Bad gateway: " + err.message);
  });
  req.pipe(proxyReq);
}

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Astrix desktop proxy → ${UPSTREAM}`);
  console.log(`Open http://127.0.0.1:${PORT}/auth`);
});
