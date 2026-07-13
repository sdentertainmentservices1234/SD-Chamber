/* SD War Room / Display Board — service worker.
   The board HTML is NETWORK-FIRST so a deployed change is live on the next open
   (cache is the offline fallback). Firebase SDK + fonts + icons are CACHE-FIRST
   so the login button is armed instantly. Live data (the SC board relay,
   Firestore, Auth) is NEVER cached. */
const CACHE = "sdboard-v3";
const SHELL = ["./board.html", "./board-manifest.json",
  "./icon-192.png", "./icon-512.png", "./apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url), host = url.hostname;
  // Live data — always straight to network, never cache.
  if (host.endsWith("workers.dev") || host.includes("firestore") ||
      host.includes("identitytoolkit") || host.includes("securetoken") ||
      host.includes("firebaseio") || host.includes("firebaseinstallations")) return;
  // Board HTML — NETWORK-FIRST so fixes go live immediately; cache is the offline fallback.
  const isHTML = req.mode === "navigate"
    || (url.origin === location.origin && (url.pathname.endsWith(".html") || url.pathname.endsWith("/")));
  if (isHTML) {
    e.respondWith(
      fetch(req).then(r => {
        if (r && r.status === 200) caches.open(CACHE).then(c => c.put(req, r.clone()));
        return r;
      }).catch(() => caches.match(req).then(m => m || caches.match("./board.html")))
    );
    return;
  }
  // Libraries + fonts + icons (immutable, versioned) — cache-first for speed.
  // status 0 = opaque cross-origin (fonts / firebase SDK) — cache those too.
  const isStatic = url.origin === location.origin
    || host === "www.gstatic.com"      // firebase SDK
    || host === "fonts.googleapis.com" // font CSS
    || host === "fonts.gstatic.com"    // font files
    || host === "cdn.jsdelivr.net";    // tabler icons
  if (!isStatic) return;
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(req);
    const net = fetch(req).then(r => { if (r && (r.status === 200 || r.status === 0)) cache.put(req, r.clone()); return r; })
                          .catch(() => hit);
    return hit || net;
  })());
});
