# 01 - MAYA methodology

MAYA turns a legacy-to-Databricks migration into a deterministic, mostly-autonomous
pipeline. The phases below take an estate from raw source artifacts to a
prod-certified Databricks lakehouse, with the MAYA two-phase validation technique
making the validation step cheap and the sustained soak making certification durable.

```mermaid
flowchart TD
  p0["Phase 0: prereqs (workspaces, connections proven, MAYA dev sample, SIT prod copy)"]
  p1["Phase 1: collect source artifacts"]
  p2["Phase 2: parse -> normalized graph"]
  p3["Phase 3: build order (waves) + verify"]
  p4["Phase 4: per-pipeline contract + report (the PREVIEW)"]
  p5["Phase 5: AI agent swarm BUILDS the real pipelines (engines E1-E7, SQL-first)"]
  p6["Phase 6: MAYA validate (dev sample -> SIT scale) + drift loop"]
  p7["Phase 7: provisional-certify wave, advance; live dashboard"]
  p8["Phase 8: MAYA-Soak (parallel run, T+7/T+14) -> final certify"]
  p9["Phase 9: BI layer migration (dashboards + Genie AI/BI)"]
  p10["Phase 10: whole-system certification -> MIGRATION COMPLETE"]
  p0 --> p1 --> p2 --> p3 --> p4 --> p5 --> p6 --> p7 --> p8 --> p9 --> p10
  p7 -->|"next wave"| p5
```

The first four phases are **preview**: MAYA reads the estate and, without building
anything, produces the plan a human can review - the graph, the verified wave order, a
per-pipeline contract, and a branded PDF report. The build only starts in Phase 5, when a
**swarm of AI coding agents** turns those contracts into the real Databricks pipelines,
wave by wave, each one self-validating through MAYA before the wave advances. The run ends
only when **every** pipeline (and its BI) is certified - a single whole-system verdict.

## The phases
1. **Collect** - the adapter gathers all source artifacts (code, procs, schedules,
   configs, DDL). See [12_adapter_authoring_guide.md](12_adapter_authoring_guide.md).
2. **Parse** - the adapter emits the normalized graph (`objects.csv` / `edges.csv`).
   Everything downstream is source-agnostic. See [03_graph_and_lineage.md](03_graph_and_lineage.md).
3. **Order** - topologically sort tables and pipelines into waves; verify with an
   independent validator. See [04_build_order.md](04_build_order.md).
4. **Contract + report (preview)** - derive a deterministic needs/logic/output contract
   per pipeline and render the branded PDF report. This is a *preview* of the whole
   migration - nothing is built yet; a human can review the plan before a single line of
   code is written. See [05_pipeline_contract.md](05_pipeline_contract.md).
5. **Build (AI agent swarm)** - a pool of coding agents drains the wave queue in parallel
   and implements the **real** pipelines with the reusable engines E1-E7, SQL-first -
   translating the actual source logic, never inventing. See [06_engines.md](06_engines.md)
   and [09_agent_orchestration.md](09_agent_orchestration.md).
6. **Validate (MAYA)** - each agent proves its pipeline's logic cheaply on the sampled dev
   illusion, then proves parity at scale on prod-copied SIT data; drift-loop until green.
   See [07_validation_framework.md](07_validation_framework.md) and
   [08_maya_two_phase_validation.md](08_maya_two_phase_validation.md).
7. **Provisionally certify + advance** - a wave advances only when every pipeline in it is
   provisionally certified (MAYA-Dev AND MAYA-SIT green). Then agents start the next wave.
   See [10_execution_plan.md](10_execution_plan.md).
8. **Soak + finally certify** - each pipeline runs in parallel with the source and
   re-proves parity at T+7 and T+14 (cumulative + incremental delta) with zero drift
   before final certification. Point-in-time parity proves state; the soak proves the
   ongoing incremental logic. See
   [08_maya_two_phase_validation.md](08_maya_two_phase_validation.md).
9. **BI layer migration** - once the gold tables are certified, agents migrate the
   dashboards (Looker/Tableau/Power BI) over MCP/API: extract queries, AI-convert to
   Databricks, prove result-for-result parity, republish, and replicate as Lakeview +
   Genie for AI/BI. See [13_bi_layer_migration.md](13_bi_layer_migration.md).
10. **Whole-system certification** - the migration is not "done" until **every** pipeline
    is FINAL-certified (dev + sit + soak, zero drift) and every BI object is migrated.
    `maya certify` rolls all per-pipeline gates and BI across all waves into one system
    state - `MIGRATION_IN_PROGRESS` -> `SYSTEM_PROVISIONAL` -> `MIGRATION_COMPLETE` - and
    only `MIGRATION_COMPLETE` clears the source for retirement. See
    [09_agent_orchestration.md](09_agent_orchestration.md) and
    [10_execution_plan.md](10_execution_plan.md).

## What makes it fast
- Determinism (nothing guessed), reusable engines (config + SQL, not bespoke code),
  an autonomous agent pool ([09_agent_orchestration.md](09_agent_orchestration.md)),
  and MAYA's cheap-first validation. A live dashboard
  ([11_dashboard.md](11_dashboard.md)) is the only thing a human watches.
