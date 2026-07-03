# Part 9 - MAYA-Soak: sustained parity, zero drift

> [Index](README.md) | Prev: [Part 8](08_maya_sit_and_drift_loop.md) | Next: [Part 10](10_dashboard_bi_and_cutover.md)

Point-in-time parity proves **state** - identical at one frozen moment. It cannot prove the
**ongoing incremental logic** matches. Merge/CDC/SCD/late-data differences accumulate load after
load and surface days later as a production incident. **MAYA-Soak** is the phase that catches them.

## Keep both systems running
After a pipeline is **provisionally** certified (Dev + SIT green), both systems run in parallel and
MAYA re-proves parity at scheduled checkpoints - by default **T+7 and T+14 days**. Final
certification requires every soak window green with **zero drift**.
```bash
python3 cli.py validate --config examples/northwind/northwind.yaml --pipeline nw_build_marts --env soak
```

## Cumulative AND delta
Each checkpoint runs all ten checks twice: on the **cumulative** table and on the **incremental
delta** (rows loaded since the previous checkpoint, `prev_watermark < load_dt <= now`). A broken
incremental step can be masked by the cumulative comparison (a full recompute self-corrects the
total); the delta window cannot be fooled. MAYA renders a dedicated `soak_delta_parity` check for it.

## New reason codes
- **INCREMENTAL-LOGIC** - merge/CDC/SCD/upsert logic diverges over runs. Fix the step, re-backfill
  the window, re-soak.
- **LATE-DATA** - late/out-of-order rows handled differently over time. Align late-data + watermark
  handling, re-soak.

## The three-state gate
- **BLOCKED** - Dev or SIT not yet green.
- **PROVISIONAL** - Dev + SIT green, soak in progress.
- **CERTIFIED** - Dev + SIT green **and** every soak window green (or soak not required).

The gate is encoded in `validation.maya_gate` and the `tests/` assert each transition, so the rule
cannot silently rot.

## Why it is the differentiator
Most tooling stops at point-in-time parity. MAYA treats a migration as correct only when it has
been *sustainedly* correct across real production loads.

## Reference
- MAYA validation (soak section): [../08_maya_two_phase_validation.md](../08_maya_two_phase_validation.md)
- Code: `core/validation.py` (`soak_delta_sql`, `maya_gate`)

---
Prev: [Part 8](08_maya_sit_and_drift_loop.md) | Next: [Part 10 - Dashboard, BI/Genie, cutover](10_dashboard_bi_and_cutover.md)
