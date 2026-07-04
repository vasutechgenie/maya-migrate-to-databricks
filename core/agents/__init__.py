"""
core.agents -- the AI coding-agent swarm driver.

MAYA prepares deterministic work (per-pipeline contracts, prompts, parity plans) and a
pool of coding agents authors + fixes the real Databricks build. This package abstracts
"who runs the agent" behind a single `AgentDriver` protocol with two backends:

  * OfflineAgentDriver - deterministic, no-LLM; authors specs straight from the source
    logic + context pack. Makes the Northwind demo runnable end to end with zero calls.
  * CursorAgentDriver  - drives real LLM coding agents via the Cursor SDK (cursor_sdk).

`get_driver(cfg)` returns the backend named by cfg.agents.driver.
"""
from __future__ import annotations

from .base import AgentDriver, BuildResult, FixResult


def get_driver(cfg) -> AgentDriver:
    """Instantiate the AgentDriver selected by cfg.agents.driver."""
    name = (getattr(cfg, "agents", None) and cfg.agents.driver) or "offline"
    if name == "offline":
        from .offline import OfflineAgentDriver
        return OfflineAgentDriver(cfg)
    if name == "cursor":
        from .cursor import CursorAgentDriver
        return CursorAgentDriver(cfg)
    raise ValueError(f"unknown agents.driver {name!r} (expected offline|cursor)")


__all__ = ["AgentDriver", "BuildResult", "FixResult", "get_driver"]
