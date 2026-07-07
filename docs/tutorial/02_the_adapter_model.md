# Part 2 - The adapter model: reading any source

> [Index](README.md) | Prev: [Part 1](01_meet_maya_and_northwind.md) | Next: [Part 3](03_the_dependency_graph.md)

Everything source-specific in MAYA lives in an **adapter**; everything else operates on a
normalized graph. Roughly 70-80% of a migration is the reusable core; 20-30% is the adapter.

## The adapter contract
An adapter implements five methods:
- `collect()` - ensure the raw source artifacts are present.
- `parse()` - emit the normalized graph (`objects.csv` + `edges.csv`).
- `ddl_index()` - map `schema.table -> [columns]` from CREATE TABLE DDL.
- `connections()` - inventory external connections.
- `dialect_translate()` - assistive source-SQL -> Spark SQL rewrites.

Produce those from your source and the entire rest of MAYA works unchanged.

## The normalized graph
Two CSVs with fixed columns. `objects.csv` lists pipelines, tables, views, and procs.
`edges.csv` lists relationships using a small vocabulary: `READS_TABLE`, `WRITES_TABLE`,
`CALLS_PROC`, `EXECUTES_PIPELINE`, `READS_CONFIG`, and a couple more. Collapsing every source
into this tiny schema is what makes ordering, contracts, sampling, validation, and reporting
source-independent.

## The fast-path
Real adapters parse messy artifacts (XML jobs, ARM templates, T-SQL). To avoid blocking on
that, the reference Synapse adapter supports a **fast-path**: point it at a discovery folder
that already has `objects.csv` / `edges.csv` / `connections.csv`. That is exactly how Northwind
ships (`examples/northwind/`).

```bash
python3 cli.py graph --config examples/northwind/northwind.yaml
# graph: 33 objects, 42 edges -> .../examples/northwind/out/objects.csv
```

## A second reference adapter: PostgreSQL
The repo ships a second reference adapter, `adapters/postgres/`, that reuses this same
fast-path graph/DDL machinery and only swaps the two source-specific pieces (PL/pgSQL ->
Spark SQL translation and the Postgres export instructions). It migrates the bundled retail
estate under `examples/retail/` (source DDL in `examples/retail/postgres/schema.sql`) - a
concrete demonstration that onboarding a new source is "write a thin adapter," not "fork the
tool." See the [adapter authoring guide](../12_adapter_authoring_guide.md).

## Home database vs. external
`home_database` tells MAYA which database you own the code for. Anything else is **external** -
invoked in place, not rebuilt. In Northwind, `home_database: northwind` makes `ext_erp`,
`ext_web`, and `ext_fin` boundaries rather than build targets.

## Reference
- Phase-0 prerequisites: [../02_phase0_prereqs.md](../02_phase0_prereqs.md)
- Adapter authoring guide: [../12_adapter_authoring_guide.md](../12_adapter_authoring_guide.md)
- Graph schema: `core/graph.py`

---
Prev: [Part 1](01_meet_maya_and_northwind.md) | Next: [Part 3 - The dependency graph](03_the_dependency_graph.md)
