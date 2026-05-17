/* Service worker: makes the app installable and work offline.
   Strategy: precache the app shell + the humanizer package, then
   cache-first with network fallback for everything else (incl. the
   Pyodide runtime from the CDN, cached opportunistically on first use). */

const CACHE = "humanizer-v3";
const SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./config.js",
  "./auth.js",
  "./billing.js",
  "./app.js",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-maskable-512.png",
  "./icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      await cache.addAll(SHELL).catch(() => {});
      // Also precache the Python package files listed in the manifest.
      try {
        const list = await (await fetch("./humanizer/__files__.json", { cache: "no-cache" })).json();
        await cache.addAll(
          ["./humanizer/__files__.json", ...list.map((f) => "./humanizer/" + f)]
        );
      } catch (e) {}
      self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  event.respondWith(
    (async () => {
      const cached = await caches.match(req);
      if (cached) return cached;
      try {
        const res = await fetch(req);
        // Cache successful or opaque (cross-origin CDN) responses.
        if (res && (res.ok || res.type === "opaque")) {
          const cache = await caches.open(CACHE);
          cache.put(req, res.clone()).catch(() => {});
        }
        return res;
      } catch (e) {
        // Offline and not cached: fall back to the app shell for navigations.
        if (req.mode === "navigate") {
          const shell = await caches.match("./index.html");
          if (shell) return shell;
        }
        throw e;
      }
    })()
  );
});
