#!/usr/bin/env python3
"""ETRX client index: a client's own import-mix-weighted effective tariff rate,
monthly, from a weights file. Product 2 ("your ETRX"). Not a settlement series.

  uv run python client_index.py weights/acme.json

Weights file: {"name": "acme", "label": "Acme Corp import mix",
  "cells": [{"cty": "5700", "comm": "8517", "weight": 0.35}, {"cty": "5520", "comm": "85", "weight": 0.25}, ...]}
`comm` is an HS code of 2, 4, 6 or 10 digits (level inferred). Weights = the
client's import-value shares; they must sum to 1 (±0.01). One API call per cell.

Client rate_t = Σ_i w_i × rate_i,t (each cell's national effective rate that month).
Also reported: the pooled rate Σ cal / Σ con across the same cells (what the
client would pay if its mix matched the national mix inside each cell)."""
import json
import os
import sys

import index_build as ib
import site_build as sb
from cut import COUNTRIES, fetch_range

CUTS = os.path.join(ib.ROOT, "cuts")


def level_of(comm):
    return {2: "HS2", 4: "HS4", 6: "HS6", 10: "HS10"}.get(len(comm)) or ib.fatal("bad HS code %r" % comm)


def main(argv):
    if not argv:
        ib.fatal("usage: client_index.py <weights.json> [--from YYYY-MM]")
    spec = json.load(open(argv[0]))
    start = "2010-01"
    for i, a in enumerate(argv):
        if a == "--from":
            start = argv[i + 1]
    cells = spec["cells"]
    total_w = sum(c["weight"] for c in cells)
    if abs(total_w - 1.0) > 0.01:
        ib.fatal("weights sum to %.3f, not 1.0 — fix the weights file." % total_w)
    key = ib.require_key()
    months = ib.settled_months(ib.read_prints())
    end = months[-1] if months else "2026-06"
    per_cell = {}
    for c in cells:
        comm = str(c["comm"])
        rows = fetch_range(c["cty"], comm, level_of(comm), start, end, key)
        if not rows:
            ib.fatal("no data for cell %s/%s" % (c["cty"], comm))
        expect = COUNTRIES.get(c["cty"])
        got = (rows[0].get("CTY_NAME") or "").strip().upper()
        if expect and expect not in got:
            ib.fatal("cell %s returned %r, expected %r" % (c["cty"], got, expect))
        series = {}
        for r in rows:
            m = (r.get("time") or "")[:7]
            con, cal, dut = ib.num(r, "CON_VAL_MO"), ib.num(r, "CAL_DUT_MO"), ib.num(r, "DUT_VAL_MO")
            if con and cal is not None and dut is not None:
                series[m] = (con, cal, dut)
        per_cell[(c["cty"], comm)] = (c["weight"], series, got.title())
        print("  %s %s: %d months" % (got.title(), comm, len(series)))
    common = None
    for _w, s, _n in per_cell.values():
        common = set(s) if common is None else common & set(s)
    common = sorted(common)
    if len(common) < 2:
        ib.fatal("fewer than 2 months common to all cells.")
    out = []
    for m in common:
        client = sum(w * (s[m][1] / s[m][0]) for w, s, _n in per_cell.values())
        con = sum(s[m][0] for _w, s, _n in per_cell.values())
        cal = sum(s[m][1] for _w, s, _n in per_cell.values())
        out.append({"data_month": m, "client_rate": round(client, 6), "pooled_rate": round(cal / con, 6)})
    name = spec.get("name", "client")
    label = spec.get("label", "%s import-mix tariff index" % name)
    os.makedirs(CUTS, exist_ok=True)
    csv = "data_month,client_rate,pooled_rate\n" + "".join(
        "%s,%s,%s\n" % (r["data_month"], r["client_rate"], r["pooled_rate"]) for r in out)
    latest, peak = out[-1], max(out, key=lambda r: r["client_rate"])
    meta = {"label": label, "name": name, "from": common[0], "to": common[-1],
            "cells": [{"cty": k[0], "cty_name": v[2], "comm": k[1], "weight": v[0]} for k, v in per_cell.items()],
            "method": "client_rate = sum(weight_i * cell_rate_i); pooled_rate = sum(cal)/sum(con) over the cells",
            "note": "Client-specific index on static import-value weights. Same source and formula as ETRX; not a settlement series.",
            "latest": latest, "peak": peak, "history": [[r["data_month"], r["client_rate"]] for r in out]}
    pts = [(r["data_month"], r["client_rate"]) for r in out]
    pooled = [(r["data_month"], r["pooled_rate"]) for r in out]
    sub = "client import-mix index · %s: %s (pooled %s) · peak %s (%s)" % (
        sb.month_name(latest["data_month"]), sb.pct(latest["client_rate"]), sb.pct(latest["pooled_rate"]),
        sb.pct(peak["client_rate"]), sb.month_name(peak["data_month"]))
    svg = sb.standalone_chart_svg(label, sub, pts, pooled)
    for ext, content in (("csv", csv), ("json", json.dumps(meta, indent=1)), ("svg", svg)):
        with open(os.path.join(CUTS, "%s-index.%s" % (name, ext)), "w") as fh:
            fh.write(content)
    ib.render_pngs(CUTS)
    print("client index: %s — %s..%s; latest %s (pooled %s); peak %s (%s)" % (
        label, common[0], common[-1], sb.pct(latest["client_rate"]), sb.pct(latest["pooled_rate"]),
        sb.pct(peak["client_rate"]), peak["data_month"]))
    print("  files: cuts/%s-index.{csv,json,svg,png}" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
