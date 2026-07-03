# 12 - Adapter authoring guide

Onboarding a new source system (Informatica, SSIS, Teradata, Oracle, Netezza, dbt, ...)
means writing ONE class: a `SourceAdapter`. Everything else - order, contract, engines,
MAYA validation, orchestration, reports - is reused unchanged. See
[adapters/base.py](../adapters/base.py) and the reference
[adapters/synapse/adapter.py](../adapters/synapse/adapter.py).

## Implement five methods
```python
from adapters.base import SourceAdapter
from core.graph import Graph

class MySourceAdapter(SourceAdapter):
    name = "mysource"

    def collect(self) -> str: ...              # gather raw artifacts -> artifacts_dir
    def parse(self) -> Graph: ...              # artifacts -> normalized Graph (+ save CSVs)
    def ddl_index(self) -> dict: ...           # schema.table -> [columns]
    def connections(self) -> list: ...         # connection inventory rows
    def dialect_translate(self, sql): ...      # source SQL -> Spark SQL (assistive)
```

## The only hard requirement: emit the normalized graph
`parse()` must produce `objects.csv` / `edges.csv` with the exact columns and edge-type
vocabulary in [03_graph_and_lineage.md](03_graph_and_lineage.md). If you can produce
that, the whole accelerator works.

## Tips
- **Fast path** - if a prior tool already produced a graph, load it in `parse()` (as the
  Synapse adapter does) to get running immediately, then replace with a real parser.
- **Classification signals** - reuse `DEFAULT_SIGNALS` or pass source-specific `signals`
  to `contract.generate_all` (schema->layer map lives in the project config).
- **DDL matters for MAYA** - accurate `ddl_index()` gives parity its column lists and
  lets the sampler copy full DDL/schema, which the framework requires.
- **FK metadata** - supply foreign keys (via the maya sample config or the adapter) so
  RI-preserving sampling keeps joins intact on the dev illusion.

## Wire it up
Point `adapter:` in the project config at your class
([templates/project_config.example.yaml](../templates/project_config.example.yaml)) and
run the phases via [cli.py](../cli.py).
