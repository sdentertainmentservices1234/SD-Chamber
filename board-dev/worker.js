// SD-Chamber — SC display-board relay (Cloudflare Worker)
// Fetches the Supreme Court live display board server-side (browsers can't:
// the gov site sends no CORS headers) and returns it to our app with CORS on.
// A short edge cache means 100 chamber devices polling = ~2 fetches/min at source.
//
// Deploy: dash.cloudflare.com → Workers & Pages → Create → paste this → Deploy.
// Then use the *.workers.dev URL in board.html (BOARD_PROXY).

const SRC = "https://wdb.sci.gov.in/get_board.php";      // ?ctype=c (regular) | v (video)
const EDGE_TTL = 15;                                     // seconds; source itself updates every 30s

export default {
  async fetch(req) {
    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "*",
    };
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });

    const u = new URL(req.url);
    const ctype = (u.searchParams.get("ctype") || "c").toLowerCase();
    if (ctype !== "c" && ctype !== "v")
      return new Response("bad ctype", { status: 400, headers: cors });

    const target = `${SRC}?ctype=${ctype}`;
    // Edge-cache by URL so many clients collapse to a few origin fetches.
    const cache = caches.default;
    const key = new Request(target, { method: "GET" });
    let hit = await cache.match(key);
    if (hit) {
      const h = new Headers(hit.headers); Object.entries(cors).forEach(([k, v]) => h.set(k, v));
      h.set("X-Board-Cache", "hit");
      return new Response(hit.body, { status: hit.status, headers: h });
    }

    let resp;
    try {
      resp = await fetch(target, {
        headers: {
          // The gov server rejects blank UAs; present a normal browser.
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
                        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
          "Accept": "text/html,application/xhtml+xml",
          "Referer": "https://wdb.sci.gov.in/display_original.php",
        },
        cf: { cacheTtl: EDGE_TTL, cacheEverything: true },
      });
    } catch (e) {
      return new Response("upstream fetch failed: " + e, { status: 502, headers: cors });
    }

    const body = await resp.text();
    const out = new Response(body, {
      status: resp.status,
      headers: {
        ...cors,
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": `public, max-age=${EDGE_TTL}`,
        "X-Board-Cache": "miss",
      },
    });
    // Store a cacheable copy (strip CORS-* so the cached entry stays generic).
    const store = out.clone();
    await cache.put(key, new Response(store.body, {
      status: resp.status,
      headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": `public, max-age=${EDGE_TTL}` },
    }));
    return out;
  },
};
