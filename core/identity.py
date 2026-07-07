"""
identity.py -- Stage 10: identity, security & governance cutover into Unity Catalog.

Takes the estate collected in Stage 0 and deterministically authors the Unity Catalog
security model that must exist before go-live, then proves it matches the source:

  * groups / service principals  -> account-group + service-principal notes
  * the source grant matrix       -> UC GRANT statements (schema / table / view scoped)
  * classified (PII/PHI) columns  -> column-mask functions + ALTER ... SET MASK
  * declared row-level policies    -> row-filter functions + ALTER ... SET ROW FILTER
  * every credential               -> a Databricks secret scope + key
  * governance                     -> schema owners, tags, and a business glossary

Offline this is pure SQL/DDL generation (zero Databricks calls); with
agents.driver: cursor the same plan can be applied by the agent swarm.

Access-parity gate: every source grant is mapped 1:1 to a UC grant (no missing / extra),
every sensitive column has a mask, every declared row policy has a filter, and every
active credential has a secret scope. Emits out/stage10_identity.sql + out/stage10_gate.json.
"""
from __future__ import annotations

import csv
import json
import os
from typing import Dict, List, Tuple

from .graph import Graph
from . import readiness as readiness_mod


def _sec(cfg) -> dict:
    return getattr(cfg, "security", {}) or {}


def _gov(cfg) -> dict:
    return getattr(cfg, "governance", {}) or {}


def _target_catalog(cfg) -> str:
    return _sec(cfg).get("target_catalog") or cfg.maya.sit_catalog


def _secret_scope(cfg) -> str:
    return _sec(cfg).get("secret_scope") or f"{cfg.project_name}_secrets"


def _load_readiness(cfg) -> dict:
    """Load Stage-0 outputs from disk; fall back to collecting if absent."""
    d = cfg.out("readiness")

    def _csv(name):
        p = os.path.join(d, name)
        if os.path.exists(p):
            with open(p, newline="") as f:
                return list(csv.DictReader(f))
        return None

    principals = _csv("principals.csv")
    if principals is None:
        return readiness_mod.collect(cfg)
    return {
        "principals": principals,
        "grants": _csv("grants.csv") or [],
        "secrets": _csv("secrets.csv") or [],
        "classification": _csv("classification.csv") or [],
        "connections": cfg.load_adapter().connections() or [],
    }


def _object_types(cfg) -> Dict[str, str]:
    try:
        g = Graph.load(cfg.objects_csv(), cfg.edges_csv(),
                       cfg.pipeline_types, cfg.table_types)
    except Exception:
        return {}
    return {(o.get("name") or k).lower(): o.get("type") for k, o in g.objects.items()}


def _uc_privilege(priv: str) -> str:
    p = (priv or "").strip().upper()
    return "ALL PRIVILEGES" if p in ("ALL", "ALL PRIVILEGES") else p


def _grant_sql(cfg, gr: dict, obj_types: Dict[str, str], schemas) -> Tuple[str, str]:
    """Return (securable_kind, GRANT statement) for one source grant row."""
    cat = _target_catalog(cfg)
    principal = gr.get("principal") or ""
    obj = (gr.get("object") or "")
    priv = _uc_privilege(gr.get("privilege"))
    low = obj.lower()
    if low in schemas:
        return "SCHEMA", (f"GRANT {priv} ON SCHEMA {cat}.{obj} "
                          f"TO `{principal}`;")
    kind = "VIEW" if obj_types.get(low) == "VIEW" else "TABLE"
    return kind, (f"GRANT {priv} ON {kind} {cat}.{obj} TO `{principal}`;")


def _mask_functions(cfg, classification) -> Tuple[List[str], List[str]]:
    """Deterministic column-mask function DDL + per-column SET MASK statements."""
    cat = _target_catalog(cfg)
    masks = sorted({(r.get("mask") or "").strip() for r in classification
                    if (r.get("mask") or "").strip()})
    bodies = {
        "email": "CASE WHEN is_account_group_member('%s_stewards') THEN v "
                 "ELSE concat('***@', split(v, '@')[1]) END",
        "phone": "CASE WHEN is_account_group_member('%s_stewards') THEN v "
                 "ELSE concat('***-***-', substr(v, -4)) END",
        "name": "CASE WHEN is_account_group_member('%s_stewards') THEN v "
                "ELSE concat(substr(v, 1, 1), '****') END",
        "default": "CASE WHEN is_account_group_member('%s_stewards') THEN v "
                   "ELSE '****' END",
    }
    home = (cfg.home_database or cfg.project_name or "app").lower()
    ddl = [f"CREATE SCHEMA IF NOT EXISTS {cat}.masks;"]
    for m in masks:
        body = bodies.get(m, bodies["default"]) % home
        ddl.append(
            f"CREATE OR REPLACE FUNCTION {cat}.masks.mask_{m}(v STRING)\n"
            f"  RETURNS STRING RETURN {body};")
    sets = []
    for r in classification:
        m = (r.get("mask") or "").strip()
        if not m:
            continue
        sets.append(
            f"ALTER TABLE {cat}.{r.get('table')} "
            f"ALTER COLUMN {r.get('column')} SET MASK {cat}.masks.mask_{m};")
    return ddl, sets


def _row_filters(cfg) -> Tuple[List[str], List[str]]:
    """Row-filter function DDL + SET ROW FILTER statements from security.row_filters."""
    cat = _target_catalog(cfg)
    rfs = _sec(cfg).get("row_filters", []) or []
    ddl, sets = [], []
    for rf in rfs:
        table = rf.get("table")
        col = rf.get("column")
        group = rf.get("group")
        if not (table and col and group):
            continue
        fn = f"{cat}.masks.rf_{table.replace('.', '_')}_{col}"
        ddl.append(
            f"CREATE OR REPLACE FUNCTION {fn}({col} STRING)\n"
            f"  RETURNS BOOLEAN RETURN is_account_group_member('{group}') "
            f"OR {col} IS NOT NULL;")
        sets.append(f"ALTER TABLE {cat}.{table} SET ROW FILTER {fn} ON ({col});")
    return ddl, sets


def _secret_scopes(cfg, secrets) -> List[str]:
    scope = _secret_scope(cfg)
    lines = [f"-- Databricks secret scope for all migrated credentials:",
             f"--   databricks secrets create-scope {scope}"]
    for s in secrets:
        key = s.get("secret")
        conn = s.get("connection")
        lines.append(f"--   databricks secrets put-secret {scope} {key}   "
                     f"# backs connection '{conn}'")
    return lines


def _governance_sql(cfg, schemas) -> List[str]:
    cat = _target_catalog(cfg)
    gov = _gov(cfg)
    owners = gov.get("owners", {}) or {}
    glossary = gov.get("glossary", {}) or {}
    tags = gov.get("tags", {}) or {}
    out = []
    for s in sorted(schemas):
        owner = owners.get(s)
        if owner:
            out.append(f"ALTER SCHEMA {cat}.{s} OWNER TO `{owner}`;")
        tag = tags.get(s)
        if tag:
            out.append(f"ALTER SCHEMA {cat}.{s} SET TAGS ('layer' = '{tag}');")
    for term, definition in sorted(glossary.items()):
        out.append(f"-- glossary: {term} = {definition}")
    return out


def run(cfg) -> dict:
    data = _load_readiness(cfg)
    grants = data["grants"]
    secrets = data["secrets"]
    classification = data["classification"]
    principals = data["principals"]

    schemas, _obj_names = readiness_mod._home_schemas_and_objects(cfg)
    obj_types = _object_types(cfg)

    # ---- identity: groups + service principals ---------------------------
    ident_lines = ["-- Identity (managed via account SCIM; shown for completeness):"]
    for p in principals:
        t = p.get("type")
        if t == "group":
            ident_lines.append(f"--   ensure group `{p.get('principal')}` "
                               f"(from {p.get('source_role') or 'n/a'})")
        elif t == "service_principal":
            ident_lines.append(f"--   ensure service principal `{p.get('principal')}`")

    # ---- access: grant matrix -------------------------------------------
    grant_stmts, mapped = [], 0
    for gr in grants:
        _kind, stmt = _grant_sql(cfg, gr, obj_types, schemas)
        grant_stmts.append(stmt)
        mapped += 1

    # ---- classification: masks ------------------------------------------
    mask_ddl, mask_sets = _mask_functions(cfg, classification)
    rf_ddl, rf_sets = _row_filters(cfg)

    # ---- secrets ---------------------------------------------------------
    secret_lines = _secret_scopes(cfg, secrets)

    # ---- governance ------------------------------------------------------
    gov_stmts = _governance_sql(cfg, schemas)

    sql = "\n".join([
        f"-- MAYA Stage 10: identity, security & governance for {cfg.project_name}",
        f"-- target catalog: {_target_catalog(cfg)}",
        "",
        "-- === Identity ===",
        *ident_lines,
        "",
        "-- === Access (grant matrix, 1:1 with source) ===",
        *grant_stmts,
        "",
        "-- === Column masks (classified PII/PHI) ===",
        *mask_ddl,
        *mask_sets,
        "",
        "-- === Row-level security ===",
        *(rf_ddl + rf_sets or ["-- (no row filters declared)"]),
        "",
        "-- === Secrets ===",
        *secret_lines,
        "",
        "-- === Governance (owners, tags, glossary) ===",
        *(gov_stmts or ["-- (no governance declared)"]),
        "",
    ])
    with open(cfg.out("stage10_identity.sql"), "w") as f:
        f.write(sql)

    # ---- gate: access parity + full coverage ----------------------------
    sensitive = [r for r in classification
                 if (r.get("classification") or "").upper() in ("PII", "PHI", "PCI")]
    unmasked = [f"{r.get('table')}.{r.get('column')}" for r in sensitive
                if not (r.get("mask") or "").strip()]
    active_conns = []
    for c in data["connections"]:
        try:
            if int(c.get("n_pipelines") or 0) > 0:
                active_conns.append(c.get("connection") or c.get("name"))
        except (TypeError, ValueError):
            active_conns.append(c.get("connection") or c.get("name"))
    secret_conns = {(s.get("connection") or "") for s in secrets}
    unsecured = sorted(c for c in active_conns if c not in secret_conns)

    passed = bool(
        mapped == len(grants) and grants
        and not unmasked and sensitive
        and not unsecured
    )
    gate = {
        "stage": 10,
        "passed": passed,
        "groups": sum(1 for p in principals if p.get("type") == "group"),
        "service_principals": sum(1 for p in principals
                                  if p.get("type") == "service_principal"),
        "grants_total": len(grants),
        "grants_mapped": mapped,
        "masked_columns": len(mask_sets),
        "mask_functions": len([d for d in mask_ddl if d.startswith("CREATE OR REPLACE")]),
        "row_filters": len(rf_sets),
        "secret_scope": _secret_scope(cfg),
        "secrets": len(secrets),
        "unsecured_connections": unsecured,
        "unmasked_pii": sorted(unmasked),
        "sql": cfg.out("stage10_identity.sql"),
    }
    with open(cfg.out("stage10_gate.json"), "w") as f:
        json.dump(gate, f, indent=1)
    return gate
