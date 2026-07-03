#!/usr/bin/env python3
"""
series_format.py -- turn the 15 posts into a cohesive, numbered series.

Adds (idempotently):
  - a series header line right under the byline: "Deterministic Migration
    Engineering - Part N of 15"
  - a navigation footer that replaces the old "This is post N of ..." line with a
    prev/next pointer to the next part's title.

  python3 series_format.py
"""
import glob
import os
import re

BLOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERIES = "Migrating with MAYA"
TOTAL = 10

# ordered short titles (Part N)
SHORT = [
    "MAYA is Open Source - Meet Northwind",
    "The Adapter Model",
    "Building the Dependency Graph",
    "Build Order, Waves & the Independent Verifier",
    "The Deterministic Pipeline Contract",
    "Reusable Engines E1-E7",
    "MAYA-Dev: the Illusion of Production",
    "MAYA-SIT: 10-Check Parity & the Drift Loop",
    "MAYA-Soak: Sustained Parity, Zero Drift",
    "Dashboard, BI/Genie & Cutover",
]

HEADER_RE = re.compile(rf"(?m)^\*{re.escape(SERIES)} - Part \d+ of {TOTAL}\*$")
FOOTER_RE = re.compile(
    rf"(?m)^(This is post \d+ of a {TOTAL}-part series[^\n]*|"
    rf"\*\*Part \d+ of {TOTAL} - [^\n]*)$")
BYLINE_RE = re.compile(r"(?m)^\*\*By Srinivas Nelakuditi\*\*[^\n]*$")


def footer_for(n):
    total = len(SHORT)
    if n < total:
        return (f"**Part {n} of {TOTAL} - {SERIES}.** Next up, Part {n + 1}: "
                f"\"{SHORT[n]}\". The whole framework is open source - clone it and run "
                f"`make demo`.")
    return (f"**Part {n} of {TOTAL} - {SERIES}.** That is the series - thank you for "
            f"reading. New here? Start with Part 1: \"{SHORT[0]}\", or just clone the "
            f"repo and run `make demo`.")


def process(path, n):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    header = f"*{SERIES} - Part {n} of {TOTAL}*"

    # 1) footer: replace old trailing line (or refresh an existing nav footer)
    new_footer = footer_for(n)
    if FOOTER_RE.search(text):
        text = FOOTER_RE.sub(lambda m: new_footer, text, count=1)
    else:
        text = text.rstrip() + "\n\n" + new_footer + "\n"

    # 2) header: insert right after the byline, once
    if not HEADER_RE.search(text):
        m = BYLINE_RE.search(text)
        if m:
            end = m.end()
            text = text[:end] + "\n\n" + header + text[end:]
    return text


def main():
    posts = sorted(glob.glob(os.path.join(BLOG, "[0-9][0-9]_*.md")))
    for i, path in enumerate(posts, 1):
        out = process(path, i)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"  Part {i:2d}: {os.path.basename(path)}")


if __name__ == "__main__":
    main()
