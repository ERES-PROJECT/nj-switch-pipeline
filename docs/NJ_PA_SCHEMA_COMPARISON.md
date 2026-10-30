# Unified PA and NJ offer schema

## Revised direction

PA and NJ should feed one neutral schema. The shared schema should contain useful offer facts, not scraper bookkeeping or reporting-only duplicate metrics.

The existing PA and NJ outputs can remain unchanged as staging inputs. Each pipeline transforms its source fields into the recommended tables below.

```text
PA output ──> PA staging ──┐
                           ├──> shared offer schema
NJ output ──> NJ staging ──┘
```

## Recommended tables

| Table | Purpose |
|---|---|
| `suppliers` | One supplier name and its contact information |
| `utilities` | One EDC/GDC name and its contact information |
| `offers` | One unique set of supplier offer terms |
| `offer_availability` | ZIP codes and dates associated with each offer |
| `offer_documents` | Optional contracts or disclosures linked to an offer |

`offer_availability` replaces the earlier `offer_observations` name. It describes where and when an offer was available without presenting scraper activity as a business object.

## Final recommended column list

This is the revised common output. It omits every field questioned for removal and retains `offer_fingerprint` for now.

| # | Column | # | Column |
|---:|---|---:|---|
| 1 | `offer_id` | 22 | `intro_duration_value` |
| 2 | `offer_fingerprint` | 23 | `intro_duration_unit` |
| 3 | `supplier_name` | 24 | `has_monthly_fee` |
| 4 | `supplier_product_id` | 25 | `monthly_fee` |
| 5 | `supplier_website` | 26 | `enrollment_fee` |
| 6 | `supplier_phone` | 27 | `cancellation_fee` |
| 7 | `utility_name` | 28 | `is_renewable` |
| 8 | `utility_website` | 29 | `renewable_percentage` |
| 9 | `utility_phone` | 30 | `renewable_source` |
| 10 | `state` | 31 | `has_incentive` |
| 11 | `commodity` | 32 | `incentive_text` |
| 12 | `customer_class` | 33 | `net_metering_eligible` |
| 13 | `plan_name` | 34 | `utility_rate_schedule` |
| 14 | `rate_structure` | 35 | `has_plan_end_date` |
| 15 | `rate_amount` | 36 | `plan_end_date` |
| 16 | `rate_unit` | 37 | `enrollment_url` |
| 17 | `term_months` | 38 | `zip` |
| 18 | `term_type` | 39 | `source_updated_at` |
| 19 | `has_intro_rate` | 40 | `collected_at` |
| 20 | `intro_rate_amount` | 41 | `quality_warnings` |
| 21 | `intro_rate_unit` |  |  |

`rate_unit` contains both the currency and denominator, such as `USD/kWh`, `USD/therm`, `USD/CCF`, or `USD/Dth`. There is no separate `currency` column.

`intro_rate_unit` follows the same complete-unit rule as `rate_unit`, such as `USD/kWh`. Keeping the separate introductory amount prevents the introductory rate from overwriting the normal offer rate.

## Column-by-column source mapping

### Identity and market context

| PA column | Common column | NJ column | Transformation |
|---|---|---|---|
| — | `offer_id` | — | Generate one local database ID after deduplication. |
| — | `offer_fingerprint` | `offer_fingerprint` | Keep temporarily as an internal duplicate check. Recompute from normalized shared fields. |
| `egs` / `Name` | `supplier_name` | `tps` / `supplier` | Normalize supplier spelling. |
| — | `supplier_product_id` | `product_id` | Keep a genuine supplier-issued ID when present. |
| `egs_website` / `Web` | `supplier_website` | — | Supplier homepage/contact site. |
| `egs_phone` / `Phone` | `supplier_phone` | — | Normalize phone formatting. |
| `edc` / `MainPUC` | `utility_name` | `edc_gdc` / `utility` | Normalize the EDC/GDC name. |
| `edc_website` | `utility_website` | — | Utility homepage. |
| `edc_phone` | `utility_phone` | — | Normalize phone formatting. |
| `state` / `State` | `state` | constant `NJ` | Store two-character state code. |
| `commodity` / `Commodity` | `commodity` | `commodity` | Normalize to `electric` or `gas`. |
| `service_type` / `Service` | `customer_class` | residential scraper context | Map `R` to `residential`; define PA `S` before mapping it. |
| — | `plan_name` | `plan_name` / `name` | NJ supplies this. PA remains null unless a plan name is collected. |

### Price and term

| PA column | Common column | NJ column | Transformation |
|---|---|---|---|
| `rate_type` / `PriceStructure` | `rate_structure` | `plan_type` / `rate_structure` | Map `F` to `fixed`, `V` to `variable`; review PA `U` before mapping it. |
| `rate` / `Rate` | `rate_amount` | `rate` | Decimal numeric value. |
| derived from commodity/source | `rate_unit` | `rate_unit` | Use a complete unit such as `USD/kWh`; never load a rate whose unit cannot be established. |
| `term` / `TermLength` | `term_months` | `term_months` | Integer months or null. |
| derived from term/source | `term_type` | `term_kind` | `fixed_term`, `month_to_month`, or null. |
| `intro_price` / `IntroPrice` | `has_intro_rate` | derived from NJ intro-rate fields | PA's misleadingly named field is a Boolean. NJ is true when an introductory price is explicitly present. |
| — | `intro_rate_amount` | `intro_rate` / `intro_price.value` | Keep the actual introductory price when NJ provides it. PA remains null because PA currently supplies only a Boolean. |
| — | `intro_rate_unit` | `intro_rate_unit` / `intro_price.unit` | Use a complete unit such as `USD/kWh`. |
| — | `intro_duration_value` | `intro_duration_months` or `intro_duration_billing_cycles` | Store the stated duration. |
| — | `intro_duration_unit` | determined by the populated NJ duration field | `month` or `billing_cycle`. |
| `has_monthly_fee` | `has_monthly_fee` | derived from `monthly_fee` | Keep as nullable Boolean. True for an explicit positive fee, false for an explicit zero/no-fee statement, and null when unknown. |
| `monthly_fee_amount` / `MonthlyFee` | `monthly_fee` | `monthly_fee` | Decimal USD amount or null. |
| `enroll_fee` | `enrollment_fee` | `enrollment_fee` | Decimal USD amount or null. |
| `cancel_fee` / `CancelFee` | `cancellation_fee` | `cancellation_fee` | Decimal USD amount or null. |

### Renewable attributes, incentives, and other terms

| PA column | Common column | NJ column | Transformation |
|---|---|---|---|
| `is_green` | `is_renewable` | derived from explicit renewable fields | Nullable Boolean. Do not turn missing data into false. |
| `green_percentage` | `renewable_percentage` | `renewable_percentage` | Decimal percentage from 0 through 100. |
| `green_source` | `renewable_source` | `renewable_source` | Stated source such as wind, solar, or renewable mix. |
| `discount_available` / `DiscountAvailable` | `has_incentive` | derived from `deals_and_incentives` | Nullable Boolean. |
| — | `incentive_text` | `deals_and_incentives` / `incentives` | Preserve the actual incentive description. |
| `net_metering` | `net_metering_eligible` | — | Nullable Boolean; NJ remains null until collected. |
| `rate_schedule` | `utility_rate_schedule` | — | Utility/customer tariff context; not the plan name. |
| `plan_end_date` / `EndDate` | `has_plan_end_date` | derived when a date exists | Preserve PA `YES`/`NO` separately from the date. |
| parsed date from `plan_end_date` | `plan_end_date` | — | Only valid calendar dates belong here. |
| `sign_up_link` | `enrollment_url` | `enrollment_url` | Dedicated enrollment link only. |

### Availability and collection dates

| PA column | Common column | NJ column | Transformation |
|---|---|---|---|
| `zip` / `Zip` | `zip` | `test_zip` / observed ZIP | Five-character text. One `offer_availability` record per unique offer and ZIP. |
| `date` / `Date` | `source_updated_at` | — | PA's source/supplier update date. |
| import time | `collected_at` | `captured_at` | Time the pipeline collected the record. |
| validation result | `quality_warnings` | `warnings` | Keep only actionable warnings; blank means none were recorded. |

## Deduplication before insertion

Duplicate records should not enter `offers`. Normalize the data, compute the temporary fingerprint, and resolve an existing offer before insertion.

The fingerprint should use:

- supplier and utility
- commodity and customer class
- supplier product ID when present, otherwise normalized plan name
- rate amount and unit
- rate structure
- term
- introductory-rate flag and duration
- fees
- renewable percentage/source
- incentives

ZIP and collection dates are excluded because they belong to `offer_availability`. If the material terms change, create a new offer.

The fingerprint remains in the recommendation for now because it provides an auditable way to explain why two imported rows were merged. It should be treated as internal metadata, not as another public ID.

## Removed from the recommendation

| Removed field/concept | Treatment |
|---|---|
| `currency` | Removed. Currency is included in `rate_unit`. Fee amounts are understood to be USD in the current PA/NJ scope. |
| `renewable_claim` | Removed from the shared output. Keep any claim text only in raw staging unless later requested. |
| `source_system` | Removed. The shared record should describe the offer, not which scraper produced it. |
| NJ `offer_key` | Removed. It includes ZIP and duplicates the purposes served by local `offer_id`, supplier product ID, and temporary fingerprint. |
| `source_record_id` / PA `seq` | Removed from the shared output. Source-local IDs may stay in staging for troubleshooting. |
| `source_url` | Removed from the shared output. It may stay in staging if exact-page provenance is ever needed. |
| `artifact_id` | Removed. Scraped HTML/PDF/screenshot references remain scraper-debug data, not shared offer data. |
| `duplicate_status` | Removed. Duplicates are resolved before insertion. |
| `same_rate_offer_count` | Removed. Different offers may legitimately share a rate. |
| `same_rate_status` | Removed. Same-rate similarity is not an offer attribute. |
| `zip_count` | Removed. It can be counted from `offer_availability` if ever needed. |
| `observation_count` | Removed. Collection repetition is not a consumer-facing offer attribute. |
| `document_count` | Removed. It can be counted from `offer_documents` if ever needed. |
| `rate_cents_per_unit` | Removed. It is a display conversion of `rate_amount`, not a separate fact. |
| `first_captured_at` / `last_captured_at` | Removed. `collected_at` is retained on availability records; min/max can be calculated if needed. |
| `more_info` | Removed. The current PA electric file has no populated values. |
| `unlimited_rate` | Removed pending a reliable definition and unit. Keep the raw PA value in staging. |

## Optional fields not included, with justification

These are not part of the recommendation. They are documented only so they can be reconsidered deliberately.

### Exact source page URL

`supplier_website` is the supplier's general homepage or contact site. A source-page URL is the exact page where a particular price was collected. It can help prove or reproduce a rate after a scraper failure or data dispute. It was removed because this database is currently focused on usable offer data rather than audit-grade provenance.

### Artifact reference

An artifact is a saved copy of collection evidence, such as HTML, JSON, a PDF contract, or a screenshot. An artifact ID links an offer back to that file. It is useful for scraper debugging and regulatory/audit evidence, but it adds no direct value to ordinary offer queries. It was removed from the shared output and can remain inside the NJ scraper's operational storage.

### Renewable claim text

A renewable claim is supplier language such as “100% clean energy” that may not identify the actual energy source or percentage. It can preserve marketing or disclosure wording, but it is less structured than `is_renewable`, `renewable_percentage`, and `renewable_source`. It was removed because those three fields cover the current comparison need more clearly.

### Source-system label

A source label can help troubleshoot whether a value came from PA or NJ, but state and staging lineage already make that evident for the current two-state scope. It was removed from the common output. The staging tables remain separate if lineage is needed.

## Remaining staging-only data

Keep complete PA and NJ source rows in staging until the new mapping is proven. This protects against accidental loss without forcing legacy/debug fields into the permanent schema.

PA's PTC data remains a separate subject and should not be mixed into supplier offers.
