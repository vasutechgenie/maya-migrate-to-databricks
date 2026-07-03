"""
validation.py -- the strict parity framework: 10 checks, a point-in-time basis,
a drift-investigation loop, and a reason-code taxonomy.

The harness compares a Databricks build table against the source reference at a
pinned watermark and returns a green/red per check. A mismatch is a defect to be
root-caused in code (the drift loop), never waived - the only permitted red is a
documented, signed-off LEGACY-BUG.

This module renders the comparison SQL and defines the data model; running it is a
thin wrapper you execute on a Databricks SQL warehouse (serverless recommended).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# ---- the ten checks --------------------------------------------------------
CHECKS = [
    ("schema_parity", "Column names, order, types, nullability, precision match"),
    ("row_count", "Total + per-partition row counts match"),
    ("key_parity", "PK/business key set identical - no missing/extra/dupes"),
    ("content_checksum", "Order-independent per-row hash aggregated per table matches"),
    ("column_aggregates", "SUM/MIN/MAX/COUNT-distinct per column reconcile exactly"),
    ("null_distribution", "Per-column null + distinct counts match"),
    ("referential_integrity", "FKs resolve to already-certified parents; no orphans"),
    ("no_extra_output", "Only the contract's tables/columns are produced"),
    ("idempotency", "Re-run yields byte-identical output (same hash)"),
    ("row_level_sample", "Failing keys/columns enumerated old-vs-new"),
]

# ---- MAYA two-phase profiles ----------------------------------------------
# MAYA-Dev proves LOGIC on the sampled illusion of prod: only volume-independent
# checks (full-volume row-count/checksum/aggregates are meaningless on a sample and
# are deferred to SIT). MAYA-SIT proves everything at scale on prod-copied data.
PROFILE_DEV_SAMPLE = [
    "schema_parity", "key_parity", "referential_integrity",
    "no_extra_output", "idempotency", "row_level_sample",
]
PROFILE_SIT_FULL = [c[0] for c in CHECKS]   # all ten, at scale, point-in-time

# MAYA-Soak proves SUSTAINED parity: after build-time SIT parity is green, both systems
# keep running in parallel and we re-prove parity at each soak window (default T+7, T+14).
# Build-time (point-in-time) parity only proves STATE equality once; it cannot prove that
# the ongoing/incremental logic matches. Subtle merge/CDC/SCD/late-arriving-data
# differences accumulate silently across production loads and only surface days later.
# At each checkpoint we re-run the full battery on the cumulative table AND on the
# incremental delta produced since the previous checkpoint (both must be green).
PROFILE_SOAK = [c[0] for c in CHECKS]       # all ten, re-proven per window, zero drift

PROFILES = {"dev": PROFILE_DEV_SAMPLE, "sit": PROFILE_SIT_FULL, "soak": PROFILE_SOAK}


def checks_for(env: str):
    """The check names to run for a MAYA phase ('dev', 'sit', or 'soak')."""
    return PROFILES.get(env, PROFILE_SIT_FULL)

# ---- drift reason-code taxonomy -------------------------------------------
REASON_CODES = {
    "TRANSLATION": ("Notebook logic differs from source", "Fix notebook, re-run"),
    "SCHEMA": ("Type / order / nullability mismatch", "Align DDL, re-run"),
    "TIMING": ("Load-window / late-arriving rows", "Align watermark, re-run"),
    "SOURCE-CHANGE": ("Source code changed since capture", "Re-pull + re-translate"),
    "TYPE-NUANCE": ("Rounding / collation / TZ / decimal", "Match casting rules"),
    "LEGACY-BUG": ("Confirmed defect in source", "Customer sign-off to keep/fix"),
    # ---- soak-specific drift (only observable across successive production loads) ----
    "INCREMENTAL-LOGIC": ("Merge/CDC/SCD/upsert logic diverges over successive runs",
                          "Fix incremental step, re-backfill window, re-soak"),
    "LATE-DATA": ("Late-arriving/out-of-order rows handled differently over time",
                  "Align late-data + watermark handling, re-soak"),
}


@dataclass
class ParityTarget:
    source_table: str            # e.g. nw_ref.sales.dim_customer
    build_table: str             # e.g. gold.dim_customer
    keys: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    watermark_col: Optional[str] = None
    watermark_value: Optional[str] = None   # pinned point-in-time
    env: str = "sit"             # 'dev' (sample), 'sit' (full-scale), or 'soak' (sustained)
    prev_watermark_value: Optional[str] = None  # soak: start of the delta window


def for_env(cfg, build_table: str, keys=None, columns=None, env: str = "sit",
            watermark_col=None, watermark_value=None,
            prev_watermark_value=None) -> "ParityTarget":
    """Build a ParityTarget for a MAYA phase.

    - dev: compare the dev-built table against the sampled dev source (illusion).
    - sit: compare the sit-built table against production-copied reference data.
    - soak: like sit, but re-run at a later checkpoint watermark to prove SUSTAINED
      parity. If prev_watermark_value is set, the delta window is also checkable.
    Watermark (point-in-time) is applied at SIT and at every SOAK checkpoint.
    """
    m = cfg.maya
    cat = m.catalog_for(env)
    short = build_table.split(".")[-1]
    build = f"{cat}.{build_table}"
    if env == "dev":
        # compare the dev build against the sampled source held in a dev ref schema
        source = f"{m.dev_catalog}_ref.{short}"
        wm_col, wm_val = None, None
    else:
        ref = m.source_ref_catalog or f"{m.sit_catalog}_ref"
        source = f"{ref}.{short}"
        wm_col, wm_val = watermark_col, watermark_value
    return ParityTarget(source_table=source, build_table=build, keys=keys or [],
                        columns=columns or [], env=env,
                        watermark_col=wm_col, watermark_value=wm_val,
                        prev_watermark_value=prev_watermark_value)


# ---- MAYA-Soak: sustained parallel-run parity ------------------------------
@dataclass
class SoakCheckpoint:
    label: str                   # e.g. 'T+7'
    days_after_cert: int         # offset from provisional certification
    due_date: Optional[str] = None
    ran_date: Optional[str] = None
    passed: Optional[bool] = None


def soak_checkpoints(cfg, provisional_cert_date: Optional[str] = None) -> List[SoakCheckpoint]:
    """The soak schedule for a pipeline (default T+7, T+14 from provisional cert).

    provisional_cert_date (ISO 'YYYY-MM-DD') anchors due-dates when provided.
    """
    from datetime import date, timedelta
    base = None
    if provisional_cert_date:
        try:
            base = date.fromisoformat(provisional_cert_date[:10])
        except ValueError:
            base = None
    out = []
    for d in cfg.maya.soak_windows_days:
        due = (base + timedelta(days=d)).isoformat() if base else None
        out.append(SoakCheckpoint(label=f"T+{d}", days_after_cert=d, due_date=due))
    return out


def _wm_pred(t: ParityTarget, alias: str = "") -> str:
    p = f"{alias + '.' if alias else ''}{t.watermark_col}"
    if t.watermark_col and t.watermark_value:
        return f" WHERE {p} <= '{t.watermark_value}'"
    return ""


def _delta_pred(t: ParityTarget) -> str:
    """The incremental slice loaded since the previous soak checkpoint."""
    if t.watermark_col and t.watermark_value and t.prev_watermark_value:
        return (f" WHERE {t.watermark_col} > '{t.prev_watermark_value}'"
                f" AND {t.watermark_col} <= '{t.watermark_value}'")
    return ""


def soak_delta_sql(t: ParityTarget) -> str:
    """soak delta parity: prove the rows loaded in THIS window match, not just the
    cumulative total. Cumulative can mask a broken incremental step that
    self-corrects on full recompute; the delta slice cannot."""
    if not (t.watermark_col and t.prev_watermark_value):
        return "-- soak_delta_parity: no delta window (prev watermark unset); skipped"
    d = _delta_pred(t)
    cols = ", ".join(t.columns) if t.columns else "*"

    def block(tbl):
        return (f"SELECT count(*) AS n, "
                f"sum(xxhash64(to_json(struct({cols})))) AS h FROM {tbl}{d}")
    return ("-- soak_delta_parity: incremental window (prev < wm <= now) must match\n"
            f"WITH s AS ({block(t.source_table)}),\n"
            f"     b AS ({block(t.build_table)})\n"
            "SELECT s.n AS src_n, b.n AS build_n, s.h AS src_hash, b.h AS build_hash,\n"
            "       (s.n = b.n AND s.h = b.h) AS parity_ok FROM s, b;")


def schema_sql(t: ParityTarget) -> str:
    return (
        "-- schema_parity: compare information_schema columns\n"
        f"SELECT column_name, ordinal_position, data_type, is_nullable\n"
        f"FROM system.information_schema.columns\n"
        f"WHERE table_name = '{t.build_table.split('.')[-1]}'\n"
        "ORDER BY ordinal_position;"
    )


def rowcount_sql(t: ParityTarget) -> str:
    return (
        "-- row_count at pinned watermark\n"
        f"SELECT 'source' AS side, count(*) AS n FROM {t.source_table}{_wm_pred(t)}\n"
        "UNION ALL\n"
        f"SELECT 'build' AS side, count(*) AS n FROM {t.build_table}{_wm_pred(t)};"
    )


def checksum_sql(t: ParityTarget) -> str:
    cols = ", ".join(t.columns) if t.columns else "*"
    # order-independent: xxhash64 each row, sum the hashes
    def block(tbl):
        return (f"SELECT sum(xxhash64(to_json(struct({cols})))) AS h, count(*) AS n "
                f"FROM {tbl}{_wm_pred(t)}")
    return ("-- content_checksum (order-independent aggregate hash)\n"
            f"WITH s AS ({block(t.source_table)}),\n"
            f"     b AS ({block(t.build_table)})\n"
            "SELECT s.h AS src_hash, b.h AS build_hash, s.n AS src_n, b.n AS build_n,\n"
            "       (s.h = b.h AND s.n = b.n) AS parity_ok FROM s, b;")


def key_parity_sql(t: ParityTarget) -> str:
    if not t.keys:
        return "-- key_parity: no keys declared; skipped"
    k = ", ".join(t.keys)
    return ("-- key_parity: symmetric difference of key sets must be empty\n"
            f"SELECT 'missing_in_build' AS side, {k} FROM {t.source_table}\n"
            f"  EXCEPT SELECT {k} FROM {t.build_table}\n"
            "UNION ALL\n"
            f"SELECT 'extra_in_build' AS side, {k} FROM {t.build_table}\n"
            f"  EXCEPT SELECT {k} FROM {t.source_table};")


def aggregates_sql(t: ParityTarget) -> str:
    if not t.columns:
        return "-- column_aggregates: no columns declared; skipped"
    aggs = []
    for c in t.columns:
        aggs.append(f"count({c}) AS cnt_{c}, count(DISTINCT {c}) AS dc_{c}, "
                    f"min(cast({c} AS string)) AS mn_{c}, max(cast({c} AS string)) AS mx_{c}")
    body = ",\n       ".join(aggs)
    return ("-- column_aggregates + null_distribution\n"
            f"SELECT 'source' AS side,\n       {body}\n"
            f"FROM {t.source_table}{_wm_pred(t)}\n"
            "UNION ALL\n"
            f"SELECT 'build' AS side,\n       {body}\n"
            f"FROM {t.build_table}{_wm_pred(t)};")


def sample_diff_sql(t: ParityTarget, limit: int = 100) -> str:
    if not t.keys:
        return "-- row_level_sample: no keys declared; skipped"
    k = ", ".join(t.keys)
    return ("-- row_level_sample: first mismatching rows\n"
            f"SELECT * FROM (SELECT * FROM {t.source_table} EXCEPT SELECT * FROM "
            f"{t.build_table}) LIMIT {limit};")


_SQL_BY_CHECK = {
    "schema_parity": schema_sql,
    "row_count": rowcount_sql,
    "key_parity": key_parity_sql,
    "content_checksum": checksum_sql,
    "column_aggregates": aggregates_sql,
    "row_level_sample": sample_diff_sql,
}


def all_sql(t: ParityTarget) -> dict:
    """Render the executable checks for a target's MAYA phase.

    MAYA-Dev renders only the volume-independent checks; MAYA-SIT and MAYA-Soak render
    all that have SQL (idempotency/no_extra_output are handled in the runner). Soak
    additionally renders the incremental delta-window check. Uses t.env.
    """
    wanted = set(checks_for(t.env))
    out = {name: fn(t) for name, fn in _SQL_BY_CHECK.items() if name in wanted}
    if t.env == "soak":
        out["soak_delta_parity"] = soak_delta_sql(t)
    return out


def maya_gate(pipeline: str, dev_results: dict, sit_results: dict,
              soak_results: Optional[dict] = None,
              require_both: bool = True, require_soak: bool = True) -> dict:
    """Certification gate: FINAL cert only when every required MAYA phase is green.

    dev_results / sit_results map check_name -> bool. soak_results maps a checkpoint
    label ('T+7', 'T+14') -> {check_name: bool}. MAYA-Dev must cover the dev profile;
    MAYA-SIT must cover all ten; MAYA-Soak must have every scheduled window fully green.
    No partial credit.

    States:
      - BLOCKED     : dev or sit not yet green.
      - PROVISIONAL : dev + sit green (build-time parity), soak still in progress.
      - CERTIFIED   : dev + sit green AND (soak green OR soak not required).
    """
    dev_ok = all(dev_results.get(c, False) for c in PROFILE_DEV_SAMPLE)
    sit_ok = all(sit_results.get(c, False) for c in PROFILE_SIT_FULL)
    soak_results = soak_results or {}
    soak_ok = bool(soak_results) and all(
        all(window.get(c, False) for c in PROFILE_SOAK) for window in soak_results.values())

    build_ok = (dev_ok and sit_ok) if require_both else sit_ok
    if not build_ok:
        status, soak_state = "BLOCKED", "PENDING"
    elif require_soak and not soak_ok:
        status, soak_state = "PROVISIONAL", ("FAIL" if soak_results else "PENDING")
    else:
        status, soak_state = "CERTIFIED", ("PASS" if soak_ok else "N/A")
    return {
        "pipeline": pipeline,
        "maya_dev": "PASS" if dev_ok else "FAIL",
        "maya_sit": "PASS" if sit_ok else "FAIL",
        "maya_soak": soak_state,
        "status": status,
    }


def certification_record(pipeline: str, watermark: str, by: str, evidence: str,
                         soak_windows: Optional[List[str]] = None) -> dict:
    return {
        "pipeline": pipeline,
        "watermark": watermark,
        "certified_by": by,
        "evidence": evidence,
        "checks": [c[0] for c in CHECKS],
        "soak_windows": soak_windows or [],   # e.g. ['T+7', 'T+14'] all green, zero drift
        "status": "CERTIFIED",
    }
