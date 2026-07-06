<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/maya-logo-dark.png">
    <img alt="MAYA - Migration Accelerator" src="docs/assets/maya-logo.png" width="620">
  </picture>
</p>

<h1 align="center">MAYA - Migration Accelerator</h1>

<p align="center">
  <a href="https://github.com/vasutechgenie/maya-migrate-to-databricks/actions/workflows/ci.yml"><img alt="ci" src="https://github.com/vasutechgenie/maya-migrate-to-databricks/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/badge/license-Apache--2.0-blue.svg"></a>
  <a href="pyproject.toml"><img alt="python" src="https://img.shields.io/badge/python-3.9%2B-blue.svg"></a>
</p>

**MAYA** turns *any* data-platform migration **to Databricks** into a **deterministic,
reviewable engineering process** instead of an artisanal rewrite. It reads your exported
source metadata and produces a full **preview** of the migration - one normalized
dependency graph, a provable build order, a per-pipeline contract, and a branded report -
*before anything is built*. Then a **swarm of AI coding agents builds the real pipelines**,
wave by wave, each one self-validating against the source through a strict three-phase
parity gate. The run finishes with a single **whole-system certification**: when every
pipeline and dashboard is certified, the migration is complete and the source can retire.

## The big advantage: compress years into weeks

MAYA is built on deep, hands-on expertise - **AI coding agents**, **Databricks and lakehouse
engineering**, **AI skill/agent creation**, and **large-scale migration validation** - and it
pairs that expertise with **your domain experts**, the people who know what each pipeline
actually means. That combination turns a multi-year rewrite into a governed assembly line:

1. **Collect everything.** Together with your domain experts, MAYA gathers the full estate -
   metadata for every existing pipeline, the pipeline *code*, DDL, views, and the metadata
   sitting in your config/control tables. Nothing is guessed; the source describes itself.
2. **Build the graph and contracts.** MAYA derives one normalized dependency graph and a
   per-pipeline **build contract** for *every* pipeline, with a complete **modernization to
   medallion architecture** (bronze / silver / gold) baked in - not a lift-and-shift.
3. **Preserve every gold table for automated validation.** The gold tables each pipeline
   produces are kept intact and targeted, so parity can be proven *automatically*, table by
   table, against the legacy system.
4. **Give business users a live dashboard.** A ready-made dashboard lets business and program
   stakeholders watch progress - wave by wave, gate by gate - in real time.
5. **Run the AI swarm.** A swarm of AI agents converts and validates the pipelines **in
   waves**, re-proving parity at each step, until the whole system is certified **done**.

> **The surprise factor.** That last phase - actually converting and validating hundreds of
> pipelines - is the part that, done by hand, takes **6 months to 2-3 years**. MAYA crunches
> it into a small fraction of that time. *How* small is the surprise: the compression factor
> scales directly with how well you follow the framework's rules. Clean metadata, honest
> contracts, disciplined domain-expert review, and preserved gold tables all multiply the
> speedup - follow the rules well and the timeline collapses from years to weeks.

**Source-agnostic by design.** The core never sees your source technology - it only ever
operates on a normalized graph. A thin **adapter** is the *only* piece that understands a
given source, so the same engine migrates:

| Source | Adapter status |
|---|---|
| **Azure Synapse** (SQL DW + Automic/UC4) | reference adapter (shipped) |
| **PostgreSQL** (OLTP/OLAP marts + PL/pgSQL jobs) | reference adapter (shipped) |
| **Snowflake** | adapter (SourceAdapter contract) |
| **Amazon Redshift** | adapter |
| **Hadoop / Hive / Spark (on-prem)** | adapter |
| **Microsoft SQL Server / SSIS** | adapter |
| **Teradata**, **Oracle**, **Netezza** | adapter |
| **Informatica / ADF / dbt** (orchestration) | adapter |

Every one of these lands the *same* normalized graph, so build order, contracts, engines,
the sampler, and the three-phase parity gate are identical regardless of where you're coming
from. Onboarding a new source is "write an adapter," not "fork the tool" - see the
[adapter authoring guide](docs/12_adapter_authoring_guide.md).

The name says how the *validation* works. *Maya* means "illusion": the first thing each
agent does after building a pipeline is prove its logic against a small **illusion of
production** - every table, but only a few thousand rows each - so correctness is proven
cheaply before the one expensive full-scale run. The illusion is the cheap first gate
*inside* the build loop, not the deliverable; only when logic is proven does MAYA prove
parity at full scale on production-copied data, and then keep re-proving it while both
systems run in parallel, because a pipeline that matches at cutover can still **drift** a
week later.

> Everything in this repo is source-agnostic core + reference **Synapse** and **PostgreSQL**
> adapters + a fully runnable synthetic demo (**Northwind**, Synapse), plus a second bundled
> **retail** source estate (PostgreSQL) that exercises the Postgres adapter. No customer data,
> no credentials, no live connections required.

```mermaid
flowchart LR
  ready["Stage 0: collect identity/access/secrets/classification"] --> preview["PREVIEW: graph + order + contract + report (nothing built yet)"]
  preview --> swarm["AI agent swarm builds REAL pipelines (wave N)"]
  swarm --> devA["MAYA-Dev: illusion sample (logic)"]
  devA -->|"fail"| drift["Drift loop: fix code"]
  drift --> devA
  devA -->|"logic proven"| sitB["MAYA-SIT: full-scale parity"]
  sitB --> barrier{"whole wave provisional?"}
  barrier -->|"no"| swarm
  barrier -->|"yes, next wave"| swarm
  barrier -->|"all waves"| soak["MAYA-Soak: parallel run T+7 & T+14"]
  soak -->|"zero drift + BI done"| ident["Stage 10: UC grants + masks + secrets + governance"]
  ident --> enable["Stage 11: training + cutover/rollback + day-2 ops"]
  enable -->|"go/no-go all green"| sys["System certification: MIGRATION COMPLETE"]
```

## The MAYA web application

Everything above runs from the open-source CLI. There is also a full **MAYA web application** -
a futuristic command center (FastAPI + PostgreSQL + React) that drives the entire twelve-stage
lifecycle live against real Databricks workspaces, with a knowledge base, an AI-assisted intake,
a real-time swarm view, a dependency-graph explorer, per-stage evidence, and an Impact/ROI
dashboard.

> ### This application is delivered by experts - it is not self-service
> The screenshots below are from the MAYA web application. **It is not an open-source, self-service
> product.** Standing it up and running a real migration end to end requires the MAYA experts to
> configure workspaces, connections, and governance and to drive the AI swarm. To evaluate or
> engage it for your migration, reach the **Databricks Professional Services** team or email
> **[srinivas.nelakuditi@databricks.com](mailto:srinivas.nelakuditi@databricks.com)**.

### Command center

![Login](docs/screenshots/01_login.png)
![Mission Control - lifecycle progress and Impact/ROI](docs/screenshots/02_mission_control.png)
![Knowledge Base](docs/screenshots/03_knowledge_base.png)
![Live Swarm](docs/screenshots/04_live_swarm.png)
![Graph Explorer](docs/screenshots/05_graph_explorer.png)

### The twelve lifecycle stages

![Stage 0 - Readiness](docs/screenshots/10_stage00_readiness.png)
![Stage 1 - Collect + Score](docs/screenshots/11_stage01_score.png)
![Stage 2 - Replicate (dev)](docs/screenshots/12_stage02_replicate.png)
![Stage 3 - Specs](docs/screenshots/13_stage03_specs.png)
![Stage 4 - Build + Certify (dev)](docs/screenshots/14_stage04_build_certify_dev.png)
![Stage 5 - BI Convert (dev)](docs/screenshots/15_stage05_bi_convert_dev.png)
![Stage 6 - Full Load (prod)](docs/screenshots/16_stage06_full_load.png)
![Stage 7 - Build + Certify (prod)](docs/screenshots/17_stage07_build_certify_prod.png)
![Stage 8 - BI Parity + Publish](docs/screenshots/18_stage08_bi_parity_publish.png)
![Stage 9 - Docs + Publish](docs/screenshots/19_stage09_docs.png)
![Stage 10 - Identity + Security](docs/screenshots/20_stage10_identity.png)
![Stage 11 - Enablement + Go-live](docs/screenshots/21_stage11_enablement.png)

### Operate

![Run History](docs/screenshots/30_runs.png)
![Artifacts](docs/screenshots/31_artifacts.png)
![Connections](docs/screenshots/32_connections.png)
![Admin / RBAC](docs/screenshots/33_admin.png)
![New Project](docs/screenshots/34_new_project.png)

## 60-second quickstart (the Northwind demo)
```bash
git clone https://github.com/vasutechgenie/maya-migrate-to-databricks
cd maya-migrate-to-databricks
pip install -r requirements.txt        # reportlab, pypdf, PyYAML

make demo     # the twelve-stage full-lifecycle flow, end to end, offline (see below)
make test     # the deterministic goldens for the demo
```
`make demo` runs MAYA's **twelve gated stages** on `examples/northwind/` (a fictional
retailer moving to Databricks - Synapse is the worked source, but the flow is identical
for any source) with the deterministic **offline agent driver**, so it runs end to end
with zero external calls. It writes every artifact to `examples/northwind/out/`: the
collected identity/access/secrets/classification estate, a normalized graph and verified
build order, a 100% traversability score, a whole-estate test-catalog replication script
with referential-integrity synthetic data, one spec PDF per pipeline, the swarm-built +
topologically-certified `gates.json`, the migrated BI layer (Lakeview/Genie), full
generated docs, the Unity Catalog security model (grants + masks + secrets + governance),
and the enablement + cutover/rollback + day-2 ops pack.

### The twelve stages (full lifecycle)
Stages 1-8 migrate and certify the **data + BI** across two explicit phases - dev (a ~10k
RI-preserving sample) and prod (the full/historical backfill) - using the **same pipeline
and BI code** in both. Stage 0 collects the **non-data** estate up front, and Stages 9-11
finish the migration the way a real program does - docs, security, people, and operations.

```bash
make demo                                          # run all twelve stages in order
python3 cli.py run --stage all --config examples/northwind/northwind.yaml
python3 cli.py run --stage 7   --config examples/northwind/northwind.yaml   # one stage
```
| Stage | Command | Gate |
|---|---|---|
| 0 readiness | `cli.py readiness` | identity/access/secrets/classification collected + consistent |
| 1 collect + score | `cli.py score` | 100% traversable; all tables/views/externals identified |
| 2 replicate (dev) | `cli.py replicate` | every table+view in the test catalog, RI-filled on a ~10k sample |
| 3 specs | `cli.py specs` | one spec PDF per pipeline |
| 4 build + certify (dev) | `cli.py build` | swarm builds the converted SQL dev-green on the sample, in topo order |
| 5 BI convert + dev-certify (dev) | `cli.py run --stage 5` | every dashboard query converted + runs clean on the sample gold |
| 6 full load + historical (prod) | `cli.py run --stage 6` | full/historical source backfilled for every pipeline |
| 7 build + certify (prod) | `cli.py run --stage 7` | the SAME code CERTIFIED to 100% parity on real data, in topo order |
| 8 BI parity + publish (prod) | `cli.py bi run` | the SAME queries parity-checked on full gold + republished + Genie |
| 9 docs + publish | `cli.py docs` + `cli.py publish` | full docs generated + committed |
| 10 identity + security + governance | `cli.py identity` | source grant matrix mapped 1:1 to UC; every PII column masked; every credential scoped |
| 11 enablement + go-live | `cli.py enablement` | training + runbooks + cutover/rollback + day-2 ops; all go/no-go checks green |

Dev (stage 4) and prod (stage 7) build the identical authored SQL, and dev BI (stage 5)
and prod BI (stage 8) run the identical converted queries; a prod parity fix is persisted
back to the single source of truth so the two phases never diverge.

The swarm behind the build stages 4/7 (and the apply path for stages 10-11) runs via `agents.driver` in the project YAML:
`offline` (default, deterministic, no LLM - what the demo uses) or `cursor` (real LLM
coding agents via the Cursor SDK, needs `CURSOR_API_KEY`).

### Primitives (unchanged - the stages call these under the hood)
```bash
python3 cli.py graph    --config examples/northwind/northwind.yaml   # normalized graph
python3 cli.py order    --config examples/northwind/northwind.yaml   # build waves
python3 cli.py verify   --config examples/northwind/northwind.yaml   # independent order check
python3 cli.py context  --config examples/northwind/northwind.yaml   # per-pipeline contracts
python3 cli.py report   --config examples/northwind/northwind.yaml   # branded PDF
python3 cli.py maya sample --config examples/northwind/northwind.yaml --pipeline nw_build_sales
python3 cli.py validate --config examples/northwind/northwind.yaml --pipeline nw_build_marts --env soak
python3 cli.py certify  --config examples/northwind/northwind.yaml --gates examples/northwind/out/gates.json
```

## The MAYA validation technique (two-phase + sustained soak)
| Phase | Data | Proves | Cost |
|---|---|---|---|
| **MAYA-Dev** | every table, sampled to N rows (default 10k) | logic is correct: schema, keys, referential integrity, no-extra-output, idempotency, transform spot-checks | tiny |
| **MAYA-SIT** | production-copied data (full volume) | full-scale parity: all 10 checks incl. row-count, checksum, aggregates, point-in-time (**provisional cert**) | paid once, when logic is already right |
| **MAYA-Soak** | live parallel loads at T+7 & T+14 | **sustained** parity: all 10 on the cumulative table **and** the incremental delta, so slow incremental-logic drift is caught (**final cert**) | two scheduled runs per window |

**Gate rule:** MAYA-Dev AND MAYA-SIT green earns a **provisional** certification; the
pipeline then runs in parallel with the source and must re-prove parity at every soak
window (default T+7, T+14) with **zero drift** for **final** certification. Point-in-time
parity proves *state*; the soak proves the *ongoing incremental logic* stays equal over
time. Sampling is referential-integrity-preserving (seed rows + foreign-key closure) so
joins actually resolve on the sample.

## How it works
*Preview (nothing is built yet - a human can review the plan first):*
1. **Adapter** parses your exported source (Synapse, Snowflake, Redshift, Hadoop/Hive, SQL Server, Teradata, Oracle, ...) into a normalized graph (`objects.csv` / `edges.csv`) - the single boundary between "your source" and the source-agnostic core.
2. **Order** computes a topological build order (waves) via Tarjan SCC + longest-path layering.
3. **Verify** re-derives the order with *different* algorithms (Kosaraju + memoized DFS + Kahn) and proves it correct - an independent check, not a rubber stamp.
4. **Context** emits a deterministic per-pipeline contract: prereqs, produced tables (tagged bronze/silver/gold), parity targets, reachable procs, and a data-flow diagram.
5. **Report** - a branded PDF previewing waves, engines, parity, and connections.

*Build + certify (the AI agent swarm turns the preview into the real lakehouse):*
6. **Orchestrate** - a pool of AI coding agents drains each wave's queue in parallel and builds the **real** pipelines with the reusable **engines E1-E7** (SQL-first), translating the actual source logic - never inventing.
7. **MAYA sample / validate** - each agent proves its pipeline on the illusion of prod (logic), then at scale on prod-copied data (MAYA-SIT), then re-proves it in parallel run (MAYA-Soak, T+7/T+14). A **wave advances only when every pipeline in it is provisionally certified.**
8. **Certify** - `maya certify` rolls all per-pipeline gates and BI across all waves into one system state: `MIGRATION_IN_PROGRESS` -> `SYSTEM_PROVISIONAL` -> `MIGRATION_COMPLETE`. Only `MIGRATION_COMPLETE` clears the source for retirement.

## What is reusable vs per-source
| Reusable core (this repo) | Per-source adapter (you implement) |
|---|---|
| graph model, build order + independent verifier | collect the source artifacts |
| contract + classifier, engine catalog (E1-E7) | parse artifacts -> normalized graph |
| MAYA sampler + 3-phase parity framework | index source DDL |
| agent orchestration, BI migration | extract connection inventory |
| branded PDF reports + dashboard DDL | dialect translate (source SQL -> Spark) |

Roughly 70-80% of a migration is the reusable core; 20-30% is the adapter. See the
[adapter authoring guide](docs/12_adapter_authoring_guide.md).

## Full-lifecycle coverage
A real migration is more than pipelines. MAYA gates every dimension a large program has to
land - each is a real, tested stage with an offline demo artifact, not a slide:

| Migration concern | MAYA stage(s) | Evidence / artifact |
|---|---|---|
| Data pipelines + parity (dev sample -> prod full) | 1-4, 6-7 | `gates.json` (CERTIFIED), MAYA dev/SIT/soak |
| BI / dashboards (dev-certify -> prod parity + publish) | 5 + 8 | `stage5_bi_dev_gate.json`, `stage5_bi_gate.json`, republished + Genie/Lakeview |
| Users / groups / roles / service principals (RBAC) | 0 + 10 | `readiness/principals.csv`, UC grants |
| Unity Catalog grants, RLS + column masking | 10 | `stage10_identity.sql`, access-parity gate |
| Secrets / credentials | 0 + 10 | `readiness/secrets.csv`, secret scope |
| Data classification / PII / compliance | 0 + 10 | `readiness/classification.csv`, masks, `security_facts.json` |
| Data governance (owners, tags, glossary, lineage) | 9 + 10 | generated docs, `ALTER SCHEMA ... OWNER/TAGS` |
| Training / enablement / change management | 11 | `enablement/training/*`, runbooks |
| Cutover / rollback / decommission | 11 | cutover + rollback plans, decommission checklist |
| Day-2 ops (monitoring, alerting, cost, DR) | 11 | `enablement/operations.{md,json}` |

## Repo layout
```
core/               source-agnostic library (graph, order, contract, engines,
                    validation, maya, bi, orchestration, branding, reports;
                    twelve-stage: readiness, score, replicate, pipeline_spec,
                    conformance, bi, docs, publish, identity, enablement, stages)
core/agents/        AI coding-agent swarm driver (offline + Cursor SDK backends)
adapters/           SourceAdapter ABC + reference Synapse and PostgreSQL adapters; BI connectors
templates/          project/engine/maya/bi config, dashboard DDL, agent prompts
examples/northwind/ the runnable synthetic demo (graph, DDL, config, BI export,
                    artifacts/security: principals/grants/secrets/classification)
examples/retail/    second source estate: a PostgreSQL retail warehouse (postgres/schema.sql
                    + normalized graph, DDL, BI export, security) for the Postgres adapter
docs/               methodology, MAYA validation, execution plan, guides
docs/tutorial/      hands-on walkthrough (01-10) using the Northwind demo
tests/              pytest suite asserting the Northwind goldens
blog/               "Migrating with MAYA" hands-on article series + figures
cli.py              phase + twelve-stage entrypoint (run --stage N|all)
```

## Oops - my migration project has gone supersonic

*Want the world's most efficient, fastest migration to Databricks?*

Most migrations are art projects - hand-rewrites, "validate the important ones," pray at
cutover, then watch the result quietly drift in production. MAYA is the opposite:
**deterministic and provable**. A dependency graph, a build order you can prove correct, a
contract every workload must pass, and an **AI agent swarm** that builds and certifies the
estate wave by wave to "migration complete."

The swarm is the surprise: **6 months to 3 years of manual work, crunched by a factor set
only by how well you follow the framework's rules.**

### The MAYA Concept Series (15 articles)
The full narrative behind MAYA - why migrations take years, and how to turn one into a
governed, provable assembly line:

1. [The Migration Factory: why enterprise data migrations take years](https://www.linkedin.com/pulse/migration-factory-why-enterprise-data-migrations-take-nelakuditi-uyf9c)
2. [Optimizing the wrong thing: code conversion is the easy part](https://www.linkedin.com/pulse/optimizing-wrong-thing-code-conversion-easy-part-srinivas-nelakuditi-9hipc)
3. [Pillar 1 - Deterministic process: no guessing, no heroics](https://www.linkedin.com/pulse/pillar-1-deterministic-process-guessing-heroics-srinivas-nelakuditi-3nfjc)
4. [Pillar 2 - Context: the dependency graph is the foundation](https://www.linkedin.com/pulse/pillar-2-context-dependency-graph-foundation-srinivas-nelakuditi-mjooc)
5. [Knowing what to migrate (and what to leave behind)](https://www.linkedin.com/pulse/knowing-what-migrate-leave-behind-srinivas-nelakuditi-oj6vc)
6. [Sequencing the work: waves you can prove are correct](https://www.linkedin.com/pulse/sequencing-work-waves-you-can-prove-correct-srinivas-nelakuditi-wbqgc)
7. [Pillar 3 - Rules: stop prompting, start engineering](https://www.linkedin.com/pulse/pillar-3-rules-stop-prompting-start-engineering-srinivas-nelakuditi-scz9c)
8. [Proving completeness: the contract every workload must pass](https://www.linkedin.com/pulse/proving-completeness-contract-every-workload-must-pass-nelakuditi-kpf5c)
9. [Pillar 4 - Automation, last: where AI actually belongs](https://www.linkedin.com/pulse/pillar-4-automation-last-where-ai-actually-belongs-nelakuditi-ufzyc)
10. [Validating business correctness: no partial credit](https://www.linkedin.com/pulse/validating-business-correctness-partial-credit-srinivas-nelakuditi-rkgdc)
11. [The illusion of production: cutting validation cost without cutting rigor](https://www.linkedin.com/pulse/illusion-production-cutting-validation-cost-without-rigor-nelakuditi-qylzc)
12. [The drift loop: what to do when the numbers don't match](https://www.linkedin.com/pulse/drift-loop-what-do-when-numbers-dont-match-srinivas-nelakuditi-xjduc)
13. [Parallelism without chaos: agent pools and wave barriers](https://www.linkedin.com/pulse/parallelism-without-chaos-agent-pools-wave-barriers-nelakuditi-q09zc)
14. [Beyond data: migrating the BI layer - and bringing AI to it](https://www.linkedin.com/pulse/beyond-data-migrating-bi-layer-bringing-ai-srinivas-nelakuditi-xkrwc)
15. [From art to engineering: a repeatable operating model for modernization](https://www.linkedin.com/pulse/from-art-engineering-repeatable-operating-model-srinivas-nelakuditi-ygbqc)

Prefer to *do* rather than read? The same journey is a runnable, hands-on walkthrough on the
Northwind demo: [docs/tutorial/](docs/tutorial/README.md).

## Documentation
- **New here?** Do the hands-on tutorial: [docs/tutorial/](docs/tutorial/README.md) (10 parts, built on Northwind).
- **The method:** [docs/01_methodology.md](docs/01_methodology.md).
- **The validation technique:** [docs/08_maya_two_phase_validation.md](docs/08_maya_two_phase_validation.md) and [docs/07_validation_framework.md](docs/07_validation_framework.md).
- **BI migration + Genie AI/BI:** [docs/13_bi_layer_migration.md](docs/13_bi_layer_migration.md).
- **Non-data estate (Stage 0):** [docs/00_readiness.md](docs/00_readiness.md).
- **Identity, security & governance (Stage 10):** [docs/14_identity_security_governance.md](docs/14_identity_security_governance.md).
- **Enablement & training (Stage 11):** [docs/15_enablement_training.md](docs/15_enablement_training.md).
- **Cutover, rollback & day-2 ops (Stage 11):** [docs/16_cutover_rollback_operations.md](docs/16_cutover_rollback_operations.md).
- **Onboard a new source:** [docs/12_adapter_authoring_guide.md](docs/12_adapter_authoring_guide.md).
- **Release notes:** [CHANGELOG.md](CHANGELOG.md).
- **How MAYA measures up:** the [Nelakuditi Migration Benchmark (NMB)](https://github.com/vasutechgenie/nelakuditi-migration-benchmark) -
  a neutral, reproducible OSS benchmark for enterprise migrations from any source
  technology to any target technology (Databricks is the first-class reference
  target). MAYA is the Databricks-target reference adapter: its numbers there are
  **measured** by running this engine on TPC-H/TPC-DS + Northwind/Retail; competitor
  numbers are cited. MAYA leads every dimension on evidence (certified correctness,
  determinism, sustained parity).

## Running it on your estate (any source -> Databricks)
Point an adapter at your exported metadata and copy `templates/project_config.example.yaml`
to `my_project.yaml`. Because the core is source-agnostic, **the target is always Databricks
but the source can be anything** - you only implement the adapter for your source.

A `SourceAdapter` is small and mechanical: it does five things, then hands off to the shared
core forever after.

1. **Collect** the source artifacts (DDL, orchestration/ETL exports, catalog metadata).
2. **Parse** them into the normalized graph (`objects.csv` / `edges.csv`).
3. **Index** source DDL so parity checks know the columns/keys.
4. **Inventory** connections (JDBC/ADLS/S3/API) for the connection + dashboard story.
5. **Translate** dialect where needed (source SQL -> Spark SQL).

The reference **Synapse** adapter is fully implemented as the worked example and template.
Other sources - **Snowflake, Redshift, Hadoop/Hive, SQL Server/SSIS, Teradata, Oracle,
Netezza, Informatica, ADF, dbt** - are adapter work that follows the exact same
normalized-graph contract; nothing in the core changes. See the
[adapter authoring guide](docs/12_adapter_authoring_guide.md).

## Contributing
Contributions welcome - see [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md). Keep the core source-agnostic and deterministic;
new adapters should ship with a small synthetic example like Northwind.

## About the author

**Srinivas Nelakuditi** - creator of MAYA; data platform architect and AI/ML engineer
who builds at the intersection of large-scale data migrations and applied machine learning
on Databricks and the lakehouse.

MAYA didn't start as a library - it grew out of hands-on migration work where the hard part
was never writing SQL, it was *proving* that hundreds of rebuilt pipelines produced exactly
the same numbers as the legacy system, and kept producing them after cutover. Srinivas built
MAYA to replace that anxiety with evidence: turn a migration into a **deterministic,
reviewable engineering process** - one normalized dependency graph, a provable build order,
a per-pipeline contract, and a three-phase parity gate (dev -> SIT -> soak) that certifies
correctness cheaply, then at scale, then *over time*.

What he works on and cares about:
- **AI / ML engineering** - training and **fine-tuning models** (full and parameter-efficient,
  e.g. LoRA/QLoRA), and shipping them into real workflows, not just notebooks.
- **Retrieval-augmented generation (RAG)** - designing and building RAG systems end to end:
  chunking, embeddings, vector search, retrieval and re-ranking, and grounded generation.
- **Cutting-edge open-source models** - hands-on with the latest OSS LLMs and the surrounding
  ecosystem, evaluating and adopting new models as the frontier moves.
- **Benchmarking & evaluation** - rigorously benchmarking models, prompting/retrieval
  strategies, and fine-tuning approaches to pick what actually works on cost, latency, and quality.
- **Data platform migrations at scale** - Synapse, Snowflake, Redshift, Hadoop/Hive, SQL
  Server, Teradata, Oracle -> Databricks, via a clean source-adapter model.
- **Lakehouse & medallion architecture** - bronze/silver/gold done deterministically, not by hand.
- **Data quality & parity validation** - the idea that a migration isn't "done" until it's
  *provably* equal, including sustained parity that catches slow post-cutover drift.
- **Turning artisanal work into engineering** - graphs, contracts, reusable engines, tests,
  and CI instead of one-off rewrites.

The same instinct runs through his AI and data work: replace guesswork with **measurable,
reproducible evidence** - benchmark before you commit, validate before you certify.

He also writes the hands-on [**"Migrating with MAYA"**](blog/README.md) series - a 10-part,
step-by-step field guide that builds the entire workflow on the runnable Northwind demo.

**Connect / collaborate:**
- GitHub: [@vasutechgenie](https://github.com/vasutechgenie)
- Migrating a platform to Databricks and want to do it deterministically? Open an
  [issue](https://github.com/vasutechgenie/maya-migrate-to-databricks/issues) or reach out.

If MAYA helps you, a **star** on the repo genuinely helps others find it.

## License
[Apache-2.0](LICENSE). "Databricks", "Azure Synapse", "Snowflake", "Amazon Redshift",
"Apache Hadoop/Hive", "Microsoft SQL Server", "Teradata", "Oracle" and other product names
are trademarks of their respective owners; this project is not affiliated with any of them
and names them only to describe interoperability. See [NOTICE](NOTICE).

Created by **Srinivas Nelakuditi**.
