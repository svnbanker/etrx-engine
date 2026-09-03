#!/usr/bin/env python3
"""ETRX one-shot historical build. Discovers the API's history floor, builds
every month through the SAME fetch/gate/compute path as the live engine,
runs the cross-validation battery, and only then writes prints.jsonl and
publishes. Run once, keep the report, retire the script to history.

Flags:
  --limit-months N   smoke test: build only the first N months, write NOTHING
  --floor YYYY-MM    skip discovery and start here
"""
import json
import os
import subprocess
import sys

import index_build as ib

REPORT = os.path.join(ib.ROOT, "backfill_report.md")
CHECKPOINT = os.path.join(ib.ROOT, "backfill_checkpoint.jsonl")
PROBE_START = "2010-01"
PROBE_CAP = "2016-12"

# Annual reconciliation bands for ETRX-US-INCL (percent, calendar year,
# duties/customs value on total imports for consumption). Centers from the
# USITC AVE table and public effective-rate trackers; full years outside a
# band are FATAL, 2025+ bands are WARN-only (regime still moving).
FATAL_BANDS = {
    2013: (1.15, 1.75), 2014: (1.15, 1.75), 2015: (1.15, 1.75),
    2016: (1.15, 1.75), 2017: (1.15, 1.75), 2018: (1.35, 2.25),
    2019: (2.45, 3.35), 2020: (2.55, 3.45), 2021: (2.45, 3.35),
    2022: (2.45, 3.30), 2023: (2.20, 3.05), 2024: (2.05, 2.90),
}
WARN_BANDS = {2025: (3.5, 13.0), 2026: (5.0, 12.0)}

SPOT_CHECKS = [("2019-06", "ETRX-CN-85"), ("2023-03", "ETRX-US-INCL"),
               ("2025-09", "ETRX-STEEL")]


def git_head():
    try:
        return subprocess.check_output(
            ["git", "-C", ib.ROOT, "rev-parse", "--short", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "no-git"


def discover_floor(key):
    m = PROBE_START
    while m <= PROBE_CAP:
        if ib.probe_month(m, key) is not None:
            print("history floor: %s" % m)
            return m
        m = ib.month_add(m, 1)
    ib.fatal("no data found probing %s..%s — endpoint moved?" % (PROBE_START, PROBE_CAP))


def load_checkpoint():
    done = {}
    if os.path.exists(CHECKPOINT):
        for line in open(CHECKPOINT):
            line = line.strip()
            if line:
                r = json.loads(line)
                done[r["month"]] = (r["vals"], r["src"])
        if done:
            print("checkpoint: %d months already built, resuming." % len(done))
    return done


def build_all(key, floor, limit):
    done = load_checkpoint() if not limit else {}
    months, by_month, srcs = [], {}, {}
    m = floor
    while True:
        if m in done:
            by_month[m], srcs[m] = done[m][0], done[m][1]
            months.append(m)
        else:
            total = ib.probe_month(m, key)
            if total is None:
                break
            raw = ib.fetch_month(m, key, total)
            chap = ib.completeness_gate(raw)
            vals = ib.compute_series(raw, chap)
            ib.validate_series(vals, m, {}, live=False, override_jump=True)
            by_month[m] = vals
            srcs[m] = (raw["total"][0].get("LAST_UPDATE") or "").strip()
            months.append(m)
            if not limit:
                with open(CHECKPOINT, "a") as fh:
                    fh.write(
                        json.dumps({"month": m, "src": srcs[m], "vals": vals}) + "\n"
                    )
        if len(months) % 12 == 0:
            print("built %d months (through %s)" % (len(months), m))
        if limit and len(months) >= limit:
            print("limit reached (%d months) — smoke test only." % limit)
            break
        m = ib.month_add(m, 1)
    if not months:
        ib.fatal("no months built — nothing to do.")
    return months, by_month, srcs


def annual_incl(months, by_month):
    out = {}
    for m in months:
        y = int(m[:4])
        v = next(v for v in by_month[m] if v["series_id"] == "ETRX-US-INCL")
        con, cal, n = out.get(y, (0, 0, 0))
        out[y] = (con + v["con_val"], cal + v["cal_dut"], n + 1)
    return {y: (100.0 * cal / con, n) for y, (con, cal, n) in out.items()}


def rate_of(by_month, month, sid):
    if month not in by_month:
        return None
    return next(
        (v["rate"] for v in by_month[month] if v["series_id"] == sid), None
    )


def battery(months, by_month, key):
    lines, failures = [], []
    lines.append("## Annual reconciliation — ETRX-US-INCL vs external references\n")
    lines.append("| year | months | index (%) | band (%) | verdict |")
    lines.append("|---|---|---|---|---|")
    for y, (rate, n) in sorted(annual_incl(months, by_month).items()):
        band = FATAL_BANDS.get(y) or WARN_BANDS.get(y)
        if band is None:
            verdict = "no band"
        elif n < 12:
            verdict = "partial year — informational"
        elif band[0] <= rate <= band[1]:
            verdict = "PASS"
        elif y in FATAL_BANDS:
            verdict = "FAIL"
            failures.append("annual %d: %.2f%% outside (%.2f, %.2f)" % (y, rate, *band))
        else:
            verdict = "WARN (2025+ band is advisory)"
        b = "(%.2f, %.2f)" % band if band else "—"
        lines.append("| %d | %d | %.2f | %s | %s |" % (y, n, rate, b, verdict))

    lines.append("\n## Regime checks\n")
    checks = []
    a, b = rate_of(by_month, "2018-01", "ETRX-CN-85"), rate_of(by_month, "2019-12", "ETRX-CN-85")
    if a is not None and b is not None:
        ok = (b - a) >= 0.05
        checks.append(("China-85 trade-war step-up 2018-01 → 2019-12 ≥ 5pp",
                       "%.2f%% → %.2f%%" % (100 * a, 100 * b), ok))
    peak_cn = max((rate_of(by_month, m, "ETRX-CN-85") or 0)
                  for m in months if m.startswith("2025")) if any(
        m.startswith("2025") for m in months) else None
    if peak_cn is not None:
        checks.append(("China-85 2025 peak ≥ 15%", "%.1f%%" % (100 * peak_cn),
                       peak_cn >= 0.15))
    peak_us = max((rate_of(by_month, m, "ETRX-US-INCL") or 0)
                  for m in months if m.startswith("2025")) if any(
        m.startswith("2025") for m in months) else None
    if peak_us is not None:
        checks.append(("Headline-incl 2025 peak ≥ 5%", "%.1f%%" % (100 * peak_us),
                       peak_us >= 0.05))
    for name, val, ok in checks:
        lines.append("- %s: %s — %s" % (name, val, "PASS" if ok else "FAIL"))
        if not ok:
            failures.append("regime check failed: %s (%s)" % (name, val))

    lines.append("\n## Parity re-compute (same code path, second fetch)\n")
    picks = [months[0], months[len(months) // 2], months[-1]]
    for m in picks:
        raw = ib.fetch_month(m, key)
        chap = ib.completeness_gate(raw)
        vals2 = {v["series_id"]: v for v in ib.compute_series(raw, chap)}
        diff = [
            v["series_id"]
            for v in by_month[m]
            if vals2.get(v["series_id"]) != v
        ]
        lines.append("- %s: %s" % (m, "exact match" if not diff else
                                   "MISMATCH in %s" % ",".join(diff)))
        if diff:
            failures.append("parity mismatch %s: %s" % (m, ",".join(diff)))

    lines.append("\n## Plausibility warns (rate above %.0f%%)\n" % (100 * ib.RATE_WARN))
    warned = [
        "- %s %s: %.1f%%" % (m, v["series_id"], 100 * v["rate"])
        for m in months for v in by_month[m] if v["rate"] > ib.RATE_WARN
    ]
    lines.extend(warned or ["- none"])

    lines.append("\n## Manual spot-checks (record results in AUDIT.md)\n")
    lines.append("Pull each cell in USITC DataWeb (imports for consumption, "
                 "customs value + calculated duty) and compare:\n")
    for m, sid in SPOT_CHECKS:
        v = next((v for v in by_month.get(m, []) if v["series_id"] == sid), None)
        if v:
            lines.append(
                "- %s %s: customs %d, duty %d, rate %.2f%%"
                % (m, sid, v["con_val"], v["cal_dut"], 100 * v["rate"])
            )
    return lines, failures


def main(argv):
    limit = 0
    floor = None
    for a in argv:
        if a.startswith("--limit-months"):
            limit = int(a.split("=", 1)[1]) if "=" in a else 3
        if a.startswith("--floor="):
            floor = a.split("=", 1)[1]
    if os.path.exists(ib.LEDGER) and os.path.getsize(ib.LEDGER) > 0:
        ib.fatal(
            "prints.jsonl already exists — backfill is one-shot. "
            "Move the ledger aside deliberately first (see RUNBOOK.md)."
        )
    key = ib.require_key()
    floor = floor or discover_floor(key)
    months, by_month, srcs = build_all(key, floor, limit)
    if limit:
        for m in months:
            ib.print_table(by_month[m], m)
        print("smoke test only — no battery, no ledger, no publish.")
        return 0
    lines, failures = battery(months, by_month, key)
    head = [
        "# ETRX backfill report",
        "",
        "- run date: %s (UTC)" % ib.today_utc(),
        "- code: %s" % git_head(),
        "- history floor: %s; months built: %d (%s → %s)"
        % (floor, len(months), months[0], months[-1]),
        "- battery verdict: %s" % ("PASS" if not failures else
                                   "FAIL — %d problem(s)" % len(failures)),
        "",
    ]
    report = "\n".join(head + lines) + "\n"
    with open(REPORT, "w") as fh:
        fh.write(report)
    print("report written: %s" % REPORT)
    if failures:
        for f in failures:
            print("BATTERY: %s" % f)
        ib.fatal(
            "cross-validation battery failed (%d problems). "
            "No ledger write, no publish — read backfill_report.md." % len(failures)
        )
    rows = []
    for m in months:
        rows.extend(ib.make_rows(by_month[m], m, True, "backfill", srcs[m]))
    ib.append_prints(rows, dry_run=False)
    ib.publish(ib.read_prints(), dry_run=False)
    if os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)
    print("backfill complete: %d months, %d ledger rows." % (len(months), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
