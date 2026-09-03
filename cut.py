#!/usr/bin/env python3
"""ETRX custom cut: any origin × HS chapter (or HS4 heading) as a monthly
effective-rate series, with CSV, JSON and a credited chart. Same formula and
source as the index; NOT a settlement series (no first-print ledger).

  uv run python cut.py --cty 5520 --chapter 85                 Vietnam electronics
  uv run python cut.py --cty - --chapter 44 --hs4 4407         all origins, softwood lumber
  uv run python cut.py --cty 5880 --chapter 87 --from 2015-01 --name japan-vehicles
  uv run python cut.py --list-countries

One API call per cut (time range). Outputs land in cuts/<name>.{csv,json,svg,png}."""
import json
import os
import sys

import index_build as ib
import site_build as sb

CUTS = os.path.join(ib.ROOT, "cuts")

# Census Schedule C codes for frequent requests. Names are validated against the
# API's CTY_NAME at fetch time — a mismatch is fatal, never silently accepted.
COUNTRIES = {
    "-": "TOTAL FOR ALL COUNTRIES", "0003": "EUROPEAN UNION",
    "1220": "CANADA", "2010": "MEXICO", "3510": "BRAZIL", "4120": "UNITED KINGDOM",
    "4190": "IRELAND", "4210": "NETHERLANDS", "4231": "BELGIUM", "4279": "FRANCE",
    "4280": "GERMANY", "4419": "SWITZERLAND", "4700": "SPAIN", "4759": "ITALY",
    "5330": "INDIA", "5380": "BANGLADESH", "5490": "THAILAND", "5520": "VIETNAM",
    "5550": "CAMBODIA", "5570": "MALAYSIA", "5590": "SINGAPORE", "5600": "INDONESIA",
    "5650": "PHILIPPINES", "5700": "CHINA", "5800": "KOREA, SOUTH", "5830": "TAIWAN",
    "5880": "JAPAN", "6021": "AUSTRALIA",
}


def fetch_range(cty, comm, lvl, start, end, key):
    return ib.api_get(
        {
            "get": "CTY_NAME,I_COMMODITY,I_COMMODITY_SDESC,CON_VAL_MO,CAL_DUT_MO,DUT_VAL_MO",
            "COMM_LVL": lvl, "CTY_CODE": cty, "I_COMMODITY": comm,
            "time": "from %s to %s" % (start, end),
        },
        key,
    )


def main(argv):
    if "--list-countries" in argv:
        for code, name in sorted(COUNTRIES.items(), key=lambda kv: kv[1]):
            print("%s  %s" % (code, name))
        return 0
    opts = {"--cty": None, "--chapter": None, "--hs4": None, "--from": "2010-01",
            "--to": None, "--name": None}
    for i, a in enumerate(argv):
        if a in opts and i + 1 < len(argv):
            opts[a] = argv[i + 1]
    if not opts["--cty"] or not opts["--chapter"]:
        ib.fatal("usage: cut.py --cty <code|-> --chapter <HS2> [--hs4 <HS4>] [--from YYYY-MM] [--to YYYY-MM] [--name slug]")
    key = ib.require_key()
    cty, ch, hs4 = opts["--cty"], opts["--chapter"], opts["--hs4"]
    # --hs4 accepts any 4/6/10-digit HTS code; level inferred from length.
    comm = hs4 or ch
    lvl = {2: "HS2", 4: "HS4", 6: "HS6", 10: "HS10"}.get(len(comm))
    if not lvl:
        ib.fatal("HS code must be 2, 4, 6 or 10 digits, got %r" % comm)
    end = opts["--to"]
    if not end:
        months = ib.settled_months(ib.read_prints())
        end = months[-1] if months else "2026-06"
    rows = fetch_range(cty, comm, lvl, opts["--from"], end, key)
    if not rows:
        ib.fatal("no rows returned for %s / %s in %s..%s" % (cty, comm, opts["--from"], end))
    expect = COUNTRIES.get(cty)
    got = (rows[0].get("CTY_NAME") or "").strip().upper()
    if expect and expect not in got:
        ib.fatal("country code %s returned %r, expected %r — refusing to publish a mislabeled cut." % (cty, got, expect))
    rows.sort(key=lambda r: r.get("time", ""))
    series = []
    for r in rows:
        m = (r.get("time") or "")[:7]
        con, cal, dut = ib.num(r, "CON_VAL_MO"), ib.num(r, "CAL_DUT_MO"), ib.num(r, "DUT_VAL_MO")
        if not con or cal is None or dut is None:
            print("note: %s excluded — missing values" % m)
            continue
        if dut > con:
            ib.fatal("%s dutiable value exceeds customs value — data defect." % m)
        v = ib._series_val("CUT", con, cal, dut)
        v["data_month"] = m
        series.append(v)
    if len(series) < 2:
        ib.fatal("fewer than 2 usable months — nothing to cut.")
    label = "%s — %s (HS %s)" % (got.title() if cty != "-" else "All origins",
                                 (rows[0].get("I_COMMODITY_SDESC") or comm).strip().lower(), comm)
    name = opts["--name"] or ("%s-%s" % ((got.split(",")[0].lower().replace(" ", "-") if cty != "-" else "all"), comm))
    os.makedirs(CUTS, exist_ok=True)
    pts = [(v["data_month"], v["rate"]) for v in series]
    latest = series[-1]
    peak = max(series, key=lambda v: v["rate"])
    low = min(series, key=lambda v: v["rate"])
    csv = "data_month,rate,rate_dutiable,duty_free_share,con_val,cal_dut,dut_val\n" + "".join(
        "%s,%s,%s,%s,%d,%d,%d\n" % (v["data_month"], v["rate"], "" if v["rate_dutiable"] is None else v["rate_dutiable"],
                                    v["duty_free_share"], v["con_val"], v["cal_dut"], v["dut_val"])
        for v in series)
    meta = {"label": label, "cty_code": cty, "cty_name": got, "commodity": comm, "level": lvl,
            "from": series[0]["data_month"], "to": latest["data_month"], "formula": "CAL_DUT_MO / CON_VAL_MO",
            "source": "US Census Bureau International Trade API, imports for consumption",
            "note": "Custom cut on request — same formula and source as ETRX; not a settlement series.",
            "latest": {"data_month": latest["data_month"], "rate": latest["rate"]},
            "peak": {"data_month": peak["data_month"], "rate": peak["rate"]},
            "low": {"data_month": low["data_month"], "rate": low["rate"]},
            "history": [[v["data_month"], v["rate"]] for v in series]}
    sub = "custom cut · %s: %s · peak %s (%s)" % (sb.month_name(latest["data_month"]), sb.pct(latest["rate"]),
                                                   sb.pct(peak["rate"]), sb.month_name(peak["data_month"]))
    svg = sb.standalone_chart_svg(label, sub, pts)
    for ext, content in (("csv", csv), ("json", json.dumps(meta, indent=1)), ("svg", svg)):
        with open(os.path.join(CUTS, "%s.%s" % (name, ext)), "w") as fh:
            fh.write(content)
    ib.render_pngs(CUTS)
    print("cut: %s" % label)
    print("  %s..%s, %d months; latest %s = %s; peak %s (%s); low %s (%s)" % (
        series[0]["data_month"], latest["data_month"], len(series), latest["data_month"], sb.pct(latest["rate"]),
        sb.pct(peak["rate"]), peak["data_month"], sb.pct(low["rate"]), low["data_month"]))
    print("  files: cuts/%s.{csv,json,svg,png}" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
