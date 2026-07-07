# 10 - Execution plan and gates

Each pipeline crosses a fixed sequence of gates. A pipeline is a build unit; a wave is a
barrier. MAYA adds the validation gates (G6-G9): G6/G7 make build-time certification
cheap, and G9 (soak) makes it durable.

## Stage gates (the twelve-stage flow)

Above the per-pipeline gates below, MAYA runs twelve **stage** gates (0-11) end to end.
Each writes a gate JSON under `out/`; the orchestrator (`core/stages.py`, `maya run`)
refuses to advance past a failed one and records progress in `out/stage_state.json`. The
data + BI layers migrate across two explicit phases with the **same code**: a **dev** phase
on a ~10k RI sample (build+certify at 4, BI convert + dev-certify at 5) and a **prod** phase
on the full/historical load (full load at 6, build+certify at 7, BI parity + publish at 8).

| Stage gate | Passes when | Artifact |
|---|---|---|
| 0 readiness | identity/access/secrets/classification collected + consistent | `stage0_gate.json` |
| 1 collect + score | every pipeline 100% traversable, all tables/views identified, all externals tagged, order verifies | `stage1_gate.json`, `discovery_score.csv` |
| 2 replicate (dev) | every table AND view present in `maya.test_catalog` (RI-preserving ~10k fill) | `stage2_gate.json`, `stage2_replicate.sql` |
| 3 specs | one spec PDF per pipeline | `stage3_gate.json`, `specs_pdf/` |
| 4a conformance | order+waves valid AND every spec PDF conforms to its wave | `stage4_conformance.json` |
| 4b build (dev) | every pipeline authored + MAYA-Dev green on the synthetic sample | `stage4_build.json` |
| 4c certify (dev) | every pipeline CERTIFIED on the sample, in topological order | `gates.json`, `stage4_certify.json` |
| 5 BI convert + dev-certify (dev) | every BI object converted + runs clean on the sample gold (no parity/republish/Genie yet) | `stage5_bi_dev_gate.json` |
| 6 full load + historical (prod) | the full/historical source backfilled for every pipeline (reuses the replicate step, prod phase) | `stage2_replicate.sql`, `stage_state.json` |
| 7 build + certify (prod) | the SAME code CERTIFIED to 100% parity on real data, in topological order | `gates.json` |
| 8 BI parity + publish (prod) | every BI object DONE (parity on full gold + republish + Genie) | `stage5_bi_gate.json` |
| 9 docs + publish | docs generated for every object + committed | `stage9_docs.json` |
| 10 identity + security + governance | source grants mapped 1:1 to UC; PII masked; credentials scoped | `stage10_identity.sql`, `stage10_gate.json` |
| 11 enablement + go-live | training + runbooks + cutover/rollback + day-2 ops; all go/no-go checks green | `stage11_gate.json` |

The per-pipeline gates (G0-G9) and BI gates (B0-B4) below are what a single build unit
crosses **inside** the build stages (4 dev / 7 prod) and BI stages (5 dev / 8 prod).

## Gates
| Gate | Name | Passes when |
|---|---|---|
| G0 | contract | needs/logic/output 100% resolved (see [05](05_pipeline_contract.md)) |
| G1 | connections | all required connections smoke-test green (see [11](11_dashboard.md)) |
| G2 | bronze | prerequisites landed (dev sample + SIT prod copy present) |
| G3 | silver | typed hubs + intermediates built |
| G4 | gold | parity tables built with source-identical schema |
| G5 | self-check | no-extra-output + idempotency locally |
| G6 | maya_dev | dev profile green on the sampled illusion of prod |
| G7 | maya_sit | all 10 checks green at scale on prod-copied data, point-in-time |
| G8 | provisional | G6 AND G7 green; provisionally certified, soak clock starts |
| G9 | soak_certified | sustained parity green at every window (T+7, T+14), zero drift -> FINAL cert |

```mermaid
flowchart LR
  g0["G0 contract"] --> g1["G1 connections"] --> g2["G2 bronze"] --> g3["G3 silver"]
  g3 --> g4["G4 gold"] --> g5["G5 self-check"] --> g6["G6 MAYA-Dev"] --> g7["G7 MAYA-SIT"]
  g7 --> g8["G8 provisional"] --> g9["G9 soak-certified (T+7, T+14)"]
```

G0-G8 are reached in the build sprint. G9 is reached later, on the calendar: the pipeline
runs in parallel with the source for one to two weeks and re-proves parity. The build
queue does **not** wait on soak - agents move on to the next pipeline while provisional
pipelines soak in the background; only the final sign-off waits for G9.

## Timelines
- **1-2 weeks (autonomous, monitored)** - the standard MAYA run: 15-20 agents, waves in
  parallel, two-phase validation, human watches the dashboard.
- **Under one week (24/7, serverless)** - when Phase 0 is fully pre-completed
  (connections proven, dev sample + SIT prod copy in place, serverless on, dashboard
  live). MAYA-Dev iterations are near-free on serverless; MAYA-SIT is the only
  full-volume cost and runs once per certified pipeline.

The compression comes from MAYA: because logic is proven on the sample, SIT runs are
first-time-right far more often, so the paid full-volume pass rarely repeats.

## Backfill
After SIT parity is green, backfill history at the pinned watermark, then re-run G7 on
the backfilled range before G8 (provisional).

## Soak (G9) - sustained parity while running in parallel
Build-time parity proves state equality once; it cannot prove the incremental logic
matches. So after G8 the new pipeline runs **in parallel** with the source and MAYA
re-proves parity at each window in `maya.soak_windows_days` (default T+7, T+14), on the
cumulative table **and** the incremental delta since the prior checkpoint. Zero drift at
every window = G9 = final certification. Any drift (`INCREMENTAL-LOGIC` / `LATE-DATA`) is
fixed, the window re-backfilled, and the soak clock restarted. Watch it via
`v_soak_watch` (see [11](11_dashboard.md)). Because the timeline sections below cover the
build sprint, plan for final certification to land ~2 weeks after a pipeline's build,
overlapped across all pipelines rather than added per pipeline.

## BI gates (two phases)
BI migrates in two phases with the **same converted queries**. In the **dev** phase (stage 5)
each object crosses B0-B1 and dev-certifies (B2 query-parity) on the sample gold produced by
the dev build - no republish or Genie yet. In the **prod** phase (stage 8), after the full
load and prod certification, the same objects re-run B2 on the full gold and continue through
B3-B4. Once the gold tables a dashboard reads are MAYA-certified, its BI object flows through:

| Gate | Name | Passes when |
|---|---|---|
| B0 | extract | query + datasource + tables pulled via MCP/API |
| B1 | convert | AI-converted to Databricks SQL, tables repointed to certified gold |
| B2 | query-parity | converted query returns the exact same result as the original |
| B3 | republish | dashboard republished to the BI tool, now on Databricks |
| B4 | genie | Lakeview dashboard + Genie space created (AI/BI) |

```mermaid
flowchart LR
  b0["B0 extract"] --> b1["B1 convert"] --> b2["B2 query-parity"] --> b3["B3 republish"] --> b4["B4 genie"]
```

See [13_bi_layer_migration.md](13_bi_layer_migration.md).

## System gate (S) - migration complete
The per-pipeline gates above certify one build unit; the **system gate** certifies the
whole estate. It is the only gate that answers "is the migration done?"

| Gate | Name | Passes when |
|---|---|---|
| S | migration_complete | **every** in-scope pipeline is at G9 (FINAL cert) **and** every BI object is at B4 |

`maya certify` rolls all per-pipeline gates (and BI) across all waves into one state:

```mermaid
flowchart LR
  ip["MIGRATION_IN_PROGRESS (some pipeline BLOCKED)"] --> sp["SYSTEM_PROVISIONAL (all >= G8, some soaking / BI pending)"]
  sp --> mc["MIGRATION_COMPLETE (all G9 + all B4)"]
```

Only `MIGRATION_COMPLETE` clears the source systems for retirement. Run it with
`maya certify --config project.yaml` (add `--gates <json>` of real parity results for live
status). See [09_agent_orchestration.md](09_agent_orchestration.md).
