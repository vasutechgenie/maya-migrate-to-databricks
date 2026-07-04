# Migrating with MAYA - a hands-on field guide

This tutorial walks the entire MAYA workflow end to end on the bundled **Northwind** demo
(a fictional retailer moving Azure Synapse -> Databricks). Every part maps to a real
command you can run right now and to a deeper reference doc. It is the durable, versioned
companion to the "Migrating with MAYA" article series.

The arc: MAYA first **previews** the migration (graph -> order -> contract -> report,
nothing built yet), then a **swarm of AI coding agents builds the real pipelines** wave by
wave, each self-validating through MAYA-Dev -> MAYA-SIT -> MAYA-Soak, and finally a
**whole-system certification** (`maya certify`) declares the migration complete.

Operationally this arc runs as **six gated stages** (see
[methodology](../01_methodology.md)): **1** collect + score, **2** replicate the estate
into a test catalog with referential-integrity synthetic data, **3** one spec PDF per
pipeline, **4** conformance -> agent-swarm build -> strict topological certification,
**5** BI end to end, **6** generated docs + publish. `make demo` runs all six with the
deterministic **offline** agent driver, so the whole tutorial is reproducible without any
external services; the parts below zoom into each primitive the stages call.

## Before you start
```bash
git clone https://github.com/vasutechgenie/maya-migrate-to-databricks
cd maya-migrate-to-databricks
pip install -r requirements.txt
make demo        # runs the six-stage flow end to end (offline)
# or: python3 cli.py run --stage all --config examples/northwind/northwind.yaml
```

## The parts
| # | Part | You run | Reference |
|---|---|---|---|
| 01 | [Meet MAYA and Northwind](01_meet_maya_and_northwind.md) | `make demo` | [methodology](../01_methodology.md) |
| 02 | [The adapter model: reading any source](02_the_adapter_model.md) | `cli.py graph` | [phase-0](../02_phase0_prereqs.md), [adapters](../12_adapter_authoring_guide.md) |
| 03 | [Building the dependency graph](03_the_dependency_graph.md) | `cli.py graph` | [graph & lineage](../03_graph_and_lineage.md) |
| 04 | [Build order, waves, and the independent verifier](04_build_order_and_verifier.md) | `cli.py order` / `verify` | [build order](../04_build_order.md) |
| 05 | [The deterministic pipeline contract](05_the_pipeline_contract.md) | `cli.py context` | [contract](../05_pipeline_contract.md) |
| 06 | [Reusable engines E1-E7, SQL-first](06_reusable_engines.md) | (read contracts) | [engines](../06_engines.md) |
| 07 | [MAYA-Dev: the illusion of production](07_maya_dev_illusion.md) | `cli.py maya sample` | [MAYA validation](../08_maya_two_phase_validation.md) |
| 08 | [MAYA-SIT: 10-check parity and the drift loop](08_maya_sit_and_drift_loop.md) | `cli.py validate --env sit` | [validation framework](../07_validation_framework.md) |
| 09 | [MAYA-Soak: sustained parity, zero drift](09_maya_soak_sustained_parity.md) | `cli.py validate --env soak` | [MAYA validation](../08_maya_two_phase_validation.md) |
| 10 | [Dashboard, BI/Genie, cutover, and your estate](10_dashboard_bi_and_cutover.md) | `cli.py bi ...` / `certify` / `report` | [dashboard](../11_dashboard.md), [BI](../13_bi_layer_migration.md), [execution](../10_execution_plan.md) |

Parts 06-09 are where the **AI agent swarm** builds and self-validates the real pipelines
(`cli.py build` drives Stage 4 - conformance, wave-by-wave build, strict topological
certification; `cli.py orchestrate` inspects the per-wave work queue); Part 10 closes the
loop with the **whole-system certification** (`cli.py certify`) that marks the migration
complete.

Each part is self-contained but they read best in order. By the end you will have taken
Northwind from raw source metadata to a certified, dashboarded Databricks build - and you
will know exactly how to point MAYA at your own estate.

Created by **Srinivas Nelakuditi**.
