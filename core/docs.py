"""
docs.py -- Stage 9: generate comprehensive migration docs from the derived artifacts.

Emits markdown under out/docs/generated/ for every pipeline, table, view, and BI object
- lineage, DDL columns, medallion layer, MAYA parity/certification status (from
gates.json), and the BI mapping - plus an index. Pure read of what earlier stages
produced; no external calls. The gate passes when a doc exists for every object.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Dict, List

from .graph import Graph


def _docs_root(cfg) -> str:
    d = cfg.out(os.path.join("docs", "generated"))
    os.makedirs(d, exist_ok=True)
    return d


def _load_json(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


def _write(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text.rstrip() + "\n")


def run(cfg) -> dict:
    root = _docs_root(cfg)
    g = Graph.from_config(cfg)
    gates = _load_json(cfg.out("gates.json"), {})
    try:
        ddl = cfg.load_adapter().ddl_index()
    except Exception:
        ddl = {}

    # lineage maps
    producers: Dict[str, List[str]] = defaultdict(list)
    consumers: Dict[str, List[str]] = defaultdict(list)
    ctx_of: Dict[str, dict] = {}
    for pk in g.pipeline_keys():
        name = g.name_of[pk]
        cp = cfg.p(cfg.specs_dir, "context", f"{name}.json")
        ctx_of[name] = _load_json(cp, {})
        ins, outs, _ = g.pipeline_io(pk)
        for t in outs:
            producers[t].append(name)
        for t in ins:
            consumers[t].append(name)

    for d in ("pipelines", "tables", "views", "bi"):
        os.makedirs(os.path.join(root, d), exist_ok=True)

    # ---- pipelines --------------------------------------------------------
    pipe_docs = []
    for pk in sorted(g.pipeline_keys(), key=lambda k: g.name_of[k]):
        name = g.name_of[pk]
        ctx = ctx_of.get(name, {})
        gate = gates.get(name, {})
        lines = [f"# Pipeline: {name}", "",
                 f"- **Pattern**: {ctx.get('pattern','?')} - {ctx.get('pattern_label','')}",
                 f"- **Engine**: {ctx.get('engine','?')} - {ctx.get('engine_label','')}",
                 f"- **Kind**: {ctx.get('kind','')}",
                 f"- **Wave**: {ctx.get('wave',0)}",
                 f"- **Certification**: {gate.get('status','(not certified)')} "
                 f"(dev={gate.get('maya_dev','-')}, sit={gate.get('maya_sit','-')}, "
                 f"soak={gate.get('maya_soak','-')})", ""]
        prereqs = ctx.get("prereqs", [])
        lines += ["## Prerequisites", ""] + (
            [f"- `{t}`" for t in prereqs] or ["- (none)"]) + [""]
        lines += ["## Produced tables", ""]
        for p in ctx.get("produced", []):
            lines.append(f"- `{p['table']}` ({p.get('layer')}) - "
                         f"{len(p.get('ddl_columns', []))} columns")
        if not ctx.get("produced"):
            lines.append("- (none)")
        lines += ["", "## Parity targets", ""] + (
            [f"- `{p['table']}` ({p.get('layer')})" for p in ctx.get("parity", [])]
            or ["- (none)"])
        if ctx.get("procs"):
            lines += ["", "## Stored procedures", ""] + \
                [f"- `{p['name']}`" for p in ctx["procs"]]
        _write(os.path.join(root, "pipelines", f"{name}.md"), "\n".join(lines))
        pipe_docs.append(name)

    # ---- tables + views ---------------------------------------------------
    table_docs, view_docs = [], []
    for k, o in sorted(g.objects.items(), key=lambda kv: kv[1].get("name", kv[0])):
        typ = o.get("type")
        if typ not in ("TABLE", "CONFIG_TABLE", "VIEW"):
            continue
        name = o.get("name", k)
        cols = ddl.get(name, []) or ddl.get(name.lower(), [])
        prods = producers.get(name.lower(), []) + producers.get(name, [])
        cons = consumers.get(name.lower(), []) + consumers.get(name, [])
        cert = "-"
        if prods:
            statuses = {gates.get(p, {}).get("status", "?") for p in prods}
            cert = ", ".join(sorted(statuses))
        lines = [f"# {'View' if typ == 'VIEW' else 'Table'}: {name}", "",
                 f"- **Type**: {typ}",
                 f"- **Layer**: {o.get('layer') or cfg.layer_of(name)}",
                 f"- **External system**: {o.get('external_system') or '(home)'}",
                 f"- **Produced by**: {', '.join(sorted(set(prods))) or '(source/external)'}",
                 f"- **Read by**: {', '.join(sorted(set(cons))) or '(none)'}",
                 f"- **Producer certification**: {cert}", "",
                 "## Columns", ""]
        lines += ([f"- `{c}`" for c in cols] or ["- (columns not captured)"])
        sub = "views" if typ == "VIEW" else "tables"
        _write(os.path.join(root, sub, f"{name}.md"), "\n".join(lines))
        (view_docs if typ == "VIEW" else table_docs).append(name)

    # ---- BI ---------------------------------------------------------------
    bi_docs = []
    from . import bi as bi_mod
    for o in bi_mod.load_objects(cfg):
        rec_path = os.path.join(cfg.out("bi_authored"), f"{bi_mod._safe(o.obj_id)}.json")
        rec = _load_json(rec_path, {})
        lines = [f"# BI object: {o.obj_id}", "",
                 f"- **System**: {o.system}",
                 f"- **Dashboard / tile**: {o.dashboard} / {o.tile}",
                 f"- **Target tables**: {', '.join(o.target_tables) or '(none)'}",
                 f"- **Parity passed**: {rec.get('parity_passed', '?')}",
                 f"- **Republished**: {rec.get('republished', '?')}",
                 f"- **Genie/Lakeview**: {rec.get('genie_created', '?')}", "",
                 "## Original query", "", "```sql", o.original_query, "```", "",
                 "## Converted (Databricks) query", "", "```sql",
                 rec.get("converted_query") or o.converted_query, "```"]
        _write(os.path.join(root, "bi", f"{bi_mod._safe(o.obj_id)}.md"),
               "\n".join(lines))
        bi_docs.append(o.obj_id)

    # ---- index ------------------------------------------------------------
    idx = [f"# {cfg.project_name} - Migration documentation", "",
           "Generated by MAYA Stage 9 from the derived migration artifacts.", "",
           f"## Pipelines ({len(pipe_docs)})", ""]
    idx += [f"- [{p}](pipelines/{p}.md)" for p in sorted(pipe_docs)]
    idx += ["", f"## Tables ({len(table_docs)})", ""]
    idx += [f"- [{t}](tables/{t}.md)" for t in sorted(table_docs)]
    idx += ["", f"## Views ({len(view_docs)})", ""]
    idx += [f"- [{v}](views/{v}.md)" for v in sorted(view_docs)]
    idx += ["", f"## BI objects ({len(bi_docs)})", ""]
    idx += [f"- [{b}](bi/{bi_mod._safe(b)}.md)" for b in sorted(bi_docs)]
    _write(os.path.join(root, "index.md"), "\n".join(idx))

    total = len(pipe_docs) + len(table_docs) + len(view_docs) + len(bi_docs)
    gate = {"stage": 9, "passed": total > 0, "root": root,
            "pipelines": len(pipe_docs), "tables": len(table_docs),
            "views": len(view_docs), "bi": len(bi_docs)}
    with open(cfg.out("stage9_docs.json"), "w") as f:
        json.dump(gate, f, indent=1)
    return gate
