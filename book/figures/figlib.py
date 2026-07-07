"""
figlib.py -- colorful, publication-grade figure primitives (Pillow backend).

Design goals:
  - LARGE horizontal/vertical safe margins so LinkedIn's cover crop never clips content.
  - vibrant, per-figure color theme + soft gradient background.
  - crisp output: supersampled 4x, downsampled 2x with LANCZOS.
  - both a high-res PNG (LinkedIn) and a PDF copy.

Content is authored in a top-down logical space of width W x height H. A generous inset
(IX, IY) is added around that space and every primitive is offset into it, so the whole
series has a consistent, un-croppable frame. No client names, code, or data appear.
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFont


def _rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# ---- vibrant palette ------------------------------------------------------
INK = _rgb("#12203A")
NAVY = _rgb("#1F3A93")
INDIGO = _rgb("#3B36B0")
BLUE = _rgb("#2563EB")
CYAN = _rgb("#0EA5C6")
TEAL = _rgb("#0FB5AE")
GREEN = _rgb("#12A150")
GOLD = _rgb("#E8A400")
ORANGE = _rgb("#FB6514")
ACCENT = _rgb("#FB6514")
CORAL = _rgb("#F0426B")
PINK = _rgb("#DB2777")
PURPLE = _rgb("#7C3AED")
RED = _rgb("#E23B3B")
CRIMSON = _rgb("#D6336C")
BRONZE = _rgb("#B4763B")
SILVER = _rgb("#7A8AA0")
LINE = _rgb("#5B6b84")
FILL_LT = _rgb("#EEF2Fb")
FILL_MD = _rgb("#D5DEEE")
WHITE = _rgb("#FFFFFF")
CAPTION = _rgb("#48566E")

# per-figure theme, indexed by figure number (1..15); None -> INDIGO
THEME_CYCLE = [INDIGO, ORANGE, TEAL, BLUE, GREEN, PURPLE, ACCENT, GOLD, PINK,
               CRIMSON, TEAL, CORAL, BLUE, PURPLE, INDIGO]

_FONTS = {
    "reg": "/System/Library/Fonts/Supplemental/Arial.ttf",
    "bold": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "ital": "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
}


def tint(c, t=0.85):
    """Light tint of a color toward white."""
    return tuple(int(round(v + (255 - v) * t)) for v in c)


def shade(c, t=0.4):
    """Darken a color toward near-black."""
    return tuple(int(round(v * (1 - t) + 18 * t)) for v in c)


class Fig:
    """A top-down drawing canvas (Pillow) with color theme, safe margins, helpers."""

    S = 4          # supersample factor
    OUT = 2        # final downscale target (relative to logical points)
    IX_FRAC = 0.14  # horizontal safe margin (fraction of W) each side
    IY_FRAC = 0.11  # vertical safe margin (fraction of H) each side

    def __init__(self, w=760, h=460, title="", number=None, caption="", theme=None):
        self.W, self.H = w, h
        self.IX = int(round(w * self.IX_FRAC))
        self.IY = int(round(h * self.IY_FRAC))
        self.theme = theme or (THEME_CYCLE[(number - 1) % len(THEME_CYCLE)]
                               if number else INDIGO)
        fw = (w + 2 * self.IX) * self.S
        fh = (h + 2 * self.IY) * self.S
        self.img = Image.new("RGB", (fw, fh), WHITE)
        self.dr = ImageDraw.Draw(self.img)
        self._fcache = {}
        self.pad = 26
        self._number = number
        self._caption = caption
        self._paint_background(fw, fh)
        if title:
            self.text(self.pad, 24, title, 14, shade(self.theme, 0.35), bold=True)
            self.hline(self.pad, 34, w - self.pad, color=self.theme, width=2.2)

    # ---- background -------------------------------------------------------
    def _paint_background(self, fw, fh):
        top = tint(self.theme, 0.90)
        bot = WHITE
        for j in range(0, fh, self.S):  # step by S for speed; blocks are tiny
            t = j / fh
            col = tuple(int(round(top[k] + (bot[k] - top[k]) * t)) for k in range(3))
            self.dr.rectangle([0, j, fw, j + self.S], fill=col)
        # colorful left spine in the margin
        self.dr.rectangle([0, 0, int(self.IX * self.S * 0.28), fh], fill=self.theme)

    # ---- coordinate transforms (logical -> pixel, with inset) -------------
    def px(self, x):
        return (x + self.IX) * self.S

    def py(self, y):
        return (y + self.IY) * self.S

    def _s(self, v):
        return v * self.S

    # ---- fonts ------------------------------------------------------------
    def _font(self, size, bold=False, italic=False):
        key = (round(size, 1), bold, italic)
        if key in self._fcache:
            return self._fcache[key]
        path = _FONTS["bold"] if bold else (_FONTS["ital"] if italic else _FONTS["reg"])
        if not os.path.exists(path):
            path = _FONTS["reg"]
        fnt = ImageFont.truetype(path, int(round(size * self.S)))
        self._fcache[key] = fnt
        return fnt

    # ---- text -------------------------------------------------------------
    def _text(self, x, y, s, size, color, bold, italic, anchor):
        fnt = self._font(size, bold, italic)
        self.dr.text((self.px(x), self.py(y)), s, font=fnt, fill=color, anchor=anchor)

    def text(self, x, y, s, size=9, color=INK, bold=False, italic=False,
             anchor="start"):
        a = {"start": "ls", "middle": "ms", "end": "rs"}[anchor]
        self._text(x, y, s, size, color, bold, italic, a)

    def ctext(self, cx, y, s, size=9, color=INK, bold=False):
        self._text(cx, y, s, size, color, bold, False, "ms")

    def _cmid(self, cx, cy, s, size, color, bold=False):
        self._text(cx, cy, s, size, color, bold, False, "mm")

    def wrap_center(self, cx, y, lines, size=9, color=INK, bold=False, lh=None):
        lh = lh or (size + 3)
        for i, ln in enumerate(lines):
            self.ctext(cx, y + i * lh, ln, size, color, bold)

    # ---- shapes -----------------------------------------------------------
    def box(self, x, y, w, h, label="", sub="", fill=FILL_LT, stroke=LINE,
            text_color=INK, sub_color=None, radius=8, lw=1.4, label_size=10,
            sub_size=8, label_bold=True):
        self.dr.rounded_rectangle(
            [self.px(x), self.py(y), self.px(x + w), self.py(y + h)],
            radius=self._s(radius), fill=fill, outline=stroke,
            width=max(1, int(self._s(lw))))
        cx = x + w / 2
        if label and sub:
            self._cmid(cx, y + h / 2 + 3, label, label_size, text_color, label_bold)
            self._cmid(cx, y + h / 2 - sub_size, sub, sub_size, sub_color or CAPTION)
        elif label:
            lines = label.split("\n")
            lh = label_size + 3
            start = y + h / 2 - (len(lines) - 1) * lh / 2
            for i, ln in enumerate(lines):
                self._cmid(cx, start + i * lh, ln, label_size, text_color, label_bold)

    def chip(self, x, y, w, h, label, fill, text_color=WHITE, size=8.5, radius=10):
        self.dr.rounded_rectangle(
            [self.px(x), self.py(y), self.px(x + w), self.py(y + h)],
            radius=self._s(radius), fill=fill, outline=None)
        self._cmid(x + w / 2, y + h / 2, label, size, text_color, True)

    def circle(self, cx, cy, r, fill=FILL_LT, stroke=LINE, lw=1.4):
        self.dr.ellipse(
            [self.px(cx - r), self.py(cy - r), self.px(cx + r), self.py(cy + r)],
            fill=fill, outline=stroke, width=max(1, int(self._s(lw))))

    def _dashed(self, x1, y1, x2, y2, color, width, dash):
        dl = dash[0] if dash else 4
        gap = dash[1] if len(dash) > 1 else dl
        total = math.hypot(x2 - x1, y2 - y1)
        if total == 0:
            return
        ux, uy = (x2 - x1) / total, (y2 - y1) / total
        pos = 0.0
        while pos < total:
            a, b = pos, min(pos + dl, total)
            self.dr.line([self.px(x1 + ux * a), self.py(y1 + uy * a),
                          self.px(x1 + ux * b), self.py(y1 + uy * b)],
                         fill=color, width=max(1, int(self._s(width))))
            pos += dl + gap

    def line(self, x1, y1, x2, y2, color=LINE, width=1.2, dash=None):
        if dash:
            self._dashed(x1, y1, x2, y2, color, width, dash)
        else:
            self.dr.line([self.px(x1), self.py(y1), self.px(x2), self.py(y2)],
                         fill=color, width=max(1, int(self._s(width))))

    def hline(self, x1, y, x2, color=LINE, width=1.0, dash=None):
        self.line(x1, y, x2, y, color, width, dash)

    def arrow(self, x1, y1, x2, y2, color=INK, width=1.6, head=6, dash=None):
        self.line(x1, y1, x2, y2, color, width, dash)
        ang = math.atan2(y2 - y1, x2 - x1)
        for da in (math.radians(150), math.radians(-150)):
            hx = x2 + head * math.cos(ang + da)
            hy = y2 + head * math.sin(ang + da)
            self.line(x2, y2, hx, hy, color, width)

    def poly(self, pts, fill=FILL_LT, stroke=LINE, lw=1.4):
        flat = [c for xy in pts for c in (self.px(xy[0]), self.py(xy[1]))]
        self.dr.polygon(flat, fill=fill, outline=stroke,
                        width=max(1, int(self._s(lw))))

    def polyline(self, pts, color=LINE, width=1.4, dash=None):
        for i in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            self.line(x1, y1, x2, y2, color, width, dash)

    # ---- caption + render -------------------------------------------------
    def caption(self):
        if not self._caption and self._number is None:
            return
        self.hline(self.pad, self.H - 30, self.W - self.pad, color=FILL_MD, width=1.0)
        label = f"Figure {self._number}" if self._number is not None else "Figure"
        y = self.H - 15
        self.text(self.pad, y, label, 8.5, shade(self.theme, 0.3), bold=True)
        w = self.dr.textlength(label, font=self._font(8.5, True)) / self.S
        self.text(self.pad + w + 6, y, "| " + self._caption, 8.5, CAPTION,
                  italic=True)

    def save(self, out_dir, name, dpi=300):
        self.caption()
        os.makedirs(out_dir, exist_ok=True)
        out_w = (self.W + 2 * self.IX) * self.OUT
        out_h = (self.H + 2 * self.IY) * self.OUT
        final = self.img.resize((out_w, out_h), Image.LANCZOS)
        png = os.path.join(out_dir, name + ".png")
        pdf = os.path.join(out_dir, name + ".pdf")
        final.save(png, "PNG")
        final.save(pdf, "PDF", resolution=float(dpi))
        return png
