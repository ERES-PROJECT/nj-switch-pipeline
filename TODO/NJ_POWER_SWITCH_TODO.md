# NJ Power Switch Pipeline TODO

## Status legend

- `[ ]` Untouched
- `[ - ]` In progress
- `[ x ]` Completed

Only change a status when the item itself meets its acceptance criteria. Do not mark an entire phase complete while any required item beneath it remains incomplete.

## Phase 0: Planning and baseline protection

- [ x ] Analyze the current supplier registry, scraper strategies, parsers, data files, demo results, debug artifacts, and logs.
- [ x ] Define the recommended API-first hybrid collection architecture.
- [ x ] Write the full implementation plan in `docs/NJ_POWER_SWITCH_IMPLEMENTATION_PLAN.md`.
- [ x ] Create a read-only backup or immutable snapshot of the current `data/` outputs before changing any exporter.
- [ ] Record the provenance, capture date, source type, and known limitations of each existing CSV.
- [ ] Label the March NJ Energy Ratings-derived CSVs as legacy third-party data.
- [ x ] Confirm that no current first-party scraper output can overwrite an incompatible legacy filename.
- [ ] Inventory all Python dependencies imported by functional and diagnostic scripts.
- [ x ] Add a locked project dependency definition and reproducible setup instructions.
- [ x ] Add a root project README that links to the implementation plan and this TODO.
- [ x ] Decide and document the supported Python version.
- [ ] Add standard commands for install, test, collect, validate, report, and export.
- [ ] Establish `data/raw`, `data/processed`, `data/exports`, and `data/fixtures` directories with retention rules.

### Phase 0 completion gate

- [ ] Verify that existing data is recoverable and no new command overwrites it.
- [ ] Verify that a new contributor can install the project and run offline tests from documented commands.

## Phase 1: Registry cleanup and authoritative scope

- [ x ] Restore every representative New Jersey ZIP code to exactly five digits.
- [ - ] Add validation that rejects malformed or non-five-digit ZIP values.
- [ - ] Create canonical IDs and aliases for ACE, JCP&L, PSE&G Electric, Rockland Electric, ETG, NJNG, PSE&G Gas, and SJG.
- [ ] Define canonical supplier names independently from website display names.
- [ ] Collect the current NJBPU active TPS license list and preserve the raw source artifact.
- [ ] Collect the current NJBPU supplier-by-EDC/GDC relationships and preserve the raw source artifact.
- [ ] Reconcile NJBPU suppliers with `master_third_party_supplier_list.csv`.
- [ ] Identify suppliers missing locally, suppliers no longer active, and naming aliases.
- [ ] Review every proposed supplier or territory removal manually before applying it.
- [ ] Record BPU license number, status, effective date, and anniversary date when available.
- [ ] Verify one representative ZIP for every utility territory and document how it was chosen.
- [ ] Separate residentially available suppliers from commercial-only or otherwise inapplicable entries.
- [ ] Preserve an explicit reason for every skipped or manual-review supplier.
- [ ] Replace free-text scraper status values with a validated status enumeration.
- [ x ] Ensure regenerating the supplier registry preserves adapter/platform assignments.

### Phase 1 completion gate

- [ ] Produce a reconciliation report showing authoritative NJBPU combinations versus local combinations.
- [ ] Confirm that every active in-scope supplier/territory combination has a ZIP, source, and collection disposition.

## Phase 2: Canonical models and database

- [ x ] Create the new `src/nj_switch` package without deleting the existing scraper.
- [ ] Implement the canonical `Supplier` model.
- [ ] Implement the canonical `Utility` and `ServiceTerritory` models.
- [ ] Implement the canonical `Plan` model.
- [ ] Implement the canonical `PlanSnapshot` model.
- [ - ] Implement the canonical `ContractSummary` model with every NJBPU standardized section.
- [ ] Implement the canonical `Incentive` and `RenewableAttribute` models.
- [ - ] Implement the canonical `SourceArtifact`, `CollectionRun`, and `CollectionResult` models.
- [ - ] Distinguish missing, unknown, not applicable, zero, and false values in all models.
- [ x ] Define canonical electricity and gas rate units and explicit supported conversions.
- [ x ] Preserve raw values and units beside normalized values.
- [ ] Select SQLite as the initial operational system of record or document an approved alternative.
- [ ] Create database migrations for all canonical tables and indexes.
- [ ] Add uniqueness constraints that prevent accidental duplicate plans and artifacts.
- [ ] Add effective timestamps and first/last observation timestamps.
- [ ] Add source, capture time, parser version, and artifact foreign keys to extracted records.
- [ ] Implement transactional database writes per supplier/territory result.
- [ ] Implement deterministic database-to-CSV exports.
- [ x ] Add schema-version metadata to every export.

### Phase 2 completion gate

- [ ] Round-trip representative canonical records through validation, database storage, and CSV export.
- [ ] Confirm that every exported fact can be traced to a source artifact.

## Phase 3: Artifact storage and collection runtime

- [ ] Define the immutable raw artifact directory convention by date, run, supplier, utility, and commodity.
- [ x ] Implement SHA-256 hashing and content-addressed deduplication.
- [ - ] Implement safe storage for JSON, HTML, PDF, DOCX, screenshots, traces, and response metadata.
- [ - ] Redact cookies, authorization headers, session tokens, personal data, and sensitive query parameters.
- [ x ] Add automated tests for artifact redaction.
- [ - ] Implement collection run creation, completion, failure, and recovery states.
- [ x ] Define machine-readable error categories.
- [ - ] Implement retries with exponential backoff and jitter for transient failures.
- [ - ] Implement domain-level concurrency and request-rate limits.
- [ x ] Implement one Playwright browser per run and isolated contexts per supplier/platform.
- [ ] Reuse a context for multiple territories only when state isolation is verified.
- [ ] Replace arbitrary sleeps with response-, navigation-, or locator-based waits.
- [ - ] Capture final HTML, screenshot, trace, and candidate network metadata on browser failure.
- [ ] Block nonessential assets only after verifying that this does not change application behavior.
- [ x ] Ensure one supplier failure does not stop unrelated supplier runs.
- [ - ] Add graceful shutdown that closes contexts, the browser, artifact writers, and database transactions.

### Phase 3 completion gate

- [ ] Run a simulated multi-supplier collection using fixtures and verify isolated results and artifacts.
- [ ] Confirm that logs and artifacts contain no secrets or protected personal information.

## Phase 4: API and structured-data discovery

- [ - ] Add Playwright request, response, request-finished, download, and WebSocket observation hooks.
- [ - ] Classify candidate JSON responses using content type, URL patterns, and payload keys.
- [ - ] Save redacted candidate response bodies with request/response metadata.
- [ x ] Detect embedded JSON, JSON-LD, Next.js state, and other structured data in HTML.
- [ x ] Create a discovery command that runs one supplier/territory and produces a candidate endpoint report.
- [ - ] Identify the request triggered by ZIP entry for each existing specialized supplier.
- [ - ] Identify the request triggered by utility selection for each existing specialized supplier.
- [ - ] Identify the request triggered by commodity selection for each existing specialized supplier.
- [ - ] Determine which endpoints can be replayed safely through the browser request context.
- [ x ] Implement direct `httpx` collection for stable public endpoints where permitted.
- [ ] Preserve request variables needed for ZIP, utility, commodity, and service class.
- [ - ] Detect shared API hostnames, response shapes, and document services across suppliers.
- [ - ] Group suppliers into platform clusters based on collected evidence.
- [ x ] Document endpoints as implementation details that may change, not guaranteed public APIs.

### Phase 4 completion gate

- [ ] Produce a platform-clustering report for all currently specialized suppliers.
- [ x ] Demonstrate at least one supplier collected from structured data without parsing rendered plan-card CSS.

## Phase 5: Shared offer extraction and normalization

- [ - ] Create a field-alias registry for common offer JSON and HTML labels.
- [ - ] Parse supplier product IDs, rate IDs, plan names, rates, units, terms, and rate structures.
- [ - ] Parse introductory rates and introductory durations.
- [ - ] Parse monthly, enrollment, cancellation, and other fees without defaulting missing values to zero.
- [ - ] Parse discounts, cashback, gift cards, rewards, and eligibility conditions.
- [ - ] Parse renewable indicator, percentage, source, certification, and marketing claims separately.
- [ ] Parse tier thresholds and tier rates.
- [ - ] Parse enrollment links, detail links, and contract-document references.
- [ - ] Normalize supplier and utility aliases through shared lookup tables.
- [ x ] Normalize electricity rates using one documented canonical unit.
- [ x ] Preserve gas source units and perform conversions only under explicit supported rules.
- [ x ] Retain raw field names and values for audit and parser debugging.
- [ ] Create configurable plausibility ranges that flag rather than silently discard unusual rates.
- [ x ] Implement deterministic offer deduplication.
- [ ] Implement material-change comparison against the previous snapshot.

### Phase 5 completion gate

- [ ] Validate representative fixed, variable, indexed, introductory, green, fee-bearing, tiered, and incentive-bearing offers.
- [ ] Confirm that an unchanged plan does not create a false material-change alert.

## Phase 6: Contract-document collection and extraction

- [ - ] Create document discovery from offer APIs, rendered links, modal contents, and browser download events.
- [ - ] Resolve relative document URLs and redirect chains.
- [ x ] Detect actual content type independently of filename extension.
- [ - ] Store identical documents once by hash while retaining all plan relationships.
- [ x ] Implement native PDF text and table extraction.
- [ - ] Implement PDF layout-aware label-to-value association.
- [ x ] Implement DOCX table and paragraph extraction with `python-docx`.
- [ - ] Implement HTML contract table, definition-list, and section extraction.
- [ ] Implement OCR fallback for image-only PDFs.
- [ - ] Add the official NJBPU standardized section labels and known label variants.
- [ - ] Extract supplier information and responsibility statement.
- [ - ] Extract price structure, fixed period, variable-rate method, index, range, and ceiling.
- [ - ] Extract generation/supply price and introductory period.
- [ - ] Extract savings statement and reference-price methodology.
- [ - ] Extract switching-time disclosure.
- [ - ] Extract incentives and associated terms.
- [ - ] Extract cancellation/rescission disclosure.
- [ - ] Extract expected contract start timing.
- [ - ] Extract contract term and exact end date.
- [ - ] Extract early-termination applicability, fee, calculation, and avoidance conditions.
- [ - ] Extract renewal notice, options, consent, and post-term behavior.
- [ - ] Extract distribution-company identity, contact information, billing/delivery statement, and emergency instructions.
- [ x ] Preserve the full raw text associated with every extracted section.
- [ - ] Add completeness scoring based on expected standardized sections.
- [ x ] Flag ambiguous or missing sections for manual review.

### Phase 6 completion gate

- [ ] Parse representative PDF, DOCX, HTML, and scanned contract fixtures offline.
- [ ] Confirm that each structured field retains the exact supporting raw text and artifact reference.

## Phase 7: Plan-to-contract matching

- [ - ] Define matching priority using product ID, rate ID, document URL, plan name, term, rate, utility, and commodity.
- [ - ] Implement exact matching on supplier/platform identifiers.
- [ - ] Implement deterministic composite-key matching when identifiers are unavailable.
- [ - ] Reject supplier, utility, or commodity conflicts.
- [ - ] Flag multiple plausible matches instead of selecting one silently.
- [ - ] Represent contracts that legitimately apply to multiple plan snapshots.
- [ x ] Prevent contract-derived data from creating duplicate pseudo-plan rows.
- [ x ] Store match method, evidence, and review status.
- [ - ] Add fixtures for exact, composite, shared-document, ambiguous, and failed matches.

### Phase 7 completion gate

- [ ] Achieve deterministic matching for all demonstrated contract-bearing suppliers.
- [ ] Verify that HTML offer facts and contract facts appear in one related plan view without losing provenance.

## Phase 8: Adapter framework

- [ - ] Define the base adapter interface and version metadata.
- [ - ] Define platform adapters and supplier configuration overlays.
- [ x ] Support accessible role/name and label-based browser locators.
- [ x ] Support stable semantic attributes and API-response patterns.
- [ - ] Restrict structural CSS selectors to documented last-resort cases.
- [ x ] Move utility option aliases out of Python and into validated configuration.
- [ x ] Move supplier entry URLs and representative inputs into configuration.
- [ ] Implement adapter health checks.
- [ x ] Require one or more offline fixtures for every automated adapter.
- [ ] Add an adapter-development guide and template.
- [ - ] Define when an adapter must be downgraded to manual review.
- [ x ] Add versioned parser/adapter identifiers to collection results.

### Phase 8 completion gate

- [ ] Implement one platform adapter supporting more than one supplier or document platform where evidence permits.
- [ ] Confirm that adapter code contains only source-specific behavior and not shared storage/export logic.

## Phase 9: Migrate the demonstrated suppliers

### Constellation Energy

- [ x ] Capture and fixture Constellation offer responses for every supported EDC/GDC.
- [ x ] Replace DOM-first rate parsing with API/structured-data parsing when available. No separate offer API was exposed; the adapter uses semantic product IDs and sibling detail records from the rendered source.
- [ x ] Match each Terms and Conditions/contract document reference to its product ID.
- [ - ] Verify all contract-summary sections and plan terms.

### Direct Energy

- [ x ] Capture and fixture Direct Energy offer responses for electric and gas territories.
- [ x ] Discover contract-document URLs without relying solely on modal presentation.
- [ x ] Investigate and document previously blank/unparseable contract PDFs.
- [ x ] Verify commodity separation and rate units.

### Ambit Energy

- [ x ] Capture and fixture the service-area and offer responses.
- [ - ] Replace popup-text extraction with structured response parsing where available.
- [ - ] Collect and match Contract Summary/Terms documents.
- [ x ] Verify rate structure rather than inferring it from the plan name alone.

### Think Energy

- [ x ] Capture and fixture offer API responses rather than styled-component font-size attributes.
- [ - ] Parse generated DOCX/PDF contract content using the shared document pipeline.
- [ x ] Match exposed contract parameters and rate IDs to the plan; document downloads remain access-blocked.
- [ x ] Verify renewable percentage and source claims.

### NRG

- [ x ] Capture the network calls made by the commodity/utility modal flow.
- [ x ] Identify why the existing flow returns zero plans.
- [ x ] Implement the API or corrected browser adapter.
- [ x ] Add regression fixtures for the prior zero-plan failure and every assigned NRG territory.
- [ x ] Verify More Info contract-summary discovery.

### Major Energy

- [ x ] Capture and fixture offer responses and product IDs.
- [ x ] Normalize dollar-per-unit values without unnecessary precision changes.
- [ - ] Collect and match all Terms of Service documents.
- [ - ] Verify fees, incentives, and renewal terms beyond the first-page rate.

### Xoom Energy

- [ x ] Capture and fixture electric and gas utility-choice responses.
- [ x ] Fix the test/schema mismatch between `rate_cents` and `rate`.
- [ x ] Parse plan type and renewable attributes into separate fields.
- [ x ] Deduplicate repeated cards and shared contract documents.

### Phase 9 completion gate

- [ x ] Run all seven suppliers across every NJBPU-supported territory assigned to their adapters in the registry.
- [ x ] Require valid artifacts, explicit zero/unsupported dispositions, fixtures, and coverage results for every automated combination.

## Phase 10: Expand remaining suppliers by platform cluster

- [ x ] Rank the next EDC suppliers by territory breadth and public accessibility. The September 11 baseline selected Smart Energy, Clearview, IDT, CleanSky, Green Mountain, and Great American; gas mappings remain deliberately untouched.
- [ x ] Investigate Frontier Utilities and assign a platform or supplier adapter. Current ZIP flow redirects to the Frontier enrollment portal, which returned HTTP 503 during the bounded September 11 check; adapter reports this rather than treating it as zero plans.
- [ x ] Repair CleanChoice Energy using its direct ZIP plan route; capture three plans in each configured EDC and document the current requirement to run this supplier with `--headed`.
- [ x ] Investigate Smart Energy and assign an electric-only adapter. Public ZIP/utility form endpoints now lead to scoped plan HTML; one current offer was captured in each of JCP&L, ACE, and Rockland.
- [ x ] Extend Clearview Energy to gas and repair its changed responsive ZIP form; product attributes now scope NJNG and SJG gas offers as well as its electric offers.
- [ x ] Replace CleanSky's generic blocked disposition with its real cookie/ZIP/dual-utility modal flow; capture Rockland electric and all configured PSE&G, SJG, and ETG gas markets.
- [ x ] Extend IDT Energy's public two-stage form and utility-scoped rate-table parser to PSE&G and NJNG gas.
- [ x ] Repair NJG&E's two-stage ZIP and utility-confirmation flow; capture two gas plans for both NJNG and SJG.
- [ x ] Investigate Residents Energy and assign a gas adapter; its current fixed-rate comparison table yields two offers for each of PSE&G, NJNG, and SJG.
- [ x ] Repair NextEra's legacy key-event and utility-selection flow; capture two ACE plans with `data-rate` product identities.
- [ x ] Investigate Green Mountain Energy and assign an electric-only adapter. The public React flow completes, but the configured Rockland ZIP redirects to an explicit not-served result.
- [ x ] Investigate Eligo Energy and assign an NJNG gas adapter; its official utility route currently yields three fixed-rate offers.
- [ x ] Investigate Great American Gas & Electric and assign an electric-only adapter. Its public comparison form accepts the PSE&G context but explicitly reports no current products for the configured ZIP.
- [ x ] Investigate Alpha Gas & Electric without entering protected enrollment information. The adapter now reads the official public NJ pricing page and rate-sheet PDF; the current ACE sheet is dated 2025-01-15.
- [ x ] Investigate American Power & Gas without entering a real customer address. The adapter now derives and cross-checks one residential unit rate from the official public NJ comparison table; ETG remains explicitly unsupported because it is absent from that table.
- [ ] Add newly reconciled NJBPU suppliers not present in the current registry.
- [ - ] Add fixtures and tests before enabling each new adapter in scheduled runs; deterministic Alpha and American Power & Gas parser tests were added on September 18, but captured live fixtures are still needed.

### Phase 10 completion gate

- [ x ] Give every active in-scope supplier/territory combination an automated, skipped, blocked, or manual-review result with a reason. No registry row uses `default` or `skip` after the September 18 pass.
- [ x ] Confirm that no supplier is silently omitted from coverage reporting. The September 11 all-functions run emitted a row for all 76 registry combinations across 21 TPS suppliers, including failed, blocked, empty, and unsupported outcomes.

## Phase 11: Validation, QA, and regression suite

- [ - ] Add unit tests for ZIP, alias, rate, unit, fee, percentage, and date normalization.
- [ x ] Add unit tests for every standardized contract section.
- [ - ] Add unit tests for deduplication and change classification.
- [ x ] Add unit tests for plan/document matching.
- [ - ] Convert useful saved debug pages into redacted regression fixtures.
- [ ] Remove hard-coded user-specific absolute paths from automated tests.
- [ x ] Separate interactive diagnostic scripts from the default test suite.
- [ - ] Add opt-in live smoke tests for one territory per platform.
- [ - ] Ensure live tests assert structure rather than fixed rates or plan counts.
- [ - ] Add zero-plan regression detection.
- [ - ] Add contract-completeness thresholds.
- [ ] Add unusual rate-change and plan-count-change alerts.
- [ - ] Add duplicate and conflicting-contract validation.
- [ ] Add database migration tests.
- [ - ] Add exporter snapshot tests.
- [ ] Configure linting, formatting, and type checking.
- [ ] Run all offline tests in continuous integration.

### Phase 11 completion gate

- [ ] Confirm that every production adapter has an offline deterministic regression test.
- [ ] Confirm that known source changes fail loudly rather than silently producing empty or partial exports.

## Phase 12: Historical data migration and reporting

- [ ] Profile every existing CSV column and value convention.
- [ ] Map legacy columns to canonical fields without inventing missing values.
- [ ] Preserve legacy source URLs and source-type labels.
- [ ] Import legacy data into a separate staging schema.
- [ ] Validate rate units and suspicious values before promoting legacy snapshots.
- [ ] Reconcile duplicate plans across legacy and first-party sources without merging provenance.
- [ ] Create a current electric-offers view.
- [ ] Create a current gas-offers view.
- [ ] Create a full plan-history view.
- [ ] Create a contract-summary view.
- [ ] Create incentive and renewable-attribute views.
- [ - ] Create coverage and field-completeness reports.
- [ ] Create material rate, fee, term, incentive, renewable, and document change reports.
- [ - ] Add `captured_at`, stable IDs, source type, source URL, and artifact ID to all exports.
- [ - ] Document all derived fields and conversions in a data dictionary.

### Phase 12 completion gate

- [ ] Reproduce every published CSV from database queries and versioned exporter code.
- [ ] Trace a sample of historical and current records back to their original sources.

## Phase 13: Scheduling and operations

- [ ] Define an initial weekly full-collection schedule.
- [ ] Define optional targeted daily checks for high-change suppliers only if justified.
- [ - ] Add commands for full, supplier, utility, commodity, and discovery-only runs.
- [ ] Add safe resume behavior for interrupted runs.
- [ ] Add transient retry and permanent-failure policies.
- [ x ] Generate a concise run summary after every collection.
- [ ] Generate alerts for zero plans, stale success dates, parser failures, schema changes, and material offer changes.
- [ ] Define artifact and log retention policies.
- [ ] Add database and artifact-index backups.
- [ ] Add a manual-review queue with owner, reason, evidence, and resolution status.
- [ ] Document how to pause a broken adapter without hiding the affected coverage gap.
- [ - ] Write operating, troubleshooting, and recovery documentation.
- [ ] Review robots directives, source terms, and request rates before enabling each scheduled adapter.

### Phase 13 completion gate

- [ ] Complete at least two scheduled full runs with reproducible outputs and no silent failures.
- [ ] Demonstrate detection of an intentional fixture/schema change and successful operator diagnosis.

## Phase 14: Legacy scraper retirement

- [ ] Compare new-pipeline results with the old scraper for all seven demonstrated suppliers.
- [ ] Resolve unexplained rate, plan-count, utility, term, and document differences.
- [ ] Verify that the new pipeline covers every retained old capability.
- [ - ] Update all documented commands to use the new entry point.
- [ ] Move obsolete interactive inspection scripts to an explicitly archived location or remove them after approval.
- [ ] Retain useful redacted debug artifacts as regression fixtures.
- [ x ] Stop the old scraper from writing production filenames.
- [ ] Archive the old implementation with a migration note and final version reference.

### Phase 14 completion gate

- [ ] Confirm that production collection, validation, reporting, and exports run exclusively through the new architecture.
- [ ] Confirm that archived code and legacy data remain recoverable.

## Production milestone

- [ ] Verify that every active NJBPU supplier/territory combination has an explicit, reported disposition.
- [ ] Verify that every automated adapter has offline fixtures and deterministic tests.
- [ ] Verify that offers reference immutable raw artifacts.
- [ ] Verify that contract summaries are related to plans rather than emitted as duplicate plans.
- [ ] Verify that disclosed fees, incentives, renewable attributes, rate structures, terms, renewal conditions, and cancellation conditions are retained.
- [ ] Verify that current and historical electric/gas exports are reproducible.
- [ ] Verify that incompatible legacy datasets cannot be overwritten.
- [ ] Verify that coverage, completeness, staleness, and failure reports are available.
- [ ] Verify that installation, adapter development, operation, manual review, troubleshooting, and recovery are documented.
- [ ] Mark the initial production milestone complete only after all preceding verification items pass.

## Scoped first-pass milestone September 4 2026

This milestone is narrower than the production gates above. The user accepted a passable implementation with later iteration. See the modernization report and manual verification guide for evidence and limitations.

- [ x ] Route the seven existing supplier functions and generic fallback through shared collection and reporting.
- [ x ] Add historical observed fixtures for seven PSE&G electric suppliers and three gas cases.
- [ x ] Extract Direct Energy PDF form values and verify all twelve sections in the sampled electric summaries.
- [ x ] Correct Xoom month-to-month versus eligibility-period parsing and retain introductory billing-cycle duration separately.
- [ x ] Provide offline tests, replay, integrity checks, setup instructions and manual live-check commands.
- [ x ] Document first-pass achievements, incomplete document access and unverified territory coverage.
- [ ] Resolve Ambit dynamic plan-document links and restricted/unresolved document-host permissions.
- [ x ] Verify every retained supplier across all applicable EDC/GDC combinations.
- [ ] Expand browser-flow regression tests and improve remaining contract interpretations.

## Assigned-adapter completion milestone September 11 2026

This milestone applies to the nine adapters and 47 supplier/utility combinations currently assigned in the master table. It does not mark the broader statewide production milestone complete.

- [ x ] Execute every assigned supplier/EDC/GDC combination and retain an explicit offer-bearing, empty, unsupported, or blocked disposition.
- [ x ] Add an offline fixture for all 47 assigned combinations; registry-to-fixture audit reports zero missing rows.
- [ x ] Expand NRG, Direct Energy, Xoom Energy, Major Energy, Ambit Energy, Think Energy, and Constellation Energy across every territory assigned to their adapters.
- [ x ] Add explicit Frontier Utilities and CleanChoice Energy adapters that report current external blockages without claiming empty markets.
- [ x ] Preserve blocked document-host and incomplete-contract limitations in coverage results and the modernization report.
- [ x ] Pass the complete 98-test offline suite after the final navigation, status, parser, and fixture changes.
- [ x ] Verify the final Direct Energy redirect recovery live: three PSE&G Gas offers, verified context, zero errors, and valid artifact hashes.
- [ x ] Synchronize the modernization report and TODO with the final assigned-adapter results and remaining big-picture gaps.
- [ x ] Add a single TPS-sorted purchasing CSV with one physical line per verified plan and essential comparison fields; keep contract, coverage, diagnostic, and zero-offer detail out of this reader-facing file.
- [ x ] Split reader-facing exports into offer prices, contract information, offer-document relationships, and coverage tables while preserving the technical JSON/CSV outputs.
- [ x ] Add a verified consolidation command so successful focused retries can replace failed rows and rebuild one aggregate report without losing hashed evidence.
- [ x ] Add targeted multi-ZIP sampling for uncertain empty/unsupported markets without multiplying every registry row.
- [ x ] Separate canonical offers from ZIP-level observations using stable purchasing fingerprints, duplicate status, ZIP counts, and same-rate distinct-offer flags.
- [ x ] Add structured remediation type, retryability, and next action fields to coverage output for blocked, unsupported, and empty suppliers.
- [ x ] Treat ordinary 4xx `robots.txt` responses as unavailable under RFC 9309 while retaining explicit Disallow rules, 429 handling, page-level blocks, and request throttling.
- [ x ] Add CleanChoice, NextEra, CleanSky, and NJG&E rendered-card parser tests and complete the 131-test regression suite.
- [ x ] Add the user-confirmed CleanSky PSE&G-gas ZIP `07430` as a targeted observation and consolidate equivalent products across ZIPs rather than duplicating canonical offers.
- [ ] Add an automatic isolated headed-browser retry for suppliers such as CleanChoice that reject the bundled headless browser; until then use the documented `--headed` run.
