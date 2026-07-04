"""AgentDriver selection, the offline backend, and the build+fix drift loop."""
import json
import os

from core.agents import get_driver
from core.agents.offline import OfflineAgentDriver
from core.agents.base import AgentDriver, BuildResult, FixResult
from core import orchestration as orch


def test_get_driver_defaults_to_offline(built):
    cfg, _, _ = built
    d = get_driver(cfg)
    assert isinstance(d, OfflineAgentDriver)
    assert d.name == "offline"


def test_offline_build_covers_parity_columns(built):
    cfg, _, _ = built
    ctx = json.load(open(cfg.p(cfg.specs_dir, "context", "nw_build_sales.json")))
    res = get_driver(cfg).build(ctx)
    text = json.dumps(res.spec).lower()
    for p in ctx["parity"]:
        assert p["table"].lower() in text
        for col in p["ddl_columns"]:
            assert col.lower() in text


def test_parity_report_red_on_incomplete_spec(built):
    cfg, _, _ = built
    ctx = json.load(open(cfg.p(cfg.specs_dir, "context", "nw_build_sales.json")))
    bad = {"summary": "x", "parity": [], "bronze": {"desc": "", "code": ""},
           "silver": {"desc": "", "code": ""}, "gold": {"desc": "", "code": ""}}
    report = orch.parity_report(cfg, ctx, bad, env="dev")
    assert not all(report.values())          # missing columns -> red


class _FailOnceDriver(AgentDriver):
    """Builds an empty (red) spec first, then fix() produces the correct one."""
    name = "failonce"

    def __init__(self, cfg):
        super().__init__(cfg)
        self._offline = OfflineAgentDriver(cfg)
        self.fixes = 0

    def build(self, ctx, prompt=""):
        return BuildResult(pipeline=ctx.get("pipeline", ""),
                           spec={"summary": "stub", "parity": [],
                                 "bronze": {"desc": "", "code": ""},
                                 "silver": {"desc": "", "code": ""},
                                 "gold": {"desc": "", "code": ""}})

    def fix(self, ctx, spec, parity_report, original_code=None):
        self.fixes += 1
        return FixResult(pipeline=ctx.get("pipeline", ""),
                         spec=self._offline.build(ctx).spec)

    def convert_bi(self, obj):
        return self._offline.convert_bi(obj)


def test_build_fix_loop_recovers(built, tmp_path):
    import conftest
    cfg = conftest._load_cfg(tmp_path / "fixloop")
    adapter = cfg.load_adapter()
    adapter.build_graph()
    from core import order as om, contract
    om.run(cfg)
    contract.generate_all(cfg, ddl_index=adapter.ddl_index())
    driver = _FailOnceDriver(cfg)
    gate = orch.build_swarm(cfg, driver=driver)
    assert gate["passed"] is True            # fix loop closed every red spec
    assert driver.fixes > 0                  # the loop actually ran


def test_certify_swarm_topological(built, tmp_path):
    import conftest
    cfg = conftest._load_cfg(tmp_path / "certtopo")
    adapter = cfg.load_adapter()
    adapter.build_graph()
    from core import order as om, contract
    om.run(cfg)
    contract.generate_all(cfg, ddl_index=adapter.ddl_index())
    orch.build_swarm(cfg)
    gate = orch.certify_swarm(cfg)
    assert gate["passed"] is True
    gates = json.load(open(cfg.out("gates.json")))
    # predecessor gating recorded no blocked_by for any pipeline (all certify in order)
    assert all(g.get("status") == "CERTIFIED" for g in gates.values())
