#!/usr/bin/env python3
"""
build_book.py -- render the MAYA migration guide (content.py) to a polished,
self-contained landscape PDF via headless Chrome (Playwright page.pdf()).

  python build_book.py            -> MAYA_Migration_Guide.pdf (+ book.html)
  python build_book.py --html     -> only write book.html (no PDF)

All images are base64-embedded, so the PDF/HTML is fully portable.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content as C  # noqa: E402

PAGE_W, PAGE_H = 1280, 960
MAYA_T = "assets/maya-logo-trans.png"
NMB_T = "assets/nmb-logo-trans.png"
OUT_PDF = os.path.join(HERE, "MAYA_Migration_Guide.pdf")
OUT_HTML = os.path.join(HERE, "book.html")

_embed_cache: dict[str, str] = {}


def embed(rel):
    """Return a data: URI for an asset path relative to the book dir."""
    if rel in _embed_cache:
        return _embed_cache[rel]
    path = os.path.normpath(os.path.join(HERE, rel))
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    uri = f"data:{mime};base64,{data}"
    _embed_cache[rel] = uri
    return uri


def esc(s):
    return html.escape(str(s))


# ---------------------------------------------------------------- CSS
CSS = """
:root{
  --ink:#12203A; --ink2:#26344F; --muted:#5A6B84; --faint:#8794A8;
  --orange:#FB6514; --pink:#F0426B; --gold:#E8A400; --navy:#1F2A44;
  --line:#E3E8F0; --bg:#FFFFFF; --soft:#F5F7FB;
}
*{box-sizing:border-box; -webkit-print-color-adjust:exact; print-color-adjust:exact;}
html,body{margin:0;padding:0;}
body{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; color:var(--ink);}
@page{ size:1280px 960px; margin:0; }
.page{ position:relative; width:1280px; height:960px; overflow:hidden;
       background:var(--bg); page-break-after:always; }
.page:last-child{ page-break-after:auto; }
.pad{ position:absolute; inset:0; padding:78px 92px; }

.eyebrow{ text-transform:uppercase; letter-spacing:.22em; font-size:14px;
  font-weight:700; color:var(--orange); }
h1.title{ font-size:46px; line-height:1.06; font-weight:800; letter-spacing:-.01em;
  margin:12px 0 0; max-width:1000px; }
h1.title.sm{ font-size:38px; }
.rule{ height:4px; width:96px; margin:22px 0 26px; border-radius:3px;
  background:linear-gradient(90deg,var(--orange),var(--pink)); }
p.body{ font-size:19px; line-height:1.55; color:var(--ink2); margin:0 0 16px; max-width:900px; }
ul.body,ol.body{ font-size:19px; line-height:1.5; color:var(--ink2); margin:0 0 16px; padding-left:26px; max-width:900px;}
ul.body li,ol.body li{ margin:0 0 10px; }
.quote{ border-left:5px solid var(--orange); padding:6px 0 6px 22px; margin:6px 0 18px;
  font-size:22px; line-height:1.45; font-style:italic; color:var(--ink); max-width:900px;}
.signoff{ font-size:18px; font-style:italic; color:var(--muted); margin-top:8px;}

.footer{ position:absolute; left:92px; right:92px; bottom:34px; display:flex;
  justify-content:space-between; align-items:center; font-size:12.5px;
  color:var(--faint); letter-spacing:.02em; }
.footer .dot{ color:var(--orange); }
.pgnum{ font-weight:700; color:var(--muted); }

/* ---- BOOK COVER: technical blueprint (distinct from photo/comic/light covers) ---- */
.bcover{ position:absolute; inset:0; overflow:hidden;
  background:radial-gradient(1200px 820px at 76% 10%,#17335F 0%,#0C1B36 45%,#06112A 100%); }
.bcover .grid{ position:absolute; inset:0;
  background-image:linear-gradient(rgba(120,190,255,.10) 1px,transparent 1px),
    linear-gradient(90deg,rgba(120,190,255,.10) 1px,transparent 1px);
  background-size:54px 54px; }
.bcover .grid.fine{ background-image:linear-gradient(rgba(120,190,255,.05) 1px,transparent 1px),
    linear-gradient(90deg,rgba(120,190,255,.05) 1px,transparent 1px);
  background-size:18px 18px; }
.bcover .glow{ position:absolute; right:-160px; top:-140px; width:560px; height:560px;
  border-radius:50%; background:radial-gradient(circle,#1E63C8 0%,transparent 66%); opacity:.55; }
.bcover .logos{ position:absolute; top:64px; left:92px; right:92px; display:flex;
  justify-content:space-between; align-items:center; }
.bcover .logos img{ height:56px; }
.bcover .hero{ position:absolute; left:96px; right:96px; top:288px; }
.bcover .kick{ color:#79D0FF; letter-spacing:.34em; font-weight:800; font-size:16px;
  text-transform:uppercase; }
.bcover h1{ margin:12px 0 0; font-size:158px; line-height:.88; font-weight:900;
  letter-spacing:-.02em; color:rgba(127,209,255,.06); -webkit-text-stroke:2.5px #8ED0FF;
  text-shadow:0 0 40px rgba(30,99,200,.4); }
.bcover h2{ margin:20px 0 0; font-size:38px; font-weight:600; color:#EAF3FF;
  max-width:840px; line-height:1.12; }
.bcover .pill{ display:inline-block; margin-top:26px; padding:12px 24px; border-radius:8px;
  background:rgba(20,44,84,.6); border:1.5px solid #4FA8E8; color:#CDE8FF; font-weight:800;
  font-size:18px; letter-spacing:.02em; }
.bcover .schema{ position:absolute; left:96px; right:96px; bottom:158px; display:flex;
  align-items:center; }
.bcover .node{ border:1.5px solid #7FC7F5; color:#DCEFFF; border-radius:11px;
  padding:11px 18px; font-size:15px; font-weight:800; background:rgba(18,40,80,.55);
  white-space:nowrap; }
.bcover .node.mid{ border-color:#FFB05C; color:#FFE0C2; background:rgba(60,30,10,.5);
  box-shadow:0 0 0 3px rgba(251,101,20,.25); }
.bcover .link{ flex:1; height:2px; margin:0 12px;
  background:repeating-linear-gradient(90deg,#6FB6E8 0 9px,transparent 9px 18px); }
.bcover .byline{ position:absolute; left:96px; right:96px; bottom:64px; color:#CFE0F5; }
.bcover .byline .nm{ font-size:26px; font-weight:900; color:#EAF3FF; }
.bcover .byline .hl{ font-size:15px; color:#9CB6D6; margin-top:3px; max-width:780px; }
.bcover .byline .ed{ position:absolute; right:0; bottom:2px; font-size:13px; color:#7E97BC;
  letter-spacing:.16em; text-transform:uppercase; }

/* cover */
.cover{ position:absolute; inset:0; background-size:cover; background-position:center; }
.cover .veil{ position:absolute; inset:0;
  background:linear-gradient(90deg,rgba(8,12,22,.35) 0%,rgba(8,12,22,.15) 40%,rgba(8,12,22,.62) 100%);}
.cover .logos{ position:absolute; top:64px; left:92px; right:92px; display:flex;
  justify-content:space-between; align-items:center; }
.cover .logos img{ height:60px; }
.cover .hero{ position:absolute; left:92px; right:92px; top:300px; }
.cover .kick{ color:#FFD9A8; letter-spacing:.34em; font-weight:700; font-size:16px;
  text-transform:uppercase; }
.cover h1{ margin:8px 0 0; font-size:150px; line-height:.9; font-weight:900;
  letter-spacing:-.02em; background:linear-gradient(92deg,#FFB05C,#FB6514 45%,#F0426B);
  -webkit-background-clip:text; background-clip:text; color:transparent; }
.cover h2{ margin:14px 0 0; font-size:40px; font-weight:600; color:#F3F6FF;
  letter-spacing:.01em; max-width:820px; line-height:1.12;}
.cover .pill{ display:inline-block; margin-top:26px; padding:13px 26px; border-radius:40px;
  background:linear-gradient(90deg,var(--gold),#F6B93B); color:#3A2600; font-weight:800;
  font-size:20px; letter-spacing:.01em; box-shadow:0 8px 30px rgba(232,164,0,.35);}
.cover .byline{ position:absolute; left:92px; right:92px; bottom:64px; color:#E7ECF6;}
.cover .byline .nm{ font-size:28px; font-weight:800; letter-spacing:.01em;}
.cover .byline .hl{ font-size:16px; color:#AEB9CE; margin-top:4px; max-width:760px;}
.cover .byline .ed{ position:absolute; right:0; bottom:2px; font-size:14px; color:#9AA6BC;
  letter-spacing:.16em; text-transform:uppercase;}

/* divider */
.divider{ position:absolute; inset:0;
  background:radial-gradient(1200px 700px at 12% 20%,#20305A 0%,#141F38 45%,#0C1425 100%);}
.divider .spine{ position:absolute; left:0; top:0; bottom:0; width:16px;
  background:linear-gradient(180deg,var(--orange),var(--pink)); }
.divider .wrap{ position:absolute; left:110px; right:110px; top:50%; transform:translateY(-52%);}
.divider .part{ color:var(--orange); font-weight:800; letter-spacing:.3em; font-size:20px;
  text-transform:uppercase;}
.divider h1{ color:#FFFFFF; font-size:78px; font-weight:900; letter-spacing:-.015em;
  margin:14px 0 0; line-height:1.0;}
.divider .sub{ color:#B9C4D8; font-size:22px; line-height:1.5; margin-top:22px; max-width:820px;}
.divider .mark{ position:absolute; right:110px; bottom:70px; height:40px; opacity:.95;}

/* figures */
.figwrap{ margin-top:6px; display:flex; align-items:center; justify-content:center;}
.figwrap img{ max-width:100%; max-height:560px; border:1px solid var(--line);
  border-radius:14px; box-shadow:0 18px 50px rgba(18,32,58,.12);}
.caption{ font-size:16px; color:var(--muted); font-style:italic; line-height:1.5;
  margin-top:16px; max-width:1040px;}
.note{ display:inline-block; margin-top:14px; background:var(--soft); border:1px solid var(--line);
  color:var(--ink2); font-size:15px; padding:10px 16px; border-radius:10px; }
.note b{ color:var(--orange);}

/* figure_text two-col */
.cols{ display:flex; gap:44px; margin-top:6px; align-items:center;}
.cols .txt{ flex:1;}
.cols .img{ flex:0 0 520px; display:flex; align-items:center;}
.cols .img img{ width:100%; border:1px solid var(--line); border-radius:14px;
  box-shadow:0 16px 44px rgba(18,32,58,.12);}

/* table */
table.mt{ width:100%; border-collapse:separate; border-spacing:0; margin-top:8px;
  font-size:17px; border:1px solid var(--line); border-radius:14px; overflow:hidden;}
table.mt th{ background:var(--navy); color:#fff; text-align:left; padding:16px 18px;
  font-size:15px; letter-spacing:.03em; text-transform:uppercase;}
table.mt td{ padding:15px 18px; vertical-align:top; color:var(--ink2); line-height:1.42;
  border-top:1px solid var(--line);}
table.mt tr:nth-child(even) td{ background:var(--soft);}
table.mt td.k{ font-weight:800; color:var(--ink); white-space:nowrap;}
.footnote{ font-size:15px; color:var(--muted); margin-top:18px; line-height:1.5; max-width:1040px;}
.footnote b{ color:var(--orange);}
.intro{ font-size:19px; color:var(--ink2); line-height:1.5; margin:0 0 18px; max-width:960px;}

/* stages grid */
.sgrid{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-top:8px;}
.scard{ border:1px solid var(--line); border-radius:14px; padding:16px 16px 14px;
  background:linear-gradient(180deg,#fff, #FbFcFe); position:relative; min-height:118px;}
.scard .no{ display:inline-flex; align-items:center; justify-content:center; width:34px;
  height:34px; border-radius:9px; color:#fff; font-weight:800; font-size:16px;
  background:linear-gradient(135deg,var(--orange),var(--pink));}
.scard .nm{ font-weight:800; font-size:17px; margin-top:12px; color:var(--ink);}
.scard .gt{ font-size:13.5px; color:var(--muted); margin-top:5px; line-height:1.35;}

/* screenshots */
.sh2{ display:flex; gap:34px; margin-top:8px;}
.sh2 .cell{ flex:1;}
.sh2 img{ width:100%; height:520px; object-fit:cover; object-position:top center;
  border:1px solid var(--line); border-radius:12px;
  box-shadow:0 14px 40px rgba(18,32,58,.12);}
.sh2 .cap{ font-size:15px; color:var(--muted); font-style:italic; margin-top:12px; line-height:1.45;}
.sh4{ display:grid; grid-template-columns:1fr 1fr; gap:20px 30px; margin-top:6px;}
.sh4 .cell img{ width:100%; height:262px; object-fit:cover; object-position:top center;
  border:1px solid var(--line); border-radius:11px;
  box-shadow:0 10px 30px rgba(18,32,58,.10);}
.sh4 .cap{ font-size:14px; color:var(--muted); margin-top:8px; font-weight:600;}

/* benchmark */
.bm{ position:absolute; top:34px; right:92px; height:40px; mix-blend-mode:multiply;}
.bmrow{ display:flex; gap:30px; margin-top:6px; align-items:flex-end;}
.bmrow .big{ flex:1.42; }
.bmrow .rad{ flex:1; }
.bmrow img{ width:100%; border:1px solid var(--line); border-radius:12px;
  box-shadow:0 12px 34px rgba(18,32,58,.10);}
.stats{ display:grid; grid-template-columns:repeat(4,1fr); gap:18px; margin-top:24px;}
.stat{ border:1px solid var(--line); border-radius:14px; padding:16px 18px; background:var(--soft);}
.stat .v{ font-size:34px; font-weight:900; letter-spacing:-.01em;
  background:linear-gradient(92deg,var(--orange),var(--pink));
  -webkit-background-clip:text; background-clip:text; color:transparent;}
.stat .l{ font-weight:800; font-size:15px; margin-top:4px; color:var(--ink);}
.stat .d{ font-size:13px; color:var(--muted); margin-top:2px;}

/* code */
.code{ background:#0E1626; color:#E7ECF6; border-radius:14px; padding:26px 28px;
  font-family:"SF Mono",Menlo,Consolas,monospace; font-size:18px; line-height:1.6;
  margin-top:6px; box-shadow:0 16px 44px rgba(12,20,38,.28); white-space:pre;}
.code .c{ color:#7F8CA6;}
.code .k{ color:#FFB05C;}

/* author */
.auth{ display:flex; gap:46px; margin-top:8px;}
.auth .left{ flex:0 0 340px;}
.auth .left img{ width:250px; height:250px; border-radius:50%; object-fit:cover;
  border:6px solid #fff; box-shadow:0 14px 40px rgba(18,32,58,.22);}
.auth .nm{ font-size:30px; font-weight:900; margin-top:20px;}
.auth .hl{ font-size:15px; color:var(--muted); margin-top:8px; line-height:1.45;}
.auth .meta{ font-size:14px; color:var(--ink2); margin-top:14px; line-height:1.7;}
.auth .meta b{ color:var(--orange);}
.auth .right{ flex:1;}
.auth .right p{ font-size:15.5px; line-height:1.5; color:var(--ink2); margin:0 0 12px;}
.chiprow{ display:flex; flex-wrap:wrap; gap:9px; margin-top:6px;}
.chip{ font-size:13px; font-weight:700; padding:7px 13px; border-radius:20px;
  background:var(--soft); border:1px solid var(--line); color:var(--ink2);}
.chip.o{ background:linear-gradient(90deg,#FFF1E6,#FFE9EF); border-color:#FBD9C6; color:#B4400F;}
.subh{ font-size:14px; font-weight:800; text-transform:uppercase; letter-spacing:.14em;
  color:var(--orange); margin:18px 0 8px;}

/* cta / back cover */
.cta{ position:absolute; inset:0;
  background:radial-gradient(1100px 700px at 85% 15%,#243560 0%,#151F39 48%,#0B1322 100%);}
.cta .pad2{ position:absolute; inset:0; padding:88px 100px;}
.cta h1{ color:#fff; font-size:56px; font-weight:900; letter-spacing:-.015em; margin:0;}
.cta .lead{ color:#FFD9A8; font-size:23px; font-weight:700; margin-top:22px; max-width:960px; line-height:1.4;}
.cta .txt{ color:#C3CDE0; font-size:18px; margin-top:14px; max-width:960px; line-height:1.55;}
.cta .grid{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:34px; max-width:1000px;}
.cta .card{ border:1px solid rgba(255,255,255,.14); border-radius:14px; padding:18px 22px;
  background:rgba(255,255,255,.04);}
.cta .card .t{ color:#fff; font-weight:800; font-size:18px;}
.cta .card .s{ color:#AEB9CE; font-size:15px; margin-top:5px; word-break:break-word;}
.cta .foot{ position:absolute; left:100px; right:100px; bottom:64px; display:flex;
  justify-content:space-between; align-items:flex-end;}
.cta .foot img{ height:46px;}
.cta .foot .cr{ color:#9AA6BC; font-size:14px; text-align:right;}
.cta .foot .cr b{ color:#E7ECF6;}
"""


# ---------------------------------------------------------------- block helpers
def render_blocks(blocks):
    out = []
    for kind, val in blocks:
        if kind == "p":
            out.append(f'<p class="body">{esc(val)}</p>')
        elif kind == "quote":
            out.append(f'<div class="quote">{esc(val)}</div>')
        elif kind == "bullets":
            lis = "".join(f"<li>{esc(x)}</li>" for x in val)
            out.append(f'<ul class="body">{lis}</ul>')
        elif kind == "num":
            lis = "".join(f"<li>{esc(x)}</li>" for x in val)
            out.append(f'<ol class="body">{lis}</ol>')
    return "".join(out)


def header(kicker, title, small=False):
    return (f'<div class="eyebrow">{esc(kicker)}</div>'
            f'<h1 class="title{" sm" if small else ""}">{esc(title)}</h1>'
            f'<div class="rule"></div>')


def footer(n):
    return (f'<div class="footer"><div>MAYA <span class="dot">&bull;</span> '
            f'Supersonic Migrate to Databricks Accelerator</div>'
            f'<div class="pgnum">{n:02d}</div></div>')


# ---------------------------------------------------------------- templates
def t_cover(p, n):
    # technical blueprint cover - deliberately unlike the light value-brief and the
    # bright comic story covers: navy blueprint grid, wireframe MAYA, schematic flow.
    return f"""
    <div class="bcover">
      <div class="grid"></div>
      <div class="grid fine"></div>
      <div class="glow"></div>
      <div class="logos">
        <img src="{embed(MAYA_T)}"><img src="{embed(NMB_T)}">
      </div>
      <div class="hero">
        <div class="kick">The Field Guide</div>
        <h1>MAYA</h1>
        <h2>Supersonic Migrate to Databricks Accelerator</h2>
        <div class="pill">{esc(C.SUBTITLE)}</div>
      </div>
      <div class="schema">
        <div class="node">Legacy Warehouse</div>
        <div class="link"></div>
        <div class="node mid">MAYA &bull; 12-gate AI swarm</div>
        <div class="link"></div>
        <div class="node">Databricks Lakehouse</div>
      </div>
      <div class="byline">
        <div class="nm">{esc(C.AUTHOR)}</div>
        <div class="hl">{esc(C.AUTHOR_HEADLINE)}</div>
        <div class="ed">{esc(C.EDITION)}</div>
      </div>
    </div>"""


def t_toc(p, n):
    rows = ""
    for part, title, desc in p["items"]:
        rows += (f'<div class="scard" style="min-height:0;padding:18px 20px">'
                 f'<span class="no" style="width:auto;height:auto;padding:6px 12px;'
                 f'border-radius:20px;font-size:13px;letter-spacing:.08em">{esc(part)}</span>'
                 f'<div class="nm" style="margin-top:10px">{esc(title)}</div>'
                 f'<div class="gt" style="font-size:14px">{esc(desc)}</div></div>')
    return f"""<div class="pad">
      {header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <div class="sgrid" style="grid-template-columns:1fr 1fr;gap:18px">{rows}</div>
      {footer(n)}
    </div>"""


def t_prose(p, n):
    signoff = f'<div class="signoff">{esc(p["signoff"])}</div>' if p.get("signoff") else ""
    return f"""<div class="pad">
      {header(p['kicker'], p['title'])}
      {render_blocks(p['body'])}
      {signoff}
      {footer(n)}
    </div>"""


def t_divider(p, n):
    return f"""
    <div class="divider">
      <div class="spine"></div>
      <div class="wrap">
        <div class="part">{esc(p['part'])}</div>
        <h1>{esc(p['title'])}</h1>
        <div class="sub">{esc(p['sub'])}</div>
      </div>
      <img class="mark" src="{embed(MAYA_T)}">
    </div>"""


def t_figure(p, n):
    note = f'<div class="note"><b>Key:</b> {esc(p["note"])}</div>' if p.get("note") else ""
    return f"""<div class="pad">
      {header(p['kicker'], p['title'], small=True)}
      <div class="figwrap"><img src="{embed(p['img'])}"></div>
      <div class="caption">{esc(p['caption'])}</div>
      {note}
      {footer(n)}
    </div>"""


def t_figure_text(p, n):
    return f"""<div class="pad">
      {header(p['kicker'], p['title'], small=True)}
      <div class="cols">
        <div class="txt">{render_blocks(p['body'])}</div>
        <div class="img"><img src="{embed(p['img'])}"></div>
      </div>
      {footer(n)}
    </div>"""


def t_table(p, n):
    ths = "".join(f"<th>{esc(c)}</th>" for c in p["columns"])
    trs = ""
    for row in p["rows"]:
        tds = "".join(f'<td class="{"k" if i==0 else ""}">{esc(c)}</td>'
                      for i, c in enumerate(row))
        trs += f"<tr>{tds}</tr>"
    fn = f'<div class="footnote"><b>Gate rule.</b> {esc(p["footnote"].split(":",1)[-1].strip())}</div>' if p.get("footnote") else ""
    return f"""<div class="pad">
      {header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <table class="mt"><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>
      {fn}
      {footer(n)}
    </div>"""


def t_stages(p, n):
    cards = ""
    for no, nm, gt in p["stages"]:
        cards += (f'<div class="scard"><span class="no">{esc(no)}</span>'
                  f'<div class="nm">{esc(nm)}</div><div class="gt">{esc(gt)}</div></div>')
    return f"""<div class="pad">
      {header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <div class="sgrid">{cards}</div>
      {footer(n)}
    </div>"""


def t_screens2(p, n):
    cells = ""
    for img, cap in p["imgs"]:
        cells += (f'<div class="cell"><img src="{embed(img)}">'
                  f'<div class="cap">{esc(cap)}</div></div>')
    return f"""<div class="pad">
      {header(p['kicker'], p['title'])}
      <div class="sh2">{cells}</div>
      {footer(n)}
    </div>"""


def t_screens4(p, n):
    cells = ""
    for img, cap in p["imgs"]:
        cells += (f'<div class="cell"><img src="{embed(img)}">'
                  f'<div class="cap">{esc(cap)}</div></div>')
    return f"""<div class="pad">
      {header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <div class="sh4">{cells}</div>
      {footer(n)}
    </div>"""


def t_benchmark(p, n):
    stats = ""
    for v, l, d in p["stats"]:
        stats += (f'<div class="stat"><div class="v">{esc(v)}</div>'
                  f'<div class="l">{esc(l)}</div><div class="d">{esc(d)}</div></div>')
    return f"""<div class="pad">
      <img class="bm" src="{embed(C.NMB_L)}">
      {header(p['kicker'], p['title'])}
      <div class="bmrow">
        <div class="big"><img src="{embed(p['mfvi'])}"></div>
        <div class="rad"><img src="{embed(p['radar'])}"></div>
      </div>
      <div class="stats">{stats}</div>
      <div class="footnote">{esc(p['note'])}</div>
      {footer(n)}
    </div>"""


def t_code(p, n):
    lines = []
    for ln in p["code"].split("\n"):
        if ln.strip().startswith("#"):
            lines.append(f'<span class="c">{esc(ln)}</span>')
        elif ln.strip() and not ln.startswith(" ") and ln.split(" ")[0] in (
                "git", "cd", "pip", "make", "python3"):
            head, _, rest = ln.partition(" ")
            lines.append(f'<span class="k">{esc(head)}</span> {esc(rest)}')
        else:
            lines.append(esc(ln))
    code = "\n".join(lines)
    return f"""<div class="pad">
      {header(p['kicker'], p['title'])}
      <div class="code">{code}</div>
      <div style="margin-top:22px">{render_blocks(p['body'])}</div>
      {footer(n)}
    </div>"""


def t_author(p, n):
    a = AUTHOR
    paras = "".join(f"<p>{esc(x)}</p>" for x in [a["about"][0], a["about"][1], a["about"][3]])
    interests = "".join(f'<span class="chip o">{esc(x)}</span>' for x in a["interests"])
    skills = "".join(f'<span class="chip">{esc(x)}</span>' for x in a["top_skills"])
    follows = "".join(f'<span class="chip">{esc(x)}</span>' for x in a.get("follows", []))
    return f"""<div class="pad">
      {header(p['kicker'], a['name'])}
      <div class="auth">
        <div class="left">
          <img src="{embed(C.HEAD)}">
          <div class="nm">{esc(a['name'])}</div>
          <div class="hl">{esc(a['headline'])}</div>
          <div class="meta">
            <b>&#9679;</b> {esc(a['current'])} &nbsp; | &nbsp; {esc(a['location'])}<br>
            <b>&#9679;</b> {esc(a['network'])}<br>
            <b>&#9679;</b> {esc(a['contact_email'])}
          </div>
        </div>
        <div class="right">
          {paras}
          <div class="subh">Focus &amp; interests</div>
          <div class="chiprow">{interests}</div>
          <div class="subh">Top skills</div>
          <div class="chiprow">{skills}</div>
          <div class="subh">Follows</div>
          <div class="chiprow">{follows}</div>
        </div>
      </div>
      {footer(n)}
    </div>"""


def t_cta(p, n):
    cards = ""
    for t, s in p["ctas"]:
        cards += (f'<div class="card"><div class="t">{esc(t)}</div>'
                  f'<div class="s">{esc(s)}</div></div>')
    return f"""
    <div class="cta">
      <div class="pad2">
        <h1>{esc(p['title'])}</h1>
        <div class="lead">{esc(p['lead'])}</div>
        <div class="txt">{esc(p['body'])}</div>
        <div class="grid">{cards}</div>
        <div class="foot">
          <img src="{embed(MAYA_T)}">
          <div class="cr">Created by <b>{esc(C.AUTHOR)}</b><br>
            {esc(C.EDITION)} &nbsp;&bull;&nbsp; Apache-2.0 open source</div>
        </div>
      </div>
    </div>"""


TEMPLATES = {
    "cover": t_cover, "toc": t_toc, "prose": t_prose, "divider": t_divider,
    "figure": t_figure, "figure_text": t_figure_text, "table": t_table,
    "stages": t_stages, "screens2": t_screens2, "screens4": t_screens4,
    "benchmark": t_benchmark, "code": t_code, "author": t_author, "cta": t_cta,
}

AUTHOR = {}


def build_html():
    global AUTHOR
    with open(os.path.join(HERE, "author.json"), encoding="utf-8") as f:
        AUTHOR = json.load(f)
    pages_html = []
    for i, p in enumerate(C.PAGES, start=1):
        fn = TEMPLATES[p["tpl"]]
        pages_html.append(f'<section class="page">{fn(p, i)}</section>')
    body = "\n".join(pages_html)
    return (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>MAYA - Supersonic Migrate to Databricks Accelerator</title>"
            f"<style>{CSS}</style></head><body>{body}</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", action="store_true", help="write book.html only")
    args = ap.parse_args()
    doc = build_html()
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {OUT_HTML} ({len(doc)//1024} KB, {len(C.PAGES)} pages)")
    if args.html:
        return 0
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome")
        pg = b.new_page()
        pg.goto("file://" + OUT_HTML, wait_until="networkidle")
        pg.pdf(path=OUT_PDF, width=f"{PAGE_W}px", height=f"{PAGE_H}px",
               print_background=True, margin={"top": "0", "bottom": "0",
                                              "left": "0", "right": "0"})
        b.close()
    print(f"wrote {OUT_PDF} ({os.path.getsize(OUT_PDF)//1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
