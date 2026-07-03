"""
orchestration.py -- deterministic, resumable scaffolding around the AI coding-agent
runs. It does NOT call an LLM; it prepares work and validates output so a pool of
agents can author specs in parallel, wave by wave, and the run is freely resumable.

A pipeline is "done" iff a VALID authored/<pipeline>.json exists, so batches resume
naturally. Public helpers: status(), pending(), prompt(), validate().
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import List, Optional

# required top-level keys per kind for an authored spec
REQUIRED = {
    "medallion": ["summary", "bronze", "silver", "gold", "parity"],
    "orchestration": ["summary", "parity"],
    "external_invoke": ["summary", "parity"],
    "utility": ["summary", "parity"],
}
LAYER_KEYS = ["desc", "code"]

_TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "templates", "agent_prompt.md")


def _wave(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 99


def load_index(cfg) -> List[dict]:
    path = cfg.p(cfg.specs_dir, "index.json")
    if not os.path.exists(path):
        return []
    return json.load(open(path))


def _authored_dir(cfg) -> str:
    d = cfg.p(cfg.specs_dir, "authored")
    os.makedirs(d, exist_ok=True)
    return d


def _context(cfg, pipeline) -> Optional[dict]:
    path = cfg.p(cfg.specs_dir, "context", f"{pipeline}.json")
    return json.load(open(path)) if os.path.exists(path) else None


def is_authored(cfg, pipeline, kind) -> bool:
    path = os.path.join(_authored_dir(cfg), f"{pipeline}.json")
    if not os.path.exists(path):
        return False
    try:
        d = json.load(open(path))
    except Exception:
        return False
    return all(k in d for k in REQUIRED.get(kind, ["summary", "parity"]))


def status(cfg) -> dict:
    idx = load_index(cfg)
    by_wave = defaultdict(lambda: [0, 0])   # wave -> [done, total]
    by_kind = defaultdict(lambda: [0, 0])
    done = 0
    for r in idx:
        d = is_authored(cfg, r["pipeline"], r["kind"])
        by_wave[_wave(r["wave"])][1] += 1
        by_kind[r["kind"]][1] += 1
        if d:
            done += 1
            by_wave[_wave(r["wave"])][0] += 1
            by_kind[r["kind"]][0] += 1
    return {"total": len(idx), "done": done, "pending": len(idx) - done,
            "by_wave": {k: by_wave[k] for k in sorted(by_wave)},
            "by_kind": dict(by_kind)}


def pending(cfg, wave: Optional[int] = None, limit: Optional[int] = None,
            kind: Optional[str] = None) -> List[dict]:
    idx = load_index(cfg)
    rows = []
    for r in sorted(idx, key=lambda x: (_wave(x["wave"]), x["pipeline"])):
        if wave is not None and _wave(r["wave"]) != wave:
            continue
        if kind is not None and r["kind"] != kind:
            continue
        if is_authored(cfg, r["pipeline"], r["kind"]):
            continue
        rows.append(r)
        if limit and len(rows) >= limit:
            break
    return rows


def prompt(cfg, pipeline: str) -> str:
    ctx = _context(cfg, pipeline)
    if ctx is None:
        return f"# ERROR: no context pack for {pipeline} (run `context` first)"
    template = (open(_TEMPLATE).read() if os.path.exists(_TEMPLATE)
                else _FALLBACK_TEMPLATE)
    return (template
            .replace("{{PIPELINE}}", pipeline)
            .replace("{{KIND}}", ctx.get("kind", ""))
            .replace("{{ENGINE}}", ctx.get("engine", ""))
            .replace("{{CONTEXT_JSON}}", json.dumps(ctx, indent=1)))


def validate(cfg, pipeline: str) -> dict:
    ctx = _context(cfg, pipeline)
    kind = ctx.get("kind", "utility") if ctx else "utility"
    path = os.path.join(_authored_dir(cfg), f"{pipeline}.json")
    if not os.path.exists(path):
        return {"pipeline": pipeline, "ok": False, "error": "no authored json"}
    try:
        d = json.load(open(path))
    except Exception as e:
        return {"pipeline": pipeline, "ok": False, "error": f"invalid json: {e}"}
    missing = [k for k in REQUIRED.get(kind, ["summary", "parity"]) if k not in d]
    for layer in ("bronze", "silver", "gold"):
        if layer in REQUIRED.get(kind, []) and isinstance(d.get(layer), dict):
            for lk in LAYER_KEYS:
                if lk not in d[layer]:
                    missing.append(f"{layer}.{lk}")
    return {"pipeline": pipeline, "ok": not missing, "missing": missing}


def validate_all(cfg) -> dict:
    idx = load_index(cfg)
    res = [validate(cfg, r["pipeline"]) for r in idx]
    return {"total": len(res), "ok": sum(1 for r in res if r["ok"]),
            "failures": [r for r in res if not r["ok"]]}


_FALLBACK_TEMPLATE = """# Author the Databricks build for {{PIPELINE}}
Kind: {{KIND}}  Engine: {{ENGINE}}

Read the context pack below. Translate the REAL source logic (never invent). Author
bronze/silver/gold notebooks (SQL-first). Every parity table must appear in code with
the source-identical schema. Output authored/{{PIPELINE}}.json.

MAYA Definition of Done:
 1. MAYA-Dev: run on the sampled dev tables; pass the dev profile (schema, keys,
    referential integrity, no-extra-output, idempotency, row-level sample).
 2. MAYA-SIT: only after dev is green, run at scale on prod-copied data; pass all 10
    checks at the pinned watermark. Dev + SIT green = PROVISIONAL certification.
 3. MAYA-Soak: run the pipeline in parallel with the source and re-prove parity at each
    soak window (T+7, T+14) on the cumulative table AND the incremental delta window.
    Zero drift at every window = FINAL certification. Any drift is a defect
    (INCREMENTAL-LOGIC / LATE-DATA): fix, re-backfill the window, restart the soak clock.

## Context
{{CONTEXT_JSON}}
"""
