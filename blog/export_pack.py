#!/usr/bin/env python3
"""
export_pack.py -- build a copy-paste publishing pack for the series.

Each post is a full 600-900 word essay, which exceeds LinkedIn's 3,000-char *feed post*
limit - so the series is meant to be published as **LinkedIn Articles** (long-form, no
cap, inline image). For each post this writes the FULL, untruncated body text (byline +
series header + post + footer + hashtags) and a POSTING_CHECKLIST.md mapping each day to
its article title, paste file, and figure.

  python3 export_pack.py                 # writes ./publish_pack/
  python3 export_pack.py --out somedir
"""
import argparse
import glob
import os

from publish_to_linkedin import parse_post, to_plain_text

HERE = os.path.dirname(os.path.abspath(__file__))


def full_text(meta, body):
    text = to_plain_text(body)
    tags = meta.get("hashtags", "").strip()
    if tags:
        text = f"{text}\n\n{tags}"
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export a copy-paste publishing pack")
    ap.add_argument("--out", default=os.path.join(HERE, "publish_pack"),
                    help="output folder (default: ./publish_pack)")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    posts = sorted(glob.glob(os.path.join(HERE, "[0-9][0-9]_*.md")))
    rows = []
    for path in posts:
        meta, body = parse_post(path)
        text = full_text(meta, body)
        base = os.path.splitext(os.path.basename(path))[0]
        with open(os.path.join(args.out, base + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        fig = os.path.basename(meta.get("image", "")) or "(none)"
        rows.append((base, meta.get("title", base), meta.get("hook", ""), fig,
                     len(text.split()), len(text)))

    cl = [
        "# Posting checklist - Migrating with MAYA (10-part hands-on series)",
        "",
        "These are full-length essays (600-900 words). LinkedIn **feed posts** cap at "
        "3,000 characters, so publish each one as a **LinkedIn Article** (long-form, no "
        "cap, keeps the figure inline). Nothing is cut.",
        "",
        "### How to publish each part (LinkedIn Article)",
        "1. LinkedIn home -> **Write article** (opens the article editor).",
        "2. **Title** = the \"Article title\" column below.",
        "3. Insert the figure from `../figures/` at the top (cover image).",
        "4. Open the matching `.txt`, **copy all**, paste into the article body.",
        "5. **Publish**. Then share the article to your feed with a one-line intro so "
        "it reaches your network.",
        "",
        "Recommended cadence: **one part per day** (weekdays) or **2 per week** for a "
        "longer run. Post them in order 1 -> 10; each ends with a pointer to the next.",
        "",
        "For each part you need three fields: **Title**, **Subtitle** (LinkedIn's "
        "\"Tell readers what your article is about\" box), and the **body** (`.txt`).",
        "",
        "| Part | Article title | Subtitle (paste in the 'about' box) | Body | Cover figure |",
        "|------|---------------|-------------------------------------|------|--------------|",
    ]
    for i, (base, title, hook, fig, words, chars) in enumerate(rows, 1):
        cl.append(f"| {i} | {title} | {hook} | `{base}.txt` | `figures/{fig}` |")
    cl += [
        "",
        "## Notes",
        "- Each `.txt` already contains: your byline, the series header (\"Part N of "
        "10\"), the full essay, the next-part pointer, and hashtags. Paste as-is.",
        "- Articles support the inline figure as a cover image - add it once at the top.",
        "- Series intro (optional day 0): share `figures/00_author_card.png` or "
        "`figures/00_architecture_master.png` with a short note announcing the series.",
        "- Prefer short feed posts instead? Say the word and I'll generate 3,000-char "
        "teasers that link to each article - without touching the article content.",
        "",
    ]
    with open(os.path.join(args.out, "POSTING_CHECKLIST.md"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(cl))

    print(f"wrote {len(rows)} full-length posts + checklist to {args.out}")


if __name__ == "__main__":
    main()
