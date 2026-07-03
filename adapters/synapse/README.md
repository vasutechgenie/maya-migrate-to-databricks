# Synapse reference adapter

Turns an **Azure Synapse + Automic (UC4) + Synapse DW SQL** estate into the
accelerator's normalized graph. It is the worked example and the template for writing
any new adapter (see [../../docs/12_adapter_authoring_guide.md](../../docs/12_adapter_authoring_guide.md)).

## What it produces
| Method | Output |
|---|---|
| `collect()` | ensures raw artifacts + copies a pre-built graph (fast-path) |
| `parse()` | `objects.csv` / `edges.csv` (the normalized graph) |
| `ddl_index()` | `schema.table -> [columns]` from `artifacts/DW/<db>/<schema>/{Tables,Views}/*.sql` |
| `connections()` | connection inventory rows from `connections.csv` |
| `dialect_translate()` | assistive T-SQL -> Spark SQL rewrites |

## Two modes
1. **Fast-path (default)** - point `adapter_options.source_dir` at a `discovery/` folder
   that already contains `objects.csv` / `edges.csv` / `connections.csv`. The accelerator
   then runs `order`, `verify`, `context`, `orchestrate`, and `report` immediately. This is
   how the bundled **Northwind demo** ([../../examples/northwind/](../../examples/northwind/)) runs.
2. **Full parse** - plug real artifact parsers (Automic XML jobs, Synapse ARM
   pipelines/linked-services, DW `CREATE PROC`/`CREATE TABLE` SQL) into `parse()`. That is
   a mechanical lift; the graph schema they must emit is documented in `core/graph.py`.

## Config
```yaml
adapter: adapters.synapse.adapter.SynapseAdapter
home_database: northwind        # tables in other DBs are treated as external
adapter_options:
  source_dir: examples/northwind          # discovery dir with objects/edges/connections
  artifacts_dir: examples/northwind/artifacts
```

## Classification signals
The generic classifier in `core/contract.py` uses `DEFAULT_SIGNALS` (control tables ->
pattern A, dynamic-SQL configs -> C, file-intake name hints -> D, replication/Qlik -> F,
external-only -> E). Override them per engagement by passing a `signals` dict to
`contract.generate_all`.
