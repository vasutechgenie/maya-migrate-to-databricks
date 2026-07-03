"""
branding.py -- configurable PDF branding + reusable flowables.

Any project can rebrand by passing a Branding config. Returns a Brand object
exposing paragraph styles, a key/value table, bullets, an escape helper, a page
footer, a vector Diagram flowable, and box/arrow primitives + a Databricks lockup.
"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Flowable, Paragraph, Table, TableStyle


def esc(t) -> str:
    s = "" if t is None else str(t)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Diagram(Flowable):
    """A fixed-size flowable that delegates to a draw(canvas, w, h) callback."""

    def __init__(self, width, height, draw_fn):
        super().__init__()
        self.width = width
        self.height = height
        self._draw = draw_fn

    def draw(self):
        self._draw(self.canv, self.width, self.height)


class Brand:
    def __init__(self, branding=None):
        b = branding
        dark = getattr(b, "dark", "#1F2430") if b else "#1F2430"
        accent = getattr(b, "accent", "#3B4CCA") if b else "#3B4CCA"
        teal = getattr(b, "teal", "#0E7C7B") if b else "#0E7C7B"
        gray = getattr(b, "gray", "#6B7280") if b else "#6B7280"
        self.org = getattr(b, "org", "MAYA") if b else "MAYA"
        self.show_dbx = getattr(b, "show_databricks_lockup", True) if b else True

        self.DARK = colors.HexColor(dark)
        self.ACCENT = colors.HexColor(accent)
        self.TEAL = colors.HexColor(teal)
        self.GRAY = colors.HexColor(gray)
        self.DBX_RED = colors.HexColor("#FF3621")
        # semantic tokens reused by diagrams
        self.NAVY = self.DARK
        self.STEEL = self.TEAL
        self.GREEN = self.TEAL
        self.BRONZE = colors.HexColor("#B87333")
        self.SILVER = colors.HexColor("#8A95A5")
        self.GOLD = colors.HexColor("#C9A227")

        S = getSampleStyleSheet()
        self.H1 = ParagraphStyle("H1", parent=S["Heading1"], textColor=self.DARK,
                                 fontSize=17, spaceAfter=6)
        self.H2 = ParagraphStyle("H2", parent=S["Heading2"], textColor=self.TEAL,
                                 fontSize=12.5, spaceAfter=4)
        self.H3 = ParagraphStyle("H3", parent=S["Heading3"], textColor=self.ACCENT,
                                 fontSize=10.5, spaceAfter=3)
        self.BODY = ParagraphStyle("BODY", parent=S["BodyText"], fontSize=9.5,
                                   leading=13.5, spaceAfter=5)
        self.SMALL = ParagraphStyle("SMALL", parent=self.BODY, fontSize=8,
                                    textColor=self.GRAY)
        self.CAP = ParagraphStyle("CAP", parent=self.SMALL, alignment=TA_CENTER,
                                  spaceBefore=2, spaceAfter=8)
        self.BULLET = ParagraphStyle("BULLET", parent=self.BODY, leftIndent=14,
                                     bulletIndent=4, spaceAfter=2)

    # ---- text helpers ------------------------------------------------------
    def P(self, t, st=None):
        return Paragraph(t, st or self.BODY)

    def bullets(self, items, st=None):
        st = st or self.BULLET
        return [Paragraph(f"\u2022 {esc(i)}", st) for i in items]

    def kv_table(self, rows, col_w, header=None, fs=8.2):
        data = []
        if header:
            data.append([Paragraph(f"<b>{esc(h)}</b>", self._cell(fs)) for h in header])
        for r in rows:
            data.append([Paragraph(esc(c), self._cell(fs)) for c in r])
        t = Table(data, colWidths=col_w, repeatRows=1 if header else 0)
        style = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9DEE5")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), self.DARK),
                      ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
        t.setStyle(TableStyle(style))
        return t

    def _cell(self, fs):
        return ParagraphStyle(f"cell{fs}", parent=self.BODY, fontSize=fs,
                              leading=fs + 2.5)

    # ---- canvas primitives -------------------------------------------------
    def footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(self.DARK)
        canvas.rect(0, 0, doc.pagesize[0], 0.35 * inch, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(0.7 * inch, 0.13 * inch,
                          f"{self.org}  \u00b7  MAYA - Migration Accelerator")
        canvas.drawRightString(doc.pagesize[0] - 0.7 * inch, 0.13 * inch,
                               f"p. {doc.page}")
        canvas.restoreState()

    def draw_dbx_lockup(self, c, x, y, mark=16, fs=15, color=None):
        if not self.show_dbx:
            return
        color = color or self.DARK
        c.setFillColor(self.DBX_RED)
        c.rect(x, y, mark * 0.5, mark, fill=1, stroke=0)
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", fs)
        c.drawString(x + mark * 0.7, y + 1, "Databricks")

    def box(self, c, x, y, w, h, fill, label, sub="", fs=9, subfs=7,
            txtcolor=colors.white):
        c.setFillColor(fill)
        c.roundRect(x, y, w, h, 4, fill=1, stroke=0)
        c.setFillColor(txtcolor)
        c.setFont("Helvetica-Bold", fs)
        lines = label.split("\n")
        ty = y + h - 12
        for ln in lines:
            c.drawCentredString(x + w / 2, ty, ln)
            ty -= fs + 1
        if sub:
            c.setFont("Helvetica", subfs)
            for ln in sub.split("\n"):
                c.drawCentredString(x + w / 2, ty, ln)
                ty -= subfs + 1

    # legacy aliases used by ported diagram code
    def _box(self, c, x, y, w, h, fill, label, sub="", fs=9, subfs=7,
             txtcolor=colors.white):
        self.box(c, x, y, w, h, fill, label, sub, fs, subfs, txtcolor)

    def arrow(self, c, x1, y1, x2, y2, col=None, w=1.3):
        col = col or self.DARK
        c.setStrokeColor(col)
        c.setLineWidth(w)
        c.line(x1, y1, x2, y2)
        # arrowhead
        import math
        ang = math.atan2(y2 - y1, x2 - x1)
        for da in (math.radians(150), math.radians(-150)):
            c.line(x2, y2, x2 + 5 * math.cos(ang + da), y2 + 5 * math.sin(ang + da))

    def _arrow(self, c, x1, y1, x2, y2, col=None, w=1.3):
        self.arrow(c, x1, y1, x2, y2, col, w)
