# Migrating with MAYA - a hands-on field guide

This tutorial walks the entire MAYA workflow end to end on the bundled **Northwind** demo
(a fictional retailer moving Azure Synapse -> Databricks). Every part maps to a real
command you can run right now and to a deeper reference doc. It is the durable, versioned
companion to the "Migrating with MAYA" article series.

## Before you start
```bash
git clone https://github.com/srinivasnelakuditi/maya-migrate
cd maya-migrate
pip install -r requirements.txt
make demo        # runs everything below in one shot
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
| 10 | [Dashboard, BI/Genie, cutover, and your estate](10_dashboard_bi_and_cutover.md) | `cli.py bi ...` / `report` | [dashboard](../11_dashboard.md), [BI](../13_bi_layer_migration.md), [execution](../10_execution_plan.md) |

Each part is self-contained but they read best in order. By the end you will have taken
Northwind from raw source metadata to a certified, dashboarded Databricks build - and you
will know exactly how to point MAYA at your own estate.

Created by **Srinivas Nelakuditi**.
