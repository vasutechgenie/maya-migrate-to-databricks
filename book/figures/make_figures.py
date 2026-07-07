#!/usr/bin/env python3
"""
make_figures.py -- book-quality benchmark figures for the MAYA migration guide.

Reads the committed NMB leaderboard (assets/leaderboard.json) and renders:
  assets/nmb_mfvi.png    headline MFVI ranking bar chart (MAYA #1)
  assets/nmb_radar.png   8-dimension radar: MAYA vs the best of the field

Numbers are pulled from the leaderboard so the book never drifts from the repo.
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from figlib import (Fig, INK, NAVY, ORANGE, GOLD, CORAL, PINK, GREEN, SILVER,
                    LINE, WHITE, CAPTION, FILL_LT, FILL_MD, tint, shade)

BOOK = os.path.dirname(HERE)
ASSETS = os.path.join(BOOK, "assets")


def load():
    with open(os.path.join(ASSETS, "leaderboard.json"), encoding="utf-8") as f:
        return json.load(f)


class BookFig(Fig):
    IX_FRAC = 0.045
    IY_FRAC = 0.05


def _entries(lb):
    rows = []
    for e in lb["divisions"]["closed"]:
        rows.append((e["tool"], e["mfvi"], e["dimensions"], "MEASURED"))
    for e in lb["divisions"]["open"]:
        rows.append((e["tool"], e["mfvi"], e["dimensions"], "REPORTED"))
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows


def fig_mfvi(lb):
    rows = _entries(lb)
    W, H = 900, 470
    f = BookFig(w=W, h=H, title="")
    # header
    f.text(26, 46, "MAYA leads the Nelakuditi Migration Benchmark",
           19, INK, bold=True)
    f.text(26, 70, "Migration Fidelity & Velocity Index (MFVI) — composite of 8 "
           "dimensions, 0-100. Higher is better.", 10.5, CAPTION, italic=True)
    f.hline(26, 82, W - 26, color=ORANGE, width=2.4)

    x0, x1 = 210, 828          # bar track span (0..100)
    scale = (x1 - x0) / 100.0
    top, bot = 108, H - 40
    pitch = (bot - top) / len(rows)
    bh = min(34, pitch * 0.56)

    # gridlines at 25/50/75/100
    for g in (25, 50, 75, 100):
        gx = x0 + g * scale
        f.line(gx, top - 6, gx, bot, color=FILL_MD, width=1.0, dash=(3, 4))
        f.ctext(gx, top - 10, str(g), 8, SILVER)

    for i, (tool, mfvi, _dims, prov) in enumerate(rows):
        cy = top + i * pitch + pitch / 2
        y = cy - bh / 2
        winner = (i == 0)
        # track
        f.box(x0, y, x1 - x0, bh, fill=tint(NAVY, 0.94), stroke=None, radius=bh / 2)
        # value bar
        bw = max(bh, mfvi * scale)
        bar_fill = ORANGE if winner else tint(NAVY, 0.62)
        bar_stroke = shade(ORANGE, 0.28) if winner else tint(NAVY, 0.5)
        f.box(x0, y, bw, bh, fill=bar_fill, stroke=bar_stroke, radius=bh / 2,
              lw=1.6 if winner else 1.0)
        # tool name (right-aligned in label gutter)
        f.text(196, cy + 4, tool, 12 if winner else 11,
               INK if winner else shade(NAVY, 0.15), bold=winner, anchor="end")
        # value label
        vx = x0 + bw + 10
        f.text(vx, cy + 4, f"{mfvi:.1f}", 12 if winner else 10.5,
               shade(ORANGE, 0.25) if winner else CAPTION, bold=winner)
        # provenance tag
        tag = "measured" if prov == "MEASURED" else "public / vendor-reported"
        f.text(vx + (46 if winner else 34), cy + 4, tag, 8, SILVER, italic=True)
        if winner:
            f.chip(x0 + 8, y + bh / 2 - 9, 46, 18, "#1", GOLD, INK, size=10)

    f.text(26, H - 12, "Source: Nelakuditi Migration Benchmark v0.1, Closed "
           "(measured) vs Open (reported) divisions.", 8.5, SILVER, italic=True)
    return f.save(ASSETS, "nmb_mfvi")


def fig_radar(lb):
    dims = lb["dimensions"]
    labels_map = {
        "correctness": "Correctness", "autonomy": "Autonomy",
        "coverage": "Coverage", "determinism": "Determinism",
        "sustained_parity": "Parity", "velocity": "Velocity",
        "cost_efficiency": "Cost / Effort", "evidence": "Evidence",
    }
    maya = lb["divisions"]["closed"][0]["dimensions"]
    field = {d: max(e["dimensions"].get(d, 0) for e in lb["divisions"]["open"])
             for d in dims}

    W, H = 780, 680
    f = BookFig(w=W, h=H, title="")
    f.text(30, 44, "A clean sweep across every dimension", 18, INK, bold=True)
    f.text(30, 66, "MAYA (measured) vs the best score any other tool reports on "
           "each axis.", 10.5, CAPTION, italic=True)
    f.hline(30, 78, W - 30, color=ORANGE, width=2.2)

    cx, cy, R = W / 2, 358, 190
    n = len(dims)

    def ang_of(i):
        return -math.pi / 2 + i * 2 * math.pi / n

    def pt(val, i):
        a = ang_of(i)
        r = R * max(0.0, min(100.0, val)) / 100.0
        return (cx + r * math.cos(a), cy + r * math.sin(a))

    # rings + ring scale labels
    for ring in (25, 50, 75, 100):
        poly = [(cx + R * ring / 100.0 * math.cos(ang_of(i)),
                 cy + R * ring / 100.0 * math.sin(ang_of(i))) for i in range(n)]
        f.polyline(poly + [poly[0]], color=FILL_MD, width=1.0)
        f.text(cx + 3, cy - R * ring / 100.0 + 3, str(ring), 7, SILVER)

    # axes
    for i in range(n):
        ex, ey = pt(100, i)
        f.line(cx, cy, ex, ey, color=tint(NAVY, 0.72), width=1.0)

    # MAYA polygon first (light orange), field on top so both read clearly
    mp = [pt(maya[d], i) for i, d in enumerate(dims)]
    f.poly(mp + [mp[0]], fill=tint(ORANGE, 0.62), stroke=ORANGE, lw=2.4)
    fp = [pt(field[d], i) for i, d in enumerate(dims)]
    f.poly(fp + [fp[0]], fill=tint(NAVY, 0.55), stroke=NAVY, lw=1.8)
    for (x, y) in mp:
        f.circle(x, y, 3.0, fill=ORANGE, stroke=WHITE, lw=1.0)

    # labels with angle-aware anchoring
    for i, d in enumerate(dims):
        a = ang_of(i)
        lx = cx + (R + 26) * math.cos(a)
        ly = cy + (R + 26) * math.sin(a)
        ca = math.cos(a)
        anchor = "middle" if abs(ca) < 0.25 else ("start" if ca > 0 else "end")
        f.text(lx, ly + 4, labels_map[d], 9.5, shade(NAVY, 0.1), bold=True,
               anchor=anchor)

    # legend
    ly = H - 30
    f.box(60, ly, 16, 12, fill=tint(ORANGE, 0.62), stroke=ORANGE, radius=3)
    f.text(82, ly + 11, "MAYA (measured)", 10.5, INK, bold=True)
    f.box(280, ly, 16, 12, fill=tint(NAVY, 0.55), stroke=NAVY, radius=3)
    f.text(302, ly + 11, "Best of the field (reported)", 10.5, CAPTION)
    return f.save(ASSETS, "nmb_radar")


def main():
    lb = load()
    p1 = fig_mfvi(lb)
    p2 = fig_radar(lb)
    print("wrote:", p1)
    print("wrote:", p2)


if __name__ == "__main__":
    main()
