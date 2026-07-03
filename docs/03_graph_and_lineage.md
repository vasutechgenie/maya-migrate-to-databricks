# 03 - Graph and lineage

The normalized dependency graph is the stable interface between any source adapter and
the source-agnostic core. An adapter emits two CSVs; everything else operates only on
them. See [core/graph.py](../core/graph.py).

## objects.csv
| column | meaning |
|---|---|
| object_key | unique key |
| name | fully-qualified name (e.g. `sales.dim_customer`) |
| type | PIPELINE / SYNAPSE_PIPELINE / TABLE / CONFIG_TABLE / STORED_PROC / VIEW |
| layer | optional medallion hint |
| schema_or_domain | schema / domain |
| title | human title |
| source_file | repo-relative path to the defining artifact |
| active | 1/0 |
| target_database | owning database (used to detect external) |
| job_class | scheduler class |
| external_system | non-empty for invoke-in-place systems |

## edges.csv
| column | meaning |
|---|---|
| src_key, src_name, src_type | source node |
| edge_type | see vocabulary below |
| dst_key, dst_name, dst_type | destination node |
| exec_order, predecessors, when_condition | orchestration metadata |
| context | free-form provenance |

### Edge-type vocabulary
`READS_TABLE`, `WRITES_TABLE`, `CALLS_PROC`, `EXECUTES_PIPELINE`, `READS_CONFIG`,
`MAPS_TO_SOURCE` (a.k.a. `MAPS_TO_SYNAPSE`), `INVOKES_EXTERNAL`.

## Optional companions
- **ddl_index** - `schema.table -> [columns]` from source CREATE TABLE/VIEW (adapter
  `ddl_index()`); drives parity column lists.
- **connections.csv** - connection inventory (adapter `connections()`); drives
  provisioning + smoke tests.

## Traversal helpers (core)
`Graph.pipeline_keys()`, `reachable_procs()` (transitive `CALLS_PROC`), and
`pipeline_io()` (reads/writes incl. reachable procs) are the primitives the order and
contract modules build on.
