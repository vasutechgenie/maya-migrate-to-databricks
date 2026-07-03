-- MAYA - Migration Accelerator - control tables for the live migration dashboard.
-- Delta tables in a dedicated control schema; the agents write, DBSQL reads.
-- Everything is MAYA-aware: parity + gates carry an env dimension (dev sample vs
-- sit full-scale vs sustained soak). Build-time parity yields PROVISIONAL cert; the
-- FINAL certification gate additionally requires every soak window green (zero drift).

CREATE SCHEMA IF NOT EXISTS mig_control;

-- one row per pipeline (build unit)
CREATE TABLE IF NOT EXISTS mig_control.job_status (
  pipeline        STRING,
  wave            INT,
  kind            STRING,          -- medallion / orchestration / external_invoke / utility
  engine          STRING,          -- E1..E7
  status          STRING,          -- PENDING / BUILDING / MAYA_DEV / MAYA_SIT / DRIFT / PROVISIONAL / SOAKING / CERTIFIED / BLOCKED
  maya_dev        STRING,          -- PENDING / PASS / FAIL  (logic proof on sample)
  maya_sit        STRING,          -- PENDING / PASS / FAIL  (scale proof on prod copy, point-in-time)
  maya_soak       STRING,          -- PENDING / PASS / FAIL  (sustained parity T+7, T+14, zero drift)
  agent_id        STRING,
  started_at      TIMESTAMP,
  provisional_at  TIMESTAMP,       -- build-time parity green (dev + sit)
  soak_started_at TIMESTAMP,       -- parallel-run soak clock starts here
  soak_due_at     TIMESTAMP,       -- last scheduled soak checkpoint (e.g. T+14)
  certified_at    TIMESTAMP,       -- FINAL cert: soak windows all green
  attempts        INT,
  updated_at      TIMESTAMP
) USING DELTA;

-- one row per gate crossing (G0..G9) per pipeline
CREATE TABLE IF NOT EXISTS mig_control.gate_status (
  pipeline        STRING,
  gate            STRING,          -- G0_contract .. G6_maya_dev, G7_maya_sit, G8_provisional, G9_soak_certified
  passed          BOOLEAN,
  detail          STRING,
  recorded_at     TIMESTAMP
) USING DELTA;

-- one row per parity check per table per attempt PER MAYA ENV
CREATE TABLE IF NOT EXISTS mig_control.parity_results (
  pipeline        STRING,
  env             STRING,          -- 'dev' (sample) / 'sit' (full-scale) / 'soak' (sustained)
  checkpoint      STRING,          -- 'build' (sit) or 'T+7' / 'T+14' (soak windows)
  table_name      STRING,
  check_name      STRING,          -- schema_parity, row_count, ..., soak_delta_parity
  watermark       STRING,          -- pinned point-in-time (SIT + each soak checkpoint)
  passed          BOOLEAN,
  src_value       STRING,
  build_value     STRING,
  reason_code     STRING,          -- TRANSLATION / ... / INCREMENTAL-LOGIC / LATE-DATA / LEGACY-BUG
  attempt         INT,
  recorded_at     TIMESTAMP
) USING DELTA;

-- one row per pipeline per soak checkpoint (the sustained parallel-run watch)
CREATE TABLE IF NOT EXISTS mig_control.soak_status (
  pipeline        STRING,
  checkpoint      STRING,          -- 'T+7' / 'T+14'
  due_at          TIMESTAMP,       -- when this checkpoint should run
  ran_at          TIMESTAMP,       -- when it actually ran
  cumulative_ok   BOOLEAN,         -- full-table parity still green
  delta_ok        BOOLEAN,         -- incremental window (rows since prev checkpoint) parity green
  drift_rows      BIGINT,          -- rows that diverged in this window (0 = certified)
  reason_code     STRING,          -- INCREMENTAL-LOGIC / LATE-DATA / ... when not green
  passed          BOOLEAN,
  recorded_at     TIMESTAMP
) USING DELTA;

-- MAYA dev sampling manifest: what the dev "illusion of prod" should contain
CREATE TABLE IF NOT EXISTS mig_control.maya_sample_manifest (
  table_name      STRING,
  kind            STRING,          -- sample / reference_full
  target_rows     STRING,          -- integer or 'all'
  actual_rows     BIGINT,
  keys            STRING,
  seed            INT,
  sampling        STRING,          -- ri_preserving / random / none
  built_at        TIMESTAMP
) USING DELTA;

-- one row per connection smoke test (must be green before a wave can build)
CREATE TABLE IF NOT EXISTS mig_control.connection_smoketest (
  connection      STRING,
  category        STRING,
  passed          BOOLEAN,
  latency_ms      INT,
  detail          STRING,
  recorded_at     TIMESTAMP
) USING DELTA;

-- ---- BI layer migration ---------------------------------------------------
-- one row per query-bearing BI object (Looker/Tableau/Power BI)
CREATE TABLE IF NOT EXISTS mig_control.bi_object_status (
  obj_id          STRING,
  system          STRING,          -- looker / tableau / powerbi
  dashboard       STRING,
  tile            STRING,
  state           STRING,          -- EXTRACTED / CONVERTED / PARITY / REPUBLISHED / GENIE / DONE
  parity_passed   BOOLEAN,
  republished     BOOLEAN,
  genie_created   BOOLEAN,
  agent_id        STRING,
  attempts        INT,
  updated_at      TIMESTAMP
) USING DELTA;

-- one row per BI query-result parity check per attempt
CREATE TABLE IF NOT EXISTS mig_control.bi_parity_results (
  obj_id          STRING,
  check_name      STRING,          -- result_schema / result_rowcount / result_set_equality / result_checksum / result_order
  passed          BOOLEAN,
  orig_value      STRING,
  new_value       STRING,
  reason_code     STRING,
  attempt         INT,
  recorded_at     TIMESTAMP
) USING DELTA;

-- ---- dashboard views ------------------------------------------------------
CREATE OR REPLACE VIEW mig_control.v_progress AS
SELECT wave,
       count(*)                                                AS total,
       sum(CASE WHEN maya_dev = 'PASS' THEN 1 ELSE 0 END)      AS dev_passed,
       sum(CASE WHEN maya_sit = 'PASS' THEN 1 ELSE 0 END)      AS sit_passed,
       sum(CASE WHEN status = 'PROVISIONAL' THEN 1 ELSE 0 END) AS provisional,
       sum(CASE WHEN status = 'SOAKING' THEN 1 ELSE 0 END)     AS soaking,
       sum(CASE WHEN status = 'CERTIFIED' THEN 1 ELSE 0 END)   AS certified,
       round(100.0 * sum(CASE WHEN status = 'CERTIFIED' THEN 1 ELSE 0 END)
             / count(*), 1)                                    AS pct_done
FROM mig_control.job_status
GROUP BY wave ORDER BY wave;

-- open drift, split by MAYA phase (dev logic / sit scale / soak sustained drift)
CREATE OR REPLACE VIEW mig_control.v_drift AS
SELECT pipeline, env, checkpoint, table_name, check_name, reason_code,
       src_value, build_value, attempt, recorded_at
FROM mig_control.parity_results
WHERE passed = false
ORDER BY recorded_at DESC;

-- MAYA phase funnel: how many pipelines cleared dev vs sit vs soak
CREATE OR REPLACE VIEW mig_control.v_maya_funnel AS
SELECT
  count(*)                                                 AS pipelines,
  sum(CASE WHEN maya_dev = 'PASS' THEN 1 ELSE 0 END)       AS cleared_dev,
  sum(CASE WHEN maya_sit = 'PASS' THEN 1 ELSE 0 END)       AS cleared_sit,
  sum(CASE WHEN status = 'PROVISIONAL' THEN 1 ELSE 0 END)  AS provisional,
  sum(CASE WHEN maya_soak = 'PASS' THEN 1 ELSE 0 END)      AS cleared_soak,
  sum(CASE WHEN status = 'CERTIFIED' THEN 1 ELSE 0 END)    AS certified
FROM mig_control.job_status;

-- soak watch: pipelines in the sustained parallel-run window, with days remaining and
-- any drift that must be root-caused before FINAL certification
CREATE OR REPLACE VIEW mig_control.v_soak_watch AS
SELECT j.pipeline, j.wave, j.maya_sit, j.maya_soak,
       j.soak_started_at, j.soak_due_at,
       datediff(j.soak_due_at, current_timestamp())        AS days_remaining,
       s.checkpoint, s.due_at, s.ran_at,
       s.cumulative_ok, s.delta_ok, s.drift_rows, s.reason_code, s.passed
FROM mig_control.job_status j
LEFT JOIN mig_control.soak_status s USING (pipeline)
WHERE j.status IN ('PROVISIONAL', 'SOAKING')
ORDER BY j.soak_due_at, j.pipeline, s.checkpoint;

-- BI migration progress: extract -> convert -> parity -> republish -> genie
CREATE OR REPLACE VIEW mig_control.v_bi_progress AS
SELECT system,
       count(*)                                              AS objects,
       sum(CASE WHEN parity_passed THEN 1 ELSE 0 END)        AS parity_green,
       sum(CASE WHEN republished THEN 1 ELSE 0 END)          AS republished,
       sum(CASE WHEN genie_created THEN 1 ELSE 0 END)        AS genie_created,
       sum(CASE WHEN state = 'DONE' THEN 1 ELSE 0 END)       AS done
FROM mig_control.bi_object_status
GROUP BY system ORDER BY system;
