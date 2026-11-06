# New Jersey supplier collection pipeline

This project collects public residential electricity and natural-gas offers from third-party suppliers serving New Jersey. It preserves the source evidence, normalizes offer and contract fields, and produces CSV and JSON exports for review or database loading.

The collector does **not** enter customer account numbers, credentials, addresses, or payment information. A failed or blocked supplier is recorded as such; the pipeline does not turn missing data into a zero price or claim that no offers exist.

## Professor's manual run guide

The instructions below assume a Windows computer and PowerShell. No API key, paid scraping service, supplier account, or model subscription is required.

### 1. Download the required software

Install the following before the first run:

1. [Python 3.13 for Windows](https://www.python.org/downloads/windows/)
   - Keep the Python Launcher selected during installation.
   - Select **Add Python to PATH** if the installer offers that option.
2. [Google Chrome](https://www.google.com/chrome/)
   - Some suppliers reject a fresh background browser. The pipeline therefore uses an isolated Chrome session for those sites.
   - It never uses the professor's normal Chrome profile.
3. A working internet connection.

[Git for Windows](https://git-scm.com/download/win) is required. The supported handoff is a recursive clone of the master `ERES-PROJECT` repository; a GitHub ZIP does not include the NJ submodule correctly.

### 2. Clone the master repository and open the NJ pipeline

Choose a parent folder, then clone the master repository with all of its submodules. Run the NJ pipeline only from its location under the master repository:

```powershell
git clone --recurse-submodules https://github.com/ERES-PROJECT/ERES-PROJECT.git
cd .\ERES-PROJECT\pipeline\nj-switch-pipeline
```

If the master repository was cloned previously, initialize its submodules before entering the NJ folder:

```powershell
cd .\ERES-PROJECT
git submodule update --init --recursive
cd .\pipeline\nj-switch-pipeline
```

All remaining commands in this README must be run from `ERES-PROJECT\pipeline\nj-switch-pipeline`. Do not copy an existing `.venv` into this folder; virtual environments contain machine-specific absolute paths.

### 3. Perform the one-time setup

Confirm that Python 3.13 is available, create a private Python environment, install the locked dependencies, install the project, and download Playwright's Chromium browser:

```powershell
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m playwright install chromium
```

The virtual environment does not need to be activated. Every command below calls its Python executable directly, which also avoids PowerShell execution-policy problems.

Confirm that the installed command starts correctly, then print the configured supplier/distribution-company combinations:

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli --help
.\.venv\Scripts\python.exe -m nj_switch.cli list
```

The current registry contains **84 configured supplier/utility/ZIP queries**. The `list` command is also the authoritative source for the exact supplier names, utility names, commodities, and test ZIP codes accepted by the filters.

### 4. Run the complete NJ collection

For a normal complete run:

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli collect --all
```

Important behavior during a run:

- Keep the computer awake and connected to the internet until the command finishes.
- Chrome windows may open automatically for suppliers that reject background sessions. This is expected; do not close or interact with them.
- The collector checkpoints each completed query, so its individual `result.json` remains available even if a later supplier fails.
- A new directory is created automatically under `data\runs`. Existing runs are not overwritten.
- The last line printed by the command gives the full output-directory path.

The command can take a while because it visits multiple supplier sites and downloads public contract documents.

### 5. Verify and inspect the result

The following PowerShell commands select the most recently modified run, validate its schemas, references, and evidence hashes, summarize its statuses, and open its folder:

```powershell
$run = Get-ChildItem .\data\runs -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
.\.venv\Scripts\python.exe -m nj_switch.cli verify "$($run.FullName)"
Import-Csv (Join-Path $run.FullName "coverage.csv") | Group-Object status | Select-Object Name, Count
Get-Content (Join-Path $run.FullName "report.md")
Invoke-Item $run.FullName
```

A fully successful run has one `success` row for every attempted query. Verification proves that the exported files are internally consistent; it does not independently certify that a supplier's posted price is correct or still current.

### Exit codes

After a command, PowerShell stores its exit code in `$LASTEXITCODE`:

```powershell
$LASTEXITCODE
```

| Exit code | Meaning |
| ---: | --- |
| `0` | Every selected query succeeded, or the requested verification passed. |
| `2` | Collection finished, but at least one query was partial, failed, blocked, unsupported, empty, or requires review. This does not necessarily mean the program crashed. |
| Other nonzero value | Read the terminal error and the run's `report.md` and `coverage.csv` files. |

Always inspect `coverage.csv`; the presence of CSV output alone does not mean every supplier succeeded.

## Running a smaller test or retry

Use `list` first so the filter text exactly matches the registry:

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli list
```

Collect one exact supplier/utility combination:

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli collect --supplier "Think Energy" --utility "PSE&G Electric"
```

Collect every configured territory for one supplier:

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli collect --supplier "Direct Energy" --all
```

Collect every configured supplier for one distribution company:

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli collect --utility "PSE&G Gas" --all
```

Filter to configured ZIP-code queries:

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli collect --supplier "Think Energy" --zip "07446" --zip "07480" --all
```

ZIP arguments are filters for ZIP codes already in the registry; they do not create arbitrary new market tests. Without `--all`, collection defaults to the first query matching the filters. Add `--all` when all matching rows should be run.

To watch a standard Playwright interaction for troubleshooting, use:

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli collect --supplier "Think Energy" --utility "PSE&G Electric" --headed --browser-channel chrome
```

The `discover` command is a developer diagnostic that skips document collection and normally exits with code 2. It is not the recommended command for a production data run.

## Combining a full run with focused retries

If a complete run has a few failures, rerun only those combinations. Then consolidate the successful retries into the original run without discarding the original evidence:

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli consolidate data\runs\FULL-RUN --retry data\runs\FOCUSED-RETRY --output data\runs\CONSOLIDATED-RUN
```

Replace the three example directory names with real run directories. The output directory must not already exist. If multiple retry directories contain the same supplier/utility query, the later `--retry` argument takes precedence.

## Output files

Every live collection creates `data\runs\<UTC timestamp>-<random suffix>\`. The main files are:

| File | Purpose |
| --- | --- |
| `coverage.csv` | One outcome for each attempted supplier, utility, and ZIP query. Check this first. |
| `report.md` | Human-readable collection report with offer and contract counts. |
| `offer_prices.csv` | Canonical purchasing rows after materially equivalent ZIP observations are consolidated. |
| `offer_observations.csv` | ZIP-level sightings mapped to their canonical offers. |
| `contract_information.csv` | Normalized public contract-document records. |
| `offer_documents.csv` | Explicit links between canonical offers and contract documents. |
| `results.json` | Complete interchange record for the run. |
| `offers.csv`, `contracts.csv` | More technical normalized exports. |
| `compiled_offerings.csv` | Compatibility copy of `offer_prices.csv`. |
| Per-query directories | Checkpoint JSON and hashed source artifacts used as evidence. |

Canonical prices are dollars per explicitly stated unit, not cents. Gas units are preserved as published; the pipeline does not guess a CCF-to-therm conversion.

ZIP code does not define offer uniqueness. Equivalent ZIP observations are consolidated with `offer_fingerprint`, while observation keys, supplier product IDs, individual source URLs, and capture history remain in `offer_observations.csv` and the technical JSON. See [Offer identity and ZIP sampling](docs/OFFER_IDENTITY_AND_ZIP_SAMPLING.md).

## Current verified baseline

The latest complete verified production run is `data/runs/20261019-complete-production-final`:

- All **84 of 84** configured queries finished with `success`.
- `offer_prices.csv` contains 295 canonical offer rows.
- `offer_observations.csv` contains 300 ZIP-level observations.
- `contract_information.csv` contains 465 contract rows.
- `offer_documents.csv` contains 407 offer/document links.
- All 84 source/export plan counts reconciled, with no ambiguous contract associations.

This baseline is historical evidence, not a promise that supplier websites or current rates have remained unchanged. A new run should always be verified and reviewed.

## Troubleshooting

### `py -3.13` is not recognized

Install Python 3.13 from the official Windows download page, including the Python Launcher. Close and reopen PowerShell, then rerun `py -3.13 --version`.

### `No module named nj_switch`

Confirm PowerShell is in the `nj-switch-pipeline` directory, then repeat:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

### Playwright says that a browser executable is missing

Repeat:

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

Also confirm that ordinary Google Chrome is installed for supplier adapters that require it.

If Chrome is installed in a nonstandard location, set its executable path for the current PowerShell session before collecting:

```powershell
$env:NJ_SWITCH_CHROME = "C:\path\to\chrome.exe"
```

### A supplier reports `blocked`, `partial`, `empty`, or `failed`

Do not interpret that status as a zero-price offer or proof that the supplier has no plans. Read the matching row in `coverage.csv`, the details in `report.md`, and the query's `result.json`. Website access rules and page layouts can change. Retry only the affected combination before considering a code change.

### An output directory already exists

Do not delete or overwrite a previous evidence run. Let `collect` generate a new directory automatically, or choose a new path for `consolidate`.

## Additional commands

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli backup
.\.venv\Scripts\python.exe -m nj_switch.cli replay tests\fixtures\manual_demo.json
.\.venv\Scripts\python.exe -m nj_switch.cli replay tests\fixtures\observed
```

`replay` is offline and is useful for regression work; fixtures under `tests/fixtures/observed` are historical public captures, **not current rates**.

Developers can run the full offline test suite with the command below. This is not required for a normal professor-operated collection:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Code and documentation map

- `src/nj_switch/navigation.py`: supplier-specific public shopping interactions and conservative generic discovery.
- `profiles.py`: observed Direct Energy, Think Energy, and NRG response mappings.
- `offers.py`, `normalize.py`: reusable offline parsing and normalization.
- `contracts.py`: PDF text, tables, form fields, DOCX tables, and HTML sections; deterministic matching.
- `pipeline.py`, `transport.py`, `evidence.py`: collection, bounded downloads, evidence, and failure isolation.
- `models.py`, `reporting.py`, `cli.py`: validated records, exports, reports, and commands.
- [Manual verification guide](docs/MANUAL_VERIFICATION.md): human review procedure.
- [Scraper modernization report](docs/SCRAPER_MODERNIZATION_REPORT.md): architecture and modernization findings.
- [NJ Power Switch implementation plan](docs/NJ_POWER_SWITCH_IMPLEMENTATION_PLAN.md): longer-term roadmap.

The old `src/scraper/nj_scraper.py` and `demo_test.py` commands delegate to the shared collector. Other old `inspect_*.py` scripts are exploratory diagnostics, not part of the supported workflow; some require historical dependencies that are intentionally absent from the core lockfile.

Run broad collection manually and supervise the visible browser sessions. Before any future scheduled or unattended use, review source access conditions and current site behavior.
