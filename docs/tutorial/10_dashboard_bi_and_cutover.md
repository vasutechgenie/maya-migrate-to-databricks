# Part 10 - Dashboard, BI/Genie, cutover - and your estate

> [Index](README.md) | Prev: [Part 9](09_maya_soak_sustained_parity.md)

The operational last mile: watch progress, migrate the BI layer on certified data, cut over - then
point MAYA at your own estate.

## A migration you can watch
MAYA ships control tables and dashboard views (`templates/dashboard_control_tables.sql`,
[../11_dashboard.md](../11_dashboard.md)) that track every pipeline through gates **G0-G9**:
- **v_progress** - pipelines by wave and state (blocked / building / provisional / soaking / certified).
- **v_drift** - open parity failures by reason code.
- **v_soak_watch** - pipelines in soak with T+7 / T+14 due dates and drift status.

## Migrating the BI layer
Certified gold is only half the value - the dashboards must move and show the same numbers.
```bash
python3 cli.py bi extract --config examples/northwind/northwind.yaml
python3 cli.py bi genie  --config examples/northwind/northwind.yaml
```
Per BI object: **extract** (MCP/API or an offline export like `examples/northwind/bi_export/`),
**AI-convert** the query to Databricks SQL repointed at certified gold, **prove result parity**
(schema, row count, set equality both ways, checksum, order) with the same drift-loop discipline,
**republish**, and **replicate** natively as a Lakeview dashboard with an attached **Genie** space.
BI work starts only after the gold tables it reads are MAYA-certified.

## Cutover
Because each table is certified and each wave built on certified data, cutover is flipping consumers
to already-proven tables. The `report` phase produces the sign-off PDF:
```bash
python3 cli.py report --config examples/northwind/northwind.yaml
```

## Running it on your estate
1. **Write (or reuse) an adapter** emitting the normalized graph, DDL index, and connections;
   ship a small synthetic example like Northwind. See [../12_adapter_authoring_guide.md](../12_adapter_authoring_guide.md).
2. **Copy `templates/project_config.example.yaml`** and point it at your discovery folder; set your
   schema->layer map, dev/sit catalogs, and soak windows.
3. **Run the same seven phases**, wave by wave, certifying as you go.

Everything in this tutorial is source-agnostic; only the adapter changes per source.

## Reference
- BI layer migration: [../13_bi_layer_migration.md](../13_bi_layer_migration.md)
- Execution plan + gates: [../10_execution_plan.md](../10_execution_plan.md)

---
That is the tutorial. Clone the repo, run `make demo`, and adapt it to your estate. Contributions
welcome - see [../../CONTRIBUTING.md](../../CONTRIBUTING.md).
