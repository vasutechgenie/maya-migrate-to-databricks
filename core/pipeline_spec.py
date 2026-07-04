"""
pipeline_spec.py -- Stage 3: one branded spec PDF per pipeline.

For every Stage-1 context pack it renders a self-contained build spec the swarm (or a
human) can implement against: pattern/engine/kind, prerequisites, produced tables with
layer + DDL columns, parity targets, reachable procs, the bronze->silver->gold data
flow, and the MAYA gate plan (Dev -> SIT -> Soak). All PDFs are merged into one omnibus
via reports.merge_pdfs. The gate passes when there is exactly one PDF per pipeline.
"""
from __future__ import annotations

import json
import os
from typing import List

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Spacer, PageBreak

from .branding import Brand, Diagram
from . import reports as reports_mod


def _context_dir(cfg) -> str:
    return cfg.p(cfg.specs_dir, "context")


def _render_one(cfg, ctx: dict, out_path: str) -> str:
    B = Brand(cfg.branding)
    W = letter[0] - 1.4 * inch
    pipe = ctx.get("pipeline", "pipeline")

    def band(c, w, h):
        c.setFillColor(B.DARK)
        c.roundRect(0, 0, w, h, 6, fill=1, stroke=0)
        c.setFillColor(B.ACCENT)
        c.rect(0, 0, 5, h, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(16, h - 26, f"MAYA Pipeline Spec - {pipe}")
        c.setFillColor(colors.HexColor("#C8D2DE"))
        c.setFont("Helvetica", 9)
        c.drawString(16, h - 42, f"{ctx.get('pattern_label', '')}  -  engine "
                     f"{ctx.get('engine', '')}  -  {ctx.get('kind', '')}")
        c.setFillColor(B.ACCENT)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(16, 12, B.org)
        B.draw_dbx_lockup(c, w - 120, 9, mark=13, fs=12, color=colors.white)

    story = [Diagram(W, 58, band), Spacer(1, 10)]

    story.append(B.P("1. Classification", B.H1))
    story.append(B.kv_table([
        ["Pattern", f"{ctx.get('pattern')} - {ctx.get('pattern_label')}"],
        ["Engine", f"{ctx.get('engine')} - {ctx.get('engine_label')}"],
        ["Kind", ctx.get("kind", "")],
        ["Wave", str(ctx.get("wave", 0))],
        ["Prereqs / Produced / Parity",
         f"{ctx.get('n_prereqs',0)} / {ctx.get('n_produced',0)} / {ctx.get('n_parity',0)}"],
    ], [2.3 * inch, 4.4 * inch], header=["Field", "Value"], fs=8))

    story.append(B.P("2. Prerequisites (bronze landing set)", B.H1))
    prereqs = ctx.get("prereqs", [])
    if prereqs:
        story += B.bullets(prereqs)
    else:
        story.append(B.P("No upstream table prerequisites.", B.SMALL))

    story.append(B.P("3. Produced tables", B.H1))
    prod = ctx.get("produced", [])
    if prod:
        rows = [[p["table"], p.get("layer", ""),
                 ", ".join(p.get("ddl_columns", [])[:10]) +
                 ("..." if len(p.get("ddl_columns", [])) > 10 else "")]
                for p in prod]
        story.append(B.kv_table(rows, [2.3 * inch, 0.9 * inch, 3.5 * inch],
                                header=["Table", "Layer", "Columns"], fs=7.2))
    else:
        story.append(B.P("This pipeline produces no persisted tables.", B.SMALL))

    story.append(B.P("4. Parity targets", B.H1))
    parity = ctx.get("parity", [])
    if parity:
        story += B.bullets([f"{p['table']} ({p.get('layer')})" for p in parity])
    else:
        story.append(B.P("No silver/gold parity targets (bronze/ingest or external).",
                         B.SMALL))

    procs = ctx.get("procs", [])
    if procs:
        story.append(B.P("5. Reachable stored procedures", B.H1))
        story += B.bullets([f"{p['name']}  {p.get('source_file','')}" for p in procs])

    story.append(PageBreak())
    story.append(B.P("6. MAYA gate plan", B.H1))
    m = cfg.maya
    wins = " & ".join(f"T+{d}" for d in m.soak_windows_days) or "T+7 & T+14"
    story += B.bullets([
        f"MAYA-Dev: build on the synthetic test catalog ({m.test_catalog}); prove "
        "schema, keys, RI, no-extra-output, idempotency, and a row-level sample.",
        "MAYA-SIT: at prod scale on prod-copied data; all 10 checks, point-in-time "
        "(provisional certification).",
        f"MAYA-Soak: parallel runs re-proven at {wins} on cumulative + delta; zero "
        "drift = final certification.",
        "Certification is topological: this pipeline certifies only after its "
        "predecessors are certified.",
    ])

    story.append(B.P("7. Data flow", B.H1))
    story.append(B.P(ctx.get("mermaid", "").replace("\n", "  |  "), B.SMALL))

    doc = SimpleDocTemplate(out_path, pagesize=letter, topMargin=0.6 * inch,
                            bottomMargin=0.6 * inch, leftMargin=0.7 * inch,
                            rightMargin=0.7 * inch, title=f"{pipe} spec")
    doc.build([s for s in story if s is not None],
              onFirstPage=B.footer, onLaterPages=B.footer)
    return out_path


def run(cfg) -> dict:
    ctx_dir = _context_dir(cfg)
    if not os.path.isdir(ctx_dir):
        return {"stage": 3, "passed": False, "error": "no context packs (run context)"}
    out_dir = cfg.out("specs_pdf")
    os.makedirs(out_dir, exist_ok=True)
    ctx_files = sorted(f for f in os.listdir(ctx_dir) if f.endswith(".json"))
    pdfs: List[tuple] = []
    for fn in ctx_files:
        ctx = json.load(open(os.path.join(ctx_dir, fn)))
        pipe = ctx.get("pipeline", fn[:-5])
        out_path = os.path.join(out_dir, f"{pipe}.pdf")
        _render_one(cfg, ctx, out_path)
        pdfs.append((pipe, out_path))
    omnibus = cfg.out("pipeline_specs_omnibus.pdf")
    merge = reports_mod.merge_pdfs(omnibus, pdfs)
    gate = {"stage": 3, "passed": len(pdfs) == len(ctx_files) and len(pdfs) > 0,
            "pipelines": len(ctx_files), "pdfs": len(pdfs),
            "omnibus_pages": merge["pages"], "dir": out_dir}
    with open(cfg.out("stage3_gate.json"), "w") as f:
        json.dump(gate, f, indent=1)
    return gate
