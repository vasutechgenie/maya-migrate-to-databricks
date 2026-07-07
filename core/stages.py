"""
stages.py -- the twelve-stage MAYA full-lifecycle orchestrator.

Wraps the existing deterministic primitives (graph, order, verify, context, maya, bi,
report) and the stage capabilities into hard-gated stages. Each stage runs its steps,
evaluates its gate, and the orchestrator refuses to advance past a failed gate. State is
written to out/stage_state.json.

  0  readiness             collect + classify identity/access/secrets/classification (non-data estate)
  1  collect + score        graph -> order -> context -> collect assets -> 100% score gate
  2  replicate (dev)        test-catalog replication + RI fill on a <=10k sample
  3  specs                  one branded spec PDF per pipeline
  4  build + certify (dev)  conformance -> swarm build; dev-certify on the sample (runs clean)
  5  bi convert (dev)       convert BI queries; dev-certify they run clean on the sample gold
  6  full load (prod)       backfill the full/historical source data for every pipeline
  7  build + certify (prod) strict topological certification to 100% parity on real data
  8  bi parity + publish    parity vs source on full gold -> republish -> Genie/Lakeview
  9  docs + publish          generate docs -> commit back (local for the offline demo)
  10 identity               UC groups/roles/grants + RLS/CLS masks + secrets + governance (access parity)
  11 enablement             training + runbooks + cutover/rollback/decommission + day-2 ops (go/no-go)

Dev and prod are two phases of the SAME code (pipelines AND BI). Stage 4 builds + dev-
certifies the converted SQL on the sample and stage 5 dev-certifies the converted BI
queries on that sample gold; stage 7 runs the identical pipeline code against the full/
historical data (stage 6) and certifies real parity, then stage 8 parity-certifies +
publishes the identical BI queries. The prod fix-loop persists pipeline repairs back to
the single source of truth so the two phases never diverge. Nothing here overwrites the
existing verbs; they remain usable directly as primitives.
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
from . import readiness as readiness_mod
from . import identity as identity_mod
from . import enablement as enablement_mod
from . import apps as apps_mod


def _apps(cfg, fn_name: str, *args) -> dict:
    """Run a downstream-app lifecycle step; never crash a DW migration on app errors.

    Returns the app gate (passed True + skipped when a project has no apps)."""
    try:
        return getattr(apps_mod, fn_name)(cfg, *args)
    except Exception as exc:  # pragma: no cover - defensive
        return {"passed": False, "error": f"apps.{fn_name}: {exc}", "n_apps": -1}


# --------------------------------------------------------------------------- #
# execution scope: run the whole lifecycle ("all") or only a layer on top of an
# already-certified pipeline estate. "bi" re-runs just the dashboard/BI stages;
# "apps" re-runs just the downstream-app lifecycle (Lakebase + Databricks Apps)
# WITHOUT touching the pipeline swarm; "bi_apps" does both. This lets a user add
# BI or App migrations after the data + ETL migration is done, without repeating
# any pipeline creation.
# --------------------------------------------------------------------------- #
SCOPE_ALL = "all"
BI_STAGES = [5, 8]
APP_STAGES = [0, 1, 2, 3, 4, 6, 7, 9, 10, 11]


def _do_bi(scope: str) -> bool:
    return scope in (SCOPE_ALL, "bi", "bi_apps")


def _do_apps(scope: str) -> bool:
    return scope in (SCOPE_ALL, "apps", "bi_apps")


def _do_pipeline(scope: str) -> bool:
    return scope == SCOPE_ALL


def _skip(n: int, scope: str) -> dict:
    """A stage that has no work under the current scope: pass without running anything."""
    return {"stage": n, "passed": True, "skipped": True, "scope": scope}


def scope_stages(scope: str) -> list:
    """The ordered stage numbers a given scope executes."""
    if scope == "bi":
        return list(BI_STAGES)
    if scope == "apps":
        return list(APP_STAGES)
    if scope == "bi_apps":
        return sorted(set(BI_STAGES) | set(APP_STAGES))
    return sorted(STAGES)


def _apps_only_gate(cfg, n: int, scope: str, *apps_args) -> dict:
    """Run only the downstream-app slice of a stage (used for apps / bi_apps scope)."""
    if len(apps_args) == 1:
        app = _apps(cfg, apps_args[0])
        return {"stage": n, "passed": bool(app.get("passed")), "scope": scope,
                "apps": app}
    # (fn_name, *args) form
    app = _apps(cfg, apps_args[0], *apps_args[1:])
    return {"stage": n, "passed": bool(app.get("passed")), "scope": scope,
            "apps": app}


def _stage0(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    if not _do_pipeline(scope):
        return _apps_only_gate(cfg, 0, scope, "readiness") if _do_apps(scope) \
            else _skip(0, scope)
    gate = readiness_mod.run(cfg)
    app = _apps(cfg, "readiness")
    gate["apps"] = app
    gate["passed"] = bool(gate.get("passed")) and bool(app.get("passed"))
    return gate


def _stage1(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    if not _do_pipeline(scope):
        # apps re-register (subgraph + Lakebase DDL) without rebuilding the DW graph
        return _apps_only_gate(cfg, 1, scope, "collect") if _do_apps(scope) \
            else _skip(1, scope)
    adapter = cfg.load_adapter()
    adapter.build_graph()
    order_mod.run(cfg)
    try:
        ddl = adapter.ddl_index()
    except Exception:
        ddl = {}
    contract_mod.generate_all(cfg, ddl_index=ddl)
    gate = score_mod.run(cfg)
    app = _apps(cfg, "collect")
    gate["apps"] = app
    gate["passed"] = bool(gate.get("passed")) and bool(app.get("passed"))
    return gate


def _stage2(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    if not _do_pipeline(scope):
        return _apps_only_gate(cfg, 2, scope, "replicate", "dev") if _do_apps(scope) \
            else _skip(2, scope)
    gate = replicate_mod.run(cfg)
    app = _apps(cfg, "replicate", "dev")
    gate["apps"] = app
    gate["passed"] = bool(gate.get("passed")) and bool(app.get("passed"))
    return gate


def _stage3(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    if not _do_pipeline(scope):
        return _apps_only_gate(cfg, 3, scope, "specs") if _do_apps(scope) \
            else _skip(3, scope)
    gate = spec_mod.run(cfg)
    app = _apps(cfg, "specs")
    gate["apps"] = app
    gate["passed"] = bool(gate.get("passed")) and bool(app.get("passed"))
    return gate


def _stage4(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    """Build + certify (dev): conformance, then the swarm builds every pipeline and
    dev-certifies it on the sample (schema/keys/RI/idempotency). No prod parity yet --
    that is stage 6, which runs this same authored code against the full data.

    Under a non-`all` scope the pipeline swarm is skipped entirely; only the downstream-app
    build/dev-certify runs (apps / bi_apps), so pipelines are never re-created."""
    if not _do_pipeline(scope):
        if not _do_apps(scope):
            return _skip(4, scope)
        app_build = _apps(cfg, "build", "dev")
        app_cert = _apps(cfg, "certify", "dev")
        passed = bool(app_build.get("passed")) and bool(app_cert.get("passed"))
        return {"stage": 4, "passed": passed, "phase": "dev", "scope": scope,
                "apps": {"build": app_build, "certify": app_cert}}
    conf = conformance_mod.run(cfg)
    if not conf.get("passed"):
        return {"stage": 4, "passed": False, "phase": "dev", "conformance": conf}
    build = orch.build_swarm(cfg, progress=progress)
    app_build = _apps(cfg, "build", "dev")
    app_cert = _apps(cfg, "certify", "dev")
    passed = (bool(build.get("passed")) and bool(app_build.get("passed"))
              and bool(app_cert.get("passed")))
    return {"stage": 4, "passed": passed, "phase": "dev",
            "conformance": conf, "build": build,
            "apps": {"build": app_build, "certify": app_cert}}


def _stage5(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    """BI convert + dev-certify: convert the BI queries and prove they run clean on the
    dev/sample gold produced by stage 4. No source parity or republish yet -- that is the
    prod BI stage (8), which parity-checks + publishes the SAME converted queries."""
    if not _do_bi(scope):
        return _skip(5, scope)
    return bi_mod.run(cfg, phase="dev")


def _stage6(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    """Full load + historical (prod): backfill the full/historical source estate. Offline
    this reuses the deterministic replication (same manifest) tagged as the prod phase; a
    live project loads the real full source into the test schema before prod certification."""
    if not _do_pipeline(scope):
        return _apps_only_gate(cfg, 6, scope, "replicate", "prod") if _do_apps(scope) \
            else _skip(6, scope)
    gate = replicate_mod.run(cfg)
    app = _apps(cfg, "replicate", "prod")
    return {"stage": 6, "passed": bool(gate.get("passed")) and bool(app.get("passed")),
            "phase": "prod",
            "data_mode": "full", "replicate": gate,
            "tables": gate.get("tables"), "views": gate.get("views"),
            "replicated": gate.get("replicated"), "apps": app}


def _stage7(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    """Build + certify (prod): strict topological certification of the SAME authored code
    (from stage 4) against the full/historical data, to 100% parity. Drift triggers the
    fix-vs-original loop; the repaired code is the single source of truth for both phases.

    Under a non-`all` scope the certify swarm is skipped; only the downstream-app
    build/prod-certify runs (apps / bi_apps) -- pipelines are never re-certified."""
    if not _do_pipeline(scope):
        if not _do_apps(scope):
            return _skip(7, scope)
        app_build = _apps(cfg, "build", "prod")
        app_cert = _apps(cfg, "certify", "prod")
        passed = bool(app_build.get("passed")) and bool(app_cert.get("passed"))
        return {"stage": 7, "passed": passed, "phase": "prod", "scope": scope,
                "apps": {"build": app_build, "certify": app_cert}}
    cert = orch.certify_swarm(cfg, progress=progress)
    gates = json.load(open(cfg.out("gates.json"))) if os.path.exists(
        cfg.out("gates.json")) else {}
    waves = {r["pipeline"]: orch._wave(r["wave"]) for r in orch.load_index(cfg)}
    system = val.system_certification(gates, waves=waves)
    app_build = _apps(cfg, "build", "prod")
    app_cert = _apps(cfg, "certify", "prod")
    passed = (bool(cert.get("passed")) and bool(app_build.get("passed"))
              and bool(app_cert.get("passed")))
    return {"stage": 7, "passed": passed, "phase": "prod",
            "certify": cert, "system": system,
            "apps": {"build": app_build, "certify": app_cert}}


def _stage8(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    """BI parity + publish (prod): parity-check the converted BI queries against the full
    gold vs the real source, then republish + build Genie/Lakeview."""
    if not _do_bi(scope):
        return _skip(8, scope)
    return bi_mod.run(cfg, phase="prod")


def _stage9(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    if not _do_pipeline(scope):
        return _apps_only_gate(cfg, 9, scope, "docs") if _do_apps(scope) \
            else _skip(9, scope)
    d = docs_mod.run(cfg)
    p = publish_mod.run(cfg)
    app = _apps(cfg, "docs")
    return {"stage": 9,
            "passed": bool(d.get("passed") and p.get("passed") and app.get("passed")),
            "docs": d, "publish": p, "apps": app}


def _stage10(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    if not _do_pipeline(scope):
        return _apps_only_gate(cfg, 10, scope, "identity") if _do_apps(scope) \
            else _skip(10, scope)
    gate = identity_mod.run(cfg)
    app = _apps(cfg, "identity")
    gate["apps"] = app
    gate["passed"] = bool(gate.get("passed")) and bool(app.get("passed"))
    return gate


def _stage11(cfg, progress=None, scope=SCOPE_ALL) -> dict:
    if not _do_pipeline(scope):
        return _apps_only_gate(cfg, 11, scope, "deploy") if _do_apps(scope) \
            else _skip(11, scope)
    gate = enablement_mod.run(cfg)
    app = _apps(cfg, "deploy")
    gate["apps"] = app
    gate["passed"] = bool(gate.get("passed")) and bool(app.get("passed"))
    return gate


STAGES: Dict[int, tuple] = {
    0: ("readiness", _stage0),
    1: ("collect+score", _stage1),
    2: ("replicate-dev", _stage2),
    3: ("specs", _stage3),
    4: ("build+certify-dev", _stage4),
    5: ("bi-convert-dev", _stage5),
    6: ("full-load+historical-prod", _stage6),
    7: ("build+certify-prod", _stage7),
    8: ("bi-parity+publish-prod", _stage8),
    9: ("docs+publish", _stage9),
    10: ("identity+security+governance", _stage10),
    11: ("enablement+go-live", _stage11),
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
    return {"stages": {}, "last_passed": -1}


def _save_state(cfg, state: dict):
    os.makedirs(cfg.p(cfg.out_dir), exist_ok=True)
    with open(_state_path(cfg), "w") as f:
        json.dump(state, f, indent=1)


def run_stage(cfg, n: int, enforce_prev: bool = True, progress=None,
              scope: str = SCOPE_ALL) -> dict:
    """Run one stage. If enforce_prev, refuse unless stages before n have passed.

    An optional `progress` callback receives per-wave/per-pipeline events (Stage 4).

    `scope` selects how much of the stage runs: "all" (default) runs the full stage;
    "bi" / "apps" / "bi_apps" run only that layer and skip the pipeline swarm. For a
    scoped run the result is MERGED onto any prior gate for the stage so the existing
    pipeline certification record is preserved (only the BI/app slice is refreshed).
    """
    if n not in STAGES:
        lo, hi = min(STAGES), max(STAGES)
        raise ValueError(f"unknown stage {n} (expected {lo}..{hi})")
    state = _load_state(cfg)
    if enforce_prev and n > min(STAGES) and state.get("last_passed", -1) < n - 1:
        return {"stage": n, "passed": False,
                "error": f"gate not satisfied: stage {n-1} has not passed "
                         f"(last_passed={state.get('last_passed', -1)})"}
    name, fn = STAGES[n]
    gate = fn(cfg, progress=progress, scope=scope)
    gate.setdefault("name", name)
    prev = state["stages"].get(str(n))
    if scope != SCOPE_ALL and isinstance(prev, dict):
        if gate.get("skipped"):
            # no work this scope: keep the prior (pipeline) gate untouched
            stored = prev
        else:
            # overlay the refreshed BI/app slice on the preserved pipeline gate
            stored = {**prev, **gate}
            stored["passed"] = bool(prev.get("passed", True)) and \
                bool(gate.get("passed", True))
        gate = stored
    state["stages"][str(n)] = gate
    if gate.get("passed"):
        state["last_passed"] = max(state.get("last_passed", -1), n)
    state["complete"] = state.get("last_passed", -1) >= max(STAGES)
    _save_state(cfg, state)
    return gate


def run_all(cfg, progress=None) -> dict:
    """Run every stage in order (0..11), stopping at the first failed gate."""
    state = {"stages": {}, "last_passed": -1}
    _save_state(cfg, state)
    for n in sorted(STAGES):
        gate = run_stage(cfg, n, enforce_prev=False, progress=progress)
        state = _load_state(cfg)
        if not gate.get("passed"):
            state["stopped_at"] = n
            _save_state(cfg, state)
            break
    return _load_state(cfg)


def run_scope(cfg, scope: str, progress=None) -> dict:
    """Run only a layer (bi / apps / bi_apps) on top of an already-migrated estate.

    Preserves the existing out/stage_state.json (pipeline gates + last_passed) and never
    calls the pipeline swarm, so no pipeline is re-created. Stops at the first real
    (non-skipped) failure. Returns the reloaded state.
    """
    if scope == SCOPE_ALL:
        return run_all(cfg, progress=progress)
    for n in scope_stages(scope):
        gate = run_stage(cfg, n, enforce_prev=False, progress=progress, scope=scope)
        if not gate.get("passed") and not gate.get("skipped"):
            state = _load_state(cfg)
            state["stopped_at"] = n
            _save_state(cfg, state)
            break
    return _load_state(cfg)


def pipelines_certified(cfg) -> bool:
    """True once the data + ETL (pipeline) migration has produced CERTIFIED pipelines.

    Read from out/gates.json (written by stage 7 / prod certify). Used to gate the
    BI-only / Apps-only add-on runs so we never schedule a layer on an estate whose
    pipelines have not been built + certified yet.
    """
    path = cfg.out("gates.json")
    if not os.path.exists(path):
        return False
    try:
        gates = json.load(open(path))
    except Exception:
        return False
    return any((g or {}).get("status") == "CERTIFIED" for g in gates.values())
