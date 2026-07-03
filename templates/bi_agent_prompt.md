# Agent task: migrate a BI object (MAYA BI layer)

You migrate one query-bearing BI object (a Looker Look/tile, Tableau sheet, or Power BI
visual/dataset query) from the source BI tool to Databricks. You act over MCP/API.

## Steps
1. **Extract** (B0) - via the BI tool's MCP/API, pull this object's original query,
   its datasource, and the tables it reads.
2. **Convert** (B1) - AI-convert the query to Databricks SQL and repoint every source
   table to its certified Databricks gold table (use the config `table_map`). Do not
   change semantics.
3. **Query-result parity** (B2) - run the ORIGINAL query on the source and snapshot its
   result; run the CONVERTED query against certified gold; prove the results are the
   EXACT same: result_schema, result_rowcount, result_set_equality (EXCEPT both ways
   empty), result_checksum, and result_order if the original is ordered. On any diff,
   inspect both queries, assign a reason code, fix the converted query, re-run - until
   green. No waivers except a signed-off LEGACY-BUG.
4. **Republish** (B3) - publish the migrated dashboard back to the BI tool via API, now
   pointed at Databricks.
5. **Genie + Lakeview** (B4) - replicate the dashboard natively in Databricks (Lakeview)
   and attach a Genie space seeded with this dashboard's queries as trusted assets and
   its tile titles as sample questions, so business users get AI/BI on the same numbers.

## Output
Write `bi_authored/<obj_id>.json` with:
`converted_query` (string), `parity_passed` (bool), `reason_codes` (list),
`republished` (bool), `genie_created` (bool).

## Definition of done
The converted query returns the exact same result as the original against certified
gold, the dashboard is republished, and its Genie + Lakeview replica exist. Only then is
the BI object DONE. BI objects may only start after the gold tables they read are
MAYA-certified.
