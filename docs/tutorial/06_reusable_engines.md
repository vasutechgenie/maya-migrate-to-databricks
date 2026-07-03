# Part 6 - Reusable engines E1-E7, SQL-first

> [Index](README.md) | Prev: [Part 5](05_the_pipeline_contract.md) | Next: [Part 7](07_maya_dev_illusion.md)

Most pipelines are not snowflakes. A **deterministic classifier** maps each one to a **pattern**
(A-G), which maps to a reusable **engine** (E1-E7). Build the engine once; configure it many times.

## Northwind's classification
Straight from `out/pipeline_specs/index.json`:

| Pipeline | Pattern | Engine | What it is |
|---|---|---|---|
| `nw_ingest_erp` | A | **E1** | metadata-driven ingestion |
| `nw_web_intake` | D | **E1** | file / document intake |
| `nw_qlik_replicate` | F | **E1** | replication / CDC serving |
| `nw_build_sales` | B | **E2** | transform chain |
| `nw_build_web` | B | **E2** | transform |
| `nw_build_marts` | B | **E2** | transform |
| `nw_fx_sync` | E | **E4** | external invoke-in-place |
| `nw_daily_master` | G | **E5** | orchestrator fan-out |

Eight pipelines, four engines.

## The engine catalog
- **E1** Ingestion (bronze) - jdbc extract, file intake, CDC snapshot, metadata multi-ingest.
- **E2** Transform (silver/gold) - Spark SQL step-DAG; dynamic-SQL expansion.
- **E3** Delta-Apply - SCD / MERGE / dynamic deltas.
- **E4** External-Invoke - invoke in place (JDBC exec / proc / file).
- **E5** Orchestration - run child jobs.
- **E6** Utility / Maintenance - copy, retention, dedup, no-op.
- **E7** Custom Notebook - the deliberate escape hatch for genuine one-offs.

## SQL-first
E2 is Spark **SQL**, not bespoke PySpark per job - most warehouse logic is already SQL, so the
work is translation + configuration. Engines are configured with small per-pipeline YAML; see
`templates/engine_config.example.yaml`.

## Not everything is a rebuild
`nw_fx_sync` (pattern E) calls a proc in an external system outside `home_database` -> invoke in
place. `nw_daily_master` (pattern G) produces nothing; it orchestrates -> the orchestration
engine. The classifier gets both from the graph alone.

## Reference
- Engines: [../06_engines.md](../06_engines.md)
- Code: `core/engines.py`, classifier in `core/contract.py`

---
Prev: [Part 5](05_the_pipeline_contract.md) | Next: [Part 7 - MAYA-Dev: the illusion of production](07_maya_dev_illusion.md)
