# selfheal

Tiered extraction, fill-rate drift detection, selector repair, and replay tests over Crawlbase Storage.

Config targets Python 3.11. The commands below were run with Python 3.13.14 from `code/.venv`.

## Run

```
python tasks.py test
python tasks.py coverage
python tasks.py lint
python tasks.py typecheck
python tasks.py test-live
python tasks.py refresh-fixtures
python -m selfheal.pipeline --fixtures
```

`test` is `pytest -m "not live"`. `test-live` calls Crawlbase and OpenAI and needs `.env` (`CRAWLBASE_TOKEN`, `CRAWLBASE_JS_TOKEN`, `OPENAI_API_KEY`, optional `OPENAI_MODEL`).

## Results from this build

- Offline tests: 66 passed. Coverage of `selfheal`: 86.93%.
- Live tests: 4 passed.
- `ruff check` and `ruff format --check`: clean.
- `mypy --strict`: no issues in 21 source files.
- Fixture replay: 15 pages, exit 0. Amazon and Walmart win on the named scraper JSON. Allbirds wins on CSS at fill rate 0.75.

## Layout

- `selfheal/extractors/` is the chain: named scraper, CSS, `generic-extractor`, LLM on Markdown.
- `selfheal/drift.py` keeps SQLite samples and raises an incident when the watched tier drops more than 30 points while the LLM tier stays within 10.
- `selfheal/repair.py` validates a selector proposal on stored snapshots and writes a diff under `repair_out/`. It does not edit the selector files.
- `fixtures/manifest.json` is the mirror. `scripts/refresh_fixtures.py` replaces it. A page that misses the site fill rate is not kept.
- `docs/verified-behavior.md` records the storage checks: scraper crawls store JSON, the rid is on `storage_url`, URL lookup returns the newest copy, and retention in the current docs is 30 days (older material says 14).

Sites and URLs are in `selfheal/sites.py`. The JS token is used only when a response is a 503 or a checkpoint page.
