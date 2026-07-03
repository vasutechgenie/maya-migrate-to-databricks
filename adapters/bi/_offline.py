"""
_offline.py -- shared offline fast-path for the reference BI connectors.

Live extraction happens over each tool's MCP server / REST API (documented in each
connector). To keep the flow runnable without credentials, all three connectors can also
read an exported package folder containing a `bi_queries.json` array of objects:

  [{"obj_id": "...", "dashboard": "...", "tile": "...", "original_query": "...",
    "datasource": "...", "target_tables": ["gold.x"], "ordered": false}, ...]
"""
from __future__ import annotations

import json
import os
from typing import List

from core.bi import BIObject


def package_dir(connector) -> str:
    return connector.opts.get("package_dir", "")


def offline_extract(connector, system: str) -> List[BIObject]:
    d = package_dir(connector)
    path = os.path.join(d, "bi_queries.json") if d else ""
    if not path or not os.path.exists(path):
        return []
    rows = json.load(open(path))
    objs = []
    for r in rows:
        if system and r.get("system") not in (None, system):
            continue
        r.setdefault("system", system)
        objs.append(BIObject(**{k: v for k, v in r.items()
                                if k in BIObject.__dataclass_fields__}))
    return objs
