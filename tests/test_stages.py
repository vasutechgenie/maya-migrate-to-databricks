"""End-to-end six-stage flow on Northwind with the deterministic offline driver.

Proves each stage's gate passes, and that the whole flow reaches a certified,
documented, complete migration with zero external calls.
"""
import json
import os


def test_all_stages_pass(staged):
    _cfg, state = staged
    assert state["complete"] is True
    assert state["last_passed"] == 6
    for n in range(1, 7):
        assert state["stages"][str(n)]["passed"], f"stage {n} failed"


def test_stage_state_written(staged):
    cfg, _ = staged
    assert os.path.exists(cfg.out("stage_state.json"))
    st = json.load(open(cfg.out("stage_state.json")))
    assert st["stages"]["4"]["system"]["status"] == "MIGRATION_COMPLETE"


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


def test_stage5_bi_done(staged):
    cfg, _ = staged
    gate = json.load(open(cfg.out("stage5_bi_gate.json")))
    assert gate["passed"] is True
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
