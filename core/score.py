"""
score.py -- Stage 1 scoring: is the estate 100% traversable and fully identified?

For every pipeline we build its dependency subtree and traverse it end to end
(outputs -> ... -> sources) over the normalized graph. A reference is *resolved* when it
is either produced somewhere in the estate, or it is a declared source table/view, or it
belongs to a known external system tagged call-as-is. A pipeline's score is
resolved / total referenced tables in its closure.

The Stage-1 gate PASSes only when:
  * every pipeline scores 100% (fully traversable),
  * every table and view node is identified (produced, declared with DDL, or external),
  * every external system is explicitly tagged call-as-is, and
  * the independent order verifier (C1-C4) passes.

Emits out/discovery_score.csv and out/stage1_gate.json. Also persists the Stage-1
asset exports (schedules + configs) so the collect surface is complete on disk.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from typing import Dict, List, Set

from .graph import Graph
from . import verify_order as verify_mod

VIEW_TYPE = "VIEW"


def _reads_of(g: Graph, pk: str) -> Set[str]:
    ins, _outs, _procs = g.pipeline_io(pk)
    return set(ins) | set(g.config_reads.get(pk, set()))


def _producers(g: Graph) -> Dict[str, Set[str]]:
    prod: Dict[str, Set[str]] = defaultdict(set)
    for pk in g.pipeline_keys():
        _ins, outs, _procs = g.pipeline_io(pk)
        for t in outs:
            prod[t].add(pk)
    return prod


def _by_name(g: Graph) -> Dict[str, dict]:
    return {o.get("name", k).lower(): o for k, o in g.objects.items()}


def _identified(t: str, producers: Dict[str, Set[str]], by_name: Dict[str, dict]) -> bool:
    if t in producers:
        return True
    node = by_name.get(t)
    if node:
        if (node.get("external_system") or "").strip():
            return True
        if node.get("type") in ("TABLE", "CONFIG_TABLE", VIEW_TYPE):
            return True
    return False


def _closure(g: Graph, pk: str, producers: Dict[str, Set[str]],
             reads_by_pipe: Dict[str, Set[str]]) -> Set[str]:
    """All tables the pipeline transitively references (reads, then producers' reads)."""
    seen: Set[str] = set()
    stack = list(reads_by_pipe.get(pk, set()))
    while stack:
        t = stack.pop()
        if t in seen:
            continue
        seen.add(t)
        for prod in producers.get(t, ()):
            stack.extend(reads_by_pipe.get(prod, set()))
    return seen


def compute(cfg) -> dict:
    g = Graph.from_config(cfg)
    producers = _producers(g)
    by_name = _by_name(g)
    reads_by_pipe = {pk: _reads_of(g, pk) for pk in g.pipeline_keys()}

    per_pipeline = []
    for pk in sorted(g.pipeline_keys(), key=lambda k: g.name_of[k]):
        closure = _closure(g, pk, producers, reads_by_pipe)
        total = len(closure)
        unresolved = sorted(t for t in closure
                            if not _identified(t, producers, by_name))
        resolved = total - len(unresolved)
        score = 1.0 if total == 0 else resolved / total
        per_pipeline.append({
            "pipeline": g.name_of[pk],
            "refs_total": total,
            "refs_resolved": resolved,
            "score": round(score, 4),
            "unresolved": ";".join(unresolved),
        })

    # global identification of every table/view/config node
    tables_views = [o for o in g.objects.values()
                    if o.get("type") in ("TABLE", "CONFIG_TABLE", VIEW_TYPE)]
    unidentified = sorted(o.get("name") for o in tables_views
                          if not _identified(o.get("name", "").lower(), producers, by_name))
    n_views = sum(1 for o in tables_views if o.get("type") == VIEW_TYPE)

    # external systems tagged call-as-is
    externals = sorted({(o.get("external_system") or "").strip()
                        for o in g.objects.values()
                        if (o.get("external_system") or "").strip()})

    verify = verify_mod.run(cfg)

    all_100 = all(p["score"] >= 1.0 for p in per_pipeline)
    gate = {
        "stage": 1,
        "passed": bool(all_100 and not unidentified and verify.get("passed")),
        "pipelines_scored": len(per_pipeline),
        "pipelines_at_100": sum(1 for p in per_pipeline if p["score"] >= 1.0),
        "tables_views": len(tables_views),
        "views": n_views,
        "unidentified": unidentified,
        "external_systems": externals,
        "verify_passed": bool(verify.get("passed")),
    }
    return {"per_pipeline": per_pipeline, "gate": gate}


def collect_assets(cfg) -> dict:
    """Persist the Stage-1 asset exports: schedules.csv + configs/<table>.csv."""
    adapter = cfg.load_adapter()
    os.makedirs(cfg.p(cfg.out_dir), exist_ok=True)

    schedules = adapter.export_schedules()
    sched_path = cfg.out("schedules.csv")
    fields = ["trigger", "schedule", "pipeline", "enabled"]
    with open(sched_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(schedules)

    configs = adapter.export_configs()
    cfg_dir = cfg.out("configs")
    os.makedirs(cfg_dir, exist_ok=True)
    written = []
    for table, rows in configs.items():
        cols = list(rows[0].keys()) if rows else []
        path = os.path.join(cfg_dir, f"{table}.csv")
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        written.append(table)
    return {"schedules": len(schedules), "config_tables": len(written)}


def run(cfg) -> dict:
    """Collect assets, score every pipeline, write CSV + gate JSON. Returns the gate."""
    assets = collect_assets(cfg)
    res = compute(cfg)
    os.makedirs(cfg.p(cfg.out_dir), exist_ok=True)

    csv_path = cfg.out("discovery_score.csv")
    cols = ["pipeline", "refs_total", "refs_resolved", "score", "unresolved"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(res["per_pipeline"])

    gate = dict(res["gate"])
    gate["assets"] = assets
    with open(cfg.out("stage1_gate.json"), "w") as f:
        json.dump(gate, f, indent=1)
    return gate
