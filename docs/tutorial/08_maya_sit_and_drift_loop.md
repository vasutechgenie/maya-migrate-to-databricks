# Part 8 - MAYA-SIT: 10-check parity and the drift loop

> [Index](README.md) | Prev: [Part 7](07_maya_dev_illusion.md) | Next: [Part 9](09_maya_soak_sustained_parity.md)

Once the logic is proven on the sample, prove it at scale: **MAYA-SIT** is full-volume parity
against production-copied data, pinned to a point in time, across ten checks - **no partial
credit**.

## Point-in-time
Both systems are frozen to the same watermark (a load timestamp) so the comparison is like-for-like.

## The ten checks
```bash
python3 cli.py validate --config examples/northwind/northwind.yaml --pipeline nw_build_marts --env sit
```
1. schema parity  2. row count  3. key parity  4. content checksum  5. column aggregates
6. null distribution  7. referential integrity  8. no extra output  9. idempotency
10. row-level sample

The checksum (per-row hash, summed) is order-independent, so identical rows in different physical
order still match, while any single differing value flips the aggregate.

## No partial credit
All ten green, or the table is red. "99.9% match" is a defect with a downstream blast radius.

## The drift loop
A red check starts a disciplined loop:
1. **Run** the checks; note the red.
2. **Localize** to keys/columns (check 10).
3. **Compare logic** source vs. rebuilt at that spot.
4. **Assign a reason code**.
5. **Fix at source**, re-validate; repeat until green.

Reason codes: `TRANSLATION`, `SCHEMA`, `TIMING`, `TYPE-NUANCE`, `SOURCE-CHANGE`, and the only
permitted red - `LEGACY-BUG` (a confirmed source defect, signed off). Everything else must go
green.

## Provisional, not final
MAYA-Dev + MAYA-SIT green earns a **provisional** certification. It is not final, because
point-in-time parity cannot prove the ongoing incremental logic stays equal over time - that is
the soak (Part 9).

## Reference
- Validation framework: [../07_validation_framework.md](../07_validation_framework.md)
- Code: `core/validation.py`

---
Prev: [Part 7](07_maya_dev_illusion.md) | Next: [Part 9 - MAYA-Soak: sustained parity](09_maya_soak_sustained_parity.md)
