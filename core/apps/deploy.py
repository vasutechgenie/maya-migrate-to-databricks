"""Emit the Databricks deployment for a migrated app: Lakebase + Databricks App bundle.

Offline (no workspace bound) this writes a real Databricks Asset Bundle (``databricks.yml``)
plus a Lakebase provisioning plan into ``out/apps/<key>/bundle/`` -- the source of truth
that ``databricks bundle deploy`` consumes. When a workspace + token are available the
same bundle is deployed via the Databricks CLI; failures are reported, never simulated.
"""
from __future__ import annotations

import os
from typing import Any, Dict

from .model import App


def _bundle_yaml(app: App, instance: str, catalog: str) -> str:
    name = f"maya_app_{app.schema}"
    return (
        "# Databricks Asset Bundle for a MAYA-migrated app (generated)\n"
        "bundle:\n"
        f"  name: {name}\n\n"
        "resources:\n"
        "  database_instances:\n"
        f"    {app.schema}_lakebase:\n"
        f"      name: {instance}\n"
        "      capacity: CU_1\n"
        "  apps:\n"
        f"    {app.schema}_app:\n"
        f"      name: maya-{app.schema.replace('_', '-')}\n"
        "      source_code_path: ./generated\n"
        "      resources:\n"
        "        - name: lakebase\n"
        "          database:\n"
        f"            instance_name: {instance}\n"
        f"            database_name: {app.schema}\n"
        "            permission: CAN_CONNECT_AND_CREATE\n\n"
        "targets:\n"
        "  dev:\n    default: true\n"
        "  prod:\n    default: false\n"
    )


def _lakebase_plan(app: App, instance: str, catalog: str) -> str:
    lines = [f"# Lakebase provisioning plan for app '{app.key}'",
             f"instance: {instance}", f"catalog: {catalog}",
             f"schema: {app.schema}", "synced_tables:"]
    for e in app.entities:
        if e.source:
            lines.append(f"  - target: {app.schema}.{e.name}")
            lines.append(f"    source: {catalog}.{e.source}")
            lines.append("    scheduling_policy: SNAPSHOT")
    return "\n".join(lines) + "\n"


def build_bundle(app: App, out_dir: str, instance: str, catalog: str) -> Dict[str, Any]:
    """Write the app's deploy bundle + Lakebase plan; return a deployment record."""
    bundle_dir = os.path.join(out_dir, "bundle")
    os.makedirs(bundle_dir, exist_ok=True)
    with open(os.path.join(bundle_dir, "databricks.yml"), "w") as f:
        f.write(_bundle_yaml(app, instance, catalog))
    with open(os.path.join(bundle_dir, "lakebase_plan.yaml"), "w") as f:
        f.write(_lakebase_plan(app, instance, catalog))
    return {
        "lakebase_instance": instance,
        "bundle_path": os.path.relpath(bundle_dir, os.path.dirname(out_dir)),
        "mode": "offline",
        "status": "bundled",
        "app_url": "",
    }


def deploy(app: App, out_dir: str, instance: str, catalog: str,
           host: str = "", token: str = "", emit=None) -> Dict[str, Any]:
    """Emit the bundle, then deploy via the Databricks CLI when creds are present."""
    rec = build_bundle(app, out_dir, instance, catalog)
    if not (host and token):
        rec["status"] = "bundled"
        return rec
    try:
        from core.execution.bundle import cli_available, deploy_and_run  # noqa: F401
        if not cli_available():
            rec["status"] = "bundled"
            rec["message"] = "databricks CLI not found; bundle emitted only"
            return rec
        import subprocess
        env = dict(os.environ)
        env["DATABRICKS_HOST"] = host
        env["DATABRICKS_TOKEN"] = token
        bundle_dir = os.path.join(out_dir, "bundle")
        dep = subprocess.run(["databricks", "bundle", "deploy", "-t", "dev"],
                             cwd=bundle_dir, env=env, capture_output=True,
                             text=True, timeout=1800)
        rec["mode"] = "databricks"
        rec["status"] = "deployed" if dep.returncode == 0 else "failed"
        if dep.returncode != 0:
            rec["message"] = (dep.stderr or dep.stdout or "").strip()[:2000]
    except Exception as exc:  # pragma: no cover - live path
        rec["status"] = "failed"
        rec["message"] = str(exc)
    return rec
