#!/usr/bin/env python3
"""
story_content.py -- authored content for "MAYA - The Migration That Won Every Round",
a playful, illustrated migration STORY: a CEO sets the mandate, the CTO deploys a top
architect, and the architect + two developers + MAYA migrate a legacy warehouse to
Databricks in weeks - running the Data+ETL, BI, and Downstream-App layers separately
(from both the CLI and the UI), winning an original superhero "MAYA Hero Award" at
every phase.

Rendered by build_story.py into a landscape PDF that reuses the MAYA book engine
(build_book.py) for branding, CSS, and shared templates.

The narrative (roles, dialogue, award ceremony) is playful storytelling. The product
behavior shown (staged ETL/BI/Apps runs in CLI + UI, no pipeline rebuilt) is real and
screenshotted. Benchmark facts are measured on the open Nelakuditi Migration Benchmark.
"""

SUBTITLE = "A Databricks migration told in three acts - and three awards"
KICK = "A MAYA Migration Story"

# asset shortcuts (relative to maya-oss/book/, embedded by the builder)
BG = "assets/cover_bg.png"
# story gets its OWN bright comic "movie-poster" cover so it looks nothing like the
# dark MAYA book / value-brief covers
COVER_BG = "assets/story/cover_bg.png"

# original superhero mascots (generated, no IP)
SQUAD = "assets/heroes/hero_squad.png"
H_FOUNDRY = "assets/heroes/hero_foundry.png"
H_STORYTELLER = "assets/heroes/hero_storyteller.png"
H_BUILDER = "assets/heroes/hero_builder.png"
H_GUARDIAN = "assets/heroes/hero_guardian.png"
H_CHAMPION = "assets/heroes/hero_champion.png"

# UI screenshots (copied into assets/story/ from the web app docs)
S_INTAKE = "assets/story/intake.png"
S_ETL = "assets/story/etl_certified.png"
S_DASH = "assets/story/dashboard_after.png"
S_APPS_BEFORE = "assets/story/apps_before.png"
S_APPS_CERT = "assets/story/apps_certified.png"
S_RUNS = "assets/story/runs_history.png"
S_APP_BUILDER = "assets/story/app_builder.png"
S_APP_REG = "assets/story/app_registered.png"
S_APP_MIGRATED = "assets/story/app_migrated.png"
S_APP_DETAIL = "assets/story/app_detail.png"

CONTACT = "srinivas.nelakuditi@databricks.com"

STORY_FN = ("The characters and award ceremony are playful storytelling. The product "
            "behavior shown - staged Data+ETL / BI / Apps runs from the CLI and UI, with "
            "no pipeline rebuilt - is real and screenshotted. Program time/cost figures "
            "are illustrative; benchmark figures are measured on the open Nelakuditi "
            "Migration Benchmark (NMB).")

PAGES = [

    # 1 --- COVER --------------------------------------------------------------
    {"tpl": "storycover"},

    # 2 --- THE CAST -----------------------------------------------------------
    {"tpl": "cast", "kicker": "Dramatis personae",
     "title": "Every great migration needs a small, brave team",
     "intro": "No army. No three-year death march. One executive mandate, one "
     "architect, two developers - and MAYA, the AI swarm that does the heavy lifting.",
     "squad": SQUAD,
     "cast": [
         ("The CEO", "The Mandate", "\"Get us off the legacy warehouse. This year - not "
          "next decade.\""),
         ("The CTO", "The Deployer", "Doesn't panic. Deploys the org's best architect "
          "and backs the plan."),
         ("The Architect", "The Hero", "Picks a tiny elite pod and one harness instead "
          "of a cast of hundreds."),
         ("Dev One", "The Pathfinder", "Wires the source, drives the graph, reviews the "
          "gates - not thousands of lines."),
         ("Dev Two", "The Finisher", "Owns BI + downstream apps, ships parity, keeps the "
          "business live."),
         ("MAYA", "The AI Swarm", "Discovers, builds, certifies, governs - table by "
          "table, gate by gate, at machine speed."),
     ]},

    # 3 --- THE ASK ------------------------------------------------------------
    {"tpl": "scene", "kicker": "Act 0 - The Ask", "eyebrow_hero": H_CHAMPION,
     "title": "The boardroom sets an impossible deadline",
     "quote": "\"Our legacy warehouse is slow, expensive, and a risk. Move everything to "
     "Databricks - the data, the dashboards, and the apps the business runs on. And do "
     "it this year.\"",
     "quote_by": "- The CEO, to a very quiet room",
     "body": [
         ("p", "Every head turned to the CTO. The old playbook said: hire a hundred "
          "consultants, spend three years, hope the numbers match at the end. The CTO "
          "had watched that movie before. It does not end well."),
         ("p", "So the CTO did something different. Instead of an army, they deployed "
          "one top architect - and gave them a single instruction: \"Use MAYA. Bring a "
          "small team. Prove it.\""),
     ]},

    # 4 --- THE PLAN -----------------------------------------------------------
    {"tpl": "scene", "kicker": "Act 0 - The Plan", "eyebrow_hero": H_GUARDIAN,
     "title": "One harness. One project. Three phases.",
     "quote": "\"We don't boil the ocean. We migrate the Data + ETL first and certify "
     "it. Then we add BI. Then the apps. Same project - and we never rebuild a "
     "pipeline.\"",
     "quote_by": "- The Architect, whiteboard marker in hand",
     "body": [
         ("p", "The architect picked two developers and MAYA. The plan fit on one "
          "whiteboard: register the estate once, let MAYA build a provable dependency "
          "graph, then run the migration in gated phases."),
         ("bullets", [
             "Phase 1 - Data + ETL: warehouse, pipelines, procs to a certified "
             "medallion, parity-proven table by table.",
             "Phase 2 - BI / dashboards: converted, parity-checked, republished as "
             "Lakeview + Genie - added later, on top.",
             "Phase 3 - Downstream apps: custom DW apps to Lakebase + Databricks Apps - "
             "added later, on top.",
         ]),
         ("p", "Each phase runs on its own - from the CLI or the UI - on top of the "
          "already-certified estate. No phase ever recomputes the one before it."),
     ]},

    # 5 --- THE HARNESS (12 gates) --------------------------------------------
    {"tpl": "stages", "kicker": "The harness", "title": "Twelve gates, one command center",
     "intro": "MAYA runs a gated, twelve-stage lifecycle. A phase only advances when it "
     "proves itself - so \"done\" always means certified, never \"looks done\".",
     "stages": [
         ("0", "Readiness", "Estate + connections checked"),
         ("1", "Collect + Score", "Normalized dependency graph"),
         ("2", "Replicate (dev)", "RI-preserving 10k sample"),
         ("3", "Specs", "Per-pipeline build contracts"),
         ("4", "Build + Certify (dev)", "Swarm builds + parity-gates"),
         ("5", "BI convert (dev)", "Dashboards converted"),
         ("6", "Full load (prod)", "Historical backfill"),
         ("7", "Build + Certify (prod)", "100% parity certified"),
         ("8", "BI parity (prod)", "Republished + Genie"),
         ("9", "Docs + Publish", "Generated docs + Git"),
         ("10", "Identity + Governance", "Unity Catalog + PII"),
         ("11", "Enablement + Go-live", "Runbooks + cutover"),
     ]},

    # 6 --- ACT I: DATA + ETL (CLI + UI) --------------------------------------
    {"tpl": "cli_ui", "kicker": "Act I - Data + ETL", "eyebrow_hero": H_FOUNDRY,
     "title": "The foundation: every table, certified",
     "intro": "Dev One points MAYA at the warehouse and runs the full pipeline "
     "migration. The AI swarm builds the medallion and certifies every table - schema, "
     "keys, row-counts, checksums, aggregates - at full scale.",
     "cli_title": "From the CLI",
     "code": "# Phase 1 - build + certify the whole warehouse\n"
     "python cli.py run --config project.yaml\n\n"
     "# ...or advance one gate at a time\n"
     "python cli.py run --stage 7\n"
     "run stage 7 [build+certify-prod]: PASS",
     "img": S_ETL,
     "cap": "Mission Control: the Data + ETL pipelines land 100% certified. The estate is "
     "now a trustworthy foundation for everything else."},

    # 7 --- AWARD I ------------------------------------------------------------
    {"tpl": "award", "hero": H_FOUNDRY, "award": "MAYA Hero Award",
     "phase": "Act I - Data + ETL",
     "name": "The Foundry",
     "citation": "For turning a tangled legacy warehouse into a certified Databricks "
     "medallion - and proving it table by table.",
     "wins": [
         "Every table certified: schema, keys, RI, row-count, checksum, aggregates",
         "Sustained soak parity (T+7 / T+14) before the source retires",
         "Weeks, not years - the whole estate, gate-certified",
     ]},

    # 8 --- ACT II: BI / DASHBOARDS (CLI + UI) --------------------------------
    {"tpl": "cli_ui", "kicker": "Act II - BI / Dashboards", "eyebrow_hero": H_STORYTELLER,
     "title": "The dashboards nobody wanted to touch",
     "intro": "Weeks later, the business asks for the dashboards. No problem - and no "
     "rebuild. Dev Two runs ONLY the BI layer on top of the certified estate, from the "
     "CLI or with one click in the UI.",
     "cli_title": "From the CLI",
     "code": "# Phase 2 - add BI later, on the certified estate\n"
     "python cli.py run --scope bi\n"
     "  stage 5 [bi-convert-dev]: PASS\n"
     "  stage 8 [bi-parity+publish-prod]: PASS\n"
     "run --scope bi: (pipelines untouched)",
     "img": S_DASH,
     "cap": "Every dashboard query converted, parity-checked, and republished as Lakeview "
     "with Genie AI/BI - added as its own gated run, no pipeline recomputed."},

    # 9 --- AWARD II -----------------------------------------------------------
    {"tpl": "award", "hero": H_STORYTELLER, "award": "MAYA Hero Award",
     "phase": "Act II - BI / Dashboards",
     "name": "The Storyteller",
     "citation": "For migrating the entire BI layer as a clean add-on run - so the "
     "business kept its dashboards without a single pipeline being rebuilt.",
     "wins": [
         "Dashboard queries converted + result-parity checked",
         "Republished as Lakeview; Genie AI/BI on certified gold",
         "BI-only run - pipelines left completely untouched",
     ]},

    # 10 --- ACT III: DOWNSTREAM APPS (register in UI) ------------------------
    {"tpl": "screens2", "kicker": "Act III - Downstream Apps",
     "title": "Registering a custom app - right from the UI",
     "imgs": [
         (S_APP_BUILDER, "The app builder: import the domain model, define entities / "
          "endpoints / screens, attach backend, API, UI and screenshots."),
         (S_APP_REG, "The Sales Ops Console is registered - entities, endpoints and "
          "screens recognized - ready to migrate whole."),
     ]},

    # 11 --- ACT III cont: run apps (CLI + UI) --------------------------------
    {"tpl": "cli_ui", "kicker": "Act III - Downstream Apps", "eyebrow_hero": H_BUILDER,
     "title": "The apps most migrations abandon",
     "intro": "The sales, ops and supply-chain apps built on the warehouse are usually "
     "left behind. Not here. Dev Two runs ONLY the app layer - the data model becomes a "
     "Lakebase (OLTP) schema and the backend/API/UI become a Databricks App.",
     "cli_title": "From the CLI",
     "code": "# Phase 3 - migrate downstream apps, no rebuild\n"
     "python cli.py run --scope apps\n"
     "  stage 10 [identity+security+governance]: PASS\n"
     "run --scope apps: (pipelines untouched)",
     "img": S_APP_MIGRATED,
     "cap": "The Sales Ops Console: CERTIFIED and deployed - migrated whole to Databricks "
     "Lakebase + Databricks Apps, governed by Unity Catalog."},

    # 12 --- AWARD III ---------------------------------------------------------
    {"tpl": "award", "hero": H_BUILDER, "award": "MAYA Hero Award",
     "phase": "Act III - Downstream Apps",
     "name": "The Builder",
     "citation": "For migrating the apps the business actually clicks on - data model to "
     "Lakebase, backend/API/UI to Databricks Apps, parity-certified end to end.",
     "wins": [
         "Domain model to Databricks Lakebase (managed OLTP) schema",
         "Backend + API + UI to a runnable Databricks App on Unity Catalog",
         "Apps-only run - registered and migrated straight from the UI",
     ]},

    # 13 --- INTERLUDE: no rebuild --------------------------------------------
    {"tpl": "figure", "kicker": "The secret sauce",
     "title": "Three phases, one project - and no pipeline ever rebuilt",
     "img": S_RUNS,
     "caption": "The run history tells the story: a full pipeline migration, then a "
     "BI-only add-on, then an Apps-only add-on. Each later phase rides on the certified "
     "estate - nothing is recomputed, nothing is redone.",
     "note": "Selective add-on runs (--scope bi / --scope apps, or the UI add-on "
     "buttons) execute only their layer once the Data + ETL migration is certified."},

    # 14 --- THE WIN: awards gallery ------------------------------------------
    {"tpl": "awards", "kicker": "The ceremony",
     "title": "Every round, won",
     "intro": "Three phases. Three awards. One small team and MAYA - and a migration "
     "that used to take years, finished in weeks.",
     "medals": [
         (H_FOUNDRY, "The Foundry", "Data + ETL certified"),
         (H_STORYTELLER, "The Storyteller", "BI migrated as an add-on"),
         (H_BUILDER, "The Builder", "Apps to Lakebase + Databricks Apps"),
         (H_GUARDIAN, "The Guardian", "Unity Catalog governance + PII"),
         (H_CHAMPION, "The Champion", "#1 on the open benchmark"),
     ],
     "banner": "Same scope. A fraction of the time, team, and cost - proven, "
     "table-by-table."},

    # 15 --- PROOF: benchmark --------------------------------------------------
    {"tpl": "benchmark", "kicker": "Nelakuditi Migration Benchmark (NMB)",
     "title": "The Champion's trophy is measured, not marketed",
     "mfvi": "assets/nmb_mfvi.png", "radar": "assets/nmb_radar.png",
     "stats": [
         ("98.96", "MAYA MFVI", "composite of 8 dimensions"),
         ("2.6x", "the field", "vs the next-best tool (37.9)"),
         ("8 / 8", "dimensions led", "correctness to sustained parity"),
         ("100%", "measured", "TPC-H / TPC-DS + Northwind / Retail"),
     ],
     "note": "MAYA's scores are measured by running the engine on the open corpus; "
     "competitor scores are cited from public / vendor sources. Benchmark, harness, and "
     "results are open source and reproducible."},

    # 16 --- ABOUT THE AUTHOR --------------------------------------------------
    {"tpl": "author", "kicker": "About the author"},

    # 17 --- CTA / back cover --------------------------------------------------
    {"tpl": "award_cta", "title": "Do you want to win these awards?",
     "lead": "Use MAYA for your migration - and give your team a story like this one.",
     "body": "MAYA is delivered by experts: the team configures your workspaces, "
     "connections and governance and drives the AI swarm to migrate your Data + ETL, "
     "BI, and downstream apps - in phases, in weeks. To model it for your estate or to "
     "get started, reach us:",
     "heroes": [H_FOUNDRY, H_STORYTELLER, H_BUILDER, H_GUARDIAN, H_CHAMPION],
     "ctas": [
         ("Databricks Professional Services & FDE", "the team that delivers "
          "MAYA-driven migrations end to end"),
         ("Email", CONTACT),
         ("Open source", "github.com/vasutechgenie/maya-migrate-to-databricks"),
         ("Benchmark", "github.com/vasutechgenie/nelakuditi-migration-benchmark"),
     ]},
]
