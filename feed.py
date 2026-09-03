#!/usr/bin/env python3
"""ETRX wide feed (Product 1): every HS2 chapter × the top-N origins (+ EU, + all
countries), monthly since 2010, same formula and source as the index. Delivered
as files; NOT published in docs/ (paid product). Current-vintage only — the
first-print vintage ledger covers the 13 core series, not the wide feed (v1).

  uv run python feed.py build [--origins 60]   full history (checkpointed, resumable)
  uv run python feed.py update                 append the latest settled month
  uv run python feed.py pack                   zip feed/by_origin -> feed/dist/

Calls: build ≈ 5 per origin (4-year chunks); update = 1 per origin.
feed/ is gitignored except README + manifest; rebuildable from Census."""
import csv
import json
import os
import sys
import time
import zipfile

import index_build as ib

FEED = os.path.join(ib.ROOT, "feed")
BY_ORIGIN = os.path.join(FEED, "by_origin")
CHECKPOINT = os.path.join(FEED, "checkpoint.jsonl")
MANIFEST = os.path.join(FEED, "manifest.json")
COLS = ["data_month", "cty_code", "cty_name", "chapter", "rate", "rate_dutiable",
        "duty_free_share", "con_val", "cal_dut", "dut_val"]


def latest_month():
    months = ib.settled_months(ib.read_prints())
    return months[-1] if months else ib.fatal("no settled months in the ledger")


def rank_origins(month, key, n):
    rows = ib.api_get({"get": "CTY_CODE,CTY_NAME,CON_VAL_MO", "SUMMARY_LVL": "DET", "time": month}, key)
    rows = [r for r in rows if (r.get("CTY_CODE") or "").strip() not in ("-", "") and ib.num(r, "CON_VAL_MO")]
    rows.sort(key=lambda r: -ib.num(r, "CON_VAL_MO"))
    origins = [("-", "TOTAL FOR ALL COUNTRIES"), ("0003", "EUROPEAN UNION")]
    origins += [((r["CTY_CODE"]).strip(), (r["CTY_NAME"] or "").strip()) for r in rows[:n]]
    return origins


def fetch_origin_chunk(cty, start, end, key):
    return ib.api_get(
        {"get": "CTY_NAME,I_COMMODITY,CON_VAL_MO,CAL_DUT_MO,DUT_VAL_MO", "COMM_LVL": "HS2",
         "CTY_CODE": cty, "time": "from %s to %s" % (start, end)}, key,
    ) or []


def rows_from(cty, name, api_rows):
    out = []
    for r in api_rows:
        c = (r.get("I_COMMODITY") or "").strip()
        m = (r.get("time") or "")[:7]
        if len(c) != 2 or not c.isdigit() or len(m) != 7:
            continue
        con, cal, dut = ib.num(r, "CON_VAL_MO"), ib.num(r, "CAL_DUT_MO"), ib.num(r, "DUT_VAL_MO")
        if not con or cal is None or dut is None or dut > con:
            continue
        out.append([m, cty, name, c, round(cal / con, 6), round(cal / dut, 6) if dut else "",
                    round(1 - dut / con, 6), con, cal, dut])
    out.sort(key=lambda x: (x[0], x[3]))
    return out


def write_origin(cty, rows):
    os.makedirs(BY_ORIGIN, exist_ok=True)
    path = os.path.join(BY_ORIGIN, "%s.csv" % ("ALL" if cty == "-" else cty))
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        w.writerows(rows)
    return path


def build(argv):
    n = 60
    for i, a in enumerate(argv):
        if a == "--origins":
            n = int(argv[i + 1])
    key = ib.require_key()
    end = latest_month()
    os.makedirs(FEED, exist_ok=True)
    done = set()
    if os.path.exists(CHECKPOINT):
        done = {json.loads(l)["cty"] for l in open(CHECKPOINT) if l.strip()}
        if done:
            print("checkpoint: %d origins done, resuming." % len(done))
    origins = rank_origins(end, key, n)
    chunks = []
    y = 2010
    while "%d-01" % y <= end:
        chunks.append(("%d-01" % y, min("%d-12" % (y + 3), end)))
        y += 4
    for cty, name in origins:
        if cty in done:
            continue
        rows = []
        for s, e in chunks:
            time.sleep(ib.POLITE_PAUSE)
            rows += rows_from(cty, name, fetch_origin_chunk(cty, s, e, key))
        if len(rows) < 100:
            print("note: %s %s only %d rows — skipped" % (cty, name, len(rows)))
        else:
            write_origin(cty, rows)
        with open(CHECKPOINT, "a") as fh:
            fh.write(json.dumps({"cty": cty, "name": name, "rows": len(rows)}) + "\n")
        print("  %s %-28s %6d rows" % (cty, name[:28], len(rows)))
    manifest = {"built": ib.today_utc(), "through": end, "origins": [{"cty": c, "name": nm} for c, nm in origins],
                "chapters": "all HS2 (01-99)", "columns": COLS,
                "vintage": "current (rebuilt from Census as of the build date); not a first-print ledger",
                "formula": "rate = CAL_DUT_MO / CON_VAL_MO; rate_dutiable = CAL_DUT_MO / DUT_VAL_MO; duty_free_share = 1 - DUT_VAL_MO / CON_VAL_MO"}
    with open(MANIFEST, "w") as fh:
        json.dump(manifest, fh, indent=1)
    if os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)
    print("feed built through %s for %d origins -> %s" % (end, len(origins), BY_ORIGIN))
    return 0


def update():
    key = ib.require_key()
    end = latest_month()
    mani = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else ib.fatal("no manifest — run build first")
    if mani["through"] >= end:
        print("feed already through %s. No-op." % end)
        return 0
    start = ib.month_add(mani["through"], 1)
    for o in mani["origins"]:
        cty, name = o["cty"], o["name"]
        time.sleep(ib.POLITE_PAUSE)
        new = rows_from(cty, name, fetch_origin_chunk(cty, start, end, key))
        path = os.path.join(BY_ORIGIN, "%s.csv" % ("ALL" if cty == "-" else cty))
        with open(path, "a", newline="") as fh:
            csv.writer(fh).writerows(new)
        print("  %s %-28s +%d rows" % (cty, name[:28], len(new)))
    mani["through"], mani["updated"] = end, ib.today_utc()
    with open(MANIFEST, "w") as fh:
        json.dump(mani, fh, indent=1)
    print("feed updated through %s." % end)
    return 0


def pack():
    mani = json.load(open(MANIFEST))
    dist = os.path.join(FEED, "dist")
    os.makedirs(dist, exist_ok=True)
    out = os.path.join(dist, "etrx-feed-%s.zip" % mani["through"])
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(BY_ORIGIN)):
            z.write(os.path.join(BY_ORIGIN, name), "by_origin/%s" % name)
        z.write(MANIFEST, "manifest.json")
        rd = os.path.join(FEED, "README.md")
        if os.path.exists(rd):
            z.write(rd, "README.md")
    print("packed %s (%.1f MB)" % (out, os.path.getsize(out) / 1e6))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd = a[0] if a else "build"
    sys.exit({"build": lambda: build(a[1:]), "update": update, "pack": pack}.get(cmd, lambda: ib.fatal("usage: feed.py build|update|pack"))())
