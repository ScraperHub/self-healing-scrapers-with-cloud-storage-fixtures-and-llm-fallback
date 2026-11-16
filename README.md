# Self-healing scrapers

A Python 3.11+ pipeline that extracts a product through four tiers, watches fill rate for selector drift, proposes a CSS repair, and replays mirrored pages with no network.

The suite ran on Python 3.13.14. Ruff, mypy, and the package metadata target 3.11.

## Layout

- `steps/` holds eight self-contained examples. Each one runs with `python main.py`. Steps 2, 4, 7, and 8 also accept `--live`.
- `final/` is the package `selfheal`. Fixtures, tests, and the verified storage notes live there.
- Tokens stay in `.env`. Copy `.env.example`. The files that ship do not contain keys.

Create the virtualenv from `code/` and install the package:

```
python -m venv .venv
.venv\Scripts\python -m pip install -e final[dev]
```

## Steps

```
.venv\Scripts\python steps\run_all.py
.venv\Scripts\python steps\run_all.py --live
.venv\Scripts\python -m pytest steps\step08_replay_tests
```

`run_all.py` and `run_all.py --live` both exited 0. The step 8 pytest run was 1 passed. `--live` stored `example.com`, called the model for one Markdown extract (181 input tokens, 39 output tokens) and one selector proposal, and read the stored page back by rid.

## Package

From `final/`:

```
python tasks.py test
python tasks.py coverage
python tasks.py lint
python tasks.py typecheck
python tasks.py test-live
python -m selfheal.pipeline --fixtures
```

Offline pytest (`-m "not live"`) was 66 passed. Coverage on `selfheal` was 86.93% (fail under is 85). `ruff check` and `ruff format --check` were clean. `mypy --strict` reported no issues in 21 source files. Live pytest (`-m live`) was 4 passed. `python -m selfheal.pipeline --fixtures` replayed 15 pages, five each for Amazon, Walmart, and Allbirds, and exited 0.

## What was checked live

`final/docs/verified-behavior.md` is the record from 16 November 2026.

- `store=true` together with `scraper=amazon-product-details` stores the scraper JSON. HTML fixtures come from a second `store=true` crawl with no scraper.
- The rid is the `rid` query parameter on `storage_url`.
- A second crawl left the first rid readable. Lookup by URL returned the newer copy.
- Current storage docs say 30 days. Older material says 14.
- `StorageAPI.get`, `rids`, `totalCount`, and `bulk` worked on `crawlbase` 1.0.0. Bulk bodies are base64 of gzip.
