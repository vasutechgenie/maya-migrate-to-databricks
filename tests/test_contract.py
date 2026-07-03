"""Pipeline classification, engine mapping, and parity-target derivation goldens."""

EXPECTED = {
    "nw_daily_master":   ("G", "E5", "orchestration"),
    "nw_ingest_erp":     ("A", "E1", "medallion"),
    "nw_web_intake":     ("D", "E1", "medallion"),
    "nw_fx_sync":        ("E", "E4", "external_invoke"),
    "nw_build_sales":    ("B", "E2", "medallion"),
    "nw_build_web":      ("B", "E2", "medallion"),
    "nw_build_marts":    ("B", "E2", "medallion"),
    "nw_qlik_replicate": ("F", "E1", "medallion"),
}


def test_pattern_engine_kind(index_by_pipeline):
    for pipe, (pat, eng, kind) in EXPECTED.items():
        r = index_by_pipeline[pipe]
        assert (r["pattern"], r["engine"], r["kind"]) == (pat, eng, kind), pipe


def test_parity_targets_only_silver_and_gold(index_by_pipeline):
    # bronze ingestion has no parity targets; silver/gold builds do
    assert index_by_pipeline["nw_ingest_erp"]["n_parity"] == 0
    assert index_by_pipeline["nw_build_sales"]["n_parity"] == 4
    assert index_by_pipeline["nw_build_web"]["n_parity"] == 1
    assert index_by_pipeline["nw_build_marts"]["n_parity"] == 3


def test_total_parity_targets(built):
    _, _, index = built
    assert sum(r["n_parity"] for r in index) == 8


def test_context_pack_has_ddl_columns(built):
    import json
    cfg, _, _ = built
    ctx = json.load(open(cfg.p(cfg.specs_dir, "context", "nw_build_sales.json")))
    parity = {p["table"]: p for p in ctx["parity"]}
    assert "customer_key" in parity["sales.dim_customer"]["ddl_columns"]
    assert parity["sales.dim_customer"]["layer"] == "silver"
