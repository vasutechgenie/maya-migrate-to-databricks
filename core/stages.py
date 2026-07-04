"""
stages.py -- the six-stage MAYA orchestrator.

Wraps the existing deterministic primitives (graph, order, verify, context, maya, bi,
report) and the new stage capabilities into six hard-gated stages. Each stage runs its
steps, evaluates its gate, and the orchestrator refuses to advance past a failed gate.
State is written to out/stage_state.json.

  1  collect + score      graph -> order -> context -> collect assets -> 100% score gate
  2  replicate            whole-estate test-catalog replication + RI fill
  3  specs                one branded spec PDF per pipeline
  4  build + certify      conformance -> swarm build (dev) -> strict topo certification
  5  bi                   extract -> convert -> parity -> republish -> Genie/Lakeview
  6  docs + publish        generate docs -> commit back (local for the offline demo)

Nothing here overwrites the existing verbs; they remain usable directly as primitives.
"""
from __future__ import annotations

import json
import os
from typing import Callable, Dict

from . import order as order_mod
from . import contract as contract_mod
from . import score as score_mod
from . import replicate as replicate_mod
from . import pipeline_spec as spec_mod
from . import conformance as conformance_mod
from . import orchestration as orch
from . import bi as bi_mod
from . import docs as docs_mod
from . import publish as publish_mod
from . import validation as val


def _stage1(cfg) -> dict:
    adapter = cfg.load_adapter()
    adapter.build_graph()
    order_mod.run(cfg)
    try:
        ddl = adapter.ddl_index()
    except Exception:
        ddl = {}
    contract_mod.generate_all(cfg, ddl_index=ddl)
    return score_mod.run(cfg)


def _stage2(cfg) -> dict:
    return replicate_mod.run(cfg)


def _stage3(cfg) -> dict:
    return spec_mod.run(cfg)


def _stage4(cfg) -> dict:
    conf = conformance_mod.run(cfg)
    if not conf.get("passed"):
        return {"stage": 4, "passed": False, "conformance": conf}
    build = orch.build_swarm(cfg)
    if not build.get("passed"):
        return {"stage": 4, "passed": False, "conformance": conf, "build": build}
    cert = orch.certify_swarm(cfg)
    gates = json.load(open(cfg.out("gates.json"))) if os.path.exists(
        cfg.out("gates.json")) else {}
    waves = {r["pipeline"]: orch._wave(r["wave"]) for r in orch.load_index(cfg)}
    system = val.system_certification(gates, waves=waves)
    return {"stage": 4, "passed": bool(cert.get("passed")),
            "conformance": conf, "build": build, "certify": cert,
            "system": system}


def _stage5(cfg) -> dict:
    return bi_mod.run(cfg)


def _stage6(cfg) -> dict:
    d = docs_mod.run(cfg)
    p = publish_mod.run(cfg)
    return {"stage": 6, "passed": bool(d.get("passed") and p.get("passed")),
            "docs": d, "publish": p}


STAGES: Dict[int, tuple] = {
    1: ("collect+score", _stage1),
    2: ("replicate", _stage2),
    3: ("specs", _stage3),
    4: ("conformance+build+certify", _stage4),
    5: ("bi", _stage5),
    6: ("docs+publish", _stage6),
}


def _state_path(cfg) -> str:
    return cfg.out("stage_state.json")


def _load_state(cfg) -> dict:
    p = _state_path(cfg)
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except Exception:
            pass
    return {"stages": {}, "last_passed": 0}


def _save_state(cfg, state: dict):
    os.makedirs(cfg.p(cfg.out_dir), exist_ok=True)
    with open(_state_path(cfg), "w") as f:
        json.dump(state, f, indent=1)


def run_stage(cfg, n: int, enforce_prev: bool = True) -> dict:
    """Run one stage. If enforce_prev, refuse unless stages 1..n-1 have passed."""
    if n not in STAGES:
        raise ValueError(f"unknown stage {n} (expected 1..6)")
    state = _load_state(cfg)
    if enforce_prev and n > 1 and state.get("last_passed", 0) < n - 1:
        return {"stage": n, "passed": False,
                "error": f"gate not satisfied: stage {n-1} has not passed "
                         f"(last_passed={state.get('last_passed', 0)})"}
    name, fn = STAGES[n]
    gate = fn(cfg)
    gate.setdefault("name", name)
    state["stages"][str(n)] = gate
    if gate.get("passed"):
        state["last_passed"] = max(state.get("last_passed", 0), n)
    state["complete"] = state.get("last_passed", 0) >= max(STAGES)
    _save_state(cfg, state)
    return gate


def run_all(cfg) -> dict:
    """Run stages 1..6 in order, stopping at the first failed gate."""
    state = {"stages": {}, "last_passed": 0}
    _save_state(cfg, state)
    for n in sorted(STAGES):
        gate = run_stage(cfg, n, enforce_prev=False)
        state = _load_state(cfg)
        if not gate.get("passed"):
            state["stopped_at"] = n
            _save_state(cfg, state)
            break
    return _load_state(cfg)
