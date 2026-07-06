# Changelog

All notable changes to MAYA are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-07-05

The **BI layer becomes two-phase**, mirroring the pipeline dev/prod split. The flow grows
from eleven to **twelve stages (0-11)** by inserting a BI convert + dev-certify stage right
after the dev build (while the sample gold still exists), and moving BI parity + publish to
run after the prod build against the full-load gold. The **same converted BI queries** are
used in both phases.

### Changed
- **Twelve-stage model (0-11).** New sequence: 0 readiness, 1 collect+score,
  2 replicate (dev), 3 specs, 4 build+certify (dev), **5 BI convert + dev-certify (dev)**
  [new, route `bidev`], 6 full load + historical (prod), 7 build+certify (prod),
  **8 BI parity + publish (prod)** (was 7 `bi`), 9 docs+publish, 10 identity+security+
  governance, 11 enablement+go-live. Stages 6-11 are the former 5-10, renumbered.
- **One BI, two phases.** `core/bi.run(cfg, phase=...)` splits into `_run_dev` (convert +
  dev-certify clean on the sample gold; sets `dev_certified`, writes
  `stage5_bi_dev_gate.json`; no source parity/republish/Genie) and `_run_prod` (parity vs
  source on the full gold, then republish + Genie/Lakeview; writes `stage5_bi_gate.json`).
  `core/execution/live.stage5_bi(queries, phase=...)` and `server/live.bi_parity(ctx,
  phase=...)` are phase-aware; the runner dispatches stage 5 as dev BI and stage 8 as prod
  BI. Because pipeline gold lands in the same `dev_schema` in both build phases, BI dev runs
  between the dev build and the full load so the sample gold is still present.
- `cert_phase` now flips to `prod` at stage 6 (full load) instead of 5.

### Added
- `BIObject.dev_certified` column + alembic migration `0006_bi_dev_certified`.
- Frontend: shared `BIView({ n, phase })`; new `Stage5BIDev` (route `bidev`, hides
  parity/republish/Genie); prod BI page renumbered to stage 8. Sidebar/dashboard render all
  twelve stages.

## [0.3.0] - 2026-07-05

Dev and prod certification become **distinct lifecycle stages** instead of a runtime
toggle. The flow grows from nine to **eleven stages (0-10)** by inserting a prod
full-load and a prod build+certify after the dev build, and both build phases run the
**same pipeline code** from one source of truth.

### Changed
- **Eleven-stage model (0-10).** New sequence: 0 readiness, 1 collect+score,
  2 replicate (dev / RI ~10k sample), 3 specs, 4 build+certify (dev / sample),
  **5 full load + historical (prod)** [new], **6 build+certify (prod / 100% parity)**
  [new], 7 BI, 8 docs+publish, 9 identity+security+governance, 10 enablement+go-live.
  Stages 7-10 are the former 5-8, renumbered.
- **One code, two phases.** `server/live.py` `live_context(db, project, phase=...)` now
  selects the dev vs prod workspace and data volume by phase (driven by the stage, not a
  global `data_mode` toggle). The dev build (stage 4) and prod certify (stage 6) load the
  identical `source/pipelines.json`; any prod fix-loop repair is persisted back to that
  single source of truth so dev and prod never diverge.
- `cert_phase` is now derived from stage progress (reaching stage 5 = prod) rather than
  the `data_mode` toggle. `/connections/projects/{id}/promote` is kept for API
  back-compat but is no longer required.
- Frontend: shared `ReplicateView` and `BuildCertifyView` components back both phases;
  new `Stage5FullLoad` (route `fullload`) and `Stage6CertifyProd` (route `certify`)
  pages; sidebar, dashboard rail, and swarm render all eleven stages.

## [0.2.0] - 2026-07-04

Full-lifecycle coverage: MAYA grows from six data-focused stages to a **nine-stage**
flow that also gates identity, security, governance, enablement, cutover, and day-2
operations. Stages 1-6 are unchanged; Stage 0 and Stages 7-8 are additive.

### Added
- **Stage 0 - readiness** (`core/readiness.py`, `cli.py readiness`, `make stage0`):
  collects the non-data estate (users/groups/roles/service principals, the grant matrix,
  the secret inventory, per-column data classification, and security-posture facts) and
  applies a completeness + consistency gate -> `out/stage0_gate.json`.
- **Stage 7 - identity, security & governance** (`core/identity.py`, `cli.py identity`,
  `make stage7`): deterministically authors the Unity Catalog security model - group/SP
  identity, the source grant matrix mapped **1:1** to UC grants, column-mask functions +
  `SET MASK`, row-filter functions + `SET ROW FILTER`, secret scopes, and schema
  owners/tags/glossary. Access-parity gate -> `out/stage7_identity.sql` +
  `out/stage7_gate.json`.
- **Stage 8 - enablement & go-live** (`core/enablement.py`, `cli.py enablement`,
  `make stage8`): role-based training packs, operational runbooks, cutover/rollback plans,
  a source-decommission checklist, and day-2 operations (monitors, alerts, cost budget,
  DR). Runs a **go/no-go gate** over every upstream gate, then performs the consolidated
  docs publish (data + identity + enablement) -> `out/stage8_gate.json`.
- Adapter Stage-0 hooks on `SourceAdapter` with safe defaults: `export_principals`,
  `export_grants`, `export_secrets`, `classify_data`, `export_security_facts`; implemented
  in the reference Synapse adapter.
- Northwind synthetic security artifacts under
  `examples/northwind/artifacts/security/` (`principals.csv`, `grants.csv`, `secrets.csv`,
  `classification.csv`, `security_facts.json`) and new `security`/`governance`/
  `enablement`/`ops` config sections in `northwind.yaml`.
- Documentation: `docs/00_readiness.md`, `docs/14_identity_security_governance.md`,
  `docs/15_enablement_training.md`, `docs/16_cutover_rollback_operations.md`, cross-linked
  from Phase 0; README gains a nine-stage narrative and a **Full-lifecycle coverage**
  matrix.
- Tests: `tests/test_stages.py` extended to stages 0-8 (`last_passed == 8`) with Stage 0/7/8
  gate tests and a negative Stage-0 gate test.

### Changed
- `core/config.py` adds free-form `security`, `governance`, `enablement`, and `ops`
  sections.
- Orchestrator (`core/stages.py`) now spans stages 0-8; `last_passed` initializes to `-1`
  and `cli.py run --stage` accepts `0..8`. Makefile targets/help updated for nine stages.

## [0.1.0] - 2026-07-03

Initial public release of MAYA - a deterministic, source-agnostic accelerator for
migrating data platforms to Databricks.

### Added
- Six-stage flow: collect + score, replicate, specs, build + certify, BI, docs + publish,
  driven by `cli.py run --stage N|all` and the `Makefile`.
- Source-agnostic core (graph, order, contract, engines, validation, MAYA two-phase +
  sustained-soak parity, BI migration, branded reports) with a reference Synapse adapter.
- AI agent swarm with pluggable drivers: deterministic `offline` (default) and `cursor`
  (Cursor SDK) backends.
- The runnable Northwind synthetic demo, methodology + tutorial docs, the "Migrating with
  MAYA" blog series, and a deterministic pytest golden suite.

[0.2.0]: https://github.com/vasutechgenie/maya-migrate-to-databricks/releases/tag/v0.2.0
[0.1.0]: https://github.com/vasutechgenie/maya-migrate-to-databricks/releases/tag/v0.1.0
