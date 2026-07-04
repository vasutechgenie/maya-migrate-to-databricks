"""
base.py -- the AgentDriver contract every swarm backend implements.

A driver only has to do three things MAYA cannot do deterministically:

  * build(cfg, ctx)              -> author the Databricks build spec for a pipeline
  * fix(cfg, ctx, spec, report)  -> revise the spec to close a parity failure (drift loop)
  * convert_bi(cfg, obj)         -> translate one BI query to Databricks SQL

Everything else (queueing, parity, gating, certification, docs) is deterministic core.
The authored spec is a plain dict with the keys orchestration.REQUIRED expects
(summary + bronze/silver/gold{desc,code} for medallion, summary + parity otherwise).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BuildResult:
    pipeline: str
    spec: dict                       # the authored spec dict
    ok: bool = True
    agent_id: str = ""               # backend run id (cursor) for observability
    notes: str = ""


@dataclass
class FixResult:
    pipeline: str
    spec: dict
    changed: bool = True
    reason_code: str = ""            # a validation.REASON_CODES key when known
    notes: str = ""


class AgentDriver(ABC):
    """Base class for the two swarm backends (offline / cursor)."""

    name: str = "base"

    def __init__(self, cfg):
        self.cfg = cfg
        self.opts = getattr(cfg, "agents", None)

    @abstractmethod
    def build(self, ctx: dict, prompt: str = "") -> BuildResult:
        """Author the Databricks build spec for a single pipeline from its context pack."""

    @abstractmethod
    def fix(self, ctx: dict, spec: dict, parity_report: dict,
            original_code: Optional[Dict[str, str]] = None) -> FixResult:
        """Revise a spec to close a parity failure, comparing against the original code."""

    @abstractmethod
    def convert_bi(self, obj) -> str:
        """Translate one BI object's original query to Databricks SQL (repointed)."""

    # context-manager convenience so callers can `with get_driver(cfg) as d:`
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def close(self):
        """Release any backend resources (no-op by default)."""
