"""Downstream-app migration: discovery, Lakebase DDL, codegen, parity, and a full
end-to-end run of the synthesized Northwind "Sales Ops Console" app through all 12 stages.
"""
import json
import os
import shutil
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

NWAPP = os.path.join(REPO_ROOT, "examples", "northwind-app")
NW = os.path.join(REPO_ROOT, "examples", "northwind")
CONFIG = os.path.join(NWAPP, "northwind-app.yaml")

pytestmark = pytest.mark.skipif(
    not os.path.isfile(CONFIG), reason="northwind-app example not present")


def _app_cfg(base, with_app=True):
    from core.config import AcceleratorConfig
    cfg = AcceleratorConfig.from_yaml(CONFIG)
    # copy the app source into the temp workspace so committed fixtures stay pristine.
    # with_app=False simulates a project that migrates pipelines first and only adds the
    # downstream apps later.
    if with_app:
        shutil.copytree(os.path.join(NWAPP, "app"), os.path.join(base, "app"))
    cfg.base_dir = str(base)
    cfg.adapter_options = dict(cfg.adapter_options)
    cfg.adapter_options["source_dir"] = NW
    cfg.adapter_options["artifacts_dir"] = os.path.join(NW, "artifacts")
    return cfg


@pytest.fixture(scope="module")
def app_cfg(tmp_path_factory):
    return _app_cfg(tmp_path_factory.mktemp("nwapp"))


def test_discover(app_cfg):
    from core.apps import model
    apps = model.discover(app_cfg)
    assert len(apps) == 1
    a = apps[0]
    assert a.key == "sales_ops"
    assert len(a.entities) == 3
    assert len(a.endpoints) == 3
    assert len(a.screens) == 3


def test_lakebase_ddl(app_cfg):
    from core.apps import model
    a = model.discover(app_cfg)[0]
    ddl = model.lakebase_ddl(a)
    assert "CREATE SCHEMA IF NOT EXISTS sales_ops" in ddl
    assert "sales_ops.orders_ops" in ddl
    assert "primary key" in ddl.lower()
    # source-derived entities become UC synced tables
    objs = model.lakebase_objects(a, "nw_sit")
    synced = [o for o in objs if o["kind"] == "synced"]
    assert len(synced) == 3
    assert any("mart_sales_daily" in o["synced_from"] for o in synced)


def test_etl_retarget(app_cfg, tmp_path):
    from core.apps import etl, model
    a = model.discover(app_cfg)[0]
    out = str(tmp_path / "etl_out")
    os.makedirs(out, exist_ok=True)
    bindings = etl.retarget(app_cfg, a, "nw_sit", out)
    assert len(bindings) == 3
    assert etl.sync_ok(bindings)
    assert os.path.isfile(os.path.join(out, "etl", "sync_orders_ops.sql"))


def test_appgen(app_cfg, tmp_path):
    from core.apps import appgen, model
    a = model.discover(app_cfg)[0]
    out = str(tmp_path / "gen")
    res = appgen.generate(a, out)
    assert res["api"]["endpoints"] == 3
    assert res["ui"]["screens"] == 3
    assert os.path.isfile(os.path.join(out, "generated", "backend", "app.py"))
    assert os.path.isfile(os.path.join(out, "generated", "ui", "orders_queue.html"))
    assert os.path.isfile(os.path.join(out, "generated", "api", "openapi.json"))
    assert os.path.isfile(os.path.join(out, "generated", "app.yaml"))


def test_parity_gate():
    from core.apps import parity
    assert parity.app_gate("green", "green", "green", "green")["status"] == "CERTIFIED"
    prov = parity.app_gate("green", "green", "green", "red")  # sync pending at prod
    assert prov["status"] == "PROVISIONAL"
    blocked = parity.app_gate("red", "green", "green", "green")
    assert blocked["status"] == "BLOCKED"
    assert "schema" in blocked["blocked_by"]


def test_offline_app_subgraph(app_cfg):
    from core.ingest.offline import OfflineIngestDriver
    drv = OfflineIngestDriver(app_cfg)
    p = os.path.join(app_cfg.base_dir, "app", "sales_ops", "model", "app.json")
    frag = drv.parse_asset("app_model", p, "app/sales_ops/model/app.json")
    types = {o["type"] for o in frag["objects"]}
    assert {"APP", "APP_ENTITY", "APP_ENDPOINT", "APP_SCREEN"} <= types
    ets = {e["edge_type"] for e in frag["edges"]}
    assert {"CONTAINS", "MAPS_TO_SOURCE", "POPULATES_ENTITY",
            "EXPOSES_ENTITY", "SERVES_SCREEN"} <= ets


def test_e2e_run_all_certifies_app(app_cfg):
    from core import stages
    final = stages.run_all(app_cfg)
    assert final.get("complete") is True, final
    apps = json.load(open(app_cfg.out("apps.json")))["apps"]
    assert len(apps) == 1
    a = apps[0]
    cert = a["certification"]
    assert cert["status"] == "CERTIFIED", cert
    assert cert["schema_parity"] == cert["api_parity"] == "green"
    assert cert["ui_parity"] == cert["sync_parity"] == "green"
    assert all(e["schema_parity"] == "green" for e in a["entities"])
    assert all(ep["contract_parity"] == "green" for ep in a["endpoints"])
    assert all(s["ui_parity"] == "green" for s in a["screens"])
    assert a["deployed"] is True
    base = app_cfg.out(os.path.join("apps", "sales_ops"))
    assert os.path.isfile(os.path.join(base, "lakebase", "sales_ops.sql"))
    assert os.path.isfile(os.path.join(base, "generated", "backend", "app.py"))
    assert os.path.isfile(os.path.join(base, "bundle", "databricks.yml"))


def test_no_apps_project_still_passes(tmp_path):
    """A DW-only project (no app/ dir) must skip the app steps and pass."""
    from core import apps as app_mod
    from core.config import AcceleratorConfig
    cfg = AcceleratorConfig.from_yaml(CONFIG)
    cfg.base_dir = str(tmp_path)  # empty workspace: no app/ dir
    for fn in ("readiness", "collect", "specs", "identity", "docs", "deploy"):
        gate = getattr(app_mod, fn)(cfg)
        assert gate["passed"] is True
        assert gate.get("skipped") is True


# --------------------------------------------------------------------------- #
# BI-only / Apps-only add-on runs (scope): run a layer on top of an already-
# certified pipeline estate WITHOUT rebuilding any pipeline.
# --------------------------------------------------------------------------- #
def _md5(path):
    import hashlib
    return hashlib.md5(open(path, "rb").read()).hexdigest() if os.path.isfile(path) else None


@pytest.fixture(scope="module")
def migrated_cfg(tmp_path_factory):
    """A fully migrated estate (full run_all) to layer BI/App add-on runs on top of."""
    from core import stages
    cfg = _app_cfg(tmp_path_factory.mktemp("nwapp_scope"))
    final = stages.run_all(cfg)
    assert final.get("complete") is True, final
    return cfg


def test_scope_stages_lists():
    from core import stages
    assert stages.scope_stages("bi") == [5, 8]
    assert stages.scope_stages("apps") == [0, 1, 2, 3, 4, 6, 7, 9, 10, 11]
    assert stages.scope_stages("bi_apps") == list(range(12))
    assert stages.pipelines_certified  # symbol exists


def test_pipelines_certified_gate(migrated_cfg, tmp_path):
    from core import stages
    from core.config import AcceleratorConfig
    assert stages.pipelines_certified(migrated_cfg) is True
    empty = AcceleratorConfig.from_yaml(CONFIG)
    empty.base_dir = str(tmp_path)  # no gates.json
    assert stages.pipelines_certified(empty) is False


def test_run_scope_apps_does_not_rebuild_pipelines(migrated_cfg):
    """Apps add-on run re-certifies apps but leaves every pipeline artifact untouched."""
    from core import stages
    gates_before = _md5(migrated_cfg.out("gates.json"))
    build_before = _md5(migrated_cfg.out("stage4_build.json"))
    lp_before = stages._load_state(migrated_cfg).get("last_passed")

    state = stages.run_scope(migrated_cfg, "apps")

    assert _md5(migrated_cfg.out("gates.json")) == gates_before
    assert _md5(migrated_cfg.out("stage4_build.json")) == build_before
    assert stages._load_state(migrated_cfg).get("last_passed") == lp_before
    # apps re-certified
    a = json.load(open(migrated_cfg.out("apps.json")))["apps"][0]
    assert a["certification"]["status"] == "CERTIFIED"
    # the merged stage-4 gate preserves the pipeline build record + adds the app slice
    s4 = state["stages"]["4"]
    assert "build" in s4 and "conformance" in s4
    assert s4["scope"] == "apps"
    assert s4["passed"] is True


def test_run_scope_bi_only_touches_bi(migrated_cfg):
    """BI add-on run re-runs only stages 5/8 and leaves pipeline gates intact."""
    from core import stages
    gates_before = _md5(migrated_cfg.out("gates.json"))
    state = stages.run_scope(migrated_cfg, "bi")
    assert _md5(migrated_cfg.out("gates.json")) == gates_before
    assert state["stages"]["5"].get("phase") == "dev"
    assert state["stages"]["8"].get("phase") == "prod"
    # a non-BI stage keeps its full prior gate (not overwritten with a skip)
    assert "build" in state["stages"]["4"]


def test_run_scope_preserves_complete(migrated_cfg):
    from core import stages
    state = stages.run_scope(migrated_cfg, "bi_apps")
    assert state.get("complete") is True


# --------------------------------------------------------------------------- #
# End-to-end staged flow: migrate the pipelines FIRST (data + ETL only), then add
# the BI migration and the App migration SEPARATELY as add-on runs -- proving the
# "add BI/apps later" story works and never re-creates a pipeline.
# --------------------------------------------------------------------------- #
# the data + ETL (pipeline build + certify) stages: everything needed to certify the
# pipeline estate, excluding BI (5, 8) and the lifecycle-finalization stages (9, 10, 11
# whose go/no-go legitimately depends on BI + apps being present).
_PIPELINE_STAGES = [0, 1, 2, 3, 4, 6, 7]


def test_staged_pipeline_then_apps_then_bi(tmp_path_factory):
    from core import stages
    base = tmp_path_factory.mktemp("staged")

    # ---- Phase 1: PIPELINE migration only (no apps registered, BI not run yet) -----
    cfg = _app_cfg(base, with_app=False)  # user forgot BI + apps at first
    for n in _PIPELINE_STAGES:
        gate = stages.run_stage(cfg, n, enforce_prev=False, scope="all")
        assert gate.get("passed"), (n, gate)
    # pipelines are built + certified...
    assert stages.pipelines_certified(cfg) is True
    assert os.path.isfile(cfg.out("gates.json"))
    assert os.path.isfile(cfg.out("stage4_build.json"))
    # ...but BI has not run and no app exists yet
    st = stages._load_state(cfg)
    assert "5" not in st["stages"] and "8" not in st["stages"]
    assert not os.path.exists(cfg.out("apps.json"))
    pipe_gates = _md5(cfg.out("gates.json"))
    pipe_build = _md5(cfg.out("stage4_build.json"))

    # ---- Phase 2: user ADDS downstream apps later, runs ONLY the app migration -----
    shutil.copytree(os.path.join(NWAPP, "app"), os.path.join(base, "app"))
    app_state = stages.run_scope(cfg, "apps")
    a = json.load(open(cfg.out("apps.json")))["apps"][0]
    assert a["certification"]["status"] == "CERTIFIED", a["certification"]
    assert a["deployed"] is True
    assert os.path.isfile(cfg.out(os.path.join("apps", "sales_ops", "lakebase",
                                               "sales_ops.sql")))
    assert os.path.isfile(cfg.out(os.path.join("apps", "sales_ops", "generated",
                                               "backend", "app.py")))
    # the pipeline artifacts were NOT rebuilt
    assert _md5(cfg.out("gates.json")) == pipe_gates
    assert _md5(cfg.out("stage4_build.json")) == pipe_build
    # BI still has not run
    assert "5" not in app_state["stages"] and "8" not in app_state["stages"]

    # ---- Phase 3: user runs ONLY the BI migration (dev + prod) ----------------------
    bi_state = stages.run_scope(cfg, "bi")
    assert bi_state["stages"]["5"]["passed"] is True
    assert bi_state["stages"]["8"]["passed"] is True
    assert bi_state["stages"]["5"].get("phase") == "dev"
    assert bi_state["stages"]["8"].get("phase") == "prod"
    # neither the pipelines nor the apps were disturbed by the BI run
    assert _md5(cfg.out("gates.json")) == pipe_gates
    a2 = json.load(open(cfg.out("apps.json")))["apps"][0]
    assert a2["certification"]["status"] == "CERTIFIED"
    # the merged stage-4 ledger still carries the original pipeline build record
    assert "build" in bi_state["stages"]["4"]
