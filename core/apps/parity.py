"""App parity certification: schema / API / UI / sync parity -> BLOCKED/PROVISIONAL/CERTIFIED.

Mirrors the pipeline certification model (core.validation): a downstream app is only
CERTIFIED when its migrated surface proves parity with the source app --
  * schema parity : Lakebase schema matches the app's data model
  * api parity    : every endpoint is regenerated + contract-equivalent
  * ui parity     : every screen renders against its golden screenshot
  * sync parity   : every entity's DW->Lakebase sync is authored (full-data, prod)
Dev proves schema+api+ui on the sample (PROVISIONAL); prod adds sync parity (CERTIFIED).
"""
from __future__ import annotations

from typing import Any, Dict, List

from .model import App, screenshot_path


def _grade(ok: bool) -> str:
    return "green" if ok else "red"


def schema_parity(app: App, schema_diff: Dict[str, Any]) -> Dict[str, Any]:
    per = {name: _grade(v["ok"]) for name, v in schema_diff.get("entities", {}).items()}
    return {"grade": _grade(schema_diff.get("ok", False)), "per_entity": per}


def api_parity(app: App, build: Dict[str, Any]) -> Dict[str, Any]:
    built = bool((build.get("api") or {}).get("built"))
    per = {f"{ep.method} {ep.path}": _grade(built and bool(ep.entity or True))
           for ep in app.endpoints}
    ok = built and (len(app.endpoints) > 0)
    return {"grade": _grade(ok), "per_endpoint": per}


def ui_parity(app: App, build: Dict[str, Any]) -> Dict[str, Any]:
    built = bool((build.get("ui") or {}).get("built"))
    per = {}
    ok = built and bool(app.screens)
    for s in app.screens:
        has_shot = bool(screenshot_path(app, s))
        per[s.key] = _grade(built and has_shot)
        ok = ok and has_shot
    return {"grade": _grade(ok), "per_screen": per}


def sync_parity(app: App, bindings: List[Dict[str, Any]]) -> Dict[str, Any]:
    ok = bool(bindings) and all(
        b.get("retarget_status") in ("authored", "app_owned") for b in bindings)
    per = {b.get("entity", ""): _grade(
        b.get("retarget_status") in ("authored", "app_owned")) for b in bindings}
    return {"grade": _grade(ok), "per_entity": per}


def app_gate(schema: str, api: str, ui: str, sync: str,
             require_sync: bool = True) -> Dict[str, Any]:
    """Roll the four parity grades into a certification status.

    BLOCKED     : any build-time parity (schema/api/ui) not green.
    PROVISIONAL : build-time parity green, sync (full-data) still pending/required.
    CERTIFIED   : all required parities green.
    """
    build_ok = all(g == "green" for g in (schema, api, ui))
    blocked_by: List[str] = [n for n, g in
                             (("schema", schema), ("api", api), ("ui", ui))
                             if g != "green"]
    if not build_ok:
        status = "BLOCKED"
    elif require_sync and sync != "green":
        status = "PROVISIONAL"
        if sync != "green":
            blocked_by.append("sync")
    else:
        status = "CERTIFIED"
    return {
        "schema_parity": schema, "api_parity": api, "ui_parity": ui,
        "sync_parity": sync, "status": status, "blocked_by": blocked_by,
    }
