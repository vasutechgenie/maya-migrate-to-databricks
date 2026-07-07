#!/usr/bin/env python3
"""
build_value_brief.py -- render the MAYA VALUE BRIEF (value_content.py) to a polished
landscape PDF. Reuses build_book.py's engine (CSS, helpers, cover/table/author/cta
templates) and adds punchy chart/table templates: KPI hero, bar comparison, stacked
cost, phased add-on flow, coverage grid, maintainability, and complexity cards.

  python build_value_brief.py          -> MAYA_Value_Brief.pdf (+ value_brief.html)
  python build_value_brief.py --html   -> only write value_brief.html

Charts are pure HTML/CSS (Chrome renders them into the PDF), so no plotting deps.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_book as BB  # noqa: E402  (engine: CSS, helpers, some templates)
import value_content as VC  # noqa: E402

OUT_PDF = os.path.join(HERE, "MAYA_Value_Brief.pdf")
OUT_HTML = os.path.join(HERE, "value_brief.html")
PAGE_W, PAGE_H = BB.PAGE_W, BB.PAGE_H

emb, esc = BB.embed, BB.esc


# ---------------------------------------------------------------- extra CSS
EXTRA_CSS = """
/* value cover kicker override */
.cover .kickv{ color:#FFD9A8; letter-spacing:.34em; font-weight:700; font-size:16px;
  text-transform:uppercase; }

/* KPI hero */
.lead{ font-size:21px; line-height:1.5; color:var(--ink2); margin:2px 0 22px; max-width:1040px;}
.kstats{ display:grid; grid-template-columns:repeat(4,1fr); gap:20px; margin-top:6px;}
.kstat{ border:1px solid var(--line); border-radius:16px; padding:22px 22px 20px;
  background:linear-gradient(180deg,#fff,#F7F9FD); box-shadow:0 10px 30px rgba(18,32,58,.06);}
.kstat .v{ font-size:40px; font-weight:900; letter-spacing:-.01em; line-height:1.02;
  background:linear-gradient(92deg,var(--orange),var(--pink));
  -webkit-background-clip:text; background-clip:text; color:transparent;}
.kstat .l{ font-weight:800; font-size:16px; margin-top:8px; color:var(--ink);}
.kstat .d{ font-size:14px; color:var(--muted); margin-top:3px; line-height:1.35;}
.banner{ margin-top:26px; border-radius:14px; padding:18px 24px; font-size:19px;
  font-weight:800; color:#3A2600; letter-spacing:.005em;
  background:linear-gradient(90deg,#FFE9C2,#FFD9A8);}

/* bar comparison */
.bars{ display:flex; flex-direction:column; gap:26px; margin-top:12px;}
.barrow .top{ display:flex; justify-content:space-between; align-items:baseline;
  margin-bottom:10px;}
.barrow .lab{ font-weight:800; font-size:19px; color:var(--ink);}
.barrow .red{ font-weight:800; font-size:16px; color:#B4400F;
  background:linear-gradient(90deg,#FFF1E6,#FFE9EF); border:1px solid #FBD9C6;
  padding:5px 13px; border-radius:20px;}
.track{ position:relative; height:34px; margin:7px 0; }
.fill{ position:absolute; left:0; top:0; bottom:0; border-radius:8px; display:flex;
  align-items:center; padding:0 14px; color:#fff; font-weight:800; font-size:15px;
  white-space:nowrap; min-width:64px;}
.fill.trad{ background:linear-gradient(90deg,#8794A8,#5A6B84);}
.fill.maya{ background:linear-gradient(90deg,var(--orange),var(--pink));
  box-shadow:0 6px 18px rgba(251,101,20,.28);}
.tag{ position:absolute; left:0; top:-2px; font-size:12.5px; font-weight:800;
  letter-spacing:.08em; text-transform:uppercase; color:var(--faint);}

/* stacked cost */
.stackwrap{ display:flex; gap:60px; margin-top:6px; align-items:stretch;}
.stackcols{ flex:1; display:flex; gap:70px; align-items:flex-end;
  justify-content:center; padding-top:8px;}
.col{ display:flex; flex-direction:column; align-items:center;}
.colbar{ width:190px; display:flex; flex-direction:column; border-radius:12px;
  overflow:hidden; box-shadow:0 16px 40px rgba(18,32,58,.14);}
.seg{ color:#fff; font-weight:700; font-size:13.5px; display:flex; align-items:center;
  justify-content:center; text-align:center; padding:0 8px; line-height:1.15;}
.coltot{ font-weight:900; font-size:22px; margin-bottom:10px; color:var(--ink);}
.colnm{ margin-top:12px; font-weight:800; font-size:18px; color:var(--ink2);
  text-transform:uppercase; letter-spacing:.06em;}
.savebox{ flex:0 0 320px; align-self:center; border:1px solid var(--line);
  border-radius:18px; padding:30px 26px; text-align:center;
  background:radial-gradient(400px 240px at 50% 0%,#FFF3E9,#fff);}
.savebox .big{ font-size:64px; font-weight:900; letter-spacing:-.02em; line-height:1;
  background:linear-gradient(92deg,var(--orange),var(--pink));
  -webkit-background-clip:text; background-clip:text; color:transparent;}
.savebox .sub{ font-size:18px; font-weight:800; color:var(--ink); margin-top:8px;}
.legend{ display:flex; gap:18px; flex-wrap:wrap; margin-top:20px; justify-content:center;}
.legend .it{ display:flex; align-items:center; gap:8px; font-size:14px; color:var(--ink2);}
.legend .sw{ width:14px; height:14px; border-radius:4px;}

/* phased flow */
.flow{ display:flex; align-items:stretch; gap:0; margin-top:10px;}
.pcard{ flex:1; border:1px solid var(--line); border-radius:16px; padding:22px 22px;
  background:linear-gradient(180deg,#fff,#F7F9FD); box-shadow:0 10px 28px rgba(18,32,58,.07);}
.pcard .no{ display:inline-flex; align-items:center; justify-content:center; width:40px;
  height:40px; border-radius:11px; color:#fff; font-weight:900; font-size:19px;
  background:linear-gradient(135deg,var(--orange),var(--pink));}
.pcard .nm{ font-weight:900; font-size:22px; margin-top:14px; color:var(--ink);}
.pcard .tx{ font-size:15.5px; color:var(--ink2); margin-top:8px; line-height:1.45;}
.arrowc{ flex:0 0 58px; display:flex; align-items:center; justify-content:center;
  font-size:40px; color:var(--orange); font-weight:900;}
.chipbanner{ margin-top:24px; display:inline-block; border-radius:24px; padding:12px 22px;
  font-size:16px; font-weight:800; color:#0B4A2F;
  background:linear-gradient(90deg,#D9F5E6,#C2F0DA); border:1px solid #A7E3C6;}

/* coverage grid */
.cov{ display:grid; grid-template-columns:repeat(3,1fr); gap:18px; margin-top:8px;}
.covc{ border:1px solid var(--line); border-radius:14px; padding:20px 20px;
  background:linear-gradient(180deg,#fff,#FbFcFe); min-height:150px;}
.covc .h{ font-weight:900; font-size:19px; color:var(--ink);
  border-left:4px solid var(--orange); padding-left:12px;}
.covc .d{ font-size:15px; color:var(--ink2); margin-top:12px; line-height:1.45;}

/* maintainability */
.maint{ display:flex; gap:44px; margin-top:8px;}
.maint .pts{ flex:1.2; display:flex; flex-direction:column; gap:16px;}
.mpt{ border:1px solid var(--line); border-radius:13px; padding:16px 18px;
  background:var(--soft);}
.mpt .h{ font-weight:900; font-size:17.5px; color:var(--ink);}
.mpt .d{ font-size:14.5px; color:var(--ink2); margin-top:5px; line-height:1.42;}
.maint .side{ flex:1;}

/* complexity cards */
.ccards{ display:flex; gap:20px; margin-top:10px;}
.ccard{ flex:1; border:1px solid var(--line); border-radius:16px; padding:24px 22px;
  background:linear-gradient(180deg,#fff,#F7F9FD); box-shadow:0 10px 28px rgba(18,32,58,.07);}
.ccard .from{ font-size:15px; color:var(--muted); font-weight:700;}
.ccard .to{ font-size:24px; font-weight:900; color:var(--ink); margin-top:10px;
  line-height:1.12;}
.ccard .to b{ background:linear-gradient(92deg,var(--orange),var(--pink));
  -webkit-background-clip:text; background-clip:text; color:transparent;}
.ccard .d{ font-size:15px; color:var(--ink2); margin-top:14px; line-height:1.45;}
.ccard .ar{ font-size:22px; color:var(--orange); margin:8px 0 0;}
"""


def footer(n):
    return (f'<div class="footer"><div>MAYA <span class="dot">&bull;</span> '
            f'The Business Case &mdash; Value Brief</div>'
            f'<div class="pgnum">{n:02d}</div></div>')


def note(txt):
    return f'<div class="note"><b>Note:</b> {esc(txt)}</div>' if txt else ""


def footnote(txt):
    return f'<div class="footnote">{esc(txt)}</div>' if txt else ""


# ---------------------------------------------------------------- templates
def t_cover2(p, n):
    return f"""
    <div class="cover" style="background-image:url('{emb(VC.BG)}')">
      <div class="veil"></div>
      <div class="logos"><img src="{emb(BB.MAYA_T)}"><img src="{emb(BB.NMB_T)}"></div>
      <div class="hero">
        <div class="kickv">{esc(VC.KICK)}</div>
        <h1>MAYA</h1>
        <h2>The Business Case: Supersonic Migrate to Databricks</h2>
        <div class="pill">{esc(VC.SUBTITLE)}</div>
      </div>
      <div class="byline">
        <div class="nm">{esc(BB.C.AUTHOR)}</div>
        <div class="hl">{esc(BB.C.AUTHOR_HEADLINE)}</div>
        <div class="ed">{esc(BB.C.EDITION)}</div>
      </div>
    </div>"""


def t_kpi(p, n):
    cards = "".join(f'<div class="kstat"><div class="v">{esc(v)}</div>'
                    f'<div class="l">{esc(l)}</div><div class="d">{esc(d)}</div></div>'
                    for v, l, d in p["stats"])
    return f"""<div class="pad">
      {BB.header(p['kicker'], p['title'])}
      <div class="lead">{esc(p['lead'])}</div>
      <div class="kstats">{cards}</div>
      <div class="banner">{esc(p['banner'])}</div>
      {footer(n)}
    </div>"""


def t_bars(p, n):
    rows = ""
    for lab, tval, tpct, mval, mpct, red in p["bars"]:
        rows += f"""<div class="barrow">
          <div class="top"><div class="lab">{esc(lab)}</div>
            <div class="red">{esc(red)}</div></div>
          <div class="track"><div class="fill trad" style="width:{tpct}%">{esc(tval)}</div></div>
          <div class="track"><div class="fill maya" style="width:{max(mpct,4)}%">{esc(mval)}</div></div>
        </div>"""
    return f"""<div class="pad">
      {BB.header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <div class="bars">{rows}</div>
      {note(p.get('note'))}
      {footnote(p.get('footnote'))}
      {footer(n)}
    </div>"""


def t_stack(p, n):
    MAXPX = 360
    totals = [sum(v for _, v, _ in segs) for _, segs in p["cols"]]
    mx = max(totals) or 1
    cols_html = ""
    for (name, segs), tot in zip(p["cols"], totals):
        segs_html = ""
        for lab, v, color in segs:
            h = v / mx * MAXPX
            show = f"{esc(lab)}" if h >= 26 else ""
            segs_html += (f'<div class="seg" style="height:{h:.1f}px;background:{color}">'
                          f'{show}</div>')
        cols_html += f"""<div class="col">
          <div class="coltot">{tot}</div>
          <div class="colbar">{segs_html}</div>
          <div class="colnm">{esc(name)}</div>
        </div>"""
    legend = "".join(
        f'<div class="it"><span class="sw" style="background:{c}"></span>{esc(l)}</div>'
        for l, c in [("Labor", "#5A6B84"), ("Software / licensing", "#8794A8"),
                     ("Cloud / compute", "#0EA5C6"), ("Rework + overruns", "#E23B3B")])
    return f"""<div class="pad">
      {BB.header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <div class="stackwrap">
        <div class="stackcols">{cols_html}</div>
        <div class="savebox"><div class="big">{esc(p['callout'])}</div>
          <div class="sub">{esc(p['callout_sub'])}</div></div>
      </div>
      <div class="legend">{legend}</div>
      {footnote(p.get('footnote'))}
      {footer(n)}
    </div>"""


def t_phased(p, n):
    cells = []
    for no, nm, tx in p["phases"]:
        cells.append(f'<div class="pcard"><span class="no">{esc(no)}</span>'
                     f'<div class="nm">{esc(nm)}</div><div class="tx">{esc(tx)}</div></div>')
    flow = '<div class="arrowc">&rarr;</div>'.join(cells)
    return f"""<div class="pad">
      {BB.header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <div class="flow">{flow}</div>
      <div class="chipbanner">{esc(p['chip'])}</div>
      {footnote(p.get('footnote'))}
      {footer(n)}
    </div>"""


def t_grid(p, n):
    cards = "".join(f'<div class="covc"><div class="h">{esc(h)}</div>'
                    f'<div class="d">{esc(d)}</div></div>' for h, d in p["cards"])
    return f"""<div class="pad">
      {BB.header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <div class="cov">{cards}</div>
      {footer(n)}
    </div>"""


def t_maintain(p, n):
    pts = "".join(f'<div class="mpt"><div class="h">{esc(h)}</div>'
                  f'<div class="d">{esc(d)}</div></div>' for h, d in p["points"])
    ths = "<th>Aspect</th><th>Traditional</th><th>With MAYA</th>"
    trs = ""
    for row in p["mrows"]:
        tds = "".join(f'<td class="{"k" if i==0 else ""}">{esc(c)}</td>'
                      for i, c in enumerate(row))
        trs += f"<tr>{tds}</tr>"
    return f"""<div class="pad">
      {BB.header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <div class="maint">
        <div class="pts">{pts}</div>
        <div class="side"><table class="mt"><thead><tr>{ths}</tr></thead>
          <tbody>{trs}</tbody></table>
          {footnote(p.get('footnote'))}
        </div>
      </div>
      {footer(n)}
    </div>"""


def t_cards(p, n):
    cards = "".join(
        f'<div class="ccard"><div class="from">{esc(frm)}</div>'
        f'<div class="ar">&darr;</div>'
        f'<div class="to"><b>{esc(to)}</b></div>'
        f'<div class="d">{esc(d)}</div></div>' for frm, to, d in p["cards"])
    return f"""<div class="pad">
      {BB.header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <div class="ccards">{cards}</div>
      {footer(n)}
    </div>"""


def t_benchmark2(p, n):
    stats = "".join(f'<div class="stat"><div class="v">{esc(v)}</div>'
                    f'<div class="l">{esc(l)}</div><div class="d">{esc(d)}</div></div>'
                    for v, l, d in p["stats"])
    return f"""<div class="pad">
      <img class="bm" src="{emb(VC.NMB_L)}">
      {BB.header(p['kicker'], p['title'])}
      <div class="bmrow">
        <div class="big"><img src="{emb(p['mfvi'])}"></div>
        <div class="rad"><img src="{emb(p['radar'])}"></div>
      </div>
      <div class="stats">{stats}</div>
      <div class="footnote">{esc(p['note'])}</div>
      {footer(n)}
    </div>"""


# reuse the book engine's table/author/cta, but with the value-brief footer
def t_table(p, n):
    html = BB.t_table(p, n)
    return html.replace(BB.footer(n), footer(n))


def t_author(p, n):
    return BB.t_author(p, n).replace(BB.footer(n), footer(n))


TEMPLATES = {
    "cover2": t_cover2, "kpi": t_kpi, "table": t_table, "bars": t_bars,
    "stack": t_stack, "phased": t_phased, "grid": t_grid, "maintain": t_maintain,
    "cards": t_cards, "benchmark2": t_benchmark2, "author": t_author,
    "cta": BB.t_cta,
}


def build_html():
    with open(os.path.join(HERE, "author.json"), encoding="utf-8") as f:
        BB.AUTHOR = json.load(f)
    pages = []
    for i, p in enumerate(VC.PAGES, start=1):
        pages.append(f'<section class="page">{TEMPLATES[p["tpl"]](p, i)}</section>')
    body = "\n".join(pages)
    return (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>MAYA - The Business Case (Value Brief)</title>"
            f"<style>{BB.CSS}{EXTRA_CSS}</style></head><body>{body}</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", action="store_true")
    args = ap.parse_args()
    doc = build_html()
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {OUT_HTML} ({len(doc)//1024} KB, {len(VC.PAGES)} pages)")
    if args.html:
        return 0
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome")
        pg = b.new_page()
        pg.goto("file://" + OUT_HTML, wait_until="networkidle")
        pg.pdf(path=OUT_PDF, width=f"{PAGE_W}px", height=f"{PAGE_H}px",
               print_background=True,
               margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        b.close()
    print(f"wrote {OUT_PDF} ({os.path.getsize(OUT_PDF)//1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
