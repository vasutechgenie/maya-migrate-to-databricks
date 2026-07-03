# Part 7 - MAYA-Dev: the illusion of production

> [Index](README.md) | Prev: [Part 6](06_reusable_engines.md) | Next: [Part 8](08_maya_sit_and_drift_loop.md)

Proving correctness by re-running the new pipeline on full production volume through every fix is
where validation budgets die. MAYA proves the **logic** on a small **illusion of production**
first, cheaply, then proves scale once.

## Why naive sampling fails
`LIMIT 10000` on each table independently breaks joins: sampled order rows reference customers
not in the sample, and joins silently drop rows. Sampling must **preserve referential
integrity**.

## RI-preserving sampling
1. Deterministic seed sample of each table (ordered by key, hashed with a fixed seed).
2. **FK closure** - pull in parent rows referenced by sampled children so joins resolve.
3. Reference/config tables copied whole.

```bash
python3 cli.py maya sample --config examples/northwind/northwind.yaml --pipeline nw_build_sales
# maya sample: 5 tables across 1 pipeline(s) -> out/maya_sample.sql, out/maya_sample_manifest.csv
```
The pipeline's five bronze prerequisites become five sample specs. `src.orders` and
`src.order_lines` carry larger budgets (`sample_overrides`) so the fact grain is exercised.

## Determinism is a feature
The seed is fixed (42), so the dev sample is reproducible run to run - which is what makes the
idempotency check meaningful. The manifest records exactly what dev should contain.

## What MAYA-Dev proves (and defers)
Only volume-independent checks: schema parity, key parity, referential integrity, no-extra-output,
idempotency, and a row-level sample diff. Row counts, checksums, and aggregates at full volume are
**deferred to SIT**. Render the dev plan with:
```bash
python3 cli.py validate --config examples/northwind/northwind.yaml --pipeline nw_build_sales --env dev
```

## The economics
The many drift-loop iterations happen on a few thousand rows; full-volume compute is incurred once,
later, when the logic is already correct.

## Reference
- MAYA validation: [../08_maya_two_phase_validation.md](../08_maya_two_phase_validation.md)
- Code: `core/maya.py`

---
Prev: [Part 6](06_reusable_engines.md) | Next: [Part 8 - MAYA-SIT and the drift loop](08_maya_sit_and_drift_loop.md)
