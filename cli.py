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
  certify     whole-system rollup: is the migration complete? (--gates results.json)
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
from core import score as score_mod
from core import replicate as replicate_mod
from core import pipeline_spec as spec_mod
from core import conformance as conformance_mod
from core import docs as docs_mod
from core import publish as publish_mod
from core import readiness as readiness_mod
from core import identity as identity_mod
from core import enablement as enablement_mod
from core import stages as stages_mod


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


def cmd_certify(args):
    cfg = _cfg(args)
    idx = orch.load_index(cfg)
    waves = {r["pipeline"]: orch._wave(r["wave"]) for r in idx}

    gates = {}
    if args.gates and os.path.exists(args.gates):
        raw = json.load(open(args.gates))
        for pipe, v in raw.items():
            gates[pipe] = {"status": v} if isinstance(v, str) else v
    else:
        # no live parity results: every pipeline is un-certified (build in progress)
        gates = {r["pipeline"]: {"status": "BLOCKED"} for r in idx}

    bi_done = {}
    try:
        objs = bi_mod.load_objects(cfg)
        bi_done = {o.obj_id: bool(getattr(o, "converted_query", "")) for o in objs}
    except Exception:
        bi_done = {}

    r = val.system_certification(gates, bi_done=bi_done or None, waves=waves)
    t = r["totals"]
    print(f"certify: {r['status']}")
    print(f"  pipelines: {t['certified']} certified / {t['provisional']} provisional / "
          f"{t['blocked']} blocked (of {t['pipelines']})")
    if r["bi"]["total"]:
        print(f"  BI objects: {r['bi']['done']}/{r['bi']['total']} migrated")
    for w, b in r["by_wave"].items():
        print(f"  wave {w}: {b['certified']}/{b['total']} certified, "
              f"{b['provisional']} provisional, {b['blocked']} blocked")
    if r["blocking"]:
        print(f"  blocking: {', '.join(str(x) for x in r['blocking'][:12])}")
    print("  states: MIGRATION_IN_PROGRESS -> SYSTEM_PROVISIONAL -> MIGRATION_COMPLETE")
    if not (args.gates and os.path.exists(args.gates)):
        print("  (pass --gates <json> of pipeline->maya_gate results for live status)")


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


def cmd_readiness(args):
    cfg = _cfg(args)
    g = readiness_mod.run(cfg)
    print(f"readiness (Stage 0): {'PASS' if g['passed'] else 'FAIL'}")
    print(f"  principals: {g['principals']} ({g['groups']} groups, "
          f"{g['service_principals']} SP, {g['users']} users), grants: {g['grants']}")
    print(f"  secrets: {g['secrets']}, classified columns: {g['classified_columns']} "
          f"({g['pii_columns']} PII)")
    for k in ("unknown_principals", "unresolved_grants", "bad_secret_connections",
              "unsecured_connections", "unmasked_pii"):
        if g.get(k):
            print(f"  {k}: {', '.join(g[k][:12])}")
    sys.exit(0 if g["passed"] else 1)


def cmd_identity(args):
    cfg = _cfg(args)
    g = identity_mod.run(cfg)
    print(f"identity (Stage 7): {'PASS' if g['passed'] else 'FAIL'}")
    print(f"  grants mapped: {g['grants_mapped']}/{g['grants_total']}, "
          f"masked columns: {g['masked_columns']}, row filters: {g['row_filters']}")
    print(f"  secret scope: {g['secret_scope']} ({g['secrets']} secrets) -> {g['sql']}")
    if g.get("unmasked_pii"):
        print(f"  unmasked PII: {', '.join(g['unmasked_pii'][:12])}")
    if g.get("unsecured_connections"):
        print(f"  unsecured connections: {', '.join(g['unsecured_connections'][:12])}")
    sys.exit(0 if g["passed"] else 1)


def cmd_enablement(args):
    cfg = _cfg(args)
    g = enablement_mod.run(cfg)
    print(f"enablement (Stage 8): {'PASS' if g['passed'] else 'FAIL'}")
    print(f"  training packs: {g['training_packs']}, runbooks: {g['runbooks']}, "
          f"monitors: {g['monitors']}, alerts: {g['alerts']}")
    for c in g.get("go_no_go", []):
        print(f"  [{'x' if c['ok'] else ' '}] {c['item']}")
    sys.exit(0 if g["passed"] else 1)


def cmd_score(args):
    cfg = _cfg(args)
    g = score_mod.run(cfg)
    print(f"score (Stage 1): {'PASS' if g['passed'] else 'FAIL'}")
    print(f"  pipelines at 100%: {g['pipelines_at_100']}/{g['pipelines_scored']}")
    print(f"  tables+views: {g['tables_views']} ({g['views']} views), "
          f"unidentified: {len(g['unidentified'])}")
    print(f"  external systems (call-as-is): {', '.join(g['external_systems']) or '-'}")
    print(f"  order verify: {'PASS' if g['verify_passed'] else 'FAIL'}")
    if g["unidentified"]:
        print(f"  unidentified: {', '.join(g['unidentified'][:12])}")
    sys.exit(0 if g["passed"] else 1)


def cmd_replicate(args):
    cfg = _cfg(args)
    g = replicate_mod.run(cfg)
    print(f"replicate (Stage 2): {'PASS' if g['passed'] else 'FAIL'}")
    print(f"  {g['replicated']}/{g['tables'] + g['views']} objects into "
          f"catalog {g['test_catalog']} ({g['fill_mode']} fill) -> "
          f"{cfg.out('stage2_replicate.sql')}")
    sys.exit(0 if g["passed"] else 1)


def cmd_specs(args):
    cfg = _cfg(args)
    g = spec_mod.run(cfg)
    if not g.get("passed"):
        print(f"specs (Stage 3): FAIL ({g.get('error', '')})")
        sys.exit(1)
    print(f"specs (Stage 3): PASS - {g['pdfs']} PDFs + {g['omnibus_pages']}-page "
          f"omnibus -> {g['dir']}")


def cmd_build(args):
    cfg = _cfg(args)
    conf = conformance_mod.run(cfg)
    print(f"conformance (Stage 4a): {'PASS' if conf['passed'] else 'FAIL'} "
          f"({conf['conforming']}/{conf['pipelines']} conform)")
    if not conf["passed"]:
        print(f"  nonconforming: {', '.join(conf['nonconforming'][:12])}")
        sys.exit(1)
    b = orch.build_swarm(cfg)
    print(f"swarm build (Stage 4b): {'PASS' if b['passed'] else 'FAIL'} "
          f"({b['dev_green']}/{b['pipelines']} dev-green across {b['waves']} waves)")
    if not b["passed"]:
        print(f"  not green: {', '.join(b['not_green'][:12])}")
        sys.exit(1)
    c = orch.certify_swarm(cfg)
    print(f"certification (Stage 4c): {'PASS' if c['passed'] else 'FAIL'} "
          f"({c['certified']}/{c['pipelines']} certified) -> {cfg.out('gates.json')}")
    if not c["passed"]:
        print(f"  not certified: {', '.join(c['not_certified'][:12])}")
    sys.exit(0 if c["passed"] else 1)


def cmd_docs(args):
    cfg = _cfg(args)
    g = docs_mod.run(cfg)
    print(f"docs (Stage 6): {'PASS' if g['passed'] else 'FAIL'} - "
          f"{g['pipelines']} pipelines, {g['tables']} tables, {g['views']} views, "
          f"{g['bi']} BI -> {g['root']}")
    sys.exit(0 if g["passed"] else 1)


def cmd_publish(args):
    cfg = _cfg(args)
    g = publish_mod.run(cfg, message=args.message or "")
    if not g.get("passed"):
        print(f"publish: FAIL ({g.get('error', '')})")
        sys.exit(1)
    print(f"publish (Stage 6): {g['files']} doc files; committed={g['committed']} "
          f"pushed={g['pushed']} (remote_enabled={g['remote_enabled']})")


def cmd_run(args):
    cfg = _cfg(args)
    if args.stage == "all":
        state = stages_mod.run_all(cfg)
        for n in sorted(stages_mod.STAGES):
            g = state["stages"].get(str(n))
            if g is None:
                print(f"  stage {n}: (not reached)")
                continue
            print(f"  stage {n} [{g.get('name','')}]: "
                  f"{'PASS' if g.get('passed') else 'FAIL'}")
        print(f"run: last_passed={state.get('last_passed', 0)}/{max(stages_mod.STAGES)}"
              f"  complete={state.get('complete', False)}")
        sys.exit(0 if state.get("complete") else 1)
    n = int(args.stage)
    g = stages_mod.run_stage(cfg, n)
    print(f"run stage {n} [{g.get('name','')}]: "
          f"{'PASS' if g.get('passed') else 'FAIL'}")
    if g.get("error"):
        print(f"  {g['error']}")
    sys.exit(0 if g.get("passed") else 1)


def cmd_bi(args):
    cfg = _cfg(args)
    if args.bi_cmd == "run":
        g = bi_mod.run(cfg)
        print(f"bi run (Stage 5): {'PASS' if g['passed'] else 'FAIL'} - "
              f"{g['done']}/{g['objects']} objects DONE "
              f"(gold-gated={g['gold_gated']})")
        if g["not_done"]:
            print(f"  not done: {', '.join(g['not_done'][:12])}")
        sys.exit(0 if g["passed"] else 1)
    if args.bi_cmd == "republish":
        objs = bi_mod.load_objects(cfg)
        conn = cfg.load_bi_connector()
        conn.connect()
        ready = [o for o in objs if o.converted_query]
        res = conn.redeploy(ready) if ready else {}
        for oid, ok in res.items():
            rec_path = os.path.join(cfg.out("bi_authored"),
                                    f"{bi_mod._safe(oid)}.json")
            rec = json.load(open(rec_path)) if os.path.exists(rec_path) else {}
            rec["republished"] = bool(ok)
            bi_mod.write_authored(cfg, oid, rec)
        print(f"bi republish: {sum(1 for v in res.values() if v)}/{len(res)} "
              f"dashboards redeployed ({conn.name})")
        return
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

    cert = sub.add_parser("certify",
                          help="whole-system rollup: is the migration complete?")
    add_common(cert)
    cert.add_argument("--gates", metavar="JSON",
                      help="pipeline->maya_gate results (else reports build progress)")
    cert.set_defaults(func=cmd_certify)

    r = sub.add_parser("report", help="branded PDF report")
    add_common(r)
    r.set_defaults(func=cmd_report)

    m = sub.add_parser("maya", help="MAYA sampling (illusion of prod)")
    m.add_argument("maya_cmd", choices=["sample"])
    add_common(m)
    m.add_argument("--pipeline")
    m.set_defaults(func=cmd_maya)

    b = sub.add_parser("bi", help="BI layer migration (dashboards + Genie AI/BI)")
    b.add_argument("bi_cmd",
                   choices=["extract", "parity", "genie", "status", "run", "republish"])
    add_common(b)
    b.add_argument("--pipeline", help="filter to one dashboard name")
    b.set_defaults(func=cmd_bi)

    # ---- full-lifecycle stage commands (additive; verbs stay as primitives) ----
    rd = sub.add_parser("readiness",
                        help="Stage 0: collect + classify identity/security/governance")
    add_common(rd)
    rd.set_defaults(func=cmd_readiness)

    sc = sub.add_parser("score", help="Stage 1: traversability + identification score")
    add_common(sc)
    sc.set_defaults(func=cmd_score)

    rp = sub.add_parser("replicate", help="Stage 2: replicate estate into test catalog")
    add_common(rp)
    rp.set_defaults(func=cmd_replicate)

    sp = sub.add_parser("specs", help="Stage 3: one branded spec PDF per pipeline")
    add_common(sp)
    sp.set_defaults(func=cmd_specs)

    bd = sub.add_parser("build", help="Stage 4: conformance + swarm build + certify")
    add_common(bd)
    bd.set_defaults(func=cmd_build)

    dc = sub.add_parser("docs", help="Stage 6: generate full migration docs")
    add_common(dc)
    dc.set_defaults(func=cmd_docs)

    pub = sub.add_parser("publish", help="Stage 6: commit generated docs back to repo")
    add_common(pub)
    pub.add_argument("--message", help="commit message")
    pub.set_defaults(func=cmd_publish)

    idn = sub.add_parser("identity",
                         help="Stage 7: UC groups/grants + masks + secrets + governance")
    add_common(idn)
    idn.set_defaults(func=cmd_identity)

    en = sub.add_parser("enablement",
                        help="Stage 8: training + runbooks + cutover/rollback + day-2 ops")
    add_common(en)
    en.set_defaults(func=cmd_enablement)

    rn = sub.add_parser("run", help="run a stage (0..11) or the whole flow (all)")
    add_common(rn)
    rn.add_argument("--stage", default="all",
                    help="stage number 0..11, or 'all' (default)")
    rn.set_defaults(func=cmd_run)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
