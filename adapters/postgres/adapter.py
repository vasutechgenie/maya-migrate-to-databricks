"""
adapter.py -- the PostgreSQL source adapter.

Postgres is a very common *source* (OLTP OLAP marts, PL/pgSQL "jobs", warehouse-in-a-DB
estates). This adapter proves the accelerator's core is source-agnostic: it reuses the
same normalized-graph fast-path as the Synapse adapter (objects.csv / edges.csv /
connections.csv + CREATE TABLE/VIEW DDL under artifacts/DW/<db>/<schema>/), and only
swaps the two genuinely source-specific pieces:

  * dialect_translate: assistive PL/pgSQL / Postgres SQL -> Spark SQL rewrites.
  * kb_manifest instructions: how to export the estate *from Postgres* (pg_dump -s,
    information_schema, pg_proc, and the in-DB job/control tables).

Modes (inherited from the fast-path):
  * fast-path (default): reuse a discovery directory produced by introspecting Postgres
    (objects.csv / edges.csv / connections.csv / schedules.csv + DDL). The bundled
    Retail demo (examples/retail/) runs end-to-end this way, offline and deterministic.
  * live: scripts/setup_retail_postgres.py builds a real retail_src database (tables,
    views, PL/pgSQL gold procs, an etl_jobs table, RI-preserving seed data) so the same
    estate can also be introspected/replicated against a live Databricks workspace.
"""
from __future__ import annotations

import re
from typing import Dict, List

from adapters.base import SourceAdapter
from adapters.synapse.adapter import SynapseAdapter


class PostgresAdapter(SynapseAdapter):
    """PostgreSQL source adapter (reuses the Synapse fast-path graph/DDL machinery)."""

    name = "postgres"

    # ---- dialect translate (Postgres/PL-pgSQL -> Spark SQL, assistive) -----
    def dialect_translate(self, sql: str) -> str:
        """Best-effort Postgres -> Spark SQL rewrites. The agent still verifies parity."""
        s = sql
        # now()/clock/statement timestamp -> current_timestamp()
        s = re.sub(r"\b(now|clock_timestamp|statement_timestamp|transaction_timestamp)"
                   r"\s*\(\s*\)", "current_timestamp()", s, flags=re.I)
        s = re.sub(r"\bCURRENT_TIMESTAMP\b", "current_timestamp()", s, flags=re.I)
        # ::type postgres casts -> CAST(... AS sparktype) for the common scalar types
        cast_map = {
            "text": "STRING", "varchar": "STRING", "bpchar": "STRING", "char": "STRING",
            "int": "INT", "int4": "INT", "integer": "INT",
            "int8": "BIGINT", "bigint": "BIGINT", "smallint": "SMALLINT",
            "numeric": "DECIMAL(38,10)", "decimal": "DECIMAL(38,10)",
            "float8": "DOUBLE", "double precision": "DOUBLE", "real": "FLOAT",
            "bool": "BOOLEAN", "boolean": "BOOLEAN",
            "date": "DATE", "timestamp": "TIMESTAMP", "timestamptz": "TIMESTAMP",
        }

        def _cast(m: "re.Match[str]") -> str:
            expr, typ = m.group(1), m.group(2).lower().strip()
            spark = cast_map.get(typ, typ.upper())
            return f"CAST({expr} AS {spark})"

        # identifier or ) or literal followed by ::type
        s = re.sub(r"([A-Za-z0-9_\.\"\)']+)\s*::\s*([A-Za-z_][A-Za-z0-9_ ]*)",
                   _cast, s)
        # string functions / operators
        s = re.sub(r"\bILIKE\b", "LIKE", s, flags=re.I)               # + agent lowers operands
        s = re.sub(r"\bSTRING_AGG\s*\(", "concat_ws_agg(", s, flags=re.I)  # agent maps to collect_list/concat_ws
        s = re.sub(r"\bCOALESCE\s*\(", "coalesce(", s, flags=re.I)
        s = re.sub(r"\bnextval\s*\(([^)]*)\)", "-- nextval(\\1)  (use IDENTITY / monotonically_increasing_id)", s, flags=re.I)
        # boolean literals are fine; LIMIT/OFFSET are fine; date_trunc is fine
        return s

    # ---- knowledge-base manifest (Postgres-specific export instructions) ---
    @classmethod
    def kb_manifest(cls) -> List[dict]:
        m = SourceAdapter.kb_manifest()
        how = {
            "graph": "From Postgres: export the pipeline/table dependency graph as "
                     "objects.csv/edges.csv. scripts/setup_retail_postgres.py shows how "
                     "to derive it by introspecting pg_proc (PL/pgSQL jobs), "
                     "information_schema.view_table_usage, and the in-DB etl_jobs table.",
            "ddl": "From Postgres: `pg_dump -s -t <schema>.<obj>` (or query "
                   "information_schema.columns) into "
                   "artifacts/DW/<db>/<schema>/{Tables,Views}/<name>.sql.",
            "connections": "Export the source/target connection inventory (JDBC DSNs, "
                           "file/API endpoints, external-proc systems) as connections.csv.",
            "schedules": "Export the in-warehouse job table (e.g. meta.etl_jobs) or the "
                         "external orchestrator (cron/Airflow/ADF) triggers as "
                         "schedules.csv (trigger,schedule,pipeline,enabled).",
            "configs": "Dump control/watermark tables (e.g. meta.etl_control) to "
                       "configs/*.csv.",
            "security": "Export roles (pg_roles), GRANTs (information_schema."
                        "role_table_grants), pgcrypto/secret references, and PII "
                        "classification into artifacts/security/*.",
            "bi": "Export the Power BI/Tableau/Looker package whose queries read this "
                  "Postgres warehouse.",
        }
        for entry in m:
            if entry["kind"] in how:
                entry["instructions"] = how[entry["kind"]]
        return m
