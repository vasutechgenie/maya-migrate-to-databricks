# Part 5 - The deterministic pipeline contract

> [Index](README.md) | Prev: [Part 4](04_build_order_and_verifier.md) | Next: [Part 6](06_reusable_engines.md)

The **build contract** is a precise, machine-generated spec for each pipeline, derived straight
from the graph so it is complete and never invented.

## Generate the contracts
```bash
python3 cli.py context --config examples/northwind/northwind.yaml
# context: 8 contracts, 8 parity targets -> out/pipeline_specs/context
```

## Anatomy (nw_build_sales)
Every contract has three sections, read directly off the graph:
- **Needs (prerequisites)** - tables read but not produced: `src.customers`, `src.products`,
  `src.suppliers`, `src.orders`, `src.order_lines`.
- **Logic** - the pattern + engine (Part 6), reachable procs, and a bronze->silver->gold sketch.
- **Output (produced)** - every written table, tagged with a medallion **layer**;
  `nw_build_sales` produces four `sales.*` tables, all **silver**.

From the output, MAYA computes the **parity targets** - the persisted silver/gold tables to
certify. `nw_build_sales` has 4; an ingestion job that only lands bronze has 0.

## Layers are computed
The layer comes from a configurable schema map:
```yaml
schema_layers: { src: bronze, sales: silver, rdm: gold, serving: serving, metadata: config }
```
So `sales.dim_customer` is silver and `rdm.mart_sales_daily` is gold - automatically.

## DDL columns come along
Because the adapter built a DDL index, each parity target carries its **column list** (e.g.
`sales.dim_customer` lists `customer_key`, `customer_id`, `region`, ...). Those columns become
the inputs to the parity SQL in Parts 8-9.

## No partial credit starts here
A pipeline is buildable only when needs, logic, and output are fully resolved. Anything missing
is **named, not assumed** - the same philosophy that runs through the whole tool.

## Reference
- Pipeline contract: [../05_pipeline_contract.md](../05_pipeline_contract.md)
- Code: `core/contract.py`; output: `out/pipeline_specs/context/*.json`

---
Prev: [Part 4](04_build_order_and_verifier.md) | Next: [Part 6 - Reusable engines](06_reusable_engines.md)
