// SD-Chamber — SC display-board relay (Cloudflare Worker)
// Fetches the Supreme Court live display board server-side (browsers can't:
// the gov site sends no CORS headers) and returns it to our app with CORS on.
// A short edge cache means 100 chamber devices polling = ~2 fetches/min at source.
//
//   ?ctype=c            -> the live court-wise board (regular).  ctype=v = video.
//   ?remarks=<token>    -> a court's FULL cause list, PARSED to a small
//                          { court, items:{ "5":"OVER", "7":"PASS OVER" } } JSON.
//                          The <token> is the display_court_all_cases.php query
//                          string taken from a court's row on the main board. The
//                          page itself is ~0.5 MB; parsing it here keeps the phone
//                          download to ~1 KB.
//
// Deploy: dash.cloudflare.com → Workers & Pages → Create → paste this → Deploy.
// Then use the *.workers.dev URL in board.html (BOARD_PROXY).

const HOST = "https://wdb.sci.gov.in";
const SRC  = HOST + "/get_board.php";                    // ?ctype=c (regular) | v (video)
const EDGE_TTL  = 6;                                     // board: 6s (see note below)
const RMK_TTL   = 25;                                    // remarks change slowly; cache longer

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
           "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "*",
};

// Parse a court's full-cause-list page down to { item -> remark }. Each matter is
// a <tr class="record"> whose LAST cell is the remark column; the bench writes
// OVER / PASS OVER (in bold) there, or leaves it blank. Only non-blank remarks are
// returned. Advocate/heading cells are excluded so a "P:"/"R:" never leaks in.
function parseRemarks(html) {
  const strip = s => s.replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&").replace(/\s+/g, " ").trim();
  const items = {};
  const rows = html.split(/<tr class="record"/i).slice(1);
  for (let raw of rows) {
    raw = raw.split(/<\/tr>/i)[0];
    const tds = [...raw.matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/gi)].map(m => m[1]);
    if (tds.length < 3) continue;
    const item = strip(tds[0]);
    if (!/^\d/.test(item)) continue;                     // first cell must be the item number
    const last = tds[tds.length - 1];                    // remark column
    const bold = last.match(/<b>([\s\S]*?)<\/b>/i);
    let rem = strip(bold ? bold[1] : last);
    if (!rem) continue;                                  // blank remark (the common case) — skip
    if (/\bVs\b|P:|R:/i.test(rem)) continue;             // safety: not a remark cell
    const up = rem.toUpperCase();
    let norm;
    if (/PASS\s*OVER/.test(up))      norm = "PASS OVER";
    else if (/^OVER$/.test(up))      norm = "OVER";
    else if (/PART\s*HEARD/.test(up))norm = "PART HEARD";
    else if (/DISPOSED/.test(up))    norm = "DISPOSED";
    else if (rem.length <= 24)       norm = rem;         // keep any other short remark verbatim
    else continue;
    items[item] = norm;
  }
  const cm = html.match(/Court\s+(\d+)\s*:/i);
  return { court: cm ? cm[1] : null, items };
}

async function upstream(url) {
  return fetch(url, {
    headers: {
      "User-Agent": UA,
      "Accept": "text/html,application/xhtml+xml",
      "Referer": HOST + "/display_original.php",
    },
    cf: { cacheTtl: EDGE_TTL, cacheEverything: true },
  });
}

export default {
  async fetch(req) {
    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
    const u = new URL(req.url);

    // ---- per-court remarks (parsed JSON) ----
    const token = u.searchParams.get("remarks");
    if (token != null) {
      if (!/^[A-Za-z0-9.]+$/.test(token))
        return new Response(JSON.stringify({ error: "bad token" }), { status: 400, headers: { ...CORS, "Content-Type": "application/json" } });
      const target = `${HOST}/display_court_all_cases.php?${token}`;
      const cache = caches.default;
      const key = new Request("https://cache/remarks/" + token, { method: "GET" });
      let hit = await cache.match(key);
      if (hit) {
        const h = new Headers(hit.headers); Object.entries(CORS).forEach(([k, v]) => h.set(k, v));
        h.set("X-Board-Cache", "hit");
        return new Response(hit.body, { status: 200, headers: h });
      }
      let resp;
      try { resp = await upstream(target); }
      catch (e) { return new Response(JSON.stringify({ error: "upstream " + e }), { status: 502, headers: { ...CORS, "Content-Type": "application/json" } }); }
      const body = await resp.text();
      const json = JSON.stringify(parseRemarks(body));
      const headers = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": `public, max-age=${RMK_TTL}` };
      await cache.put(key, new Response(json, { headers }));
      return new Response(json, { headers: { ...CORS, ...headers, "X-Board-Cache": "miss" } });
    }

    // ---- live court-wise board ----
    const ctype = (u.searchParams.get("ctype") || "c").toLowerCase();
    if (ctype !== "c" && ctype !== "v")
      return new Response("bad ctype", { status: 400, headers: CORS });

    const target = `${SRC}?ctype=${ctype}`;
    const cache = caches.default;
    const key = new Request(target, { method: "GET" });
    let hit = await cache.match(key);
    if (hit) {
      const h = new Headers(hit.headers); Object.entries(CORS).forEach(([k, v]) => h.set(k, v));
      h.set("X-Board-Cache", "hit");
      return new Response(hit.body, { status: hit.status, headers: h });
    }
    let resp;
    try { resp = await upstream(target); }
    catch (e) { return new Response("upstream fetch failed: " + e, { status: 502, headers: CORS }); }
    const body = await resp.text();
    const out = new Response(body, {
      status: resp.status,
      headers: { ...CORS, "Content-Type": "text/html; charset=utf-8", "Cache-Control": `public, max-age=${EDGE_TTL}`, "X-Board-Cache": "miss" },
    });
    await cache.put(key, new Response(body, {
      status: resp.status,
      headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": `public, max-age=${EDGE_TTL}` },
    }));
    return out;
  },
};
