#!/usr/bin/env python3
"""ETRX heatmap: effective rate by origin × HS chapter for one month, as a
credited SVG (+PNG). Launch asset and a monthly print-day chart.

  uv run python heatmap.py [--month YYYY-MM] [--origins 12] [--chapters 24]

~1 + N API calls (one per origin). Writes docs/charts/heatmap-<month>.{svg,png}."""
import math
import os
import sys
import time

import index_build as ib
import site_build as sb
import chapters as hs_labels


def top_origins(month, key, n):
    rows = ib.api_get({"get": "CTY_CODE,CTY_NAME,CON_VAL_MO", "SUMMARY_LVL": "DET", "time": month}, key)
    rows = [r for r in rows if (r.get("CTY_CODE") or "").strip() not in ("-", "") and ib.num(r, "CON_VAL_MO")]
    rows.sort(key=lambda r: -ib.num(r, "CON_VAL_MO"))
    return [((r["CTY_CODE"]).strip(), (r["CTY_NAME"] or "").strip().title()) for r in rows[:n]]


def chapter_scan(cty, month, key):
    rows = ib.api_get(
        {"get": "I_COMMODITY,I_COMMODITY_SDESC,CON_VAL_MO,CAL_DUT_MO", "COMM_LVL": "HS2",
         "CTY_CODE": cty, "time": month}, key,
    ) or []
    out = {}
    for r in rows:
        c = (r.get("I_COMMODITY") or "").strip()
        if len(c) == 2 and c.isdigit():
            out[c] = (ib.num(r, "CON_VAL_MO") or 0, ib.num(r, "CAL_DUT_MO") or 0,
                      (r.get("I_COMMODITY_SDESC") or "").strip())
    return out


def shade(rate, cap=0.40):
    """Sequential single-hue scale on the accent; sqrt so 2% and 10% stay distinguishable."""
    f = min(1.0, math.sqrt(max(rate, 0.0) / cap))
    return "rgba(31,78,121,%.3f)" % (0.06 + 0.94 * f), ("#fff" if f > 0.55 else sb.INK)


def render(month, origins, chapters, grid, w=1600):
    left, top, cell_w, cell_h, right = 300, 230, 96, 40, 40
    h = top + cell_h * len(chapters) + 90
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
           'font-family="Inter, Helvetica, Arial, sans-serif">' % (w, h, w, h),
           '<rect width="%d" height="%d" fill="#fff"/>' % (w, h),
           '<text x="48" y="58" font-size="34" font-weight="600" fill="%s">Effective tariff rate by origin and product, %s</text>'
           % (sb.INK, sb.esc(sb.month_name(month))),
           '<text x="48" y="92" font-size="20" fill="%s">Calculated duties ÷ customs value, US imports for consumption. Chapters ordered by import value; origins by import value.</text>'
           % sb.INK2]
    for j, (_code, name) in enumerate(origins):
        x = left + j * cell_w + cell_w / 2
        ax, ay = x + 6, top - 22
        out.append('<text x="%.1f" y="%d" font-size="14" fill="%s" text-anchor="start" transform="rotate(-35 %.1f %d)">%s</text>'
                   % (ax, ay, sb.INK2, ax, ay, sb.esc(name[:18])))
    for i, (ch, desc) in enumerate(chapters):
        y = top + i * cell_h
        out.append('<text x="%d" y="%.1f" font-size="14" fill="%s" text-anchor="end">%s</text>'
                   % (left - 12, y + cell_h * 0.64, sb.INK, sb.esc("%s · %s" % (ch, hs_labels.label(ch, desc)))))
        for j, (code, _name) in enumerate(origins):
            x = left + j * cell_w
            rate = grid.get((code, ch))
            if rate is None:
                out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>' % (x + 1, y + 1, cell_w - 2, cell_h - 2, sb.FILL))
                continue
            fill, ink = shade(rate)
            out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>' % (x + 1, y + 1, cell_w - 2, cell_h - 2, fill))
            out.append('<text x="%.1f" y="%.1f" font-size="14" fill="%s" text-anchor="middle">%s</text>'
                       % (x + cell_w / 2, y + cell_h * 0.64, ink, ("%.1f" % (100 * rate))))
    credit = "%s — %s · %s · Source: US Census Bureau, imports for consumption · blank = no trade recorded" % (
        sb.SITE["name"], sb.SITE["long_name"], sb.SITE["url"].replace("https://", ""))
    out.append('<text x="48" y="%d" font-size="16" fill="%s">%s</text>' % (h - 28, sb.INK3, sb.esc(credit)))
    out.append("</svg>")
    return "".join(out)


def main(argv):
    month, n_or, n_ch = None, 12, 24
    for i, a in enumerate(argv):
        if a == "--month":
            month = argv[i + 1]
        if a == "--origins":
            n_or = int(argv[i + 1])
        if a == "--chapters":
            n_ch = int(argv[i + 1])
    key = ib.require_key()
    if not month:
        months = ib.settled_months(ib.read_prints())
        month = months[-1] if months else ib.fatal("no settled month; pass --month")
    origins = top_origins(month, key, n_or)
    time.sleep(ib.POLITE_PAUSE)
    allc = chapter_scan("-", month, key)
    if not allc:
        ib.fatal("all-countries chapter scan empty for %s" % month)
    ranked = sorted(((c, v) for c, v in allc.items() if c not in ("98", "99")), key=lambda cv: -cv[1][0])[:n_ch]
    chapters = [(c, v[2]) for c, v in ranked]
    grid = {}
    for code, name in origins:
        time.sleep(ib.POLITE_PAUSE)
        scan = chapter_scan(code, month, key)
        for c, (con, cal, _d) in scan.items():
            if con > 0:
                grid[(code, c)] = cal / con
        print("  %s %s: %d chapters" % (code, name, len(scan)))
    svg = render(month, origins, chapters, grid)
    charts = os.path.join(ib.DOCS_DIR, "charts")
    os.makedirs(charts, exist_ok=True)
    path = os.path.join(charts, "heatmap-%s.svg" % month)
    with open(path, "w") as fh:
        fh.write(svg)
    ib.render_pngs(charts)
    print("heatmap: %s (%d origins × %d chapters) -> %s" % (month, len(origins), len(chapters), path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
