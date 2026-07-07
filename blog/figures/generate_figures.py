#!/usr/bin/env python3
"""
generate_figures.py -- publication-grade figures for the "Migrating with MAYA"
hands-on series (series 2). Every figure is anchored to the runnable Northwind demo.

Each function returns a Fig; the runner renders a 300-DPI PNG (LinkedIn) and a vector
PDF into this folder. Style is shared via figlib for a consistent, journal-like series.
No customer names, credentials, or real data appear in any figure.

  python3 generate_figures.py            # render all
  python3 generate_figures.py 03 07      # render a subset by number
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figlib import (Fig, INK, NAVY, TEAL, ACCENT, GOLD, SILVER, BRONZE, GREEN, RED,
                    BLUE, PURPLE, LINE, FILL_LT, FILL_MD, WHITE, CAPTION, tint)

HERE = os.path.dirname(os.path.abspath(__file__))


# 01 - the twelve-stage lifecycle on Northwind (make demo)
def fig01():
    f = Fig(1140, 360, "One command, the full lifecycle: `make demo` on Northwind", 1,
            "Preview, build + certify on a sampled dev catalog, re-prove at full volume, "
            "then publish and go live - the twelve-stage lifecycle, run end to end in seconds.")
    subs = ["readiness", "collect\n+ score", "replicate\n(dev)", "specs",
            "build+cert\n(dev)", "BI conv\n(dev)", "full load\n(prod)",
            "build+cert\n(prod)", "BI parity\n(prod)", "docs +\npublish",
            "identity\n+ security", "enable +\ngo-live"]
    # phase groups: preview/dev-prep (teal), dev build (blue),
    # prod build (purple), publish + go-live (green)
    cols = [TEAL, TEAL, TEAL, TEAL, BLUE, BLUE, PURPLE, PURPLE, PURPLE,
            GREEN, GREEN, GREEN]
    n = 12
    bw, bh = 70, 46
    gap = (f.W - 60 - n * bw) / (n - 1)
    y = 150
    for i, (s, col) in enumerate(zip(subs, cols)):
        x = 30 + i * (bw + gap)
        f.box(x, y, bw, bh, str(i), fill=tint(col, .82), stroke=col, label_size=15)
        f.wrap_center(x + bw / 2, y + bh + 15, s.split("\n"), 7.4, CAPTION)
        if i < n - 1:
            f.arrow(x + bw, y + bh / 2, x + bw + gap, y + bh / 2, width=1.1, head=5)
    # phase-group labels sit just above their box groups
    def gx(i):
        return 30 + i * (bw + gap)
    f.text(gx(0), y - 18, "preview + dev prep", 8.0, TEAL, bold=True)
    f.text(gx(4), y - 18, "dev build (sampled)", 8.0, BLUE, bold=True)
    f.text(gx(6), y - 18, "prod build (full volume)", 8.0, PURPLE, bold=True)
    f.text(gx(9), y - 18, "publish + go-live", 8.0, GREEN, bold=True)
    f.box(30, 58, 210, 32, "git clone -> pip install", fill=tint(ACCENT, .82),
          stroke=ACCENT, label_size=10)
    f.text(260, 74, "Northwind: a fictional retailer migrating Azure Synapse -> Databricks, "
           "hand-authored to run green through the whole lifecycle.", 8.4, CAPTION,
           italic=True)
    f.text(30, 108, "Two-phase build + certify: the SAME code is proven on the sampled dev "
           "catalog (Stage 4), then re-proven at full volume (Stages 6-7). BI is two-phase "
           "too (5, 8).", 8.2, CAPTION, italic=True)
    return f


# 02 - the adapter model
def fig02():
    f = Fig(820, 380, "The adapter model: one narrow contract for any source", 2,
            "An adapter is the only source-specific code. It emits a normalized graph; "
            "everything downstream is source-agnostic.")
    f.box(40, 90, 160, 180, fill=tint(ACCENT, .9), stroke=ACCENT, radius=10)
    f.text(120, 112, "Source artifacts", 9.5, ACCENT, bold=True, anchor="middle")
    for i, s in enumerate(["Automic / UC4 jobs", "Synapse pipelines", "DW proc + DDL",
                           "connections"]):
        f.chip(56, 130 + i * 32, 128, 24, s, fill=BRONZE, size=7.6)
    f.box(250, 120, 120, 120, "Adapter", fill=NAVY, stroke=NAVY, text_color=WHITE,
          label_size=11)
    f.wrap_center(310, 250, ["collect / parse", "ddl_index", "connections"], 7.6,
                  CAPTION)
    f.arrow(200, 180, 250, 180, color=INK)
    outs = [("objects.csv", TEAL), ("edges.csv", TEAL), ("ddl index", BLUE),
            ("connections.csv", PURPLE)]
    for i, (o, col) in enumerate(outs):
        f.box(430, 96 + i * 44, 160, 34, o, fill=tint(col, .84), stroke=col,
              label_size=9)
        f.arrow(370, 180, 430, 113 + i * 44, color=LINE, width=0.9, head=4)
    f.box(630, 120, 150, 120, "Source-agnostic\ncore\n(order, contract,\nMAYA, report)",
          fill=tint(GREEN, .86), stroke=GREEN, label_size=9)
    f.arrow(590, 180, 630, 180, color=INK)
    f.text(40, 300, "Northwind ships as a discovery folder (objects/edges/connections + "
           "DDL) so the reference Synapse adapter runs offline, with no live source.",
           8.5, CAPTION, italic=True)
    return f


# 03 - the Northwind dependency graph
def fig03():
    f = Fig(860, 400, "The Northwind dependency graph (bronze -> silver -> gold)", 3,
            "Lineage is derived from the source, not guessed: 8 pipelines, ~25 tables, "
            "read/write edges across medallion layers.")
    cols = [("ext_*", 70, BRONZE, ["customers", "orders", "clickstream"]),
            ("src (bronze)", 250, SILVER, ["customers", "orders", "web_events"]),
            ("sales (silver)", 440, TEAL, ["dim_customer", "fact_order", "web_sessions"]),
            ("rdm (gold)", 630, GOLD, ["mart_sales_daily", "mart_customer_360",
                                       "mart_product_perf"])]
    pos = {}
    for ci, (title, x, col, nodes) in enumerate(cols):
        f.chip(x - 6, 62, 150, 22, title, fill=col, size=8.5)
        for j, nm in enumerate(nodes):
            y = 110 + j * 60
            f.box(x, y, 150, 40, nm, fill=tint(col, .84), stroke=col, label_size=8.2)
            pos[(ci, j)] = (x, y + 20, x + 150, y + 20)
    for j in range(3):
        f.arrow(pos[(0, j)][2], pos[(0, j)][3], pos[(1, j)][0], pos[(1, j)][1],
                color=LINE, width=0.9, head=4)
        f.arrow(pos[(1, j)][2], pos[(1, j)][3], pos[(2, j)][0], pos[(2, j)][1],
                color=LINE, width=0.9, head=4)
    for j in range(3):
        f.arrow(pos[(2, 1)][2], pos[(2, 1)][3], pos[(3, j)][0], pos[(3, j)][1],
                color=LINE, width=0.8, head=4)
    f.text(70, 330, "serving.sales_daily replicates the gold mart; nw_daily_master "
           "orchestrates the whole run; nw_fx_sync invokes an external proc in place.",
           8.5, CAPTION, italic=True)
    return f


# 04 - waves + independent verifier
def fig04():
    f = Fig(860, 400, "Build order: 5 verified waves", 4,
            "Tarjan SCC + longest-path layering produce the waves; a DIFFERENT algorithm "
            "set re-derives and proves them.")
    waves = [("W0", ["nw_ingest_erp", "nw_web_intake", "nw_fx_sync"]),
             ("W1", ["nw_build_sales", "nw_build_web"]),
             ("W2", ["nw_build_marts"]), ("W3", ["nw_qlik_replicate"]),
             ("W4", ["nw_daily_master"])]
    n = len(waves)
    colw = (f.W - 60) / n
    for wi, (w, pipes) in enumerate(waves):
        cx = 30 + colw * wi
        f.chip(cx + 8, 66, colw - 24, 22, w, fill=NAVY, size=9)
        for j, p in enumerate(pipes):
            f.box(cx + 6, 100 + j * 50, colw - 20, 38, p, fill=tint(TEAL, .84),
                  stroke=TEAL, label_size=7.8)
        if wi < n - 1:
            f.arrow(cx + colw - 12, 120, cx + colw + 6, 120, color=LINE, head=5)
    fy = 300
    f.text(30, fy, "Independent verifier (does NOT import the builder):", 9, INK,
           bold=True)
    checks = [("C1 completeness", GREEN), ("C2 wave agreement", GREEN),
              ("C3 forward edges", GREEN), ("C4 build sim", GREEN)]
    for i, (c, col) in enumerate(checks):
        x = 30 + i * 200
        f.box(x, fy + 14, 186, 32, c, fill=tint(col, .85), stroke=col, label_size=8.6)
        f.circle(x + 12, fy + 30, 4.5, fill=GREEN, stroke=GREEN)
    return f


# 05 - the pipeline contract
def fig05():
    f = Fig(820, 420, "The build contract for nw_build_sales", 5,
            "Derived straight from the graph: prerequisites, produced tables tagged by "
            "layer, and the parity targets that must be certified.")
    dx, dy, dw = 60, 70, 360
    f.box(dx, dy, dw, 320, fill=WHITE, stroke=NAVY, radius=10)
    f.text(dx + 16, dy + 26, "context/nw_build_sales.json", 10, NAVY, bold=True)
    f.hline(dx + 12, dy + 36, dx + dw - 12, color=FILL_MD)
    bands = [
        ("PREREQS (bronze inputs)", ["src.customers", "src.products", "src.suppliers",
                                     "src.orders", "src.order_lines"], TEAL),
        ("PRODUCED (silver)", ["sales.dim_customer", "sales.dim_product",
                               "sales.dim_supplier", "sales.fact_order"], NAVY),
        ("PARITY TARGETS", ["4 silver tables -> certified", "pattern B -> engine E2"],
         ACCENT),
    ]
    by = dy + 48
    for name, items, col in bands:
        h = 34 + len(items) * 15
        f.box(dx + 12, by, dw - 24, h, fill=tint(col, .9), stroke=col, radius=7)
        f.text(dx + 24, by + 20, name, 9, col, bold=True)
        for i, it in enumerate(items):
            f.text(dx + 30, by + 36 + i * 15, "- " + it, 7.8, INK)
        by += h + 10
    f.box(500, 120, 250, 120, "engine E2\nSpark SQL step-DAG\n\nbronze -> silver -> gold",
          fill=tint(GREEN, .86), stroke=GREEN, label_size=9)
    f.arrow(420, 180, 500, 180, color=INK)
    f.text(500, 270, "Nothing is invented. If the graph doesn't\nsupport it, it isn't in "
           "the contract.", 8.4, CAPTION, italic=True)
    return f


# 06 - reusable engines E1-E7
def fig06():
    f = Fig(840, 440, "Seven engines cover the whole estate", 6,
            "A deterministic classifier maps each pipeline pattern to one reusable "
            "engine. Build the engine once; configure it many times.")
    engines = [
        ("E1", "Ingestion (bronze)", ["nw_ingest_erp (A)", "nw_web_intake (D)",
                                      "nw_qlik_replicate (F)"], TEAL),
        ("E2", "Transform (silver/gold)", ["nw_build_sales (B)", "nw_build_web (B)",
                                           "nw_build_marts (B)"], NAVY),
        ("E4", "External invoke", ["nw_fx_sync (E)"], BRONZE),
        ("E5", "Orchestration", ["nw_daily_master (G)"], PURPLE),
    ]
    y = 80
    for eng, label, pipes, col in engines:
        f.box(40, y, 90, 60, eng, fill=col, stroke=col, text_color=WHITE,
              label_size=14)
        f.text(150, y + 22, label, 10, INK, bold=True)
        x = 150
        for p in pipes:
            w = 8 + len(p) * 5.4
            f.box(x, y + 32, w, 22, p, fill=tint(col, .86), stroke=col, label_size=7.6)
            x += w + 10
        y += 82
    f.text(40, y + 6, "E3 (delta-apply), E6 (utility) and E7 (custom-notebook escape "
           "hatch) round out the catalog for larger estates.", 8.5, CAPTION,
           italic=True)
    return f


# 07 - MAYA-Dev: the illusion of production
def fig07():
    f = Fig(840, 420, "Stage 4 - Build + Certify (dev): the illusion of production", 7,
            "Phase one of two-phase build+certify: every table sampled to a few thousand "
            "rows, with foreign-key closure so joins still resolve. Iterate fast and cheap.")
    f.box(50, 80, 300, 150, fill=tint(RED, .9), stroke=RED, radius=10)
    f.text(200, 102, "Production (full volume)", 9.5, RED, bold=True, anchor="middle")
    for i in range(5):
        f.line(70, 124 + i * 18, 330, 124 + i * 18, color=tint(RED, .4), width=6)
    f.text(200, 216, "expensive to run on every iteration", 7.6, CAPTION, italic=True,
           anchor="middle")
    f.arrow(350, 155, 440, 155, color=INK)
    f.text(395, 146, "sample", 7.6, CAPTION, italic=True, anchor="middle")
    f.box(440, 80, 340, 150, fill=tint(TEAL, .9), stroke=TEAL, radius=10)
    f.text(610, 102, "nw_dev illusion (~10k rows/table)", 9.5, TEAL, bold=True,
           anchor="middle")
    for i, c in enumerate(["schema", "key parity", "referential integrity"]):
        f.chip(456, 122 + i * 24, 150, 18, c, fill=TEAL, size=7.6)
    for i, c in enumerate(["no extra output", "idempotency", "row sample"]):
        f.chip(620, 122 + i * 24, 150, 18, c, fill=TEAL, size=7.6)
    f.text(50, 300, "RI-preserving = seed rows + foreign-key closure (deterministic, "
           "seed 42). src.orders and src.order_lines carry larger sample budgets so the "
           "fact grain is exercised.", 8.5, CAPTION, italic=True)
    return f


# 08 - MAYA-SIT: 10 checks + drift loop
def fig08():
    f = Fig(860, 440, "Stage 7 - Build + Certify (prod): 10-check parity + drift loop", 8,
            "Phase two of build+certify: the SAME code, now at full volume on "
            "production-copied data at a pinned watermark. One red check fails the table - "
            "no partial credit.")
    checks = ["1 schema", "2 row count", "3 key parity", "4 checksum", "5 aggregates",
              "6 nulls", "7 ref integrity", "8 no extra out", "9 idempotency",
              "10 row sample"]
    cw, ch, gx, gyv = 150, 34, 12, 12
    x0, y0 = 40, 74
    for i, c in enumerate(checks):
        r, col = divmod(i, 5)
        x = x0 + col * (cw + gx)
        y = y0 + r * (ch + gyv)
        f.box(x, y, cw, ch, c, fill=FILL_LT, stroke=NAVY, label_size=8.2)
        f.circle(x + 12, y + ch / 2, 4, fill=GREEN, stroke=GREEN)
    fy = 200
    steps = [("run checks", NAVY), ("localize red", ACCENT), ("compare logic", ACCENT),
             ("reason code", GOLD), ("fix at source", TEAL)]
    x = 40
    for lab, col in steps:
        f.box(x, fy, 140, 40, lab, fill=tint(col, .84), stroke=col, label_size=8.6)
        if lab != "fix at source":
            f.arrow(x + 140, fy + 20, x + 152, fy + 20, color=LINE, head=5)
        x += 152
    f.polyline([(x - 12, fy + 40), (x - 12, fy + 66), (40 + 70, fy + 66),
                (40 + 70, fy + 40)], color=ACCENT, width=1.2, dash=[4, 3])
    f.arrow(770, fy + 20, 812, fy + 20, color=GREEN)
    f.box(792, fy - 4, 44, 48, "green", fill=tint(GREEN, .82), stroke=GREEN,
          label_size=8)
    codes = ["TRANSLATION", "SCHEMA", "TIMING", "TYPE-NUANCE", "LEGACY-BUG"]
    f.text(40, fy + 96, "Reason codes:", 9, INK, bold=True)
    for i, c in enumerate(codes):
        f.chip(150 + i * 130, fy + 84, 120, 20, c, fill=SILVER, size=7.4)
    return f


# 09 - MAYA-Soak: sustained parity
def fig09():
    f = Fig(880, 400, "Sustained soak (Stage 7): provisional now, final after zero drift", 9,
            "Point-in-time parity proves state; the soak proves the ongoing incremental "
            "logic stays equal - re-checked at T+7 and T+14 before final certification.")
    y = 150
    f.line(60, y, 820, y, color=LINE, width=2)
    marks = [(60, "Full volume", "dev + prod green", TEAL),
             (300, "Provisional", "cert issued", GOLD),
             (540, "T+7", "re-prove parity", ACCENT),
             (760, "T+14", "final cert", GREEN)]
    for x, lab, sub, col in marks:
        f.circle(x, y, 8, fill=col, stroke=col)
        f.box(x - 70, y - 70, 140, 44, lab, sub, fill=tint(col, .85), stroke=col,
              label_size=9.5, sub_size=7.4)
    f.box(300, y + 40, 460, 40,
          "each window: all 10 checks on the CUMULATIVE table AND the incremental DELTA",
          fill=tint(NAVY, .9), stroke=NAVY, label_size=8.4)
    f.text(60, y + 110, "Both systems run in parallel through the soak. A merge/CDC/SCD "
           "bug that self-corrects on full recompute is exposed by the delta window.",
           8.5, CAPTION, italic=True)
    return f


# 10 - dashboard, BI, cutover, gates
def fig10():
    f = Fig(880, 420, "Dashboard, BI/Genie, and the cutover gates", 10,
            "The estate advances through machine-checked gates; the BI layer is migrated "
            "and mirrored as Genie + Lakeview on the same certified numbers.")
    gates = ["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"]
    subl = ["scope", "graph", "order", "contract", "build", "dev cert", "prod cert",
            "cutover", "provis.", "final"]
    n = len(gates)
    bw = (f.W - 60 - (n - 1) * 8) / n
    for i, (g, s) in enumerate(zip(gates, subl)):
        x = 30 + i * (bw + 8)
        col = GREEN if i >= n - 2 else TEAL
        f.box(x, 80, bw, 44, g, fill=tint(col, .84), stroke=col, label_size=9)
        f.wrap_center(x + bw / 2, 134, [s], 7.2, CAPTION)
    f.box(60, 210, 340, 120, fill=FILL_LT, stroke=NAVY, radius=10)
    f.text(76, 232, "BI layer (two-phase: dev + prod)", 9.5, NAVY, bold=True)
    for i, s in enumerate(["extract (MCP/API)", "AI-convert query", "result parity",
                           "republish + Genie/Lakeview"]):
        f.chip(76, 246 + i * 20, 300, 16, s, fill=NAVY if i % 2 else TEAL, size=7.4)
    f.box(480, 210, 340, 120, "Live dashboard\n\nv_progress - v_drift - v_soak_watch",
          fill=tint(GOLD, .86), stroke=GOLD, label_size=9)
    f.text(60, 356, "A pipeline is finally certified only after the soak; BI objects go "
           "live only on MAYA-certified gold. Run `make demo` to see it all.", 8.5,
           CAPTION, italic=True)
    return f


# master - Northwind architecture
def fig_master():
    f = Fig(860, 500, "MAYA on Northwind: core vs. adapter architecture", None,
            "A thin Synapse adapter emits one normalized graph; the source-agnostic core "
            "orders, contracts, samples, validates, and reports.")
    f.box(30, 70, 170, 250, fill=tint(ACCENT, .9), stroke=ACCENT, radius=10)
    f.text(115, 92, "Synapse adapter", 10, ACCENT, bold=True, anchor="middle")
    for i, s in enumerate(["collect()", "parse -> graph", "ddl_index()",
                           "connections()", "dialect translate"]):
        f.chip(48, 110 + i * 38, 144, 26, s, fill=ACCENT, size=8.2)
    f.text(115, 312, "examples/northwind/", 7.6, CAPTION, italic=True, anchor="middle")
    f.box(240, 160, 90, 70, "Normalized\ngraph", fill=NAVY, stroke=NAVY,
          text_color=WHITE, label_size=9)
    f.arrow(200, 195, 240, 195, color=INK)
    f.box(360, 70, 460, 250, fill=FILL_LT, stroke=NAVY, radius=10)
    f.text(376, 92, "Source-agnostic core", 10, NAVY, bold=True)
    core = ["Build order + verify", "Contract + classifier", "Engines E1-E7",
            "Validation (10-check)", "Two-phase build+certify", "Agent orchestration",
            "Branded reports", "Two-phase BI + Genie"]
    for i, c in enumerate(core):
        r, col = divmod(i, 2)
        x = 376 + col * 224
        y = 110 + r * 46
        f.box(x, y, 210, 34, c, fill=WHITE, stroke=TEAL, label_size=8.6)
    f.arrow(330, 195, 360, 195, color=INK)
    f.box(f.W / 2 - 220, 360, 440, 34,
          "Certified Databricks lakehouse (bronze -> silver -> gold) + migrated BI (Genie)",
          fill=NAVY, stroke=NAVY, text_color=WHITE, label_size=9.5)
    f.arrow(f.W / 2, 320, f.W / 2, 360)
    return f


# author card
def fig_author():
    f = Fig(820, 170, "", None, "")
    f.dr.rectangle([0, 0, f._s(8), f._s(f.H)], fill=ACCENT)
    f.circle(70, 85, 44, fill=NAVY, stroke=NAVY)
    f._cmid(70, 85, "SN", 24, WHITE, True)
    f.text(150, 58, "Srinivas Nelakuditi", 20, INK, bold=True)
    f.text(150, 82, "Creator of MAYA - a deterministic migration accelerator", 11, TEAL,
           bold=True)
    chips = ["data platform migration", "Spark - Delta - CDC", "Synapse -> Databricks",
             "open source"]
    x = 150
    for c in chips:
        w = f.dr.textlength(c, font=f._font(8.2, False)) / f.S + 22
        f.chip(x, 104, w, 22, c, fill=SILVER, size=8.2)
        x += w + 10
    f.hline(150, 142, f.W - 26, color=FILL_MD, width=0.8)
    f.text(150, 158, "Author, 'Migrating with MAYA' - a 10-part hands-on series", 8.5,
           CAPTION, italic=True)
    return f


FIGURES = {
    "01": fig01, "02": fig02, "03": fig03, "04": fig04, "05": fig05,
    "06": fig06, "07": fig07, "08": fig08, "09": fig09, "10": fig10,
    "master": fig_master, "author": fig_author,
}

NAMES = {
    "01": "01_meet_maya_northwind", "02": "02_adapter_model",
    "03": "03_dependency_graph", "04": "04_build_order_waves",
    "05": "05_pipeline_contract", "06": "06_reusable_engines",
    "07": "07_maya_dev_illusion", "08": "08_maya_sit_drift_loop",
    "09": "09_maya_soak_sustained", "10": "10_dashboard_bi_cutover",
    "master": "00_architecture_master", "author": "00_author_card",
}


def render(selected=None):
    keys = selected or list(FIGURES.keys())
    for k in keys:
        if k not in FIGURES:
            continue
        f = FIGURES[k]()
        out = f.save(HERE, NAMES[k])
        print(f"  {k} -> {os.path.basename(out)}")


if __name__ == "__main__":
    render(sys.argv[1:] or None)
