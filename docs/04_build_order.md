# 04 - Build order (waves)

MAYA orders the estate so nothing is built before its inputs. Table-level order is
primary (metadata-driven pipelines emit different tables per config row, so the real
constraint is between tables); a pipeline-level order is derived for the build units.
See [core/order.py](../core/order.py) and [core/verify_order.py](../core/verify_order.py).

## Algorithm
1. Build the table dependency graph: every writer's inputs precede its outputs.
2. Collapse cycles with **Tarjan SCC** (iterative, stack-safe).
3. Layer the condensed DAG by **longest path from a source** (Kahn). The layer is the
   wave.
4. Derive pipeline waves from producer/consumer table relationships plus explicit
   `EXECUTES_PIPELINE` orchestration edges.

Outputs (in `out_dir`): `build_order_tables.csv`, `build_order_pipelines.csv`,
`build_order.md`.

## Independent verification
`verify_order.py` deliberately does not import `order.py`. It re-derives waves with
**different** algorithms (Kosaraju SCC + memoized-DFS longest path + Kahn-peel build
simulation) and checks the published order:

| Check | Proves |
|---|---|
| C1 completeness | published tables == graph tables |
| C2 wave agreement | recomputed wave == published wave |
| C3 forward edges | every dependency goes to an equal/greater wave |
| C4 build sim | Kahn peeling reaches all components (no deadlock) |

A green verify is the proof the order is correct and replayable.

## Waves and MAYA
Waves define the parallelism envelope: within a wave, an agent pool builds pipelines
concurrently ([09_agent_orchestration.md](09_agent_orchestration.md)); a strict barrier
means a wave advances only when every pipeline in it is MAYA-certified.
