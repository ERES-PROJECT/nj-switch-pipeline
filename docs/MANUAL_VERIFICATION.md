# Manual verification of the first-pass collector

The goal is to reproduce extraction, inspect the supporting evidence, and distinguish a usable partial result from a complete quote. These checks do not require enrolling with a supplier. Run the commands from the project root after the README setup.

## 1. Verify the protected baseline and offline tests

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli backup
.\.venv\Scripts\python.exe -m pytest -q
```

`backup` creates the snapshot only if absent; otherwise it verifies existing hashes. The baseline is under `data/legacy/pre-v2-baseline/manifest.json`. It includes the original data CSVs, master registry and the two original scraper entry points. It is a local, hash-checked snapshot, not a filesystem permission lock or off-machine backup.

## 2. Run a small synthetic demonstration

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli replay tests/fixtures/manual_demo.json
```

This is explicitly synthetic, not a supplier quote. Expect one fixed 12-month offer, $0.199/kWh, $4.95 monthly fee, $150 cancellation fee, 100% wind and a $50 gift-card incentive, related to a complete synthetic contract summary. Inspect `replayed: true` in the JSON.

The command prints a new output directory. Substitute that exact directory here:

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli verify 'data/runs/PRINTED-DIRECTORY'
```

Expect a successful hash/schema/reference check. Existing output directories are rejected by `--output`, so reruns cannot silently replace prior evidence.

## 3. Replay real historical supplier evidence without the internet

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli replay tests/fixtures/observed
```

This reparses ten captures: all seven suppliers for PSE&G Electric, plus Direct Energy, Major Energy and Xoom for PSE&G Gas. It does not make new quotes or reproduce browser navigation. Counts and prices in tests are assertions about these fixed fixtures only.

Inspect these important cases:

- Direct Energy: two differently identified 24-month offers must remain separate even when their names match. Five electric contract summaries include values extracted from PDF form fields; an ordinary PDF text-only reader misses them.
- NRG: introductory three-month pricing is separate from a month-to-month contract. Reward eligibility and renewable marketing text remain available.
- Think Energy: community solar is excluded from electricity supply offers. Check `billing`, public rate display, rate ID, green percentage and source claims in the saved JSON.
- Xoom: SimpleFlex must be month-to-month, not a six-month contract. The first-three-bill introductory window is represented as billing cycles, not assumed calendar months.
- Major: dollars per THM normalize to dollars per therm. The lower utility price-to-compare in the description must not replace the supplier price.
- Ambit: use its new shopping-page detail panels, not the retired popup flow. Terms, explicit fixed structure, zero cancellation fee and incentive conditions should be preserved.

## 4. Run one live public-shopping check

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli list
.\.venv\Scripts\python.exe -m nj_switch.cli discover --supplier 'Think Energy' --utility 'PSE&G Electric'
.\.venv\Scripts\python.exe -m nj_switch.cli collect --supplier 'Direct Energy' --utility 'PSE&G Electric' --headed
```

`discover` records candidate responses and skips document downloads. `collect` also tries permitted public documents. Use exact registry names from `list`. `--limit` defaults to **one combination**, not one supplier across every utility. Repeat `--supplier` for several suppliers and explicitly increase `--limit` when appropriate.

CleanChoice currently must be run with `--headed`. Its public `/plans?area=ZIP` route returned plans in an ordinary visible Playwright session but an access-block page in the bundled headless browser. This is a recorded source limitation, not a signal to add stealth or access-control bypasses.

Optional seven-supplier demonstration:

```powershell
.\.venv\Scripts\python.exe src/scraper/demo_test.py --headed
```

Optional gas checks:

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli collect --supplier 'Direct Energy' --supplier 'Major Energy' --supplier 'Xoom Energy' --utility 'PSE&G Gas' --limit 3
```

Do not compare live output against fixed historical prices/counts. Check that the ZIP, utility, commodity, public plan identity and displayed units match. A failure, CAPTCHA, restriction or changed layout is an actionable report, not permission to force hidden controls or bypass a restriction. The collector never selects/enrolls in a supply plan or enters personal customer data.

## 5. Inspect the outputs

| File | What to verify |
|---|---|
| `coverage.csv` / `report.md` | Every requested combination has a status, including failures and partial results. |
| `offers.csv` | Plan identity, explicit rate unit, structure, duration, fees, incentives and renewable facts. Blank is not zero. |
| `contracts.csv` | Standardized section text, missing sections, document kind and related offer IDs. |
| `results.json` | Full raw field values, provenance, candidate endpoints, warnings and errors. |
| Per-query `artifacts/` | Captured source bytes, named by SHA-256. Compare a PDF visually with the extracted fields. |

Use the offer's `artifact_id` to locate its supporting artifact; use `contract_ids` and `matched_offer_keys` to follow document relationships. Contract discrepancies are flagged, not silently used to replace the shopping-page quote. `text_extracted` on a terms/environmental document does not mean all its provisions have been normalized.

`success` requires verified query context and a complete matched contract summary for every offer, without recorded offer/document problems. `partial` is useful data with unresolved gaps. `needs_review` means context or interpretation is unverified. `failed` does not mean no offers exist. `unsupported` and `blocked` include reasons. Read the warnings even if some fields look plausible.

## 6. Save a new regression fixture

```powershell
.\.venv\Scripts\python.exe -m nj_switch.cli freeze-fixture 'data/runs/RUN/SUPPLIER__UTILITY__ZIP/result.json' 'tests/fixtures/my-new-capture.json'
.\.venv\Scripts\python.exe -m nj_switch.cli replay tests/fixtures/my-new-capture.json
```

Review captures before committing or sharing. Redaction is heuristic, and public PDFs are stored byte-for-byte. Do not freeze authenticated or customer-personalized pages. Fixture JSON can contain `query`, `html`, `source_url`, `context_verified`, `payloads` (`url`/`body`) and `documents` (`url` with `text` or a relative local `path`). Binary document paths must stay within the fixture directory. Discovery-only captures naturally cannot demonstrate complete contract extraction.

## Known limits and recovery

Some public document hosts return 403 for robots policy, or explicitly disallow document paths. The default collector leaves these blocked and preserves the visible link. Request permission or review/download manually through the site's normal user interface if appropriate; this first pass provides no bypass flag. There is no OCR installation, database, scheduler, historical migration or automatic repair of changed pages.

Each completed live combination is checkpointed to `result.json`. A fully interrupted run may lack aggregate reports; there is no automatic resume yet. Keep the checkpoint and start a new bounded run. Raw browser traces/screenshots are disabled because they can contain session details; failure HTML and relevant JSON are retained. Generated runs and baseline backups are gitignored: back up useful results separately. Retain curated fixtures in version control, keep run evidence through review, and prune only deliberately after it is no longer needed.
