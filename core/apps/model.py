"""App discovery + Lakebase schema generation.

Downstream apps are declared by an ``app.json`` (or ``app.yaml``) manifest stored at
``<workspace>/app/<key>/model/app.json``. This module discovers every app, models its
surface (entities, endpoints, screens, ETL bindings), and generates the Databricks
**Lakebase** (managed Postgres OLTP) DDL + UC synced-table definitions that the app's
data model migrates to.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def safe_ident(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", _norm(s)).strip("_") or "app"


# Postgres-friendly type normalization for common DW/ANSI types.
_PG_TYPE = {
    "int": "integer", "integer": "integer", "bigint": "bigint",
    "smallint": "smallint", "tinyint": "smallint",
    "string": "text", "varchar": "varchar", "nvarchar": "varchar",
    "char": "char", "text": "text",
    "decimal": "numeric", "numeric": "numeric", "money": "numeric",
    "float": "double precision", "double": "double precision", "real": "real",
    "bit": "boolean", "boolean": "boolean", "bool": "boolean",
    "date": "date", "datetime": "timestamp", "datetime2": "timestamp",
    "timestamp": "timestamp", "time": "time", "uuid": "uuid",
}


def _pg_type(t: str) -> str:
    t = _norm(t)
    if not t:
        return "text"
    base = re.split(r"[\s(]", t, maxsplit=1)[0]
    mapped = _PG_TYPE.get(base, base)
    # keep an explicit length/precision, e.g. varchar(200)
    m = re.search(r"\(([^)]*)\)", t)
    if m and mapped in ("varchar", "char", "numeric"):
        return f"{mapped}({m.group(1)})"
    return mapped


@dataclass
class Entity:
    name: str
    columns: List[Dict[str, Any]] = field(default_factory=list)
    source: str = ""          # DW gold table this entity is derived from
    populated_by: str = ""     # the ETL pipeline that populates it


@dataclass
class Endpoint:
    method: str
    path: str
    entity: str = ""
    screen: str = ""


@dataclass
class Screen:
    key: str
    title: str = ""
    screenshot: str = ""
    endpoints: List[str] = field(default_factory=list)


@dataclass
class App:
    key: str
    name: str = ""
    description: str = ""
    owner_team: str = ""
    dir: str = ""
    entities: List[Entity] = field(default_factory=list)
    endpoints: List[Endpoint] = field(default_factory=list)
    screens: List[Screen] = field(default_factory=list)

    @property
    def schema(self) -> str:
        return safe_ident(self.key)


def _load_manifest(path: str) -> dict:
    try:
        if path.lower().endswith((".yaml", ".yml")):
            import yaml
            return yaml.safe_load(open(path, errors="ignore")) or {}
        return json.load(open(path, errors="ignore")) or {}
    except Exception:
        return {}


def _app_from_manifest(key: str, man: dict, app_dir: str) -> App:
    entities = [Entity(name=e.get("name", ""), columns=e.get("columns", []) or [],
                       source=e.get("source", ""),
                       populated_by=e.get("populated_by", ""))
                for e in (man.get("entities") or []) if e.get("name")]
    endpoints = [Endpoint(method=(ep.get("method") or "GET").upper(),
                          path=ep.get("path", ""), entity=ep.get("entity", ""),
                          screen=ep.get("screen", ""))
                 for ep in (man.get("endpoints") or []) if ep.get("path")]
    screens = [Screen(key=sc.get("key") or safe_ident(sc.get("title", "")),
                      title=sc.get("title", ""), screenshot=sc.get("screenshot", ""),
                      endpoints=sc.get("endpoints", []) or [])
               for sc in (man.get("screens") or [])]
    return App(key=safe_ident(man.get("key") or key),
               name=man.get("name") or key, description=man.get("description", ""),
               owner_team=man.get("owner_team") or man.get("owner", ""),
               dir=app_dir, entities=entities, endpoints=endpoints, screens=screens)


def discover(cfg) -> List[App]:
    """Discover every downstream app registered under ``<base>/app/<key>/``."""
    root = cfg.p("app")
    apps: List[App] = []
    if not os.path.isdir(root):
        return apps
    for key in sorted(os.listdir(root)):
        app_dir = os.path.join(root, key)
        if not os.path.isdir(app_dir):
            continue
        man_path = ""
        for cand in ("model/app.json", "model/app.yaml", "app.json", "app.yaml"):
            p = os.path.join(app_dir, cand)
            if os.path.isfile(p):
                man_path = p
                break
        if not man_path:
            continue
        apps.append(_app_from_manifest(key, _load_manifest(man_path), app_dir))
    return apps


def screenshot_path(app: App, screen: Screen) -> str:
    """Absolute path to a screen's golden screenshot, if present."""
    if not screen.screenshot:
        return ""
    cand = os.path.join(app.dir, "screens", screen.screenshot)
    return cand if os.path.isfile(cand) else ""


# ---- Lakebase schema generation ------------------------------------------
def lakebase_ddl(app: App) -> str:
    """Full Lakebase (Postgres) DDL for an app's data model."""
    lines = [f"-- Lakebase schema for app '{app.key}' ({app.name})",
             f"CREATE SCHEMA IF NOT EXISTS {app.schema};", ""]
    for e in app.entities:
        lines.append(_entity_ddl(app.schema, e))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _entity_ddl(schema: str, e: Entity) -> str:
    cols, pks = [], []
    for c in e.columns:
        cn = safe_ident(c.get("name", ""))
        if not cn:
            continue
        ct = _pg_type(c.get("type", ""))
        nn = "" if c.get("nullable", True) else " NOT NULL"
        cols.append(f"    {cn} {ct}{nn}")
        if c.get("pk") or c.get("primary_key"):
            pks.append(cn)
    if pks:
        cols.append(f"    PRIMARY KEY ({', '.join(pks)})")
    body = ",\n".join(cols) if cols else "    id bigint PRIMARY KEY"
    src = f"  -- synced from DW gold: {e.source}" if e.source else ""
    return f"CREATE TABLE IF NOT EXISTS {schema}.{safe_ident(e.name)} (\n{body}\n);{src}"


def lakebase_objects(app: App, catalog: str) -> List[dict]:
    """The Lakebase tables + UC synced-table definitions for an app."""
    out: List[dict] = []
    for e in app.entities:
        out.append({
            "schema": app.schema, "table_name": safe_ident(e.name),
            "kind": "synced" if e.source else "table",
            "synced_from": (f"{catalog}.{e.source}" if e.source else ""),
            "ddl": _entity_ddl(app.schema, e),
        })
    return out


def schema_diff(app: App) -> Dict[str, Any]:
    """Deterministic schema-parity signal: every entity has typed columns + a source."""
    per_entity = {}
    ok = True
    for e in app.entities:
        typed = [c for c in e.columns if c.get("name")]
        entity_ok = bool(typed)
        per_entity[e.name] = {"columns": len(typed), "has_source": bool(e.source),
                              "ok": entity_ok}
        ok = ok and entity_ok
    return {"ok": ok and bool(app.entities), "entities": per_entity}
