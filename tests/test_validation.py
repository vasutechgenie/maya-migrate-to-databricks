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
