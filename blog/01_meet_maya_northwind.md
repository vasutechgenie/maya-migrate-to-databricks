---
title: "Migrating with MAYA (Part 1): Deterministic Migration is Open Source - Meet Northwind"
hook: "A migration you can clone and run end to end in seconds - and the fictional retailer we'll rebuild together."
hashtags: "#Databricks #DataEngineering #Synapse #Lakehouse #DataMigration #OpenSource #MAYA"
author: "Srinivas Nelakuditi"
image: "figures/01_meet_maya_northwind.png"
---

![Figure 1. MAYA turns a migration into a deterministic pipeline you can clone and run end to end in seconds.](figures/01_meet_maya_northwind.png)

*Figure 1. MAYA turns a migration into a deterministic pipeline you can clone and run end to end in seconds.*

**By Srinivas Nelakuditi**  |  Creator of MAYA - an open-source, deterministic migration accelerator

*Migrating with MAYA - Part 1 of 10*

# Deterministic migration is open source - meet Northwind

Most platform migrations are run like art projects. A talented team rewrites pipelines
by hand, validates "the important ones," and hopes the numbers hold. It works until it
doesn't - and you find out weeks later, in production, when a report quietly disagrees
with the system it replaced.

MAYA takes the opposite stance: a migration should be a **deterministic pipeline**, not
an artisanal rewrite. Same inputs, same outputs, every time. Today I'm open-sourcing the
whole thing under Apache-2.0, and this 10-part series will walk the entire workflow on a
small, fully runnable demo you can clone right now.

## The 60-second version

```bash
git clone https://github.com/vasutechgenie/maya-migrate-to-databricks
cd maya-migrate-to-databricks
pip install -r requirements.txt
make demo
```

`make demo` runs the full workflow against a bundled example and writes every artifact to
`examples/northwind/out/`: a normalized dependency graph, an independently verified build
order, a build contract for every pipeline (the preview), the agent work queue by wave,
referential-integrity-preserving sample SQL, parity SQL for three validation phases, the
whole-system certification rollup, and a branded PDF report. No cloud account, no
credentials, no live source system required.

## Meet Northwind

The demo is **Northwind**, a fictional retailer moving from Azure Synapse to Databricks.
It's deliberately small but realistic: eight pipelines, around twenty-five tables and
views, four external connections, and a clean multi-wave dependency structure. It has an
orchestrator that fans out to children, a metadata-driven ingestion job, a file-intake
job, an external "invoke-in-place" job, a chain of SQL transforms across bronze / silver
/ gold, and a replication job to a serving layer. In other words, the same shapes you
meet on a real estate - just synthetic, so it's safe to publish and safe to break.

Northwind isn't just a toy for the blog. It's also the project's **test fixture**: the
pytest suite asserts on Northwind's exact waves, classifications, and parity targets, so
the examples in these posts are guaranteed to stay true as the code evolves.

## The phases

Everything MAYA does is a function of one normalized graph. The workflow splits into a
**preview** (nothing is built yet - you can review the plan before a line of code is
written) and a **build + certify** loop (a swarm of AI agents turns the plan into the real
lakehouse, wave by wave):

Preview:

1. **graph** - the adapter parses your source into `objects.csv` + `edges.csv`.
2. **order** - topological build order (waves) via SCC + longest-path layering.
3. **verify** - a *different* set of algorithms re-derives the order and proves it.
4. **context** - a deterministic build contract per pipeline (needs / logic / output).
5. **report** - a branded PDF preview of the whole migration.

Build + certify:

6. **orchestrate** - a pool of AI agents drains each wave's queue and builds the *real* pipelines.
7. **sample** - build a small "illusion of production" for cheap logic proofs.
8. **validate** - prove parity dev -> sit -> soak, with no partial credit.
9. **certify** - the whole-system rollup: the migration is complete only when every pipeline (and dashboard) is certified.

The thing I care most about is that none of this is guessed. The graph comes from the
source; the order is computed and independently checked; the contracts are derived, not
authored; the agents build inside those contracts; and certification is binary and
machine-verified - per pipeline, then for the whole system.

## Why "MAYA"?

*Maya* means "illusion," and it names the validation trick at the heart of the tool. In
dev you build against a small **illusion of production** - every table, but only a few
thousand rows each - so you prove the logic is correct cheaply. Only then do you prove it
at full scale on production-copied data. And because a pipeline that matches at cutover
can still drift a week later, MAYA then runs both systems in parallel and re-proves parity
over time. We'll get deep into all three phases later in the series.

## Where we're headed

Over the next nine parts we'll follow Northwind through the whole pipeline: how MAYA reads
any source, how it builds and verifies the dependency graph and the wave plan, how the
per-pipeline contract is derived, how seven reusable engines cover the estate, how a swarm
of AI agents builds the estate wave by wave, and how the three-phase parity gate (Dev, SIT,
and the sustained Soak) certifies each table - up to the whole-system certification that
declares the migration complete. We'll finish with the live dashboard, BI/Genie migration,
and cutover - and how to point MAYA at your own estate.

If you want to read ahead, the repo has a durable, versioned version of this same
walkthrough under `docs/tutorial/`. But the best way to follow along is to clone it and run
`make demo` as you read.

**Part 1 of 10 - Migrating with MAYA.** Next up, Part 2: "The Adapter Model". The whole framework is open source - clone it and run `make demo`.
