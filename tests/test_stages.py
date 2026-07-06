"""End-to-end twelve-stage full-lifecycle flow on Northwind with the offline driver.

Proves each stage's gate passes, and that the whole flow reaches a certified,
documented, secured, and enabled complete migration with zero external calls.
"""
import json
import os


def test_all_stages_pass(staged):
    _cfg, state = staged
    assert state["complete"] is True
    assert state["last_passed"] == 11
    for n in range(0, 12):
        assert state["stages"][str(n)]["passed"], f"stage {n} failed"


def test_stage_state_written(staged):
    cfg, _ = staged
    assert os.path.exists(cfg.out("stage_state.json"))
    st = json.load(open(cfg.out("stage_state.json")))
    # system certification is emitted by the prod build+certify stage (7)
    assert st["stages"]["7"]["system"]["status"] == "MIGRATION_COMPLETE"


def test_stage0_readiness_gate(staged):
    cfg, _ = staged
    gate = json.load(open(cfg.out("stage0_gate.json")))
    assert gate["passed"] is True
    assert gate["principals"] == 7 and gate["groups"] == 4
    assert gate["service_principals"] == 1 and gate["users"] == 2
    assert gate["grants"] == 17 and gate["secrets"] == 4
    assert gate["pii_columns"] == 2
    for k in ("unknown_principals", "unresolved_grants", "bad_secret_connections",
              "unsecured_connections", "unmasked_pii"):
        assert gate[k] == [], f"{k} not empty"


def test_stage0_artifacts_collected(staged):
    cfg, _ = staged
    import csv
    d = cfg.out("readiness")
    for name in ("principals.csv", "grants.csv", "secrets.csv", "classification.csv"):
        assert os.path.exists(os.path.join(d, name)), name
    assert os.path.exists(os.path.join(d, "security_facts.json"))
    principals = list(csv.DictReader(open(os.path.join(d, "principals.csv"))))
    assert any(p["type"] == "service_principal" for p in principals)


def test_stage0_gate_fails_on_unknown_principal(tmp_path):
    """A grant to a principal that does not exist -> Stage-0 gate FAILS."""
    import conftest
    from core import readiness
    broken = conftest._load_cfg(tmp_path / "broken0")
    collected = readiness.collect(broken)
    collected["grants"] = collected["grants"] + [
        {"principal": "ghost_group", "object": "src", "privilege": "SELECT"}]
    gate = readiness.compute(broken, collected)
    assert gate["passed"] is False
    assert "ghost_group" in gate["unknown_principals"]


def test_stage7_identity_access_parity(staged):
    cfg, _ = staged
    gate = json.load(open(cfg.out("stage7_gate.json")))
    assert gate["passed"] is True
    assert gate["grants_mapped"] == gate["grants_total"] == 17
    assert gate["masked_columns"] == 2 and gate["row_filters"] == 1
    assert gate["secrets"] == 4 and gate["secret_scope"] == "nw_secrets"
    assert gate["unmasked_pii"] == [] and gate["unsecured_connections"] == []
    sql = open(cfg.out("stage7_identity.sql")).read()
    assert "GRANT ALL PRIVILEGES ON SCHEMA nw_sit.src TO `nw_engineers`;" in sql
    assert "SET MASK nw_sit.masks.mask_name" in sql
    assert "SET ROW FILTER" in sql
    assert "ALTER SCHEMA nw_sit.rdm SET TAGS ('layer' = 'gold');" in sql


def test_stage8_enablement_go_no_go(staged):
    cfg, _ = staged
    gate = json.load(open(cfg.out("stage8_gate.json")))
    assert gate["passed"] is True
    assert gate["training_packs"] == 4 and gate["runbooks"] == 3
    assert gate["monitors"] == 5 and gate["alerts"] == 3
    assert all(c["ok"] for c in gate["go_no_go"])
    d = gate["dir"]
    for f in ("cutover_plan.md", "rollback_plan.md", "decommission_checklist.md",
              "operations.json"):
        assert os.path.exists(os.path.join(d, f)), f
    for aud in ("engineer", "analyst", "steward", "ops"):
        assert os.path.exists(os.path.join(d, "training", f"{aud}.md"))


def test_stage1_score_gate_100(staged):
    cfg, _ = staged
    gate = json.load(open(cfg.out("stage1_gate.json")))
    assert gate["passed"] is True
    assert gate["pipelines_at_100"] == gate["pipelines_scored"] == 8
    assert gate["views"] == 2
    assert gate["unidentified"] == []
    assert set(gate["external_systems"]) == {"ext_erp", "ext_web", "ext_fin"}


def test_stage1_assets_exported(staged):
    cfg, _ = staged
    assert os.path.exists(cfg.out("schedules.csv"))
    assert os.path.isdir(cfg.out("configs"))
    # every pipeline has a scheduler trigger
    import csv
    rows = list(csv.DictReader(open(cfg.out("schedules.csv"))))
    assert len(rows) == 8


def test_stage1_gate_fails_on_unresolved_ref(tmp_path):
    """Inject a read with no producer/declaration -> Stage-1 gate FAILS."""
    import csv
    import conftest
    from core import order as order_mod, score
    broken = conftest._load_cfg(tmp_path / "broken")
    broken.load_adapter().build_graph()
    order_mod.run(broken)
    epath = broken.edges_csv()
    rows = list(csv.DictReader(open(epath)))
    fields = list(rows[0].keys())
    rows.append({**{k: "" for k in fields},
                 "src_key": "nw_build_marts", "src_name": "nw_build_marts",
                 "src_type": "PIPELINE", "edge_type": "READS_TABLE",
                 "dst_key": "ghost.nowhere", "dst_name": "ghost.nowhere",
                 "dst_type": "TABLE", "exec_order": "9"})
    with open(epath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    res = score.compute(broken)
    assert res["gate"]["passed"] is False
    assert "ghost.nowhere" in " ".join(p["unresolved"] for p in res["per_pipeline"])


def test_stage2_synthetic_ri_and_views(staged):
    cfg, _ = staged
    gate = json.load(open(cfg.out("stage2_gate.json")))
    assert gate["passed"] is True
    assert gate["views"] == 2
    assert gate["replicated"] == gate["tables"] + gate["views"]
    sql = open(cfg.out("stage2_replicate.sql")).read()
    # child FK columns draw from a parent key range (referential integrity)
    assert "AS customer_key" in sql and "pmod(" in sql
    # views are replicated into the test catalog
    assert "CREATE VIEW nw_test.sales.v_active_customers" in sql


def test_stage3_one_pdf_per_pipeline(staged):
    cfg, _ = staged
    gate = json.load(open(cfg.out("stage3_gate.json")))
    assert gate["passed"] is True
    assert gate["pdfs"] == 8
    for pipe in ("nw_build_sales", "nw_build_marts", "nw_fx_sync"):
        assert os.path.exists(os.path.join(gate["dir"], f"{pipe}.pdf"))


def test_stage4_conformance(staged):
    cfg, _ = staged
    conf = json.load(open(cfg.out("stage4_conformance.json")))
    assert conf["gate"]["passed"] is True
    assert conf["gate"]["conforming"] == conf["gate"]["pipelines"] == 8


def test_stage4_topological_certification(staged):
    cfg, _ = staged
    gates = json.load(open(cfg.out("gates.json")))
    assert all(g["status"] == "CERTIFIED" for g in gates.values())
    # marts depends on sales/web: it certifies, and so do its predecessors
    for p in ("nw_build_sales", "nw_build_web", "nw_build_marts"):
        assert gates[p]["status"] == "CERTIFIED"


def test_stage5_bi_dev_certified(staged):
    """BI dev phase (stage 5): converted queries dev-certify clean on the sample gold, with
    no source parity / republish / Genie yet."""
    cfg, _ = staged
    gate = json.load(open(cfg.out("stage5_bi_dev_gate.json")))
    assert gate["passed"] is True
    assert gate["phase"] == "dev"
    assert gate["dev_certified"] == gate["objects"] == 2
    # authored records carry dev_certified but not the prod flags yet
    from core import bi as bi_mod
    for o in bi_mod.load_objects(cfg):
        rec = json.load(open(os.path.join(
            bi_mod._authored_dir(cfg), f"{bi_mod._safe(o.obj_id)}.json")))
        assert rec["dev_certified"] is True


def test_stage8_bi_done(staged):
    """BI prod phase (stage 8): parity + republish + Genie on the full gold."""
    cfg, _ = staged
    gate = json.load(open(cfg.out("stage5_bi_gate.json")))
    assert gate["passed"] is True
    assert gate.get("phase") == "prod"
    assert gate["done"] == gate["objects"] == 2


def test_stage6_docs_generated(staged):
    cfg, _ = staged
    gate = json.load(open(cfg.out("stage6_docs.json")))
    assert gate["passed"] is True
    root = gate["root"]
    assert os.path.exists(os.path.join(root, "index.md"))
    assert os.path.exists(os.path.join(root, "pipelines", "nw_build_marts.md"))
    assert os.path.exists(os.path.join(root, "views", "sales.v_active_customers.md"))
    # cert status flows into the docs
    txt = open(os.path.join(root, "pipelines", "nw_build_marts.md")).read()
    assert "CERTIFIED" in txt
