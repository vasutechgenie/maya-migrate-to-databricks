"""Topological build order + the INDEPENDENT verifier, on the Northwind demo."""
from core import order as order_mod
from core import verify_order as verify_mod


def test_table_waves(built):
    _, g, _ = built
    table_wave, _pipe_wave, _m = order_mod.compute(g)
    assert table_wave["ext_erp.customers"] == 0
    assert table_wave["src.customers"] == 1
    assert table_wave["sales.dim_customer"] == 2
    assert table_wave["rdm.mart_sales_daily"] == 3
    assert table_wave["serving.sales_daily"] == 4


def test_pipeline_waves(built):
    _, g, _ = built
    _table_wave, pipe_wave, _m = order_mod.compute(g)
    assert pipe_wave["nw_ingest_erp"] == 0
    assert pipe_wave["nw_web_intake"] == 0
    assert pipe_wave["nw_build_sales"] == 1
    assert pipe_wave["nw_build_marts"] == 2
    assert pipe_wave["nw_qlik_replicate"] == 3
    assert pipe_wave["nw_daily_master"] == 4


def test_independent_verifier_passes(built):
    cfg, _, _ = built
    r = verify_mod.run(cfg)
    assert r["passed"] is True
    assert r["C1_completeness"] is True
    assert r["C2_wave_agreement"] is True
    assert r["C3_forward_edges"] is True
    assert r["C4_build_sim"] is True
    assert r["n_waves"] == 5


def test_no_cycles(built):
    _, g, _ = built
    _tw, _pw, m = order_mod.compute(g)
    # every strongly-connected component is a single table (acyclic estate)
    assert all(len(c) == 1 for c in m["comps"])
