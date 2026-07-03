"""MAYA validation: check profiles, rendered SQL, and the soak gate state machine."""
from core import validation as V


def test_profiles():
    assert len(V.checks_for("dev")) == 6
    assert len(V.checks_for("sit")) == 10
    assert len(V.checks_for("soak")) == 10


def test_soak_reason_codes_present():
    assert "INCREMENTAL-LOGIC" in V.REASON_CODES
    assert "LATE-DATA" in V.REASON_CODES


def _all_pass(checks):
    return {c: True for c in checks}


DEV = V.PROFILE_DEV_SAMPLE
SIT = V.PROFILE_SIT_FULL
SOAK = V.PROFILE_SOAK


def test_gate_blocked_when_sit_incomplete():
    r = V.maya_gate("p", _all_pass(DEV), {"schema_parity": True})
    assert r["status"] == "BLOCKED"


def test_gate_provisional_after_dev_and_sit():
    r = V.maya_gate("p", _all_pass(DEV), _all_pass(SIT), soak_results=None)
    assert r["status"] == "PROVISIONAL"
    assert r["maya_dev"] == "PASS" and r["maya_sit"] == "PASS"
    assert r["maya_soak"] == "PENDING"


def test_gate_provisional_when_a_soak_window_fails():
    soak = {"T+7": _all_pass(SOAK), "T+14": {"schema_parity": True}}
    r = V.maya_gate("p", _all_pass(DEV), _all_pass(SIT), soak_results=soak)
    assert r["status"] == "PROVISIONAL"
    assert r["maya_soak"] == "FAIL"


def test_gate_certified_when_all_windows_green():
    soak = {"T+7": _all_pass(SOAK), "T+14": _all_pass(SOAK)}
    r = V.maya_gate("p", _all_pass(DEV), _all_pass(SIT), soak_results=soak)
    assert r["status"] == "CERTIFIED"
    assert r["maya_soak"] == "PASS"


def test_gate_certified_when_soak_not_required():
    r = V.maya_gate("p", _all_pass(DEV), _all_pass(SIT),
                    soak_results=None, require_soak=False)
    assert r["status"] == "CERTIFIED"


def _cert(pipe):
    return V.maya_gate(pipe, _all_pass(DEV), _all_pass(SIT),
                       soak_results={"T+7": _all_pass(SOAK), "T+14": _all_pass(SOAK)})


def _prov(pipe):
    return V.maya_gate(pipe, _all_pass(DEV), _all_pass(SIT), soak_results=None)


def _blocked(pipe):
    return V.maya_gate(pipe, _all_pass(DEV), {"schema_parity": True})


def test_system_in_progress_when_any_blocked():
    gates = {"a": _cert("a"), "b": _blocked("b")}
    r = V.system_certification(gates)
    assert r["status"] == "MIGRATION_IN_PROGRESS"
    assert r["blocking"] == ["b"]
    assert r["totals"] == {"pipelines": 2, "certified": 1, "provisional": 0, "blocked": 1}


def test_system_provisional_when_all_at_least_provisional():
    gates = {"a": _cert("a"), "b": _prov("b")}
    r = V.system_certification(gates)
    assert r["status"] == "SYSTEM_PROVISIONAL"
    assert r["blocking"] == ["b"]


def test_system_complete_when_all_certified_and_no_bi():
    gates = {"a": _cert("a"), "b": _cert("b")}
    r = V.system_certification(gates)
    assert r["status"] == "MIGRATION_COMPLETE"
    assert r["blocking"] == []


def test_system_bi_incomplete_blocks_completion():
    gates = {"a": _cert("a"), "b": _cert("b")}
    r = V.system_certification(gates, bi_done={"dash::t1": True, "dash::t2": False})
    assert r["status"] == "SYSTEM_PROVISIONAL"
    assert r["bi"] == {"done": 1, "total": 2}
    assert "BI:1/2" in r["blocking"]


def test_system_complete_with_all_bi_done():
    gates = {"a": _cert("a")}
    r = V.system_certification(gates, bi_done={"dash::t1": True})
    assert r["status"] == "MIGRATION_COMPLETE"


def test_system_by_wave_rollup():
    gates = {"a": _cert("a"), "b": _prov("b"), "c": _blocked("c")}
    waves = {"a": 0, "b": 1, "c": 1}
    r = V.system_certification(gates, waves=waves)
    assert r["by_wave"][0] == {"certified": 1, "provisional": 0, "blocked": 0, "total": 1}
    assert r["by_wave"][1] == {"certified": 0, "provisional": 1, "blocked": 1, "total": 2}


def test_soak_delta_sql_renders_window():
    t = V.for_env(_DummyCfg(), "rdm.mart_sales_daily",
                  keys=["sales_date"], columns=["sales_date", "revenue"],
                  env="soak", watermark_col="load_dt",
                  watermark_value="2026-07-14", prev_watermark_value="2026-07-07")
    sql = V.soak_delta_sql(t)
    assert "load_dt > '2026-07-07'" in sql
    assert "load_dt <= '2026-07-14'" in sql


class _DummyCfg:
    """Minimal cfg stub exposing .maya for validation.for_env."""
    class maya:
        dev_catalog = "nw_dev"
        sit_catalog = "nw_sit"
        source_ref_catalog = "nw_ref"

        @staticmethod
        def catalog_for(env):
            return "nw_sit" if env in ("sit", "soak") else "nw_dev"
