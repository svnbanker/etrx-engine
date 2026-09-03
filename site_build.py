#!/usr/bin/env python3
"""ETRX site generator. Pure string-builders: self-contained HTML pages,
inline SVG charts, standalone credited chart files, per-series JSON,
llms.txt. No JavaScript, no external assets, no dependencies.

Entry point: render_all(latest, history, revisions, schedule) -> {relpath: content}.
Imported by index_build.publish(). `python site_build.py` renders a preview
from the ledger into docs/."""
import json
import os
import re

# ---- site configuration (edit here; RUNBOOK "Domain") -----------------------
SITE = {
    "name": "ETRX",
    "long_name": "US Effective Tariff Rate Index",
    "tagline": "Trade policy, quantified.",
    "url": "https://etrxindex.com",
    "domain": "etrxindex.com",      # written to docs/CNAME on every publish
    "contact": "press@etrxindex.com",
    "x_handle": "@etrxindex",
    "newsletter": "ETRX Monthly Print",
    "signup_url": "https://buttondown.com/etrxindex",       # print-day email list, shown when set
    "admin_line": "ETRX is maintained by an independent administrator based in Montréal.",
    "license_short": "The published series and charts are free to use, cite and republish, including commercially, with attribution to ETRX (CC BY 4.0). The full panel, vintage feed, API and any use as a settlement reference require a license.",
}

# Ink ladder and the single accent.
INK = "#000000"
INK2 = "rgba(0,0,0,0.64)"
INK3 = "rgba(0,0,0,0.56)"
HAIR = "rgba(0,0,0,0.10)"
GRID = "rgba(0,0,0,0.08)"
FILL = "rgba(0,0,0,0.03)"
ACCENT = "#1f4e79"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Inter,'Helvetica Neue',Arial,sans-serif"

NICE_TOPS = [
    0.02, 0.03, 0.04, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20,
    0.25, 0.30, 0.40, 0.50, 0.75, 1.00, 1.50, 2.00,
]

SERIES_NOTES = {
    "ETRX-US": "All US imports for consumption from all origins, excluding HS chapters 98 and 99 (special-provision imports such as returned goods). The settlement headline.",
    "ETRX-US-INCL": "All US imports for consumption including chapters 98 and 99. Published for reconciliation with totals-based external measures; not intended for settlement.",
    "ETRX-STEEL": "Iron and steel (HS 72) and articles of iron or steel (HS 73), all origins. Carries the Section 232 steel actions since 2018.",
    "ETRX-PHARMA": "Pharmaceutical products (HS 30), all origins. Historically near-zero duty; the series records any Section 232 pharmaceutical action.",
    "ETRX-APPAREL": "Knitted apparel (HS 61) and woven apparel (HS 62), all origins. A structurally high-MFN chapter — tariffs here predate every recent action.",
    "ETRX-CN-85": "Electrical machinery, electronics and components (HS 85) from China. The largest single China import chapter; carries the 2018–19 Section 301 lists and the 2025 escalations.",
    "ETRX-CN-84": "Machinery and mechanical appliances (HS 84) from China, including computers.",
    "ETRX-CN-95": "Toys, games and sports equipment (HS 95) from China. Duty-free before 2019; a clean marker of List 4A and later actions.",
    "ETRX-EU-87": "Vehicles and parts (HS 87) from the European Union (Census grouping 0003). The 2.5% MFN car tariff for a decade, then the 2025 actions.",
    "ETRX-MX-87": "Vehicles and parts (HS 87) from Mexico. USMCA-compliant trade is duty-free; the series measures how much of the flow pays duty.",
    "ETRX-CA-76": "Aluminum and articles of aluminum (HS 76) from Canada. Section 232 in 2018–19, then the 2025 actions.",
    "ETRX-CA-44": "Wood and articles of wood (HS 44) from Canada. Note: antidumping/countervailing duties on softwood lumber are assessed separately and are not part of calculated duty.",
    "ETRX-CA-87": "Vehicles and parts (HS 87) from Canada.",
}


# ---- formatting helpers ------------------------------------------------------
def esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def pct(v, dp=2):
    if v is None:
        return "–"
    return ("%." + str(dp) + "f%%") % (100.0 * v)


def axis_pct(v):
    s = ("%.2f" % (100.0 * v)).rstrip("0").rstrip(".")
    return s + "%"


def bps(d):
    if d is None:
        return "–"
    if d == 0:
        return "0 bps"
    return "%s%d bps" % ("+" if d > 0 else "−", abs(d))


def usd(n):
    if n is None:
        return "–"
    if n >= 1e9:
        return "$%.2fB" % (n / 1e9)
    if n >= 1e6:
        return "$%.1fM" % (n / 1e6)
    return "$%s" % format(n, ",")


def month_name(m):
    names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    return "%s %d" % (names[int(m[5:7]) - 1], int(m[:4]))


def slug(sid):
    return sid.lower()


def nice_top(vmax):
    for t in NICE_TOPS:
        if t >= vmax * 1.02:
            return t
    return NICE_TOPS[-1]


# ---- charts --------------------------------------------------------------------
def _poly(points, w, h, pad_l, pad_r, pad_t, pad_b, top):
    n = len(points)
    span = max(n - 1, 1)
    iw = w - pad_l - pad_r
    ih = h - pad_t - pad_b
    coords = []
    for i, (_m, v) in enumerate(points):
        x = pad_l + iw * i / span
        y = pad_t + ih * (1.0 - min(v, top) / top)
        coords.append("%.1f,%.1f" % (x, y))
    return coords


def _line_layer(main_pts, companion_pts, w, h, pad_l, pad_r, pad_t, pad_b, fs, label_end=False):
    top = nice_top(max(v for _m, v in main_pts + (companion_pts or [])))
    out = []
    for frac in (0.0, 0.5, 1.0):
        y = pad_t + (h - pad_t - pad_b) * (1.0 - frac)
        out.append(
            '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
            % (pad_l, y, w - pad_r, y, GRID)
        )
        out.append(
            '<text x="%d" y="%.1f" font-size="%s" fill="%s">%s</text>'
            % (w - pad_r + 8, y + fs * 0.35, fs, INK3, axis_pct(top * frac))
        )
    years = sorted({m[:4] for m, _v in main_pts})
    step = max(1, len(years) // 7)
    shown = set(years[::step])
    span = max(len(main_pts) - 1, 1)
    for i, (m, _v) in enumerate(main_pts):
        if m.endswith("-01") and m[:4] in shown:
            x = pad_l + (w - pad_l - pad_r) * i / span
            out.append(
                '<text x="%.1f" y="%d" font-size="%s" fill="%s">%s</text>'
                % (x, h - pad_b + fs + 6, fs, INK3, m[:4])
            )
    if companion_pts:
        c = _poly(companion_pts, w, h, pad_l, pad_r, pad_t, pad_b, top)
        out.append(
            '<polyline points="%s" fill="none" stroke="rgba(0,0,0,0.26)" '
            'stroke-width="1.25"/>' % " ".join(c)
        )
    c = _poly(main_pts, w, h, pad_l, pad_r, pad_t, pad_b, top)
    out.append(
        '<polyline points="%s" fill="none" stroke="%s" stroke-width="1.75" '
        'stroke-linejoin="round"/>' % (" ".join(c), INK)
    )
    lx, ly = c[-1].split(",")
    out.append('<circle cx="%s" cy="%s" r="3.5" fill="%s"/>' % (lx, ly, ACCENT))
    if label_end:
        out.append(
            '<text x="%.1f" y="%.1f" font-size="%s" font-weight="600" fill="%s">%s</text>'
            % (float(lx) - 4, float(ly) - 12, fs + 2, ACCENT, pct(main_pts[-1][1]))
        )
    return "".join(out)


def chart_svg(main_pts, companion_pts=None, w=1040, h=380):
    """Inline page chart: hairline grid, year ticks, accent terminal dot."""
    if len(main_pts) < 2:
        return ""
    return (
        '<svg viewBox="0 0 %d %d" width="100%%" role="img" '
        'aria-label="Effective tariff rate, monthly">%s</svg>'
        % (w, h, _line_layer(main_pts, companion_pts, w, h, 8, 64, 12, 28, 12.5))
    )


def spark_svg(points, w=260, h=64):
    if len(points) < 2:
        return ""
    top = nice_top(max(v for _m, v in points))
    c = _poly(points, w, h, 2, 10, 6, 6, top)
    lx, ly = c[-1].split(",")
    return (
        '<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-hidden="true">'
        '<polyline points="%s" fill="none" stroke="%s" stroke-width="1.5" '
        'stroke-linejoin="round"/>'
        '<circle cx="%s" cy="%s" r="2.75" fill="%s"/></svg>'
        % (w, h, " ".join(c), INK, lx, ly, ACCENT)
    )


def standalone_chart_svg(title, subtitle, main_pts, companion_pts=None, w=1600, h=640):
    """Downloadable chart with title and credit baked in — survives screenshots."""
    if len(main_pts) < 2:
        return ""
    fs = 20
    body = _line_layer(main_pts, companion_pts, w, h, 48, 110, 130, 90, fs, label_end=True)
    credit = "%s — %s · %s · Source: US Census Bureau, imports for consumption" % (
        SITE["name"], SITE["long_name"], SITE["url"].replace("https://", ""))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
        'font-family="Inter, Helvetica, Arial, sans-serif">'
        '<rect width="%d" height="%d" fill="#fff"/>'
        '<text x="48" y="58" font-size="34" font-weight="600" fill="%s">%s</text>'
        '<text x="48" y="92" font-size="20" fill="%s">%s</text>'
        "%s"
        '<text x="48" y="%d" font-size="16" fill="%s">%s</text>'
        "</svg>"
        % (w, h, w, h, w, h, INK, esc(title), INK2, esc(subtitle), body, h - 28, INK3, esc(credit))
    )


# ---- markdown (rulebook) -> html, minimal ------------------------------------------
def _inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
    return s


def md_to_html(md):
    out, para, table, lst = [], [], [], []

    def flush():
        if para:
            out.append("<p>%s</p>" % _inline(" ".join(para)))
            para.clear()
        if table:
            rows = [r for r in table if not re.match(r"^\|[\s\-|:]+\|$", r)]
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            if cells:
                head = "".join("<th>%s</th>" % _inline(c) for c in cells[0])
                body = "".join(
                    "<tr>%s</tr>" % "".join("<td>%s</td>" % _inline(c) for c in r)
                    for r in cells[1:]
                )
                out.append(
                    '<div class=tblwrap><table class=doc><thead><tr>%s</tr></thead>'
                    "<tbody>%s</tbody></table></div>" % (head, body)
                )
            table.clear()
        if lst:
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % _inline(i) for i in lst))
            lst.clear()

    for line in md.splitlines():
        s = line.rstrip()
        if not s.strip():
            flush()
            continue
        if s.startswith("#"):
            flush()
            level = len(s) - len(s.lstrip("#"))
            out.append("<h%d>%s</h%d>" % (min(level + 1, 4), _inline(s.lstrip("#").strip()), min(level + 1, 4)))
        elif s.startswith("|"):
            if para or lst:
                flush()
            table.append(s)
        elif re.match(r"^\s*[-*] ", s):
            if para or table:
                flush()
            lst.append(re.sub(r"^\s*[-*] ", "", s))
        elif re.match(r"^\s*\d+\. ", s):
            if para or table:
                flush()
            lst.append(re.sub(r"^\s*\d+\. ", "", s))
        else:
            if table or lst:
                flush()
            para.append(s.strip())
    flush()
    return "\n".join(out)


# ---- page shell ----------------------------------------------------------------------
CSS = """
:root{color-scheme:light}
*{margin:0;padding:0;box-sizing:border-box}
body{background:#fff;color:%(ink)s;font:16.5px/1.55 %(font)s;
 -webkit-font-smoothing:antialiased;padding:0 24px}
main{max-width:1040px;margin:0 auto}
a{color:%(accent)s;text-decoration:none}
a:hover{text-decoration:underline}
nav{max-width:1040px;margin:28px auto 0;display:flex;flex-wrap:wrap;gap:6px 22px;
 align-items:baseline;font-size:15px}
nav .mark{font-weight:600;letter-spacing:.02em;color:%(ink)s;margin-right:10px}
nav a{color:%(ink2)s;font-weight:500}
nav a.on{color:%(ink)s}
section{margin:96px 0}
header.mast{margin:56px 0 0}
h1{font-size:clamp(28px,4vw,40px);font-weight:600;line-height:1.1;
 letter-spacing:-0.015em;margin:10px 0 14px}
.sub{color:%(ink2)s;max-width:62ch}
.bigrow{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px 28px;margin:0 0 26px}
.bigval{font-size:clamp(56px,9vw,92px);font-weight:600;letter-spacing:-0.02em;
 line-height:1;font-variant-numeric:tabular-nums}
.bigmeta{color:%(ink2)s}
.delta{font-variant-numeric:tabular-nums}
h2{font-size:22px;font-weight:600;letter-spacing:-0.01em;margin:0 0 6px}
h3{font-size:17px;font-weight:600;margin:28px 0 8px}
h4{font-size:16px;font-weight:600;margin:20px 0 6px}
.chapsub{color:%(ink2)s;margin:0 0 26px;max-width:62ch}
figcaption{color:%(ink3)s;font-size:14px;margin-top:10px;max-width:70ch}
.chartwrap{overflow-x:auto;direction:rtl}
.chartwrap svg{min-width:640px;display:block;direction:ltr}
table{width:100%%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th,td{white-space:nowrap}
th{font-weight:500;color:%(ink2)s;font-size:14px;text-align:right;
 padding:8px 12px;border-bottom:1px solid %(hair)s}
th:first-child,td:first-child{text-align:left;padding-left:0}
th:last-child,td:last-child{padding-right:0}
td{padding:9px 12px;text-align:right}
tbody tr:nth-child(even){background:%(fill)s}
td.name{color:%(ink)s}
table.doc th,table.doc td{text-align:left;white-space:normal;vertical-align:top}
.tblwrap{overflow-x:auto;margin:14px 0 22px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));
 gap:40px 36px}
.cell .lbl{font-size:14px;color:%(ink2)s;margin-bottom:8px;min-height:2.6em}
.cell .lbl a{color:%(ink2)s}
.cell .val{display:flex;justify-content:space-between;align-items:baseline;
 margin-top:6px;font-variant-numeric:tabular-nums}
.cell .val b{font-weight:600;font-size:18px}
.cell .val span{color:%(ink3)s;font-size:14px}
.prose p,.prose li{max-width:68ch;margin:0 0 14px}
.prose ul{margin:0 0 14px 22px}
.prose code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:14.5px;
 background:%(fill)s;padding:1px 5px}
.formula{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
 font-size:15px;background:%(fill)s;padding:14px 18px;margin:18px 0;
 max-width:68ch;overflow-x:auto;white-space:pre-wrap;word-break:break-all}
.cite{background:%(fill)s;padding:16px 20px;max-width:68ch;margin:18px 0}
.cite .k{font-size:14px;color:%(ink2)s;margin-bottom:4px}
.downloads{margin-top:18px}
.kv{max-width:68ch}
.kv div{display:flex;gap:16px;padding:8px 0;border-bottom:1px solid %(hair)s}
.kv div:last-child{border-bottom:0}
.kv b{flex:0 0 190px;font-weight:500;color:%(ink2)s;font-size:15px}
.stat{display:flex;flex-wrap:wrap;gap:12px 48px;margin:22px 0}
.stat div b{display:block;font-size:26px;font-weight:600;letter-spacing:-0.01em;
 font-variant-numeric:tabular-nums}
.stat div span{font-size:14px;color:%(ink2)s}
footer{margin:120px 0 64px;padding-top:20px;border-top:1px solid %(hair)s;
 color:%(ink3)s;font-size:14px}
footer p{margin:0 0 6px}
@media(max-width:640px){section{margin:64px 0}header.mast{margin:40px 0 0}
 .grid{gap:32px 24px}footer{margin-top:80px}.kv b{flex-basis:120px}}
@media print{body{padding:0}section{margin:40px 0}nav{display:none}}
""" % {"ink": INK, "ink2": INK2, "ink3": INK3, "hair": HAIR, "fill": FILL,
       "accent": ACCENT, "font": FONT}

NAV = [
    ("index.html", "Index"),
    ("series.html", "Series"),
    ("methodology.html", "Methodology"),
    ("verify.html", "Verify"),
    ("data.html", "Data"),
    ("calendar.html", "Calendar"),
    ("about.html", "About"),
    ("press.html", "Press"),
    ("reconcile.html", "Reconcile"),
    ("notes/index.html", "Notes"),
]

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' fill='%231f4e79'/%3E%3Cpath d='M8 22 13 15 18 18 24 9' "
           "stroke='%23fff' stroke-width='2.5' fill='none'/%3E%3C/svg%3E")


def shell(title, active, body, latest, depth=0, description=None):
    pre = "../" * depth
    links = "".join(
        '<a href="%s%s"%s>%s</a>' % (pre, href, ' class=on' if href == active else "", label)
        for href, label in NAV
    )
    npi = latest["next_print"]
    desc = description or ("A rules-based monthly index of realized effective US tariff rates "
                           "by country of origin and HS chapter, from official Census trade data.")
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<link rel="icon" href="%(fav)s">
<link rel="canonical" href="%(canon)s">
<style>%(css)s</style>
</head>
<body>
<nav><a class=mark href="%(pre)sindex.html">ETRX</a>%(links)s</nav>
<main>
%(body)s
<footer>
%(subscribe)s<p>Next print: on the Census FT-900 release of %(nrel)s, covering %(ndm)s. Latest data month: %(dm)s.</p>
<p>Generated %(gen)s from the print ledger. First prints settle; revisions are logged, never restated.</p>
<p>Research and commentary. Not investment advice.</p>
</footer>
</main>
</body>
</html>
""" % {
        "title": esc(title), "desc": esc(desc), "fav": FAVICON, "css": CSS, "pre": pre,
        "links": links, "body": body,
        "subscribe": ('<p><a href="%s">Get the print by email</a> — one message a month, '
                      'nothing else.</p>' % esc(SITE["signup_url"])) if SITE["signup_url"] else "",
        "canon": SITE["url"] + "/" + ("" if active == "index.html" else active),
        "nrel": esc(npi["release"]), "ndm": esc(npi["data_month"]),
        "dm": esc(month_name(latest["data_month"])), "gen": esc(latest["generated"]),
    }


def cite_block(latest, series_id=None, series_label=None):
    dm = month_name(latest["data_month"])
    what = "%s — %s" % (SITE["name"], SITE["long_name"])
    if series_label:
        what += ", %s (%s)" % (series_label, series_id)
    text = "%s, %s print. %s" % (what, dm, SITE["url"])
    return (
        '<div class=cite><div class=k>Cite as</div>%s<div class=k style="margin-top:10px">License</div>%s</div>'
        % (esc(text), esc(SITE["license_short"]))
    )


def contact_line():
    if SITE["contact"]:
        return 'Contact: <a href="mailto:%s">%s</a>.' % (esc(SITE["contact"]), esc(SITE["contact"]))
    return "A press and licensing contact address will be published at launch."


def signup_line():
    if SITE["signup_url"]:
        return ('<a href="%s">Subscribe to %s</a> — one message per print, nothing else.'
                % (esc(SITE["signup_url"]), esc(SITE["newsletter"])))
    return "%s, the print-day email, opens at launch." % esc(SITE["newsletter"])


# ---- pages -------------------------------------------------------------------------------
def page_index(latest, history):
    cur = latest["data_month"]
    by_id = {s["id"]: s for s in latest["series"]}
    head = by_id["ETRX-US"]
    movers = [s for s in latest["series"] if s["id"] != "ETRX-US-INCL"]
    movers.sort(key=lambda s: (s["delta_bps"] is None, -abs(s["delta_bps"] or 0)))
    rows = "".join(
        "<tr><td class=name><a href=\"series/%s.html\">%s</a></td><td>%s</td><td>%s</td>"
        "<td>%s</td><td>%s</td></tr>"
        % (slug(s["id"]), esc(s["label"]), pct(s["rate"]), bps(s["delta_bps"]),
           pct(s["rate_dutiable"]), pct(s["duty_free_share"], 1))
        for s in movers
    )
    cells = "".join(
        '<div class=cell><div class=lbl><a href="series/%s.html">%s</a></div>%s'
        "<div class=val><b>%s</b><span>%s</span></div></div>"
        % (slug(s["id"]), esc(s["label"]), spark_svg(history.get(s["id"], [])),
           pct(s["rate"]), bps(s["delta_bps"]))
        for s in latest["series"] if s["id"] not in ("ETRX-US", "ETRX-US-INCL")
    )
    pts = history.get("ETRX-US", [])
    prior = pts[-2][0] if len(pts) > 1 else cur
    delta_txt = "%s vs %s" % (bps(head["delta_bps"]), month_name(prior)) if head["delta_bps"] is not None else ""
    first_year = pts[0][0][:4] if pts else cur[:4]
    body = """
<header class=mast>
<h1>US Effective Tariff Rate Index</h1>
<p class=sub>The current effective US tariff rate: the realized duty rate on US
imports for consumption — calculated duties as a share of customs value — by
country of origin and HS chapter, from official US Census Bureau trade data.
Monthly, rules-based, first print settles.</p>
</header>

<section>
<div class=bigrow>
<div class=bigval>%(bigval)s</div>
<div class=bigmeta>%(bigmonth)s · headline, all imports ex&nbsp;98/99<br>
<span class=delta>%(delta)s</span></div>
</div>
<figure>
<div class=chartwrap>%(chart)s</div>
<figcaption>United States, %(fy)s–%(cy)s. Ink line: settlement headline (all imports
excluding HS chapters 98/99). Light line: companion including 98/99. Source: US
Census Bureau, imports for consumption. <a href="charts/etrx-us.png">Download chart (PNG)</a> ·
<a href="charts/etrx-us.svg">SVG</a></figcaption>
</figure>
</section>

<section>
<h2>This print</h2>
<p class=chapsub>All series for %(bigmonth)s, ordered by the size of the month-over-month move.</p>
<div style="overflow-x:auto"><table>
<thead><tr><th>Series</th><th>Effective rate</th><th>Change</th>
<th>Rate on dutiable value</th><th>Duty-free share</th></tr></thead>
<tbody>%(rows)s</tbody></table></div>
</section>

<section>
<h2>Series</h2>
<p class=chapsub>Full history since %(fy)s for each country-of-origin and chapter series.
Each has its own page with the full chart, definition and downloads.</p>
<div class=grid>%(cells)s</div>
</section>

<section class=prose>
<h2>Methodology</h2>
<p>Each series is the ratio of calculated duties to the customs value of US imports
for consumption, for one country of origin and one HS chapter (or an aggregate), in
one statistical month:</p>
<div class=formula>effective rate = calculated duties ÷ customs value (imports for consumption)</div>
<p>Values come from the US Census Bureau International Trade API. Calculated duty is
fixed at entry and is never restated by later refund litigation, which is why the
index settles on it rather than on collected cash. The first published value for a
month is the settlement value; later Census revisions are logged separately and
never restate a settled print. Full rules: <a href="methodology.html">Methodology</a> ·
check any number yourself: <a href="verify.html">Verify</a>.</p>
%(cite)s
<p class=downloads><a href="data.html">Data &amp; downloads</a> ·
<a href="etrx.csv">Full panel (CSV)</a> · <a href="latest.json">Latest print (JSON)</a> ·
<a href="calendar.html">Release calendar</a></p>
</section>
""" % {
        "bigval": pct(head["rate"]), "bigmonth": esc(month_name(cur)), "delta": esc(delta_txt),
        "chart": chart_svg(history.get("ETRX-US", []), history.get("ETRX-US-INCL", [])),
        "fy": esc(first_year), "cy": esc(cur[:4]), "rows": rows, "cells": cells,
        "cite": cite_block(latest),
    }
    return shell("ETRX — US Effective Tariff Rate Index", "index.html", body, latest,
                 description="The current effective US tariff rate, monthly, by country and product: "
                             "%s in %s. Rules-based, from official Census data." % (pct(head["rate"]), month_name(cur)))


def page_series_list(latest, history):
    items = "".join(
        '<div class=cell><div class=lbl><a href="series/%s.html">%s</a></div>%s'
        "<div class=val><b>%s</b><span>%s</span></div></div>"
        % (slug(s["id"]), esc(s["label"]), spark_svg(history.get(s["id"], [])),
           pct(s["rate"]), bps(s["delta_bps"]))
        for s in latest["series"]
    )
    body = """
<header class=mast><h1>Series</h1>
<p class=sub>Thirteen series: the settlement headline, its inclusive companion, three
all-origin product aggregates, and eight country-of-origin × chapter cells. Every
series shares one formula and one source; only the slice differs.</p></header>
<section><div class=grid>%s</div></section>
""" % items
    return shell("Series — ETRX", "series.html", body, latest)


def page_series(latest, history, s, series_stats):
    sid = s["id"]
    pts = history.get(sid, [])
    st = series_stats.get(sid, {})
    body = """
<header class=mast>
<p class=sub><a href="../series.html">Series</a> · %(sid)s</p>
<h1>%(label)s</h1>
<p class=sub>%(note)s</p>
</header>
<section>
<div class=stat>
<div><b>%(rate)s</b><span>effective rate, %(dm)s</span></div>
<div><b>%(delta)s</b><span>month over month</span></div>
<div><b>%(rd)s</b><span>rate on dutiable value</span></div>
<div><b>%(dfs)s</b><span>duty-free share</span></div>
<div><b>%(cv)s</b><span>customs value, %(dm)s</span></div>
<div><b>%(cd)s</b><span>calculated duty, %(dm)s</span></div>
</div>
<figure><div class=chartwrap>%(chart)s</div>
<figcaption>%(label)s, %(fy)s–%(cy)s, monthly. Peak %(peak)s (%(peakm)s); low %(low)s (%(lowm)s).
<a href="../charts/%(slug)s.png">Download chart (PNG)</a> · <a href="../charts/%(slug)s.svg">SVG</a></figcaption></figure>
</section>
<section class=prose>
<h2>Definition</h2>
<p>Formula: calculated duties ÷ customs value of imports for consumption, dollars
summed before dividing. Source: US Census Bureau International Trade API, monthly
imports (HS), variables <code>CAL_DUT_MO</code>, <code>CON_VAL_MO</code>, <code>DUT_VAL_MO</code>.</p>
%(cite)s
<p class=downloads><a href="../series/%(slug)s.json">This series (JSON)</a> ·
<a href="../etrx.csv">Full panel (CSV)</a> · <a href="../methodology.html">Methodology</a> ·
<a href="../verify.html">Verify a number</a></p>
</section>
""" % {
        "sid": esc(sid), "label": esc(s["label"]), "note": esc(SERIES_NOTES.get(sid, "")),
        "rate": pct(s["rate"]), "dm": esc(month_name(latest["data_month"])),
        "delta": bps(s["delta_bps"]), "rd": pct(s["rate_dutiable"]),
        "dfs": pct(s["duty_free_share"], 1), "cv": usd(st.get("con_val")), "cd": usd(st.get("cal_dut")),
        "chart": chart_svg(pts), "fy": esc(pts[0][0][:4] if pts else ""), "cy": esc(latest["data_month"][:4]),
        "peak": pct(st.get("peak")), "peakm": esc(month_name(st["peak_m"])) if st.get("peak_m") else "",
        "low": pct(st.get("low")), "lowm": esc(month_name(st["low_m"])) if st.get("low_m") else "",
        "slug": slug(sid), "defn": esc(st.get("defn", "")),
        "cite": cite_block(latest, sid, s["label"]),
    }
    return shell("%s — ETRX" % s["label"], "series.html", body, latest, depth=1,
                 description="%s: effective US tariff rate %s in %s. Monthly history since 2010." % (
                     s["label"], pct(s["rate"]), month_name(latest["data_month"])))


def page_methodology(latest, rulebook_md):
    body = """
<header class=mast><h1>Methodology</h1>
<p class=sub>The complete rulebook, rendered from the versioned source. This is the
document a settlement reference is held to: series definitions, formulas, calendar,
first-print rule, revision policy, fallbacks, governance.</p></header>
<section class=prose>%s</section>
""" % md_to_html(rulebook_md)
    return shell("Methodology — ETRX", "methodology.html", body, latest)


def page_verify(latest, sample):
    """sample: dict with series_id, label, cty, chapter, month, con_val, cal_dut, rate."""
    api = ("https://api.census.gov/data/timeseries/intltrade/imports/hs?"
           "get=CTY_NAME,I_COMMODITY,CON_VAL_MO,CAL_DUT_MO,DUT_VAL_MO&COMM_LVL=HS2"
           "&CTY_CODE=%s&I_COMMODITY=%s&time=%s&key=YOUR_KEY" % (sample["cty"], sample["chapter"], sample["month"]))
    body = """
<header class=mast><h1>Verify a number yourself</h1>
<p class=sub>ETRX has no authority except that anyone can check it. Here is how to
reproduce a published value from the government's own data in a few minutes.</p></header>
<section class=prose>
<h2>Worked example: %(label)s, %(dm)s</h2>
<p>ETRX printed <b>%(rate)s</b>. The two inputs behind it:</p>
<div class=kv>
<div><b>Customs value</b><span>%(cv)s (CON_VAL_MO)</span></div>
<div><b>Calculated duty</b><span>%(cd)s (CAL_DUT_MO)</span></div>
<div><b>Rate</b><span>%(cd)s ÷ %(cv)s = %(rate_full)s</span></div>
</div>
<h3>Route 1 — the Census API (one URL)</h3>
<p>The calculation code is open source: <a href="https://github.com/svnbanker/etrx-engine">github.com/svnbanker/etrx-engine</a>. Clone it, run the selftest, and print a month yourself.</p>
<p>Get a free key at <a href="https://api.census.gov/data/key_signup.html">api.census.gov/data/key_signup.html</a>
(instant, email activation), then open:</p>
<div class=formula>%(api)s</div>
<p>The row returned carries <code>CON_VAL_MO</code> and <code>CAL_DUT_MO</code>. Divide. You will
get the number above to the last digit, unless Census has since revised the month —
in which case the difference is exactly what our <a href="revisions.html">revisions log</a> records.</p>
<h3>Route 2 — USITC DataWeb (no key, point and click)</h3>
<ul>
<li>Open <a href="https://dataweb.usitc.gov/">dataweb.usitc.gov</a> → Trade data → Imports for consumption.</li>
<li>Data to report: <b>Customs value</b> and <b>Calculated duties</b>. Timeframe: monthly, %(dm)s.</li>
<li>Commodities: HTS 2-digit, chapter <b>%(chapter)s</b>. Countries: <b>%(cty_name)s</b>.</li>
<li>Run the report; divide calculated duties by customs value.</li>
</ul>
<h3>What "matches" means</h3>
<p>Aggregates (the headline, steel, pharma, apparel) sum dollars across chapters before
dividing; check them by summing the chapter rows. The headline excludes chapters 98 and 99.
Every published value is stored to six decimals; displayed values are rounded to two.
The full formula set and all edge rules are in the <a href="methodology.html">methodology</a>.</p>
</section>
""" % {
        "label": esc(sample["label"]), "dm": esc(month_name(sample["month"])), "rate": pct(sample["rate"]),
        "rate_full": "%.6f" % sample["rate"], "cv": "$%s" % format(sample["con_val"], ","),
        "cd": "$%s" % format(sample["cal_dut"], ","), "api": esc(api),
        "chapter": esc(sample["chapter"]), "cty_name": esc(sample["cty_name"]),
    }
    return shell("Verify — ETRX", "verify.html", body, latest)


def page_data(latest):
    cols = [
        ("data_month", "Statistical month, YYYY-MM."),
        ("series_id", "Series identifier, e.g. ETRX-CN-85."),
        ("rate", "Effective rate: calculated duty ÷ customs value. Decimal (0.0713 = 7.13%), six places."),
        ("rate_dutiable", "Calculated duty ÷ dutiable value. Empty when dutiable value is zero."),
        ("duty_free_share", "1 − dutiable value ÷ customs value."),
        ("con_val", "Customs value of imports for consumption, US dollars."),
        ("cal_dut", "Calculated duty, US dollars."),
        ("dut_val", "Dutiable value, US dollars."),
        ("vintage_date", "Date this value was printed (UTC)."),
        ("vintage_note", "backfill (built retroactively; embeds Census revisions), live (first print on release), or revision."),
    ]
    dict_rows = "".join("<div><b>%s</b><span>%s</span></div>" % (esc(k), esc(v)) for k, v in cols)
    series_links = " · ".join(
        '<a href="series/%s.json">%s</a>' % (slug(s["id"]), esc(s["id"])) for s in latest["series"]
    )
    body = """
<header class=mast><h1>Data</h1>
<p class=sub>Everything ETRX publishes, at stable URLs, free with attribution. Files are
regenerated on every print; URLs never change.</p></header>
<section class=prose>
<h2>Downloads</h2>
<div class=kv>
<div><b>Settlement panel</b><span><a href="etrx.csv">etrx.csv</a> — every series, every month, first prints only.</span></div>
<div><b>Latest print</b><span><a href="latest.json">latest.json</a> — all series for the latest month, with prior values and deltas.</span></div>
<div><b>Revisions</b><span><a href="revisions.csv">revisions.csv</a> — later vintages of settled months (see <a href="revisions.html">log</a>).</span></div>
<div><b>Per-series JSON</b><span>%(series)s</span></div>
<div><b>Charts</b><span><a href="charts/etrx-us.png">Headline PNG</a> · every series has PNG and SVG at <code>charts/&lt;series-id&gt;.png</code></span></div>
<div><b>Rulebook</b><span><a href="RULEBOOK.md">RULEBOOK.md</a> · <a href="methodology.html">rendered</a></span></div>
<div><b>For AI assistants</b><span><a href="llms.txt">llms.txt</a></span></div>
</div>
<h2 style="margin-top:56px">Data dictionary</h2>
<div class=kv>%(dict)s</div>
<h2 style="margin-top:56px">Data products</h2>
<p>Beyond the free index, the same pipeline produces three things professionals ask for:</p>
<div class=kv>
<div><b>Full-granularity feed</b><span>Every HS chapter × the top 60 origins, monthly since 2010 — about 6,000 series, updated the day each print lands. Sample: <a href="sample-5520.csv">Vietnam, all chapters (CSV)</a>.</span></div>
<div><b>Custom cuts and client indices</b><span>Any origin × HS2/HS4/HS6/HS10 series, full history, delivered as CSV, JSON and a credited chart — usually same day. Or an import-mix-weighted index on a client's own origin × product shares, rebuilt every print. Useful for entry-level duty histories in refund and customs work, and for measuring one company's exposure rather than the nation's.</span></div>
<div><b>Settlement and benchmark licensing</b><span>Use of the index as the reference of a listed, cleared or OTC product, with calculation-agent services under the rulebook's calendar, fallback and revision policy.</span></div>
</div>
<p style="margin-top:14px">To request a cut, a client index, feed access or licensing terms, write to
%(contact_plain)s with the origins, products and period you need. Academic and think-tank use of the
feed is free with citation.</p>
<h2 style="margin-top:56px">License</h2>
<p>%(license)s Attribution: “ETRX — US Effective Tariff Rate Index, %(url)s”. Charts may be
republished as-is; the credit line is part of the image.</p>
</section>
""" % {"series": series_links, "dict": dict_rows, "license": esc(SITE["license_short"]),
       "url": esc(SITE["url"].replace("https://", "")), "contact": contact_line(),
       "contact_plain": ('<a href="mailto:%s">%s</a>' % (esc(SITE["contact"]), esc(SITE["contact"]))
                         if SITE["contact"] else "the contact address")}
    return shell("Data — ETRX", "data.html", body, latest)


def page_calendar(latest, schedule):
    today = latest["generated"]
    rows = "".join(
        "<tr><td class=name>%s</td><td>%s</td><td>%s</td></tr>"
        % (esc(rel), esc(month_name(dm)), "upcoming" if rel >= today else "printed")
        for rel, dm in schedule
    )
    body = """
<header class=mast><h1>Release calendar</h1>
<p class=sub>Census publishes monthly trade data with the FT-900 release at 8:30 a.m. ET.
ETRX prints within one business day of each release — usually within hours.</p></header>
<section>
<div style="overflow-x:auto"><table>
<thead><tr><th>Census release</th><th>Data month</th><th>Status</th></tr></thead>
<tbody>%(rows)s</tbody></table></div>
<p class=chapsub style="margin-top:22px">Source: census.gov/foreign-trade/reference/release_schedule.html.
Catch-up releases (several months at once, off-schedule dates) print on detection.</p>
</section>
<section class=prose>
<h2>Print-day email</h2>
<p>%(signup)s</p>
</section>
""" % {"rows": rows, "signup": signup_line()}
    return shell("Release calendar — ETRX", "calendar.html", body, latest)


def page_about(latest):
    body = """
<header class=mast><h1>About</h1>
<p class=sub>ETRX is an independent, rules-based index of the effective US tariff rate.
It exists because the number importers actually pay was being estimated, modeled and
argued about — but not measured on a schedule anyone could rely on.</p></header>
<section class=prose>
<h2>What it is</h2>
<p>A monthly measurement, not a forecast: calculated duties as a share of the customs
value of US imports for consumption, by country of origin and HS chapter, from official
US Census Bureau data. The methodology is public, the calculation is deterministic, and
every published value can be reproduced by anyone from the same public data.</p>
<h2>Independence</h2>
<p>The engine is public (<a href="https://github.com/svnbanker/etrx-engine">etrx-engine</a>, MIT). Publishing the code removes key-person risk: anyone can reproduce every number, and the index does not depend on one person to run.</p>
<p>The administrator holds no positions referencing the index, accepts no sponsorship,
and has no affiliation with any exchange, dealer, trade association or government body.
Input data is official statistics the administrator cannot influence. The index is
computed whole or not at all — never from partial data — and the first published value
for any month is never restated.</p>
<h2>Who</h2>
<p>%(admin)s %(contact)s</p>
<h2>Governance</h2>
<p>Methodology changes require a new rulebook version with a full print cycle of notice
and are never applied to settled values. See the <a href="methodology.html">methodology</a>
for the fallback policy, revision policy and IOSCO alignment statement, the
<a href="audit.html">audit log</a> for every verification and decision on the record, and the
<a href="revisions.html">revisions log</a> for what later Census vintages would have said.</p>
</section>
""" % {"admin": esc(SITE["admin_line"]), "contact": contact_line()}
    return shell("About — ETRX", "about.html", body, latest)


NOTES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes")


def load_notes():
    items = []
    if not os.path.isdir(NOTES_DIR):
        return items
    for f in sorted(os.listdir(NOTES_DIR), reverse=True):
        if not f.endswith(".md"):
            continue
        md = open(os.path.join(NOTES_DIR, f)).read()
        title = next((l[2:].strip() for l in md.splitlines() if l.startswith("# ")), f[:-3])
        items.append({"slug": f[:-3], "date": f[:10], "title": title, "md": md})
    return items


def page_notes_index(latest, notes):
    lis = "".join('<li><span class=muted>%s</span> &nbsp; <a href="%s.html">%s</a></li>'
                  % (n["date"], n["slug"], esc(n["title"])) for n in notes)
    body = ('<header class=mast><h1>ETRX Notes</h1>'
            '<p class=sub>The index prints numbers and nothing else. Commentary lives here, separately: '
            'what moved, what is about to move, and where public coverage gets the scope wrong. '
            'Every explanation of a move traces to a verified entry in the policy ledger.</p></header>'
            '<section class=prose><ul class=plain>' + lis + '</ul>'
            '<p class=muted>Research and commentary. Not investment advice.</p></section>')
    return shell("ETRX Notes", "notes/index.html", body, latest, depth=1)


def page_note(latest, n):
    md_body = "\n".join(l for l in n["md"].splitlines() if not l.startswith("# "))
    body = ('<header class=mast><h1>%s</h1><p class=sub><a href="index.html">ETRX Notes</a> · %s</p></header>'
            % (esc(n["title"]), n["date"])
            + '<section class=prose>' + md_to_html(md_body)
            + '<p class=muted>Research and commentary. Not investment advice. '
              'The index itself: <a href="../index.html">the current print</a>.</p></section>')
    return shell(n["title"] + " · ETRX Notes", "notes/index.html", body, latest, depth=1)


def page_reconcile(latest):
    head = next(x for x in latest["series"] if x["id"] == "ETRX-US")
    steel = next(x for x in latest["series"] if x["id"] == "ETRX-STEEL")
    dm = month_name(latest["data_month"])
    body = ('<header class=mast><h1>Reconciliation</h1>'
        '<p class=sub>Four numbers are called "the US tariff rate". They measure different things. '
        'What each one is, its latest stated value, and why the gaps exist. Updated every print.</p></header>'
        '<section class=prose>'
        '<div class=tblwrap><table class=data><thead><tr><th>Source</th><th>What it measures</th><th>Cadence</th><th>Latest stated</th></tr></thead><tbody>'
        '<tr><td class=name><b>ETRX</b></td><td>Realized: calculated duty assessed at entry as a share of customs value, by origin and HS chapter, imports for consumption, HS 98 and 99 excluded. First print settles.</td>'
        '<td>Monthly, on the Census FT-900 date</td><td><b>' + pct(head["rate"]) + '</b> (' + dm + ')</td></tr>'
        '<tr><td class=name><b>Penn Wharton Budget Model</b></td><td>Realized effective rate from USITC DataWeb customs data, national aggregate with partner and product breakdowns. Research output, revised as published.</td>'
        '<td>Irregular updates</td><td>7.1% for June 2026 (post of August 10, 2026; China 23.2%, steel and aluminum 40.9%, vehicles 13.2%)</td></tr>'
        '<tr><td class=name><b>Yale Budget Lab</b></td><td>Statutory: the average tariff rate implied by policy as written, applied to trade weights, including actions announced but not yet collected. Measures the policy, not the border.</td>'
        '<td>Updated with each policy action</td><td><a href="https://budgetlab.yale.edu/topic/trade">budgetlab.yale.edu</a> (statutory, not comparable one to one)</td></tr>'
        '<tr><td class=name><b>Treasury customs receipts</b></td><td>Cash deposited into the Treasury as customs duties, net of refunds, on a cash-timing basis (Monthly Treasury Statement).</td>'
        '<td>Monthly</td><td><a href="https://fiscaldata.treasury.gov/">fiscaldata.treasury.gov</a> (dollars, not a rate)</td></tr>'
        '</tbody></table></div>'
        '<h2>Why the numbers differ</h2>'
        '<ul>'
        '<li><b>Paper versus border.</b> A statutory rate counts every duty the law imposes. A realized rate counts what was assessed on the goods that actually entered: exemptions, USMCA carve-outs, exclusions and trade shifting away from the highest rates all lower it. The gap is information, not error.</li>'
        '<li><b>Calculated duty versus cash.</b> ETRX uses the duty fixed at entry. Cash receipts arrive later and are reduced by refunds; after the Supreme Court struck down the IEEPA tariffs in February 2026, a refund process exceeding $100B makes cash-based measures hard to read for years. Calculated duty is immune to it.</li>'
        '<li><b>Baskets.</b> ETRX steel (HS 72 and 73, all origins) printed ' + pct(steel["rate"]) + ' in ' + dm + '; Penn Wharton groups steel with aluminum. ETRX publishes vehicles per origin (EU, Mexico, Canada); Penn Wharton for all origins. Same data, different cuts.</li>'
        '<li><b>Revisions.</b> Census revises trade data. ETRX never restates a first print and publishes revisions separately; research outputs generally republish the revised figure.</li>'
        '<li><b>Coverage.</b> ETRX uses imports for consumption and excludes HS chapters 98 and 99 and AD/CVD duties. Aggregates that include them differ by construction.</li>'
        '</ul>'
        '<p class=muted>External figures are quoted with their publication date and never restated by ETRX. Reproduce any ETRX value on the <a href="verify.html">verify page</a>.</p>'
        '</section>')
    return shell("Reconciliation", "reconcile.html", body, latest, description="How ETRX differs from Penn Wharton, Yale Budget Lab and Treasury receipts, and why.")


def page_press(latest):
    head = next(s for s in latest["series"] if s["id"] == "ETRX-US")
    dm = month_name(latest["data_month"])
    boiler = ("ETRX, the US Effective Tariff Rate Index, is an independent, rules-based monthly "
              "measure of the duty rate actually paid on US imports — calculated duties as a share "
              "of customs value — by country of origin and product chapter, computed from official "
              "US Census Bureau trade data. The index prints within a day of each Census trade "
              "release, publishes its full methodology, and never restates a settled value.")
    body = """
<header class=mast><h1>Press</h1>
<p class=sub>Everything needed to cite, quote or chart the index. Charts and data are free
to republish with attribution.</p></header>
<section class=prose>
<h2>Latest print</h2>
<p>%(dm)s: headline effective tariff rate <b>%(rate)s</b> (%(delta)s month over month).
The full table is on the <a href="index.html">index page</a>; every series has a
downloadable chart with the credit baked in.</p>
<h2>Boilerplate</h2>
<div class=cite>%(boiler)s</div>
%(cite)s
<h2>Chart pack</h2>
<p><a href="charts/etrx-us.png">Headline, full history (PNG)</a> · all series:
<code>charts/&lt;series-id&gt;.png</code>, e.g. <a href="charts/etrx-cn-85.png">China electronics</a>,
<a href="charts/etrx-steel.png">steel</a>, <a href="charts/etrx-ca-76.png">Canadian aluminum</a>.</p>
<h2>Wordmark</h2>
<p>The wordmark is the word ETRX set in a neutral sans-serif at weight 600. No logo file is
required; please do not recolor it.</p>
<h2>Contact</h2>
<p>%(contact)s Briefings on a published print, the methodology or the history are available on
request. No unpublished index value is shared with anyone before publication — including under
embargo — because the values settle financial contracts.</p>
</section>
""" % {"dm": esc(dm), "rate": pct(head["rate"]), "delta": bps(head["delta_bps"]),
       "boiler": esc(boiler), "cite": cite_block(latest), "contact": contact_line()}
    return shell("Press — ETRX", "press.html", body, latest)


def page_audit(latest, audit_md):
    body = """
<header class=mast><h1>Audit log</h1>
<p class=sub>The administrator's append-only record of every verification, defect, fix and decision
— including decisions to change nothing. Rulebook §8 and §11 commit to keeping it public; this is
it, published verbatim from the engine repository on every print.</p></header>
<section class=prose>%s</section>
""" % md_to_html(audit_md)
    return shell("Audit log — ETRX", "about.html", body, latest)


def page_revisions(latest, revisions):
    if not revisions:
        table = ("<p class=chapsub>No revisions logged yet. Backfilled history embeds Census revisions "
                 "to date; the revision log begins with the first live print (see calendar).</p>")
    else:
        rows = "".join(
            "<tr><td class=name>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (esc(r["data_month"]), esc(r["series_id"]), pct(r["rate"]), esc(r["vintage_date"]))
            for r in revisions
        )
        table = ('<div style="overflow-x:auto"><table><thead><tr><th>Data month</th><th>Series</th>'
                 '<th>Revised rate</th><th>Vintage</th></tr></thead><tbody>%s</tbody></table></div>' % rows)
    body = """
<header class=mast><h1>Revisions</h1>
<p class=sub>Census revises recent months with each release and restates a full year each
summer. ETRX records what later vintages would have said — and never changes the settled
first print. This log is the settlement discipline made visible.</p></header>
<section>%s</section>
""" % table
    return shell("Revisions — ETRX", "revisions.html", body, latest)


# ---- machine-readable -----------------------------------------------------------------------
def llms_txt(latest):
    head = next(s for s in latest["series"] if s["id"] == "ETRX-US")
    lines = [
        "# ETRX — US Effective Tariff Rate Index",
        "",
        "> A rules-based monthly index of the realized effective US tariff rate — calculated duties "
        "as a share of the customs value of US imports for consumption — by country of origin and HS "
        "chapter, computed from official US Census Bureau trade data. First print settles; revisions "
        "are logged, never restated. Free to cite with attribution.",
        "",
        "Latest print: %s — headline effective tariff rate %s (%s month over month). Next print: %s."
        % (month_name(latest["data_month"]), pct(head["rate"]), bps(head["delta_bps"]),
           latest["next_print"]["release"]),
        "",
        "## Latest values (%s)" % month_name(latest["data_month"]),
    ]
    for s in latest["series"]:
        lines.append("- %s (%s): %s effective rate, %s vs prior month" % (
            s["label"], s["id"], pct(s["rate"]), bps(s["delta_bps"])))
    lines += [
        "",
        "## Data",
        "- Settlement panel (CSV): %s/etrx.csv" % SITE["url"],
        "- Latest print (JSON): %s/latest.json" % SITE["url"],
        "- Per-series JSON: %s/series/<series-id-lowercase>.json" % SITE["url"],
        "- Charts (PNG/SVG, credited): %s/charts/<series-id-lowercase>.png" % SITE["url"],
        "",
        "## Methodology",
        "- Rulebook: %s/methodology.html" % SITE["url"],
        "- Verify a number from source data: %s/verify.html" % SITE["url"],
        "- Formula: effective rate = CAL_DUT_MO / CON_VAL_MO (Census International Trade API, imports "
        "for consumption). Headline excludes HS chapters 98 and 99. Calculated duty excludes "
        "antidumping/countervailing duties.",
        "",
        "## Citation",
        "- Cite as: ETRX — US Effective Tariff Rate Index, <month> print, %s" % SITE["url"],
        "- License: %s" % SITE["license_short"],
        "",
        "## Pages",
        "- Index: %s/" % SITE["url"],
        "- Series: %s/series.html" % SITE["url"],
        "- Release calendar: %s/calendar.html" % SITE["url"],
        "- About: %s/about.html" % SITE["url"],
        "- Press: %s/press.html" % SITE["url"],
    ]
    return "\n".join(lines) + "\n"


def series_json(latest, s, history, st):
    return json.dumps(
        {
            "id": s["id"], "label": s["label"], "note": SERIES_NOTES.get(s["id"], ""),
            "index": "ETRX", "source": latest["source"], "rulebook": SITE["url"] + "/methodology.html",
            "latest": {k: s[k] for k in ("rate", "prior_rate", "delta_bps", "rate_dutiable",
                                          "duty_free_share", "first_print_vintage", "vintage_note")},
            "data_month": latest["data_month"], "peak": st.get("peak"), "peak_month": st.get("peak_m"),
            "history": [[m, r] for m, r in history.get(s["id"], [])],
            "history_columns": ["data_month", "rate"],
            "license": SITE["license_short"],
        },
        indent=1, sort_keys=True,
    )


# ---- assembly ------------------------------------------------------------------------------------
def render_all(latest, history, revisions, schedule, rulebook_md, raw_latest_rows):
    """Returns {relative path: content}. raw_latest_rows: {series_id: ledger row} for the latest month."""
    stats = {}
    for s in latest["series"]:
        pts = history.get(s["id"], [])
        row = raw_latest_rows.get(s["id"], {})
        st = {"con_val": row.get("con_val"), "cal_dut": row.get("cal_dut"),
              "defn": SERIES_NOTES.get(s["id"], "")}
        if pts:
            pm, pv = max(pts, key=lambda p: p[1])
            lm, lv = min(pts, key=lambda p: p[1])
            st.update({"peak": pv, "peak_m": pm, "low": lv, "low_m": lm})
        stats[s["id"]] = st
    cn = raw_latest_rows.get("ETRX-CN-85", {})
    sample = {
        "series_id": "ETRX-CN-85", "label": "China — electronics (HS 85)", "cty": "5700",
        "cty_name": "China", "chapter": "85", "month": latest["data_month"],
        "con_val": cn.get("con_val", 0), "cal_dut": cn.get("cal_dut", 0), "rate": cn.get("rate", 0.0),
    }
    methodology = page_methodology(latest, rulebook_md)
    audit_md = ""
    audit_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AUDIT.md")
    if os.path.exists(audit_path):
        audit_md = open(audit_path).read()
    out = {
        "index.html": page_index(latest, history),
        "series.html": page_series_list(latest, history),
        "methodology.html": methodology,
        # etrxindex.com/rulebook — the canonical link used in licensing material.
        # Pages serves /rulebook from rulebook.html; the directory form redirects
        # in case a host resolves the directory first (relative links would break).
        "rulebook.html": methodology,
        "rulebook/index.html": (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<title>ETRX Rulebook</title><link rel="canonical" href="%s/methodology.html">'
            '<meta http-equiv="refresh" content="0; url=../methodology.html">'
            '</head><body><p><a href="../methodology.html">ETRX Rulebook</a></p></body></html>\n'
            % SITE["url"]
        ),
        "verify.html": page_verify(latest, sample),
        "data.html": page_data(latest),
        "calendar.html": page_calendar(latest, schedule),
        "about.html": page_about(latest),
        "press.html": page_press(latest),
        "revisions.html": page_revisions(latest, revisions),
        "audit.html": page_audit(latest, audit_md),
        "reconcile.html": page_reconcile(latest),
        "llms.txt": llms_txt(latest),
        "CNAME": SITE["domain"] + "\n",
        "robots.txt": "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % SITE["url"],
    }
    for s in latest["series"]:
        sid = s["id"]
        out["series/%s.html" % slug(sid)] = page_series(latest, history, s, stats)
        out["series/%s.json" % slug(sid)] = series_json(latest, s, history, stats[sid])
        pts = history.get(sid, [])
        comp = history.get("ETRX-US-INCL", []) if sid == "ETRX-US" else None
        sub = "%s · %s print: %s (%s month over month)" % (
            sid, month_name(latest["data_month"]), pct(s["rate"]), bps(s["delta_bps"]))
        out["charts/%s.svg" % slug(sid)] = standalone_chart_svg(s["label"], sub, pts, comp)
    notes = load_notes()
    out["notes/index.html"] = page_notes_index(latest, notes)
    for n in notes:
        out["notes/%s.html" % n["slug"]] = page_note(latest, n)
    pages = sorted(p for p in out if p.endswith(".html") and not p.startswith("rulebook/"))
    out["sitemap.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join("  <url><loc>%s/%s</loc><lastmod>%s</lastmod></url>\n"
                  % (SITE["url"], "" if p == "index.html" else p, latest["generated"][:10])
                  for p in pages)
        + "</urlset>\n")
    return out


if __name__ == "__main__":
    import index_build as ib

    prints = ib.read_prints()
    if not prints:
        raise SystemExit("FATAL: prints.jsonl is empty — nothing to render.")
    ib.publish(prints, dry_run=False)
    print("preview rendered into", ib.DOCS_DIR)
