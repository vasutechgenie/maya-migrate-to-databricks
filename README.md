# MAYA - Migration Accelerator

[![ci](https://github.com/vasutechgenie/maya-migrate-to-databricks/actions/workflows/ci.yml/badge.svg)](https://github.com/vasutechgenie/maya-migrate-to-databricks/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

**MAYA** turns *any* data-platform migration **to Databricks** into a **deterministic,
reviewable engineering process** instead of an artisanal rewrite. It reads your exported
source metadata, builds one normalized dependency graph, computes a provable build order,
emits a per-pipeline build contract, and proves every rebuilt table against the source with
a strict, three-phase parity gate.

**Source-agnostic by design.** The core never sees your source technology - it only ever
operates on a normalized graph. A thin **adapter** is the *only* piece that understands a
given source, so the same engine migrates:

| Source | Adapter status |
|---|---|
| **Azure Synapse** (SQL DW + Automic/UC4) | reference adapter (shipped) |
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

The name says how the validation works. *Maya* means "illusion": in dev you build against a
small **illusion of production** - every table, but only a few thousand rows each - so you
prove the logic is correct cheaply, and only then prove it at full scale on
production-copied data. Then both systems run in parallel and MAYA re-proves parity over
time, because a pipeline that matches at cutover can still **drift** a week later.

> Everything in this repo is source-agnostic core + a reference Synapse adapter + a fully
> runnable synthetic demo (**Northwind**). No customer data, no credentials, no live
> connections required.

```mermaid
flowchart LR
  build["Agent builds pipeline"] --> devA["MAYA-Dev: 10k-row sample (logic)"]
  devA -->|"logic proven"| sitB["MAYA-SIT: full-scale parity on prod copy"]
  sitB -->|"scale proven"| prov["Provisional cert"]
  prov --> soak["MAYA-Soak: parallel run, T+7 & T+14"]
  soak -->|"zero drift"| cert["FINAL certified"]
  devA -->|"fail"| drift["Drift loop: fix code"]
  drift --> devA
```

## 60-second quickstart (the Northwind demo)
```bash
git clone https://github.com/vasutechgenie/maya-migrate-to-databricks
cd maya-migrate-to-databricks
pip install -r requirements.txt        # reportlab, pypdf, PyYAML

make demo     # graph -> order -> verify -> context -> sample -> validate -> report -> bi
make test     # the deterministic goldens for the demo
```
`make demo` runs the whole pipeline on `examples/northwind/` (a fictional retailer moving
to Databricks - Synapse is used as the worked source, but the flow is identical for any
source) and writes every artifact to `examples/northwind/out/`:
a normalized graph, a verified 5-wave build order, per-pipeline contracts, RI-preserving
dev sample SQL, MAYA parity SQL for dev/sit/soak, and a branded PDF report.

Run a single phase yourself:
```bash
python3 cli.py graph    --config examples/northwind/northwind.yaml
python3 cli.py order    --config examples/northwind/northwind.yaml
python3 cli.py verify   --config examples/northwind/northwind.yaml
python3 cli.py context  --config examples/northwind/northwind.yaml
python3 cli.py maya sample --config examples/northwind/northwind.yaml --pipeline nw_build_sales
python3 cli.py validate --config examples/northwind/northwind.yaml --pipeline nw_build_marts --env soak
python3 cli.py report   --config examples/northwind/northwind.yaml
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
1. **Adapter** parses your exported source (Synapse, Snowflake, Redshift, Hadoop/Hive, SQL Server, Teradata, Oracle, ...) into a normalized graph (`objects.csv` / `edges.csv`) - the single boundary between "your source" and the source-agnostic core.
2. **Order** computes a topological build order (waves) via Tarjan SCC + longest-path layering.
3. **Verify** re-derives the order with *different* algorithms (Kosaraju + memoized DFS + Kahn) and proves it correct - an independent check, not a rubber stamp.
4. **Context** emits a deterministic per-pipeline contract: prereqs, produced tables (tagged bronze/silver/gold), parity targets, reachable procs, and a data-flow diagram.
5. **Engines (E1-E7)** - most pipelines are configuration + SQL, not bespoke code.
6. **MAYA sample / validate** - build the illusion of prod, then prove parity dev -> sit -> soak.
7. **Report** - a branded PDF summarizing waves, engines, parity, and connections.

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

## Repo layout
```
core/               source-agnostic library (graph, order, contract, engines,
                    validation, maya, bi, orchestration, branding, reports)
adapters/           SourceAdapter ABC + reference Synapse adapter; BI connectors
templates/          project/engine/maya/bi config, dashboard DDL, agent prompts
examples/northwind/ the runnable synthetic demo (graph, DDL, config, BI export)
docs/               methodology, MAYA validation, execution plan, guides
docs/tutorial/      hands-on walkthrough (01-10) using the Northwind demo
tests/              pytest suite asserting the Northwind goldens
blog/               "Migrating with MAYA" hands-on article series + figures
cli.py              phase entrypoint
```

## Documentation
- **New here?** Do the hands-on tutorial: [docs/tutorial/](docs/tutorial/README.md) (10 parts, built on Northwind).
- **The method:** [docs/01_methodology.md](docs/01_methodology.md).
- **The validation technique:** [docs/08_maya_two_phase_validation.md](docs/08_maya_two_phase_validation.md) and [docs/07_validation_framework.md](docs/07_validation_framework.md).
- **BI migration + Genie AI/BI:** [docs/13_bi_layer_migration.md](docs/13_bi_layer_migration.md).
- **Onboard a new source:** [docs/12_adapter_authoring_guide.md](docs/12_adapter_authoring_guide.md).

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

**Srinivas Nelakuditi** - creator of MAYA; data platform architect and engineer focused on
large-scale migrations to Databricks and the lakehouse.

MAYA didn't start as a library - it grew out of hands-on migration work where the hard part
was never writing SQL, it was *proving* that hundreds of rebuilt pipelines produced exactly
the same numbers as the legacy system, and kept producing them after cutover. Srinivas built
MAYA to replace that anxiety with evidence: turn a migration into a **deterministic,
reviewable engineering process** - one normalized dependency graph, a provable build order,
a per-pipeline contract, and a three-phase parity gate (dev -> SIT -> soak) that certifies
correctness cheaply, then at scale, then *over time*.

What he works on and cares about:
- **Data platform migrations at scale** - Synapse, Snowflake, Redshift, Hadoop/Hive, SQL
  Server, Teradata, Oracle -> Databricks, via a clean source-adapter model.
- **Lakehouse & medallion architecture** - bronze/silver/gold done deterministically, not by hand.
- **Data quality & parity validation** - the idea that a migration isn't "done" until it's
  *provably* equal, including sustained parity that catches slow post-cutover drift.
- **Turning artisanal work into engineering** - graphs, contracts, reusable engines, tests,
  and CI instead of one-off rewrites.

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
