# Proposed single-table NJ TPS dashboard schema

## Status

The schema was approved and applied to EEdb on October 30, 2026. The verified
`20261019-complete-production-final` run loaded 295 canonical offers, all from
collection queries marked successful, context-verified, and live-data-verified.
This document and its companion SQL file contain no database credentials.

## Recommended row grain

One row represents **one canonical offer in one verified collection run**:

```text
(collection_run_id, offer_fingerprint)
```

This grain is the safe basis for plan counts, supplier counts, rates, fees,
terms, and renewable metrics. The October 19 verified run demonstrates why the
grain must be explicit:

| Layer | Rows | Relationship |
|---|---:|---|
| Canonical offers | 295 | One target row each |
| ZIP observations | 300 | Up to 2 per canonical offer |
| Offer/document links | 407 | Up to 6 per canonical offer |
| Canonical contract rows | 465 | Many-to-many with offers |
| Coverage queries | 84 | One per supplier/utility/commodity/ZIP query |

A normal SQL join across those files would multiply rows and make counts and
averages incorrect. The proposed table therefore uses ordinary typed columns
for the canonical offer and lossless JSON arrays for one-to-many child rows.
Each JSON object retains the original CSV column names and values.

## Input-file roles

### Authoritative offer row

`offer_prices.csv` supplies the canonical offer and determines the target row.
`compiled_offerings.csv` is an exact compatibility copy and must not be loaded
again.

### Offer enrichments

- `offer_observations.csv`: ZIP-level sightings and provenance.
- `offers.csv`: technical offer fields not included in the reader-facing CSV.
- `offer_completeness.csv`: offer validation results.
- `document_associations.csv`: document-link completeness.

### Contract enrichments

- `offer_documents.csv`: many-to-many link between fingerprints and contracts.
- `contract_information.csv`: canonical reader-facing contract rows.
- `contracts.csv`: technical/raw contract fields.
- `contract_completeness.csv`: contract validation fields.

Only contracts linked through `offer_documents.csv` belong on an offer row.
Unlinked contracts remain in the immutable run files; forcing them onto an
unrelated offer would corrupt the data. If unlinked-contract reporting becomes
a dashboard requirement, the one-table/one-offer constraint should be revisited.

### Query and run quality enrichments

- `coverage.csv`
- `plan_count_reconciliation.csv`
- `completed_coverage.csv`
- `reproducibility.csv`
- `scraper_alerts.csv`

These files describe collection quality, not new offers. Their scalar fields
are repeated on the appropriate offer rows and their original rows are retained
in JSON.

## Join plan

1. Start with `offer_prices.csv`, keyed by `offer_fingerprint`.
2. Join `offer_observations.csv` by `offer_fingerprint`; aggregate all matching
   rows into `offer_observations_json`.
3. Join `offers.csv` through
   `offer_observations.offer_key = offers.key`; aggregate into
   `technical_offers_json`.
4. Join `offer_documents.csv` by `offer_fingerprint`; aggregate the link rows.
5. Join canonical contract rows using the composite identity
   `(tps, edc_gdc, commodity, contract_id)`. `contract_id` alone is not globally
   unique in the verified run.
6. Join technical `contracts.csv` using
   `(supplier, utility, commodity, zip, id)`.
7. Join offer quality files by `(market_key, zip, offer_key)`.
8. Join query quality files by `(market_key, zip)`.
9. Join `completed_coverage.csv` by `(utility, commodity)`.

Every one-to-many join must be aggregated before it is attached to the
canonical offer row.

## Complete CSV-to-table mapping

### `offer_prices.csv` and `compiled_offerings.csv`

`compiled_offerings.csv` is not independently loaded because it duplicates
`offer_prices.csv`.

| Source column | Target column |
|---|---|
| `tps` | `tps` |
| `edc_gdc` | `edc_gdc` |
| `commodity` | `commodity` |
| `test_zip` | `test_zip` |
| `observed_zip_codes` | parsed into `observed_zip_codes_json` |
| `offer_fingerprint` | `offer_fingerprint` |
| `plan_name` | `plan_name` |
| `rate` | `rate` |
| `rate_unit` | `rate_unit` |
| `plan_type` | `plan_type` |
| `term_months` | `term_months` |
| `monthly_fee` | `monthly_fee` |
| `enrollment_fee` | `enrollment_fee` |
| `cancellation_fee` | `cancellation_fee` |
| `intro_rate` | `intro_rate` |
| `intro_rate_unit` | `intro_rate_unit` |
| `intro_duration_months` | `intro_duration_months` |
| `intro_duration_billing_cycles` | `intro_duration_billing_cycles` |
| `renewable_percentage` | `renewable_percentage` |
| `renewable_details` | `renewable_details` |
| `deals_and_incentives` | `deals_and_incentives` |
| `document_count` | checked against `linked_document_count` |
| `source_urls` | parsed into `source_urls_json` |
| `captured_at` | contributes to `captured_first_utc` and `captured_last_utc` |

### `offer_observations.csv`

Every original row and column is stored in `offer_observations_json`. The
following fields also populate dashboard-friendly summaries:

| Source column(s) | Target |
|---|---|
| `offer_fingerprint` | join key |
| `offer_key` | `offer_keys_json` |
| `product_id` | `product_ids_json` |
| `test_zip` | `observation_zips_json` |
| `canonical_observation` | `canonical_observation_count` |
| `duplicate_status` | `observation_duplicate_statuses_json` |
| `source_url` | `source_urls_json` |
| `artifact_id` | `artifact_ids_json` |
| `captured_at` | first/last capture timestamps |
| `tps`, `edc_gdc`, `commodity`, `plan_name`, `rate`, `rate_unit`, `term_months` | validation against the canonical row |

### `offers.csv`

Every original row and column is stored in `technical_offers_json`.

| Source column(s) | Target |
|---|---|
| `key` | join through observation `offer_key` |
| `schema_version` | `schema_version` |
| `adapter_version` | `adapter_versions_json` |
| `replayed` | `replayed` |
| `collection_method` | `collection_method` |
| `context_verified` | `context_verified` |
| `live_data_verified` | `live_data_verified` |
| `product_id` | `product_ids_json` |
| `rate_structure` | `plan_type` |
| `term_kind` | `term_kind` |
| `fee_terms` | `fee_terms_json` |
| `renewable_source` | `renewable_source` |
| `renewable_claim` | `renewable_claim` |
| `incentives` | `incentives_json` |
| `contract_ids` | `contract_ids_json` |
| `source_kind` | `source_kind` |
| `status` | `offer_status` |
| `warnings` | `offer_warnings_json` |
| remaining identity, price, fee, ZIP, URL, artifact and capture columns | validation and the full JSON record |

### `offer_documents.csv`

All columns are retained in `offer_documents_json`.

| Source column(s) | Target |
|---|---|
| `offer_fingerprint` | join key |
| `contract_id` | `contract_ids_json` |
| `document_kind` | `document_kinds_json` |
| `parse_status` | `document_parse_statuses_json` |
| `match_method` | `document_match_methods_json` |
| `offer_key`, `source_offer_keys`, `product_id`, `contract_url` | full link JSON; identifiers/URLs also contribute to their aggregate columns |
| `tps`, `edc_gdc`, `commodity`, `test_zip`, `observed_zip_codes`, `observation_count`, `duplicate_status`, `plan_name`, `rate`, `rate_unit` | validation and full link JSON |

### `contract_information.csv`

Every linked canonical contract row, including all standardized contract
sections, is stored in `contract_information_json`. This preserves all source
columns: identity/context fields, ZIP and duplicate fields, document metadata,
matched-offer identifiers, rate/term/fee/renewable fields, missing-section
fields, `supplier_information`, `price_structure`, `supply_price`, `savings`,
`switching_time`, `incentives`, `rescission`, `start_date`, `term`,
`cancellation`, `renewal`, `distribution_company`, URLs, and warnings.

The columns `linked_contract_count`, `document_kinds_json`,
`document_parse_statuses_json`, `document_match_methods_json`,
`contract_missing_section_count`, and `contract_warning_count` are derived from
those complete JSON rows.

### `contracts.csv`

Every linked technical contract row is stored in `technical_contracts_json`,
including `schema_version`, market identity, ZIP, `id`, document kind/status,
URL, matched offer keys, match method, missing sections, every standardized
contract section, `fields`, and warnings.

### Offer and contract quality CSVs

| File | Lossless target | Promoted scalar fields |
|---|---|---|
| `offer_completeness.csv` | `offer_completeness_json` | `core_complete`, missing/unreported field JSON, warning count |
| `document_associations.csv` | `document_associations_json` | linked/summary counts, association status and scope |
| `contract_completeness.csv` | `contract_completeness_json` | parsed/review counts, missing-section and warning totals |

All identity columns in these files remain present inside their JSON objects;
they are also used as join keys.

### Coverage and run-quality CSVs

| File | Lossless target | Promoted scalar fields |
|---|---|---|
| `coverage.csv` | `coverage_json` | market, adapter, status, method, verification flags, counts, retry/resolution fields |
| `plan_count_reconciliation.csv` | `plan_count_reconciliation_json` | source/export counts, status, difference |
| `completed_coverage.csv` | `completed_coverage_json` | supplier counts/lists, target, remaining count |
| `reproducibility.csv` | `reproducibility_json` | run count, status, offer counts |
| `scraper_alerts.csv` | `scraper_alerts_json` | alert count; every severity/code/detail row retained |

The verified run has zero scraper alerts, so its value is an empty JSON array,
not SQL `NULL`.

## Loading rules

1. Validate every source file before constructing rows.
2. Reject a run if `offer_prices.csv` contains duplicate fingerprints.
3. Normalize blank CSV cells to SQL `NULL`; use empty JSON arrays for valid
   one-to-many relationships with no children.
4. Preserve rate values and their units. Do not combine `USD/kWh` and
   `USD/therm` in one dashboard average.
5. Treat `(collection_run_id, offer_fingerprint)` as idempotent.
6. Build all 295 proposed rows in staging memory or a temporary local database,
   verify counts and joins, and only then consider a future EEdb transaction.
7. Do not load `compiled_offerings.csv` separately.
8. Do not attach an unlinked contract to an arbitrary offer.

## Known limitation of the single-table requirement

The table is complete for offer-centered dashboard analysis, but an offer row
cannot naturally represent contracts that have no offer link or coverage
queries that produced no offers. Those records remain preserved in the source
run files. If the dashboard must analyze those records directly, a normalized
multi-table design is safer than adding mixed-grain placeholder rows to this
table.
