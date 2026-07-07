# 15 - Stage 11a: enablement & training

The last mile of a migration is people, not pipelines. A technically perfect cutover
fails if engineers do not know how to operate the new platform, analysts cannot find the
migrated marts, and stewards have no process for access reviews. Stage 11 generates the
enablement material as a first-class, gated artifact.

## Role-based training packs
`python3 cli.py enablement --config <project>.yaml` (or `make stage11`) writes a training
pack per audience under `out/enablement/training/`:

- **Data engineers** - building/operating pipelines with the shared engines, proving
  every change with MAYA parity (dev -> SIT -> soak) before certifying.
- **BI analysts** - pointing BI + Genie/AI-BI at the migrated gold/serving marts; how
  masking affects them; the drift-reporting process.
- **Data stewards** - owning grants, running access reviews, maintaining classification
  and the glossary.
- **Platform operations** - monitors, alerts, incidents, cost, and DR.

Audiences default to those four; override with the `enablement.audiences` config block.

## Runbooks
Operational runbooks under `out/enablement/runbooks/`:

- **Daily operations** - confirm jobs, review parity/soak monitors, triage.
- **Incident response** - acknowledge, locate the failing pipeline in the graph, roll
  back to the last certified snapshot, re-run and re-prove parity.
- **Backfill / reprocessing** - run in wave order, re-prove parity, update watermarks.

## Why it is gated
Stage 11's go/no-go gate requires the enablement artifacts to exist alongside every green
upstream gate 0-10 (see [16_cutover_rollback_operations.md](16_cutover_rollback_operations.md)).
Training is not a nice-to-have slide deck produced after go-live; it is a precondition for
declaring the migration complete, and it is published with the rest of the docs.
