# NJ supplier collection pipeline

Collect public New Jersey supplier offers with a shared, evidence-first process. This is a usable first pass, not complete statewide coverage. Missing contracts, uncertain fields and failed navigation remain visible; they are not converted to zero prices or empty-market claims.

Start with the [manual verification guide](docs/MANUAL_VERIFICATION.md) and [modernization report](docs/SCRAPER_MODERNIZATION_REPORT.md). The longer [implementation plan](docs/NJ_POWER_SWITCH_IMPLEMENTATION_PLAN.md) and [TODO](TODO/NJ_POWER_SWITCH_TODO.md) remain the roadmap.

## Setup

Run PowerShell from this project directory. CPython **3.13** is the tested version; package metadata permits 3.12+, but other versions have not been verified here.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest -q
```

All core libraries are free/open-source. Running locally needs no paid scraping service or model API. Network access and Chromium are required only for live collection; no live tests run under the default pytest command.

## Commands

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli list
.\.venv\Scripts\python.exe -m nj_switch.cli backup
.\.venv\Scripts\python.exe -m nj_switch.cli replay tests/fixtures/manual_demo.json
.\.venv\Scripts\python.exe -m nj_switch.cli replay tests/fixtures/observed
.\.venv\Scripts\python.exe -m nj_switch.cli discover --supplier 'Think Energy' --utility 'PSE&G Electric'
.\.venv\Scripts\python.exe -m nj_switch.cli collect --supplier 'Direct Energy' --utility 'PSE&G Electric' --headed
.\.venv\Scripts\python.exe -m nj_switch.cli collect --supplier 'Think Energy' --zip 07446 --zip 07480 --all
.\.venv\Scripts\python.exe -m nj_switch.cli collect --all
.\.venv\Scripts\python.exe -m nj_switch.cli consolidate data/runs/FULL --retry data/runs/FOCUSED-RETRY --output data/runs/CONSOLIDATED
```

Use the printed output directory with `python -m nj_switch.cli verify DIRECTORY`. Exit code **2 means partial, failed, unsupported, or review-required collection**, not necessarily a crashed command. Discovery skips documents and normally returns 2. `verify` checks schemas, references and artifact hashes; it does not certify a quote is correct or current.

Use `consolidate` after focused retries to replace the matching supplier/utility rows in a base run, copy their hashed evidence, rebuild every table, and verify the resulting aggregate. Later retry arguments take precedence for the same query.

Every run writes a new `data/runs/<UTC timestamp>-<random suffix>/` directory. The main reader-facing tables are `offer_prices.csv` (one canonical purchasing row per materially equivalent offer), `offer_observations.csv` (one ZIP-level sighting mapped to its canonical offer), `contract_information.csv` (one canonical row per document), `offer_documents.csv` (the explicit canonical offer/document links), and `coverage.csv` (one disposition per attempted supplier/territory/ZIP). `compiled_offerings.csv` remains as a compatibility copy of `offer_prices.csv`. The directory also retains `results.json`, the more technical `offers.csv` and `contracts.csv`, `report.md`, and per-query hashed artifacts. JSON is the complete interchange record; CSVs are convenience views. Canonical prices are **dollars per explicitly stated unit**, not cents. Gas units are preserved; no CCF/therm heat-content conversion is guessed.

ZIP does not define offer uniqueness. `offer_prices.csv` consolidates equivalent ZIP observations using `offer_fingerprint` and lists all `observed_zip_codes`. Observation-level keys, supplier product IDs, duplicate diagnostics, individual source URLs, and capture history remain in `offer_observations.csv` and the technical JSON rather than being repeated in the canonical purchasing table. See [offer identity and ZIP sampling](docs/OFFER_IDENTITY_AND_ZIP_SAMPLING.md).

Current coverage snapshot (September 18, 2026): all 21 master-list suppliers have a dedicated adapter and no registry row uses generic discovery or a manual skip. The latest verified aggregate is `data/runs/20260918-user-confirmed-supplier-coverage-final`, with 261 ZIP-level offer observations from 18 suppliers. Reader-facing offer exports consolidate repeated products across ZIPs, group electric first and gas second, then alphabetize by supplier. CleanChoice's public plan route blocks fresh headless sessions, so the CLI automatically routes that adapter through a dedicated visible Chrome process while the rest of a broad run remains headless. A dedicated adapter can also return `blocked`, `empty`, or `unsupported`; that is an explicit source disposition, not a claim that rates were collected.

Direct Energy update (October 16, 2026): Direct is routed through an ordinary Chrome process using a dedicated scraper-owned profile and Chrome's loopback debugging interface. The profile is initialized only from Direct's public homepage and is never the user's normal Chrome profile. `data/runs/20261016-direct-cdp-all` verified all eight configured NJ markets with 32 current offers and 84 connected documents; rendered, API, and exported plan counts match in every territory.

## Code map

- `src/nj_switch/navigation.py`: supplier-specific public shopping interactions and conservative generic discovery.
- `profiles.py`: observed Direct Energy, Think Energy and NRG response mappings.
- `offers.py`, `normalize.py`: reusable offline parsing and normalization.
- `contracts.py`: PDF text/tables/form fields, DOCX tables and HTML sections; deterministic matching.
- `pipeline.py`, `transport.py`, `evidence.py`: collection, bounded downloads, evidence and failure isolation.
- `models.py`, `reporting.py`, `cli.py`: validated records, exports and commands.
- `tests/fixtures/observed`: historical public captures for regression tests, **not current rates**.

The old `src/scraper/nj_scraper.py` and `demo_test.py` commands now delegate to the shared collector. Original source and CSVs remain in git and the verified baseline snapshot. Other old `inspect_*.py` scripts are exploratory diagnostics and are not part of the supported test suite. Some still require their historical dependencies (for example pandas); they are intentionally not installed by the new core lockfile.

Do not schedule broad collection yet. Review source access conditions and the remaining coverage/document gaps first. Never supply account numbers, addresses, credentials or payment information to these collectors.
