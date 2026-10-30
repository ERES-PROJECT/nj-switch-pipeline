# NJ TPS live-source audit — 2026-10-01

## Audit result

- A fresh run covered all 83 configured supplier/utility/ZIP combinations. The final evidence set contains 213 ZIP-level offer observations and 207 consolidated current offers; artifact hashes and result schemas verify successfully.
- Reader-facing offer files now admit only fresh, non-replayed results that explicitly passed ZIP, commodity, and utility qualification. Historical fixtures, dated PDFs, utility-only pages, comparison tables, and generic JSON candidates cannot be promoted.

`partial` below still means the offers are live and ZIP-qualified. It usually means a contract document was missing, incomplete, or produced a non-fatal warning.

## Per-TPS findings

### Alpha Gas & Electric

- No current offer is exported. The only public NJ rate source found is dated January 15, 2025.
- The PDF is retained as evidence, but Alpha is `unsupported` until it publishes a current accessible price source.

### Ambit Energy

- All 4 configured electric combinations are live and ZIP/utility-qualified: PSE&G, JCP&L, ACE, and Rockland.
- Each combination returned 4 offers (16 observations total); results are `partial` because document discovery is incomplete, not because rates are historical.

### American Power & Gas

- Neither configured gas check produced an eligible current offer for PSE&G or ETG.
- Its public NJ comparison table did not list the requested utilities, so both checks are `unsupported` and export zero offers.

### CleanChoice Energy

- PSE&G, JCP&L, and ACE electric all returned an access-block page to the automated collector.
- No old fixture or cached rate is substituted; all 3 combinations are `blocked` with zero exported offers.

### CleanSky Energy

- All 5 configured combinations completed the public ZIP, commodity, and utility flow successfully.
- The run returned 25 live observations across Rockland electric and PSE&G, SJG, and ETG gas; all are `partial` only because of document-level gaps.

### Clearview Energy

- All 4 configured combinations are live and ZIP/utility-qualified: JCP&L and ACE electric, plus NJNG and SJG gas.
- The run returned 24 live observations; current offers are usable, while some contract parsing still needs review.

### Constellation Energy

- The 3 electric pages exposed 2 current-looking candidates each, but they were utility-level pages and did not independently validate the configured ZIP.
- Those candidates are review-only and export zero offers; PSE&G gas explicitly returned no plans, and NJNG, SJ, and ETG gas were unsupported.

### Direct Energy

- The automated collector is blocked by Incapsula for all 8 configured combinations, so it exports zero Direct offers and never falls back to saved rates.
- A separate ordinary-Chrome check of ZIP 07102 immediately displayed 5 current electricity plans, confirming the supplier is live and the remaining issue is the automation fingerprint/path, not plan availability.

### Eligo Energy

- The NJNG gas page currently exposes 3 offer-like candidates on an official utility route.
- Because the route does not independently validate ZIP 07712, all 3 remain review-only and zero offers are exported.

### Frontier Utilities

- The changed two-form/new-tab ZIP navigation was repaired and all 5 NJ combinations were retested against the form's current public GET target.
- The enrollment service returned an access block for every NJ check; all are `blocked`, with no fixture or prior rate substituted.

### Great American Gas & Electric

- The public enrollment flow was tested for PSE&G electric at ZIPs 07102, 07302, and 08901.
- All 3 ZIPs explicitly reported no available products, so they are correctly `empty` rather than scraper failures.

### Green Mountain Energy

- Rockland ZIP 07430 explicitly reported that it is not served; no offer was exported.
- ZIPs 07446 and 07480 repeatedly returned an empty Gatsby application shell even after a bounded reload, so both remain failed rather than being filled from prior data.

### IDT Energy

- All 4 configured combinations completed the current public ZIP/commodity/utility workflow.
- The run returned 19 live observations across JCP&L and Rockland electric plus PSE&G and NJNG gas; document warnings keep the status `partial`.

### Major Energy

- All 6 configured combinations are now live and ZIP/utility-qualified after fixing a completed-click/navigation wait on ETG.
- The run returned 13 live observations across PSE&G and ACE electric plus PSE&G, NJNG, SJG, and ETG gas.

### NextEra Energy Services

- The ACE electric ZIP and utility flow completed successfully.
- It returned 2 live offers; the result is `partial` because supporting documents were not collected, not because the rates are stale.

### NJG&E

- Both configured gas checks completed the current public ZIP and preselected-utility confirmation flow.
- NJNG and SJG returned 2 offers each (4 live observations total), with document-level gaps keeping the results `partial`.

### NRG

- All 5 configured combinations are live and ZIP/utility-qualified: PSE&G, ACE, and Rockland electric plus PSE&G and SJG gas.
- The run returned 77 live observations; these are current API-backed products, with `partial` reflecting contract/document warnings.

### Residents Energy

- PSE&G, NJNG, and SJG gas each exposed 2 current-looking comparison-table candidates.
- The page does not validate the entered ZIP, so all 6 candidates remain review-only and zero offers are exported.

### Smart Energy

- JCP&L, ACE, and Rockland electric completed the current public ZIP/utility flow and returned 4 live observations total.
- The current NJ site publishes electricity only, so the configured SJG and ETG gas checks are `unsupported`.

### Think Energy

- PSE&G and JCP&L electric each returned 1 current offer through the public ZIP API.
- Rockland ZIPs 07430, 07446, and 07480 were verified by that API but explicitly returned no in-scope supply offers, so they are `empty`.

### Xoom Energy

- All 6 configured combinations completed the live ZIP and utility workflow successfully.
- The run returned 27 observations across PSE&G, JCP&L, and Rockland electric plus PSE&G, NJNG, and SJG gas; contract gaps keep results `partial`.

## Guardrails added during this audit

- `live_data_verified` is separate from general page/context verification and is required for reader-facing offer exports.
- Offline replay remains available for parser regression tests, but replayed observations are excluded from current offer, observation, contract, and offer-document tables.
- Unverified DOM/API values are retained only as candidates in `results.json`; they cannot become offer rows.
- Direct Incapsula pages and Frontier access blocks are classified as blocks, not as evidence of an empty market.

## Evidence

- Final consolidated run: `data/runs/20261001-live-source-audit-final`
- Main outputs: `coverage.csv`, `offer_prices.csv`, `offer_observations.csv`, `results.json`, and `report.md`
