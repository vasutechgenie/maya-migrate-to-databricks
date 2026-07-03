"""MAYA RI-preserving dev sampling plan goldens."""
import json

from core import maya as maya_mod


def _ctx(cfg, pipe):
    return json.load(open(cfg.p(cfg.specs_dir, "context", f"{pipe}.json")))


def test_specs_from_context_cover_prereqs(built):
    cfg, _, _ = built
    specs = maya_mod.specs_from_context(cfg, _ctx(cfg, "nw_build_sales"))
    tables = {s.table for s in specs}
    assert tables == {
        "src.customers", "src.products", "src.suppliers",
        "src.orders", "src.order_lines",
    }


def test_sample_overrides_applied(built):
    cfg, _, _ = built
    specs = {s.table: s for s in
             maya_mod.specs_from_context(cfg, _ctx(cfg, "nw_build_sales"))}
    assert specs["src.orders"].rows == 20000        # per-table override
    assert specs["src.order_lines"].rows == 40000   # per-table override
    assert specs["src.customers"].rows == 10000     # default


def test_plan_is_deterministic_and_complete(built):
    cfg, _, _ = built
    specs = maya_mod.specs_from_context(cfg, _ctx(cfg, "nw_build_sales"))
    p1 = maya_mod.plan_samples(cfg, specs)
    p2 = maya_mod.plan_samples(cfg, specs)
    assert p1["sql"] == p2["sql"]                   # deterministic
    assert len(p1["manifest"]) == 5
    assert all(row["seed"] == 42 for row in p1["manifest"])
    assert any("CREATE OR REPLACE TABLE" in s for s in p1["sql"])
