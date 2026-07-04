"""
cursor.py -- AgentDriver that drives real LLM coding agents via the Cursor SDK.

This is the production backend. It runs a local Cursor agent against the repo working
directory, hands it the deterministic MAYA prompt (contract + parity plan), and lets it
author `authored/<pipeline>.json`. MAYA then validates + parity-checks the output
deterministically; on drift it re-prompts the same agent with the parity report and the
original source so it can fix against ground truth.

Requires `cursor_sdk` and CURSOR_API_KEY. It is never touched by the offline demo, so
the dependency is imported lazily and failures raise a clear, actionable error.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

from .base import AgentDriver, BuildResult, FixResult


class CursorAgentDriver(AgentDriver):
    name = "cursor"

    def __init__(self, cfg):
        super().__init__(cfg)
        self._repo = cfg.base_dir or os.getcwd()
        self._authored = cfg.p(cfg.specs_dir, "authored")
        os.makedirs(self._authored, exist_ok=True)

    # ---- SDK plumbing ------------------------------------------------------
    def _sdk(self):
        try:
            from cursor_sdk import Agent, LocalAgentOptions, CursorAgentError
        except Exception as e:  # pragma: no cover - only when cursor backend selected
            raise RuntimeError(
                "agents.driver=cursor requires the Cursor SDK: "
                "`pip install cursor-sdk` and set CURSOR_API_KEY."
            ) from e
        key = os.environ.get("CURSOR_API_KEY")
        if not key:
            raise RuntimeError("CURSOR_API_KEY is not set (required for agents.driver=cursor)")
        return Agent, LocalAgentOptions, CursorAgentError, key

    def _run(self, prompt: str, pipeline: str) -> dict:
        """Run one agent to completion and return the authored JSON it wrote."""
        Agent, LocalAgentOptions, CursorAgentError, key = self._sdk()
        model = self.opts.model if self.opts else "composer-2.5"
        agent = None
        try:
            agent = Agent.create(model=model, api_key=key,
                                 local=LocalAgentOptions(cwd=self._repo))
        except CursorAgentError as e:  # startup failure
            raise RuntimeError(f"cursor agent failed to start for {pipeline}: {e}") from e
        try:
            run = agent.send(prompt)
            result = run.wait()
            if getattr(result, "status", "") == "error":
                raise RuntimeError(f"cursor run failed for {pipeline}: "
                                   f"{getattr(result, 'error', 'unknown error')}")
        finally:
            try:
                if agent is not None:
                    agent.dispose()
            except Exception:
                pass
        path = os.path.join(self._authored, f"{pipeline}.json")
        if not os.path.exists(path):
            raise RuntimeError(f"cursor agent did not write authored/{pipeline}.json")
        return json.load(open(path))

    # ---- AgentDriver contract ---------------------------------------------
    def build(self, ctx: dict, prompt: str = "") -> BuildResult:
        pipe = ctx.get("pipeline", "")
        if not prompt:
            from core import orchestration as orch
            prompt = orch.prompt(self.cfg, pipe)
        spec = self._run(prompt, pipe)
        return BuildResult(pipeline=pipe, spec=spec, ok=True, agent_id=self.name)

    def fix(self, ctx: dict, spec: dict, parity_report: dict,
            original_code: Optional[Dict[str, str]] = None) -> FixResult:
        pipe = ctx.get("pipeline", "")
        prompt = (
            f"# Fix parity drift for {pipe}\n\n"
            "The Databricks build you authored does not match the original source. Compare "
            "your authored code against the ORIGINAL source below and fix it so parity is "
            "EXACT. Do not invent logic; match the source. Rewrite "
            f"authored/{pipe}.json.\n\n"
            f"## Parity report\n```json\n{json.dumps(parity_report, indent=1)}\n```\n\n"
            f"## Original source\n```json\n{json.dumps(original_code or {}, indent=1)}\n```\n"
        )
        newspec = self._run(prompt, pipe)
        return FixResult(pipeline=pipe, spec=newspec, changed=True)

    def convert_bi(self, obj) -> str:
        Agent, LocalAgentOptions, CursorAgentError, key = self._sdk()
        model = self.opts.model if self.opts else "composer-2.5"
        prompt = (
            "Translate this BI query to Databricks SQL, repointing tables to the certified "
            "Databricks gold tables. Return ONLY the SQL.\n\n"
            f"Original ({obj.system}): {obj.original_query}\n"
            f"Target tables: {', '.join(obj.target_tables)}\n"
        )
        agent = Agent.create(model=model, api_key=key,
                             local=LocalAgentOptions(cwd=self._repo))
        try:
            result = agent.send(prompt).wait()
            return getattr(result, "text", "") or obj.original_query
        finally:
            try:
                agent.dispose()
            except Exception:
                pass
