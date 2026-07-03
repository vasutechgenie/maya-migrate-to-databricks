"""Shared pytest fixtures.

Runs the real MAYA phases against the bundled Northwind demo, writing derived
artifacts into a temp directory (so the committed fixtures stay pristine) and asserts
against deterministic goldens.
"""
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

NORTHWIND = os.path.join(REPO_ROOT, "examples", "northwind")
CONFIG = os.path.join(NORTHWIND, "northwind.yaml")


def _load_cfg(base_dir):
    from core.config import AcceleratorConfig
    cfg = AcceleratorConfig.from_yaml(CONFIG)
    # keep committed fixtures read-only: derive into the temp base_dir instead
    cfg.base_dir = str(base_dir)
    cfg.adapter_options = dict(cfg.adapter_options)
    cfg.adapter_options["source_dir"] = NORTHWIND
    cfg.adapter_options["artifacts_dir"] = os.path.join(NORTHWIND, "artifacts")
    return cfg


@pytest.fixture(scope="session")
def cfg(tmp_path_factory):
    """A Northwind config whose outputs land in a temp dir."""
    return _load_cfg(tmp_path_factory.mktemp("nw_out"))


@pytest.fixture(scope="session")
def built(cfg):
    """Run graph -> order -> context once; return (cfg, graph, index)."""
    import json
    from core import order as order_mod
    from core import contract as contract_mod

    adapter = cfg.load_adapter()
    graph = adapter.build_graph()
    order_mod.run(cfg)
    contract_mod.generate_all(cfg, ddl_index=adapter.ddl_index())
    index = json.load(open(cfg.p(cfg.specs_dir, "index.json")))
    return cfg, graph, index


@pytest.fixture(scope="session")
def index_by_pipeline(built):
    _, _, index = built
    return {r["pipeline"]: r for r in index}
