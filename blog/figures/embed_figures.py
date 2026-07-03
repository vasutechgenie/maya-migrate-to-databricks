#!/usr/bin/env python3
"""
embed_figures.py -- insert each post's figure (and an `image:` front-matter key) into
its markdown, idempotently. Safe to re-run: it skips a post that already references a
figure. Run after (re)generating figures.

  python3 embed_figures.py
"""
import os
import re

BLOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# NN -> (figure basename, journal caption)
CAPS = {
    "01": ("01_meet_maya_northwind",
           "MAYA turns a migration into a deterministic pipeline you can clone and run "
           "end to end in seconds."),
    "02": ("02_adapter_model",
           "An adapter is the only source-specific code; it emits a normalized graph, "
           "and everything downstream is source-agnostic."),
    "03": ("03_dependency_graph",
           "Lineage is derived from the source, not guessed: pipelines and tables as "
           "read/write edges across the medallion layers."),
    "04": ("04_build_order_waves",
           "Waves come from SCC + longest-path layering; a different algorithm set "
           "independently re-derives and proves them."),
    "05": ("05_pipeline_contract",
           "The build contract is derived straight from the graph: prerequisites, "
           "produced tables by layer, and parity targets."),
    "06": ("06_reusable_engines",
           "A deterministic classifier maps each pipeline pattern to one reusable "
           "engine - build the engine once, configure it many times."),
    "07": ("07_maya_dev_illusion",
           "Prove the logic on a small illusion of production - every table sampled "
           "with foreign-key closure so joins still resolve."),
    "08": ("08_maya_sit_drift_loop",
           "Full-scale parity across ten checks at a pinned watermark; one red check "
           "fails the table and opens the drift loop."),
    "09": ("09_maya_soak_sustained",
           "Point-in-time parity proves state; the soak re-proves the ongoing "
           "incremental logic at T+7 and T+14 with zero drift."),
    "10": ("10_dashboard_bi_cutover",
           "The estate advances through machine-checked gates; the BI layer is migrated "
           "and mirrored as Genie + Lakeview on certified numbers."),
}


def process(path, nn):
    base, caption = CAPS[nn]
    num = int(nn)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if "](figures/" in text:
        return "skip (already has figure)"
    # split front matter
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return "skip (no front matter)"
    fm = m.group(1)
    body = text[m.end():]
    if "image:" not in fm:
        fm = fm + f'\nimage: "figures/{base}.png"'
    fig_block = (f"![Figure {num}. {caption.split(';')[0].split('-')[0].strip()}]"
                 f"(figures/{base}.png)\n\n"
                 f"*Figure {num}. {caption}*\n\n")
    new = f"---\n{fm}\n---\n\n{fig_block}{body.lstrip()}"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return "embedded"


def main():
    for nn in sorted(CAPS):
        base = CAPS[nn][0]
        path = os.path.join(BLOG, base + ".md")
        if not os.path.exists(path):
            print(f"  {nn}: MISSING {base}.md")
            continue
        print(f"  {nn}: {process(path, nn)}")


if __name__ == "__main__":
    main()
