#!/usr/bin/env python3
"""
cli.py -- MAYA phase entrypoint.

A migration is: implement an adapter, then run the phases:

  graph       adapter parses source -> objects.csv / edges.csv
  order       topological build order (waves)
  verify      independent order validator
  context     per-pipeline build contracts (needs/logic/output)
  maya sample RI-preserving dev sampling SQL + manifest (the illusion of prod)
  orchestrate agent work queue: --status / --pending / --prompt / --validate
  validate    render MAYA parity checks for a phase (--env dev|sit|soak)
  report      branded PDF report

All commands take --config <project.yaml>.
"""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from core.config import AcceleratorConfig
from core import order as order_mod
from core import verify_order as verify_mod
from core import contract as contract_mod
from core import orchestration as orch
from core import reports as reports_mod
from core import maya as maya_mod
from core import validation as val
from core import bi as bi_mod


def _cfg(args) -> AcceleratorConfig:
    if not args.config:
        print("error: --config <project.yaml> is required", file=sys.stderr)
        sys.exit(2)
    return AcceleratorConfig.from_yaml(args.config)


def cmd_graph(args):
    cfg = _cfg(args)
    adapter = cfg.load_adapter()
    g = adapter.build_graph()
    print(f"graph: {len(g.objects)} objects, {len(g.edges)} edges -> "
          f"{cfg.objects_csv()}")


def cmd_order(args):
    cfg = _cfg(args)
    stats = order_mod.run(cfg)
    print(f"order: {stats['tables']} tables in {stats['table_waves']} waves; "
          f"{stats['pipelines']} pipelines in {stats['pipeline_waves']} waves")


def cmd_verify(args):
    cfg = _cfg(args)
    r = verify_mod.run(cfg)
    for k in ("C1_completeness", "C2_wave_agreement", "C3_forward_edges",
              "C4_build_sim"):
        print(f"  {k}: {r.get(k)}")
    print(f"verify: {'PASS' if r.get('passed') else 'FAIL'} "
          f"({r['n_tables']} tables, {r['n_waves']} waves)")
    sys.exit(0 if r.get("passed") else 1)


def cmd_context(args):
    cfg = _cfg(args)
    adapter = cfg.load_adapter()
    try:
        ddl = adapter.ddl_index()
    except Exception as e:
        print(f"  (ddl_index unavailable: {e})")
        ddl = {}

    def prog(i, n):
        if i % 50 == 0 or i == n:
            print(f"  context {i}/{n}")
    stats = contract_mod.generate_all(cfg, ddl_index=ddl, progress=prog)
    print(f"context: {stats['pipelines']} contracts, "
          f"{stats['parity_targets']} parity targets -> {cfg.specs_dir}/context")


def cmd_orchestrate(args):
    cfg = _cfg(args)
    if args.status:
        s = orch.status(cfg)
        print(f"orchestrate: {s['done']}/{s['total']} done, {s['pending']} pending")
        for w, (d, t) in s["by_wave"].items():
            print(f"  wave {w}: {d}/{t}")
    elif args.prompt:
        print(orch.prompt(cfg, args.prompt))
    elif args.validate:
        if args.validate == "all":
            r = orch.validate_all(cfg)
            print(f"validate: {r['ok']}/{r['total']} ok")
            for f in r["failures"][:50]:
                print(f"  FAIL {f['pipeline']}: {f.get('missing') or f.get('error')}")
        else:
            print(json.dumps(orch.validate(cfg, args.validate), indent=1))
    else:
        rows = orch.pending(cfg, wave=args.wave, limit=args.limit, kind=args.kind)
        for r in rows:
            print(f"  w{r['wave']} {r['kind']:16} {r['engine']} {r['pipeline']}")
        print(f"pending: {len(rows)}")


def cmd_report(args):
    cfg = _cfg(args)
    out = reports_mod.build_report(cfg)
    print(f"report: {out}")


def cmd_validate(args):
    cfg = _cfg(args)
    ctx_path = cfg.p(cfg.specs_dir, "context", f"{args.pipeline}.json")
    if not os.path.exists(ctx_path):
        print(f"error: no context for {args.pipeline} (run `context`)", file=sys.stderr)
        sys.exit(2)
    ctx = json.load(open(ctx_path))
    env = args.env
    label = {"dev": "Dev", "sit": "SIT", "soak": "Soak"}.get(env, env.upper())
    print(f"# MAYA-{label} parity plan for {args.pipeline} ({env})")
    if env == "soak":
        wins = ", ".join(f"T+{d}" for d in cfg.maya.soak_windows_days)
        print(f"# sustained parallel-run parity at {wins} (cumulative + delta), zero drift")
    print(f"# checks: {', '.join(val.checks_for(env))}\n")
    for p in ctx.get("parity", []):
        t = val.for_env(cfg, p["table"], keys=[], columns=p.get("ddl_columns", []),
                        env=env)
        print(f"## {p['table']}  ({p['layer']})")
        for name, sql in val.all_sql(t).items():
            print(f"-- [{name}]\n{sql}\n")


def cmd_maya(args):
    if args.maya_cmd != "sample":
        print("usage: cli.py maya sample --config ... [--pipeline NAME]", file=sys.stderr)
        sys.exit(2)
    cfg = _cfg(args)
    ctx_dir = cfg.p(cfg.specs_dir, "context")
    if args.pipeline:
        pipes = [args.pipeline]
    else:
        pipes = [f[:-5] for f in os.listdir(ctx_dir)] if os.path.isdir(ctx_dir) else []
    all_manifest, sql_lines = [], []
    for pipe in pipes:
        cp = os.path.join(ctx_dir, f"{pipe}.json")
        if not os.path.exists(cp):
            print(f"  skip {pipe}: no context", file=sys.stderr)
            continue
        ctx = json.load(open(cp))
        specs = maya_mod.specs_from_context(cfg, ctx)
        plan = maya_mod.plan_samples(cfg, specs)
        sql_lines.append(f"-- ===== {pipe} =====")
        sql_lines.extend(plan["sql"])
        for row in plan["manifest"]:
            row["pipeline"] = pipe
            all_manifest.append(row)
    sql_out = cfg.out("maya_sample.sql")
    os.makedirs(os.path.dirname(sql_out), exist_ok=True)
    with open(sql_out, "w") as f:
        f.write("\n\n".join(sql_lines) + "\n")
    man_out = cfg.out("maya_sample_manifest.csv")
    if all_manifest:
        cols = ["pipeline", "table", "kind", "target_rows", "keys", "seed", "sampling"]
        with open(man_out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_manifest)
    print(f"maya sample: {len(all_manifest)} tables across {len(pipes)} pipeline(s) -> "
          f"{sql_out}, {man_out}")


def cmd_bi(args):
    cfg = _cfg(args)
    if args.bi_cmd == "extract":
        conn = cfg.load_bi_connector()
        conn.connect()
        objs = conn.extract_queries()
        bi_mod.save_objects(cfg, objs)
        print(f"bi extract: {len(objs)} BI objects ({conn.name}) -> "
              f"{cfg.out('bi_objects.json')}")
        return
    objs = bi_mod.load_objects(cfg)
    if not objs:
        print("no BI objects; run `bi extract` first (or set package_dir)",
              file=sys.stderr)
        sys.exit(2)
    if args.pipeline:  # here --pipeline filters by dashboard name
        objs = [o for o in objs if o.dashboard == args.pipeline]

    if args.bi_cmd == "parity":
        for o in objs:
            print(f"## {o.obj_id}  ({o.system} / {o.dashboard})")
            if not o.converted_query:
                print("-- converted_query missing; agent must convert first (B1)\n")
                continue
            for name, sql in bi_mod.result_parity_sql(cfg, o).items():
                print(f"-- [{name}]\n{sql}\n")
    elif args.bi_cmd == "genie":
        by_dash = {}
        for o in objs:
            by_dash.setdefault(o.dashboard, []).append(o)
        out = {"genie_spaces": [], "lakeview_dashboards": []}
        for dash, group in by_dash.items():
            out["genie_spaces"].append(bi_mod.genie_space_spec(cfg, dash, group))
            out["lakeview_dashboards"].append(bi_mod.lakeview_spec(cfg, dash, group))
        path = cfg.out("bi_genie_lakeview.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(out, open(path, "w"), indent=1)
        print(f"bi genie: {len(out['genie_spaces'])} Genie space(s) + "
              f"{len(out['lakeview_dashboards'])} Lakeview dashboard(s) -> {path}")
    elif args.bi_cmd == "status":
        s = bi_mod.status(cfg)
        print(f"bi: {s['done']}/{s['total']} done, {s['pending']} pending")
        for sysname, (d, t) in s["by_system"].items():
            print(f"  {sysname}: {d}/{t}")


def build_parser():
    p = argparse.ArgumentParser(prog="maya",
                                description="MAYA - Migration Accelerator")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp):
        sp.add_argument("--config", help="project YAML config")

    g = sub.add_parser("graph", help="adapter parses source -> normalized graph")
    add_common(g)
    g.set_defaults(func=cmd_graph)

    o = sub.add_parser("order", help="topological build order (waves)")
    add_common(o)
    o.set_defaults(func=cmd_order)

    v = sub.add_parser("verify", help="independent build-order validator")
    add_common(v)
    v.set_defaults(func=cmd_verify)

    c = sub.add_parser("context", help="per-pipeline build contracts")
    add_common(c)
    c.set_defaults(func=cmd_context)

    orc = sub.add_parser("orchestrate", help="agent work queue")
    add_common(orc)
    orc.add_argument("--status", action="store_true")
    orc.add_argument("--pending", action="store_true")
    orc.add_argument("--prompt", metavar="PIPELINE")
    orc.add_argument("--validate", metavar="PIPELINE|all")
    orc.add_argument("--wave", type=int)
    orc.add_argument("--kind")
    orc.add_argument("--limit", type=int)
    orc.set_defaults(func=cmd_orchestrate)

    val_p = sub.add_parser("validate", help="render MAYA parity checks for a phase")
    add_common(val_p)
    val_p.add_argument("--pipeline", required=True)
    val_p.add_argument("--env", choices=["dev", "sit", "soak"], default="dev")
    val_p.set_defaults(func=cmd_validate)

    r = sub.add_parser("report", help="branded PDF report")
    add_common(r)
    r.set_defaults(func=cmd_report)

    m = sub.add_parser("maya", help="MAYA sampling (illusion of prod)")
    m.add_argument("maya_cmd", choices=["sample"])
    add_common(m)
    m.add_argument("--pipeline")
    m.set_defaults(func=cmd_maya)

    b = sub.add_parser("bi", help="BI layer migration (dashboards + Genie AI/BI)")
    b.add_argument("bi_cmd", choices=["extract", "parity", "genie", "status"])
    add_common(b)
    b.add_argument("--pipeline", help="filter to one dashboard name")
    b.set_defaults(func=cmd_bi)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
