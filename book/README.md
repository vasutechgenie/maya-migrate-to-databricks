<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../docs/assets/maya-logo-dark.png">
    <img alt="MAYA - Migration Accelerator" src="../docs/assets/maya-logo.png" width="520">
  </picture>
</p>

<h1 align="center">MAYA - Supersonic Migrate to Databricks Accelerator</h1>
<p align="center"><b>#1 Benchmark Winner in Multiple Categories</b> &bull; a co-branded field guide</p>

A professional, self-contained PDF guide to using **MAYA** for migrations to
Databricks - built to be published on LinkedIn as a native **document post**
(in-feed flipbook) and offered as a download. It is co-branded with **MAYA** and
the **Nelakuditi Migration Benchmark (NMB)**, and includes the measured proof
that MAYA leads the field.

The deliverable is **[`MAYA_Migration_Guide.pdf`](MAYA_Migration_Guide.pdf)**
(22 landscape pages, 4:3, fully self-contained - every image is base64-embedded).

## What's inside
Cover &bull; contents &bull; foreword &bull; the MAYA model (adapter + source-agnostic core) &bull;
preview before you build &bull; reusable engines &bull; the three-phase validation technique &bull;
the drift loop &bull; the twelve-stage lifecycle &bull; BI/Genie &bull; identity, security &
governance &bull; the web command center &bull; the **NMB benchmark proof** &bull; a 60-second
quickstart &bull; **About the Author** &bull; how to engage.

## Structure
```
book/
  content.py        authored pages (edit prose here - one dict per page)
  build_book.py     renders content.py -> book.html -> MAYA_Migration_Guide.pdf
  author.json       scraped LinkedIn bio/headline/interests (About the Author page)
  figures/
    figlib.py            drawing primitives (shared with NMB)
    make_figures.py      builds the NMB proof charts from assets/leaderboard.json
    make_translogos.py   transparent logo variants for dark pages
  assets/           logos, headshot, cover art, leaderboard.json, generated charts
  MAYA_Migration_Guide.pdf   the deliverable
```

## Rebuild
Requires Python with **Pillow** (figures) and **Playwright + Google Chrome**
(PDF render).

```bash
# 1) (optional) refresh author bio + headshot from your LinkedIn session
python ../../li-updater/scrape_profile.py

# 2) regenerate the benchmark proof charts + transparent logos
python figures/make_figures.py
python figures/make_translogos.py

# 3) build the PDF (uses system Chrome via Playwright)
python build_book.py            # -> MAYA_Migration_Guide.pdf
python build_book.py --html     # book.html only (fast layout preview)
```

The benchmark numbers are read live from `assets/leaderboard.json` (a copy of
the committed NMB leaderboard), so the proof spread never drifts from the repo.

## Publish to LinkedIn
Post the PDF as a native **document** (not a link) so it renders as an in-feed
flipbook with a download button:

```bash
python ../../li-updater/post_document.py --probe      # inspect the composer
python ../../li-updater/post_document.py --dry-run    # attach + caption, do not post
python ../../li-updater/post_document.py              # publish
```

## Disclaimer
The MAYA web application shown in this guide is **delivered by experts - it is
not an open-source, self-service product**. To evaluate or engage it, contact
the **Databricks Professional Services / FDE** team or
**srinivas.nelakuditi@databricks.com**.

Created by **Srinivas Nelakuditi**. Apache-2.0.
