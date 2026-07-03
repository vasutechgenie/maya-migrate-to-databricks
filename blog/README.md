# Migrating with MAYA - a 10-part hands-on series

Long-form articles that walk the entire MAYA workflow on the runnable **Northwind** demo.
Each post pairs with a durable tutorial page under [`../docs/tutorial/`](../docs/tutorial/README.md)
and a publication-grade figure in [`figures/`](figures/).

| # | Post | Figure |
|---|---|---|
| 1 | [MAYA is open source - meet Northwind](01_meet_maya_northwind.md) | `figures/01_meet_maya_northwind.png` |
| 2 | [The adapter model](02_adapter_model.md) | `figures/02_adapter_model.png` |
| 3 | [Building the dependency graph](03_dependency_graph.md) | `figures/03_dependency_graph.png` |
| 4 | [Build order, waves, and the independent verifier](04_build_order_waves.md) | `figures/04_build_order_waves.png` |
| 5 | [The deterministic pipeline contract](05_pipeline_contract.md) | `figures/05_pipeline_contract.png` |
| 6 | [Reusable engines E1-E7](06_reusable_engines.md) | `figures/06_reusable_engines.png` |
| 7 | [MAYA-Dev: the illusion of production](07_maya_dev_illusion.md) | `figures/07_maya_dev_illusion.png` |
| 8 | [MAYA-SIT: 10-check parity and the drift loop](08_maya_sit_drift_loop.md) | `figures/08_maya_sit_drift_loop.png` |
| 9 | [MAYA-Soak: sustained parity, zero drift](09_maya_soak_sustained.md) | `figures/09_maya_soak_sustained.png` |
| 10 | [Dashboard, BI/Genie, cutover](10_dashboard_bi_cutover.md) | `figures/10_dashboard_bi_cutover.png` |

## Regenerating the assets
```bash
make figures                        # render every figure (needs Pillow)
python3 figures/add_author.py       # add the byline (idempotent)
python3 figures/embed_figures.py    # embed each post's figure (idempotent)
python3 figures/series_format.py    # add series header/footer (idempotent)
python3 export_pack.py              # write publish_pack/ (copy-paste text + checklist)
```

## Publishing
`export_pack.py` writes `publish_pack/` with the full, untruncated body text for each part plus
`POSTING_CHECKLIST.md`. These are long-form essays, so publish each as a **LinkedIn Article**
(not a feed post). `publish_to_linkedin.py` can post via the official API (dry-run first);
`publish_pack/` is gitignored since it is regenerated. See the repo's `RELEASE_RUNBOOK.md`.

Created by **Srinivas Nelakuditi**.
