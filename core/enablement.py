"""
enablement.py -- Stage 11: enablement, go-live, and day-2 operations.

The last mile of a real migration is not data - it is people and operations. Stage 11
generates everything a program needs to actually cut over and run:

  * role-based training packs (engineer / analyst / steward / ops)
  * operational runbooks (daily operations, incident response, backfill)
  * a cutover plan, a rollback plan, and a source-decommission checklist
  * day-2 operations definitions (monitors, alerts, cost budget, DR/backup)

It then runs a go/no-go gate that refuses go-live unless every upstream gate is green
(readiness, data certification, BI, docs, identity) and every required artifact exists,
and finally performs the consolidated docs publish (data + identity + enablement).

Emits out/enablement/** and out/stage11_gate.json. Offline it writes files and does a
local commit only (no push), so the whole flow runs with zero external calls.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List

from .graph import Graph
from . import publish as publish_mod


DEFAULT_AUDIENCES = [
    {"id": "engineer", "title": "Data Engineers", "group_suffix": "engineers",
     "focus": "building, operating and fixing pipelines on Databricks"},
    {"id": "analyst", "title": "BI Analysts", "group_suffix": "analysts",
     "focus": "querying gold/serving marts, dashboards, and Genie/AI-BI"},
    {"id": "steward", "title": "Data Stewards", "group_suffix": "stewards",
     "focus": "ownership, classification, access reviews and governance"},
    {"id": "ops", "title": "Platform Operations", "group_suffix": "ops",
     "focus": "monitoring, alerting, cost, incident response and DR"},
]

RUNBOOKS = [
    ("daily_operations", "Daily operations",
     ["Confirm all scheduled jobs succeeded (check the run dashboard).",
      "Review parity/soak monitors for any drift alerts.",
      "Triage failed tasks using the pipeline's generated doc + spec PDF.",
      "Record any manual intervention in the change log."]),
    ("incident_response", "Incident response",
     ["Acknowledge the alert and open an incident channel.",
      "Identify the failing pipeline and its wave/dependents from the graph.",
      "Roll back the affected table to the last certified snapshot if needed.",
      "Re-run from the failed wave; re-prove parity before closing."]),
    ("backfill", "Backfill / reprocessing",
     ["Pick the target date range and affected pipelines.",
      "Run in topological (wave) order so dependents see fresh inputs.",
      "Re-run MAYA parity for each backfilled table.",
      "Update watermarks in the control table."]),
]


def _ops(cfg) -> dict:
    return getattr(cfg, "ops", {}) or {}


def _enablement_cfg(cfg) -> dict:
    return getattr(cfg, "enablement", {}) or {}


def _out_dir(cfg, *parts) -> str:
    d = cfg.out(os.path.join("enablement", *parts)) if parts else cfg.out("enablement")
    os.makedirs(d, exist_ok=True)
    return d


def _write(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text.rstrip() + "\n")


def _load_json(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


def _pipeline_count(cfg) -> int:
    try:
        g = Graph.load(cfg.objects_csv(), cfg.edges_csv(),
                       cfg.pipeline_types, cfg.table_types)
        return len(list(g.pipeline_keys()))
    except Exception:
        return 0


def _audiences(cfg) -> List[dict]:
    return _enablement_cfg(cfg).get("audiences") or DEFAULT_AUDIENCES


def _gen_training(cfg) -> List[str]:
    home = (cfg.home_database or cfg.project_name or "app").lower()
    npipe = _pipeline_count(cfg)
    written = []
    for a in _audiences(cfg):
        group = f"{home}_{a['group_suffix']}"
        lines = [
            f"# Training: {a['title']}", "",
            f"**Audience group:** `{group}`  ",
            f"**Focus:** {a['focus']}", "",
            "## What changed", "",
            f"- The `{cfg.project_name}` estate ({npipe} pipelines) now runs on "
            f"Databricks (Unity Catalog: `{cfg.maya.sit_catalog}`), rebuilt in the "
            "medallion (bronze/silver/gold) model.",
            "- Access is governed by Unity Catalog grants; sensitive columns are masked.",
            "", "## What you need to do", "",
        ]
        if a["id"] == "engineer":
            lines += [
                "- Author/maintain pipelines with the shared engines (E1-E7); never hand-fork.",
                "- Prove every change with MAYA parity (dev -> SIT -> soak) before certifying.",
                "- Use the generated pipeline docs + spec PDFs as the source of truth.",
            ]
        elif a["id"] == "analyst":
            lines += [
                "- Point BI tools + Genie/AI-BI at the migrated gold/serving marts.",
                "- Sensitive columns are masked unless you are a steward - request access via steward review.",
                "- Report any number that does not match legacy through the drift process.",
            ]
        elif a["id"] == "steward":
            lines += [
                "- Own schema/table grants and run periodic access reviews.",
                "- Maintain the data classification + masking policy.",
                "- Approve exceptions and keep the business glossary current.",
            ]
        else:  # ops
            lines += [
                "- Watch the monitors + alerts; follow the incident runbook.",
                "- Track cost against the budget; investigate anomalies.",
                "- Exercise the DR/backup restore on the defined cadence.",
            ]
        lines += ["", "## Where to learn more", "",
                  "- Generated migration docs (pipelines, tables, views, BI).",
                  "- Runbooks in this pack; the MAYA methodology docs."]
        path = os.path.join(_out_dir(cfg, "training"), f"{a['id']}.md")
        _write(path, "\n".join(lines))
        written.append(a["id"])
    return written


def _gen_runbooks(cfg) -> List[str]:
    written = []
    for rid, title, steps in RUNBOOKS:
        lines = [f"# Runbook: {title}", ""]
        lines += [f"{i}. {s}" for i, s in enumerate(steps, 1)]
        _write(os.path.join(_out_dir(cfg, "runbooks"), f"{rid}.md"),
               "\n".join(lines))
        written.append(rid)
    return written


def _gen_cutover(cfg):
    d = _out_dir(cfg)
    cutover = [
        f"# Cutover plan - {cfg.project_name}", "",
        "## Preconditions (all must be green)", "",
        "- Stage 0 readiness gate passed (identity, access, secrets, classification).",
        "- Data estate CERTIFIED (dev build+certify, full load, prod certify) - Stages 4, 6, 7.",
        "- BI layer dev-certified (Stage 5) and prod parity-verified + republished (Stage 8).",
        "- Identity/security/governance applied - Stage 10.",
        "", "## Cutover sequence", "",
        "1. Freeze source writes for the cutover window.",
        "2. Final incremental load + final MAYA-SIT parity per wave (topological order).",
        "3. Flip orchestration/schedules to the Databricks jobs.",
        "4. Repoint BI/Genie and downstream consumers to Unity Catalog.",
        "5. Run smoke checks + first live parity (soak T+0).",
        "6. Announce go-live; keep the source in read-only parallel run.",
    ]
    rollback = [
        f"# Rollback plan - {cfg.project_name}", "",
        "Rollback is possible until the source is decommissioned (parallel run window).",
        "", "## Triggers", "",
        "- A certified pipeline drifts in the soak window, or a Sev-1 incident at go-live.",
        "", "## Steps", "",
        "1. Re-enable source writes / source schedules.",
        "2. Repoint BI + consumers back to the source.",
        "3. Quarantine the failing Databricks pipeline; open a drift ticket.",
        "4. Fix + re-certify on Databricks; re-attempt cutover next window.",
    ]
    decommission = [
        f"# Source decommission checklist - {cfg.project_name}", "",
        "Only after a clean parallel-run soak with zero drift.", "",
        "- [ ] All pipelines FINAL-certified (soak windows green).",
        "- [ ] BI + all downstream consumers confirmed on Databricks.",
        "- [ ] Final source snapshot archived + retention set.",
        "- [ ] Source credentials rotated/revoked; secrets removed.",
        "- [ ] Source schedules disabled; compute deprovisioned.",
        "- [ ] Stakeholder sign-off recorded.",
    ]
    _write(os.path.join(d, "cutover_plan.md"), "\n".join(cutover))
    _write(os.path.join(d, "rollback_plan.md"), "\n".join(rollback))
    _write(os.path.join(d, "decommission_checklist.md"), "\n".join(decommission))


def _gen_operations(cfg) -> dict:
    ops = _ops(cfg)
    monitors = ops.get("monitors") or [
        "job_success_rate", "pipeline_latency", "maya_parity_drift",
        "freshness_sla", "row_count_delta"]
    alerts = ops.get("alerts") or [
        {"name": "job_failure", "channel": "pagerduty", "severity": "sev1"},
        {"name": "parity_drift", "channel": "slack", "severity": "sev2"},
        {"name": "freshness_breach", "channel": "slack", "severity": "sev2"}]
    cost = ops.get("cost_budget") or {"monthly_usd": 5000, "alert_at_pct": 80}
    dr = ops.get("dr") or {"rpo_hours": 24, "rto_hours": 4,
                           "backup": "Delta deep clone to a secondary region, daily"}
    operations = {"monitors": monitors, "alerts": alerts,
                  "cost_budget": cost, "dr": dr}
    d = _out_dir(cfg)
    with open(os.path.join(d, "operations.json"), "w") as f:
        json.dump(operations, f, indent=1)
    lines = [f"# Day-2 operations - {cfg.project_name}", "",
             "## Monitors", ""] + [f"- `{m}`" for m in monitors]
    lines += ["", "## Alerts", ""]
    lines += [f"- **{a['name']}** -> {a['channel']} ({a['severity']})" for a in alerts]
    lines += ["", "## Cost governance", "",
              f"- Monthly budget: ${cost['monthly_usd']}, alert at {cost['alert_at_pct']}%.",
              "", "## Disaster recovery", "",
              f"- RPO {dr['rpo_hours']}h / RTO {dr['rto_hours']}h. Backup: {dr['backup']}."]
    _write(os.path.join(d, "operations.md"), "\n".join(lines))
    return operations


def _consolidated_publish(cfg, training, runbooks) -> dict:
    """Add identity + enablement summary pages to the generated docs, then publish."""
    root = cfg.out(os.path.join("docs", "generated"))
    os.makedirs(root, exist_ok=True)

    s10 = _load_json(cfg.out("stage10_gate.json"), {})
    id_lines = ["# Identity, security & governance", "",
                f"- Groups: {s10.get('groups', '?')}, "
                f"service principals: {s10.get('service_principals', '?')}",
                f"- Grants mapped: {s10.get('grants_mapped', '?')}/"
                f"{s10.get('grants_total', '?')}",
                f"- Masked columns: {s10.get('masked_columns', '?')}, "
                f"row filters: {s10.get('row_filters', '?')}",
                f"- Secret scope: `{s10.get('secret_scope', '?')}` "
                f"({s10.get('secrets', '?')} secrets)",
                "", "See `stage10_identity.sql` for the full DDL."]
    _write(os.path.join(root, "identity", "index.md"), "\n".join(id_lines))

    en_lines = ["# Enablement, cutover & operations", "",
                "## Training packs", ""]
    en_lines += [f"- {t}" for t in training]
    en_lines += ["", "## Runbooks", ""] + [f"- {r}" for r in runbooks]
    en_lines += ["", "## Go-live", "",
                 "- Cutover plan, rollback plan, decommission checklist",
                 "- Day-2 operations (monitors, alerts, cost, DR)"]
    _write(os.path.join(root, "enablement", "index.md"), "\n".join(en_lines))

    return publish_mod.run(
        cfg, message=f"docs: MAYA full-lifecycle docs for {cfg.project_name}")


def run(cfg) -> dict:
    training = _gen_training(cfg)
    runbooks = _gen_runbooks(cfg)
    _gen_cutover(cfg)
    operations = _gen_operations(cfg)

    # go/no-go: every upstream gate green + every required artifact present
    d = _out_dir(cfg)
    required = [
        os.path.join(d, "cutover_plan.md"),
        os.path.join(d, "rollback_plan.md"),
        os.path.join(d, "decommission_checklist.md"),
        os.path.join(d, "operations.json"),
    ]
    artifacts_ok = all(os.path.exists(p) for p in required) and bool(training) \
        and bool(runbooks)

    gates_data = _load_json(cfg.out("gates.json"), {})
    data_certified = bool(gates_data) and all(
        g.get("status") == "CERTIFIED" for g in gates_data.values())

    checks = [
        ("readiness (Stage 0)",
         _load_json(cfg.out("stage0_gate.json"), {}).get("passed") is True),
        ("data certified (Stages 4, 6, 7)", data_certified),
        ("BI dev-certified (Stage 5)",
         _load_json(cfg.out("stage5_bi_dev_gate.json"), {}).get("passed") is True),
        ("BI parity + republished (Stage 8)",
         _load_json(cfg.out("stage5_bi_gate.json"), {}).get("passed") is True),
        ("docs generated (Stage 9)",
         _load_json(cfg.out("stage9_docs.json"), {}).get("passed") is True),
        ("identity/security (Stage 10)",
         _load_json(cfg.out("stage10_gate.json"), {}).get("passed") is True),
        ("enablement artifacts", artifacts_ok),
    ]
    go_no_go = [{"item": name, "ok": bool(ok)} for name, ok in checks]
    passed = all(c["ok"] for c in go_no_go)

    pub = _consolidated_publish(cfg, training, runbooks)

    gate = {
        "stage": 11,
        "passed": bool(passed),
        "training_packs": len(training),
        "runbooks": len(runbooks),
        "cutover_plan": True,
        "rollback_plan": True,
        "decommission_checklist": True,
        "monitors": len(operations["monitors"]),
        "alerts": len(operations["alerts"]),
        "go_no_go": go_no_go,
        "published": bool(pub.get("passed")),
        "dir": d,
    }
    with open(cfg.out("stage11_gate.json"), "w") as f:
        json.dump(gate, f, indent=1)
    return gate
