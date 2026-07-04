"""
config.py -- AcceleratorConfig: the single object that points the source-agnostic
core at a concrete migration project and its source adapter.

Everything downstream (graph, order, contract, reports) is parameterized by this,
so nothing in core/ hard-codes a project, path, brand, or source system.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import yaml  # optional; only needed for from_yaml
except Exception:  # pragma: no cover
    yaml = None


# Canonical node vocabulary every adapter should emit (synonyms accepted where noted).
PIPELINE_TYPES_DEFAULT = ["PIPELINE", "SYNAPSE_PIPELINE"]
TABLE_TYPES_DEFAULT = ["TABLE", "CONFIG_TABLE"]
PROC_TYPE = "STORED_PROC"

# Default schema -> medallion layer map (override per project/source).
SCHEMA_LAYERS_DEFAULT = {
    "ods": "bronze", "src": "bronze",
    "ds": "silver", "rdw": "silver",
    "qlik": "serving",
    "metadata": "config",
}


@dataclass
class Branding:
    org: str = "MAYA"
    dark: str = "#1F2430"
    accent: str = "#3B4CCA"
    teal: str = "#0E7C7B"
    gray: str = "#6B7280"
    show_databricks_lockup: bool = True


@dataclass
class Maya:
    """The MAYA two-phase, cost-saving validation settings.

    MAYA-Dev runs every pipeline against a small, referential-integrity-preserving
    sample of production (the "illusion") to prove logic cheaply; MAYA-SIT then proves
    parity at scale on production-copied data. A pipeline is certified only after both.
    """
    sample_rows: int = 10000                 # default per-table dev sample size
    sample_overrides: Dict[str, int] = field(default_factory=dict)  # table -> rows
    sampling: str = "ri_preserving"          # ri_preserving | random | none (dev already sampled)
    seed: int = 42                           # deterministic sampling seed
    dev_catalog: str = "dev"                 # UC catalog holding the sampled dev tables
    sit_catalog: str = "sit"                 # UC catalog holding prod-copied data
    source_ref_catalog: str = ""             # federated/source ref used to build samples + parity
    require_both_phases: bool = True         # both MAYA-Dev and MAYA-SIT before certify

    # ---- MAYA-Soak: sustained parallel-run parity (guards against slow drift) ----
    # Point-in-time SIT parity proves STATE equality once; it cannot prove that the
    # ongoing/incremental logic matches. Subtle merge/CDC/SCD/late-data differences
    # only surface after several production loads. MAYA-Soak keeps BOTH systems running
    # in parallel and re-proves parity at each window (default T+7 and T+14 days) with
    # zero drift before a pipeline is FINAL-certified.
    require_soak: bool = True                 # soak windows must be green for final cert
    soak_windows_days: List[int] = field(default_factory=lambda: [7, 14])  # checkpoints
    soak_drift_tolerance: float = 0.0        # allowed drift fraction (0 = exact; >0 only
                                             # for documented non-deterministic columns)

    # ---- Stage 2: whole-estate replication into a Databricks test catalog ------
    # Every source table AND view is replicated into `test_catalog` and filled either by
    # sampling the source (source_ref_catalog set) or by generating deterministic
    # synthetic rows (synthetic_rows each) with referential integrity via topological fill.
    test_catalog: str = "test"               # UC catalog holding the replicated test estate
    synthetic_rows: int = 10000              # rows per table when generating synthetic data
    test_from_source: bool = False           # True: sample test estate from source_ref_catalog;
                                             # False (default): generate synthetic RI data offline

    def rows_for(self, table: str) -> int:
        return self.sample_overrides.get(table, self.sample_rows)

    def catalog_for(self, env: str) -> str:
        # soak runs at full scale, so it uses the SIT catalog like MAYA-SIT
        return self.sit_catalog if env in ("sit", "soak") else self.dev_catalog


@dataclass
class Agents:
    """How MAYA drives the AI coding-agent swarm that builds/validates/fixes pipelines.

    MAYA prepares deterministic work (contracts, prompts, parity plans) and then a pool
    of coding agents authors the real Databricks build. The `driver` selects the backend:

      * "offline" (default): a deterministic, no-LLM backend that authors specs straight
        from the source logic + context pack, so the bundled demo runs end-to-end with
        zero external calls and CI stays green.
      * "cursor": drives real LLM coding agents through the Cursor SDK (`cursor_sdk`).
        Requires CURSOR_API_KEY; runs local agents against the repo working directory.
    """
    driver: str = "offline"              # offline | cursor
    model: str = "composer-2.5"          # model id for the cursor driver
    concurrency: int = 6                 # max agents building in parallel within a wave
    max_fix_iters: int = 5               # drift-loop attempts before a pipeline is flagged
    publish_remote: bool = False         # Stage 6: push docs to GitHub (else local commit)
    publish_branch: str = "main"


@dataclass
class AcceleratorConfig:
    project_name: str = "migration"
    # dotted import path to the adapter class, e.g. "adapters.synapse.adapter.SynapseAdapter"
    adapter: str = "adapters.synapse.adapter.SynapseAdapter"

    # filesystem
    artifacts_dir: str = "artifacts"        # raw exported source artifacts
    graph_dir: str = "discovery"            # where objects.csv / edges.csv live
    out_dir: str = "discovery"              # where derived CSV/PDF land
    specs_dir: str = "discovery/pipeline_specs"

    # graph vocabulary
    pipeline_types: List[str] = field(default_factory=lambda: list(PIPELINE_TYPES_DEFAULT))
    table_types: List[str] = field(default_factory=lambda: list(TABLE_TYPES_DEFAULT))

    # classification hints (source/project specific, but optional)
    schema_layers: Dict[str, str] = field(default_factory=lambda: dict(SCHEMA_LAYERS_DEFAULT))
    home_database: str = ""                 # the DB we have code for (others = external)

    # validation / sizing
    table_max_tb: float = 2.0               # <= this -> exact full-compare feasible

    branding: Branding = field(default_factory=Branding)
    maya: Maya = field(default_factory=Maya)
    agents: Agents = field(default_factory=Agents)
    # free-form adapter-specific settings
    adapter_options: Dict[str, Any] = field(default_factory=dict)

    # ---- path helpers ------------------------------------------------------
    base_dir: str = "."

    def p(self, *parts: str) -> str:
        return os.path.join(self.base_dir, *parts)

    def objects_csv(self) -> str:
        return self.p(self.graph_dir, "objects.csv")

    def edges_csv(self) -> str:
        return self.p(self.graph_dir, "edges.csv")

    def out(self, name: str) -> str:
        return self.p(self.out_dir, name)

    def layer_of(self, table: str) -> str:
        """Medallion layer for a fully-qualified table name (schema.name)."""
        schema = table.split(".")[0].lower() if "." in table else ""
        if schema in self.schema_layers:
            return self.schema_layers[schema]
        if schema.startswith("az_"):
            return "bronze"
        if "stg" in table.lower():
            return "silver"
        return "gold"

    # ---- loading -----------------------------------------------------------
    @classmethod
    def from_yaml(cls, path: str) -> "AcceleratorConfig":
        if yaml is None:
            raise RuntimeError("PyYAML is required for from_yaml; pip install PyYAML")
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        brand = raw.pop("branding", {}) or {}
        maya = raw.pop("maya", {}) or {}
        agents = raw.pop("agents", {}) or {}
        cfg = cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})
        if brand:
            cfg.branding = Branding(**{k: v for k, v in brand.items()
                                       if k in Branding.__dataclass_fields__})
        if maya:
            cfg.maya = Maya(**{k: v for k, v in maya.items()
                               if k in Maya.__dataclass_fields__})
        if agents:
            cfg.agents = Agents(**{k: v for k, v in agents.items()
                                   if k in Agents.__dataclass_fields__})
        # anchor relative paths to the config file's directory unless base_dir set
        if "base_dir" not in raw:
            cfg.base_dir = os.path.dirname(os.path.abspath(path)) or "."
        return cfg

    def load_adapter(self):
        """Import and instantiate the configured adapter."""
        import importlib
        mod_path, _, cls_name = self.adapter.rpartition(".")
        mod = importlib.import_module(mod_path)
        return getattr(mod, cls_name)(self)

    # default BI connectors by system
    _BI_CONNECTORS = {
        "looker": "adapters.bi.looker.LookerConnector",
        "tableau": "adapters.bi.tableau.TableauConnector",
        "powerbi": "adapters.bi.powerbi.PowerBIConnector",
    }

    def load_bi_connector(self):
        """Import and instantiate the BI connector from adapter_options.bi.

        Uses an explicit dotted `connector` path if given, else maps by `system`.
        """
        bi = (self.adapter_options or {}).get("bi", {})
        dotted = bi.get("connector") or self._BI_CONNECTORS.get(
            bi.get("system", "powerbi"))
        if not dotted:
            raise ValueError("no BI connector configured (adapter_options.bi.system)")
        import importlib
        mod_path, _, cls_name = dotted.rpartition(".")
        mod = importlib.import_module(mod_path)
        return getattr(mod, cls_name)(self)
