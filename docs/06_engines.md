# 06 - Reusable engines (E1-E7)

Most jobs are not bespoke code - they are configuration over a small set of reusable
engines. Build the engine once, configure it many times. See
[core/engines.py](../core/engines.py) and
[templates/engine_config.example.yaml](../templates/engine_config.example.yaml).

| Engine | Role | Example ops |
|---|---|---|
| E1 | Ingestion (bronze): source -> bronze | jdbc_extract, file_intake, cdc_snapshot, metadata_multi_ingest |
| E2 | Transform (silver/gold): Spark SQL step-DAG | sql_step (DAG), dynamic_sql_expand |
| E3 | Delta-Apply: SCD / MERGE / dynamic deltas | scd_merge, delta_apply, upsert |
| E4 | External-Invoke: invoke-in-place | invoke_external (JDBC exec / proc / file) |
| E5 | Orchestration: sub-pipeline fan-out | run_child_jobs |
| E6 | Utility / maintenance | copy, retention_purge, index_refresh, dedup, noop |
| E7 | Custom notebook (framework-invoked fallback) | run_notebook |

## Pattern -> engine
Pipeline patterns map to a primary engine: A/D/F -> E1, B/C -> E2, E -> E4, G -> E5,
X -> E6. E3 appears inside medallion gold builds (MERGE/SCD). E7 is the deliberate
escape hatch for the rare pipeline that cannot be expressed as config.

## Config-driven usage
An engine reads a per-pipeline YAML (bronze/silver/gold blocks with ops, sources,
steps, and parity targets) instead of hand-written orchestration. SQL-first: author in
Spark SQL; use PySpark only by exception (Auto Loader, dynamic SQL, complex parsing).

## MAYA validation block
Each engine config carries a `validation:` block with `dev_sample` and `sit_full`
sub-blocks (catalogs, checks, watermark), so the same config drives both MAYA phases.
