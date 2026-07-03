# Part 1 - Meet MAYA and Northwind

> Hands-on series - [tutorial index](README.md) | Next: [Part 2 - The adapter model](02_the_adapter_model.md)

MAYA treats a data-platform migration as a **deterministic pipeline**, not an artisanal
rewrite: same inputs, same outputs, every time. This tutorial walks the whole workflow on a
small, fully runnable demo.

## Run it now
```bash
git clone https://github.com/vasutechgenie/maya-migrate-to-databricks
cd maya-migrate-to-databricks
pip install -r requirements.txt
make demo
```
`make demo` runs the full workflow against the bundled **Northwind** example and writes
every artifact to `examples/northwind/out/`.

## Meet Northwind
Northwind is a fictional retailer moving from Azure Synapse to Databricks. It is deliberately
small but realistic:
- **8 pipelines** - an orchestrator, metadata-driven ingestion, file intake, an external
  invoke-in-place job, three SQL transform jobs, and a serving replication job.
- **~25 tables and views** across bronze (`src`), silver (`sales`), gold (`rdm`), a
  `serving` layer, and a `metadata` config table.
- **4 connections** (JDBC, ADLS, a REST API, a serving target).

Northwind is also the project's **test fixture**: `tests/` asserts on its exact waves,
classifications, and parity targets, so every example in this tutorial stays true as the code
evolves.

## The full arc
Everything MAYA does is a function of one normalized graph. The workflow splits into a
**preview** (nothing is built - a human can review the plan) and a **build + certify** loop
(the AI agent swarm turns the plan into the real lakehouse):

Preview:
1. **graph** - the adapter parses the source into `objects.csv` + `edges.csv`.
2. **order** - topological build order (waves).
3. **verify** - an independent re-derivation proves the order.
4. **context** - a deterministic build contract per pipeline.
5. **report** - a branded PDF preview of the whole migration.

Build + certify:
6. **orchestrate** - a swarm of AI coding agents drains each wave's queue and builds the
   **real** pipelines (`cli.py orchestrate --status`).
7. **sample** - a small "illusion of production" for cheap logic proofs inside the build loop.
8. **validate** - parity across dev -> sit -> soak, with no partial credit; a wave advances
   only when every pipeline in it is provisionally certified.
9. **certify** - the whole-system rollup (`cli.py certify`) that declares the migration
   complete once every pipeline and dashboard is certified.

## Why "MAYA"
*Maya* means "illusion". After an agent builds a pipeline it first proves the logic against a
small illusion of production (every table, a few thousand rows) - the cheap first gate inside
the build loop, not the deliverable - then proves it at full scale, then re-proves it over
time to catch drift. The three validation phases - Dev, SIT, Soak - are covered in Parts 7-9,
and the whole-system certification in Part 10.

## Reference
- Methodology: [../01_methodology.md](../01_methodology.md)
- The validation technique: [../08_maya_two_phase_validation.md](../08_maya_two_phase_validation.md)

---
Next: [Part 2 - The adapter model](02_the_adapter_model.md)
