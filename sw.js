/* SD Chamber — service worker.
   STALE-WHILE-REVALIDATE: the shell (index.html), the Firebase SDK, fonts and
   icons are served from cache INSTANTLY and refreshed in the background — so
   opens are fast on mobile instead of waiting to re-download ~700KB each time.
   Live data (Firestore, Auth, the hourly court-updates.json) is NEVER cached.
   Updates land on the next open, or immediately via the in-app Refresh button. */
const CACHE = "chamber-shell-v8";
const SHELL = ["./", "./index.html", "./manifest.json",
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
  if (host.includes("firestore") || host.includes("identitytoolkit") ||
      host.includes("securetoken") || host.includes("firebaseio") ||
      host.includes("firebaseinstallations")) return;
  if (url.pathname.endsWith("court-updates.json")) return;   // hourly causelist — always fresh
  // Static shell + libraries + fonts + icons — serve from cache, refresh behind.
  const isStatic = url.origin === location.origin
    || host === "www.gstatic.com"      // firebase SDK
    || host === "fonts.googleapis.com" // font CSS
    || host === "fonts.gstatic.com"    // font files
    || host === "cdn.jsdelivr.net";    // tabler icons
  if (!isStatic) return;
  // status 0 = opaque cross-origin (fonts / firebase SDK) — cache those too.
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(req);
    const net = fetch(req).then(r => { if (r && (r.status === 200 || r.status === 0)) cache.put(req, r.clone()); return r; })
                          .catch(() => hit);
    return hit || net;   // cache-first for speed; network refreshes the cache for next time
  })());
});
