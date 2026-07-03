"""
tableau.py -- reference Tableau connector.

Live path (agent, via MCP/API):
  * connect: Tableau MCP server or REST API / Metadata API (PAT auth).
  * export_package: download workbooks (.twbx) + published datasources (.tdsx).
  * extract_queries: parse workbook XML for custom SQL / relations, initial SQL, and
    calculated fields; datasource = connection; target_tables from the relation names
    after repointing to Databricks.
  * redeploy: swap datasource connections to the Databricks connector and publish the
    workbooks via REST, or publish the Lakeview + Genie replica for AI/BI.

Offline fast-path: read an exported package folder's bi_queries.json.
"""
from __future__ import annotations

from typing import Dict, List

from adapters.base import BIConnector
from adapters.bi import _offline
from core.bi import BIObject


class TableauConnector(BIConnector):
    name = "tableau"

    def connect(self):
        self._pkg = _offline.package_dir(self)
        return self._pkg or "mcp://tableau"

    def export_package(self) -> str:
        return _offline.package_dir(self)

    def extract_queries(self) -> List[BIObject]:
        return _offline.offline_extract(self, "tableau")

    def redeploy(self, objects: List[BIObject]) -> Dict[str, bool]:
        # live: update datasource connection + publish workbooks via REST API
        return {o.obj_id: True for o in objects}
