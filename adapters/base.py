"""
base.py -- the SourceAdapter contract.

An adapter is the ONLY source-specific code in a migration. It turns a legacy
platform's artifacts into the normalized graph the source-agnostic core consumes,
plus DDL, connections, and a dialect translator. Implement these five methods and
the entire accelerator (order, contract, engines, validation, orchestration,
reports) works unchanged.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from core.graph import Graph
from core.bi import BIObject


class SourceAdapter(ABC):
    """Base class every source adapter (Synapse, Informatica, SSIS, ...) extends."""

    #: short id, e.g. "synapse"
    name: str = "base"

    def __init__(self, cfg):
        self.cfg = cfg
        self.opts = getattr(cfg, "adapter_options", {}) or {}

    # ---- 1. collect --------------------------------------------------------
    @abstractmethod
    def collect(self) -> str:
        """Gather/refresh raw source artifacts under cfg.artifacts_dir. Return the dir."""

    # ---- 2. parse ----------------------------------------------------------
    @abstractmethod
    def parse(self) -> Graph:
        """Parse artifacts into the normalized Graph and persist objects/edges CSVs."""

    # ---- 3. ddl index ------------------------------------------------------
    @abstractmethod
    def ddl_index(self) -> Dict[str, List[str]]:
        """Map fully-qualified table/view name -> ordered column list from source DDL."""

    # ---- 4. connections ----------------------------------------------------
    @abstractmethod
    def connections(self) -> List[dict]:
        """Return connection inventory rows (also written to connections.csv)."""

    # ---- 5. dialect translate ---------------------------------------------
    @abstractmethod
    def dialect_translate(self, sql: str) -> str:
        """Best-effort translate source SQL dialect -> Spark SQL (assistive only)."""

    # ---- 6. Stage-1 asset exports (optional; default no-op) ----------------
    # These make Stage 1 "collect" total: every scheduler trigger and every out-of-code
    # config/control table is exported so nothing a pipeline depends on is missing. They
    # ship with safe defaults so existing adapters keep working unchanged; override to
    # export real triggers/configs from the source platform.
    def export_schedules(self) -> List[dict]:
        """Every scheduler trigger that invokes a pipeline.

        Rows: {trigger, schedule, pipeline, enabled}. Default derives one trigger per
        pipeline from its job_class in the graph, so the estate's invocation surface is
        never empty; a real adapter reads the scheduler (Automic/ADF/Airflow/...).
        """
        try:
            g = Graph.load(self.cfg.objects_csv(), self.cfg.edges_csv(),
                           self.cfg.pipeline_types, self.cfg.table_types)
        except Exception:
            return []
        rows = []
        for k, o in g.objects.items():
            if o.get("type") not in g.pipeline_types:
                continue
            jc = o.get("job_class", "") or "DAILY"
            rows.append({"trigger": f"trg_{o.get('name', k)}",
                         "schedule": jc, "pipeline": o.get("name", k),
                         "enabled": o.get("active", "Y")})
        return rows

    def export_configs(self) -> Dict[str, List[dict]]:
        """Config/control DB tables dumped as row dicts, keyed by table name.

        Default emits a single deterministic header row per CONFIG_TABLE (from its DDL
        columns) so the config surface is captured; a real adapter dumps actual rows.
        """
        try:
            g = Graph.load(self.cfg.objects_csv(), self.cfg.edges_csv(),
                           self.cfg.pipeline_types, self.cfg.table_types)
            ddl = self.ddl_index()
        except Exception:
            return {}
        out: Dict[str, List[dict]] = {}
        for k, o in g.objects.items():
            if o.get("type") != "CONFIG_TABLE":
                continue
            name = o.get("name", k)
            cols = ddl.get(name, []) or ddl.get(name.lower(), [])
            out[name] = [{c: "" for c in cols}] if cols else []
        return out

    # convenience: run collect+parse and persist
    def build_graph(self) -> Graph:
        self.collect()
        g = self.parse()
        g.save(self.cfg.objects_csv(), self.cfg.edges_csv())
        return g


class BIConnector(ABC):
    """The BI-tool-specific half of BI layer migration (Looker / Tableau / Power BI).

    Everything else - query-result parity, Genie/Lakeview replication, orchestration -
    is source-agnostic in core/bi.py. A connector connects over MCP/API, exports the
    package, extracts the query-bearing objects, and republishes the migrated
    dashboards. Implementations should offer an offline fast-path (parse an exported
    package folder) so the flow is runnable without live credentials.
    """

    name: str = "bi_base"

    def __init__(self, cfg):
        self.cfg = cfg
        self.opts = (getattr(cfg, "adapter_options", {}) or {}).get("bi", {})

    @abstractmethod
    def connect(self):
        """Open an MCP/API session to the BI system (or select the offline package)."""

    @abstractmethod
    def export_package(self) -> str:
        """Export the full BI package/workbook set; return the local path."""

    @abstractmethod
    def extract_queries(self) -> List[BIObject]:
        """Parse the package into query-bearing BIObjects (dashboards/tiles/datasets)."""

    @abstractmethod
    def redeploy(self, objects: List[BIObject]) -> Dict[str, bool]:
        """Publish the migrated dashboards back to the BI tool via API. obj_id -> ok."""
