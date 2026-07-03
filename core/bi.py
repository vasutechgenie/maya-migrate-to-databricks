"""
bi.py -- MAYA BI layer migration.

Enterprise migrations move dashboards (Looker / Tableau / Power BI) too, not just data.
MAYA agents do this end to end over MCP/API: extract the package, AI-convert each query
to Databricks SQL and repoint its tables, prove the converted query returns the EXACT
same result as the original (against certified gold), redeploy the dashboards to the BI
tool, and - to bring AI to BI - replicate the same dashboards natively in Databricks
(Lakeview) with an attached Genie space seeded by the very same queries.

This module is source-agnostic: BI-tool specifics live in connectors
(adapters/bi/*). Here we model the artifacts, render the query-result parity, build the
Genie/Lakeview replication specs, and provide resumable orchestration helpers.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import validation as V

# BI object lifecycle states (mirrors gates B0..B4)
STATES = ["EXTRACTED", "CONVERTED", "PARITY", "REPUBLISHED", "GENIE", "DONE"]

# result-parity checks (exact same result as the original query)
BI_CHECKS = [
    ("result_schema", "Result column names/order/types match the original"),
    ("result_rowcount", "Result row count matches"),
    ("result_set_equality", "Unordered row set identical (EXCEPT both ways is empty)"),
    ("result_checksum", "Order-independent aggregate row hash matches"),
    ("result_order", "If the query is ordered, row order matches"),
]


@dataclass
class BIObject:
    """One query-bearing BI artifact (a tile / view / dataset query)."""
    obj_id: str                       # stable id, e.g. "sales_dash::revenue_by_region"
    system: str = "powerbi"           # looker | tableau | powerbi
    dashboard: str = ""
    tile: str = ""
    original_query: str = ""          # source SQL/expr as extracted
    converted_query: str = ""         # AI-converted Databricks SQL (repointed tables)
    datasource: str = ""
    target_tables: List[str] = field(default_factory=list)  # Databricks gold tables read
    ordered: bool = False             # does the original enforce ORDER BY?


# ---- query-result parity ---------------------------------------------------
def ref_table(cfg, obj: BIObject) -> str:
    """Where the agent snapshots the ORIGINAL query's result for comparison."""
    cat = getattr(cfg.maya, "sit_catalog", "sit")
    safe = obj.obj_id.replace("::", "__").replace(".", "_")
    return f"{cat}_bi_ref.{safe}"


def result_parity_sql(cfg, obj: BIObject) -> Dict[str, str]:
    """Render checks comparing the converted query result vs the original snapshot.

    The agent first runs the ORIGINAL query on the source (via the connector) and lands
    it in ref_table(); the CONVERTED query runs live against certified Databricks gold.
    """
    ref = ref_table(cfg, obj)
    new = f"(\n{obj.converted_query.rstrip().rstrip(';')}\n)"
    checks = {
        "result_rowcount": (
            "-- result_rowcount\n"
            f"SELECT 'orig' side, count(*) n FROM {ref}\n"
            f"UNION ALL SELECT 'new' side, count(*) n FROM {new} t;"),
        "result_set_equality": (
            "-- result_set_equality: both differences must be empty\n"
            f"SELECT 'missing_in_new' tag, * FROM (SELECT * FROM {ref} "
            f"EXCEPT SELECT * FROM {new} t)\n"
            "UNION ALL\n"
            f"SELECT 'extra_in_new' tag, * FROM (SELECT * FROM {new} t "
            f"EXCEPT SELECT * FROM {ref});"),
        "result_checksum": (
            "-- result_checksum: order-independent aggregate hash\n"
            f"WITH o AS (SELECT sum(xxhash64(to_json(struct(*)))) h, count(*) n FROM {ref}),\n"
            f"     n AS (SELECT sum(xxhash64(to_json(struct(*)))) h, count(*) n FROM {new} t)\n"
            "SELECT o.h orig_hash, n.h new_hash, o.n orig_n, n.n new_n,\n"
            "       (o.h = n.h AND o.n = n.n) AS parity_ok FROM o, n;"),
        "result_schema": (
            "-- result_schema: compare the two result schemas\n"
            f"DESCRIBE QUERY {new};   -- compare against DESCRIBE of the original result"),
    }
    if obj.ordered:
        checks["result_order"] = (
            "-- result_order: compare row order via a row_number join on position\n"
            f"WITH o AS (SELECT *, row_number() OVER (ORDER BY 1) rn FROM {ref}),\n"
            f"     n AS (SELECT *, row_number() OVER (ORDER BY 1) rn FROM {new} t)\n"
            "SELECT count(*) mismatches FROM o JOIN n USING (rn)\n"
            "WHERE xxhash64(to_json(struct(o.*))) <> xxhash64(to_json(struct(n.*)));")
    return checks


# ---- Genie + Lakeview replication -----------------------------------------
def genie_space_spec(cfg, dashboard: str, objs: List[BIObject]) -> dict:
    """A Genie space per dashboard, seeded by the dashboard's own queries.

    Bringing AI to BI: the extracted tile titles become curated sample questions and the
    converted queries become the trusted SQL the space reasons over.
    """
    tables = sorted({t for o in objs for t in o.target_tables})
    sample_questions = [o.tile or o.obj_id for o in objs if (o.tile or o.obj_id)]
    trusted = [{"question": (o.tile or o.obj_id), "sql": o.converted_query}
               for o in objs if o.converted_query]
    return {
        "genie_space": f"{dashboard} (MAYA)",
        "description": f"AI/BI Genie replica of {dashboard}, migrated by MAYA.",
        "tables": tables,
        "sample_questions": sample_questions,
        "trusted_assets": trusted,
        "instructions": ("Answer only from the listed certified gold tables. Prefer the "
                         "trusted SQL for known questions; all measures must match the "
                         "certified originals."),
    }


def lakeview_spec(cfg, dashboard: str, objs: List[BIObject]) -> dict:
    """A native Databricks (Lakeview) dashboard mirroring the original."""
    datasets = [{"name": o.obj_id, "query": o.converted_query} for o in objs
                if o.converted_query]
    widgets = [{"title": o.tile or o.obj_id, "dataset": o.obj_id} for o in objs]
    return {"display_name": f"{dashboard} (MAYA)", "datasets": datasets,
            "widgets": widgets}


# ---- inventory + orchestration --------------------------------------------
def _inv_path(cfg) -> str:
    return cfg.out("bi_objects.json")


def load_objects(cfg) -> List[BIObject]:
    p = _inv_path(cfg)
    if not os.path.exists(p):
        return []
    rows = json.load(open(p))
    return [BIObject(**{k: v for k, v in r.items()
                        if k in BIObject.__dataclass_fields__}) for r in rows]


def save_objects(cfg, objs: List[BIObject]):
    p = _inv_path(cfg)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump([o.__dict__ for o in objs], open(p, "w"), indent=1)


def _authored_dir(cfg) -> str:
    d = cfg.p(cfg.out_dir, "bi_authored")
    os.makedirs(d, exist_ok=True)
    return d


# an authored BI object is "done" when all lifecycle keys are present + true
REQUIRED_BI = ["converted_query", "parity_passed", "republished", "genie_created"]


def is_done(cfg, obj_id: str) -> bool:
    p = os.path.join(_authored_dir(cfg), f"{_safe(obj_id)}.json")
    if not os.path.exists(p):
        return False
    try:
        d = json.load(open(p))
    except Exception:
        return False
    return bool(d.get("converted_query")) and d.get("parity_passed") is True \
        and d.get("republished") is True and d.get("genie_created") is True


def status(cfg) -> dict:
    objs = load_objects(cfg)
    by_system: Dict[str, list] = {}
    done = 0
    for o in objs:
        rec = by_system.setdefault(o.system, [0, 0])
        rec[1] += 1
        if is_done(cfg, o.obj_id):
            rec[0] += 1
            done += 1
    return {"total": len(objs), "done": done, "pending": len(objs) - done,
            "by_system": by_system}


def pending(cfg, system: Optional[str] = None, limit: Optional[int] = None) -> List[BIObject]:
    out = []
    for o in load_objects(cfg):
        if system and o.system != system:
            continue
        if is_done(cfg, o.obj_id):
            continue
        out.append(o)
        if limit and len(out) >= limit:
            break
    return out


def validate(cfg, obj_id: str) -> dict:
    p = os.path.join(_authored_dir(cfg), f"{_safe(obj_id)}.json")
    if not os.path.exists(p):
        return {"obj_id": obj_id, "ok": False, "error": "no authored record"}
    try:
        d = json.load(open(p))
    except Exception as e:
        return {"obj_id": obj_id, "ok": False, "error": f"invalid json: {e}"}
    missing = [k for k in REQUIRED_BI if k not in d]
    reds = [k for k in ("parity_passed", "republished", "genie_created")
            if d.get(k) is not True]
    return {"obj_id": obj_id, "ok": (not missing and not reds),
            "missing": missing, "not_green": reds}


def _safe(obj_id: str) -> str:
    return obj_id.replace("::", "__").replace("/", "_").replace(".", "_")


# reason codes are shared with the data drift loop
REASON_CODES = V.REASON_CODES
