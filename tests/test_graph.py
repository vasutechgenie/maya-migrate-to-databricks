"""Graph load + normalized-model goldens for the Northwind demo."""


def test_object_and_edge_counts(built):
    _, g, _ = built
    assert len(g.objects) == 33
    assert len(g.edges) == 42


def test_pipeline_keys(built):
    _, g, _ = built
    pipes = set(g.pipeline_keys())
    assert pipes == {
        "nw_daily_master", "nw_ingest_erp", "nw_web_intake", "nw_fx_sync",
        "nw_build_sales", "nw_build_web", "nw_build_marts", "nw_qlik_replicate",
    }


def test_pipeline_io_reads_writes(built):
    _, g, _ = built
    ins, outs, procs = g.pipeline_io("nw_build_sales")
    assert outs == {
        "sales.dim_customer", "sales.dim_product",
        "sales.dim_supplier", "sales.fact_order",
    }
    assert "src.orders" in ins and "src.customers" in ins
    assert procs == set()


def test_orchestrator_fans_out(built):
    _, g, _ = built
    assert g.exec_pipe.get("nw_daily_master") == {
        "nw_ingest_erp", "nw_web_intake", "nw_fx_sync", "nw_build_sales",
        "nw_build_web", "nw_build_marts", "nw_qlik_replicate",
    }


def test_external_proc_call(built):
    _, g, _ = built
    assert g.calls.get("nw_fx_sync") == {"ext_fin.usp_load_fx"}
    assert g.objects["ext_fin.usp_load_fx"]["target_database"] == "ext_fin"
