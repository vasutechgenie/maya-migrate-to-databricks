# Part 4 - Build order, waves, and the independent verifier

> [Index](README.md) | Prev: [Part 3](03_the_dependency_graph.md) | Next: [Part 5](05_the_pipeline_contract.md)

MAYA **computes** the safe build sequence and then **proves** it with an independent check.

## Waves
```bash
python3 cli.py order --config examples/northwind/northwind.yaml
# order: 22 tables in 5 waves; 8 pipelines in 5 waves
```
A wave is a set of units with no intra-wave dependency. Northwind's pipeline waves:
- **W0** - `nw_ingest_erp`, `nw_web_intake`, `nw_fx_sync`
- **W1** - `nw_build_sales`, `nw_build_web`
- **W2** - `nw_build_marts`
- **W3** - `nw_qlik_replicate`
- **W4** - `nw_daily_master`

Table-level order is primary; pipeline waves are derived from it.

## The algorithms
Order is produced with **Tarjan SCC** (collapse cycles into single units) + **longest-path
layering** (assign each unit to a wave). Northwind is acyclic, so every component is a single
table - but the SCC machinery handles the tangled estates you meet in the wild.

## Independent verification
The verifier **does not import the builder.** It re-derives the waves with a *different*
algorithm set (Kosaraju SCC, memoized-DFS longest path, Kahn peel) and checks four things:
```bash
python3 cli.py verify --config examples/northwind/northwind.yaml
#   C1_completeness: True      published tables == graph tables
#   C2_wave_agreement: True    recomputed wave == published wave
#   C3_forward_edges: True     every dependency points forward
#   C4_build_sim: True         a Kahn peel reaches every table (no hidden cycle)
# verify: PASS (22 tables, 5 waves)
```
Two independent implementations agreeing is a far stronger guarantee than one asserting it is
right. Machine-checked forward edges make "built a mart on a dimension that wasn't ready"
structurally impossible.

## Why it matters
A verified wave plan is what makes parallelism safe: staff a wave with several builders at once;
the barrier to the next wave opens only when the current one is done and certified. Re-running
after a source change re-plans deterministically.

## Reference
- Build order: [../04_build_order.md](../04_build_order.md)
- Code: `core/order.py`, `core/verify_order.py`

---
Prev: [Part 3](03_the_dependency_graph.md) | Next: [Part 5 - The pipeline contract](05_the_pipeline_contract.md)
