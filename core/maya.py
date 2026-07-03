"""
maya.py -- the MAYA two-phase, cost-saving validation engine.

MAYA ("illusion") builds a small, referential-integrity-preserving copy of
production in the dev workspace so pipelines can be proven correct cheaply, then
proves them at scale on production-copied data in SIT. This module:

  * plans + renders the RI-preserving dev sampling (seed rows + FK closure),
  * emits a deterministic sample manifest,
  * defines the two validation phases and the promotion record.

Sampling is deterministic (ordered by key + a fixed seed) so a dev sample is
reproducible run to run, which keeps MAYA-Dev idempotency checks meaningful.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# the two MAYA phases
PHASE_DEV = "dev"      # logic proof on the sampled illusion of prod
PHASE_SIT = "sit"      # scale proof on production-copied data


@dataclass
class FK:
    """A foreign-key reference: this table's `col` points at parent.`parent_key`."""
    col: str
    parent_table: str
    parent_key: str


@dataclass
class SampleSpec:
    table: str                                   # fully-qualified source name
    keys: List[str] = field(default_factory=list)
    fks: List[FK] = field(default_factory=list)
    rows: int = 10000
    is_reference: bool = False                    # small dim/config -> copy whole


def _src(cfg, table: str) -> str:
    ref = cfg.maya.source_ref_catalog
    return f"{ref}.{table}" if ref else table


def _dev(cfg, table: str) -> str:
    return f"{cfg.maya.dev_catalog}.{table}"


def sample_table_sql(cfg, spec: SampleSpec) -> str:
    """Deterministic seed sample of a single table into the dev catalog."""
    src, dst = _src(cfg, spec.table), _dev(cfg, spec.table)
    if cfg.maya.sampling == "none":
        return f"-- {spec.table}: dev already sampled by source team; no build needed"
    order = ", ".join(spec.keys) if spec.keys else "1"
    if spec.is_reference:
        body = f"SELECT * FROM {src}"
        note = "reference/dim table -> full copy"
    elif cfg.maya.sampling == "random":
        body = (f"SELECT * FROM {src} "
                f"ORDER BY xxhash64(concat_ws('|', {order}), {cfg.maya.seed}) "
                f"LIMIT {spec.rows}")
        note = "random deterministic sample"
    else:  # ri_preserving seed
        body = (f"SELECT * FROM {src} "
                f"ORDER BY xxhash64(concat_ws('|', {order}), {cfg.maya.seed}) "
                f"LIMIT {spec.rows}")
        note = "RI-preserving seed (parents pulled by closure below)"
    return (f"-- MAYA-Dev sample: {spec.table}  ({note}, rows<= {spec.rows})\n"
            f"CREATE OR REPLACE TABLE {dst} AS\n{body};")


def ri_closure_sql(cfg, parent: SampleSpec, children: List[SampleSpec]) -> str:
    """Augment a parent sample with rows referenced by already-sampled children.

    Guarantees joins resolve on the dev sample: every FK value present in a sampled
    child has its parent row present in the sampled parent.
    """
    src, dst = _src(cfg, parent.table), _dev(cfg, parent.table)
    unions = []
    for ch in children:
        for fk in ch.fks:
            if fk.parent_table == parent.table:
                unions.append(f"SELECT {fk.col} AS k FROM {_dev(cfg, ch.table)}")
    if not unions:
        return f"-- {parent.table}: no child FK references; seed sample is sufficient"
    keyset = "\nUNION\n".join(unions)
    pk = parent.keys[0] if parent.keys else "id"
    return (f"-- MAYA-Dev RI closure: add referenced parents into {parent.table}\n"
            f"INSERT INTO {dst}\n"
            f"SELECT p.* FROM {src} p\n"
            f"WHERE p.{pk} IN (\n  {keyset}\n)\n"
            f"AND p.{pk} NOT IN (SELECT {pk} FROM {dst});")


def plan_samples(cfg, specs: List[SampleSpec]) -> Dict[str, object]:
    """Order the work (seed children first, then parent closure) and render SQL.

    Returns {"sql": [...], "manifest": [...]} where manifest rows are the deterministic
    record of what dev should contain.
    """
    sql: List[str] = []
    # 1. seed every table
    for s in specs:
        sql.append(sample_table_sql(cfg, s))
    # 2. RI closure: for each parent referenced by any child, pull referenced rows
    by_name = {s.table: s for s in specs}
    parents = set()
    for s in specs:
        for fk in s.fks:
            parents.add(fk.parent_table)
    for pt in sorted(parents):
        parent = by_name.get(pt) or SampleSpec(table=pt)
        sql.append(ri_closure_sql(cfg, parent, specs))
    manifest = [{
        "table": s.table,
        "kind": "reference_full" if s.is_reference else "sample",
        "target_rows": "all" if s.is_reference else s.rows,
        "keys": ";".join(s.keys),
        "seed": cfg.maya.seed,
        "sampling": cfg.maya.sampling,
    } for s in specs]
    return {"sql": sql, "manifest": manifest}


def specs_from_context(cfg, ctx: dict, fk_map: Optional[Dict[str, List[FK]]] = None
                       ) -> List[SampleSpec]:
    """Build sample specs for a pipeline's bronze inputs from its context pack.

    Config/helper tables are treated as reference (full copy); everything else is
    sampled to the configured row budget. FK metadata (if supplied) drives closure.
    """
    fk_map = fk_map or {}
    specs = []
    for t in ctx.get("prereqs", []):
        schema = t.split(".")[0] if "." in t else ""
        is_ref = schema in ("metadata", "config") or "token" in t
        specs.append(SampleSpec(
            table=t,
            rows=cfg.maya.rows_for(t),
            is_reference=is_ref,
            fks=fk_map.get(t, []),
        ))
    return specs


def promotion_record(pipeline: str, dev_pass: bool, sit_pass: bool,
                     require_both: bool = True) -> dict:
    """Whether a pipeline may be certified for prod under MAYA's gate rule."""
    certified = (dev_pass and sit_pass) if require_both else (dev_pass and sit_pass)
    return {
        "pipeline": pipeline,
        "maya_dev": "PASS" if dev_pass else "FAIL",
        "maya_sit": "PASS" if sit_pass else "FAIL",
        "certified": certified,
        "status": "CERTIFIED" if certified else "BLOCKED",
    }
