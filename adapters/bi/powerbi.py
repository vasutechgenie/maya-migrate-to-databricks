"""
powerbi.py -- reference Power BI connector.

Live path (agent, via MCP/API):
  * connect: Power BI MCP server or Power BI REST API + XMLA endpoint (service principal).
  * export_package: export PBIX / thin reports + dataset (TMDL/BIM) definitions.
  * extract_queries: pull Power Query (M) source steps and DAX/native queries; datasource
    = the M source; target_tables from the table source expressions after repointing the
    dataset to the Databricks connector.
  * redeploy: rebind the dataset to Databricks (DirectQuery/Import), then publish reports
    via REST, or publish the Lakeview + Genie replica for AI/BI.

Offline fast-path: read an exported package folder's bi_queries.json.
"""
from __future__ import annotations

from typing import Dict, List

from adapters.base import BIConnector
from adapters.bi import _offline
from core.bi import BIObject


class PowerBIConnector(BIConnector):
    name = "powerbi"

    def connect(self):
        self._pkg = _offline.package_dir(self)
        return self._pkg or "mcp://powerbi"

    def export_package(self) -> str:
        return _offline.package_dir(self)

    def extract_queries(self) -> List[BIObject]:
        return _offline.offline_extract(self, "powerbi")

    def redeploy(self, objects: List[BIObject]) -> Dict[str, bool]:
        # live: rebind dataset to Databricks + publish reports via Power BI REST API
        return {o.obj_id: True for o in objects}
