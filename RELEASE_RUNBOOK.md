# MAYA release runbook

Everything in this repo is staged and verified. This runbook is the short, human-executed
checklist to (1) push `maya-oss/` to a public GitHub repo and (2) publish the 10-part
"Migrating with MAYA" series to LinkedIn. Nothing here runs automatically - you execute it
with your own credentials.

> Repo slug suggestion: **`maya-migrate`** (the brand text stays "MAYA"; "maya" alone is
> heavily overloaded on GitHub). Adjust the URLs below to your final name.

---

## 0. Pre-flight (already green, re-run if you like)

```bash
cd maya-oss
make demo        # graph -> order -> verify -> context -> sample -> validate -> report -> bi
make test        # 24 pytest goldens (or: python3 -m pytest)

# scrub gate - must print nothing:
grep -RInE "vizient|hrzn|\bhorizon\b" \
  --exclude-dir=.git --exclude-dir=out --exclude-dir=workflows .
```

All three must be clean before you push. CI (`.github/workflows/ci.yml`) re-runs the same
three gates on push/PR across Python 3.9/3.11/3.12.

---

## 1. Publish the code to GitHub

`maya-oss/` becomes the repo root. Do **not** push the parent `vizient/` workspace.

```bash
cd maya-oss

git init
git add .
git status                      # sanity-check: no out/, no *.pdf, no publish_pack/ (all gitignored)
git commit -m "MAYA v0.1.0 - open-source deterministic migration accelerator + Northwind demo"

# Option A - GitHub CLI (creates the repo and pushes in one step)
gh repo create maya-migrate --public --source=. --remote=origin --push

# Option B - manual: create an empty public repo named maya-migrate in the GitHub UI, then:
# git remote add origin https://github.com/<you>/maya-migrate.git
# git branch -M main
# git push -u origin main
```

Tag the release once `main` is up and CI is green:

```bash
git tag -a v0.1.0 -m "MAYA v0.1.0"
git push origin v0.1.0
```

Then, in the GitHub UI:
- Add repo topics: `databricks`, `data-migration`, `synapse`, `lineage`, `data-engineering`.
- Set the description to the one-liner from `pyproject.toml`.
- (Optional) Create a **Release** from tag `v0.1.0` and paste the highlights from `README.md`.
- Confirm the **Actions** tab shows the `ci` workflow passing.

---

## 2. Publish the blog series to LinkedIn

These are long-form essays (>3000 chars), so publish each as a **LinkedIn Article**
(Profile -> "Write article"), *not* a feed post. The feed-post API path is only for short
teasers.

### 2a. Build the copy-paste pack

```bash
cd maya-oss/blog
python3 export_pack.py          # writes publish_pack/*.txt + POSTING_CHECKLIST.md
```

Each `publish_pack/NN_*.txt` already contains the byline, the "Part N of 10" header, the full
untruncated body, the next-part pointer, and hashtags. Paste as-is into the Article editor.
The matching cover image is `blog/figures/NN_*.png`.

### 2b. Order and cadence (10 parts)

Publish in order 1 -> 10; each ends with a pointer to the next part.

| # | Article | Cover figure |
|---|---|---|
| 1 | `01_meet_maya_northwind.md` | `figures/01_meet_maya_northwind.png` |
| 2 | `02_adapter_model.md` | `figures/02_adapter_model.png` |
| 3 | `03_dependency_graph.md` | `figures/03_dependency_graph.png` |
| 4 | `04_build_order_waves.md` | `figures/04_build_order_waves.png` |
| 5 | `05_pipeline_contract.md` | `figures/05_pipeline_contract.png` |
| 6 | `06_reusable_engines.md` | `figures/06_reusable_engines.png` |
| 7 | `07_maya_dev_illusion.md` | `figures/07_maya_dev_illusion.png` |
| 8 | `08_maya_sit_drift_loop.md` | `figures/08_maya_sit_drift_loop.png` |
| 9 | `09_maya_soak_sustained.md` | `figures/09_maya_soak_sustained.png` |
| 10 | `10_dashboard_bi_cutover.md` | `figures/10_dashboard_bi_cutover.png` |

Recommended cadence: **one part per weekday** (2 weeks) or **2 per week** for a longer run.
LinkedIn enforces a rolling ~24h limit on new Articles, so if you hit it, **schedule** the
next part for the following day rather than forcing it.

### 2c. Per-article steps (repeat for each part)

1. Profile -> **Write article**.
2. Title = the `title:` from the post's front matter (or the first `# H1`).
3. Cover = upload `figures/NN_*.png`.
4. Body = paste the full text from `publish_pack/NN_*.txt`.
5. In Part 1, add a line linking to the GitHub repo (`https://github.com/<you>/maya-migrate`).
6. Publish (or schedule).
7. Optional: post a short **teaser feed post** the same day linking to the Article to drive reach.

### 2d. (Optional) API path for short teasers only

`publish_to_linkedin.py` posts *feed shares* via the official API (3000-char cap - teasers,
not the full articles). Always dry-run first:

```bash
export LINKEDIN_ACCESS_TOKEN="..."              # w_member_social scope
export LINKEDIN_AUTHOR_URN="urn:li:person:..."  # GET /v2/userinfo -> sub
python3 publish_to_linkedin.py --all --dry-run  # preview
```

---

## 3. Post-launch

- Pin Part 1 (or a series-intro post) to your profile's Featured section.
- Add the repo link + series link to your profile.
- Watch the GitHub **Issues** tab; the bug/feature templates are already in place.
- `publish_pack/` and generated PDFs are gitignored - regenerate any time with
  `python3 export_pack.py` / `make report`.

---

*Created by Srinivas Nelakuditi. This runbook is documentation only - all `git push` and
LinkedIn actions are performed by you.*
