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


def parse_courts(text):
    """Text of one list PDF -> {court_number(str): {coram, total, fresh}}."""
    courts = {}
    cur = None
    in_header = False
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
            courts.setdefault(cur, {"coram": "", "total": "", "fresh": ""})
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
        if in_header:
            if is_coram(line):
                piece = re.sub(r"\s+", " ", line).strip()
                courts[cur]["coram"] = (courts[cur]["coram"] + " " + piece).strip()[:200]
            else:
                # first non-blank, non-coram line (item, note, party) ends the header
                in_header = False
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


def build_for_date(date_str):
    lists_found, lists = [], {}
    for human, variants in LIST_TYPES.items():
        merged = {}
        for suffix, variant in variants:
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
    return lists_found, lists


def main():
    dates = [sys.argv[1]] if len(sys.argv) > 1 else upcoming_days(WINDOW_DAYS)
    print("Checking dates:", ", ".join(dates))
    by_date = {}
    for date_str in dates:
        lists_found, lists = build_for_date(date_str)
        if lists_found:
            by_date[date_str] = {"lists_found": lists_found, "lists": lists}
            ncourts = sum(len(v) for v in lists.values())
            print("  {}: {} list(s), {} court bench(es)".format(date_str, len(lists), ncourts))
    result = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "window": dates,
        "by_date": by_date,
        "note": "Per-court bench (coram) from the SC published lists. Drafting aid "
                "only — the court's published list is authoritative.",
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("Wrote {} — {} day(s) with lists.".format(OUTPUT_FILE, len(by_date)))


if __name__ == "__main__":
    main()
