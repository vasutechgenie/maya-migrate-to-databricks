#!/usr/bin/env python3
"""
content.py -- authored content for the MAYA migration guide (the ebook).

Kept separate from build_book.py so the prose/pages can be edited without
touching the rendering engine. Each page is a dict with a "tpl" (template) key;
build_book.py knows how to render each template into a fixed landscape page.

Asset paths are relative to this directory (maya-oss/book/); build_book.py
resolves and base64-embeds them so the PDF is fully self-contained.
"""

TITLE = "MAYA"
TITLE_FULL = "Supersonic Migrate to Databricks Accelerator"
SUBTITLE = "#1 Benchmark Winner in Multiple Categories"
AUTHOR = "Srinivas Nelakuditi"
AUTHOR_HEADLINE = ("Global Head FDE | Exec Sponsor (CIO/CTO/CISO) | "
                   "Scaled Enterprise AI Deployments")
EDITION = "First Edition"
CONTACT = "srinivas.nelakuditi@databricks.com"

# asset shortcuts
BG = "assets/cover_bg.png"
HEAD = "assets/headshot.png"
MAYA_L = "assets/maya-logo.png"
MAYA_D = "assets/maya-logo-dark.png"
NMB_L = "assets/nmb-logo.png"
NMB_D = "assets/nmb-logo-dark.png"
MFVI = "assets/nmb_mfvi.png"
RADAR = "assets/nmb_radar.png"
FIG = "../blog/figures/"

PAGES = [

    # 1 --- COVER ----------------------------------------------------------
    {"tpl": "cover"},

    # 2 --- WHAT'S INSIDE (TOC) -------------------------------------------
    {"tpl": "toc", "title": "What's inside", "kicker": "A field guide",
     "intro": "How to turn a multi-year migration to Databricks into a "
              "deterministic, provable engineering process - and the "
              "independent benchmark that shows MAYA leads the field.",
     "items": [
         ("Part I", "The MAYA model", "Source-agnostic core, one normalized "
          "graph, a provable build order, and a contract every workload passes."),
         ("Part II", "Proving correctness", "The three-phase parity gate - "
          "Dev illusion, SIT at scale, and a sustained soak that catches drift."),
         ("Part III", "The full lifecycle", "Twelve gated stages: data, BI/Genie, "
          "identity & governance, enablement, and cutover."),
         ("Part IV", "The proof", "MAYA is #1 on the Nelakuditi Migration "
          "Benchmark - measured, not marketed."),
         ("Part V", "Get started", "A 60-second quickstart on the runnable "
          "Northwind demo, and how to run it on your estate."),
     ]},

    # 3 --- FOREWORD -------------------------------------------------------
    {"tpl": "prose", "kicker": "Foreword", "title": "Migration is an "
     "engineering problem, not an art project",
     "body": [
         ("p", "Most enterprise migrations to Databricks are run like art "
          "projects: hand-rewrite the pipelines, \"validate the important "
          "ones,\" pray at cutover, then watch the result quietly drift in "
          "production. That is why they take 6 months to 3 years - and why so "
          "many never fully retire the source."),
         ("p", "MAYA takes the opposite stance. A migration is a "
          "deterministic, reviewable engineering process: one normalized "
          "dependency graph, a build order you can prove correct, a contract "
          "every workload must pass, and an AI agent swarm that builds and "
          "certifies the estate wave by wave until the system is provably "
          "complete."),
         ("quote", "The hard part of a migration was never writing SQL. It "
          "was proving that hundreds of rebuilt pipelines produce exactly the "
          "same numbers as the legacy system - and keep producing them after "
          "cutover."),
         ("p", "This guide is the short version of that method. It is written "
          "for the leaders and engineers who own the outcome, and it ends with "
          "independent, reproducible evidence that the method works."),
     ],
     "signoff": "— Srinivas Nelakuditi"},

    # 4 --- DIVIDER Part I -------------------------------------------------
    {"tpl": "divider", "part": "Part I", "title": "The MAYA Model",
     "sub": "Source-agnostic core. One normalized graph. A plan you can review "
            "before anything is built."},

    # 5 --- Why migrations take years -------------------------------------
    {"tpl": "prose", "kicker": "The problem", "title": "Why migrations take years",
     "body": [
         ("p", "Code conversion is the easy part. The cost lives everywhere "
          "else: understanding what actually exists, in what order it must be "
          "built, and proving that the rebuilt system is equal - table by "
          "table, at full scale, and over time."),
         ("bullets", [
             "Thousands of interdependent tables, views, procs and jobs, with "
             "the real dependencies buried in code and control tables.",
             "No provable build order - so teams rebuild things out of order "
             "and discover breakage late.",
             "Validation done by spot-check and vibe, not by contract - so "
             "\"done\" is a feeling, not a fact.",
             "Post-cutover drift: a pipeline that matched on go-live day "
             "silently diverges a week later.",
         ]),
         ("p", "MAYA attacks each of these directly - and automates the "
          "expensive part last, on top of a foundation that is already "
          "correct."),
     ]},

    # 6 --- The MAYA model / architecture ---------------------------------
    {"tpl": "figure", "kicker": "The model", "title": "A thin adapter, a "
     "source-agnostic core",
     "img": FIG + "00_architecture_master.png",
     "caption": "The core never sees your source technology - it only operates "
     "on a normalized graph. A thin adapter is the only piece that understands "
     "a given source, so the same engine migrates Synapse, Snowflake, Redshift, "
     "Hadoop/Hive, SQL Server/SSIS, Teradata, or Oracle - all to Databricks.",
     "note": "~70-80% of a migration is the reusable core; ~20-30% is the "
     "adapter. Onboarding a new source is \"write an adapter,\" not \"fork the "
     "tool.\""},

    # 7 --- Preview before you build --------------------------------------
    {"tpl": "figure_text", "kicker": "Preview", "title": "See the whole "
     "migration before anything is built",
     "img": FIG + "04_build_order_waves.png",
     "body": [
         ("num", [
             "Adapter parses your exported source into a normalized graph "
             "(objects + edges).",
             "Order computes a topological build order (waves) via Tarjan SCC "
             "+ longest-path layering.",
             "Verify re-derives the order with different algorithms (Kosaraju "
             "+ memoized DFS + Kahn) and proves it correct - an independent "
             "check, not a rubber stamp.",
             "Context emits a deterministic per-pipeline contract: prereqs, "
             "produced tables (bronze/silver/gold), and parity targets.",
             "Report - a branded PDF previewing waves, engines, parity, and "
             "connections, for a human to review first.",
         ]),
     ]},

    # 8 --- Reusable engines ----------------------------------------------
    {"tpl": "figure", "kicker": "Build", "title": "Reusable engines E1-E7, "
     "SQL-first",
     "img": FIG + "06_reusable_engines.png",
     "caption": "The swarm builds real pipelines with a catalog of reusable "
     "engines - it translates the actual source logic into medallion "
     "(bronze/silver/gold) Spark SQL, and never invents business rules.",
     "note": "Modernization to the lakehouse is baked in - this is not a "
     "lift-and-shift."},

    # 9 --- DIVIDER Part II ------------------------------------------------
    {"tpl": "divider", "part": "Part II", "title": "Proving Correctness",
     "sub": "The name says how validation works. Maya means illusion: prove "
            "logic cheaply, then parity at scale, then keep proving it."},

    # 10 --- The validation technique -------------------------------------
    {"tpl": "table", "kicker": "The technique", "title": "Two phases, then a "
     "sustained soak",
     "intro": "Correctness is proven cheaply before the one expensive "
     "full-scale run - and then re-proven over time, because a pipeline that "
     "matches at cutover can still drift.",
     "columns": ["Phase", "Data", "Proves", "Cost"],
     "rows": [
         ["MAYA-Dev", "Every table, sampled to ~10k rows (RI-preserving)",
          "Logic: schema, keys, referential integrity, no-extra-output, "
          "idempotency, transform spot-checks", "Tiny"],
         ["MAYA-SIT", "Production-copied data, full volume",
          "Full-scale parity: all 10 checks incl. row-count, checksum, "
          "aggregates, point-in-time (provisional cert)", "Paid once"],
         ["MAYA-Soak", "Live parallel loads at T+7 and T+14",
          "Sustained parity on the cumulative table and the incremental delta - "
          "catches slow drift (final cert)", "Two runs / window"],
     ],
     "footnote": "Gate rule: Dev AND SIT green earns a provisional "
     "certification; zero drift across every soak window earns final "
     "certification. Only then can the source retire."},

    # 11 --- The drift loop -----------------------------------------------
    {"tpl": "figure", "kicker": "When numbers don't match", "title": "The "
     "drift loop",
     "img": FIG + "08_maya_sit_drift_loop.png",
     "caption": "When a parity check fails, the agent doesn't guess. It "
     "localizes the divergence, fixes the code, and re-proves - looping until "
     "the pipeline is green. A wave advances only when every pipeline in it is "
     "certified.",
     "note": "Point-in-time parity proves state; the soak proves the ongoing "
     "incremental logic stays equal over time."},

    # 12 --- DIVIDER Part III ---------------------------------------------
    {"tpl": "divider", "part": "Part III", "title": "The Full Lifecycle",
     "sub": "A real migration is more than pipelines. MAYA gates every "
            "dimension a large program has to land - twelve stages, each with "
            "real evidence."},

    # 13 --- The twelve stages --------------------------------------------
    {"tpl": "stages", "kicker": "Twelve gated stages", "title": "From "
     "readiness to \"migration complete\"",
     "intro": "Stages 1-8 migrate and certify data + BI across two explicit "
     "phases - dev (a ~10k RI-preserving sample) and prod (the full backfill) - "
     "using the same code in both. Stage 0 collects the non-data estate up "
     "front; Stages 9-11 finish the program.",
     "stages": [
         ("0", "Readiness", "identity / access / secrets / classification"),
         ("1", "Collect + score", "100% traversable graph"),
         ("2", "Replicate (dev)", "RI-filled ~10k test catalog"),
         ("3", "Specs", "one spec per pipeline"),
         ("4", "Build + certify (dev)", "dev-green on the sample"),
         ("5", "BI convert (dev)", "dashboards run on sample gold"),
         ("6", "Full load (prod)", "historical backfill"),
         ("7", "Build + certify (prod)", "100% parity on real data"),
         ("8", "BI parity + publish", "Genie / Lakeview republished"),
         ("9", "Docs + publish", "full generated docs"),
         ("10", "Identity + security", "UC grants, masks, secrets"),
         ("11", "Enablement + go-live", "training, cutover, day-2 ops"),
     ]},

    # 14 --- BI + Genie ----------------------------------------------------
    {"tpl": "figure_text", "kicker": "Beyond data", "title": "Migrating the BI "
     "layer - and bringing AI to it",
     "img": FIG + "10_dashboard_bi_cutover.png",
     "body": [
         ("p", "Dashboards and reports are migrated with the same rigor as the "
          "data: every dashboard query is converted, dev-certified on the "
          "sample gold, then parity-checked on the full production gold and "
          "republished."),
         ("bullets", [
             "The same converted queries run in dev and prod - no divergence.",
             "Republished as Databricks Lakeview dashboards.",
             "Genie AI/BI is wired on top so business users can ask questions "
             "in natural language over the certified gold layer.",
         ]),
     ]},

    # 15 --- Governance / enablement --------------------------------------
    {"tpl": "prose", "kicker": "Governance, people, operations",
     "title": "The parts most migrations forget",
     "body": [
         ("p", "The last mile is where most migrations quietly fail - the "
          "governance, the people, and the day-2 operations. MAYA treats them as "
          "first-class, gated stages, not afterthoughts."),
         ("bullets", [
             "Stage 10 - Identity, security & governance: source grants mapped 1:1 "
             "to Unity Catalog, every PII column masked, every credential scoped.",
             "Stage 11 - Enablement & go-live: training, runbooks, cutover / "
             "rollback plans, and day-2 operations - all go/no-go checks green.",
         ]),
     ]},

    # 16 --- DIVIDER Part IV ----------------------------------------------
    {"tpl": "divider", "part": "Part IV", "title": "The Proof",
     "sub": "Anyone can claim they're fast. MAYA's numbers are measured on a "
            "neutral, reproducible, open-source benchmark - and published."},

    # 18 --- Benchmark proof (headline spread) ----------------------------
    {"tpl": "benchmark", "kicker": "Nelakuditi Migration Benchmark (NMB)",
     "title": "#1 - and it's not close",
     "mfvi": MFVI, "radar": RADAR,
     "stats": [
         ("98.96", "MAYA MFVI", "composite of 8 dimensions"),
         ("2.6x", "the field", "vs the next-best tool (37.9)"),
         ("8 / 8", "dimensions led", "correctness to sustained parity"),
         ("100%", "measured", "run on TPC-H / TPC-DS + Northwind / Retail"),
     ],
     "note": "MAYA's scores are MEASURED by running the engine on the open "
     "corpus; competitor scores are cited from public / vendor sources. The "
     "benchmark, harness, and results are open source and reproducible."},

    # 19 --- DIVIDER Part V ------------------------------------------------
    {"tpl": "divider", "part": "Part V", "title": "Get Started",
     "sub": "The whole method is runnable today - offline, with zero external "
            "calls - on a synthetic demo estate."},

    # 20 --- Quickstart ----------------------------------------------------
    {"tpl": "code", "kicker": "60-second quickstart", "title": "Run the full "
     "lifecycle on the Northwind demo",
     "code": "git clone https://github.com/vasutechgenie/maya-migrate-to-databricks\n"
             "cd maya-migrate-to-databricks\n"
             "pip install -r requirements.txt\n\n"
             "make demo     # all twelve gated stages, end to end, offline\n"
             "make test     # the deterministic goldens for the demo",
     "body": [
         ("p", "make demo runs MAYA's twelve gated stages on a fictional "
          "retailer moving to Databricks, with the deterministic offline agent "
          "driver - so it runs end to end with no credentials and no live "
          "connections."),
         ("p", "Running it on your estate: point an adapter at your exported "
          "metadata and copy the example project config. Because the core is "
          "source-agnostic, the target is always Databricks but the source can "
          "be anything - you only implement the adapter."),
     ]},

    # 21 --- About the author ---------------------------------------------
    {"tpl": "author", "kicker": "About the author"},

    # 22 --- Engage / CTA / back cover ------------------------------------
    {"tpl": "cta", "title": "Bring MAYA to your migration",
     "lead": "The MAYA web application is delivered by experts - it is not an "
     "open-source, self-service product.",
     "body": "Standing it up and running a real migration end to end requires "
     "the MAYA experts to configure workspaces, connections, and governance and "
     "to drive the AI swarm. To evaluate or engage it for your migration:",
     "ctas": [
         ("Databricks Professional Services & FDE", "the team that delivers "
          "MAYA-driven migrations end to end"),
         ("Email", CONTACT),
         ("Open source", "github.com/vasutechgenie/maya-migrate-to-databricks"),
         ("Benchmark", "github.com/vasutechgenie/nelakuditi-migration-benchmark"),
     ]},
]
