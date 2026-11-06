-- New Jersey TPS single-table dashboard schema.
--
-- Proposed single-table dashboard model for New Jersey TPS collections.
-- Grain: one row per (collection_run_id, offer_fingerprint).
--
-- Offer-level attributes are typed columns. One-to-many child records are
-- stored as lossless JSON arrays so joining observations, documents, and
-- contracts cannot multiply offers or distort dashboard aggregates.

CREATE TABLE IF NOT EXISTS nj_tps_dashboard_data (
    -- Import identity and lineage
    nj_row_id                       BIGINT NOT NULL AUTO_INCREMENT,
    collection_run_id               VARCHAR(255) NOT NULL,
    source_directory                VARCHAR(1024) NULL,
    source_manifest_sha256          CHAR(64) NULL,
    ingested_at_utc                 DATETIME(6) NOT NULL DEFAULT UTC_TIMESTAMP(6),
    schema_version                  VARCHAR(32) NULL,
    adapter_versions_json           JSON NULL,

    -- Canonical offer identity and market context
    offer_fingerprint               VARCHAR(64) NOT NULL,
    tps                             VARCHAR(255) NOT NULL,
    edc_gdc                         VARCHAR(255) NOT NULL,
    commodity                       VARCHAR(16) NOT NULL,
    customer_class                  VARCHAR(32) NOT NULL DEFAULT 'residential',
    test_zip                        CHAR(5) NOT NULL,
    observed_zip_codes_json         JSON NOT NULL,
    plan_name                       VARCHAR(512) NOT NULL,
    product_ids_json                JSON NULL,

    -- Canonical price and contract terms
    rate                            DECIMAL(14,8) NOT NULL,
    rate_unit                       VARCHAR(32) NOT NULL,
    plan_type                       VARCHAR(32) NULL,
    term_months                     SMALLINT UNSIGNED NULL,
    term_kind                       VARCHAR(32) NULL,
    monthly_fee                     DECIMAL(12,4) NULL,
    enrollment_fee                  DECIMAL(12,4) NULL,
    cancellation_fee                DECIMAL(12,4) NULL,
    fee_terms_json                  JSON NULL,
    intro_rate                      DECIMAL(14,8) NULL,
    intro_rate_unit                 VARCHAR(32) NULL,
    intro_duration_months           SMALLINT UNSIGNED NULL,
    intro_duration_billing_cycles   SMALLINT UNSIGNED NULL,

    -- Renewable and incentive attributes
    renewable_percentage            DECIMAL(6,3) NULL,
    renewable_source                TEXT NULL,
    renewable_claim                 TEXT NULL,
    renewable_details               TEXT NULL,
    incentives_json                 JSON NULL,
    deals_and_incentives            TEXT NULL,

    -- Canonical collection/provenance attributes
    collection_method               VARCHAR(64) NULL,
    source_kind                     VARCHAR(64) NULL,
    offer_status                    VARCHAR(32) NULL,
    context_verified                BOOLEAN NULL,
    live_data_verified              BOOLEAN NULL,
    replayed                        BOOLEAN NULL,
    source_urls_json                JSON NULL,
    artifact_ids_json               JSON NULL,
    captured_first_utc              DATETIME(6) NOT NULL,
    captured_last_utc               DATETIME(6) NOT NULL,
    offer_warnings_json             JSON NULL,

    -- Observation rollup (offer_observations.csv / offers.csv)
    observation_count               INT UNSIGNED NOT NULL DEFAULT 0,
    canonical_observation_count     INT UNSIGNED NOT NULL DEFAULT 0,
    offer_keys_json                 JSON NULL,
    observation_zips_json           JSON NULL,
    observation_duplicate_statuses_json JSON NULL,
    offer_observations_json         JSON NOT NULL,
    technical_offers_json           JSON NOT NULL,

    -- Offer/document association rollup
    linked_document_count           INT UNSIGNED NOT NULL DEFAULT 0,
    contract_summary_count          INT UNSIGNED NOT NULL DEFAULT 0,
    association_status              VARCHAR(64) NULL,
    association_scope               VARCHAR(32) NULL,
    contract_ids_json               JSON NULL,
    document_kinds_json             JSON NULL,
    document_parse_statuses_json    JSON NULL,
    document_match_methods_json     JSON NULL,
    offer_documents_json            JSON NOT NULL,

    -- Linked contract rollup. Full child rows remain lossless in JSON.
    linked_contract_count           INT UNSIGNED NOT NULL DEFAULT 0,
    parsed_contract_count           INT UNSIGNED NOT NULL DEFAULT 0,
    needs_review_contract_count     INT UNSIGNED NOT NULL DEFAULT 0,
    contract_missing_section_count  INT UNSIGNED NOT NULL DEFAULT 0,
    contract_warning_count          INT UNSIGNED NOT NULL DEFAULT 0,
    contract_information_json       JSON NOT NULL,
    technical_contracts_json        JSON NOT NULL,
    contract_completeness_json      JSON NOT NULL,

    -- Query/market coverage fields (coverage.csv)
    market_key                      VARCHAR(800) NOT NULL,
    adapter                         VARCHAR(128) NULL,
    collection_status               VARCHAR(32) NULL,
    coverage_method                 VARCHAR(64) NULL,
    source_offer_count              INT UNSIGNED NULL,
    exported_offer_count            INT UNSIGNED NULL,
    candidate_count                 INT UNSIGNED NULL,
    source_document_count           INT UNSIGNED NULL,
    attempt_count                   INT UNSIGNED NULL,
    completion_issues_json          JSON NULL,
    resolution_type                 VARCHAR(64) NULL,
    retryable                       BOOLEAN NULL,
    next_action                     TEXT NULL,
    coverage_warnings_json          JSON NULL,
    coverage_errors_json            JSON NULL,
    count_status                    VARCHAR(32) NULL,
    count_difference                INT NULL,
    reproducibility_run_count       INT UNSIGNED NULL,
    reproducibility_status          VARCHAR(32) NULL,
    reproducibility_offer_counts_json JSON NULL,
    coverage_json                   JSON NOT NULL,

    -- Utility/commodity coverage summary (completed_coverage.csv)
    completed_supplier_count        INT UNSIGNED NULL,
    completed_suppliers_json        JSON NULL,
    live_supplier_count             INT UNSIGNED NULL,
    live_suppliers_json             JSON NULL,
    supplier_coverage_target        INT UNSIGNED NULL,
    suppliers_remaining_to_target  INT UNSIGNED NULL,
    completed_coverage_json         JSON NOT NULL,

    -- Offer-level quality summaries
    core_complete                   BOOLEAN NULL,
    missing_core_fields_json        JSON NULL,
    unreported_conditional_fields_json JSON NULL,
    offer_quality_warning_count     INT UNSIGNED NULL,
    offer_completeness_json         JSON NOT NULL,
    document_associations_json      JSON NOT NULL,
    plan_count_reconciliation_json  JSON NOT NULL,
    reproducibility_json            JSON NOT NULL,
    scraper_alert_count             INT UNSIGNED NOT NULL DEFAULT 0,
    scraper_alerts_json             JSON NOT NULL,

    PRIMARY KEY (nj_row_id),
    UNIQUE KEY uq_nj_tps_run_offer (collection_run_id, offer_fingerprint),
    KEY idx_nj_tps_market (commodity, edc_gdc, tps),
    KEY idx_nj_tps_rate (rate_unit, rate),
    KEY idx_nj_tps_capture (captured_last_utc),
    KEY idx_nj_tps_status (collection_status, live_data_verified),
    CONSTRAINT chk_nj_tps_commodity CHECK (commodity IN ('electric', 'gas')),
    CONSTRAINT chk_nj_tps_rate CHECK (rate > 0),
    CONSTRAINT chk_nj_tps_renewable CHECK (
        renewable_percentage IS NULL OR renewable_percentage BETWEEN 0 AND 100
    )
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_520_ci
  COMMENT='Draft denormalized NJ TPS dashboard table; one canonical offer per run';
