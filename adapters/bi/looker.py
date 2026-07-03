"""
looker.py -- reference Looker connector.

Live path (agent, via MCP/API):
  * connect: Looker MCP server or Looker SDK (API 4.0) with client_id/secret.
  * export_package: pull LookML project (models/views/explores) + dashboards/looks.
  * extract_queries: each Look/tile -> its SQL (Query.run "sql" result or generated SQL
    from the explore), datasource = connection; target_tables from the explore's
    sql_table_name after repointing to Databricks.
  * redeploy: recreate the connection against Databricks SQL and update LookML/dashboards
    via the API, or (preferred for AI/BI) publish the Lakeview + Genie replica.

Offline fast-path: read an exported package folder's bi_queries.json.
"""
from __future__ import annotations

from typing import Dict, List

from adapters.base import BIConnector
from adapters.bi import _offline
from core.bi import BIObject


class LookerConnector(BIConnector):
    name = "looker"

    def connect(self):
        self._pkg = _offline.package_dir(self)
        return self._pkg or "mcp://looker"

    def export_package(self) -> str:
        return _offline.package_dir(self)

    def extract_queries(self) -> List[BIObject]:
        return _offline.offline_extract(self, "looker")

    def redeploy(self, objects: List[BIObject]) -> Dict[str, bool]:
        # live: PATCH dashboards/looks + connection via Looker API; here, mark planned
        return {o.obj_id: True for o in objects}
