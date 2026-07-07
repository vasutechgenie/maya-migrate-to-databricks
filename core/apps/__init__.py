"""core.apps -- downstream custom-app migration (Lakebase + Databricks Apps).

Apps ride the same 12-stage lifecycle as pipelines. This package exposes one entrypoint
per lifecycle concern; stages.py calls them alongside the pipeline/BI work. Every
entrypoint is a no-op that PASSES when a project has no registered apps, so existing
DW-only projects are unaffected.

State is accumulated in ``out/apps.json`` (mirrored to Postgres by the webapp) and the
generated artifacts land under ``out/apps/<key>/``.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from . import appgen, deploy as deploy_mod, etl, model, parity
from .model import App, safe_ident


# --------------------------------------------------------------------------- #
# state + helpers
# --------------------------------------------------------------------------- #
def _state_path(cfg) -> str:
    return cfg.out("apps.json")


def _out_dir(cfg, key: str) -> str:
    d = cfg.out(os.path.join("apps", safe_ident(key)))
    os.makedirs(d, exist_ok=True)
    return d


def _catalog(cfg) -> str:
    return getattr(getattr(cfg, "maya", None), "sit_catalog", "") or "main"


def _instance(cfg) -> str:
    return f"maya_{safe_ident(cfg.project_name)}"


def load_state(cfg) -> Dict[str, Any]:
    try:
        return json.load(open(_state_path(cfg)))
    except Exception:
        return {"apps": []}


def save_state(cfg, state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_state_path(cfg)), exist_ok=True)
    with open(_state_path(cfg), "w") as f:
        json.dump(state, f, indent=2)


def _index(state: Dict[str, Any]) -> Dict[str, dict]:
    return {a.get("key"): a for a in state.get("apps", [])}


def _carry(target: list, source, key, field: str) -> None:
    """Copy a per-item parity grade from source rows into matching target rows."""
    if not source:
        return
    keyfn = key if callable(key) else (lambda x: x.get(key))
    by = {keyfn(s): s.get(field) for s in source}
    for t in target:
        if keyfn(t) in by and by[keyfn(t)]:
            t[field] = by[keyfn(t)]


def _base_record(cfg, app: App) -> Dict[str, Any]:
    """Static surface for an app (recomputed from the manifest each stage)."""
    catalog = _catalog(cfg)
    entities = [{
        "name": e.name, "source_table": e.source, "populated_by": e.populated_by,
        "lakebase_table": f"{app.schema}.{safe_ident(e.name)}",
        "columns": e.columns, "schema_parity": "",
    } for e in app.entities]
    endpoints = [{"method": ep.method, "path": ep.path, "entity": ep.entity,
                  "screen": ep.screen, "contract_parity": ""}
                 for ep in app.endpoints]
    screens = [{"key": s.key, "title": s.title, "screenshot": s.screenshot,
                "ui_parity": ""} for s in app.screens]
    return {
        "key": app.key, "name": app.name, "description": app.description,
        "owner_team": app.owner_team,
        "lakebase_instance": _instance(cfg), "lakebase_schema": app.schema,
        "app_name": f"maya-{app.schema.replace('_', '-')}",
        "status": "registered", "cert_status": "BLOCKED", "deployed": False,
        "entities": entities, "endpoints": endpoints, "screens": screens,
        "etl_bindings": [], "lakebase_objects": model.lakebase_objects(app, catalog),
        "builds": [],
        "certification": {"schema_parity": "", "api_parity": "", "ui_parity": "",
                          "sync_parity": "", "status": "BLOCKED", "blocked_by": []},
        "deployment": {"lakebase_instance": _instance(cfg), "app_url": "",
                       "bundle_path": "", "mode": "offline", "status": "planned"},
    }


def _sync_records(cfg, apps: List[App]) -> Dict[str, dict]:
    """Discover apps and merge their static surface into the persisted state."""
    state = load_state(cfg)
    existing = _index(state)
    merged: List[dict] = []
    for app in apps:
        rec = existing.get(app.key) or {}
        base = _base_record(cfg, app)
        # preserve accumulated dynamic fields
        for k in ("status", "cert_status", "deployed", "etl_bindings", "builds",
                  "certification", "deployment"):
            if rec.get(k):
                base[k] = rec[k]
        # preserve per-item parity grades written by certify()
        _carry(base["entities"], rec.get("entities"), "name", "schema_parity")
        _carry(base["endpoints"], rec.get("endpoints"),
               lambda x: f"{x.get('method')} {x.get('path')}", "contract_parity")
        _carry(base["screens"], rec.get("screens"), "key", "ui_parity")
        merged.append(base)
    state["apps"] = merged
    save_state(cfg, state)
    return _index(state)


def _gate(passed: bool, apps: List[App], **extra) -> Dict[str, Any]:
    return {"passed": passed, "n_apps": len(apps),
            "apps": [a.key for a in apps], **extra}


# --------------------------------------------------------------------------- #
# lifecycle entrypoints (called by core.stages)
# --------------------------------------------------------------------------- #
def readiness(cfg) -> Dict[str, Any]:
    """Stage 0: app identity/secret + Lakebase entitlement checklist."""
    apps = model.discover(cfg)
    if not apps:
        return _gate(True, apps, skipped=True)
    _sync_records(cfg, apps)
    checklist = []
    for a in apps:
        checklist.append({"app": a.key,
                          "lakebase_instance": _instance(cfg),
                          "needs": ["lakebase_capacity", "app_oauth", "uc_catalog"]})
    return _gate(True, apps, checklist=checklist)


def collect(cfg) -> Dict[str, Any]:
    """Stage 1: register apps, build the app subgraph surface + Lakebase schema."""
    apps = model.discover(cfg)
    if not apps:
        return _gate(True, apps, skipped=True)
    recs = _sync_records(cfg, apps)
    for a in apps:
        out = _out_dir(cfg, a.key)
        lb_dir = os.path.join(out, "lakebase")
        os.makedirs(lb_dir, exist_ok=True)
        with open(os.path.join(lb_dir, f"{a.schema}.sql"), "w") as f:
            f.write(model.lakebase_ddl(a))
        recs[a.key]["status"] = "collected"
    state = {"apps": list(recs.values())}
    save_state(cfg, state)
    ok = all(len(a.entities) > 0 for a in apps)
    return _gate(ok, apps,
                 entities=sum(len(a.entities) for a in apps),
                 endpoints=sum(len(a.endpoints) for a in apps),
                 screens=sum(len(a.screens) for a in apps))


def specs(cfg) -> Dict[str, Any]:
    """Stage 3: one migration spec per app."""
    apps = model.discover(cfg)
    if not apps:
        return _gate(True, apps, skipped=True)
    recs = _sync_records(cfg, apps)
    for a in apps:
        out = _out_dir(cfg, a.key)
        with open(os.path.join(out, "spec.md"), "w") as f:
            f.write(_spec_md(cfg, a))
        recs[a.key]["status"] = "specced"
    save_state(cfg, {"apps": list(recs.values())})
    return _gate(True, apps)


def replicate(cfg, phase: str = "dev") -> Dict[str, Any]:
    """Stage 2 (dev) / 6 (prod): provision Lakebase + author DW->Lakebase sync."""
    apps = model.discover(cfg)
    if not apps:
        return _gate(True, apps, skipped=True)
    recs = _sync_records(cfg, apps)
    catalog = _catalog(cfg)
    for a in apps:
        out = _out_dir(cfg, a.key)
        bindings = etl.retarget(cfg, a, catalog, out)
        recs[a.key]["etl_bindings"] = bindings
        recs[a.key]["status"] = f"replicated-{phase}"
    save_state(cfg, {"apps": list(recs.values())})
    return _gate(True, apps, phase=phase)


def build(cfg, phase: str = "dev") -> Dict[str, Any]:
    """Stage 4 (dev) / 7 (prod): generate the Databricks App backend/API/UI."""
    apps = model.discover(cfg)
    if not apps:
        return _gate(True, apps, skipped=True)
    recs = _sync_records(cfg, apps)
    ok = True
    for a in apps:
        out = _out_dir(cfg, a.key)
        gen = appgen.generate(a, out)
        if not recs[a.key].get("etl_bindings"):
            recs[a.key]["etl_bindings"] = etl.retarget(cfg, a, _catalog(cfg), out)
        recs[a.key]["builds"] = [
            {"phase": phase, "component": "lakebase", "engine": "E8",
             "built": True, "report": {"tables": len(a.entities)}},
            {"phase": phase, "component": "api", "engine": "E9",
             "built": bool(gen["api"]["built"]), "report": gen["api"]},
            {"phase": phase, "component": "ui", "engine": "E10",
             "built": bool(gen["ui"]["built"]), "report": gen["ui"]},
            {"phase": phase, "component": "etl", "engine": "E8",
             "built": bool(recs[a.key]["etl_bindings"]), "report": {}},
        ]
        recs[a.key]["status"] = f"built-{phase}"
        ok = ok and gen["api"]["built"] and gen["ui"]["built"]
    save_state(cfg, {"apps": list(recs.values())})
    return _gate(ok, apps, phase=phase)


def certify(cfg, phase: str = "dev") -> Dict[str, Any]:
    """Stage 4 (dev) / 7 (prod): parity-certify each app.

    dev  proves schema+api+ui parity on the sample (-> PROVISIONAL).
    prod adds DW->Lakebase sync parity on full data (-> CERTIFIED).
    """
    apps = model.discover(cfg)
    if not apps:
        return _gate(True, apps, skipped=True)
    recs = _sync_records(cfg, apps)
    require_sync = (phase == "prod")
    all_ok = True
    statuses = {}
    for a in apps:
        rec = recs[a.key]
        build_rec = {b["component"]: {"built": b["built"]} for b in rec.get("builds", [])}
        sd = model.schema_diff(a)
        sp = parity.schema_parity(a, sd)
        ap = parity.api_parity(a, build_rec)
        up = parity.ui_parity(a, build_rec)
        yp = parity.sync_parity(a, rec.get("etl_bindings", []))
        gate = parity.app_gate(sp["grade"], ap["grade"], up["grade"], yp["grade"],
                               require_sync=require_sync)
        rec["certification"] = gate
        rec["cert_status"] = gate["status"]
        for e in rec["entities"]:
            e["schema_parity"] = sp["per_entity"].get(e["name"], "")
        for ep in rec["endpoints"]:
            ep["contract_parity"] = ap["per_endpoint"].get(
                f"{ep['method']} {ep['path']}", "")
        for s in rec["screens"]:
            s["ui_parity"] = up["per_screen"].get(s["key"], "")
        rec["status"] = f"certified-{phase}" if gate["status"] != "BLOCKED" \
            else f"blocked-{phase}"
        statuses[a.key] = gate["status"]
        app_ok = (gate["status"] == "CERTIFIED") if require_sync \
            else (gate["status"] != "BLOCKED")
        all_ok = all_ok and app_ok
    save_state(cfg, {"apps": list(recs.values())})
    return _gate(all_ok, apps, phase=phase, statuses=statuses)


def docs(cfg) -> Dict[str, Any]:
    """Stage 9: app migration docs."""
    apps = model.discover(cfg)
    if not apps:
        return _gate(True, apps, skipped=True)
    recs = _sync_records(cfg, apps)
    docs_dir = cfg.out(os.path.join("apps", "_docs"))
    os.makedirs(docs_dir, exist_ok=True)
    for a in apps:
        with open(os.path.join(docs_dir, f"{a.key}.md"), "w") as f:
            f.write(_spec_md(cfg, a))
    save_state(cfg, {"apps": list(recs.values())})
    return _gate(True, apps)


def identity(cfg) -> Dict[str, Any]:
    """Stage 10: UC grants for Lakebase + the Databricks App."""
    apps = model.discover(cfg)
    if not apps:
        return _gate(True, apps, skipped=True)
    recs = _sync_records(cfg, apps)
    grants = []
    for a in apps:
        grants.append({"app": a.key,
                       "grant": f"GRANT USAGE ON SCHEMA {a.schema} TO app_{a.schema}"})
    return _gate(True, apps, grants=grants)


def deploy(cfg, host: str = "", token: str = "", emit=None) -> Dict[str, Any]:
    """Stage 11: emit the deploy bundle (+ deploy when creds present)."""
    apps = model.discover(cfg)
    if not apps:
        return _gate(True, apps, skipped=True)
    recs = _sync_records(cfg, apps)
    catalog = _catalog(cfg)
    for a in apps:
        out = _out_dir(cfg, a.key)
        rec = deploy_mod.deploy(a, out, _instance(cfg), catalog,
                                host=host, token=token, emit=emit)
        recs[a.key]["deployment"] = rec
        recs[a.key]["deployed"] = rec.get("status") in ("deployed", "bundled")
        if recs[a.key]["deployed"]:
            recs[a.key]["status"] = "deployed"
    save_state(cfg, {"apps": list(recs.values())})
    return _gate(True, apps, deployments={k: v["deployment"]["status"]
                                          for k, v in recs.items()})


def _spec_md(cfg, app: App) -> str:
    lines = [f"# App migration spec: {app.name} (`{app.key}`)", "",
             app.description or "", "",
             f"- Owner team: {app.owner_team or 'n/a'}",
             f"- Lakebase instance: `{_instance(cfg)}`",
             f"- Lakebase schema: `{app.schema}`",
             f"- Databricks App: `maya-{app.schema.replace('_', '-')}`", "",
             "## Entities (-> Lakebase tables)"]
    for e in app.entities:
        src = f" <- `{e.source}`" if e.source else ""
        lines.append(f"- `{app.schema}.{safe_ident(e.name)}`{src} "
                     f"({len(e.columns)} cols)")
    lines += ["", "## Endpoints (-> Databricks App API)"]
    for ep in app.endpoints:
        lines.append(f"- `{ep.method} {ep.path}` -> entity `{ep.entity}` "
                     f"screen `{ep.screen}`")
    lines += ["", "## Screens (-> rebuilt UI, golden-screenshot parity)"]
    for s in app.screens:
        lines.append(f"- `{s.key}` — {s.title} ({s.screenshot or 'no shot'})")
    return "\n".join(lines) + "\n"
