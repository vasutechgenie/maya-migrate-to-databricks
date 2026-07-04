# Changelog

All notable changes to MAYA are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
