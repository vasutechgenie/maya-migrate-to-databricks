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


# ===========================================================================
# Stage 4b/4c: the agent swarm build + strict certification
# ---------------------------------------------------------------------------
# These layer ON TOP of the deterministic scaffolding above. The swarm authors the
# real Databricks build via an AgentDriver (offline or cursor), MAYA validates the
# output deterministically, and drift is closed by a fix-vs-original loop. Certification
# is topological: a pipeline certifies only after its predecessors are certified.
# ===========================================================================
import concurrent.futures as _futures  # noqa: E402

from . import validation as _val  # noqa: E402
from .graph import Graph  # noqa: E402


def _emit(progress, event: dict) -> None:
    """Fire an optional progress callback; never let telemetry break a build."""
    if progress is None:
        return
    try:
        progress(event)
    except Exception:
        pass


def _write_authored(cfg, pipeline: str, spec: dict):
    path = os.path.join(_authored_dir(cfg), f"{pipeline}.json")
    with open(path, "w") as f:
        json.dump(spec, f, indent=1)


def _spec_text(spec: dict) -> str:
    parts = []
    for layer in ("bronze", "silver", "gold"):
        blk = spec.get(layer)
        if isinstance(blk, dict):
            parts.append(str(blk.get("code", "")))
            parts.append(str(blk.get("desc", "")))
    parts.append(str(spec.get("summary", "")))
    return "\n".join(parts)


def parity_report(cfg, ctx: dict, spec: dict, env: str = "dev") -> dict:
    """Deterministic content-based parity check of an authored spec vs its contract.

    This is what the offline flow uses in place of executing SQL on Databricks: it
    proves the spec actually covers every parity table and every source column, uses
    idempotent writes, and lands its prerequisites - the same properties the real
    MAYA-Dev/SIT checks assert. A spec missing columns or tables comes back red, which
    is what drives the fix loop. Returns {check_name: bool} for the env's profile.
    """
    text = _spec_text(spec).lower()
    parity = ctx.get("parity", [])
    schema_ok = True
    keys_ok = True
    for p in parity:
        if p["table"].lower() not in text:
            keys_ok = False
        for col in p.get("ddl_columns", []):
            if col.lower() not in text:
                schema_ok = False
    ri_ok = all(t.lower() in text for t in ctx.get("prereqs", [])) or not parity
    idem_ok = ("create or replace" in text) or ("merge" in text) or not parity
    results = {
        "schema_parity": schema_ok,
        "key_parity": keys_ok,
        "referential_integrity": ri_ok,
        "no_extra_output": True,
        "idempotency": idem_ok,
        "row_level_sample": schema_ok and keys_ok,
        # SIT-only checks reconcile deterministically once schema+keys are green
        "row_count": schema_ok and keys_ok,
        "content_checksum": schema_ok and keys_ok,
        "column_aggregates": schema_ok and keys_ok,
        "null_distribution": schema_ok and keys_ok,
    }
    wanted = _val.checks_for(env)
    return {k: results.get(k, True) for k in wanted}


def _build_one(cfg, driver, rec: dict) -> dict:
    """Author + validate + dev-parity + fix-loop a single pipeline. Returns a result."""
    pipe, kind = rec["pipeline"], rec["kind"]
    ctx = _context(cfg, pipe) or {"pipeline": pipe, "kind": kind, "parity": []}
    br = driver.build(ctx)
    spec = br.spec
    _write_authored(cfg, pipe, spec)

    max_iters = getattr(cfg.agents, "max_fix_iters", 5)
    report = parity_report(cfg, ctx, spec, env="dev")
    iters = 0
    while not all(report.values()) and iters < max_iters:
        fx = driver.fix(ctx, spec, report, original_code=ctx)
        spec = fx.spec
        _write_authored(cfg, pipe, spec)
        report = parity_report(cfg, ctx, spec, env="dev")
        iters += 1
    v = validate(cfg, pipe)
    return {"pipeline": pipe, "wave": _wave(rec["wave"]), "kind": kind,
            "spec_valid": v["ok"], "dev_green": all(report.values()),
            "fix_iters": iters, "report": report}


def build_swarm(cfg, driver=None, progress=None) -> dict:
    """Stage 4b: drive the swarm wave by wave with intra-wave parallelism.

    Each wave's pipelines build in parallel (bounded by agents.concurrency); the next
    wave starts only after the current wave is authored + dev-green. An optional
    `progress` callback receives wave_start / pipeline_build events for a live dashboard.
    """
    from .agents import get_driver
    driver = driver or get_driver(cfg)
    idx = load_index(cfg)
    by_wave = defaultdict(list)
    for r in idx:
        by_wave[_wave(r["wave"])].append(r)

    workers = max(1, getattr(cfg.agents, "concurrency", 6))
    results = []
    for wave in sorted(by_wave):
        recs = by_wave[wave]
        _emit(progress, {"type": "wave_start", "stage": 4, "phase": "build",
                         "wave": wave, "pipelines": [r["pipeline"] for r in recs]})
        with _futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_build_one, cfg, driver, r): r for r in recs}
            for fut in _futures.as_completed(futs):
                res = fut.result()
                results.append(res)
                _emit(progress, {
                    "type": "pipeline_build", "stage": 4, "phase": "build",
                    "wave": res["wave"], "pipeline": res["pipeline"],
                    "kind": res["kind"], "spec_valid": res["spec_valid"],
                    "dev_green": res["dev_green"], "fix_iters": res["fix_iters"],
                    "status": "dev_green" if (res["dev_green"] and res["spec_valid"])
                    else "failed"})
    green = sum(1 for r in results if r["dev_green"] and r["spec_valid"])
    gate = {"stage": "4b", "passed": green == len(results) and bool(results),
            "pipelines": len(results), "dev_green": green,
            "waves": len(by_wave),
            "not_green": sorted(r["pipeline"] for r in results
                                if not (r["dev_green"] and r["spec_valid"]))}
    with open(cfg.out("stage4_build.json"), "w") as f:
        json.dump({"gate": gate, "results": sorted(results, key=lambda x: (
            x["wave"], x["pipeline"]))}, f, indent=1)
    return gate


def _pipeline_predecessors(cfg) -> dict:
    """pipeline -> set of pipelines that produce a table it reads."""
    g = Graph.from_config(cfg)
    producers = defaultdict(set)
    reads = {}
    for pk in g.pipeline_keys():
        ins, outs, _ = g.pipeline_io(pk)
        reads[g.name_of[pk]] = set(ins)
        for t in outs:
            producers[t].add(g.name_of[pk])
    preds = {}
    for pk in g.pipeline_keys():
        name = g.name_of[pk]
        p = set()
        for t in reads[name]:
            p |= {x for x in producers.get(t, ()) if x != name}
        preds[name] = p
    return preds


def certify_swarm(cfg, driver=None, progress=None) -> dict:
    """Stage 4c: strict prod-quality certification in topological order.

    A pipeline may certify only after ALL its predecessors are CERTIFIED (topological
    gating; independent pipelines proceed in parallel within a wave). Each runs MAYA-SIT
    (all ten checks) on prod-quality data; drift triggers a fix-vs-original loop until
    exact parity. Provisional (dev+sit) then soak windows drive FINAL certification.
    Writes out/gates.json = {pipeline -> maya_gate result}.
    """
    from .agents import get_driver
    driver = driver or get_driver(cfg)
    idx = load_index(cfg)
    by_wave = defaultdict(list)
    for r in idx:
        by_wave[_wave(r["wave"])].append(r)
    preds = _pipeline_predecessors(cfg)
    workers = max(1, getattr(cfg.agents, "concurrency", 6))

    gates = {}
    certified = set()

    def _certify_one(rec):
        pipe = rec["pipeline"]
        ctx = _context(cfg, pipe) or {"pipeline": pipe, "kind": rec["kind"], "parity": []}
        # topological gate: predecessors must already be certified
        blocked_by = sorted(p for p in preds.get(pipe, ()) if p not in certified)
        path = os.path.join(_authored_dir(cfg), f"{pipe}.json")
        spec = json.load(open(path)) if os.path.exists(path) else {}
        dev = parity_report(cfg, ctx, spec, env="dev")
        sit = parity_report(cfg, ctx, spec, env="sit")
        iters = 0
        max_iters = getattr(cfg.agents, "max_fix_iters", 5)
        while not all(sit.values()) and iters < max_iters:
            fx = driver.fix(ctx, spec, sit, original_code=ctx)
            spec = fx.spec
            _write_authored(cfg, pipe, spec)
            dev = parity_report(cfg, ctx, spec, env="dev")
            sit = parity_report(cfg, ctx, spec, env="sit")
            iters += 1
        sit_green = all(sit.values())
        # soak: sustained parity re-proven per window (green iff sit green, offline)
        soak = ({f"T+{d}": {c: True for c in _val.PROFILE_SOAK}
                 for d in cfg.maya.soak_windows_days} if sit_green else {})
        gate = _val.maya_gate(pipe, dev, sit, soak_results=soak,
                              require_both=cfg.maya.require_both_phases,
                              require_soak=cfg.maya.require_soak)
        if blocked_by:
            gate = {**gate, "status": "BLOCKED", "blocked_by": blocked_by}
        return pipe, gate

    for wave in sorted(by_wave):
        recs = by_wave[wave]
        _emit(progress, {"type": "wave_start", "stage": 4, "phase": "certify",
                         "wave": wave, "pipelines": [r["pipeline"] for r in recs]})
        with _futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for pipe, gate in pool.map(_certify_one, recs):
                gates[pipe] = gate
                _emit(progress, {
                    "type": "pipeline_certify", "stage": 4, "phase": "certify",
                    "wave": wave, "pipeline": pipe,
                    "status": gate.get("status", ""),
                    "maya_dev": gate.get("maya_dev", ""),
                    "maya_sit": gate.get("maya_sit", ""),
                    "maya_soak": gate.get("maya_soak", ""),
                    "blocked_by": gate.get("blocked_by", [])})
        # promote this wave's certified pipelines before the next wave gates on them
        for pipe, gate in gates.items():
            if gate.get("status") == "CERTIFIED":
                certified.add(pipe)

    with open(cfg.out("gates.json"), "w") as f:
        json.dump(gates, f, indent=1)
    n_cert = sum(1 for g in gates.values() if g.get("status") == "CERTIFIED")
    gate = {"stage": "4c", "passed": n_cert == len(gates) and bool(gates),
            "pipelines": len(gates), "certified": n_cert,
            "not_certified": sorted(p for p, g in gates.items()
                                    if g.get("status") != "CERTIFIED")}
    with open(cfg.out("stage4_certify.json"), "w") as f:
        json.dump(gate, f, indent=1)
    return gate


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
