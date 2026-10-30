# All-scraper live run — October 15, 2026

Command scope: every configured supplier/utility/ZIP query (`collect --all`), using current supplier websites, public APIs, and public files. Historical fixtures are not accepted as current offers.

Run output: `data/runs/20261015-all-scrapers-live`

Post-run registry cleanup: the 12 suppliers previously designated for removal are now excluded from production scheduling. Future `collect --all` runs contain 19 active suppliers and 92 queries; historical results below remain unchanged as the audit record that supported removal.

## Running supplier issue list

This section is updated from the retained result records after the run. Each supplier receives its own entry when any query is `partial`, `blocked`, `failed`, `needs_review`, `empty`, or `unsupported`, or when count/document quality reports identify a gap.

- **Direct Energy** — all eight configured electric/gas territories returned `blocked` with 0 offers and 0 contracts through the dedicated visible-Chrome path. Each result identifies the supplier's Incapsula access-block page.
- **Major Energy** — all six configured territories returned current offers (3 per electric territory, 2 for PSE&G/NJNG/SJG Gas, and 1 for ETG Gas) but no downloadable contracts because the source robots policy disallows those document URLs; every query is `partial`.
- **Frontier Utilities** — all five configured territories returned `failed` with 0 offers and 0 contracts because the expected enrollment popup did not open before the bounded timeout.
- **Great American Gas & Electric** — all three PSE&G Electric ZIPs returned explicit `empty` offer results; seven generic documents were retained per query, but there are no current offers to count.
- **NextEra Energy Services** — ACE Electric returned `failed` with 0 offers and 0 contracts; the ZIP was filled but the site's `Continue` control remained disabled. The prior run had reached two offers, so this is a navigation regression.
- **Alpha Gas & Electric** — ACE Electric is `unsupported`: no current offer was accepted. Ten documents were retained, but the supplier's available NJ rate source is not current enough to count as a live offer.
- **CleanSky Energy** — all six configured observations returned complete offer/document sets but remain `partial`; the supplier contract summaries omit the required incentives section.
- **American Power & Gas** — PSE&G Gas returned one current address-qualified offer but no connected contract, so the query is `partial`.
- **Green Mountain Energy** — all three Rockland ZIP probes (`07430`, `07446`, and `07480`) returned `failed` because the expected `planlookupForm` never became visible; these are failures, not evidence of an empty market.
- **Think Energy** — all three Rockland ZIPs returned verified `empty` results from the public API. This is a current no-qualifying-offer disposition, not a scraper failure; PSE&G and JCP&L succeeded.
- **Constellation Energy** — all four gas territories returned 2 offers and 3 contracts apiece but are `partial` because the current gas contract summaries omit incentives. Its three electric territories succeeded.
- **Residents Energy** — PSE&G, NJNG, and SJG Gas returned `needs_review` with 0 accepted ZIP-qualified offers and 2 documents each. The public comparison content exposes two offer-like rows per market but is not ZIP-qualified, producing three intentional 2-to-0 count mismatches and no exported offers.
- **Smart Energy** — ETG and SJG Gas are `unsupported` because the current NJ shopping site offers electricity only. ACE, JCP&L, and Rockland Electric succeeded.
- **Mpower Energy** — ETG, NJNG, PSE&G, and SJG Gas are all `unsupported`; no Ohio or otherwise non-New-Jersey material was accepted as a current NJ offer.
- **Indra Energy** — all eight configured territories returned current API offers (3 per electric territory and 2 per gas territory) but no connected contracts, so every query is `partial`.
- **North American Power** — Rockland Electric returned `failed` because no unique visible “View Rates/Plans” action was available; 0 offers and 2 generic documents were retained.
- **Ameripro Energy** — ETG Gas returned `failed` because no ZIP input became available; 0 offers and 1 generic document were retained.
- **Astral Energy** — ETG Gas returned `failed` because no ZIP input became available; no offers or contracts were retained.
- **IGS Energy** — ETG Gas returned `failed` because no ZIP input became available; 0 offers and 1 generic document were retained.
- **Northeastern Power & Gas** — ETG Gas returned `failed` because the official host presented an SSL certificate hostname mismatch; no offers or contracts were retained.
- **RPA Energy / Green Choice Energy** — ETG Gas returned `failed` because no ZIP input became available; 0 offers and 1 generic document were retained.
- **South Bay Energy** — ETG Gas returned `failed` because no ZIP input became available; no offers or contracts were retained.

## Successful suppliers

The following suppliers succeeded in every configured offer-bearing territory tested for them:

- **Ambit Energy** — 4 successful electric territories.
- **CleanChoice Energy** — 3 successful electric territories.
- **Clearview Energy** — 6 successful electric/gas territories.
- **Eligo Energy** — 1 successful gas territory.
- **IDT Energy** — 5 successful electric/gas territories.
- **NJG&E** — 5 successful electric/gas territories.
- **Nordic Energy Services** — 7 successful electric/gas territories.
- **NRG** — 5 successful electric/gas territories.
- **Xoom Energy** — 6 successful electric/gas territories.

Mixed-disposition suppliers also produced successes: Constellation's 3 electric territories, Smart Energy's 3 supported electric territories, and Think Energy's 2 supported electric territories.

## Verification totals

- 115 configured queries executed.
- 287 current offers and 416 documents retained.
- Statuses: 50 `success`, 25 `partial`, 8 `blocked`, 16 `failed`, 6 verified `empty`, 3 `needs_review`, and 7 `unsupported`.
- All result schemas and retained artifact hashes verified successfully.
- The only source/export count mismatches are the three intentional Residents Energy review-only markets (2 candidate rows, 0 promoted offers each).
- Strict completed coverage: JCP&L Electric 10 suppliers; PSE&G Electric 9; ACE Electric 7; Rockland Electric 7; NJNG Gas 6; SJG Gas 6; PSE&G Gas 4; ETG Gas 1.
