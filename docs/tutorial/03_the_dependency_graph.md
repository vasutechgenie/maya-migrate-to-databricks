# Part 3 - Building the dependency graph

> [Index](README.md) | Prev: [Part 2](02_the_adapter_model.md) | Next: [Part 4](04_build_order_and_verifier.md)

MAYA makes the dependency graph the **single source of truth** - every later phase is a pure
computation over it. The graph is derived from the source, so it is exhaustive and current.

## What the graph contains
After the `graph` phase, Northwind resolves to **33 objects and 42 edges**. In code the graph
exposes exactly the queries the core needs:
- `reads` / `writes` - table-name sets per pipeline (including reachable procs);
- `calls` - the transitive stored-proc closure;
- `exec_pipe` - which pipelines an orchestrator fans out to;
- `config_reads` - control/metadata tables a pipeline consults.

## Northwind's shape
- **ext_*** - external source systems (read-only).
- **src** (bronze) - landed copies from the ingestion jobs.
- **sales** (silver) - conformed dimensions + the order fact.
- **rdm** (gold) - the marts (daily sales, customer-360, product performance).
- **serving** - a replicated copy of the daily mart.

`nw_ingest_erp` lands `src.*` from the ERP tables + a metadata control table; `nw_build_sales`
builds `sales.*` from `src.*`; `nw_build_marts` builds `rdm.*` from `sales.*`;
`nw_qlik_replicate` copies the daily mart to `serving`; `nw_daily_master` orchestrates; and
`nw_fx_sync` invokes an external FX proc in place.

## Derived, not drawn
Hand-drawn lineage rots and is never complete enough to compute on. Because MAYA's graph is
machine-readable and derived, the next phases are deterministic: the build order is a
topological sort of it; each contract is read off its edges; the sample plan follows FK edges;
the report counts its nodes and edges.

## The external boundary
The graph makes the external boundary explicit. The `ext_*` tables and the `ext_fin` proc sit
outside `home_database`, so MAYA treats them as boundaries - which the classifier (Part 6) turns
into a concrete "invoke in place, don't rebuild" decision.

## Reference
- Graph & lineage: [../03_graph_and_lineage.md](../03_graph_and_lineage.md)
- The files: `examples/northwind/objects.csv`, `examples/northwind/edges.csv`

---
Prev: [Part 2](02_the_adapter_model.md) | Next: [Part 4 - Build order and the verifier](04_build_order_and_verifier.md)
