# NJ Power Switch Data Pipeline Implementation Plan

## First-pass update September 4 2026

The approved existing-supplier modernization is delivered as a passable first iteration, not completion of this entire plan. See `SCRAPER_MODERNIZATION_REPORT.md` for each scraper's changes, evidence and limitations, and `MANUAL_VERIFICATION.md` for commands. The TODO uses its own 0–14 phase numbering; statuses are updated at item level.

Foundations now include the `nj_switch` package, validated records, hashed run evidence, shared offer/document parsing, PDF form-field extraction, structured Direct Energy/Think/NRG profiles, browser fallbacks, protected legacy outputs and regression tests. Ten observed fixtures cover seven PSE&G electric cases and three gas cases—not all-territory certification.

Scoped deviations: nested interchange records and per-run JSON/CSV replace database work for this milestone. No migrations, historical import, scheduling, OCR installation or additional suppliers were introduced. Screenshots/traces remain disabled in favor of sanitized HTML and selected JSON. Some document downloads are restricted; missing fields stay explicit. The architecture below remains the roadmap, not a statement of present capabilities.

## 1. Purpose

This document defines the implementation plan for a maintainable New Jersey third-party energy supplier data pipeline. The pipeline will collect current residential electricity and natural-gas offers for suppliers serving New Jersey's four electric distribution companies (EDCs) and four gas distribution companies (GDCs), extract the standardized Third Party Supplier (TPS) Contract Summary, preserve source evidence, and maintain a history of rate and contract changes.

The project will retain Playwright, but browser automation will be a fallback and session-bootstrap mechanism rather than the primary parser. The preferred collection order is:

1. Direct documented or discoverable JSON/API response.
2. Static HTML or embedded structured data.
3. Playwright-assisted navigation and network capture.
4. Rendered DOM extraction when no structured source exists.
5. Manual review when a flow requires protected personal information, authentication, CAPTCHA resolution, or another disallowed action.

The system must not bypass access controls, CAPTCHAs, authentication, or supplier terms. It must use conservative request rates and preserve the provenance of every collected fact.

## 2. Goals

- Cover all active, relevant TPS/EDC/GDC combinations listed by the New Jersey Board of Public Utilities (NJBPU).
- Collect all publicly available residential offers for representative ZIP codes in each service territory.
- Extract offer attributes such as rate, unit, rate structure, term, monthly fees, enrollment fees, cancellation fees, introductory rates, incentives, renewable content, and sign-up links.
- Extract every applicable section of the NJBPU standardized TPS Contract Summary.
- Match each contract document to the correct offer rather than storing it as an unrelated duplicate plan row.
- Preserve raw JSON, HTML, PDF, DOCX, screenshots, response metadata, and hashes as auditable source evidence.
- Maintain time-series snapshots so monthly and intra-month rate changes can be analyzed.
- Detect source breakage and material offer changes automatically.
- Make supplier-specific code small, isolated, testable, and reusable across suppliers sharing the same enrollment platform.
- Produce stable database views and CSV exports for downstream analysis.

## 3. Non-goals

- Completing supplier enrollment or creating customer accounts.
- Entering real customer account numbers, personal data, payment details, or protected addresses.
- Circumventing CAPTCHAs, bot protections, access controls, or rate limits.
- Guaranteeing that a single generic selector can navigate every supplier site.
- Treating an LLM or browser agent as the unattended source of truth.
- Replacing NJBPU as the authoritative source for supplier licensing and service territory eligibility.

## 4. Current-State Findings

The existing implementation provides a valuable proof of concept, but it has structural limitations that the new design must resolve:

- `src/scraper/nj_scraper.py` combines orchestration, browser workflows, parsing, document handling, logging, and export in one large module.
- The scraper emits a small offer schema rather than the full TPS Contract Summary schema.
- PDF parsing scans document-wide text for rates and terms instead of associating standardized labels with their values.
- HTML offer rows and PDF-derived rows are appended as separate records instead of being merged into one plan and contract relationship.
- The master supplier CSV contains 76 supplier/utility combinations, while the demonstrated run covers only one utility and seven suppliers.
- Many combinations use a generic DOM fallback that can miss dynamic offers or extract unrelated rates.
- A new Chromium process is launched for every supplier/utility row.
- Current output filenames can overwrite older files that use a different 36-column schema and different provenance.
- Representative New Jersey ZIP codes have lost leading zeroes in the current registry.
- Tests are primarily interactive inspection scripts rather than automated fixture-based tests.
- The scraper README is empty and dependencies are not locked.

These findings make schema definition, provenance, raw evidence, and testable adapters higher priorities than adding more selectors to the current monolith.

## 5. Source-of-Truth Policy

Each class of data must have an explicit preferred source:

| Data class | Preferred source | Fallback source |
|---|---|---|
| Supplier license and active status | NJBPU active license list | Manual NJBPU verification |
| EDC/GDC service eligibility | NJBPU suppliers-by-area pages | Supplier public service-area response |
| Current offer/rate | Supplier JSON/API response | Supplier rendered offer page |
| Contract terms | Supplier TPS Contract Summary | Terms of Service when summary is unavailable |
| Renewable percentage/source | Offer API, offer page, environmental disclosure | Contract document or supplier program page |
| EDC/GDC contact information | Utility's official website | NJBPU page |
| Historical rate | Previously captured first-party snapshot | Clearly labeled third-party reference data |

Third-party aggregator data must never be silently mixed with first-party supplier data. Every observation must include `source_type`, `source_url`, `captured_at`, and a raw artifact reference.

## 6. Target Architecture

```text
NJBPU registry collector
          |
          v
Supplier + territory configuration
          |
          v
Collection router
  API/HTTP -> static HTML -> Playwright/network -> DOM -> manual review
          |
          v
Immutable raw artifact store
  JSON | HTML | PDF | DOCX | screenshot | response metadata
          |
          v
Shared extractors
  offer extractor | contract-label extractor | OCR fallback
          |
          v
Normalizer and validator
          |
          v
Plan/document matcher and deduplicator
          |
          v
SQLite/DuckDB historical store
          |
          v
CSV views, QA reports, and change alerts
```

### 6.1 Recommended project layout

```text
nj-switch-pipeline/
  config/
    suppliers.yaml
    utilities.yaml
    field_aliases.yaml
  data/
    raw/
    processed/
    exports/
    fixtures/
  docs/
  TODO/
  src/nj_switch/
    cli.py
    settings.py
    models/
      supplier.py
      offer.py
      contract.py
      artifact.py
    registry/
      njbpu.py
      reconcile.py
    collectors/
      base.py
      http.py
      playwright.py
      documents.py
    adapters/
      base.py
      platforms/
      suppliers/
    extractors/
      offers.py
      contract_labels.py
      pdf.py
      docx.py
      ocr.py
    pipeline/
      normalize.py
      match.py
      validate.py
      deduplicate.py
    storage/
      database.py
      artifacts.py
      migrations/
    reporting/
      coverage.py
      changes.py
      exports.py
  tests/
    unit/
    integration/
    fixtures/
```

Existing code should remain available during migration. New modules should be introduced beside it, verified, and only then used to replace the current entry point.

## 7. Canonical Data Model

The initial implementation can use SQLite for portability. DuckDB may be used for analysis and CSV/Parquet queries, but one database must be designated as the transactional system of record.

### 7.1 `suppliers`

- `supplier_id`: stable internal identifier.
- `legal_name` and `display_name`.
- `bpu_license_number`.
- `license_status`, `license_effective_date`, and `license_anniversary_date`.
- `phone`, `email`, `website`, and New Jersey mailing address.
- `registry_source_url`, `registry_captured_at`, and `registry_artifact_id`.

### 7.2 `utilities`

- `utility_id` and canonical abbreviation.
- `name`.
- `utility_type`: `EDC` or `GDC`.
- `commodity`: `electric` or `gas`.
- Emergency phone, customer-service phone, and website.

Canonical utilities are ACE, JCP&L, PSE&G Electric, Rockland Electric, ETG, NJNG, PSE&G Gas, and SJG.

### 7.3 `service_territories`

- Supplier and utility foreign keys.
- Commodity.
- Active status and effective dates.
- Representative ZIP code stored as exactly five characters.
- Source and capture metadata.

### 7.4 `plans`

This table identifies a logical supplier product over time:

- `plan_id`.
- Supplier, utility, commodity, and service class.
- Supplier/platform product ID when available.
- Canonical and raw plan names.
- Enrollment URL.
- First and last observation timestamps.
- Active/inactive status.

### 7.5 `plan_snapshots`

This table stores the observed terms of a plan at a point in time:

- `snapshot_id`, `plan_id`, `captured_at`, and `effective_date` when disclosed.
- `rate_value`, `rate_unit`, `currency`, and `rate_structure`.
- Introductory rate and duration.
- Contract term and exact end date.
- Monthly fee, enrollment fee, early-termination fee, and other recurring/nonrecurring charges.
- Tier thresholds and tier rates.
- Unlimited-rate and net-metering indicators where applicable.
- Incentive summary and structured incentive relationship.
- Renewable indicator, renewable percentage, renewable source, and certification.
- Tax/rider inclusion indicators.
- Raw source fields and artifact reference.
- Validation status and confidence based on deterministic evidence quality.

Rates must use one canonical unit per commodity for comparison, while preserving the exact raw unit and value. Electricity rates should be normalized to dollars per kWh or cents per kWh consistently; gas rates should preserve whether the source uses therm, CCF, Dth, or another unit and convert only with an explicit supported rule.

### 7.6 `contract_summaries`

The schema must represent all NJBPU standardized sections:

- Supplier information and responsibility statement.
- Price structure, fixed period, variable-rate range/ceiling, index, Price-to-Compare relationship, and rate-change method.
- Generation/supply price and introductory price period.
- Savings statement and reference price methodology.
- Estimated switching time back to default service or another TPS.
- Incentives and associated terms.
- Seven-day cancellation/rescission disclosure.
- Expected contract start timing.
- Contract term/length and exact end date if present.
- Cancellation/early-termination applicability, amount, calculation, and avoidance conditions.
- Renewal options, notice, affirmative-consent requirements, and post-term behavior.
- Distribution-company name, phones, website, delivery statement, billing statement, and emergency instructions.
- Full raw text for every section.
- Document URL, artifact ID, document hash, capture time, parser version, and review status.

Unknown and not-applicable values must be distinct. An absent extraction must not be converted to zero or `False`.

### 7.7 `incentives`

- Incentive type: discount, cashback, gift card, loyalty reward, appliance/service, donation, or other.
- Amount/value and unit.
- Eligibility, redemption, vesting, expiration, and clawback terms.
- Raw text and artifact reference.

### 7.8 `source_artifacts`

- `artifact_id`, capture timestamp, run ID, supplier, utility, and commodity.
- Original and final URLs, HTTP status, content type, and response headers safe to retain.
- SHA-256 content hash.
- Relative storage path and byte size.
- Artifact type: JSON, HTML, PDF, DOCX, image, trace, or metadata.
- Parent artifact or request relationship.
- Parser version and parse status.

Secrets, session tokens, cookies, authorization headers, and personal data must not be retained in artifacts.

### 7.9 `collection_runs` and `collection_results`

Each run records configuration, software version, start/end time, and overall status. Each supplier/territory result records attempt count, collection path used, plans found, required fields found, artifact IDs, warnings, error category, and next retry time.

## 8. Supplier and Platform Adapter Design

An adapter should describe only what differs between sites. Shared code owns collection lifecycle, artifacts, parsing, validation, retries, and output.

### 8.1 Adapter interface

Each adapter must provide:

- A stable adapter/platform name and version.
- Supported suppliers and territories.
- Entry URL construction.
- Required public inputs such as ZIP, commodity, and utility.
- API discovery or known endpoint rules.
- Browser navigation only when necessary.
- Offer response identification and parsing hooks.
- Contract-document discovery rules.
- A health check and deterministic fixture tests.

### 8.2 Configuration versus code

Use YAML for labels, URLs, aliases, utility mappings, and stable selector alternatives. Use Python only for conditional workflows, response signing, unusual state transitions, or supplier-specific normalization that cannot be described safely in configuration.

Selector preference order:

1. Accessible role and name.
2. Associated form label.
3. Stable semantic attribute such as `name`, `data-testid`, or supplier product ID.
4. URL and API-response pattern.
5. CSS structure as a last resort.

### 8.3 Platform clustering

During discovery, record network hostnames, endpoint paths, response keys, document hostnames, and enrollment-page fingerprints. Group suppliers sharing an enrollment vendor into one platform adapter with supplier-specific configuration. This is the main mechanism for reducing repeated implementation work.

## 9. Collection Strategy

### 9.1 Registry collection

- Collect the NJBPU licensed supplier list and suppliers-by-area data.
- Save the raw source and normalized result.
- Reconcile additions, removals, aliases, and license-status changes against the local registry.
- Require review before deleting a previously active supplier/territory relationship.

### 9.2 API-first offer collection

- Attach Playwright response listeners before navigation.
- Classify JSON responses by URL, content type, and payload keys.
- Save candidate responses after redacting secrets.
- Identify which request is triggered by ZIP, utility, or commodity selection.
- When permitted and stable, replay that request with the browser context's request client or `httpx`.
- Parse from JSON into the canonical schema.
- Fall back to HTML/DOM only when the structured response is unavailable.

### 9.3 Browser lifecycle

- Launch one browser per collection run.
- Use isolated browser contexts per supplier or platform.
- Reuse a context across that supplier's EDC/GDC combinations when safe.
- Block nonessential image, font, and media resources when this does not alter application behavior.
- Use event- or locator-based waits rather than arbitrary sleeps.
- Capture a trace, screenshot, and final HTML on failures.
- Close contexts deterministically and continue other suppliers after an isolated failure.

### 9.4 Document collection

- Discover contract documents from API payloads, anchor links, modal contents, and download events.
- Support PDF, DOCX, and HTML documents.
- Resolve relative URLs and content-disposition downloads.
- Store documents once by content hash and relate them to every applicable plan.
- Never assume that a URL extension describes the actual content type.

## 10. Extraction and Normalization

### 10.1 Offer extraction

Shared extractors should use a field-alias registry for names such as `rate`, `commodityRate`, `supplyPrice`, `monthlyCharge`, `recurringFee`, `renewablePercent`, and `greenContent`. Supplier adapters map unusual fields into canonical values.

### 10.2 Contract-summary extraction

The primary parser should identify standardized section labels, then associate each label with an adjoining table cell, text block, or layout region. It should preserve raw section text before deriving structured values.

Parsing order:

1. Native PDF table extraction.
2. Native PDF layout/text association.
3. DOCX table and paragraph extraction.
4. HTML table/definition-list extraction.
5. OCR for image-only documents.
6. Manual review when required sections remain ambiguous.

An optional local or hosted language model may propose field mappings only as a reviewable fallback. It must return schema-constrained output, cite the source text used for each field, and never overwrite deterministic extraction silently.

### 10.3 Plan-to-contract matching

Preferred matching keys are supplier product ID, contract URL embedded in the offer response, rate ID, plan ID, plan name plus term, and finally rate plus term plus utility. Ambiguous matches must be flagged rather than guessed.

### 10.4 Deduplication

Use stable hashes based on supplier, utility, commodity, platform product ID, normalized plan name, term, and source document. A new snapshot should be stored when a material term changes even if the plan name remains unchanged.

## 11. Validation Rules

### 11.1 Record-level validation

- ZIP is exactly five digits.
- Supplier, utility, commodity, capture time, and source artifact are present.
- Rate is positive and within configurable commodity-specific bounds.
- Rate unit is explicit.
- Fixed plans have a term or an explicit reason the term is unavailable.
- Monthly, enrollment, and cancellation fees are not inferred as zero from missing data.
- Renewable percentage is between 0 and 100 when present.
- Contract commodity matches the plan commodity.
- Contract utility and supplier match the associated plan when disclosed.

### 11.2 Run-level validation

- A supplier/territory that previously returned plans and now returns zero is a failure requiring review.
- Large plan-count changes are flagged.
- Large rate changes are flagged but retained pending review.
- Missing standardized contract sections produce a completeness warning.
- Duplicate plans and one contract assigned to conflicting products are flagged.
- No export is published if schema validation fails globally.

### 11.3 Coverage metrics

Reports must show:

- Active NJBPU supplier/territory combinations.
- Attempted, successful, empty, blocked, skipped, and failed combinations.
- Offers with matched contract summaries.
- Field completeness by supplier and field.
- API versus HTML versus DOM collection percentage.
- Days since each supplier/territory last succeeded.
- Documents requiring manual review.

## 12. Storage, History, and Exports

- Never overwrite raw artifacts.
- Partition raw artifacts by capture date, run ID, supplier, and utility.
- Use content hashes to avoid retaining identical documents repeatedly.
- Store capture timestamps in UTC and display local time only at presentation boundaries.
- Keep database migrations under source control.
- Export current electric offers, current gas offers, full history, contract summaries, incentives, renewable attributes, and coverage reports separately.
- Include stable IDs and provenance fields in every export.
- Treat the existing March CSVs as a separately labeled legacy dataset until their provenance and field semantics are verified.

## 13. Testing Strategy

### 13.1 Unit tests

- Rate and unit normalization.
- ZIP normalization.
- Utility and supplier alias resolution.
- Fee and percentage parsing.
- Contract label/value extraction.
- Plan/document matching.
- Deduplication and change classification.

### 13.2 Fixture tests

For every adapter, retain redacted representative JSON, HTML, and document fixtures. Tests must run offline and assert exact canonical records. Fixture provenance and capture date should be documented.

### 13.3 Integration tests

- Run a small opt-in live smoke test against one representative territory per platform.
- Keep live tests separate from the default test suite.
- Validate artifact redaction and database writes.
- Do not make plan counts or live rates fixed test expectations; assert structural validity instead.

### 13.4 Regression tests

Every production failure caused by a source change should add or update a saved fixture before the adapter fix is considered complete.

## 14. Operations and Scheduling

- Run the full collector on a defined schedule, initially weekly while stabilizing.
- Increase to daily only if source policies, run time, and rate-change needs justify it.
- Retry transient network and server errors with exponential backoff and jitter.
- Do not retry permanent validation failures indefinitely.
- Assign machine-readable failure categories: network, blocked, navigation, response-shape, document-download, document-parse, validation, and manual-review.
- Produce a run summary and a material-change report after each scheduled run.
- Back up the database and artifact index before retention or migration operations.

## 15. Security, Privacy, and Responsible Collection

- Review robots directives and terms for every source.
- Use a descriptive user agent when practical.
- Rate-limit per domain and avoid concurrent bursts.
- Never store cookies, authentication tokens, customer account data, addresses, or payment information.
- Redact sensitive request headers and query parameters from logs and artifacts.
- Do not automate combinations marked as requiring protected customer information.
- Record why a supplier was placed in manual-review status.

## 16. Migration Plan

### Phase 0: Baseline and safeguards

Inventory existing code and data, preserve current outputs, document provenance, fix ZIP representation, add dependency locking, and establish a non-overwriting directory structure.

### Phase 1: Canonical models and storage

Implement Pydantic/domain models, SQLite schema, migrations, artifact storage, run tracking, validation, and deterministic exports before adding new scraping behavior.

### Phase 2: Registry reconciliation

Implement NJBPU supplier/license/territory ingestion and compare it with the current 76-row registry. Resolve aliases and representative ZIPs.

### Phase 3: Shared collection runtime

Implement the collection router, one-browser lifecycle, response capture, redaction, retries, artifacts, and structured result statuses.

### Phase 4: Contract extraction

Implement standardized label-based PDF/DOCX/HTML extraction, OCR fallback, completeness scoring, and plan/document matching.

### Phase 5: Platform and supplier adapters

Migrate the seven demonstrated suppliers first. For each, discover APIs, create fixtures, implement the smallest adapter, and verify all supported territories. Then process remaining suppliers by platform cluster and priority.

### Phase 6: Historical migration and reporting

Import legacy CSVs into explicitly labeled source datasets, add snapshot/change reports, and publish stable current/history exports.

### Phase 7: Scheduling and stabilization

Add scheduled execution, failure alerts, coverage dashboards, operating documentation, and a defined manual-review process.

## 17. Priority Order

1. Protect existing data and resolve schema/provenance conflicts.
2. Fix ZIPs and establish the authoritative registry.
3. Implement canonical models, database, artifacts, and validation.
4. Build shared contract-summary extraction.
5. Add network-response discovery and API replay.
6. Migrate successful supplier strategies into adapters.
7. Restore failed suppliers, starting with previously zero-plan sources.
8. Expand through remaining supplier/platform clusters.
9. Add history, reports, scheduling, and alerts.

## 18. Definition of Done

The initial production milestone is complete when:

- Every active NJBPU residential supplier/territory combination has an explicit status and adapter/manual-review disposition.
- Every automated combination has at least one offline fixture and a deterministic test.
- Previously successful combinations returning zero plans are treated as failures.
- All collected offers use the canonical schema and reference immutable source artifacts.
- Contract summaries are stored as structured sections and related to plans without duplicate pseudo-plan rows.
- Fees, incentives, renewable attributes, rate structure, term, renewal, and cancellation terms are preserved when publicly disclosed.
- Current and historical electric/gas exports are reproducible from the database.
- No export overwrites an incompatible legacy dataset.
- A coverage report identifies missing fields, failures, and manual-review items.
- The project has installation, operation, troubleshooting, and adapter-development documentation.

## 19. Recommended Free/Open-Source Stack

- Python 3.12 or later, subject to dependency compatibility.
- Playwright for dynamic interaction and response capture.
- `httpx` for direct HTTP/API collection.
- BeautifulSoup or Parsel for static HTML parsing.
- Pydantic for canonical models and validation.
- `pdfplumber`, `pypdf`, and Camelot for PDFs.
- `python-docx` for DOCX documents.
- Tesseract/OCRmyPDF for scanned contracts.
- SQLite for the portable operational store.
- DuckDB and Parquet for analysis if needed.
- pytest for tests.
- Ruff and a type checker for code quality.
- Optional Crawlee for Python if its routing, concurrency, and storage features reduce custom orchestration after the core schema and adapters are proven.

## 20. References

- [NJBPU Third Party Supplier licensing information](https://nj.gov/bpu/about/divisions/energy/thirdparty.html)
- [NJBPU licensed suppliers by EDC/GDC](https://nj.gov/njpowerswitch/suppliers/)
- [NJBPU TPS Contract Summary standardized format](https://nj.gov/bpu/pdf/boardorders/2014/20140930/9-30-14-7F.pdf)
- [Playwright network documentation](https://playwright.dev/python/docs/network)
- [Scrapy spider documentation](https://docs.scrapy.org/en/master/topics/spiders.html)
- [Crawlee Adaptive Playwright crawler](https://crawlee.dev/python/docs/guides/adaptive-playwright-crawler)
