"""
conformance.py -- Stage 4a: prove the build is ready for the swarm.

Two assertions, no build work:
  * the topological order + waves are valid (delegates to the independent verifier), and
  * every pipeline in build_order_pipelines.csv has a Stage-3 spec PDF AND its context
    wave matches the published wave (the spec agrees with the order it will be built in).

Emits out/stage4_conformance.json. Gate passes when order is valid and every pipeline
conforms.
"""
from __future__ import annotations

import csv
import json
import os
from typing import Dict

from . import verify_order as verify_mod


def _published_waves(cfg) -> Dict[str, int]:
    path = cfg.out("build_order_pipelines.csv")
    waves: Dict[str, int] = {}
    if os.path.exists(path):
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                try:
                    waves[r["pipeline"]] = int(r["wave"])
                except (KeyError, ValueError):
                    pass
    return waves


def _context_wave(cfg, pipeline: str):
    path = cfg.p(cfg.specs_dir, "context", f"{pipeline}.json")
    if not os.path.exists(path):
        return None
    try:
        return int(json.load(open(path)).get("wave", 0))
    except Exception:
        return None


def compute(cfg) -> dict:
    verify = verify_mod.run(cfg)
    waves = _published_waves(cfg)
    spec_dir = cfg.out("specs_pdf")

    per = []
    for pipe in sorted(waves):
        pdf = os.path.join(spec_dir, f"{pipe}.pdf")
        has_pdf = os.path.exists(pdf)
        cwave = _context_wave(cfg, pipe)
        wave_ok = (cwave is not None and cwave == waves[pipe])
        per.append({"pipeline": pipe, "wave": waves[pipe], "has_pdf": has_pdf,
                    "context_wave": cwave, "wave_match": wave_ok,
                    "conforms": bool(has_pdf and wave_ok)})

    all_conform = bool(waves) and all(p["conforms"] for p in per)
    gate = {
        "stage": "4a",
        "passed": bool(verify.get("passed") and all_conform),
        "verify_passed": bool(verify.get("passed")),
        "pipelines": len(per),
        "conforming": sum(1 for p in per if p["conforms"]),
        "nonconforming": [p["pipeline"] for p in per if not p["conforms"]],
    }
    return {"per_pipeline": per, "gate": gate}


def run(cfg) -> dict:
    res = compute(cfg)
    os.makedirs(cfg.p(cfg.out_dir), exist_ok=True)
    out = {"gate": res["gate"], "per_pipeline": res["per_pipeline"]}
    with open(cfg.out("stage4_conformance.json"), "w") as f:
        json.dump(out, f, indent=1)
    return res["gate"]
