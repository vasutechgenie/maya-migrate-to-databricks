"""
order.py -- topological build order over the normalized graph.

Table-level order is primary (a pipeline reads/writes many tables and metadata-driven
pipelines emit different tables per config row, so the real constraint is between
tables). A pipeline-level order is derived for the actual build units.

Emits (in cfg.out_dir):
  build_order_tables.csv     table -> wave, cycle, producers, #dependents
  build_order_pipelines.csv  pipeline -> wave, table I/O counts
  build_order.md             human-readable wave plan

Algorithms: iterative Tarjan SCC + longest-path (Kahn) layering.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict, deque
from typing import Dict, List

from .graph import Graph


def tarjan_scc(nodes, succ):
    index, low, onstack, stack = {}, {}, set(), []
    comp_of, comps, counter = {}, [], [0]
    for root in nodes:
        if root in index:
            continue
        work = [(root, 0)]
        while work:
            v, pi = work[-1]
            if pi == 0:
                index[v] = low[v] = counter[0]
                counter[0] += 1
                stack.append(v)
                onstack.add(v)
            recurse = False
            succ_v = succ.get(v, ())
            i = pi
            while i < len(succ_v):
                w = succ_v[i]
                if w not in index:
                    work[-1] = (v, i + 1)
                    work.append((w, 0))
                    recurse = True
                    break
                elif w in onstack:
                    low[v] = min(low[v], index[w])
                i += 1
            if recurse:
                continue
            for w in succ_v:
                if w in comp_of:
                    continue
                if w in onstack:
                    low[v] = min(low[v], low[w])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    onstack.discard(w)
                    comp_of[w] = len(comps)
                    comp.append(w)
                    if w == v:
                        break
                comps.append(comp)
            work.pop()
    return comp_of, comps


def longest_path_layers(n_comps, dag_succ):
    indeg = defaultdict(int)
    for u in range(n_comps):
        for v in dag_succ.get(u, ()):
            indeg[v] += 1
    layer = [0] * n_comps
    q = deque([u for u in range(n_comps) if indeg[u] == 0])
    while q:
        u = q.popleft()
        for v in dag_succ.get(u, ()):
            if layer[v] < layer[u] + 1:
                layer[v] = layer[u] + 1
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return layer


def compute(g: Graph):
    """Return (table_wave, pipe_wave, meta) dicts without writing files."""
    reads, writes = g.reads, g.writes

    # table dependency graph: input -> output
    all_tables, written_tables, read_tables = set(), set(), set()
    tsucc = defaultdict(set)
    for w, outs in writes.items():
        ins = reads.get(w, set())
        for o in outs:
            written_tables.add(o)
            all_tables.add(o)
            for i in ins:
                all_tables.add(i)
                if i != o:
                    tsucc[i].add(o)
    for w, ins in reads.items():
        all_tables |= ins
        read_tables |= ins
    defined_tables = set()
    for k, o in g.objects.items():
        if o.get("type") in g.table_types:
            nm = o["name"].lower()
            all_tables.add(nm)
            if o.get("source_file"):
                defined_tables.add(nm)

    source_tables = read_tables - written_tables
    tnodes = sorted(all_tables)
    tsucc_l = {n: sorted(tsucc.get(n, ())) for n in tnodes}
    comp_of, comps = tarjan_scc(tnodes, tsucc_l)
    dag = defaultdict(set)
    for u in tnodes:
        cu = comp_of[u]
        for v in tsucc_l[u]:
            cv = comp_of[v]
            if cu != cv:
                dag[cu].add(cv)
    layer = longest_path_layers(len(comps), {k: list(v) for k, v in dag.items()})
    table_wave = {t: layer[comp_of[t]] for t in tnodes}

    # pipeline level
    pipe_keys = g.pipeline_keys()
    pipe_writes, pipe_reads, pipe_procs = {}, {}, {}
    for pk in pipe_keys:
        ins, outs, procs = g.pipeline_io(pk)
        pipe_writes[pk], pipe_reads[pk], pipe_procs[pk] = outs, ins, procs
    producers_by_table = defaultdict(set)
    for pk in pipe_keys:
        for t in pipe_writes[pk]:
            producers_by_table[t].add(pk)
    psucc = defaultdict(set)
    for pk in pipe_keys:
        for t in pipe_reads[pk]:
            for prod in producers_by_table.get(t, ()):
                if prod != pk:
                    psucc[prod].add(pk)
    for parent, kids in g.exec_pipe.items():
        for kid in kids:
            if parent in pipe_writes and kid in pipe_writes:
                psucc[kid].add(parent)
    pnodes = sorted(pipe_keys)
    psucc_l = {n: sorted(psucc.get(n, ())) for n in pnodes}
    pcomp_of, pcomps = tarjan_scc(pnodes, psucc_l)
    pdag = defaultdict(set)
    for u in pnodes:
        cu = pcomp_of[u]
        for v in psucc_l[u]:
            cv = pcomp_of[v]
            if cu != cv:
                pdag[cu].add(cv)
    player = longest_path_layers(len(pcomps), {k: list(v) for k, v in pdag.items()})
    pipe_wave = {pk: player[pcomp_of[pk]] for pk in pnodes}

    meta = {
        "comp_of": comp_of, "comps": comps, "tsucc": tsucc,
        "written_tables": written_tables, "source_tables": source_tables,
        "defined_tables": defined_tables, "tnodes": tnodes,
        "pipe_keys": pipe_keys, "pipe_writes": pipe_writes, "pipe_reads": pipe_reads,
        "pipe_procs": pipe_procs, "producers_by_table": producers_by_table,
        "pcomp_of": pcomp_of, "pcomps": pcomps,
    }
    return table_wave, pipe_wave, meta


def run(cfg) -> Dict[str, int]:
    """Compute and write all order artifacts. Returns simple stats."""
    g = Graph.from_config(cfg)
    table_wave, pipe_wave, m = compute(g)
    comp_of, comps = m["comp_of"], m["comps"]
    scc_size = {i: len(c) for i, c in enumerate(comps)}
    written, source, defined = (m["written_tables"], m["source_tables"],
                                m["defined_tables"])
    producers_by_table = m["producers_by_table"]
    name_of = g.name_of

    def kind_of(t):
        if t in written:
            return "derived"
        if t in source:
            return "source"
        return "isolated"

    ndep = defaultdict(int)
    for i, outs in m["tsucc"].items():
        for _o in outs:
            ndep[i] += 1

    os.makedirs(cfg.p(cfg.out_dir), exist_ok=True)
    with open(cfg.out("build_order_tables.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wave", "table", "schema", "kind", "has_ddl", "cycle_id",
                    "cycle_size", "producers", "num_dependents"])
        for t in sorted(m["tnodes"], key=lambda x: (table_wave[x], x)):
            cid = comp_of[t]
            prods = sorted({name_of[pk] for pk in producers_by_table.get(t, ())})
            w.writerow([table_wave[t], t, t.split(".")[0] if "." in t else "",
                        kind_of(t), "yes" if t in defined else "no", cid,
                        scc_size[cid], ";".join(prods), ndep.get(t, 0)])

    pipe_writes, pipe_reads = m["pipe_writes"], m["pipe_reads"]
    pcomp_of = m["pcomp_of"]
    psize = {i: len(c) for i, c in enumerate(m["pcomps"])}
    with open(cfg.out("build_order_pipelines.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wave", "pipeline", "cycle_id", "cycle_size",
                    "num_output_tables", "num_input_tables", "max_table_wave"])
        for pk in sorted(m["pipe_keys"], key=lambda x: (pipe_wave[x], name_of[x])):
            outs = pipe_writes[pk]
            mx = max((table_wave.get(t, 0) for t in outs), default=0)
            w.writerow([pipe_wave[pk], name_of[pk], pcomp_of[pk], psize[pcomp_of[pk]],
                        len(outs), len(pipe_reads[pk]), mx])

    _write_md(cfg, table_wave, pipe_wave, m)
    return {
        "tables": len(m["tnodes"]),
        "pipelines": len(m["pipe_keys"]),
        "table_waves": (max(table_wave.values()) + 1) if table_wave else 0,
        "pipeline_waves": (max(pipe_wave.values()) + 1) if pipe_wave else 0,
    }


def _write_md(cfg, table_wave, pipe_wave, m):
    pw = defaultdict(int)
    for _pk, wv in pipe_wave.items():
        pw[wv] += 1
    tw = defaultdict(int)
    for _t, wv in table_wave.items():
        tw[wv] += 1
    lines = [f"# Build order - {cfg.project_name}", "",
             f"- Tables: {len(table_wave)} across {len(tw)} waves",
             f"- Pipelines: {len(pipe_wave)} across {len(pw)} waves", "",
             "## Pipelines per wave", "", "| Wave | #Pipelines | #Tables |",
             "|---|---|---|"]
    for wv in sorted(set(pw) | set(tw)):
        lines.append(f"| {wv} | {pw.get(wv, 0)} | {tw.get(wv, 0)} |")
    with open(cfg.out("build_order.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
