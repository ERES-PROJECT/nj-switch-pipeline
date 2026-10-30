# Energy Data Collection and Integration — Project Work Summary

- **Scope:** Pennsylvania and New Jersey retail energy offers, supporting contract information, utility comparison prices, and PJM wholesale electricity data.
- **Status date:** October 30, 2026

## Project objective and approach

The project has progressed from collecting state energy-shopping data into a research pipeline that can compare **residential offers**, **utility basic generation services**, and eventually **retail prices against wholesale conditions**. The sources differ substantially: Pennsylvania provides centralized Power Switch/Gas Switch data, New Jersey directs customers to independently designed supplier sites, and PJM publishes high-volume wholesale time series.

The resulting approach is a staged information lifecycle:

```text
Discover sources → Collect raw evidence → Verify market context → Parse and normalize
→ Match and deduplicate → Validate coverage and quality → Export/load → Monitor changes
```

Rather than relying on one universal scraper, the project uses the simplest reliable method for each source while producing consistent downstream records.

## Procedures, algorithms, and tools used

| Area | Procedure or technique | Implementation and purpose |
|---|---|---|
| Source discovery | Reproduce the customer journey, then inspect page and network activity | Establishes ZIP, utility, commodity, customer class, product identifiers, and document links before automation. |
| Direct collection | Public APIs, JSON, rate tables, and downloadable files | Preferred when structured data is exposed; `HTTPX` supports bounded public requests. |
| Interactive collection | Supplier-specific browser adapters | `Playwright` and controlled Chrome sessions handle JavaScript, ZIP/utility selection, modals, and plan cards. |
| Document collection | Public contract summaries and disclosures | `PDFPlumber`, PDF forms, `python-docx`, and HTML parsing recover terms not shown on shopping pages. |
| Parsing and normalization | Offer card-level parsing with explicit units | `Beautiful Soup`/`lxml` and validated `Pydantic` models keep plan facts together; missing facts remain null, not zero. |
| Market validation | ZIP + utility + commodity confirmation | Prevents a plausible price from being accepted for the wrong territory or fuel. Each attempt is classified as successful, empty, unsupported, blocked, partial, failed, or review-required. |
| Offer identity | Product IDs plus a normalized purchasing fingerprint | Consolidates the same plan found across ZIPs while retaining genuinely different products that happen to share a rate. ZIP and collection time do not define the offer itself. |
| Evidence and quality | Run directories, hashes, timestamps, warnings, and reconciliations | Preserves each extraction's basis, isolates failures, and supports replay without rewriting history. |
| Regression testing | Saved public responses and offline parser tests | `pytest` verifies parsers and relationships without repeatedly contacting suppliers; separate live checks establish current prices. |
| Wholesale processing | Version-aware hourly aggregation | The PJM workflow collects real-time hourly zonal LMP data, keeps current records, resolves duplicate hour/zone versions, performs daylight-saving-aware coverage checks, and calculates monthly averages and medians. |
| Database loading | Staging, transformation, and ETL | The PA project already exports CSVs and contains a MySQL/SQLAlchemy ETL path. The NJ and PJM work now has validated interchange outputs, but the shared production database and migrations remain to be implemented. |

## What has been accomplished

### Retail offer collection

The Pennsylvania pipeline established the initial model: scrape Power Switch/Gas Switch, export plan and Price-to-Compare files, transform legacy fields, and load them through the existing ETL framework. It also exposed electric/gas version differences and fields requiring semantic cleanup.

For New Jersey, earlier scripts were modernized into a shared, evidence-first framework. Supplier navigation remains source-specific, but browser management, transport, parsing, validation, models, exports, and reporting are reusable. APIs, rendered pages, rate files, and contracts can feed the same validated output, while failures remain explicit.

The latest verified NJ aggregate (`20261019-complete-production-final`) completed **84 of 84 configured live markets**, producing **295 canonical offers**, **300 ZIP-level availability records**, and **465 contract/document records**. This represents the configured production matrix, not every licensed supplier statewide.

### Transformation and quality control

The transformation layer normalizes supplier/utility names, commodity context, units, rate structure, terms, fees, incentives, and renewable attributes. Offer identity is separate from ZIP availability, and documents are matched to offers rather than inferred from price alone. Reader-facing tables and quality views are backed by complete JSON interchange records.

A PA–NJ crosswalk was refined into a neutral schema rather than forcing NJ into legacy PA columns. Recommended shared tables are `suppliers`, `utilities`, `offers`, `offer_availability`, and `offer_documents`; uncommon state attributes remain in staging or controlled extensions. This avoids both permanent state-by-state databases and an uncontrolled all-purpose table.

### Wholesale market data

The PJM repository was consolidated into a canonical real-time workflow for `AECO`, `JCPL`, `PSEG`, and `RECO`. It now has resumable hourly collection, shared zone configuration, version deduplication, DST-aware checks, and dedicated NJ/all-zone monthly outputs. Legacy duplicate processors route to the canonical implementation, while day-ahead data remains separate.

The processing code is ready, but the checked-in time series is not fully current: the local 2026 raw data ends October 4, and complete 2025 PSEG/RECO data still requires an approved PJM Data Miner API key. Wholesale LMP is treated as market context—not as a direct substitute for a TPS retail rate.

## What needs to be done next

The next phase is not simply “add more scrapers.” It is to operationalize the validated collection methods as a maintainable research system:

1. **Implement the shared database.** Create migrations/loaders for canonical tables, retain PA/NJ staging and evidence, and store PJM and utility Price-to-Compare series separately from TPS offers.
2. **Complete consumer comparison inputs.** Regularly collect utility Price-to-Compare rates and, where feasible, delivery/customer charges for usage-based supply and total-bill comparisons.
3. **Move from snapshots to history.** Schedule collection, preserve effective dates, detect plan changes, and prevent duplicate inserts through canonical identity rules.
4. **Add monitoring and review.** Detect source changes, retry transient failures, alert on coverage or value anomalies, and route ambiguous records to a documented review queue.
5. **Finish wholesale refresh.** Configure the PJM key, refresh 2025–2026 hourly data, run strict checks, and load results with clear `$/MWh` versus `$/kWh` units.
6. **Validate multi-state scalability.** Map state-specific staging adapters into the common schema; promote only stable comparison fields and retain unusual or uncertain quirks as extensions/raw data.

## Sponsor takeaway

The project now has a tested path from heterogeneous public evidence to comparable records. The remaining step is operational maturity: a shared historical database, scheduled refreshes, monitoring, Price-to-Compare integration, and controlled expansion. This supports equitable comparison by evaluating realistic usage, fees and contract risk, separating supply from delivery, and exposing differences in market access or data quality across utility territories.
