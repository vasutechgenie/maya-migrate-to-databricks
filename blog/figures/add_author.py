#!/usr/bin/env python3
"""
add_author.py -- put a prominent author byline at the very top of every post (above the
figure) and add an `author` front-matter key. Idempotent: re-running is a no-op.

  python3 add_author.py
"""
import os
import re

BLOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUTHOR = "Srinivas Nelakuditi"
BYLINE = ("**By Srinivas Nelakuditi**  |  Creator of MAYA - an open-source, "
          "deterministic migration accelerator")


def process(path):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if "By Srinivas Nelakuditi" in text:
        return "skip (byline present)"
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return "skip (no front matter)"
    fm = m.group(1)
    body = text[m.end():].lstrip("\n")
    if "author:" not in fm:
        fm = fm + f'\nauthor: "{AUTHOR}"'
    new = f"---\n{fm}\n---\n\n{BYLINE}\n\n{body}"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return "byline added"


def main():
    import glob
    for path in sorted(glob.glob(os.path.join(BLOG, "[0-9][0-9]_*.md"))):
        print(f"  {os.path.basename(path)}: {process(path)}")


if __name__ == "__main__":
    main()
