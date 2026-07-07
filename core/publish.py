"""
publish.py -- Stage 9 publish: commit the generated docs back to the repository.

Stages the Stage-9 markdown and records a manifest. When agents.publish_remote is True
(and a git remote is configured) it commits and pushes to agents.publish_branch; the
offline demo default writes the docs + manifest and performs a LOCAL commit only (never
pushes), so the whole twelve-stage flow is runnable without credentials.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import List


def _git(args: List[str], cwd: str) -> tuple:
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # pragma: no cover
        return 1, str(e)


def run(cfg, message: str = "") -> dict:
    root = cfg.out(os.path.join("docs", "generated"))
    if not os.path.isdir(root):
        return {"stage": "9-publish", "passed": False,
                "error": "no generated docs (run `docs` first)"}

    files = []
    for base, _dirs, fns in os.walk(root):
        for fn in fns:
            if fn.endswith(".md"):
                files.append(os.path.relpath(os.path.join(base, fn), cfg.base_dir))
    manifest = {"docs_root": root, "files": sorted(files), "count": len(files)}
    with open(cfg.out("stage9_publish_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)

    remote = bool(getattr(cfg.agents, "publish_remote", False))
    branch = getattr(cfg.agents, "publish_branch", "main")
    msg = message or f"docs: MAYA generated migration docs for {cfg.project_name}"

    # find the git repo root (walk up from base_dir)
    repo = cfg.base_dir
    while repo and not os.path.isdir(os.path.join(repo, ".git")):
        parent = os.path.dirname(repo)
        if parent == repo:
            repo = ""
            break
        repo = parent

    committed = pushed = False
    log = ""
    if repo:
        rc, out = _git(["add", root], repo)
        log += out
        rc, out = _git(["commit", "-m", msg, "--", root], repo)
        log += out
        committed = rc == 0
        if committed and remote:
            rc, out = _git(["push", "origin", branch], repo)
            log += out
            pushed = rc == 0

    gate = {"stage": "9-publish", "passed": True, "files": len(files),
            "repo": repo or "(none)", "committed": committed,
            "pushed": pushed, "remote_enabled": remote}
    with open(cfg.out("stage9_publish.json"), "w") as f:
        json.dump(gate, f, indent=1)
    return gate
