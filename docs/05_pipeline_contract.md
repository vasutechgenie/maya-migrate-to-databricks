# 05 - The pipeline contract

Every pipeline gets a deterministic, machine-readable contract derived straight from
the graph - never invented. See [core/contract.py](../core/contract.py) and the schema
[templates/context_pack_schema.json](../templates/context_pack_schema.json).

## What the contract fixes
| Field | Meaning |
|---|---|
| pattern / engine / kind | classification (A-G/X -> E1-E7; medallion/orchestration/external_invoke/utility) |
| prereqs | everything read but not produced = the bronze landing set |
| produced | every table written, tagged with a medallion layer |
| parity | persisted silver/gold outputs to compare vs source (with DDL columns) |
| procs | reachable stored procs + their source files |
| mermaid | bronze -> silver -> gold data-flow diagram |

## The classifier
`classify_pattern()` is signal-driven and configurable (`DEFAULT_SIGNALS`): control
tables -> A, dynamic-SQL configs -> C, file-intake hints -> D, replication -> F,
external-only -> E, else transform B / orchestrator G / utility X. Override signals per
engagement.

## Completeness gate (G0)
A contract is complete when needs, logic, and output are all resolved: every prereq is
a real object, every produced table has a layer, and every parity target has DDL
columns. Authoring cannot start until G0 is green. This is what makes the downstream
build deterministic - the agent translates known logic against a known schema.

## MAYA linkage
`maya.specs_from_context()` turns a contract's `prereqs` into sample specs (reference
tables copied whole, others sampled), so the dev "illusion of prod" contains exactly
what the pipeline needs and joins resolve. See
[08_maya_two_phase_validation.md](08_maya_two_phase_validation.md).
