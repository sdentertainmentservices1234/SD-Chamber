/* SD War Room / Display Board — service worker.
   Caches the shell + the Firebase SDK + fonts/icons so opens are instant and
   the login button is armed immediately (no waiting on a fresh SDK download).
   Live data (the SC board relay, Firestore, Auth) is NEVER cached. */
const CACHE = "sdboard-v1";
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
  // Static shell + libraries + fonts + icons — stale-while-revalidate:
  // serve from cache instantly, refresh in the background.
  const isStatic = url.origin === location.origin
    || host === "www.gstatic.com"      // firebase SDK
    || host === "fonts.googleapis.com" // font CSS
    || host === "fonts.gstatic.com"    // font files
    || host === "cdn.jsdelivr.net";    // tabler icons
  if (!isStatic) return;
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(req);
    const net = fetch(req).then(r => { if (r && r.status === 200) cache.put(req, r.clone()); return r; })
                          .catch(() => hit);
    return hit || net;
  })());
});
