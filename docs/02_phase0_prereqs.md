# 02 - Phase 0 prerequisites

Phase 0 is off the clock but mandatory. When it is truly complete, the autonomous run
is short. Nothing in Phase 0 is owned by the build agents; it is platform + data setup.

## Checklist
1. **Workspaces** - Databricks dev, SIT, (QA), prod workspaces with Unity Catalog and
   the catalogs MAYA expects: `<project>_dev`, `<project>_sit`, plus reference schemas
   `<project>_dev_ref` / `<project>_sit_ref` for parity sources.
2. **Connections proven** - every connection in the connection inventory has a
   **smoke test** that returns green before any wave builds. Connections are set up by
   the platform/source team; MAYA's job is to prove they work, not to create them. See
   [11_dashboard.md](11_dashboard.md) (`connection_smoketest`).
3. **MAYA dev sample** - the dev workspace holds every customer table sampled to a few
   thousand rows (the "illusion of prod"). Either the source team lands it, or MAYA
   builds it with `cli.py maya sample` (RI-preserving). See
   [08_maya_two_phase_validation.md](08_maya_two_phase_validation.md).
4. **SIT prod copy** - SIT has production-copied data (full volume) for scale parity.
5. **Federation / source access** - read access to the legacy source for parity and
   backfill (Lakehouse Federation or a copied reference).
6. **Legacy code access** - all source code available for the drift loop to inspect
   both sides.
7. **Serverless** - serverless SQL warehouses + serverless jobs enabled so dev
   iterations and SIT runs start instantly (big lever for the sub-week timeline).
8. **Dashboard** - control tables + DBSQL dashboard deployed
   ([templates/dashboard_control_tables.sql](../templates/dashboard_control_tables.sql)).

## Ownership
| Prereq | Owner |
|---|---|
| Workspaces, catalogs, serverless | Platform team |
| Connections (create) | Source/platform team |
| Connections (prove) | MAYA (smoke test) |
| Dev sample data | Source team lands it, or MAYA builds it |
| SIT prod copy | Data/platform team |
| Legacy code access | Migration lead |

Only when connections are green and both data tiers exist does the autonomous build
begin.

## Beyond the data estate
Phase 0 above is *platform* setup. The **non-data** estate - identity, access, secrets,
data classification, and governance - is collected and gated separately in **Stage 0**
([00_readiness.md](00_readiness.md)), applied to Unity Catalog in **Stage 7**
([14_identity_security_governance.md](14_identity_security_governance.md)), and finished
with enablement, cutover/rollback, and day-2 operations in **Stage 8**
([15_enablement_training.md](15_enablement_training.md),
[16_cutover_rollback_operations.md](16_cutover_rollback_operations.md)).
