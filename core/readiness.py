"""
readiness.py -- Stage 0: collect + score the *non-data* estate.

Stage 1 proves the data estate is 100% traversable; Stage 0 does the equivalent for
everything a large migration also has to carry over but that is not a pipeline:

  * identity  - users, groups, roles, service principals (who exists)
  * access    - the grant matrix (who can touch what)
  * secrets   - the credential inventory backing every connection (names/scopes only)
  * data classification - which columns are sensitive (PII/PHI/PCI) and how they are masked
  * security posture facts - encryption, network, audit, compliance

It collects these via the adapter's Stage-0 hooks into out/readiness/ and evaluates a
hard gate. The gate PASSes only when the collected estate is internally consistent:

  * at least one principal is collected,
  * every grant references a known principal AND an object that resolves to a home
    schema or a known table/view,
  * every secret references a known connection, and every active connection
    (n_pipelines > 0) is backed by a secret,
  * at least one column is classified, and every sensitive column has a mask.

Emits out/readiness/{principals,grants,secrets,classification}.csv,
out/readiness/security_facts.json, and out/stage0_gate.json.
"""
from __future__ import annotations

import csv
import json
import os
from typing import Dict, List

from .graph import Graph

TABLE_LIKE = ("TABLE", "CONFIG_TABLE", "VIEW")


def _readiness_dir(cfg) -> str:
    d = cfg.out("readiness")
    os.makedirs(d, exist_ok=True)
    return d


def _write_csv(path: str, rows: List[dict], fields: List[str]):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _home_schemas_and_objects(cfg):
    """Return (home_schema_set, object_name_set) for grant-object resolution."""
    try:
        g = Graph.load(cfg.objects_csv(), cfg.edges_csv(),
                       cfg.pipeline_types, cfg.table_types)
    except Exception:
        return set(), set()
    home = (cfg.home_database or "").lower()
    schemas, names = set(), set()
    for _k, o in g.objects.items():
        if o.get("type") not in TABLE_LIKE:
            continue
        names.add((o.get("name") or "").lower())
        if (o.get("external_system") or "").strip():
            continue
        if home and (o.get("target_database", "") or "").lower() not in ("", home):
            continue
        s = (o.get("schema_or_domain") or "").lower()
        if s:
            schemas.add(s)
    return schemas, names


def collect(cfg) -> dict:
    """Run the adapter Stage-0 exports and persist them under out/readiness/."""
    adapter = cfg.load_adapter()
    # ensure the normalized graph exists so schema/table resolution works even when
    # Stage 0 runs before Stage 1.
    if not (os.path.exists(cfg.objects_csv()) and os.path.exists(cfg.edges_csv())):
        adapter.build_graph()

    principals = adapter.export_principals() or []
    grants = adapter.export_grants() or []
    secrets = adapter.export_secrets() or []
    classification = adapter.classify_data() or []
    facts = adapter.export_security_facts() or {}
    connections = adapter.connections() or []

    d = _readiness_dir(cfg)
    _write_csv(os.path.join(d, "principals.csv"), principals,
               ["principal", "type", "member_of", "source_role", "description"])
    _write_csv(os.path.join(d, "grants.csv"), grants,
               ["principal", "object", "privilege"])
    _write_csv(os.path.join(d, "secrets.csv"), secrets,
               ["secret", "connection", "type", "notes"])
    _write_csv(os.path.join(d, "classification.csv"), classification,
               ["table", "column", "classification", "mask"])
    with open(os.path.join(d, "security_facts.json"), "w") as f:
        json.dump(facts, f, indent=1)

    return {"principals": principals, "grants": grants, "secrets": secrets,
            "classification": classification, "facts": facts,
            "connections": connections}


def compute(cfg, collected: dict) -> dict:
    principals = collected["principals"]
    grants = collected["grants"]
    secrets = collected["secrets"]
    classification = collected["classification"]
    connections = collected["connections"]

    principal_names = {(p.get("principal") or "").lower() for p in principals}
    groups = sum(1 for p in principals if (p.get("type") or "") == "group")
    users = sum(1 for p in principals if (p.get("type") or "") == "user")
    sps = sum(1 for p in principals
              if (p.get("type") or "") == "service_principal")

    schemas, obj_names = _home_schemas_and_objects(cfg)

    def _resolves(obj: str) -> bool:
        o = (obj or "").lower()
        return o in schemas or o in obj_names

    unknown_principals = sorted({(gr.get("principal") or "") for gr in grants
                                 if (gr.get("principal") or "").lower()
                                 not in principal_names})
    unresolved_grants = sorted({(gr.get("object") or "") for gr in grants
                                if not _resolves(gr.get("object") or "")})

    conn_names = {(c.get("connection") or c.get("name") or "").lower()
                  for c in connections}
    secret_conns = {(s.get("connection") or "").lower() for s in secrets}
    bad_secret_conns = sorted({(s.get("connection") or "") for s in secrets
                               if (s.get("connection") or "").lower()
                               not in conn_names})

    def _active(c) -> bool:
        try:
            return int(c.get("n_pipelines") or 0) > 0
        except (TypeError, ValueError):
            return True

    unsecured_connections = sorted(
        (c.get("connection") or c.get("name") or "") for c in connections
        if _active(c) and (c.get("connection") or c.get("name") or "").lower()
        not in secret_conns)

    sensitive = [r for r in classification
                 if (r.get("classification") or "").upper() in ("PII", "PHI", "PCI")]
    unmasked_pii = sorted(f"{r.get('table')}.{r.get('column')}" for r in sensitive
                          if not (r.get("mask") or "").strip())

    passed = bool(
        principal_names
        and not unknown_principals and not unresolved_grants
        and not bad_secret_conns and not unsecured_connections
        and sensitive and not unmasked_pii
    )
    gate = {
        "stage": 0,
        "passed": passed,
        "principals": len(principals),
        "groups": groups,
        "users": users,
        "service_principals": sps,
        "grants": len(grants),
        "secrets": len(secrets),
        "classified_columns": len(classification),
        "pii_columns": len(sensitive),
        "connections": len(connections),
        "unknown_principals": unknown_principals,
        "unresolved_grants": unresolved_grants,
        "bad_secret_connections": bad_secret_conns,
        "unsecured_connections": unsecured_connections,
        "unmasked_pii": unmasked_pii,
    }
    return gate


def run(cfg) -> dict:
    collected = collect(cfg)
    gate = compute(cfg, collected)
    with open(cfg.out("stage0_gate.json"), "w") as f:
        json.dump(gate, f, indent=1)
    return gate
