# 16 - Stage 11b: cutover, rollback & day-2 operations

Stage 11 also produces the go-live plan and the day-2 operating model, then runs the
**go/no-go gate** that decides whether the migration can actually be declared complete.

## Cutover plan
`out/enablement/cutover_plan.md` - preconditions (all upstream gates green) and the
sequence: freeze source writes, final incremental load + final MAYA-SIT parity per wave
(topological order), flip orchestration to Databricks jobs, repoint BI/Genie and
consumers, run smoke checks + first live parity (soak T+0), announce go-live with the
source kept in read-only parallel run.

## Rollback plan
`out/enablement/rollback_plan.md` - rollback stays possible until the source is
decommissioned. Triggers (soak drift, Sev-1 at go-live) and steps: re-enable source,
repoint consumers back, quarantine the failing pipeline, fix + re-certify, retry next
window.

## Source decommission checklist
`out/enablement/decommission_checklist.md` - only after a clean parallel-run soak with
zero drift: all pipelines FINAL-certified, consumers confirmed on Databricks, final
snapshot archived + retention set, credentials rotated/revoked and secrets removed,
source schedules disabled and compute deprovisioned, stakeholder sign-off recorded.

## Day-2 operations
`out/enablement/operations.{md,json}` from the `ops:` config block:

- **Monitors** - job success rate, pipeline latency, MAYA parity drift, freshness SLA,
  row-count delta.
- **Alerts** - routed by severity (e.g. job failure -> PagerDuty sev1, parity drift ->
  Slack sev2).
- **Cost governance** - a monthly budget with an alert threshold.
- **Disaster recovery** - RPO/RTO targets and the backup strategy (e.g. Delta deep clone
  to a secondary region).

## The go/no-go gate
Stage 11 PASSes only when every check is green:

- readiness (Stage 0), data certified (Stages 4, 6, 7), BI dev-certified (Stage 5) and BI
  parity + republished (Stage 8), docs generated (Stage 9), identity/security (Stage 10),
  and the enablement artifacts all exist.

On pass it performs the **consolidated docs publish** - data + identity + enablement docs
committed together (local commit offline; push when `agents.publish_remote: true`). Only
then is the migration truly, provably complete - not just the data, but access, people,
and operations.
