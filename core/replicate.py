"""
replicate.py -- Stage 2: replicate the WHOLE source estate into a Databricks test
catalog and fill it with data that preserves referential integrity.

Generalizes the per-pipeline RI sampling in maya.py to every table and view:

  * emit CREATE CATALOG/SCHEMA for maya.test_catalog,
  * for every table, replicate its DDL and fill it - by SAMPLING the source with RI
    when a source_ref_catalog is configured, else by generating deterministic SYNTHETIC
    rows (default 10k) with referential integrity via topological fill: parents are
    filled first and a child's foreign-key columns draw from existing parent keys,
  * replicate every VIEW definition (translated to Spark SQL via the adapter).

Emits out/stage2_replicate.sql (runnable on a Databricks SQL warehouse) and
out/stage2_manifest.csv. The gate passes when every table AND view is present.
"""
from __future__ import annotations

import csv
import os
import re
from typing import Dict, List, Optional, Tuple

from .graph import Graph
from . import order as order_mod

_TYPE_DATE = ("DATE", "DATETIME", "TIMESTAMP", "SMALLDATETIME")


def _read_sql(path: str) -> str:
    try:
        return open(path, errors="ignore").read()
    except Exception:
        return ""


def _resolve(cfg, source_file: str) -> str:
    """Resolve a graph source_file path, which is relative to the source discovery dir.

    Tries the adapter's source_dir first (where artifacts actually live), then base_dir,
    so replication works whether outputs are derived in-place or into a temp dir.
    """
    if not source_file:
        return ""
    if os.path.isabs(source_file) and os.path.exists(source_file):
        return source_file
    src_dir = (cfg.adapter_options or {}).get("source_dir", "")
    for cand in (os.path.join(src_dir, source_file) if src_dir else "",
                 cfg.p(source_file)):
        if cand and os.path.exists(cand):
            return cand
    return cfg.p(source_file)


def _typed_cols(sql: str) -> List[Tuple[str, str]]:
    """[(name, type)] in declaration order from a CREATE TABLE (...) statement."""
    i = sql.upper().find("CREATE TABLE")
    if i < 0:
        return []
    j = sql.find("(", i)
    if j < 0:
        return []
    depth, parts, cur = 0, [], ""
    for ch in sql[j:]:
        if ch == "(":
            depth += 1
            if depth == 1:
                continue
        if ch == ")":
            depth -= 1
            if depth == 0:
                if cur.strip():
                    parts.append(cur.strip())
                break
        if depth == 1 and ch == ",":
            parts.append(cur.strip())
            cur = ""
            continue
        cur += ch
    skip = ("CONSTRAINT", "PRIMARY", "INDEX", "WITH", "UNIQUE", "FOREIGN",
            "CLUSTERED", "NONCLUSTERED", ")")
    out = []
    for p in parts:
        p = p.strip().replace("[", "").replace("]", "")
        if not p or p.upper().startswith(skip):
            continue
        toks = p.split()
        if len(toks) >= 2:
            out.append((toks[0], toks[1].upper()))
        elif toks:
            out.append((toks[0], "STRING"))
    return out


def _pk_cols(sql: str) -> List[str]:
    m = re.search(r"PRIMARY\s+KEY\s*\(([^)]*)\)", sql, flags=re.I)
    if not m:
        return []
    return [c.strip().replace("[", "").replace("]", "") for c in m.group(1).split(",")]


def _short(name: str) -> str:
    return name.split(".")[-1].lower()


def _synthetic_value(col: str, typ: str, pk_single: Optional[str],
                     fk_parent_rows: Optional[int]) -> str:
    """Deterministic per-row expression given a sequence id `i`."""
    if col == pk_single:
        return "i"
    if fk_parent_rows:
        return f"pmod(i - 1, {fk_parent_rows}) + 1"
    t = typ.upper()
    if any(t.startswith(x) for x in _TYPE_DATE):
        return "date_add(DATE'2024-01-01', pmod(i, 365))"
    if t.startswith(("DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL")):
        return "cast(i AS double) * 1.0"
    if t.startswith(("INT", "BIGINT", "SMALLINT", "TINYINT")):
        return "i"
    if t.startswith("BIT") or t.startswith("BOOL"):
        return "pmod(i, 2)"
    return f"concat('{col}_', cast(i AS string))"


def plan(cfg) -> dict:
    g = Graph.from_config(cfg)
    table_wave, _pipe_wave, _meta = order_mod.compute(g)

    # column + pk sources
    typed: Dict[str, List[Tuple[str, str]]] = {}
    pks: Dict[str, List[str]] = {}
    by_short_home: Dict[str, str] = {}
    art = cfg.p(cfg.adapter_options.get("artifacts_dir", cfg.artifacts_dir))
    for k, o in g.objects.items():
        if o.get("type") not in ("TABLE", "CONFIG_TABLE"):
            continue
        name = o.get("name", k)
        sf = o.get("source_file", "")
        if sf:
            sql = _read_sql(_resolve(cfg, sf))
            cols = _typed_cols(sql)
            if cols:
                typed[name] = cols
                pks[name] = _pk_cols(sql)
                by_short_home[_short(name)] = name

    # external/source tables without DDL reuse a home table of the same short name
    for k, o in g.objects.items():
        if o.get("type") not in ("TABLE", "CONFIG_TABLE"):
            continue
        name = o.get("name", k)
        if name in typed:
            continue
        home = by_short_home.get(_short(name))
        if home:
            typed[name] = typed[home]
            pks[name] = pks[home]
        else:
            typed[name] = [("id", "BIGINT"), ("payload", "STRING")]
            pks[name] = ["id"]

    # single-col pk -> owning table, for FK resolution
    pk_owner: Dict[str, str] = {}
    for name, pk in pks.items():
        if len(pk) == 1:
            pk_owner.setdefault(pk[0], name)

    rows_of = {name: cfg.maya.sample_overrides.get(name, cfg.maya.synthetic_rows)
               for name in typed}

    table_nodes = sorted(
        [o.get("name") for o in g.objects.values()
         if o.get("type") in ("TABLE", "CONFIG_TABLE")],
        key=lambda n: (table_wave.get(n.lower(), 0), n))
    view_nodes = sorted(o.get("name") for o in g.objects.values()
                        if o.get("type") == "VIEW")

    tc = cfg.maya.test_catalog
    schemas = sorted({n.split(".")[0] for n in table_nodes + view_nodes if "." in n})
    sql: List[str] = [f"CREATE CATALOG IF NOT EXISTS {tc};"]
    for s in schemas:
        sql.append(f"CREATE SCHEMA IF NOT EXISTS {tc}.{s};")

    use_sample = bool(cfg.maya.test_from_source and cfg.maya.source_ref_catalog)
    ref = cfg.maya.source_ref_catalog
    manifest: List[dict] = []

    for name in table_nodes:
        cols = typed[name]
        pk = pks.get(name, [])
        pk_single = pk[0] if len(pk) == 1 else None
        n = rows_of[name]
        fq = f"{tc}.{name}"
        fks = []
        if use_sample:
            sql.append(f"-- replicate {name} (sample-from-source, RI-preserving)")
            sql.append(f"CREATE OR REPLACE TABLE {fq} AS "
                       f"SELECT * FROM {ref}.{name} LIMIT {n};")
            fill = "sample"
        else:
            selects = []
            for col, typ in cols:
                parent = pk_owner.get(col)
                fk_rows = None
                if parent and parent != name and col != pk_single:
                    fk_rows = rows_of.get(parent)
                    if fk_rows:
                        fks.append(f"{col}->{parent}")
                expr = _synthetic_value(col, typ, pk_single, fk_rows)
                selects.append(f"    {expr} AS {col}")
            body = ",\n".join(selects)
            sql.append(f"-- replicate {name} (synthetic {n} rows, RI via topo fill)")
            sql.append(
                f"CREATE OR REPLACE TABLE {fq} AS\n"
                f"  SELECT\n{body}\n"
                f"  FROM (SELECT explode(sequence(1, {n})) AS i);")
            fill = "synthetic"
        manifest.append({"object": name, "kind": "config" if name in
                         [o.get("name") for o in g.objects.values()
                          if o.get("type") == "CONFIG_TABLE"] else "table",
                         "fill": fill, "rows": n, "pk": ";".join(pk),
                         "fks": ";".join(fks),
                         "wave": table_wave.get(name.lower(), 0)})

    # views last: they depend on tables
    adapter = cfg.load_adapter()
    for name in view_nodes:
        o = next((x for x in g.objects.values() if x.get("name") == name), {})
        sf = o.get("source_file", "")
        vsql = _read_sql(_resolve(cfg, sf)) if sf else ""
        translated = adapter.dialect_translate(vsql) if vsql else \
            f"SELECT 1 -- view definition unavailable for {name}"
        # repoint the CREATE VIEW target into the test catalog
        translated = re.sub(r"(?is)^\s*CREATE\s+VIEW\s+\S+",
                            f"CREATE VIEW {tc}.{name}", translated, count=1)
        if not translated.upper().lstrip().startswith("CREATE VIEW"):
            translated = f"CREATE VIEW {tc}.{name} AS\n{translated}"
        sql.append(f"-- replicate view {name}")
        sql.append(translated.rstrip().rstrip(";") + ";")
        manifest.append({"object": name, "kind": "view", "fill": "view_ddl",
                         "rows": "", "pk": "", "fks": "",
                         "wave": table_wave.get(name.lower(), 0)})

    total = len(table_nodes) + len(view_nodes)
    gate = {
        "stage": 2,
        "passed": len(manifest) == total and total > 0,
        "tables": len(table_nodes),
        "views": len(view_nodes),
        "replicated": len(manifest),
        "test_catalog": tc,
        "fill_mode": "sample" if use_sample else "synthetic",
    }
    return {"sql": sql, "manifest": manifest, "gate": gate}


def run(cfg) -> dict:
    res = plan(cfg)
    os.makedirs(cfg.p(cfg.out_dir), exist_ok=True)
    with open(cfg.out("stage2_replicate.sql"), "w") as f:
        f.write("\n".join(res["sql"]) + "\n")
    cols = ["object", "kind", "fill", "rows", "pk", "fks", "wave"]
    with open(cfg.out("stage2_manifest.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(res["manifest"])
    import json
    with open(cfg.out("stage2_gate.json"), "w") as f:
        json.dump(res["gate"], f, indent=1)
    return res["gate"]
