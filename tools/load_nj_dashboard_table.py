"""Build and optionally load the completed NJ TPS run into the draft single table."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


CSV_NAMES = (
    "offer_prices.csv", "offer_observations.csv", "offers.csv",
    "offer_documents.csv", "contract_information.csv", "contracts.csv",
    "offer_completeness.csv", "contract_completeness.csv",
    "document_associations.csv", "coverage.csv",
    "plan_count_reconciliation.csv", "completed_coverage.csv",
    "reproducibility.csv", "scraper_alerts.csv",
)

INSERT_COLUMNS = (
    "collection_run_id", "source_directory", "source_manifest_sha256",
    "schema_version", "adapter_versions_json", "offer_fingerprint", "tps",
    "edc_gdc", "commodity", "customer_class", "test_zip",
    "observed_zip_codes_json", "plan_name", "product_ids_json", "rate",
    "rate_unit", "plan_type", "term_months", "term_kind", "monthly_fee",
    "enrollment_fee", "cancellation_fee", "fee_terms_json", "intro_rate",
    "intro_rate_unit", "intro_duration_months",
    "intro_duration_billing_cycles", "renewable_percentage",
    "renewable_source", "renewable_claim", "renewable_details",
    "incentives_json", "deals_and_incentives", "collection_method",
    "source_kind", "offer_status", "context_verified", "live_data_verified",
    "replayed", "source_urls_json", "artifact_ids_json", "captured_first_utc",
    "captured_last_utc", "offer_warnings_json", "observation_count",
    "canonical_observation_count", "offer_keys_json", "observation_zips_json",
    "observation_duplicate_statuses_json", "offer_observations_json",
    "technical_offers_json", "linked_document_count", "contract_summary_count",
    "association_status", "association_scope", "contract_ids_json",
    "document_kinds_json", "document_parse_statuses_json",
    "document_match_methods_json", "offer_documents_json",
    "linked_contract_count", "parsed_contract_count",
    "needs_review_contract_count", "contract_missing_section_count",
    "contract_warning_count", "contract_information_json",
    "technical_contracts_json", "contract_completeness_json", "market_key",
    "adapter", "collection_status", "coverage_method", "source_offer_count",
    "exported_offer_count", "candidate_count", "source_document_count",
    "attempt_count", "completion_issues_json", "resolution_type", "retryable",
    "next_action", "coverage_warnings_json", "coverage_errors_json",
    "count_status", "count_difference", "reproducibility_run_count",
    "reproducibility_status", "reproducibility_offer_counts_json",
    "coverage_json", "completed_supplier_count", "completed_suppliers_json",
    "live_supplier_count", "live_suppliers_json", "supplier_coverage_target",
    "suppliers_remaining_to_target", "completed_coverage_json", "core_complete",
    "missing_core_fields_json", "unreported_conditional_fields_json",
    "offer_quality_warning_count", "offer_completeness_json",
    "document_associations_json", "plan_count_reconciliation_json",
    "reproducibility_json", "scraper_alert_count", "scraper_alerts_json",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def blank_to_none(value: str | None):
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def as_bool(value: str | None) -> bool | None:
    value = blank_to_none(value)
    if value is None:
        return None
    if value.casefold() in {"true", "1", "yes"}:
        return True
    if value.casefold() in {"false", "0", "no"}:
        return False
    raise ValueError(f"invalid Boolean value: {value!r}")


def as_int(value: str | None) -> int | None:
    value = blank_to_none(value)
    return int(value) if value is not None else None


def as_decimal(value: str | None) -> Decimal | None:
    value = blank_to_none(value)
    return Decimal(value) if value is not None else None


def as_count(value: str | None) -> int | None:
    value = blank_to_none(value)
    if value is None:
        return None
    parsed = json_value(value)
    if isinstance(parsed, (list, dict)):
        return len(parsed)
    return int(parsed)


def as_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks timezone: {value!r}")
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def split_pipe(value: str | None) -> list[str]:
    value = blank_to_none(value)
    if value is None:
        return []
    return [item.strip() for item in value.split("|") if item.strip()]


def unique(values) -> list:
    output = []
    seen = set()
    for value in values:
        if value is None or value == "":
            continue
        marker = json.dumps(value, sort_keys=True, default=str)
        if marker not in seen:
            seen.add(marker)
            output.append(value)
    return output


def json_value(value: str | None):
    value = blank_to_none(value)
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def first(values, default=None):
    values = unique(values)
    return values[0] if values else default


def joined(values) -> str | None:
    values = unique(values)
    return " | ".join(str(value) for value in values) if values else None


def market_key(row: dict, supplier="supplier", utility="utility") -> tuple[str, str, str, str]:
    return (row[supplier], row[utility], row["commodity"], row["zip"])


def manifest_hash(run_dir: Path) -> str:
    digest = hashlib.sha256()
    for name in CSV_NAMES:
        path = run_dir / name
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def build_rows(run_dir: Path) -> list[dict]:
    data = {name: read_csv(run_dir / name) for name in CSV_NAMES}
    coverage = data["coverage.csv"]
    completed = {
        market_key(row)
        for row in coverage
        if row["status"] == "success"
        and as_bool(row["context_verified"]) is True
        and as_bool(row["live_data_verified"]) is True
    }
    if not completed:
        raise ValueError("no completed, context-verified, live-data-verified queries")

    observations = [
        row for row in data["offer_observations.csv"]
        if (row["tps"], row["edc_gdc"], row["commodity"], row["test_zip"]) in completed
    ]
    obs_by_fp = defaultdict(list)
    for row in observations:
        obs_by_fp[row["offer_fingerprint"]].append(row)
    eligible = set(obs_by_fp)

    prices = [row for row in data["offer_prices.csv"] if row["offer_fingerprint"] in eligible]
    if len(prices) != len({row["offer_fingerprint"] for row in prices}):
        raise ValueError("offer_prices.csv is not unique by offer_fingerprint")

    technical_by_key = {row["key"]: row for row in data["offers.csv"]}
    documents_by_fp = defaultdict(list)
    for row in data["offer_documents.csv"]:
        if row["offer_fingerprint"] in eligible:
            documents_by_fp[row["offer_fingerprint"]].append(row)

    contracts_by_identity = defaultdict(list)
    for row in data["contract_information.csv"]:
        contracts_by_identity[(row["tps"], row["edc_gdc"], row["commodity"], row["contract_id"])].append(row)
    technical_contracts_by_identity = defaultdict(list)
    for row in data["contracts.csv"]:
        technical_contracts_by_identity[(row["supplier"], row["utility"], row["commodity"], row["id"])].append(row)
    contract_quality_by_identity = defaultdict(list)
    for row in data["contract_completeness.csv"]:
        contract_quality_by_identity[(row["supplier"], row["utility"], row["commodity"], row["contract_id"])].append(row)

    offer_quality_by_key = defaultdict(list)
    for row in data["offer_completeness.csv"]:
        offer_quality_by_key[(row["market_key"], row["zip"], row["offer_key"])].append(row)
    associations_by_key = defaultdict(list)
    for row in data["document_associations.csv"]:
        associations_by_key[(row["market_key"], row["zip"], row["offer_key"])].append(row)

    coverage_by_key = defaultdict(list)
    for row in coverage:
        coverage_by_key[market_key(row)].append(row)
    reconciliation_by_key = defaultdict(list)
    for row in data["plan_count_reconciliation.csv"]:
        reconciliation_by_key[market_key(row)].append(row)
    reproducibility_by_key = defaultdict(list)
    for row in data["reproducibility.csv"]:
        reproducibility_by_key[market_key(row)].append(row)
    alerts_by_key = defaultdict(list)
    for row in data["scraper_alerts.csv"]:
        alerts_by_key[market_key(row)].append(row)
    completed_coverage = {
        (row["utility"], row["commodity"]): row
        for row in data["completed_coverage.csv"]
    }

    run_id = run_dir.name
    source_hash = manifest_hash(run_dir)
    output = []
    for price in prices:
        fp = price["offer_fingerprint"]
        obs = obs_by_fp[fp]
        offer_keys = unique(row["offer_key"] for row in obs)
        technical = [technical_by_key[key] for key in offer_keys if key in technical_by_key]
        links = documents_by_fp[fp]

        contract_rows = []
        technical_contract_rows = []
        contract_quality_rows = []
        for contract_id in unique(row["contract_id"] for row in links):
            identity = (price["tps"], price["edc_gdc"], price["commodity"], contract_id)
            contract_rows.extend(contracts_by_identity[identity])
            technical_contract_rows.extend(technical_contracts_by_identity[identity])
            contract_quality_rows.extend(contract_quality_by_identity[identity])

        query_keys = unique(
            (row["tps"], row["edc_gdc"], row["commodity"], row["test_zip"])
            for row in obs
        )
        coverage_rows = [item for key in query_keys for item in coverage_by_key[key]]
        reconciliation = [item for key in query_keys for item in reconciliation_by_key[key]]
        reproducibility = [item for key in query_keys for item in reproducibility_by_key[key]]
        alerts = [item for key in query_keys for item in alerts_by_key[key]]
        canonical_key = (price["tps"], price["edc_gdc"], price["commodity"], price["test_zip"])
        canonical_coverage = first(coverage_by_key[canonical_key], {})
        canonical_reconciliation = first(reconciliation_by_key[canonical_key], {})
        canonical_reproducibility = first(reproducibility_by_key[canonical_key], {})

        quality_rows = []
        association_rows = []
        for observation in obs:
            key = (
                f"{observation['tps']}|{observation['edc_gdc']}|{observation['commodity']}",
                observation["test_zip"], observation["offer_key"],
            )
            quality_rows.extend(offer_quality_by_key[key])
            association_rows.extend(associations_by_key[key])

        captured = [as_utc(row["captured_at"]) for row in obs]
        technical_warnings = unique(json_value(row["warnings"]) for row in technical)
        missing_core = unique(
            field for row in quality_rows for field in split_pipe(row["missing_core_fields"])
        )
        unreported = unique(
            field for row in quality_rows for field in split_pipe(row["unreported_conditional_fields"])
        )
        status_priority = {"ambiguous_summaries": 3, "missing_useful_document": 2, "complete": 1}
        association_status = first(sorted(
            unique(row["association_status"] for row in association_rows),
            key=lambda value: status_priority.get(value, 0), reverse=True,
        ))
        cc = completed_coverage.get((price["edc_gdc"], price["commodity"]), {})

        row = {
            "collection_run_id": run_id,
            "source_directory": str(run_dir),
            "source_manifest_sha256": source_hash,
            "schema_version": first(row["schema_version"] for row in technical),
            "adapter_versions_json": json_text(unique(row["adapter_version"] for row in technical)),
            "offer_fingerprint": fp,
            "tps": price["tps"], "edc_gdc": price["edc_gdc"],
            "commodity": price["commodity"], "customer_class": "residential",
            "test_zip": price["test_zip"],
            "observed_zip_codes_json": json_text(unique(split_pipe(price["observed_zip_codes"]) + [r["test_zip"] for r in obs])),
            "plan_name": price["plan_name"],
            "product_ids_json": json_text(unique(r["product_id"] for r in obs)),
            "rate": as_decimal(price["rate"]), "rate_unit": price["rate_unit"],
            "plan_type": blank_to_none(price["plan_type"]),
            "term_months": as_int(price["term_months"]),
            "term_kind": joined(row["term_kind"] for row in technical),
            "monthly_fee": as_decimal(price["monthly_fee"]),
            "enrollment_fee": as_decimal(price["enrollment_fee"]),
            "cancellation_fee": as_decimal(price["cancellation_fee"]),
            "fee_terms_json": json_text(unique(json_value(row["fee_terms"]) for row in technical)),
            "intro_rate": as_decimal(price["intro_rate"]),
            "intro_rate_unit": blank_to_none(price["intro_rate_unit"]),
            "intro_duration_months": as_int(price["intro_duration_months"]),
            "intro_duration_billing_cycles": as_int(price["intro_duration_billing_cycles"]),
            "renewable_percentage": as_decimal(price["renewable_percentage"]),
            "renewable_source": joined(row["renewable_source"] for row in technical),
            "renewable_claim": joined(row["renewable_claim"] for row in technical),
            "renewable_details": blank_to_none(price["renewable_details"]),
            "incentives_json": json_text(unique(json_value(row["incentives"]) for row in technical)),
            "deals_and_incentives": blank_to_none(price["deals_and_incentives"]),
            "collection_method": joined(row["collection_method"] for row in technical),
            "source_kind": joined(row["source_kind"] for row in technical),
            "offer_status": joined(row["status"] for row in technical),
            "context_verified": all(as_bool(row["context_verified"]) is True for row in technical),
            "live_data_verified": all(as_bool(row["live_data_verified"]) is True for row in technical),
            "replayed": any(as_bool(row["replayed"]) is True for row in technical),
            "source_urls_json": json_text(unique(split_pipe(price["source_urls"]) + [r["source_url"] for r in obs])),
            "artifact_ids_json": json_text(unique(row["artifact_id"] for row in obs)),
            "captured_first_utc": min(captured), "captured_last_utc": max(captured),
            "offer_warnings_json": json_text(technical_warnings),
            "observation_count": len(obs),
            "canonical_observation_count": sum(as_bool(row["canonical_observation"]) is True for row in obs),
            "offer_keys_json": json_text(offer_keys),
            "observation_zips_json": json_text(unique(row["test_zip"] for row in obs)),
            "observation_duplicate_statuses_json": json_text(unique(row["duplicate_status"] for row in obs)),
            "offer_observations_json": json_text(obs), "technical_offers_json": json_text(technical),
            "linked_document_count": len(links),
            "contract_summary_count": sum(as_int(row["contract_summary_count"]) or 0 for row in association_rows),
            "association_status": association_status,
            "association_scope": joined(row["association_scope"] for row in association_rows),
            "contract_ids_json": json_text(unique(row["contract_id"] for row in links)),
            "document_kinds_json": json_text(unique(row["document_kind"] for row in links)),
            "document_parse_statuses_json": json_text(unique(row["parse_status"] for row in links)),
            "document_match_methods_json": json_text(unique(row["match_method"] for row in links)),
            "offer_documents_json": json_text(links),
            "linked_contract_count": len(contract_rows),
            "parsed_contract_count": sum(row["parse_status"] in {"parsed", "text_extracted", "retained"} for row in contract_rows),
            "needs_review_contract_count": sum(row["parse_status"] in {"partial", "needs_review", "failed"} for row in contract_rows),
            "contract_missing_section_count": sum(as_int(row["missing_section_count"]) or 0 for row in contract_quality_rows),
            "contract_warning_count": sum(as_int(row["warning_count"]) or 0 for row in contract_quality_rows),
            "contract_information_json": json_text(contract_rows),
            "technical_contracts_json": json_text(technical_contract_rows),
            "contract_completeness_json": json_text(contract_quality_rows),
            "market_key": f"{price['tps']}|{price['edc_gdc']}|{price['commodity']}",
            "adapter": blank_to_none(canonical_coverage.get("adapter")),
            "collection_status": blank_to_none(canonical_coverage.get("status")),
            "coverage_method": blank_to_none(canonical_coverage.get("method")),
            "source_offer_count": as_int(canonical_coverage.get("source_offer_count")),
            "exported_offer_count": as_int(canonical_reconciliation.get("exported_offer_count")),
            "candidate_count": as_int(canonical_coverage.get("candidates")),
            "source_document_count": as_int(canonical_coverage.get("documents")),
            "attempt_count": as_count(canonical_coverage.get("attempts")),
            "completion_issues_json": json_text(unique(json_value(r["completion_issues"]) for r in coverage_rows)),
            "resolution_type": blank_to_none(canonical_coverage.get("resolution_type")),
            "retryable": as_bool(canonical_coverage.get("retryable")),
            "next_action": blank_to_none(canonical_coverage.get("next_action")),
            "coverage_warnings_json": json_text(unique(json_value(r["warnings"]) for r in coverage_rows)),
            "coverage_errors_json": json_text(unique(json_value(r["errors"]) for r in coverage_rows)),
            "count_status": blank_to_none(canonical_reconciliation.get("count_status")),
            "count_difference": as_int(canonical_reconciliation.get("difference")),
            "reproducibility_run_count": as_int(canonical_reproducibility.get("run_count")),
            "reproducibility_status": blank_to_none(canonical_reproducibility.get("reproducibility_status")),
            "reproducibility_offer_counts_json": json_text(split_pipe(canonical_reproducibility.get("offer_counts"))),
            "coverage_json": json_text(coverage_rows),
            "completed_supplier_count": as_int(cc.get("completed_supplier_count")),
            "completed_suppliers_json": json_text(split_pipe(cc.get("completed_suppliers"))),
            "live_supplier_count": as_int(cc.get("live_supplier_count")),
            "live_suppliers_json": json_text(split_pipe(cc.get("live_suppliers"))),
            "supplier_coverage_target": as_int(cc.get("target")),
            "suppliers_remaining_to_target": as_int(cc.get("remaining_to_target")),
            "completed_coverage_json": json_text([cc] if cc else []),
            "core_complete": all(as_bool(r["core_complete"]) is True for r in quality_rows),
            "missing_core_fields_json": json_text(missing_core),
            "unreported_conditional_fields_json": json_text(unreported),
            "offer_quality_warning_count": sum(as_int(r["warning_count"]) or 0 for r in quality_rows),
            "offer_completeness_json": json_text(quality_rows),
            "document_associations_json": json_text(association_rows),
            "plan_count_reconciliation_json": json_text(reconciliation),
            "reproducibility_json": json_text(reproducibility),
            "scraper_alert_count": len(alerts), "scraper_alerts_json": json_text(alerts),
        }
        missing = set(INSERT_COLUMNS) - row.keys()
        if missing:
            raise AssertionError(f"loader omitted columns: {sorted(missing)}")
        output.append(row)

    if len(output) != len(prices):
        raise AssertionError("constructed row count does not match eligible canonical offers")
    return output


def read_env(path: Path) -> dict[str, str]:
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    required = {"DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"}
    missing = required - values.keys()
    if missing:
        raise ValueError(f"environment file is missing {sorted(missing)}")
    return values


def schema_statement(path: Path) -> str:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("--")]
    sql = "\n".join(lines).strip()
    return sql[:-1] if sql.endswith(";") else sql


def apply_rows(rows: list[dict], env_file: Path, schema_file: Path) -> None:
    import pymysql

    config = read_env(env_file)
    connection = pymysql.connect(
        host=config["DB_HOST"], port=int(config["DB_PORT"]),
        user=config["DB_USER"], password=config["DB_PASSWORD"],
        database=config["DB_NAME"], charset="utf8mb4", autocommit=False,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET time_zone = '+00:00'")
            cursor.execute(schema_statement(schema_file))
            connection.commit()
            run_id = rows[0]["collection_run_id"]
            cursor.execute("SELECT COUNT(*) FROM nj_tps_dashboard_data WHERE collection_run_id=%s", (run_id,))
            if cursor.fetchone()[0]:
                raise ValueError(f"collection run {run_id!r} is already loaded")
            placeholders = ", ".join(["%s"] * len(INSERT_COLUMNS))
            insert = f"INSERT INTO nj_tps_dashboard_data ({', '.join(INSERT_COLUMNS)}) VALUES ({placeholders})"
            cursor.executemany(insert, [tuple(row[column] for column in INSERT_COLUMNS) for row in rows])
            cursor.execute("SELECT COUNT(*) FROM nj_tps_dashboard_data WHERE collection_run_id=%s", (run_id,))
            loaded = cursor.fetchone()[0]
            if loaded != len(rows):
                raise RuntimeError(f"expected {len(rows)} rows after insert; found {loaded}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--schema-file", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run_dir = args.run_directory.resolve()
    rows = build_rows(run_dir)
    markets = {(row["edc_gdc"], row["commodity"]) for row in rows}
    suppliers = {row["tps"] for row in rows}
    print(f"Validated {len(rows)} completed canonical offers across {len(suppliers)} suppliers and {len(markets)} markets.")
    print(f"Manifest SHA-256: {rows[0]['source_manifest_sha256']}")
    if not args.apply:
        print("Dry run complete; no database changes were made.")
        return 0
    if not args.env_file or not args.schema_file:
        parser.error("--apply requires --env-file and --schema-file")
    apply_rows(rows, args.env_file.resolve(), args.schema_file.resolve())
    print(f"Loaded {len(rows)} rows into nj_tps_dashboard_data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
