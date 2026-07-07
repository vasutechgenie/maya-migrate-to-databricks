#!/usr/bin/env python3
"""
value_content.py -- authored content for the MAYA VALUE BRIEF (executive one-sitting
read on savings: time, people, software spend, cloud spend, complexity, and
maintainability). Rendered by build_value_brief.py into a landscape PDF that reuses
the MAYA book's branding + templates.

Every cost/time/effort figure on the "savings" pages is an ILLUSTRATIVE MODEL for a
representative large program (100-300 engineers, 2-3 years), grounded in MAYA's
measured compression ratios and gate-once validation. The benchmark facts (MFVI,
categories) are MEASURED on the open Nelakuditi Migration Benchmark. Footnotes say so.
"""

SUBTITLE = "Weeks, not years - proven on an open benchmark"
KICK = "Executive Value Brief"

# asset shortcuts (relative to maya-oss/book/, resolved + embedded by the builder)
BG = "assets/cover_bg.png"
HEAD = "assets/headshot.png"
MAYA_L = "assets/maya-logo.png"
NMB_L = "assets/nmb-logo.png"
MFVI = "assets/nmb_mfvi.png"
RADAR = "assets/nmb_radar.png"

CONTACT = "srinivas.nelakuditi@databricks.com"

# footnote reused on modeled pages
MODEL_FN = ("Illustrative model for a representative large program (100-300 engineers, "
            "2-3 years) migrating a data warehouse + BI + downstream apps to Databricks. "
            "Percentages reflect MAYA's measured compression ratios and its gate-once "
            "validation; actuals vary by estate. Benchmark figures are measured on the "
            "open Nelakuditi Migration Benchmark (NMB).")

PAGES = [

    # 1 --- COVER ----------------------------------------------------------
    {"tpl": "cover2"},

    # 2 --- THE BOTTOM LINE (KPI hero) ------------------------------------
    {"tpl": "kpi", "kicker": "The bottom line", "title": "One harness compresses a "
     "multi-year, 200-400 person migration into weeks",
     "lead": "MAYA turns a Databricks migration from a hand-run art project into a "
     "deterministic engineering process - so the same outcome lands with a fraction "
     "of the time, people, and spend, and the result is provably correct.",
     "stats": [
         ("Years → Weeks", "Time to cut over", "24-36 months compressed to 6-12 weeks"),
         ("200-400 → ~15", "People engaged", "one expert pod driving the AI swarm"),
         ("~85-90%", "Lower total cost", "labor + software + cloud + rework combined"),
         ("8 / 8", "Benchmark categories won", "measured, #1 on the open NMB"),
     ],
     "banner": "Same scope. Same numbers, proven table-by-table. A fraction of the "
     "time, headcount, and cost."},

    # 3 --- OLD WAY vs MAYA (comparison table) ----------------------------
    {"tpl": "table", "kicker": "At a glance", "title": "The old way vs MAYA",
     "intro": "Migrations don't run long because the SQL is hard. They run long "
     "because proving correctness, at scale and over time, is done by hand. MAYA "
     "automates the expensive part on a foundation that is already correct.",
     "columns": ["Dimension", "Traditional migration", "MAYA"],
     "rows": [
         ["Timeline", "24-36 months, slips often", "6-12 weeks, gated + predictable"],
         ["Team", "100-400 engineers for years", "~10-20 expert pod + AI swarm"],
         ["Correctness", "Spot-check + \"validate the important ones\"",
          "Every table certified: schema, keys, row-count, checksum, aggregates"],
         ["Post-cutover", "Silent drift; matched at go-live, diverges later",
          "Sustained soak parity (T+7 / T+14) before the source retires"],
         ["Software spend", "Profiler + converter + validator + orchestrator licenses",
          "One harness covers discovery → build → certify → govern"],
         ["Cloud spend", "Repeated full-scale trial runs burn compute",
          "Logic proven on ~10k-row samples; one paid full-scale run"],
         ["Maintainability", "Bespoke rewrites only the original team understands",
          "SQL-first medallion + generated docs + tests, built to keep"],
     ],
     "footnote": "note: " + MODEL_FN},

    # 4 --- WEEKS NOT YEARS (bar comparison) ------------------------------
    {"tpl": "bars", "kicker": "Time, team, effort", "title": "Weeks, not years - "
     "and a pod, not an army",
     "intro": "The same migration, sized two ways. MAYA collapses calendar time and "
     "human effort by turning the plan into a provable build order and letting an AI "
     "agent swarm build + certify the estate wave by wave.",
     "bars": [
         ("Calendar time to cut over", "30 months", 100, "8 weeks", 6.7, "~93% faster"),
         ("People engaged", "250 engineers", 100, "~15 pod", 6.0, "~94% fewer"),
         ("Human effort (person-months)", "~7,500", 100, "~30", 0.5,
          "up to ~250x less"),
     ],
     "note": "Measured on individual benchmark tasks, MAYA compresses effort up to "
     "1000x; at program scale the model above shows a ~250x reduction in person-months.",
     "footnote": MODEL_FN},

    # 5 --- WHERE THE MONEY GOES (stacked cost) ---------------------------
    {"tpl": "stack", "kicker": "Total cost of migration", "title": "Where the money "
     "goes - and where it stops going",
     "intro": "Total migration cost is dominated by labor, then the sprawl of "
     "point-tool licenses, then the cloud compute burned on repeated full-scale "
     "trial runs, then rework when \"done\" turns out to be wrong. MAYA cuts every "
     "band at once.",
     "cols": [
         ("Traditional", [
             ("Labor", 62, "#5A6B84"),
             ("Software / licensing", 14, "#8794A8"),
             ("Cloud / compute", 16, "#0EA5C6"),
             ("Rework + overruns", 8, "#E23B3B"),
         ]),
         ("MAYA", [
             ("Labor", 7, "#FB6514"),
             ("Software", 2, "#F0426B"),
             ("Cloud", 3, "#0FB5AE"),
             ("Rework ~0", 1, "#12A150"),
         ]),
     ],
     "callout": "~87% lower",
     "callout_sub": "total cost of migration",
     "footnote": MODEL_FN},

    # 6 --- SAVINGS BY CATEGORY (table) -----------------------------------
    {"tpl": "table", "kicker": "Savings by category", "title": "Every line item bends "
     "the right way",
     "intro": "A one-screen view of what leadership actually asks about: time, people, "
     "spend, risk, and the cost of living with the result.",
     "columns": ["Category", "Traditional", "With MAYA", "Reduction"],
     "rows": [
         ["Time to cut over", "24-36 months", "6-12 weeks", "~85-90%"],
         ["People engaged", "100-400", "10-20 pod", "~90%"],
         ["Human effort", "thousands of person-months", "tens", "up to ~250x"],
         ["Software / tooling spend", "many point tools", "one harness", "~70-85%"],
         ["Cloud spend (migration)", "repeated full-scale runs", "gate-once",
          "~50-70%"],
         ["Post-cutover rework", "20-40% typical", "near-zero (parity-gated)",
          "~90%+"],
         ["Ongoing maintenance", "bespoke rewrites", "SQL-first + docs", "sustainable"],
     ],
     "footnote": "note: " + MODEL_FN},

    # 7 --- ONE HARNESS, ONE PROJECT, PHASED ------------------------------
    {"tpl": "phased", "kicker": "One harness. One project.", "title": "Do it all - "
     "or add layers later, without redoing the pipelines",
     "intro": "Real programs don't land in one shot. MAYA runs the whole migration, "
     "or just the layer you're ready for - all inside the same project. Data + ETL "
     "first; add BI/dashboards later; add downstream apps later - each as its own "
     "gated run that rides on the certified pipeline estate. No pipeline is ever "
     "rebuilt.",
     "phases": [
         ("1", "Data + ETL", "Warehouse, pipelines, procs → certified Databricks "
          "medallion (bronze/silver/gold), parity-proven table by table."),
         ("2", "BI / dashboards", "Convert + parity-check every dashboard query, "
          "republish as Lakeview, wire Genie AI/BI - added on top, later."),
         ("3", "Downstream apps", "Custom apps on the DW migrated whole to Lakebase "
          "(OLTP) + Databricks Apps on Unity Catalog - added on top, later."),
     ],
     "chip": "Same project - add-on runs skip pipeline creation entirely",
     "footnote": "Selective add-on runs (BI-only / Apps-only) execute only their layer "
     "once the data + ETL migration is certified, so nothing is recomputed."},

    # 8 --- WHAT MAYA MIGRATES (coverage grid) ----------------------------
    {"tpl": "grid", "kicker": "Full-migration coverage", "title": "The whole estate - "
     "not just the SQL",
     "intro": "Most tools convert code and leave the rest to you. MAYA gates every "
     "dimension a large program has to land - each with real, reviewable evidence.",
     "cards": [
         ("Data & pipelines", "Tables, views, procs, jobs → medallion Spark SQL, "
          "certified at full scale."),
         ("BI & Genie", "Dashboards + reports converted, parity-checked, republished "
          "as Lakeview; Genie AI/BI on certified gold."),
         ("Downstream apps", "Custom DW apps → Databricks Lakebase (OLTP) + Databricks "
          "Apps, governed by Unity Catalog."),
         ("Identity & governance", "Source grants mapped 1:1 to Unity Catalog, PII "
          "masked, credentials scoped."),
         ("Orchestration", "Schedules + triggers migrated to Databricks Workflows."),
         ("Docs & enablement", "Auto-generated documentation, runbooks, training, "
          "cutover / rollback, day-2 ops."),
     ]},

    # 9 --- MAINTAINABILITY -----------------------------------------------
    {"tpl": "maintain", "kicker": "Built to keep", "title": "Code your team can "
     "actually own - for years",
     "intro": "A migration you can't maintain is a future migration. MAYA's output is "
     "modern, uniform, and documented - so the savings compound long after cutover.",
     "points": [
         ("SQL-first medallion", "Every pipeline is readable bronze/silver/gold Spark "
          "SQL following one pattern - not a black box, not a per-team dialect."),
         ("Generated documentation", "Lineage, contracts, and per-pipeline docs are "
          "produced automatically and stay in sync with the code."),
         ("Deterministic + tested", "The same code runs in dev and prod; parity tests "
          "and gates ship with it, so changes are safe to make."),
         ("No lock-in", "Open, source-agnostic core on Unity Catalog governance - the "
          "estate is yours, portable and standard."),
     ],
     "mrows": [
         ["Ongoing maintenance cost", "High - bespoke, tribal", "Low - uniform + documented"],
         ["Onboarding a new engineer", "Weeks per subsystem", "Days - one pattern"],
         ["Change safety", "Fear-driven, manual checks", "Gate-checked, reproducible"],
     ],
     "footnote": MODEL_FN},

    # 10 --- COMPLEXITY REDUCTION -----------------------------------------
    {"tpl": "cards", "kicker": "Radical simplification", "title": "One graph. One "
     "contract. One harness.",
     "intro": "The complexity of a migration doesn't disappear - MAYA absorbs it into "
     "a small number of provable artifacts, so humans review a plan instead of "
     "chasing thousands of moving parts.",
     "cards": [
         ("From thousands of unknowns", "to ONE normalized dependency graph",
          "Every table, view, proc, and job with its real dependencies - 100% "
          "traversable, provable build order."),
         ("From \"validate the important ones\"", "to ONE contract every workload passes",
          "Schema, keys, referential integrity, row-count, checksum, aggregates, "
          "point-in-time, and sustained parity."),
         ("From a toolchain of point products", "to ONE harness end-to-end",
          "Discovery, build order, codegen, certification, BI, apps, governance, and "
          "enablement - driven from a single command center."),
     ]},

    # 11 --- PROOF (benchmark) --------------------------------------------
    {"tpl": "benchmark2", "kicker": "Nelakuditi Migration Benchmark (NMB)",
     "title": "#1 - measured, not marketed",
     "mfvi": MFVI, "radar": RADAR,
     "stats": [
         ("98.96", "MAYA MFVI", "composite of 8 dimensions"),
         ("2.6x", "the field", "vs the next-best tool (37.9)"),
         ("8 / 8", "dimensions led", "correctness to sustained parity"),
         ("100%", "measured", "TPC-H / TPC-DS + Northwind / Retail"),
     ],
     "note": "MAYA's scores are measured by running the engine on the open corpus; "
     "competitor scores are cited from public / vendor sources. Benchmark, harness, "
     "and results are open source and reproducible."},

    # 12 --- ABOUT THE AUTHOR ---------------------------------------------
    {"tpl": "author", "kicker": "About the author"},

    # 13 --- CTA / back cover ---------------------------------------------
    {"tpl": "cta", "title": "Turn years into weeks",
     "lead": "The MAYA web application is delivered by experts - it is not an "
     "open-source, self-service product.",
     "body": "Standing it up and running a real migration end to end requires the "
     "MAYA experts to configure workspaces, connections, and governance and to drive "
     "the AI swarm. To model the savings for your estate or to engage MAYA:",
     "ctas": [
         ("Databricks Professional Services & FDE", "the team that delivers "
          "MAYA-driven migrations end to end"),
         ("Email", CONTACT),
         ("Open source", "github.com/vasutechgenie/maya-migrate-to-databricks"),
         ("Benchmark", "github.com/vasutechgenie/nelakuditi-migration-benchmark"),
     ]},
]
