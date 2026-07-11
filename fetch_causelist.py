#!/usr/bin/env python3
"""
Supreme Court of India — per-court BENCH (coram) fetcher for SD-Chamber.

Model (owner's decision, Jul 2026): the office Staff enter each listing on the
day sheet — court no, item no, causelist type, cause title, date, briefing
counsel. This scheduled Action cannot read the app's database, so it does NOT
search for the chamber's matters. Instead it downloads the published SC lists
for a rolling window of upcoming days and extracts, per (date, list-type,
court): the BENCH (coram) and the court's total/fresh counts. The app then
looks up whatever court/item/type/date Staff entered and fills in the
authoritative bench "as per the causelist".

Writes court-updates.json at the repo root; the app reads it same-origin.
Free: pure fetch + PDF text, no API keys. Drafting aid only — the court's
published list is authoritative.

List-type PDF codes (verified against real 13-07-2026 PDFs):
  Miscellaneous  M_J   |  Regular / Final  F_J  |  Chamber  M_C
  Single Judge   M_S   |  Registrar        M_R  |  Curative & Review  M_CC
Each publishes _1 (main) and, some days, _2 (supplementary).
"""

import io
import json
import re
import sys
import time
import datetime
import urllib.request

DAILY_BASE = "https://api.sci.gov.in/jonew/cl/{date}/{suffix}.pdf"

# human list-type -> (suffix, variant) to try, main first then supplementary so
# a later supplementary court entry overrides the main one for the same court.
LIST_TYPES = {
    "Miscellaneous":      [("M_J_1", "main"), ("M_J_2", "supp")],
    "Regular":            [("F_J_1", "main"), ("F_J_2", "supp")],
    "Chamber":            [("M_C_1", "main"), ("M_C_2", "supp")],
    "Single Judge":       [("M_S_1", "main"), ("M_S_2", "supp")],
    "Registrar":          [("M_R_1", "main"), ("M_R_2", "supp")],
    "Curative & Review":  [("M_CC_1", "main")],
}

WINDOW_DAYS = 8
OUTPUT_FILE = "court-updates.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; sd-chamber-causelist-bot/1.0)"}

COURT_RE = re.compile(r"COURT\s*NO\.?\s*[:\-]?\s*([0-9]+)", re.I)
CJ_RE    = re.compile(r"CHIEF\s+JUSTICE'?S\s+COURT", re.I)
REG_RE   = re.compile(r"REGISTRAR\s+COURT\s*NO\.?\s*[:\-]?\s*([0-9]+)", re.I)
# coram lines are a judge ("HON'BLE ...") or a registrar officer ("..., REGISTRAR"
# / "REGISTRAR (TIME..."). The registrar form is kept strict so a PARTY name that
# merely contains "registrar" (e.g. "THE SUB REGISTRAR POOYAPPALLY AND ORS.") is
# NOT mistaken for the bench.
JUDGE_RE = re.compile(r"^HON'?BLE\b", re.I)
REGOFF_RE = re.compile(r",\s*REGISTRAR\b|REGISTRAR\s*(\(|$)", re.I)
TOTAL_RE = re.compile(r"total\s*(?:matters)?\s*[:\-]?\s*([0-9]+)", re.I)
FRESH_RE = re.compile(r"fresh\s*(?:matters)?\s*[:\-]?\s*([0-9]+)", re.I)
ITEM_RE  = re.compile(r"^\s*([0-9]{1,4})\b")
SKIP_CORAM = re.compile(r"NOTE|APPRECIATED|ADJOURNMENT|ASSEMBLE|WILL SIT|NORMAL", re.I)


def is_coram(line):
    if SKIP_CORAM.search(line):
        return False
    return bool(JUDGE_RE.match(line) or REGOFF_RE.search(line))


def fetch_pdf(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=60) as resp:
            ct = resp.headers.get("Content-Type", "").lower()
            if resp.status == 200 and ct.startswith("application/pdf"):
                return resp.read()
    except Exception:
        pass
    return None


def probe_size(url):
    """Cheap change-detection: a 1KB ranged GET. Returns the PDF's total size,
    or None if the list isn't published (the server answers 200/HTML for
    missing files). Lets a frequent schedule re-download a multi-MB list ONLY
    when the court actually re-published it."""
    try:
        req = urllib.request.Request(url, headers={**HEADERS, "Range": "bytes=0-1023"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            ct = resp.headers.get("Content-Type", "").lower()
            if not ct.startswith("application/pdf"):
                return None
            m = re.search(r"/(\d+)\s*$", resp.headers.get("Content-Range", ""))
            if m:
                return int(m.group(1))
            cl = resp.headers.get("Content-Length")   # server ignored Range
            return int(cl) if cl else len(resp.read())
    except Exception:
        return None


def pdf_to_text(data):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    except Exception as e:
        print("  PDF extraction failed:", e)
        return ""


ITEM_LINE_RE = re.compile(r"^([0-9]{1,4})[.\)]?\s+(.+)$")


def parse_courts(text):
    """Text of one list PDF ->
       {court(str): {coram, total, fresh, items:{item(str): case-line}}}.
    The item line carries the case number + parties, so the app can auto-fill a
    matter's title from just court + item."""
    courts = {}
    cur = None
    in_header = False
    pending = None      # (court, item) awaiting a "Versus" respondent
    await_resp = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        court = None
        m = REG_RE.search(line) or COURT_RE.search(line)
        if m:
            court = m.group(1)
        elif CJ_RE.search(line):
            court = "1"
        if court is not None:
            cur = court
            courts.setdefault(cur, {"coram": "", "total": "", "fresh": "", "items": {}})
            # collect the bench only until we have it; page headers repeat the
            # court + coram on every page, so re-collecting would duplicate it.
            in_header = not courts[cur]["coram"]
            continue
        if cur is None:
            continue
        tm = TOTAL_RE.search(line)
        if tm and not courts[cur]["total"]:
            courts[cur]["total"] = tm.group(1)
        fm = FRESH_RE.search(line)
        if fm and not courts[cur]["fresh"]:
            courts[cur]["fresh"] = fm.group(1)
        # an item line — record its number -> petitioner side (first occurrence
        # only; page-header repeats won't overwrite). The respondent is captured
        # from the line after "Versus" so the title reads "Petitioner vs Resp".
        im = ITEM_LINE_RE.match(line)
        if im and re.search(r"[A-Za-z]{3}", im.group(2)):
            in_header = False
            it = im.group(1)
            if it not in courts[cur]["items"]:
                courts[cur]["items"][it] = re.sub(r"\s+", " ", im.group(2)).strip()[:70]
                pending = (cur, it); await_resp = False
            else:
                pending = None
            continue
        if pending is not None:
            if re.match(r"^versus$", line, re.I):
                await_resp = True
                continue
            if await_resp and re.search(r"[A-Za-z]{3}", line) \
                    and not re.match(r"^[\[{(]", line):   # skip [CAVEAT] etc.
                resp = re.sub(r"\s+", " ", line).strip()[:50]
                pc, pit = pending
                courts[pc]["items"][pit] += " VERSUS " + resp
                pending = None; await_resp = False
                continue
        if in_header:
            if is_coram(line):
                piece = re.sub(r"\s+", " ", line).strip()
                courts[cur]["coram"] = (courts[cur]["coram"] + " " + piece).strip()[:200]
            else:
                in_header = False
    for c in courts.values():
        if not c["total"]:
            c["total"] = str(len(c["items"]))   # SC lists have no total line
    return courts


def upcoming_days(n):
    ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    days, d, step = [], ist.date(), 0
    while len(days) < n and step < n * 2 + 4:
        if d.weekday() < 5:
            days.append(d.strftime("%Y-%m-%d"))
        d += datetime.timedelta(days=1)
        step += 1
    return days


def build_for_date(date_str, prev_day=None, prev_sizes=None):
    """Returns (lists_found, lists, sizes, reused). Probes every list URL with a
    1KB ranged GET first; if the sizes all match the previous run, the previous
    parse is reused wholesale — no PDF is downloaded."""
    sizes = {}
    for human, variants in LIST_TYPES.items():
        for suffix, variant in variants:
            s = probe_size(DAILY_BASE.format(date=date_str, suffix=suffix))
            if s:
                sizes[suffix] = s
            time.sleep(0.15)
    if prev_day is not None and sizes == (prev_sizes or {}):
        return prev_day.get("lists_found", []), prev_day.get("lists", {}), sizes, True
    lists_found, lists = [], {}
    for human, variants in LIST_TYPES.items():
        merged = {}
        for suffix, variant in variants:
            if suffix not in sizes:
                continue
            data = fetch_pdf(DAILY_BASE.format(date=date_str, suffix=suffix))
            if not data:
                continue
            text = pdf_to_text(data)
            if not text.strip():
                continue
            lists_found.append("{} ({})".format(human, variant))
            for court, info in parse_courts(text).items():
                merged[court] = info   # supplementary overrides main for same court
        if merged:
            lists[human] = merged
    return lists_found, lists, sizes, False


def main():
    dates = [sys.argv[1]] if len(sys.argv) > 1 else upcoming_days(WINDOW_DAYS)
    print("Checking dates:", ", ".join(dates))
    prev = {}
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            prev = json.load(f)
    except Exception:
        pass
    prev_by, prev_src = prev.get("by_date", {}), prev.get("sources", {})
    by_date, sources = {}, {}
    for date_str in dates:
        lists_found, lists, sizes, reused = build_for_date(
            date_str, prev_by.get(date_str), prev_src.get(date_str))
        if sizes:
            sources[date_str] = sizes
        if lists_found or lists:
            by_date[date_str] = {"lists_found": lists_found, "lists": lists}
            ncourts = sum(len(v) for v in lists.values())
            print("  {}: {} list(s), {} courts{}".format(
                date_str, len(lists), ncourts, "  [unchanged — reused]" if reused else "  [FETCHED]"))
    # Nothing new anywhere -> leave the file untouched so the workflow commits
    # nothing and Pages doesn't rebuild. (generated_at = time of last CHANGE.)
    if prev and json.dumps(by_date, sort_keys=True) == json.dumps(prev_by, sort_keys=True) \
            and json.dumps(sources, sort_keys=True) == json.dumps(prev_src, sort_keys=True):
        print("No change since last run — output left untouched.")
        return
    result = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "window": dates,
        "by_date": by_date,
        "sources": sources,
        "note": "Per-court bench + per-item case line from the SC published lists. "
                "Drafting aid only — the court's published list is authoritative.",
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("Wrote {} — {} day(s) with lists.".format(OUTPUT_FILE, len(by_date)))


if __name__ == "__main__":
    main()
