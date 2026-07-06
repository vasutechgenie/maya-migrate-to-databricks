"""
adapter.py -- the reference Synapse (+ Automic + Synapse DW SQL) adapter.

This is the worked example that proves the accelerator's core is source-agnostic:
it emits the normalized graph, DDL index, and connections that every other module
consumes. It supports two modes:

  * fast-path (default): reuse an already-produced objects.csv / edges.csv /
    connections.csv from a Synapse discovery directory (adapter_options.source_dir).
    This lets the accelerator run end-to-end immediately - it is how the bundled
    Northwind demo runs (examples/northwind/).
  * full parse: an Automic XML + Synapse ARM + DW SQL parser plugs in here; porting
    such a parser is a mechanical lift documented in README.md. The fast-path is used
    by the demo so the example is runnable out of the box.
"""
from __future__ import annotations

import csv
import os
import re
import shutil
from typing import Dict, List

from core.graph import Graph
from adapters.base import SourceAdapter


class SynapseAdapter(SourceAdapter):
    name = "synapse"

    def _source_dir(self) -> str:
        return self.opts.get("source_dir", self.cfg.p(self.cfg.graph_dir))

    def _artifacts_dir(self) -> str:
        return self.opts.get("artifacts_dir", self.cfg.p(self.cfg.artifacts_dir))

    # ---- 1. collect --------------------------------------------------------
    def collect(self) -> str:
        """Ensure raw artifacts are present. Fast-path copies the pre-built graph."""
        src = self._source_dir()
        dst_obj = self.cfg.objects_csv()
        dst_edge = self.cfg.edges_csv()
        os.makedirs(os.path.dirname(dst_obj), exist_ok=True)
        for name, dst in (("objects.csv", dst_obj), ("edges.csv", dst_edge)):
            s = os.path.join(src, name)
            if os.path.exists(s) and os.path.abspath(s) != os.path.abspath(dst):
                shutil.copyfile(s, dst)
        # bring connections along if present
        sc = os.path.join(src, "connections.csv")
        if os.path.exists(sc):
            dc = self.cfg.out("connections.csv")
            if os.path.abspath(sc) != os.path.abspath(dc):
                os.makedirs(os.path.dirname(dc), exist_ok=True)
                shutil.copyfile(sc, dc)
        return self._artifacts_dir()

    # ---- 2. parse ----------------------------------------------------------
    def parse(self) -> Graph:
        obj, edge = self.cfg.objects_csv(), self.cfg.edges_csv()
        if not (os.path.exists(obj) and os.path.exists(edge)):
            self.collect()
        if not (os.path.exists(obj) and os.path.exists(edge)):
            raise FileNotFoundError(
                "No objects.csv/edges.csv found. Set adapter_options.source_dir to a "
                "Synapse discovery directory (e.g. examples/northwind/), or plug in a "
                "full source parser."
            )
        return Graph.load(obj, edge, self.cfg.pipeline_types, self.cfg.table_types)

    # ---- 3. ddl index ------------------------------------------------------
    def ddl_index(self) -> Dict[str, List[str]]:
        """Walk artifacts/DW/<db>/<schema>/{Tables,Views}/<name>.sql -> columns.

        Tables parse from CREATE TABLE (...); views (first-class) parse their projected
        column list from CREATE VIEW ... AS SELECT ..., so view outputs are identified
        with the same fidelity as tables.
        """
        root = os.path.join(self._artifacts_dir(), "DW")
        index: Dict[str, List[str]] = {}
        if not os.path.isdir(root):
            return index
        for dbdir in _subdirs(root):
            for schemadir in _subdirs(dbdir):
                schema = os.path.basename(schemadir).lower()
                for sub in ("Tables", "Views"):
                    d = os.path.join(schemadir, sub)
                    if not os.path.isdir(d):
                        continue
                    for fn in os.listdir(d):
                        if not fn.lower().endswith(".sql"):
                            continue
                        short = fn[:-4].lower()
                        path = os.path.join(d, fn)
                        cols = (_cols_from_view(path) if sub == "Views"
                                else _cols_from_ddl(path))
                        if cols:
                            index[f"{schema}.{short}"] = cols
        return index

    # ---- 6. Stage-1 asset exports -----------------------------------------
    def export_schedules(self) -> List[dict]:
        """Automic (or any scheduler) triggers that invoke pipelines.

        Fast-path: reuse an exported schedules.csv from the discovery dir if present;
        else derive one trigger per pipeline from its job_class in the graph.
        """
        src = os.path.join(self._source_dir(), "schedules.csv")
        if os.path.exists(src):
            with open(src, newline="") as f:
                return list(csv.DictReader(f))
        return super().export_schedules()

    def export_configs(self) -> Dict[str, List[dict]]:
        """Control/config DB tables as CSV rows.

        Fast-path: reuse exported CSVs under <source_dir>/configs/<table>.csv if present;
        else emit a deterministic header row per CONFIG_TABLE from its DDL columns.
        """
        cdir = os.path.join(self._source_dir(), "configs")
        if os.path.isdir(cdir):
            out: Dict[str, List[dict]] = {}
            for fn in os.listdir(cdir):
                if fn.lower().endswith(".csv"):
                    with open(os.path.join(cdir, fn), newline="") as f:
                        out[fn[:-4]] = list(csv.DictReader(f))
            if out:
                return out
        return super().export_configs()

    # ---- 7. Stage-0 identity/security exports -----------------------------
    def _security_dir(self) -> str:
        return os.path.join(self._artifacts_dir(), "security")

    def _read_csv(self, name: str):
        path = os.path.join(self._security_dir(), name)
        if os.path.exists(path):
            with open(path, newline="") as f:
                return list(csv.DictReader(f))
        return None

    def export_principals(self) -> List[dict]:
        rows = self._read_csv("principals.csv")
        return rows if rows is not None else super().export_principals()

    def export_grants(self) -> List[dict]:
        rows = self._read_csv("grants.csv")
        return rows if rows is not None else super().export_grants()

    def export_secrets(self) -> List[dict]:
        rows = self._read_csv("secrets.csv")
        return rows if rows is not None else super().export_secrets()

    def classify_data(self) -> List[dict]:
        rows = self._read_csv("classification.csv")
        return rows if rows is not None else super().classify_data()

    def export_security_facts(self) -> Dict[str, object]:
        import json as _json
        path = os.path.join(self._security_dir(), "security_facts.json")
        if os.path.exists(path):
            try:
                return _json.load(open(path))
            except Exception:
                pass
        return super().export_security_facts()

    # ---- 4. connections ----------------------------------------------------
    def connections(self) -> List[dict]:
        path = self.cfg.out("connections.csv")
        if not os.path.exists(path):
            src = os.path.join(self._source_dir(), "connections.csv")
            if os.path.exists(src):
                path = src
        if not os.path.exists(path):
            return []
        with open(path, newline="") as f:
            return list(csv.DictReader(f))

    # ---- 8. knowledge-base manifest (Synapse specifics) -------------------
    @classmethod
    def kb_manifest(cls) -> List[dict]:
        m = SourceAdapter.kb_manifest()
        how = {
            "graph": "From Synapse: export the DW dependency graph (or the Automic XML + "
                     "ARM templates) as objects.csv/edges.csv. MAYA can also parse raw "
                     "T-SQL/ARM/Automic to derive them.",
            "ddl": "From Synapse DW: script CREATE TABLE/VIEW for every object into "
                   "artifacts/DW/<db>/<schema>/{Tables,Views}/<name>.sql.",
            "connections": "Export Synapse linked services / JDBC connections as "
                           "connections.csv.",
            "schedules": "Export Automic (or ADF) triggers as schedules.csv.",
            "security": "Export SQL logins/AD groups, GRANTs, secret scopes, and "
                        "classification into artifacts/security/*.",
            "bi": "Export the Power BI/Tableau/Looker package that reads this DW.",
        }
        for entry in m:
            if entry["kind"] in how:
                entry["instructions"] = how[entry["kind"]]
        return m

    # ---- 5. dialect translate ---------------------------------------------
    def dialect_translate(self, sql: str) -> str:
        """Assistive T-SQL -> Spark SQL rewrites (agent still verifies)."""
        s = sql
        s = re.sub(r"\[([A-Za-z0-9_]+)\]", r"\1", s)                 # [id] -> id
        s = re.sub(r"\bISNULL\s*\(", "coalesce(", s, flags=re.I)
        s = re.sub(r"\bGETDATE\s*\(\s*\)", "current_timestamp()", s, flags=re.I)
        s = re.sub(r"\bGETUTCDATE\s*\(\s*\)", "current_timestamp()", s, flags=re.I)
        s = re.sub(r"\bLEN\s*\(", "length(", s, flags=re.I)
        s = re.sub(r"\bNEWID\s*\(\s*\)", "uuid()", s, flags=re.I)
        s = re.sub(r"\bGETUTCDATE\b", "current_timestamp()", s, flags=re.I)
        # SELECT TOP n ...  -> ... LIMIT n   (best-effort; agent confirms)
        m = re.search(r"\bTOP\s+(\d+)\b", s, flags=re.I)
        if m:
            s = re.sub(r"\bTOP\s+\d+\b", "", s, flags=re.I).rstrip()
            s = s + f"\n-- LIMIT {m.group(1)}  (verify placement)"
        return s


def _cols_from_view(path: str) -> List[str]:
    """Projected column names from a CREATE VIEW ... AS SELECT ... FROM ... .

    Best-effort: parse the top-level SELECT list (before FROM), taking each item's alias
    (after AS / trailing identifier) or the bare/qualified column name. Good enough to
    identify a view's output columns for scoring and docs; the agent verifies at build.
    """
    try:
        txt = open(path, errors="ignore").read()
    except Exception:
        return []
    up = txt.upper()
    si = up.find("SELECT")
    if si < 0:
        return []
    fi = up.find("FROM", si)
    seg = txt[si + 6: fi if fi > si else len(txt)]
    cols: List[str] = []
    depth = 0
    cur = ""
    parts: List[str] = []
    for ch in seg:
        if ch in "(":
            depth += 1
        elif ch in ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        cur += ch
    if cur.strip():
        parts.append(cur)
    for p in parts:
        p = p.strip().replace("[", "").replace("]", "")
        if not p or p == "*":
            continue
        m = re.search(r"\bAS\s+([A-Za-z0-9_]+)\s*$", p, flags=re.I)
        if m:
            name = m.group(1)
        else:
            tok = p.split()[-1]
            name = tok.split(".")[-1]
        if name and name not in cols:
            cols.append(name)
    return cols


def _subdirs(path: str) -> List[str]:
    try:
        return [os.path.join(path, d) for d in os.listdir(path)
                if os.path.isdir(os.path.join(path, d))]
    except OSError:
        return []


def _cols_from_ddl(path: str) -> List[str]:
    """Column names in declaration order from a CREATE TABLE .sql (balanced parens)."""
    try:
        txt = open(path, errors="ignore").read()
    except Exception:
        return []
    i = txt.upper().find("CREATE TABLE")
    if i < 0:
        return []
    j = txt.find("(", i)
    if j < 0:
        return []
    depth, parts, cur = 0, [], ""
    for ch in txt[j:]:
        if ch == "(":
            depth += 1
            if depth == 1:
                continue
        if ch == ")":
            depth -= 1
            if depth == 0:
                if cur.strip():
                    parts.append(cur.strip())
                break
        if depth == 1 and ch == ",":
            parts.append(cur.strip())
            cur = ""
            continue
        cur += ch
    skip = ("CONSTRAINT", "PRIMARY", "INDEX", "WITH", "UNIQUE", "FOREIGN",
            "CLUSTERED", "NONCLUSTERED", ")")
    names = []
    for p in parts:
        p = p.strip().replace("[", "").replace("]", "")
        if not p or p.upper().startswith(skip):
            continue
        tok = p.split()[0]
        if tok and tok not in names:
            names.append(tok)
    return names
