#!/usr/bin/env python3
"""
build_story.py -- render "MAYA - The Migration That Won Every Round" (story_content.py)
to a polished, self-contained landscape PDF, reusing the MAYA book engine (build_book.py)
for CSS, asset embedding, and shared templates.

  python build_story.py            -> MAYA_Migration_Story.pdf (+ story.html)
  python build_story.py --html     -> only write story.html (no PDF)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_book as BB          # noqa: E402  (engine: CSS, embed, esc, templates)
import story_content as S        # noqa: E402

esc = BB.esc
embed = BB.embed
header = BB.header
MAYA_T = BB.MAYA_T
NMB_T = BB.NMB_T

PAGE_W, PAGE_H = BB.PAGE_W, BB.PAGE_H
OUT_PDF = os.path.join(HERE, "MAYA_Migration_Story.pdf")
OUT_HTML = os.path.join(HERE, "story.html")

FOOTER_TXT = "MAYA &bull; The Migration That Won Every Round"


# ------------------------------------------------------------------ footer
def footer(n):
    return (f'<div class="footer"><div>MAYA <span class="dot">&bull;</span> '
            f'The Migration That Won Every Round</div>'
            f'<div class="pgnum">{n:02d}</div></div>')


def _refoot(html_str, n):
    """Swap the engine's book footer for the story footer on reused templates."""
    return html_str.replace(BB.footer(n), footer(n))


# ------------------------------------------------------------------ extra CSS
EXTRA_CSS = """
/* ---- STORY COVER: bright comic movie-poster (distinct from the dark covers) ---- */
.scover{ position:absolute; inset:0; overflow:hidden; background-size:cover;
  background-position:center; }
.scover .wash{ position:absolute; inset:0;
  background:radial-gradient(120% 80% at 50% 6%, rgba(255,255,255,.30) 0%,
    rgba(255,255,255,0) 42%),
    linear-gradient(180deg, rgba(20,12,30,0) 55%, rgba(20,12,30,.28) 100%); }
.scover .logos{ position:absolute; top:52px; left:74px; right:74px; display:flex;
  justify-content:space-between; align-items:center; z-index:4; }
.scover .logos .chip{ display:flex; align-items:center; gap:10px; padding:9px 16px;
  background:rgba(255,255,255,.92); border-radius:40px;
  box-shadow:0 8px 22px rgba(120,20,60,.28); }
.scover .logos .chip img{ height:30px; }
.scover .top{ position:absolute; left:0; right:0; top:92px; text-align:center; z-index:3;
  padding:0 60px; }
.scover .ribbon{ display:inline-block; padding:9px 24px; border-radius:40px;
  font-weight:900; letter-spacing:.22em; font-size:15px; text-transform:uppercase;
  color:#3A2600; background:linear-gradient(90deg,#FFE08A,#FFB347);
  border:3px solid #fff; box-shadow:0 10px 26px rgba(120,20,60,.35); }
.scover h1{ margin:18px auto 0; max-width:1120px; color:#fff; font-weight:900;
  font-size:70px; line-height:.98; letter-spacing:-.015em; text-transform:uppercase;
  -webkit-text-stroke:2.5px #221033;
  text-shadow:4px 5px 0 rgba(34,16,51,.55); }
.scover h1 .em{ -webkit-text-stroke:2.5px #221033; color:#FFE45E; }
.scover .maya{ margin-top:16px; display:inline-flex; align-items:center; gap:12px;
  color:#fff; font-weight:800; font-size:20px; letter-spacing:.02em;
  text-shadow:0 2px 8px rgba(34,16,51,.5); }
.scover .maya b{ font-size:27px; font-weight:900; letter-spacing:.04em; }
.scover .squad{ position:absolute; left:50%; bottom:112px; transform:translateX(-50%);
  width:700px; max-width:80%; z-index:2; border-radius:20px; border:7px solid #fff;
  box-shadow:0 22px 44px rgba(60,10,40,.42); }
.scover .byline{ position:absolute; left:74px; right:74px; bottom:40px; z-index:4;
  display:flex; justify-content:space-between; align-items:flex-end; color:#fff; }
.scover .byline .nm{ font-size:22px; font-weight:900;
  text-shadow:0 2px 8px rgba(34,16,51,.6); }
.scover .byline .hl{ font-size:13px; color:#FFE7D6; margin-top:2px; max-width:640px;
  text-shadow:0 1px 5px rgba(34,16,51,.6); }
.scover .byline .ed{ font-size:13px; font-weight:800; letter-spacing:.16em;
  text-transform:uppercase; color:#fff; text-shadow:0 1px 6px rgba(34,16,51,.6); }

/* story cover kicker override (legacy) */
.cover .kick.story{ color:#FFD9A8; }

/* cast */
.castbanner{ width:100%; height:210px; display:flex; align-items:center; justify-content:center;
  margin:2px 0 20px; }
.castbanner img{ height:210px; max-width:100%; object-fit:contain;
  filter:drop-shadow(0 14px 30px rgba(18,32,58,.16)); }
.castgrid{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
.castcard{ border:1px solid var(--line); border-radius:14px; padding:16px 18px;
  background:linear-gradient(180deg,#fff,#FbFcFe); min-height:132px; }
.castcard .role{ text-transform:uppercase; letter-spacing:.14em; font-size:12px;
  font-weight:800; color:var(--orange); }
.castcard .nm{ font-size:22px; font-weight:900; margin-top:4px; color:var(--ink); }
.castcard .ln{ font-size:14.5px; color:var(--muted); margin-top:8px; line-height:1.42; }

/* scene */
.scene{ display:flex; gap:40px; margin-top:4px; align-items:flex-start; }
.scene .txt{ flex:1; }
.scene .side{ flex:0 0 300px; display:flex; flex-direction:column; align-items:center; }
.scene .side img{ width:280px; height:280px; object-fit:contain;
  filter:drop-shadow(0 16px 34px rgba(18,32,58,.18)); }
.scene .qby{ font-size:16px; color:var(--muted); font-style:italic; margin:-6px 0 20px 22px; }

/* cli + ui two-column */
.cliui{ display:flex; gap:34px; margin-top:2px; align-items:stretch; }
.cliui .left{ flex:0 0 512px; display:flex; flex-direction:column; }
.cliui .lbl{ text-transform:uppercase; letter-spacing:.16em; font-size:12px; font-weight:800;
  color:var(--orange); margin-bottom:8px; }
.cliui .code{ margin-top:0; flex:1; font-size:16.5px; line-height:1.62; }
.cliui .right{ flex:1; display:flex; flex-direction:column; }
.cliui .right img{ width:100%; height:498px; object-fit:cover; object-position:top center;
  border:1px solid var(--line); border-radius:12px; box-shadow:0 14px 40px rgba(18,32,58,.12); }
.cliui .cap{ font-size:15px; color:var(--muted); font-style:italic; margin-top:12px; line-height:1.45; }
.cliui-intro{ font-size:18px; color:var(--ink2); line-height:1.5; margin:0 0 16px; max-width:1080px; }

/* award page */
.award{ position:absolute; inset:0;
  background:radial-gradient(1100px 720px at 82% 12%,#FFF3E6 0%,#FFF 46%),#fff; }
.award .band{ position:absolute; left:0; top:0; bottom:0; width:14px;
  background:linear-gradient(180deg,var(--gold),var(--orange),var(--pink)); }
.award .wrap{ position:absolute; inset:0; padding:70px 92px; display:flex; gap:52px; align-items:center; }
.award .hero{ flex:0 0 460px; display:flex; align-items:center; justify-content:center; }
.award .hero img{ width:460px; height:460px; object-fit:contain;
  filter:drop-shadow(0 22px 46px rgba(18,32,58,.22)); }
.award .info{ flex:1; }
.award .ribbon{ display:inline-block; padding:9px 20px; border-radius:30px; font-weight:900;
  letter-spacing:.14em; font-size:14px; text-transform:uppercase; color:#3A2600;
  background:linear-gradient(90deg,var(--gold),#F6B93B); box-shadow:0 8px 26px rgba(232,164,0,.4); }
.award .phase{ margin-top:16px; text-transform:uppercase; letter-spacing:.2em; font-size:14px;
  font-weight:800; color:var(--orange); }
.award .name{ font-size:64px; font-weight:900; letter-spacing:-.015em; margin:6px 0 0;
  background:linear-gradient(92deg,var(--orange),var(--pink));
  -webkit-background-clip:text; background-clip:text; color:transparent; }
.award .cite{ font-size:21px; font-style:italic; color:var(--ink2); line-height:1.42;
  margin:16px 0 20px; max-width:640px; }
.award ul.wins{ list-style:none; padding:0; margin:0; max-width:640px; }
.award ul.wins li{ font-size:16.5px; color:var(--ink2); line-height:1.4; margin:0 0 12px;
  padding-left:34px; position:relative; }
.award ul.wins li:before{ content:"\\2605"; position:absolute; left:0; top:-1px; color:var(--gold);
  font-size:20px; }

/* awards gallery */
.medals{ display:grid; grid-template-columns:repeat(5,1fr); gap:16px; margin-top:8px; }
.medal{ border:1px solid var(--line); border-radius:14px; padding:14px 12px 16px; text-align:center;
  background:linear-gradient(180deg,#fff,#FFF7EE); }
.medal img{ width:100%; height:150px; object-fit:contain; }
.medal .nm{ font-size:16px; font-weight:900; margin-top:8px; color:var(--ink); }
.medal .d{ font-size:12.5px; color:var(--muted); margin-top:4px; line-height:1.3; }
.awbanner{ margin-top:26px; text-align:center; padding:20px 24px; border-radius:16px;
  background:linear-gradient(92deg,#141F38,#243560); color:#fff; font-size:23px; font-weight:800;
  letter-spacing:.01em; box-shadow:0 16px 40px rgba(18,32,58,.24); }
.awbanner .em{ background:linear-gradient(92deg,#FFB05C,#F0426B);
  -webkit-background-clip:text; background-clip:text; color:transparent; }

/* cta hero strip */
.cta .herostrip{ display:flex; gap:14px; margin-top:30px; }
.cta .herostrip img{ height:120px; width:120px; object-fit:contain;
  background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12);
  border-radius:16px; padding:8px; }
"""


# ------------------------------------------------------------------ templates
def t_storycover(p, n):
    # comic movie-poster: bright burst background + hero squad + big story title.
    # deliberately unlike the dark "MAYA" book / value-brief covers.
    maya_dark = "assets/maya-logo.png"
    nmb_dark = "assets/nmb-logo.png"
    return f"""
    <div class="scover" style="background-image:url('{embed(S.COVER_BG)}')">
      <div class="wash"></div>
      <div class="logos">
        <div class="chip"><img src="{embed(maya_dark)}"></div>
        <div class="chip"><img src="{embed(nmb_dark)}"></div>
      </div>
      <div class="top">
        <span class="ribbon">&#9733; {esc(S.KICK)} &#9733;</span>
        <h1>The Migration That<br><span class="em">Won Every Round</span></h1>
        <div class="maya"><b>MAYA</b> &nbsp;Supersonic Migrate to Databricks</div>
      </div>
      <img class="squad" src="{embed(S.SQUAD)}">
      <div class="byline">
        <div>
          <div class="nm">{esc(BB.C.AUTHOR)}</div>
          <div class="hl">{esc(BB.C.AUTHOR_HEADLINE)}</div>
        </div>
        <div class="ed">{esc(BB.C.EDITION)}</div>
      </div>
    </div>"""


def t_cast(p, n):
    cards = ""
    for role, name, line in p["cast"]:
        cards += (f'<div class="castcard"><div class="role">{esc(role)}</div>'
                  f'<div class="nm">{esc(name)}</div>'
                  f'<div class="ln">{esc(line)}</div></div>')
    return f"""<div class="pad">
      {header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <div class="castbanner"><img src="{embed(p['squad'])}"></div>
      <div class="castgrid">{cards}</div>
      {footer(n)}
    </div>"""


def t_scene(p, n):
    body = BB.render_blocks(p["body"])
    qby = f'<div class="qby">{esc(p["quote_by"])}</div>' if p.get("quote_by") else ""
    side = ""
    if p.get("eyebrow_hero"):
        side = (f'<div class="side"><img src="{embed(p["eyebrow_hero"])}"></div>')
    return f"""<div class="pad">
      {header(p['kicker'], p['title'])}
      <div class="scene">
        <div class="txt">
          <div class="quote">{esc(p['quote'])}</div>
          {qby}
          {body}
        </div>
        {side}
      </div>
      {footer(n)}
    </div>"""


def _colorize(code):
    lines = []
    for ln in code.split("\n"):
        s = ln.strip()
        if s.startswith("#"):
            lines.append(f'<span class="c">{esc(ln)}</span>')
        elif s.startswith("python") and not ln.startswith(" "):
            head, _, rest = ln.partition(" ")
            lines.append(f'<span class="k">{esc(head)}</span> {esc(rest)}')
        elif ln.startswith(" ") or ln.startswith("run "):
            lines.append(f'<span class="c">{esc(ln)}</span>')
        else:
            lines.append(esc(ln))
    return "\n".join(lines)


def t_cli_ui(p, n):
    return f"""<div class="pad">
      {header(p['kicker'], p['title'], small=True)}
      <div class="cliui-intro">{esc(p['intro'])}</div>
      <div class="cliui">
        <div class="left">
          <div class="lbl">{esc(p.get('cli_title','From the CLI'))}</div>
          <div class="code">{_colorize(p['code'])}</div>
        </div>
        <div class="right">
          <img src="{embed(p['img'])}">
          <div class="cap">{esc(p['cap'])}</div>
        </div>
      </div>
      {footer(n)}
    </div>"""


def t_award(p, n):
    wins = "".join(f"<li>{esc(w)}</li>" for w in p["wins"])
    return f"""
    <div class="award">
      <div class="band"></div>
      <div class="wrap">
        <div class="hero"><img src="{embed(p['hero'])}"></div>
        <div class="info">
          <span class="ribbon">&#9733; {esc(p['award'])} &#9733;</span>
          <div class="phase">{esc(p['phase'])}</div>
          <div class="name">{esc(p['name'])}</div>
          <div class="cite">"{esc(p['citation'])}"</div>
          <ul class="wins">{wins}</ul>
        </div>
      </div>
      {footer(n)}
    </div>"""


def t_awards(p, n):
    medals = ""
    for img, nm, d in p["medals"]:
        medals += (f'<div class="medal"><img src="{embed(img)}">'
                   f'<div class="nm">{esc(nm)}</div><div class="d">{esc(d)}</div></div>')
    return f"""<div class="pad">
      {header(p['kicker'], p['title'])}
      <div class="intro">{esc(p['intro'])}</div>
      <div class="medals">{medals}</div>
      <div class="awbanner"><span class="em">{esc(p['banner'])}</span></div>
      {footer(n)}
    </div>"""


def t_award_cta(p, n):
    cards = ""
    for t, s in p["ctas"]:
        cards += (f'<div class="card"><div class="t">{esc(t)}</div>'
                  f'<div class="s">{esc(s)}</div></div>')
    strip = "".join(f'<img src="{embed(h)}">' for h in p.get("heroes", []))
    return f"""
    <div class="cta">
      <div class="pad2">
        <h1>{esc(p['title'])}</h1>
        <div class="lead">{esc(p['lead'])}</div>
        <div class="txt">{esc(p['body'])}</div>
        <div class="herostrip">{strip}</div>
        <div class="grid">{cards}</div>
        <div class="foot">
          <img src="{embed(MAYA_T)}">
          <div class="cr">Created by <b>{esc(BB.C.AUTHOR)}</b><br>
            {esc(BB.C.EDITION)} &nbsp;&bull;&nbsp; Apache-2.0 open source</div>
        </div>
      </div>
    </div>"""


# reused engine templates, with the story footer swapped in
def _wrap(fn):
    def inner(p, n):
        return _refoot(fn(p, n), n)
    return inner


TEMPLATES = {
    "storycover": t_storycover,
    "cast": t_cast,
    "scene": t_scene,
    "cli_ui": t_cli_ui,
    "award": t_award,
    "awards": t_awards,
    "award_cta": t_award_cta,
    "stages": _wrap(BB.t_stages),
    "figure": _wrap(BB.t_figure),
    "screens2": _wrap(BB.t_screens2),
    "benchmark": _wrap(BB.t_benchmark),
    "author": _wrap(BB.t_author),
}


def build_html():
    with open(os.path.join(HERE, "author.json"), encoding="utf-8") as f:
        BB.AUTHOR = json.load(f)
    pages = []
    for i, p in enumerate(S.PAGES, start=1):
        fn = TEMPLATES[p["tpl"]]
        pages.append(f'<section class="page">{fn(p, i)}</section>')
    body = "\n".join(pages)
    css = BB.CSS + EXTRA_CSS
    return (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>MAYA - The Migration That Won Every Round</title>"
            f"<style>{css}</style></head><body>{body}</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", action="store_true", help="write story.html only")
    args = ap.parse_args()
    doc = build_html()
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {OUT_HTML} ({len(doc)//1024} KB, {len(S.PAGES)} pages)")
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
