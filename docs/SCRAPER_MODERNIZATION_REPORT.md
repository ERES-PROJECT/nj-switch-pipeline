# Supplier scraping modernization first pass

September 4, 2026. Scope: the seven existing specialized scrapers, generic fallback and their shared collection process. This is a passable, manually verifiable first iteration—not complete statewide coverage.

## Summary for the sponsor

The scrapers now use a common collection and reporting process. This makes maintenance easier, preserves the evidence behind collected information, and exposes missing information and failures. Original datasets are protected from accidental replacement.

All seven suppliers yielded offers during bounded PSE&G Electric checks. Gas captures also cover Direct Energy, Major Energy and Xoom. These representative checks do not certify every supplier/EDC/GDC combination.

Key achievements include retaining distinct plans with the same name or price, separating introductory pricing from contract duration, preserving reward and renewable claims, and recovering previously missed PDF information. Direct Energy's apparently blank values were fillable PDF fields; the updated parser recovers all twelve standardized sections in five sampled electric summaries.

The handoff includes offline tests, historical supplier captures, live-check commands and readable outputs. Partial results are useful for review, but must not be presented as complete market coverage.

## Function-by-function changes

| Existing function | Problem addressed | First-pass result and limitation |
|---|---|---|
| `strategy_constellation` | Duplicate utility selectors, changed cards, commodity ambiguity and price-based identity. | Product-ID cards and associated legal links; two electric offers captured. Utility-level quote only; ZIP eligibility not independently proved. Current electric options must not be used for gas. Document-host access remains unresolved. |
| `strategy_direct_energy` | ZIP alone did not prove territory/commodity; modal-based documents and duplicate names could lose offers. | Browser bootstrap plus verified product/utility response mapping and API document URLs. Five electric and three gas offers captured. Final post-fix electric discovery returned five offers; other territories and intermittent page variations remain unverified. |
| `strategy_ambit` | Legacy service-area flow redirects; popup extraction and inferred defaults no longer fit. | Replacement public shopping flow, explicit utility selection and scoped detail panels. Four electric offers; fixed structure, 12/24-month terms and explicit cancellation fee now parse. Dynamic plan-document actions lack stable hrefs and need another iteration. |
| `strategy_think_energy` | Font-size-dependent pairing and separate document handling were fragile. | Direct public HTTP endpoint with browser fallback, utility filtering, rate cross-checks and rate-ID document links. One supply offer; community solar excluded. Green percentage/source and promotions retained. Generated-document redirects encounter unresolved host policy. |
| `strategy_nrg` | Forced hidden controls, hard-coded choices and outdated card selectors produced empty results. | Visible label interactions, query-aware commodity flow, SKU-based API mapping and legal-link association. Eighteen electric offers captured. Introductory period is separate from contract length. Only the observed PSE&G electric API mapping is promoted; broader territory/gas work remains. |
| `strategy_major_energy` | Electric/gas utility names overlap; card markup and gas unit labels changed. | Commodity disambiguation, product-ID cards and sibling detail/documents. Four electric and two gas offers parse. THM maps to therm; utility comparison-price prose cannot replace the supplier rate. Document paths are robots-disallowed. |
| `strategy_xoom_energy` | Positional radios, test/schema mismatch, green/type conflation and whole-card term parsing. | Labeled commodity choices, explicit rate IDs/term attributes, shared documents and separate green facts. Five electric and four gas offers. SimpleFlex is month-to-month, not a six-month eligibility condition; its first-three-bill introduction is separate. |
| `strategy_default` | Broad page/table-number extraction could manufacture plausible plans. | Conservative structured-card/JSON discovery. Unverified context remains review-required; no claim of automatic support for remaining suppliers. |

Legacy strategy names delegate to the shared collector; both old runnable entry points use it. Diagnostic tuple calls return offers, not PDF-derived pseudo-plans. Their legacy `rate` remains cents per unit with an explicit `rate_unit`; canonical CLI exports use dollars per unit. `extract_pdf_data_from_bytes` now returns an explicitly labeled contract record. Old private-helper consumers may need migration.

## Shared implementation

- Validated queries, offers, prices, contracts and results; repaired five-digit ZIPs; explicit units and no missing-to-zero defaults.
- Hashed artifacts, source timestamps, schema/parser versions, sensitive metadata redaction and retained raw fields.
- One browser per run, isolated query contexts, bounded waits/downloads, verified TLS, conservative robots checks, HTTP retries/throttling and per-query failure records.
- Reusable offer parsing and identity-based deduplication; PDF text/tables/form fields, DOCX tables and HTML contract sections; deterministic document matching and conflict warnings.
- New run directories with JSON plus offer, contract and coverage CSV views. Supported commands never write incompatible historical output filenames.
- Hash-verified baseline snapshot; candidate-only registry generation that preserves adapter assignments; dependency lockfile, setup, replay and verification commands.

The lockfile covers the new functional pipeline and tests. Other historical inspection scripts may still need optional dependencies such as pandas. They are not the supported automated test suite. Original source remains recoverable through git and `data/legacy/pre-v2-baseline`.

## Plan comparison and deliberate limits

The API-first hybrid recommendation remains the base: Think uses direct HTTP; Direct Energy and NRG use browser-established structured responses; the other four retain source-specific HTML adapters. Shared processing is reusable, but website differences have not disappeared.

Observed platform clues include OnProton for Think, Direct Energy's own APIs, NRG's product-chart service, Constellation's ptsrvs document references, Xoom's ASP.NET flow, Major's signup/document service, and Ambit's replacement Sitecore/Next.js shopping page. These are implementation observations, not guaranteed APIs or proof that other suppliers are already supported.

This advances portions of TODO phases 0–9 and 11, plus limited reporting. It does not complete a broad production milestone. Nested Pydantic records and per-run files are the first-pass substitute for database work. No migrations, historical import, scheduling, OCR installation, paid service, LLM extraction, new suppliers or full legacy-diagnostic retirement were introduced. Failure HTML and selected JSON are saved; raw screenshots/traces are disabled to avoid unredacted sessions. Redaction remains heuristic: review artifacts before sharing; public PDFs are stored byte-for-byte.

Source restrictions and missing dynamic document links are not bypassed. Full raw clause text remains important because normalized columns do not express every exception or condition. The registry has not been reconciled against a fresh NJBPU list.

## Verification evidence

The offline suite passed **57 tests**, including ten captured supplier/commodity fixtures. Fixed counts and prices in tests apply only to those historical files. Live checks were bounded and opt-in. No customer accounts, addresses or payment details were provided, and no supply plan was selected for enrollment.

The current-parser replay produced **48 offers across ten historical cases**, all explicitly partial because document/interpretation gaps remain. Schema, relationship and artifact-hash verification passed for that replay and the synthetic demonstration. All three original data CSV hashes are unchanged; the master-registry comparison confirmed that only ZIP padding changed.

Local evidence directories:

- `data/runs/20260904T155003Z-ca8d4fe7`: seven-supplier electric collection. Direct Energy failed on a late popup here; the other six yielded offers. Do not hide that failed attempt.
- `data/runs/20260904T155546Z-ba7ab162`: post-fix Direct Energy discovery, five offers; documents intentionally skipped.
- `data/runs/20260904T153355Z-399831cb`: successful Direct Energy electric acquisition and public PDFs, reparsed by the improved extractor.
- `data/runs/20260904T154036Z-928bf19e`: gas acquisition. Major's original result predates the THM parsing fix.
- `data/runs/handoff-observed-replay`: current-parser replay of ten saved captures, **not a fresh market quote**.

Earlier reports retain their original behavior and have not been rewritten to look successful. Replay and regression tests demonstrate later parser fixes. Runs are local/gitignored; curated fixtures and instructions form the reproducible handoff.

## Next iteration

1. Verify remaining territories, especially gas and NRG's limited API mapping.
2. Resolve document permissions and Ambit's dynamic links without bypasses.
3. Improve contract template variants and field-level interpretations from saved evidence.
4. Add browser-flow mock tests and schema-change checks; replay alone cannot detect all navigation regressions.
5. Reconcile the registry, then add database/history and scheduling once collection quality is sufficient.

See [manual verification](MANUAL_VERIFICATION.md) for exact commands and expected checks.

## Quick recap: what changed and what is still missing

### Function changes in plain language

- **Constellation (`strategy_constellation`):** Fragile card/utility selection became product-ID-based HTML parsing with associated legal links; plans sharing a price are no longer treated as the same plan.
- **Direct Energy (`strategy_direct_energy`):** ZIP entry, visible cards and document modals were insufficient. The browser now establishes the shopping context, then structured product/utility responses supply offers and document URLs.
- **Ambit (`strategy_ambit`):** The old service-area/popup flow no longer matched the site. The scraper now follows the replacement shopping flow, selects the utility explicitly and reads each plan's detail panel.
- **Think (`strategy_think_energy`):** Rates were paired using presentation details such as font size. A public HTTP endpoint now supplies structured offers, with utility checks, rate-ID document links and a browser fallback.
- **NRG (`strategy_nrg`):** Hidden controls and old card selectors returned no plans. Visible labeled controls now establish context, and SKU-based API responses supply the observed electric offers.
- **Major (`strategy_major_energy`):** Overlapping utility names and changed markup confused commodity/rate extraction. Explicit commodity selection, product-ID cards and adjacent details now distinguish supplier rates from comparison prices and recognize gas `THM` units.
- **Xoom (`strategy_xoom_energy`):** Positional controls and whole-card text mixed up green claims, contract terms and eligibility conditions. Labeled controls and explicit rate/term attributes now keep those facts—and introductory billing periods—separate.
- **Generic fallback (`strategy_default` / `generic_parser`):** Broad number extraction became conservative structured-card/JSON parsing; uncertain context stays flagged rather than becoming an apparently verified offer.
- **PDF extraction (`extract_pdf_data_from_bytes` / shared contract parser):** Direct Energy's missing values were in fillable PDF fields, not ordinary text. The parser now reads those fields alongside text/tables and returns linked contract records, not extra pseudo-plans.

### Big-picture gaps

- **Coverage:** Seven suppliers have representative captures, not complete coverage across the four EDCs and four GDCs. Other suppliers, broader gas/territory validation and fresh NJBPU registry reconciliation remain.
- **Complete contract data:** Ambit's dynamic document links and restricted/unresolved document hosts still leave gaps. More template variants, scanned-PDF OCR, document matching and interpretation of fees, deals, green claims and renewal conditions are needed.
- **Change resilience:** Shared processing reduces duplicated work, but supplier-specific adapters remain. Broader browser-flow tests, automated site-change detection and alerts are not yet in place.
- **Ongoing operation:** Database/history, legacy-data migration, scheduled refreshes and a managed review queue remain unfinished. The combined CSV is a run-specific export, not a historical data system.
- **Validation boundary:** The 57 passing tests verify saved examples; they do not certify current quotes or statewide completeness. All ten replayed supplier cases remain explicitly partial.

## Next-two supplier investigation — September 11, 2026

- **Frontier Utilities:** The former generic scraper looked for the wrong submit labels and reported no content. The current page uses **View Plans**; submitting ZIP `07102` redirects to `portal.frontierutilities.com/Enrollment/NE/Campaign?Zip_Code=07102`. The enrollment service returned HTTP 503 during the bounded check, so no current offers could be verified. A dedicated `frontier` adapter now follows that public ZIP flow and identifies service/access failures instead of reporting an empty market.
- **CleanChoice Energy:** Both the historical capture and the current bounded check encountered access restrictions. The current run stopped because `https://cleanchoiceenergy.com/robots.txt` returned HTTP 403, so the pipeline could not establish permission to collect. A dedicated `cleanchoice` adapter is assigned for explicit reporting and future retesting, but no restriction was bypassed and no current offer parser is claimed.

**Still missing:** Neither supplier has a successful current offer fixture, verified rate/fee/green extraction, or collected current contract summaries. Frontier still needs a successful enrollment-portal response across its listed electric and gas territories. CleanChoice needs an accessible, policy-permitted public shopping source before its HTML/API shape can be verified. These adapters are investigated and explicitly classified, not production-complete.

## All-assigned-adapter completion pass — September 11, 2026

This pass exercised all **47 supplier/utility combinations currently assigned to the nine explicit adapters**. It is complete for that registry scope: **34 combinations returned verified offers, one returned a verified empty market, four are explicitly unsupported by the current public source, and eight are externally blocked**. “Complete” here means each assigned combination has an evidence-backed result and an offline regression fixture; it does not mean every TPS in the statewide registry is automated.

| Supplier | Assigned combinations | Current disposition | Current extraction path | Contract/document result |
|---|---:|---|---|---|
| Ambit Energy | 4 | 4 offer-bearing | Public shopping flow, explicit utility choice, scoped semantic plan DOM | Two shared public HTML documents per combination; plan-specific dynamic actions still lack stable URLs. |
| Constellation Energy | 7 | 3 electric offer-bearing; 4 gas unsupported | Semantic product IDs and sibling detail dialogs | Product-linked Terms references found; S3 host policy returned 403, so documents were not downloaded. |
| Direct Energy | 8 | 8 offer-bearing | Browser-established context plus structured product/utility responses | 15 document records per electric combination and 6 per gas combination; form fields recover standardized summary values. |
| Think Energy | 3 | 2 offer-bearing; Rockland explicitly empty | Direct public offer API with utility filtering | Rate-ID document references found; document host returned 403. |
| NRG | 5 | 5 offer-bearing | Commodity/utility modal establishes context; product-chart JSON maps SKUs | 18 linked document records per electric combination and 4 shared records per gas combination. |
| Major Energy | 6 | 6 offer-bearing | Product-ID DOM and adjacent detail records | Product-linked Terms URLs found; signup host disallows collection through robots policy. |
| Xoom Energy | 6 | 6 offer-bearing | ASP.NET utility flow and semantic rate/term attributes | 13 document records per electric combination and 9 per gas combination; incomplete standardized sections remain flagged. |
| Frontier Utilities | 5 | 5 blocked | Dedicated ZIP/View Plans flow into enrollment portal | Portal consistently returned HTTP 503; no offer or contract data can be claimed during the outage. |
| CleanChoice Energy | 3 | 3 blocked | Dedicated public-entry adapter | Robots-policy request returned HTTP 403; the collector stopped without bypassing it. |

The offer-bearing combinations produced **174 current offer snapshots**. The contract runs produced **220 document records** across Ambit, Direct, NRG and Xoom. Counts are per utility snapshot, so shared documents may recur across territories and should not be read as 220 unique legal documents.

The completion work also adds bounded initial-navigation retry, removes Direct Energy’s redirect/navigation race, allows Xoom’s optional second commodity dialog, expands NRG to every assigned electric/gas utility with correct `USD/kWh` versus `USD/therm` units, treats Think’s verified zero-offer utility as `empty`, and distinguishes source outages/access blocks from parser failures. Every positive and explicit-disposition combination now has an offline fixture; representative 403/503 pages are separately regression-tested.

### Final completion verification

- The master-table audit found **47 assigned registry rows, 47 matching fixtures, zero missing fixtures, and nine explicit adapters**.
- The complete offline suite passed **98 tests** on September 11, 2026. It covers positive offer captures, explicit empty/unsupported/blocked dispositions, utility and commodity scoping, rate units, contract parsing/matching, artifact integrity, and representative access-failure pages.
- The final post-fix Direct Energy PSE&G Gas live discovery returned **3 offers**, verified its utility context, used the browser-bootstrap/API method, recorded zero errors, and passed result-schema/artifact-hash verification.
- Live rates remain point-in-time evidence. A passing fixture proves deterministic parsing of its saved public capture, not that a supplier’s future prices or website availability will remain unchanged.

### Succinct function-change summary

- **Constellation:** The old parser only read visible cards. It now joins each `data-planid` card to its sibling detail dialog for fees, deals, greenness and Terms references; gas is explicitly unsupported because the public source exposes only electric utilities.
- **Direct Energy:** Waiting on visible cards raced a two-step redirect. The adapter now waits for the product-chart URL and reads captured structured product/utility responses, then associates their document URLs.
- **Ambit:** The obsolete service-area popup became a replacement shopping flow. The adapter selects the utility and reads scoped plan/detail DOM; stable plan-specific document URLs are still absent.
- **Think Energy:** Styled HTML pairing was replaced by a direct JSON request. Utility objects and rate IDs now control matching; Rockland is a verified empty result rather than a generic failure.
- **NRG:** The prior code forced old controls and one utility. The adapter now uses the visible modal, utility-specific API slugs and separate electric/gas product arrays.
- **Major Energy:** Ambiguous utility text and first-card parsing became commodity-aware product-ID/detail parsing; legal links are found but policy-blocked.
- **Xoom Energy:** Positional radio assumptions became label-based selection with an optional dual-commodity modal; rate type, green attributes, terms and shared documents remain separate.
- **Frontier/CleanChoice:** Generic scraping became dedicated entry flows with explicit source-unavailable reporting, preventing 503/403 pages from being reported as zero-plan markets.

### Missing, big picture

- The registry still contains TPS suppliers not assigned to these nine adapters; statewide production coverage is not complete.
- Frontier needs its enrollment portal restored, and CleanChoice needs a policy-permitted public source, before either can yield current offer data.
- Constellation, Think and Major document hosts remain policy/access-blocked; Ambit still lacks stable plan-specific contract links.
- Contract interpretation is useful but incomplete for some templates, especially Xoom’s distribution-company/switching-time sections and shared Terms documents.
- Scheduling, historical database storage, material-change alerts, a managed review queue, OCR, and full NJBPU registry reconciliation remain future phases.

## Six-supplier EDC baseline — September 11, 2026

Six additional TPS suppliers now have electric-only adapter assignments covering **ten EDC combinations**. Gas rows for the same suppliers intentionally remain on the default path for a later gas phase. Seven combinations are offer-bearing, one is explicitly empty, one is explicitly unsupported for the configured ZIP, and one is externally blocked. The offer-bearing combinations produced **25 current offer snapshots**.

| Supplier | EDC combinations | Baseline result | How the source actually works | Documents/full-data result |
|---|---:|---|---|---|
| Smart Energy | JCP&L, ACE, Rockland | One offer in each EDC | ZIP submission returns JSON; multi-utility ZIPs embed a utility-choice form. The adapter submits that public choice, returns to the plan page, and parses the scoped plan card. | Full collection retrieved two terms/disclosure records per EDC. No standardized Contract Summary was exposed in the captured plan card. |
| Clearview Energy | JCP&L, ACE | Five offers in each EDC | A residential ZIP form leads to product labels whose data attributes identify commodity, utility, and product. Those attributes are safer than matching visible headings alone. | Seven document records per EDC: five offer summaries were partially parsed, with distribution-company fields still missing; shared/unmatched documents remain review items. |
| IDT Energy | JCP&L, Rockland | Six offers in each EDC | Two public form steps establish commodity, ZIP, and utility. Offer identity and exact rate/type/term context live in each rate-table enrollment URL; adjacent detail rows carry rewards and renewable descriptions. | Seven document records per EDC; six offer-specific terms pages extracted and one shared Contract Summary parsed. Two ancillary external links failed (404 and external robots-policy lookup), without losing the offer data. |
| CleanSky Energy | Rockland | Blocked | Collection stops when the supplier's robots-policy request returns HTTP 403. | No offers or contracts are claimed, and the restriction is not bypassed. |
| Green Mountain Energy | Rockland | Unsupported for test ZIP | The JavaScript application hydrates after navigation; the adapter waits for the application result instead of capturing an empty shell. ZIP `07430` then redirects to the supplier's explicit `zip-code-not-served` result. | No offer documents can be associated because the supplier reports the configured market as not served. |
| Great American Gas & Electric | PSE&G | Explicitly empty | The visible utility-logo grid mirrors hidden real form controls. After the public PSE&G form context is submitted, the site states that it has no current products for the area. | General NJ legal links are visible later in the enrollment form, but there is no current offer to associate with them. |

The full document-enabled pass for Smart, Clearview, and IDT produced **34 document records** across their seven offer-bearing combinations. All results remain `partial` because baseline capability does not imply complete standardized-contract interpretation. No plan was selected, and no name, address, account number, phone, email, consent, or payment information was submitted.

Final verification passed **109 offline tests**. The full collection output and the explicit empty/unsupported output both passed result-schema and artifact-hash verification.

### Succinct function-change summary for these six

- **Smart Energy:** The scraper initially expected offers in the first HTML page. ZIP submission actually returned JSON containing either a utility-choice fragment or a completion result; the adapter now follows that response and then parses the plan HTML.
- **Clearview:** Generic headings could mix commercial, gas, or wrong-utility products. The adapter now uses the residential form and product-level commodity/utility attributes before normalizing the displayed cents-per-kWh rate.
- **IDT:** The first page did not contain offers. The adapter now completes the public commodity/ZIP and utility steps, then reads offer IDs and exact rate metadata from the rate-table URLs and joins the adjacent detail rows.
- **CleanSky:** This is not currently an HTML-selector problem. Access stops at an HTTP 403 robots-policy response, which is recorded as blocked.
- **Green Mountain:** Capturing immediately after navigation saved an empty JavaScript shell. The adapter now waits for hydration and records the site's explicit not-served destination.
- **Great American:** The logo tiles were presentation controls, while the form's real values lived in hidden selects. The adapter updates the underlying public control and distinguishes the site's explicit no-products message from a parsing failure.

### Still missing after this baseline

- CleanSky needs a policy-permitted public source; Green Mountain and Great American need a newly served/testable EDC ZIP or a supplier-side market change before positive offer parsing can be developed.
- Smart does not expose a standardized Contract Summary in the captured plan card. Clearview is missing distribution-company fields in parsed summaries, and IDT has shared/unmatched summary material plus two inaccessible ancillary links.
- These six adapters have saved offline fixtures, but live navigation can still change independently of fixture parsing. Scheduled browser checks, DOM/API schema alerts, history storage, and review workflows remain future work.
- Gas support for these suppliers was intentionally excluded from this pass and remains unimplemented.

## All-functions compiled CSV run — September 11, 2026

The full `collect` command exercised all **76 registry combinations across 21 TPS suppliers**, including explicit adapters, the conservative generic/default function, and intentionally skipped/manual combinations. The first pass returned 181 offers and 264 document records. NRG PSE&G Electric encountered a Playwright wait after its click handler had already fired; changing that action to dispatch the public control and explicitly observe the next modal/URL produced 18 offers and 18 documents on the focused retry.

The corrected aggregate contains **199 verified offer rows** from ten TPS suppliers with current offers. The reader-facing CSV is sorted by TPS and deliberately excludes the 35 coverage-only combinations from the collection run (13 failed, 12 blocked, eight unsupported, and two explicitly empty). Those diagnostic dispositions remain available in the run-level coverage output instead of appearing as non-plan rows.

The reader-facing output is now split by purpose. `offer_prices.csv` contains one purchasing-oriented row per plan and adds stable offer/product identifiers so same-rate plans can be distinguished. `contract_information.csv` contains one row per collected document, its standardized contract-summary sections, normalized fields, parsing state, and matched plan identities. `offer_documents.csv` records the many-to-many plan/document links. `coverage.csv` retains every attempted supplier/territory disposition, including zero-offer and blocked cases. Every reader-facing record occupies exactly one physical line. The technical `offers.csv`, `contracts.csv`, and complete `results.json` remain available for auditing, and `compiled_offerings.csv` remains as a compatibility copy of the offer-price table.

The final CSV is `data/20260911T154242Z_all_tests_compiled_offerings.csv`. Both source runs pass result-schema and artifact-hash verification. The offline suite passes **109 tests** using a workspace-local pytest temporary directory. The default Windows pytest directory was inaccessible during one elevated browser invocation; that environmental error did not occur in the isolated rerun.

## Multi-table live verification — September 17, 2026

The full 76-row registry run was followed by focused retries for five developed-adapter rows that initially timed out. NRG's ZIP, commodity, and utility actions now observe the resulting modal or product state instead of waiting for unrelated page-wide activity; Direct Energy reloads one stalled public “Please Wait” transition; and Frontier observes the enrollment URL after submitting ZIP. The corrected retries recovered 18 NRG PSE&G Electric offers, 18 NRG ACE Electric offers, 12 NRG SJG Gas offers, three Direct Energy ETG Gas offers, and Frontier's explicit external block. A new `consolidate` command replaces matching failed rows with their retry evidence and rebuilds the aggregate outputs.

The verified consolidated run contains **200 offers, 286 collected documents, 240 explicit offer/document links, and 76 coverage rows**. All 15 explicitly assigned adapters now have a non-failed disposition for every assigned registry row. The remaining 13 `failed` rows all use the generic/default path and therefore still require dedicated supplier or gas adapters. Twelve additional rows are explicitly blocked, eight unsupported, and two verified empty; those statuses are retained rather than converted into offers.

Reader-facing output is split into `offer_prices.csv`, `contract_information.csv`, `offer_documents.csv`, and `coverage.csv`, with a four-sheet Excel workbook for filtering and review. The final offline suite passes **110 tests**, and both the consolidated evidence tree and exported workbook were re-opened and structurally verified.

### Succinct function-change summary

- **NRG:** Page-wide load and click completion were unreliable even after the shopping controls changed state. The adapter now treats the full-load event as optional and observes the modal/product state directly after ZIP, commodity, and utility actions.
- **Direct Energy:** ETG Gas occasionally remained on the site's loading shell after ZIP submission. The adapter now performs one bounded reload while preserving the public ZIP context, then waits for product cards.
- **Frontier:** The View Plans handler completed before its portal navigation settled. The adapter now follows the enrollment URL explicitly and records the portal's block instead of a generic click timeout.
- **Reporting:** Offer pricing, contract contents, offer/document relationships, and collection coverage are separate one-record-per-line tables. Product IDs and internal offer keys remain visible so identical prices are not mistaken for duplicate plans.

### Missing, big picture

- Thirteen registry rows still use the generic/default path and need dedicated supplier or gas navigation before they can be called functional.
- Blocked suppliers and document hosts still require a policy-permitted accessible source; the collector does not bypass those restrictions.
- Many offer-bearing results remain `partial` because a verified price does not guarantee a complete or uniquely matched standardized Contract Summary.
- OCR, historical database storage, scheduled change alerts, and a managed manual-review queue remain future phases.

## Multi-ZIP identity pass — September 17, 2026

Targeted representative ZIPs were added only to the three markets whose empty or unsupported result needed stronger evidence. Great American Gas & Electric returned an explicit no-products result in PSE&G ZIPs `07102`, `07302`, and `08901`. Think Energy's public API returned no Rockland offers for `07430`, `07446`, and `07480`. Green Mountain explicitly reported all three Rockland ZIPs as not served. These observations strengthen the market disposition without multiplying the offer table.

The reporting model now separates canonical offers from ZIP observations. `offer_prices.csv` groups materially identical offers by a purchasing fingerprint that excludes ZIP but includes product identity, rate, term, fees, introductory pricing, renewable attributes, and incentives. `offer_observations.csv` retains each ZIP-level offer, source product identity, artifact, and duplicate diagnostics. Same-rate plans remain distinct through their fingerprints without redundant same-rate count/status columns in the canonical table. Contract rows and offer/document relationships are also consolidated across identical ZIP observations.

The 82-query consolidated output contains 200 canonical offers, 200 ZIP-level offer observations, 286 canonical documents, 300 raw document observations, 240 canonical offer/document links, and 82 coverage rows. No positive offer happened to repeat across the six new ZIP queries because the three investigated markets remained empty or unsupported; deterministic tests verify that a repeated positive plan collapses to one canonical row and that different product IDs with the same rate remain separate.

## Supplier-coverage expansion — September 17, 2026

Coverage, rather than reporting polish, is now the primary implementation metric. Thirteen of the former generic/default rows received supplier-specific handling, leaving only Smart Energy's SJG and ETG gas rows on the generic path. Nineteen of the 21 master-list suppliers now have a dedicated adapter for at least one listed market; Alpha Gas & Electric and American Power & Gas remain explicit manual-review suppliers because their public flows require enrollment context or a full address.

The verified consolidated evidence is in `data/runs/20260917-supplier-coverage-expansion-final2`. It contains **219 canonical offers from 12 suppliers across 82 ZIP-level coverage queries**. The new live results add two Residents Energy offers in each of PSE&G, NJNG, and SJG gas; four IDT Energy offers in each of PSE&G and NJNG gas; one Clearview Energy offer in each of NJNG and SJG gas; and three Eligo Energy NJNG gas offers. NJG&E is explicitly blocked by its telephone-only rate page, NextEra explicitly reports no web-enrollment offer for the configured ACE ZIP, and CleanSky's known policy block now covers its gas rows.

### Succinct function-change summary

- **Clearview:** The scraper required a removed residential toggle and assumed one ZIP form; the live page now renders equivalent responsive forms and tags returned products by commodity and utility, so the adapter submits one visible form and filters those attributes.
- **IDT:** The scraper always selected Electric and rejected non-`E` offer URLs; it now selects the visible Gas label for gas queries, accepts `G` offer records, and normalizes the rate as dollars per therm.
- **Residents:** The generic form missed a public current-rate page; the new adapter parses only rows after the natural-gas table header and scopes them to the requested GDC.
- **Eligo:** The generic ZIP guess was unnecessary; the new adapter opens the official NJNG utility route and parses each rate card plus its encoded term/rate identity.
- **NextEra:** The generic action selector missed a disabled legacy submit control; the adapter submits the public ZIP form directly and preserves the supplier's explicit no-web-offer result.
- **NJG&E:** The generic handler searched for plan controls even though the official page currently routes customers to telephone support; the adapter now reports that source limitation as blocked.

### Missing, big picture after this pass

- Smart Energy's two gas rows still need a verified gas-specific flow and parser; they are the only remaining generic/default rows.
- Alpha Gas & Electric and American Power & Gas still require a policy-approved non-personal enrollment context or an alternate public feed.
- CleanChoice, CleanSky, Frontier, and NJG&E require supplier-side access restoration, permission, or an alternate official source before they can become offer-bearing.
- Green Mountain, Great American, Think Rockland, and NextEra currently return explicit not-served or no-offer results; periodic retries can detect market changes.
- Contract completeness, history storage, scheduling, and change alerts remain deferred until supplier coverage is further improved.

## Public-source completion and offer ordering — September 18, 2026

All 21 suppliers on the master list now have dedicated handling, and no row remains on the generic `default` or manual `skip` path. Smart Energy gas is explicitly unsupported because its current NJ shopping pages publish electricity offers only. Alpha Gas & Electric now yields one ACE electric offer from its official public NJ rate-sheet PDF without entering enrollment information. American Power & Gas now yields one PSE&G residential gas offer from its official public comparison table without using an address; ETG is explicitly unsupported because that table does not list it.

The verified aggregate is `data/runs/20260918-supplier-coverage-final`: **221 canonical offers from 14 suppliers across 82 coverage queries**. Its offer-price and observation tables put electric rows first and gas rows second, with suppliers alphabetical inside each block. The full offline suite passes **125 tests**, and result schemas plus artifact hashes verify successfully.

### Succinct function-change summary

- **Smart Energy gas:** The generic scraper looked for a ZIP offer form, but the official NJ source currently supports electric shopping only; gas rows now stop as explicit unsupported markets.
- **Alpha:** The old status assumed enrollment was required, but the supplier links a public PDF; the adapter extracts the labeled ACE rate, term, fee, and renewable claim from that document.
- **American Power & Gas:** The old status assumed a full address was required, but a public NJ comparison table exposes bill examples; the adapter divides supplier total by usage, confirms every residential tier implies the same unit rate, and emits one offer rather than four duplicates.
- **Offer output:** The canonical offer and observation exports now sort by commodity rank, supplier, utility, plan, and rate, producing electric and gas blocks with alphabetical TPS ordering.

### Missing, big picture

- Alpha's public rate sheet is dated 2025-01-15 and needs freshness monitoring even though it is presently the supplier's linked source.
- AP&G does not publish ETG in the current comparison table; Smart Energy does not publish NJ gas shopping offers.
- Policy/source blocks remain for CleanChoice, CleanSky, Frontier, and NJG&E; the adapters report these instead of bypassing them.
- Many offer-bearing rows remain partial because complete, uniquely matched contract summaries are not always exposed.
- Historical storage, scheduled collection, change alerts, and captured fixtures for the newest adapters remain future work.

## User-confirmed flow recovery — September 18, 2026

Manual browser observations were used as reproducible test cases rather than as copied plan data. The revised flows were run across every registry market for the affected suppliers, plus the user-confirmed `07430` PSE&G-gas observation for CleanSky. The verified aggregate is `data/runs/20260918-user-confirmed-supplier-coverage-final`: **83 ZIP-level queries, 261 offer observations, and 18 offer-bearing suppliers**. All schemas and artifact hashes verify, and the complete offline suite passes **131 tests**.

| Supplier | Current result | What changed |
|---|---|---|
| CleanChoice | 3 plans in each of PSE&G, JCP&L, and ACE | Opens `/plans?area=ZIP`, verifies the displayed ZIP/utility, and scopes each Select button to its containing plan card. A visible (`--headed`) Playwright session is currently required because the same public route blocks the bundled headless browser. |
| NextEra Energy Services | 2 ACE plans | Types ZIP keystrokes so the legacy handler enables Continue, then selects ACE in the second utility modal. `data-rate` supplies stable product identity. |
| CleanSky Energy | 3 Rockland electric; 6 PSE&G gas at both tested ZIPs; 5 SJG gas; 5 ETG gas | Dismisses Cookiebot, handles an already-open utility modal, selects the requested commodity/utility and opts out of the other commodity, then waits for asynchronous plan cards. Product, term, rate, and document metadata come from card attributes. |
| NJG&E | 2 NJNG gas and 2 SJG gas | Ignores the generic telephone-support text, submits the residential ZIP form, verifies the preselected gas utility, continues, and parses each returned rate card. |
| Constellation gas | PSE&G explicitly empty; other configured GDCs unsupported | The apparent gas area uses electric utility labels. PSE&G selection explicitly returns no plans; the products visible elsewhere are labeled “Power Plan” and “Rate per kWh,” so they are not relabeled as gas offers. |
| American Power & Gas ETG | Unsupported | Address-based inspection did not offer Elizabethtown Gas in the utility selector. A gas card shown for another selectable utility cannot be assigned to ETG. The public comparison-table PSE&G gas offer remains retained. |

### Succinct function-change summary

- **CleanChoice:** Generic ZIP/button discovery became a direct plan route plus plan-card scoping; the remaining issue is headless-only access blocking.
- **NextEra:** Synthetic form submission skipped a required utility screen; real key events and the utility modal now return ACE plans.
- **CleanSky:** Generic navigation stopped at robots/modal behavior; the scraper now follows Cookiebot, dual-commodity utility selection, modal animation, and asynchronous cards.
- **NJG&E:** A generic telephone-text check stopped too early; the scraper now completes the ZIP and confirmed-utility stages before parsing offers.
- **Constellation gas:** A gas heading looked offer-bearing, but its controls/data were electric or explicitly empty; incompatible kWh products remain excluded.

### Missing, big picture

- CleanChoice needs an automatic, isolated visible-browser retry or an official alternate feed before unattended headless scheduling is reliable.
- Frontier remains externally unavailable during the tested portal flow.
- Constellation currently exposes no verified NJ gas offers through this page, and AP&G does not expose ETG; neither should be filled using a different utility's card.
- Several new offer-bearing rows are still `partial` because linked terms are shared, blocked, or not uniquely matched to every plan.
- Historical storage, scheduling, change detection, alerting, and broader ZIP sampling remain deferred until coverage behavior stabilizes.
