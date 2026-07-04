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

    # ---- 7. Stage-0 identity/security/governance exports (optional) --------
    # These make the *non-data* estate collectable: who can touch what, which secrets
    # back which connections, and which columns are sensitive. Like the Stage-1 exports
    # they ship with safe, non-empty defaults derived from the graph/connections/DDL so
    # any adapter gets baseline coverage; override to export real principals/grants from
    # the source platform (SQL logins, AD groups, Ranger/Sentry policies, ...).
    PII_PATTERNS = ("name", "email", "e_mail", "phone", "mobile", "ssn", "dob",
                    "birth", "address", "addr", "zip", "postal")

    def _home_schemas(self) -> List[str]:
        try:
            g = Graph.load(self.cfg.objects_csv(), self.cfg.edges_csv(),
                           self.cfg.pipeline_types, self.cfg.table_types)
        except Exception:
            return []
        home = (self.cfg.home_database or "").lower()
        schemas = set()
        for _k, o in g.objects.items():
            if o.get("type") not in list(self.cfg.table_types) + ["VIEW"]:
                continue
            if (o.get("external_system") or "").strip():
                continue
            if home and (o.get("target_database", "") or "").lower() not in ("", home):
                continue
            s = (o.get("schema_or_domain") or "").lower()
            if s:
                schemas.add(s)
        return sorted(schemas)

    def export_principals(self) -> List[dict]:
        """Users/groups/roles/service principals that hold access in the source.

        Rows: {principal, type, member_of, source_role, description}. Default derives a
        small role model (engineers/analysts/stewards/ops + one ETL service principal)
        keyed on the home database so the identity surface is never empty.
        """
        home = (self.cfg.home_database or self.cfg.project_name or "app").lower()
        return [
            {"principal": f"{home}_engineers", "type": "group", "member_of": "",
             "source_role": "db_datawriter", "description": "Data engineering team"},
            {"principal": f"{home}_analysts", "type": "group", "member_of": "",
             "source_role": "db_datareader", "description": "BI analysts"},
            {"principal": f"{home}_stewards", "type": "group", "member_of": "",
             "source_role": "db_owner", "description": "Data stewards / governance"},
            {"principal": f"{home}_ops", "type": "group", "member_of": "",
             "source_role": "db_operator", "description": "Platform operations / on-call"},
            {"principal": f"sp_{home}_etl", "type": "service_principal", "member_of": "",
             "source_role": "etl_service", "description": "ETL service principal"},
        ]

    def export_grants(self) -> List[dict]:
        """Source access matrix rows: {principal, object, privilege}.

        Default grants engineers + the ETL service principal ALL on every home schema,
        analysts SELECT on gold/serving schemas, and stewards SELECT on all - so the
        access surface mirrors a typical least-privilege model.
        """
        home = (self.cfg.home_database or self.cfg.project_name or "app").lower()
        rows: List[dict] = []
        for s in self._home_schemas():
            rows.append({"principal": f"{home}_engineers", "object": s, "privilege": "ALL"})
            rows.append({"principal": f"sp_{home}_etl", "object": s, "privilege": "ALL"})
            rows.append({"principal": f"{home}_stewards", "object": s, "privilege": "SELECT"})
            if self.cfg.schema_layers.get(s) in ("gold", "serving"):
                rows.append({"principal": f"{home}_analysts", "object": s,
                             "privilege": "SELECT"})
        return rows

    def export_secrets(self) -> List[dict]:
        """Credential/secret inventory (names/scopes only, never values).

        Rows: {secret, connection, type, notes}. Default emits one secret per collected
        connection so no credential a pipeline depends on is missing.
        """
        rows = []
        for c in (self.connections() or []):
            conn = c.get("connection") or c.get("name")
            if not conn:
                continue
            rows.append({"secret": f"{conn}_secret", "connection": conn,
                         "type": f"{c.get('type', 'credential')}_secret",
                         "notes": c.get("notes", "")})
        return rows

    def classify_data(self) -> List[dict]:
        """Per-column data classification rows: {table, column, classification, mask}.

        Default scans the DDL index and flags columns whose name matches a PII pattern,
        assigning a deterministic mask. A real adapter reads source classification /
        masking policy; the demo ships an authoritative classification.csv.
        """
        try:
            ddl = self.ddl_index()
        except Exception:
            ddl = {}
        rows = []
        for table, cols in sorted(ddl.items()):
            for c in cols:
                cl = c.lower()
                if any(p in cl for p in self.PII_PATTERNS):
                    rows.append({"table": table, "column": c,
                                 "classification": "PII", "mask": "default"})
        return rows

    def export_security_facts(self) -> Dict[str, object]:
        """Non-tabular security posture facts (encryption, network, audit, compliance)."""
        return {
            "encryption_at_rest": "platform-managed keys",
            "encryption_in_transit": "TLS",
            "audit_logging": "source audit -> Unity Catalog system.access.audit",
            "compliance": [],
        }

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
