#!/usr/bin/env python3
"""ETRX - US Effective Tariff Rate Index. Monthly print engine.

Order of operations is doctrine: fetch -> completeness gate -> compute ->
validate -> publish -> ledger-append LAST. The first print of a
(data_month, series_id) is the settlement value and is never restated;
later differences are appended to prints.jsonl as revision vintages.

Flags: --dry-run  --override-jump  --revsweep  --month=YYYY-MM  --selftest
See RULEBOOK.md for methodology, RUNBOOK.md for operations.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
API = "https://api.census.gov/data/timeseries/intltrade/imports/hs"
LEDGER = os.path.join(ROOT, "prints.jsonl")
DATA_DIR = os.path.join(ROOT, "data")
DOCS_DIR = os.path.join(ROOT, "docs")

FLOOR_MONTH = "2013-01"     # guaranteed API coverage; backfill probes for earlier
REVISION_LOOKBACK = 3       # settled months re-checked whenever a new month prints
CHECKSUM_TOL_VAL = 0.005    # chapter-scan sum vs grand-total row, customs value
CHECKSUM_TOL_DUT = 0.010    # same check on calculated duty (coarser rounding)
RATE_HARD_MAX = 1.75        # above any statutory regime ever in force
RATE_WARN = 0.60            # plausible but flagged for human review
MOM_JUMP_FATAL = 0.10       # live prints only; bypass with --override-jump
MIN_SCAN_CHAPTERS = 90      # of ~97 commercial HS2 chapters
POLITE_PAUSE = 0.35         # seconds between API calls

# Cell series: one API call per (country, chapter); the gate expects exactly 1 row.
# (series_id, CTY_CODE, HS2 chapter, label)
COUNTRY_CELLS = [
    ("ETRX-CN-85", "5700", "85", "China — electronics (HS 85)"),
    ("ETRX-CN-84", "5700", "84", "China — machinery (HS 84)"),
    ("ETRX-CN-95", "5700", "95", "China — toys (HS 95)"),
    ("ETRX-EU-87", "0003", "87", "European Union — vehicles (HS 87)"),
    ("ETRX-MX-87", "2010", "87", "Mexico — vehicles (HS 87)"),
    ("ETRX-CA-76", "1220", "76", "Canada — aluminum (HS 76)"),
    ("ETRX-CA-44", "1220", "44", "Canada — wood (HS 44)"),
    ("ETRX-CA-87", "1220", "87", "Canada — vehicles (HS 87)"),
]

# Scan series: computed from the all-countries HS2 chapter scan (CTY_CODE='-').
# chapters=None means all commercial chapters 01-97; "ALL" includes 98/99.
SCAN_SERIES = [
    ("ETRX-US", None, "United States — all imports ex 98/99 (headline)"),
    ("ETRX-US-INCL", "ALL", "United States — all imports incl 98/99 (companion)"),
    ("ETRX-STEEL", ["72", "73"], "Steel — all origins (HS 72+73)"),
    ("ETRX-PHARMA", ["30"], "Pharmaceuticals — all origins (HS 30)"),
    ("ETRX-APPAREL", ["61", "62"], "Apparel — all origins (HS 61+62)"),
]
REQUIRED_CHAPTERS = {"30", "61", "62", "72", "73"}
SERIES_LABELS = dict(
    [(sid, lab) for sid, _c, _ch, lab in COUNTRY_CELLS]
    + [(sid, lab) for sid, _ch, lab in SCAN_SERIES]
)
SERIES_ORDER = [sid for sid, _ch, _l in SCAN_SERIES] + [
    sid for sid, _c, _ch, _l in COUNTRY_CELLS
]

# FT-900 release schedule (8:30 ET), from census.gov/foreign-trade/reference/
# release_schedule.html. Refresh annually - RUNBOOK "Schedule refresh".
FT900_SCHEDULE = [
    ("2026-09-03", "2026-07"),
    ("2026-10-06", "2026-08"),
    ("2026-11-04", "2026-09"),
    ("2026-12-08", "2026-10"),
]


def fatal(msg):
    print("FATAL: %s" % msg)
    sys.exit(1)


def today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def month_add(m, n):
    y, mo = int(m[:4]), int(m[5:7])
    t = y * 12 + (mo - 1) + n
    return "%04d-%02d" % (t // 12, t % 12 + 1)


def load_env():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def require_key():
    load_env()
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        fatal(
            "CENSUS_API_KEY is not set (env or .env). Refusing to run — "
            "no index, no state write, no publish."
        )
    return key


_SESSION = requests.Session()


def api_get(params, key, retries=5):
    """One Census API call. Returns list of row dicts, or None on HTTP 204
    (month not published). Key problems arrive as a 302 redirect to an HTML
    page with the X-DataWebAPI-KeyError header, so redirects must stay off.
    Retries ride out multi-minute Census flakiness observed under sustained
    load (2026-08-23 backfill timeout streak — see AUDIT.md)."""
    q = dict(params)
    q["key"] = key
    last = "no attempt"
    for attempt in range(retries):
        try:
            r = _SESSION.get(API, params=q, timeout=60, allow_redirects=False)
        except requests.RequestException as e:
            # Read-timeouts under sustained load are Census throttling by
            # stalling, not outage — back off in minutes, not seconds
            # (two backfills died ~70 months in; see AUDIT 2026-08-23).
            last = "request error: %s" % e
            time.sleep(min(300, 15 * 4**attempt))
            continue
        if r.status_code in (301, 302) or r.headers.get("X-DataWebAPI-KeyError"):
            fatal(
                "Census API rejected the key (302/X-DataWebAPI-KeyError). "
                "CENSUS_API_KEY is missing, invalid, or not yet activated. "
                "No index, no state write, no publish."
            )
        if r.status_code == 204:
            return None
        if r.status_code == 200:
            try:
                data = r.json()
            except ValueError:
                fatal(
                    "Census API returned 200 with a non-JSON body "
                    "(starts %r). No index, no state write, no publish."
                    % r.text[:120]
                )
            if not data or len(data) < 2:
                return []
            hdr = data[0]
            return [dict(zip(hdr, row)) for row in data[1:]]
        if 500 <= r.status_code < 600:
            last = "HTTP %d" % r.status_code
            time.sleep(min(45, 2 * 2**attempt))
            continue
        fatal(
            "Census API HTTP %d: %s. No index, no state write, no publish."
            % (r.status_code, r.text[:200])
        )
    fatal(
        "Census API unreachable after %d tries (last: %s). "
        "No index, no state write, no publish." % (retries, last)
    )


def num(row, field):
    v = row.get(field)
    if v is None:
        return None
    v = str(v).strip()
    if v in ("", "-", "null", "None"):
        return None
    try:
        return int(v)
    except ValueError:
        try:
            return int(float(v))
        except ValueError:
            return None


def probe_month(month, key):
    """Grand-total row for the month, or None if Census has not published it."""
    return api_get(
        {
            "get": "CTY_NAME,CON_VAL_MO,CAL_DUT_MO,DUT_VAL_MO,LAST_UPDATE",
            "CTY_CODE": "-",
            "time": month,
        },
        key,
    )


def fetch_month(month, key, total=None):
    """~10 small calls, each mapping 1:1 to a completeness-gate cell."""
    if total is None:
        total = probe_month(month, key)
        if total is None:
            fatal("fetch_month called for %s but Census has no data for it." % month)
    time.sleep(POLITE_PAUSE)
    scan = api_get(
        {
            "get": "I_COMMODITY,CON_VAL_MO,CAL_DUT_MO,DUT_VAL_MO",
            "COMM_LVL": "HS2",
            "CTY_CODE": "-",
            "time": month,
        },
        key,
    )
    cells = {}
    for sid, cty, ch, _label in COUNTRY_CELLS:
        time.sleep(POLITE_PAUSE)
        cells[sid] = api_get(
            {
                "get": "CTY_NAME,I_COMMODITY,CON_VAL_MO,CAL_DUT_MO,DUT_VAL_MO",
                "COMM_LVL": "HS2",
                "CTY_CODE": cty,
                "I_COMMODITY": ch,
                "time": month,
            },
            key,
        )
    return {"month": month, "scan": scan, "total": total, "cells": cells}


def gate_problems(raw):
    """Returns (problems, clean_chapter_dict). Pure so the selftest can call it."""
    problems = []
    notes = []
    chap = {}
    dropped = 0
    for r in raw.get("scan") or []:
        c = (r.get("I_COMMODITY") or "").strip()
        if len(c) == 2 and c.isdigit():
            if c in chap:
                problems.append("duplicate chapter-scan row for chapter %s" % c)
            chap[c] = r
        else:
            dropped += 1
    if dropped:
        notes.append("%d non-chapter rows dropped from scan" % dropped)
    if len(chap) < MIN_SCAN_CHAPTERS:
        problems.append(
            "chapter scan has %d chapters (< %d required)"
            % (len(chap), MIN_SCAN_CHAPTERS)
        )
    excluded = sorted(
        c
        for c, r in chap.items()
        if None
        in (num(r, "CON_VAL_MO"), num(r, "CAL_DUT_MO"), num(r, "DUT_VAL_MO"))
    )
    if excluded:
        notes.append(
            "%d chapters with missing values excluded loudly: %s"
            % (len(excluded), ",".join(excluded))
        )
    for c in sorted(REQUIRED_CHAPTERS):
        r = chap.get(c)
        if r is None:
            problems.append("required chapter %s missing from scan" % c)
        elif c in excluded or (num(r, "CON_VAL_MO") or 0) <= 0:
            problems.append("required chapter %s has missing or zero values" % c)
    total = raw.get("total")
    if not total or len(total) != 1:
        problems.append(
            "grand-total row: expected exactly 1, got %d" % len(total or [])
        )
    else:
        t = total[0]
        tv, td = num(t, "CON_VAL_MO"), num(t, "CAL_DUT_MO")
        if not tv or td is None:
            problems.append("grand-total row has missing values")
        else:
            good = [c for c in chap if c not in excluded]
            sv = sum(num(chap[c], "CON_VAL_MO") for c in good)
            sd = sum(num(chap[c], "CAL_DUT_MO") for c in good)
            if abs(sv - tv) / tv > CHECKSUM_TOL_VAL:
                problems.append(
                    "checksum: scan customs value %d vs total %d (off %.2f%%)"
                    % (sv, tv, 100.0 * abs(sv - tv) / tv)
                )
            if td > 0 and abs(sd - td) / td > CHECKSUM_TOL_DUT:
                problems.append(
                    "checksum: scan calculated duty %d vs total %d (off %.2f%%)"
                    % (sd, td, 100.0 * abs(sd - td) / td)
                )
    for sid, _cty, ch, _label in COUNTRY_CELLS:
        rows = (raw.get("cells") or {}).get(sid)
        if not rows:
            problems.append("%s cell returned no data" % sid)
            continue
        if len(rows) != 1:
            problems.append(
                "%s expected exactly 1 row, got %d (RP dimension split? "
                "see AUDIT.md day-one checks)" % (sid, len(rows))
            )
            continue
        r = rows[0]
        if (r.get("I_COMMODITY") or "").strip() != ch:
            problems.append(
                "%s wrong chapter %r" % (sid, r.get("I_COMMODITY"))
            )
            continue
        cv, cd, dv = num(r, "CON_VAL_MO"), num(r, "CAL_DUT_MO"), num(r, "DUT_VAL_MO")
        if not cv or cd is None or dv is None:
            problems.append("%s has missing or zero values" % sid)
        elif dv > cv:
            problems.append("%s dutiable value exceeds customs value" % sid)
    for n in notes:
        print("note: %s" % n)
    return problems, chap


def completeness_gate(raw):
    problems, chap = gate_problems(raw)
    if problems:
        for p in problems:
            print("GATE: %s" % p)
        fatal(
            "completeness gate failed for %s (%d problems). "
            "No index, no state write, no publish." % (raw.get("month"), len(problems))
        )
    return chap


def _sums(rows):
    con = sum(num(r, "CON_VAL_MO") or 0 for r in rows)
    cal = sum(num(r, "CAL_DUT_MO") or 0 for r in rows)
    dut = sum(num(r, "DUT_VAL_MO") or 0 for r in rows)
    return con, cal, dut


def _series_val(sid, con, cal, dut):
    if con <= 0:
        fatal("%s has zero customs value — cannot compute a rate." % sid)
    return {
        "series_id": sid,
        "rate": round(cal / con, 6),
        "rate_dutiable": round(cal / dut, 6) if dut > 0 else None,
        "duty_free_share": round(1.0 - dut / con, 6),
        "con_val": con,
        "cal_dut": cal,
        "dut_val": dut,
    }


def compute_series(raw, chap):
    good = {
        c: r
        for c, r in chap.items()
        if None
        not in (num(r, "CON_VAL_MO"), num(r, "CAL_DUT_MO"), num(r, "DUT_VAL_MO"))
    }
    vals = []
    for sid, chapters, _label in SCAN_SERIES:
        if chapters is None:
            rows = [r for c, r in good.items() if c not in ("98", "99")]
        elif chapters == "ALL":
            rows = list(good.values())
        else:
            missing = [c for c in chapters if c not in good]
            if missing:
                fatal("%s requires chapters %s — absent." % (sid, ",".join(missing)))
            rows = [good[c] for c in chapters]
        vals.append(_series_val(sid, *_sums(rows)))
    for sid, _cty, _ch, _label in COUNTRY_CELLS:
        vals.append(_series_val(sid, *_sums(raw["cells"][sid])))
    return vals


def jump_exceeded(prev_rate, cur_rate):
    return prev_rate is not None and abs(cur_rate - prev_rate) > MOM_JUMP_FATAL


def validate_series(vals, month, prior_rates, live, override_jump):
    for v in vals:
        if v["rate"] < 0 or v["rate"] > RATE_HARD_MAX:
            fatal(
                "%s %s rate %.2f%% outside hard bounds [0, %.0f%%]."
                % (v["series_id"], month, 100 * v["rate"], 100 * RATE_HARD_MAX)
            )
        if v["rate"] > RATE_WARN:
            print(
                "WARN: %s %s rate %.1f%% above the plausibility corridor — "
                "review by hand." % (v["series_id"], month, 100 * v["rate"])
            )
        rd = v["rate_dutiable"]
        if rd is not None and (rd < 0 or rd > RATE_HARD_MAX):
            fatal(
                "%s %s dutiable-value rate %.2f%% outside hard bounds."
                % (v["series_id"], month, 100 * rd)
            )
    if live:
        for v in vals:
            p = prior_rates.get(v["series_id"])
            if jump_exceeded(p, v["rate"]) and not override_jump:
                fatal(
                    "%s moved %.1fpp month-over-month (%.2f%% -> %.2f%%) for %s. "
                    "Verify against the release by hand; rerun with "
                    "--override-jump if the move is real."
                    % (
                        v["series_id"],
                        100 * abs(v["rate"] - p),
                        100 * p,
                        100 * v["rate"],
                        month,
                    )
                )


def read_prints():
    if not os.path.exists(LEDGER):
        return []
    rows = []
    for i, line in enumerate(open(LEDGER)):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            fatal("prints.jsonl line %d is not valid JSON — repair by hand." % (i + 1))
    return rows


def first_prints(prints):
    out = {}
    for r in prints:
        if r.get("first_print"):
            out[(r["data_month"], r["series_id"])] = r
    return out


def latest_vintages(prints):
    out = {}
    for r in prints:  # file order breaks vintage_date ties: later line wins
        out[(r["data_month"], r["series_id"])] = r
    return out


def settled_months(prints):
    return sorted({m for (m, _s) in first_prints(prints)})


def make_rows(vals, month, first, note, source_update):
    stamp = today_utc()
    rows = []
    for v in vals:
        r = dict(v)
        r.update(
            {
                "data_month": month,
                "vintage_date": stamp,
                "first_print": first,
                "vintage_note": note,
                "source_last_update": source_update,
            }
        )
        rows.append(r)
    return rows


def append_prints(rows, dry_run):
    if dry_run:
        print("dry-run: %d ledger rows NOT appended." % len(rows))
        return
    seen = set(
        (r["data_month"], r["series_id"], r["vintage_date"]) for r in read_prints()
    )
    n = 0
    with open(LEDGER, "a") as fh:
        for r in rows:
            k = (r["data_month"], r["series_id"], r["vintage_date"])
            if k in seen:
                continue
            fh.write(json.dumps(r, sort_keys=True) + "\n")
            seen.add(k)
            n += 1
    print("ledger: %d rows appended." % n)


def build_month(month, key, prior_rates, override_jump, total=None):
    raw = fetch_month(month, key, total)
    chap = completeness_gate(raw)
    vals = compute_series(raw, chap)
    validate_series(vals, month, prior_rates, live=True, override_jump=override_jump)
    src = (raw["total"][0].get("LAST_UPDATE") or "").strip()
    return vals, src


def detect_revisions(key, prints, months):
    """Refetch settled months; changed raw values become revision vintages."""
    latest = latest_vintages(prints)
    rev = []
    for month in months:
        raw = fetch_month(month, key)
        chap = completeness_gate(raw)
        vals = compute_series(raw, chap)
        validate_series(vals, month, {}, live=False, override_jump=True)
        src = (raw["total"][0].get("LAST_UPDATE") or "").strip()
        changed = []
        for v in vals:
            cur = latest.get((month, v["series_id"]))
            if cur is None:
                continue
            if (
                cur["con_val"] != v["con_val"]
                or cur["cal_dut"] != v["cal_dut"]
                or cur["dut_val"] != v["dut_val"]
            ):
                changed.append(v)
        if changed:
            print(
                "revision: %s — %d series changed vs last vintage."
                % (month, len(changed))
            )
            rev.extend(make_rows(changed, month, False, "revision", src))
    return rev


CSV_COLS = [
    "data_month",
    "series_id",
    "rate",
    "rate_dutiable",
    "duty_free_share",
    "con_val",
    "cal_dut",
    "dut_val",
    "vintage_date",
    "vintage_note",
]


def _csv(rows):
    lines = [",".join(CSV_COLS)]
    for r in rows:
        lines.append(
            ",".join("" if r.get(c) is None else str(r.get(c)) for c in CSV_COLS)
        )
    return "\n".join(lines) + "\n"


def next_print_info():
    today = today_utc()
    for release, dmonth in FT900_SCHEDULE:
        if release >= today:
            return {"release": release, "data_month": dmonth}
    return {
        "release": "TBD",
        "data_month": "TBD (refresh FT900_SCHEDULE — RUNBOOK 'Schedule refresh')",
    }


def build_latest_json(prints):
    fp = first_prints(prints)
    months = settled_months(prints)
    if not months:
        fatal("no settled months in the ledger — nothing to publish.")
    cur = months[-1]
    prior = months[-2] if len(months) > 1 else None
    series = []
    for sid in SERIES_ORDER:
        r = fp.get((cur, sid))
        if r is None:
            continue
        p = fp.get((prior, sid)) if prior else None
        series.append(
            {
                "id": sid,
                "label": SERIES_LABELS[sid],
                "rate": r["rate"],
                "prior_rate": p["rate"] if p else None,
                "delta_bps": round((r["rate"] - p["rate"]) * 10000) if p else None,
                "rate_dutiable": r["rate_dutiable"],
                "duty_free_share": r["duty_free_share"],
                "first_print_vintage": r["vintage_date"],
                "vintage_note": r["vintage_note"],
            }
        )
    return {
        "index": "ETRX",
        "name": "US Effective Tariff Rate Index",
        "data_month": cur,
        "generated": today_utc(),
        "next_print": next_print_info(),
        "series": series,
        "settlement": "first print settles; revisions are logged, never restated",
        "source": "US Census Bureau, International Trade API (imports for consumption)",
        "rulebook": "RULEBOOK.md",
        "disclaimer": "Research and commentary. Not investment advice.",
    }


def render_pngs(charts_dir):
    """SVG -> PNG via rsvg-convert when available (CI installs librsvg2-bin;
    locally `brew install librsvg`). Charts stay downloadable as SVG regardless."""
    import shutil
    import subprocess

    tool = shutil.which("rsvg-convert")
    if not tool:
        print("note: rsvg-convert not found — PNG charts skipped (SVG published).")
        return 0
    n = 0
    for name in sorted(os.listdir(charts_dir)):
        if name.endswith(".svg"):
            src = os.path.join(charts_dir, name)
            dst = src[:-4] + ".png"
            subprocess.run([tool, "-w", "1600", src, "-o", dst], check=True)
            n += 1
    return n


def publish(prints, dry_run):
    import site_build

    fp_rows = sorted(
        (r for r in prints if r.get("first_print")),
        key=lambda r: (r["data_month"], r["series_id"]),
    )
    rev_rows = sorted(
        (r for r in prints if not r.get("first_print")),
        key=lambda r: (r["vintage_date"], r["data_month"], r["series_id"]),
    )
    panel_csv = _csv(fp_rows)
    rev_csv = _csv(rev_rows)
    latest = build_latest_json(prints)
    history = {}
    for r in fp_rows:
        history.setdefault(r["series_id"], []).append((r["data_month"], r["rate"]))
    raw_latest = {r["series_id"]: r for r in fp_rows if r["data_month"] == latest["data_month"]}
    rb_path = os.path.join(ROOT, "RULEBOOK.md")
    rulebook = open(rb_path).read() if os.path.exists(rb_path) else ""
    pages = site_build.render_all(latest, history, rev_rows, FT900_SCHEDULE, rulebook, raw_latest)
    latest_json = json.dumps(latest, indent=1, sort_keys=True)
    artifacts = [
        (os.path.join(DATA_DIR, "etrx.csv"), panel_csv),
        (os.path.join(DATA_DIR, "revisions.csv"), rev_csv),
        (os.path.join(DOCS_DIR, "etrx.csv"), panel_csv),
        (os.path.join(DOCS_DIR, "revisions.csv"), rev_csv),
        (os.path.join(DOCS_DIR, "latest.json"), latest_json),
        (os.path.join(DOCS_DIR, "RULEBOOK.md"), rulebook),
    ] + [(os.path.join(DOCS_DIR, rel), content) for rel, content in sorted(pages.items())]
    if dry_run:
        import hashlib

        for path, content in artifacts:
            digest = hashlib.md5(content.encode()).hexdigest()[:10]
            print(
                "dry-run: %s NOT written (md5 %s, %d bytes)"
                % (os.path.relpath(path, ROOT), digest, len(content))
            )
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    for path, content in artifacts:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)
    pngs = render_pngs(os.path.join(DOCS_DIR, "charts"))
    try:  # chiffres vérifiés — pour que personne n'en cite un de mémoire
        import figures
        figures.main()
    except Exception as e:
        print("note: KEY-FIGURES non régénéré (%s)" % e)
    print(
        "published %d artifacts + %d PNG charts (latest data month %s)."
        % (len(artifacts), pngs, latest["data_month"])
    )


def print_table(vals, month):
    print("%s  %-14s %9s %10s %9s" % (month, "series", "rate", "dutiable", "dutyfree"))
    for v in vals:
        rd = "-" if v["rate_dutiable"] is None else "%8.2f%%" % (100 * v["rate_dutiable"])
        print(
            "        %-14s %8.2f%% %10s %8.1f%%"
            % (v["series_id"], 100 * v["rate"], rd, 100 * v["duty_free_share"])
        )


def selftest():
    scan = []
    for i in range(1, 98):
        scan.append(
            {
                "I_COMMODITY": "%02d" % i,
                "CON_VAL_MO": "1000",
                "CAL_DUT_MO": "20",
                "DUT_VAL_MO": "800",
            }
        )
    scan.append(
        {"I_COMMODITY": "98", "CON_VAL_MO": "50", "CAL_DUT_MO": "0", "DUT_VAL_MO": "0"}
    )
    total = [
        {
            "CTY_NAME": "TOTAL FOR ALL COUNTRIES",
            "CON_VAL_MO": "97050",
            "CAL_DUT_MO": "1940",
            "DUT_VAL_MO": "77600",
            "LAST_UPDATE": "fixture",
        }
    ]
    cells = {}
    for sid, _cty, ch, _label in COUNTRY_CELLS:
        cells[sid] = [
            {
                "CTY_NAME": "X",
                "I_COMMODITY": ch,
                "CON_VAL_MO": "2000",
                "CAL_DUT_MO": "500",
                "DUT_VAL_MO": "1900",
            }
        ]
    raw = {"month": "2026-01", "scan": scan, "total": total, "cells": cells}
    problems, chap = gate_problems(raw)
    assert problems == [], "gate should pass on the good fixture: %s" % problems
    vals = {v["series_id"]: v for v in compute_series(raw, chap)}
    assert vals["ETRX-US"]["rate"] == 0.02, vals["ETRX-US"]
    assert vals["ETRX-US"]["duty_free_share"] == 0.2, vals["ETRX-US"]
    assert vals["ETRX-US-INCL"]["rate"] == round(1940 / 97050.0, 6)
    assert vals["ETRX-STEEL"]["rate"] == 0.02
    assert vals["ETRX-APPAREL"]["con_val"] == 2000
    assert vals["ETRX-CN-85"]["rate"] == 0.25
    assert vals["ETRX-CN-85"]["rate_dutiable"] == round(500 / 1900.0, 6)
    assert vals["ETRX-CN-85"]["duty_free_share"] == 0.05
    validate_series(list(vals.values()), "2026-01", {}, live=False, override_jump=False)
    bad = {
        "month": "2026-01",
        "scan": [r for r in scan if r["I_COMMODITY"] != "72"],
        "total": total,
        "cells": cells,
    }
    problems, _bad_chap = gate_problems(bad)
    assert any("72" in p for p in problems), "gate must catch a missing required chapter"
    two = {
        "month": "2026-01",
        "scan": scan,
        "total": total,
        "cells": dict(cells, **{"ETRX-CN-85": cells["ETRX-CN-85"] * 2}),
    }
    problems, _two_chap = gate_problems(two)
    assert any("exactly 1 row" in p for p in problems), "gate must catch RP splits"
    assert jump_exceeded(0.02, 0.15) and not jump_exceeded(0.02, 0.05)
    assert month_add("2026-12", 1) == "2027-01" and month_add("2026-01", -1) == "2025-12"
    print("selftest: PASS (gate, compute, validate, jump, month arithmetic)")


def main(argv):
    flags = set(a for a in argv if not a.startswith("--month="))
    force_month = None
    for a in argv:
        if a.startswith("--month="):
            force_month = a.split("=", 1)[1]
    dry_run = "--dry-run" in flags
    override_jump = "--override-jump" in flags
    if "--selftest" in flags:
        selftest()
        return 0
    key = require_key()
    prints = read_prints()
    if not prints:
        fatal("prints.jsonl is empty — run backfill.py first (see RUNBOOK.md).")
    if force_month:
        vals, _src = build_month(force_month, key, {}, override_jump=True)
        print_table(vals, force_month)
        print("--month is an inspection tool: nothing was written.")
        return 0
    months = settled_months(prints)
    if "--revsweep" in flags:
        print("revsweep: re-checking all %d settled months." % len(months))
        rev = detect_revisions(key, prints, months)
        if not rev:
            print("revsweep: no revisions found. No-op.")
            return 0
        publish(prints + rev, dry_run)
        append_prints(rev, dry_run)
        return 0
    fp = first_prints(prints)
    prior_rates = {}
    last = months[-1]
    for sid in SERIES_ORDER:
        r = fp.get((last, sid))
        if r:
            prior_rates[sid] = r["rate"]
    new_rows = []
    built = []
    cand = month_add(last, 1)
    while True:
        total = probe_month(cand, key)
        if total is None:
            break
        print("new data month available: %s — building." % cand)
        vals, src = build_month(cand, key, prior_rates, override_jump, total)
        print_table(vals, cand)
        new_rows.extend(make_rows(vals, cand, True, "live", src))
        prior_rates = {v["series_id"]: v["rate"] for v in vals}
        built.append(cand)
        cand = month_add(cand, 1)
    if not built:
        print("No new data month (latest settled: %s). No-op." % last)
        return 0
    check = [m for m in months[-REVISION_LOOKBACK:] if m not in built]
    rev_rows = detect_revisions(key, prints, check)
    publish(prints + new_rows + rev_rows, dry_run)
    append_prints(new_rows + rev_rows, dry_run)
    print(
        "printed %s; %d revision rows logged." % (", ".join(built), len(rev_rows))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
