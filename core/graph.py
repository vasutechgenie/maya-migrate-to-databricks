"""
graph.py -- the normalized dependency graph: the stable interface between any
source adapter and the source-agnostic core.

An adapter's job is to emit two CSVs with these exact columns; everything else in
the accelerator operates only on this model, so it is fully source-independent.

  objects.csv columns:
    object_key, name, type, layer, schema_or_domain, title, source_file,
    active, target_database, job_class, external_system
  edges.csv columns:
    src_key, src_name, src_type, edge_type, dst_key, dst_name, dst_type,
    exec_order, predecessors, when_condition, context

Canonical edge_type vocabulary:
  READS_TABLE, WRITES_TABLE, CALLS_PROC, EXECUTES_PIPELINE, READS_CONFIG,
  MAPS_TO_SOURCE (a.k.a. MAPS_TO_SYNAPSE), INVOKES_EXTERNAL

Downstream-app vocabulary (custom apps migrated to Lakebase + Databricks Apps):
  object types  : APP, APP_ENTITY, APP_ENDPOINT, APP_SCREEN, LAKEBASE_TABLE
  edge types    : CONTAINS (app -> child), EXPOSES_ENTITY (endpoint -> entity),
                  SERVES_SCREEN (endpoint -> screen), POPULATES_ENTITY
                  (pipeline -> entity), MAPS_TO_SOURCE (entity -> DW table)
"""
from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from typing import Dict, Iterable, List, Set

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

OBJECT_FIELDS = [
    "object_key", "name", "type", "layer", "schema_or_domain", "title",
    "source_file", "active", "target_database", "job_class", "external_system",
]
EDGE_FIELDS = [
    "src_key", "src_name", "src_type", "edge_type", "dst_key", "dst_name",
    "dst_type", "exec_order", "predecessors", "when_condition", "context",
]

# edge types (accept legacy synonyms)
E_READS = "READS_TABLE"
E_WRITES = "WRITES_TABLE"
E_CALLS = "CALLS_PROC"
E_EXEC = "EXECUTES_PIPELINE"
E_CONFIG = "READS_CONFIG"
E_MAPS = {"MAPS_TO_SOURCE", "MAPS_TO_SYNAPSE"}

# downstream-app object types + edge types
T_APP = "APP"
T_APP_ENTITY = "APP_ENTITY"
T_APP_ENDPOINT = "APP_ENDPOINT"
T_APP_SCREEN = "APP_SCREEN"
T_LAKEBASE_TABLE = "LAKEBASE_TABLE"
APP_OBJECT_TYPES = {T_APP, T_APP_ENTITY, T_APP_ENDPOINT, T_APP_SCREEN,
                    T_LAKEBASE_TABLE}
E_CONTAINS = "CONTAINS"
E_EXPOSES = "EXPOSES_ENTITY"
E_SERVES = "SERVES_SCREEN"
E_POPULATES = "POPULATES_ENTITY"


class Graph:
    """In-memory normalized graph with the traversal helpers the core needs."""

    def __init__(self, objects: Dict[str, dict], edges: List[dict],
                 pipeline_types=None, table_types=None):
        self.objects = objects
        self.edges = edges
        self.pipeline_types = set(pipeline_types or ["PIPELINE", "SYNAPSE_PIPELINE"])
        self.table_types = set(table_types or ["TABLE", "CONFIG_TABLE"])
        self.name_of = {k: o.get("name", k) for k, o in objects.items()}
        self.type_of = {k: o.get("type", "") for k, o in objects.items()}
        self._index()

    # ---- construction ------------------------------------------------------
    def _index(self):
        self.reads = defaultdict(set)      # key -> {table_name(lower)}
        self.writes = defaultdict(set)
        self.calls = defaultdict(set)      # caller_key -> {proc_key}
        self.exec_pipe = defaultdict(set)  # parent_key -> {child_key}
        self.config_reads = defaultdict(set)
        self.out_edges = defaultdict(list)
        for e in self.edges:
            et = e.get("edge_type", "")
            sk = e.get("src_key", "")
            self.out_edges[sk].append(e)
            if et == E_READS:
                self.reads[sk].add(e["dst_name"].lower())
            elif et == E_WRITES:
                self.writes[sk].add(e["dst_name"].lower())
            elif et == E_CALLS:
                self.calls[sk].add(e["dst_key"])
            elif et == E_EXEC:
                self.exec_pipe[sk].add(e["dst_key"])
            elif et == E_CONFIG:
                self.config_reads[sk].add(e["dst_name"].lower())

    # ---- queries -----------------------------------------------------------
    def pipeline_keys(self) -> List[str]:
        return [k for k, o in self.objects.items()
                if o.get("type") in self.pipeline_types]

    def is_table(self, key: str) -> bool:
        return self.objects.get(key, {}).get("type") in self.table_types

    def reachable_procs(self, start: str) -> Set[str]:
        """Transitive CALLS_PROC closure from a node."""
        seen: Set[str] = set()
        stack = list(self.calls.get(start, ()))
        while stack:
            p = stack.pop()
            if p in seen:
                continue
            seen.add(p)
            stack.extend(self.calls.get(p, ()))
        return seen

    def pipeline_io(self, pk: str):
        """(reads, writes) table-name sets for a pipeline incl. its reachable procs."""
        procs = self.reachable_procs(pk)
        ins = set(self.reads.get(pk, ()))
        outs = set(self.writes.get(pk, ()))
        for pr in procs:
            ins |= self.reads.get(pr, set())
            outs |= self.writes.get(pr, set())
        return ins, outs, procs

    # ---- downstream apps ---------------------------------------------------
    def app_keys(self) -> List[str]:
        """object_keys of every registered downstream APP node."""
        return [k for k, o in self.objects.items() if o.get("type") == T_APP]

    def app_children(self, app_key: str, child_type: str = "") -> List[str]:
        """Children (entities/endpoints/screens) contained by an app node."""
        out = []
        for e in self.out_edges.get(app_key, []):
            if e.get("edge_type") != E_CONTAINS:
                continue
            if child_type and e.get("dst_type") != child_type:
                continue
            out.append(e.get("dst_key"))
        return out

    # ---- io ----------------------------------------------------------------
    @classmethod
    def load(cls, objects_csv: str, edges_csv: str, pipeline_types=None,
             table_types=None) -> "Graph":
        objects = {r["object_key"]: r for r in _read(objects_csv)}
        edges = _read(edges_csv)
        return cls(objects, edges, pipeline_types, table_types)

    @classmethod
    def from_config(cls, cfg) -> "Graph":
        return cls.load(cfg.objects_csv(), cfg.edges_csv(),
                        cfg.pipeline_types, cfg.table_types)

    def save(self, objects_csv: str, edges_csv: str):
        _write(objects_csv, OBJECT_FIELDS, self.objects.values())
        _write(edges_csv, EDGE_FIELDS, self.edges)


def _read(path: str) -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        return list(csv.DictReader(f))


def _write(path: str, fields: List[str], rows: Iterable[dict]):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
