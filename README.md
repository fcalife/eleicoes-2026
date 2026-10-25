# Eleições 2026 — Lula × Flávio, seção a seção

Static site (GitHub Pages, `/docs` on `main`) comparing the 1st and 2nd round of the 2026 presidential election section by section, and projecting the 2nd-round result from the ballot-box reports (boletins de urna) TSE has published so far.

- `pipeline/` — Python, stdlib only. `fetch_t2.py` downloads TSE's consolidated result per municipality (municipalities 100% totalized enter whole; cached in `data/mun2`) plus a sample of published 2nd-round BUs from the partial ones, up to 30 per municipality (`AMOSTRA`; cached in `data/bu2`), `bu.py` decodes them, `analyze.py` matches sections across rounds and extrapolates.
- `docs/` — the site. `docs/data/*.json` is what `analyze.py` writes to `data/dash/`.
- `./publish.sh` — reruns the pipeline and refreshes `docs/data`. The first run also downloads TSE's 1st-round per-section CSV.

Method and caveats are on the page itself.
