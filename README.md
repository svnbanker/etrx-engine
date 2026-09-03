# ETRX engine

The calculation code behind the ETRX US Effective Tariff Rate Index (https://etrxindex.com), published so that anyone can reproduce every number the index prints.

**What it computes.** Calculated duty assessed at entry divided by customs value, from the US Census Bureau International Trade API, monthly, by origin country and HS chapter, since 2010. The headline excludes HS chapters 98 and 99. Aggregation is value-weighted: dollars are summed, then divided. AD/CVD duties are excluded. The first print of a month settles and is never restated; later differences are appended to the vintage ledger (`prints.jsonl`) with their own dates. The full rules are in `RULEBOOK.md`.

**Why the code is public.** A benchmark that asks to be referenced should be checkable line by line. Publishing the engine removes key-person risk and turns "trust us" into "run it".

## Reproduce a print

    uv sync --frozen
    export CENSUS_API_KEY=...        # free key: api.census.gov/data/key_signup.html
    uv run python index_build.py --selftest
    uv run python index_build.py --dry-run

`--dry-run` fetches, gates, computes and validates but writes nothing. Without the flag the engine appends to `prints.jsonl` and renders the site into `docs/`.

## Files

| file | role |
|---|---|
| `index_build.py` | fetch, completeness gate, compute, validate, publish, ledger append (in that order, always) |
| `backfill.py` | one-shot history since 2010 with the cross-validation battery |
| `site_build.py` | the static site, hand-rolled SVG charts, per-series JSON |
| `feed.py`, `cut.py`, `client_index.py`, `heatmap.py` | the full origin x chapter panel, custom cuts, client-weighted indices, the heatmap |
| `figures.py` | regenerates the verified key figures from the files |
| `prints.jsonl`, `data/` | the append-only vintage ledger and the published series |
| `policy_events.md` | the verified timeline of tariff actions that commentary may cite |
| `AUDIT.md` | the append-only log of everything that happened to the index |

## Not in this repository

Publishing automation, outreach drafts, and the operations runbook live in a private repository. They contain no calculation. The site itself is served from `svnbanker/etrx-site`.

## License

Code: MIT. Published series and charts: CC BY 4.0 with attribution to ETRX. The full panel, vintage feed, API access and any use as a settlement reference require a license from the administrator (press@etrxindex.com).
