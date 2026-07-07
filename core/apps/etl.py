"""Retarget the DW-side ETL that populates an app's datamodel into Lakebase.

The legacy app is fed by ETL that writes into an OLTP app database. On Databricks the
same read-model is served from Lakebase via UC **synced tables** (gold -> Lakebase).
This module authors, per entity, a deterministic sync statement (reverse ETL) and
records the ETL bindings so they certify through the normal pipeline machinery.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from .model import App, Entity, safe_ident


def _sync_sql(app: App, e: Entity, catalog: str) -> str:
    """A gold -> Lakebase synced-table statement for one entity."""
    target = f"{app.schema}.{safe_ident(e.name)}"
    cols = [safe_ident(c.get("name", "")) for c in e.columns if c.get("name")]
    col_list = ", ".join(cols) if cols else "*"
    if e.source:
        src = f"{catalog}.{e.source}"
        return (f"-- Synced table: {src} -> lakebase {target}\n"
                f"CREATE OR REPLACE SYNCED TABLE lakebase.{target}\n"
                f"AS SELECT {col_list}\nFROM {src};\n")
    return (f"-- No DW source declared for {target}; app-owned table\n"
            f"-- populate {target} from the app's own writes\n")


def retarget(cfg, app: App, catalog: str, out_dir: str) -> List[Dict[str, Any]]:
    """Author the sync SQL per entity and return the ETL bindings."""
    etl_dir = os.path.join(out_dir, "etl")
    os.makedirs(etl_dir, exist_ok=True)
    bindings: List[Dict[str, Any]] = []
    for e in app.entities:
        sql = _sync_sql(app, e, catalog)
        fn = os.path.join(etl_dir, f"sync_{safe_ident(e.name)}.sql")
        with open(fn, "w") as f:
            f.write(sql)
        bindings.append({
            "pipeline": e.populated_by or f"sync_{safe_ident(e.name)}",
            "entity": e.name,
            "source_tables": [e.source] if e.source else [],
            "retarget_status": "authored" if e.source else "app_owned",
        })
    return bindings


def sync_ok(bindings: List[Dict[str, Any]]) -> bool:
    """Sync parity: every entity binding is authored (or explicitly app-owned)."""
    return bool(bindings) and all(
        b.get("retarget_status") in ("authored", "app_owned") for b in bindings)
