"""
engines.py -- the reusable, config-driven engine catalog (E1-E7).

Every pipeline pattern and every table's producing logic maps to exactly one engine.
You build the engine once and configure it many times; E7 is the deliberate
custom-notebook escape hatch. This module is pure data + small helpers so it is
shared by the classifier, the reports, and the config templates.
"""
from __future__ import annotations

# pipeline patterns (source-neutral names; adapters map their jobs onto these)
PATTERN_LABELS = {
    "A": "Metadata-driven ingestion (control-table)",
    "B": "Stored-procedure transformation chain",
    "C": "Dynamic-SQL engine (config-expanded)",
    "D": "File / document intake",
    "E": "External invoke-in-place",
    "F": "Replication / CDC serving",
    "G": "Orchestrator (sub-pipeline fan-out)",
    "X": "Utility / maintenance / other",
}

ENGINE_LABELS = {
    "E1": "Ingestion (bronze): source -> bronze",
    "E2": "Transform (silver/gold): Spark SQL step-DAG",
    "E3": "Delta-Apply: SCD / MERGE / dynamic deltas",
    "E4": "External-Invoke: invoke-in-place (JDBC/proc/file)",
    "E5": "Orchestration: sub-pipeline fan-out",
    "E6": "Utility / Maintenance",
    "E7": "Custom Notebook (framework-invoked fallback)",
    # ---- downstream-app engines (Lakebase + Databricks Apps) --------------
    "E8": "Lakebase schema + UC synced tables (OLTP serving)",
    "E9": "Databricks App backend + API (FastAPI on Apps)",
    "E10": "App UI (rebuilt screens served by the Databricks App)",
}

ENGINE_OPS = {
    "E1": "jdbc_extract, file_intake, cdc_snapshot, metadata_multi_ingest",
    "E2": "sql_step (DAG), dynamic_sql_expand",
    "E3": "scd_merge, delta_apply, upsert",
    "E4": "invoke_external (JDBC exec / proc / file xfer)",
    "E5": "run_child_jobs",
    "E6": "copy, retention_purge, index_refresh, dedup, noop",
    "E7": "run_notebook",
    "E8": "lakebase_ddl, synced_table, reverse_etl",
    "E9": "gen_backend, gen_api, app_yaml, oauth_wire",
    "E10": "gen_ui, build_ui, screen_parity",
}

ENGINE_DEFAULT_OP = {
    "E1": "ingest", "E2": "sql_step", "E3": "delta_apply", "E4": "invoke_external",
    "E5": "run_child_jobs", "E6": "utility", "E7": "run_notebook",
    "E8": "lakebase_ddl", "E9": "gen_backend", "E10": "gen_ui",
}

# app asset-kind -> the engine that migrates it
ENGINE_OF_APP_KIND = {
    "app_model": "E8", "app_etl": "E8",
    "app_api": "E9", "app_backend": "E9",
    "app_ui": "E10", "app_screens": "E10",
}

ENGINE_OF_PATTERN = {
    "A": "E1", "D": "E1", "F": "E1",   # ingestion flavors
    "B": "E2", "C": "E2",              # transform flavors
    "E": "E4",                         # external invoke
    "G": "E5",                         # orchestration
    "X": "E6",                         # utility / maintenance
}

# how a pattern maps to a build unit "kind"
KIND_OF_PATTERN = {
    "E": "external_invoke",
    "G": "orchestration",
    "X": "utility",
    # A/B/C/D/F resolve to "medallion" when they produce tables (decided in contract)
}


def engine_of_pattern(pattern: str) -> str:
    return ENGINE_OF_PATTERN.get(pattern, "E6")


def catalog():
    """List of engine dicts for reports/docs."""
    return [
        {"engine": e, "label": ENGINE_LABELS[e], "ops": ENGINE_OPS[e],
         "default_op": ENGINE_DEFAULT_OP[e]}
        for e in sorted(ENGINE_LABELS)
    ]
