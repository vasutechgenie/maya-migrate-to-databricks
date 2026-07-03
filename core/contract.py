"""
contract.py -- the deterministic per-pipeline build contract.

For each pipeline it derives, straight from the normalized graph (never invented):
  * pattern + engine + kind
  * prereqs  - everything it reads but does not produce (the bronze landing set)
  * produced - every table it writes, each tagged with a medallion layer
  * parity   - the persisted silver/gold outputs to schema/data compare vs source
  * procs    - reachable stored procs (with their source file when known)
  * mermaid  - a bronze->silver->gold data-flow diagram source

The classifier is signal-driven and configurable: the defaults are reasonable
Synapse-style heuristics, but a project/adapter can override signals via
AcceleratorConfig or by supplying its own `signals` mapping.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from .graph import Graph
from . import engines as E


# Default classification signals (reasonable Synapse-style defaults; override per project).
# These are generic examples; tune them per source via AcceleratorConfig or a `signals` dict.
DEFAULT_SIGNALS = {
    "control_configs": {"metadata.etl_control", "metadata.control",
                        "config.etl_control"},                   # -> A
    "dynamic_configs": {"metadata.dynamic_sql", "config.job_control"},  # -> C
    "dynamic_name_hints": ["dynamic", "benchmark", "_dyn_"],
    "file_name_hints": ["intake", "file", "extract", "dropoff", "xml"],
    "replication_hints": ["qlik", "replicate", "cdc"],
    "replication_config": "metadata.replication_tables",
    "serving_schema": "serving",
}


def classify_pattern(g: Graph, pk: str, cfg, signals: dict) -> str:
    o = g.objects[pk]
    nm = o["name"].lower()
    cfgs = g.config_reads.get(pk, set())
    exelp = bool(g.exec_pipe.get(pk))
    direct = list(g.calls.get(pk, ()))
    _ins, writes, _procs = g.pipeline_io(pk)
    home = (cfg.home_database or "").lower()
    ext = any((g.objects.get(dk, {}).get("target_database", "").lower()
               not in ("", home)) for dk in direct)
    entry = " ".join(g.objects[dk]["name"].lower() for dk in direct if dk in g.objects)

    rep_cfg = signals["replication_config"]
    if (any(h in nm for h in signals["replication_hints"]) or rep_cfg in cfgs
            or any(h in entry for h in signals["replication_hints"])
            or any(w.startswith(signals["serving_schema"] + ".") for w in writes)):
        return "F"
    if ext and len(writes) == 0:
        return "E"
    if signals["control_configs"] & cfgs:
        return "A"
    if (signals["dynamic_configs"] & cfgs
            or any(h in nm or h in entry for h in signals["dynamic_name_hints"])):
        return "C"
    if any(h in nm for h in signals["file_name_hints"]):
        return "D"
    if len(writes) > 0 or direct:
        return "B"
    if exelp:
        return "G"
    return "X"


def kind_of(pattern: str, has_writes: bool) -> str:
    if pattern in E.KIND_OF_PATTERN:
        return E.KIND_OF_PATTERN[pattern]
    return "medallion" if has_writes else "utility"


def build_context(g: Graph, pk: str, cfg, wave: int = 0,
                  ddl_index: Optional[Dict[str, List[str]]] = None,
                  signals: Optional[dict] = None) -> dict:
    signals = signals or DEFAULT_SIGNALS
    ddl_index = ddl_index or {}
    name = g.name_of[pk]
    ins, outs, procs = g.pipeline_io(pk)
    pattern = classify_pattern(g, pk, cfg, signals)
    engine = E.engine_of_pattern(pattern)
    kind = kind_of(pattern, bool(outs))

    prereqs = sorted(ins - outs)
    produced = []
    for t in sorted(outs):
        layer = cfg.layer_of(t)
        produced.append({"table": t, "layer": layer,
                         "ddl_columns": ddl_index.get(t, [])})
    # parity targets: persisted silver/gold outputs (kept), with DDL when known
    parity = [p for p in produced if p["layer"] in ("silver", "gold")]

    proc_rows = []
    for prk in sorted(procs):
        po = g.objects.get(prk, {})
        proc_rows.append({"name": po.get("name", prk),
                          "source_file": po.get("source_file", "")})

    ctx = {
        "pipeline": name,
        "wave": wave,
        "pattern": pattern,
        "pattern_label": E.PATTERN_LABELS[pattern],
        "engine": engine,
        "engine_label": E.ENGINE_LABELS[engine],
        "kind": kind,
        "n_prereqs": len(prereqs),
        "n_produced": len(produced),
        "n_parity": len(parity),
        "n_gold": sum(1 for p in produced if p["layer"] == "gold"),
        "n_silver": sum(1 for p in produced if p["layer"] == "silver"),
        "n_procs": len(proc_rows),
        "prereqs": prereqs,
        "produced": produced,
        "parity": parity,
        "procs": proc_rows,
        "mermaid": _mermaid(name, prereqs, produced),
    }
    return ctx


def _mermaid(name, prereqs, produced) -> str:
    lines = ["flowchart LR"]
    lines.append(f'  src["{len(prereqs)} bronze inputs"] --> silver["silver hubs"]')
    ng = sum(1 for p in produced if p["layer"] == "gold")
    lines.append(f'  silver --> gold["{ng} gold parity tables"]')
    return "\n".join(lines)


def generate_all(cfg, ddl_index: Optional[Dict[str, List[str]]] = None,
                 signals: Optional[dict] = None, wave_of: Optional[dict] = None,
                 progress: Optional[Callable[[int, int], None]] = None) -> dict:
    """Write context/<pipeline>.json for every pipeline + an index.json. Returns stats."""
    g = Graph.from_config(cfg)
    ctx_dir = cfg.p(cfg.specs_dir, "context")
    os.makedirs(ctx_dir, exist_ok=True)

    # wave lookup from published pipelines file if not provided
    if wave_of is None:
        wave_of = {}
        pub = cfg.out("build_order_pipelines.csv")
        if os.path.exists(pub):
            import csv
            with open(pub, newline="") as f:
                for r in csv.DictReader(f):
                    try:
                        wave_of[r["pipeline"]] = int(r["wave"])
                    except (KeyError, ValueError):
                        pass

    pks = g.pipeline_keys()
    index = []
    for i, pk in enumerate(sorted(pks, key=lambda k: g.name_of[k])):
        name = g.name_of[pk]
        ctx = build_context(g, pk, cfg, wave=wave_of.get(name, 0),
                            ddl_index=ddl_index, signals=signals)
        with open(os.path.join(ctx_dir, f"{name}.json"), "w") as f:
            json.dump(ctx, f, indent=1)
        index.append({k: ctx[k] for k in ("pipeline", "wave", "pattern", "engine",
                                          "kind", "n_prereqs", "n_produced",
                                          "n_parity", "n_gold", "n_silver", "n_procs")})
        if progress:
            progress(i + 1, len(pks))
    with open(cfg.p(cfg.specs_dir, "index.json"), "w") as f:
        json.dump(index, f, indent=1)
    return {"pipelines": len(index),
            "parity_targets": sum(r["n_parity"] for r in index)}
