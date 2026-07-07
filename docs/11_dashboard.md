# 11 - Live dashboard

The dashboard is the one thing a human watches. It reads Delta control tables the agents
write. DDL: [templates/dashboard_control_tables.sql](../templates/dashboard_control_tables.sql).

## Control tables
| Table | One row per | Key MAYA columns |
|---|---|---|
| job_status | pipeline | status, `maya_dev`, `maya_sit`, `maya_soak`, wave, soak_due_at |
| gate_status | gate crossing | gate G0..G9 (incl. G6_maya_dev, G7_maya_sit, G8_provisional, G9_soak_certified) |
| parity_results | check per table per attempt | `env` (dev/sit/soak), `checkpoint` (build/T+7/T+14), check_name, passed, reason_code |
| soak_status | pipeline per soak checkpoint | checkpoint, due_at, cumulative_ok, delta_ok, drift_rows, passed |
| maya_sample_manifest | dev sampled table | kind, target_rows, actual_rows, seed, sampling |
| connection_smoketest | connection | passed, latency_ms (must be green before a wave builds) |

## Views
- `v_progress` - per wave: total, `dev_passed`, `sit_passed`, provisional, soaking, certified, pct_done.
- `v_drift` - open (red) checks, split by MAYA env (dev logic / sit scale / soak sustained drift).
- `v_maya_funnel` - how many pipelines cleared dev vs sit vs soak vs certified.
- `v_soak_watch` - pipelines in the parallel-run window: days remaining, per-checkpoint cumulative/delta parity and drift.

## What to watch
1. **Connection smoke tests** - all green before building (else G1 blocks the wave).
2. **MAYA funnel** - pipelines should stream through dev, then sit (provisional), then soak, then certified.
3. **Drift** - `v_drift` should trend to empty; a stuck row with exhausted attempts is
   the only thing that needs a human.
4. **Soak watch** - `v_soak_watch` shows provisional pipelines and their T+7/T+14 due
   dates. A soak checkpoint showing `delta_ok = false` is creeping incremental drift and
   needs a human before final certification.

## Reporting
`cli.py report` renders a branded PDF with the coverage funnel, engine catalog, wave
plan, the 10 checks, and the MAYA two-phase + cost-savings section. See
[core/reports.py](../core/reports.py).

## Mission control (the MAYA web application)
The open-source CLI writes the control tables above; the separately delivered **MAYA web
application** turns them into a live command center. Its mission-control view renders all
**twelve lifecycle stages (0-11)** as a progress rail (dev vs prod build/BI phases,
per-stage evidence), a real-time swarm view, and a dependency-graph explorer, alongside an
**Impact/ROI** panel that contrasts a traditional migration's effort with MAYA's measured
performance (see the screenshots in the top-level [README](../README.md)). The web app is
expert-delivered, not self-service.
