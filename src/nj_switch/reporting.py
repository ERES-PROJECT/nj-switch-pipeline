import csv
import hashlib
import json
from pathlib import Path

from .models import CollectionResult
from .contracts import LABELS
from .registry import CONFIG
from .quality import (alert_rows, completed_coverage_rows, contract_completeness_rows,
                      document_association_rows, offer_completeness_rows,
                      plan_count_rows, reproducibility_rows)


def csv_safe(value):
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    return "'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value


def single_line(value) -> str:
    """Keep reader-facing CSV cells on one physical line."""
    return " ".join(str("" if value is None else value).split())


def _reader_row(row: dict, columns: list[str]) -> dict:
    return {column: csv_safe(single_line(row.get(column))) for column in columns}


def write_rows(path: Path, rows: list[dict], columns: list[str]):
    """Write a stable, spreadsheet-safe quality view, including its header when empty."""
    with path.open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(_reader_row(row, columns))


def _decimal_token(value) -> str:
    if value is None:
        return ""
    token = format(value, "f")
    return token.rstrip("0").rstrip(".") if "." in token else token


def offer_fingerprint(offer) -> str:
    """Stable purchasing identity that deliberately excludes ZIP and capture metadata."""
    identity = {"product_id": offer.product_id} if offer.product_id else {
        "plan_name": " ".join(offer.name.casefold().split())
    }
    data = {
        "supplier": offer.supplier,
        "utility": offer.utility,
        "commodity": offer.commodity,
        "identity": identity,
        "rate": _decimal_token(offer.price.value),
        "rate_unit": offer.price.unit,
        "rate_structure": offer.rate_structure,
        "term_months": offer.term_months,
        "term_kind": offer.term_kind,
        "monthly_fee": _decimal_token(offer.monthly_fee),
        "enrollment_fee": _decimal_token(offer.enrollment_fee),
        "cancellation_fee": _decimal_token(offer.cancellation_fee),
        "intro_rate": _decimal_token(offer.intro_price.value) if offer.intro_price else "",
        "intro_rate_unit": offer.intro_price.unit if offer.intro_price else "",
        "intro_duration_months": offer.intro_duration_months,
        "intro_duration_billing_cycles": offer.intro_duration_billing_cycles,
        "renewable_percentage": _decimal_token(offer.renewable_percentage),
        "renewable_source": single_line(offer.renewable_source).casefold(),
        "renewable_claim": single_line(offer.renewable_claim).casefold(),
        "incentives": sorted(single_line(value).casefold() for value in offer.incentives),
        "fee_terms": offer.fee_terms,
    }
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()[:24]


def _offer_groups(results: list[CollectionResult]) -> list[dict]:
    groups = {}
    for result in results:
        if result.replayed or not result.live_data_verified:
            continue
        for offer in result.offers:
            fingerprint = offer_fingerprint(offer)
            groups.setdefault(fingerprint, {"fingerprint": fingerprint, "observations": []})["observations"].append((result, offer))
    return sorted(groups.values(), key=lambda group: (
        {"electric": 0, "gas": 1}.get(group["observations"][0][1].commodity, 2),
        group["observations"][0][1].supplier.casefold(),
        group["observations"][0][1].utility.casefold(),
        group["observations"][0][1].name.casefold(),
        group["observations"][0][1].price.value,
    ))


def _duplicate_status(observations) -> str:
    if len(observations) == 1:
        return "unique"
    if len({result.query.zip for result, _ in observations}) > 1:
        return "consolidated_across_zips"
    return "repeated_observation"


def write_offer_prices(results: list[CollectionResult], path: Path):
    """Write one canonical purchasing row per materially equivalent offer."""
    columns = [
        "tps", "edc_gdc", "commodity", "test_zip", "observed_zip_codes",
        "offer_fingerprint", "plan_name", "rate", "rate_unit",
        "plan_type", "term_months", "monthly_fee", "enrollment_fee",
        "cancellation_fee", "intro_rate", "intro_rate_unit", "intro_duration_months",
        "intro_duration_billing_cycles", "renewable_percentage", "renewable_details",
        "deals_and_incentives", "document_count", "source_urls", "captured_at",
    ]
    groups = _offer_groups(results)
    with path.open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, columns)
        writer.writeheader()
        for group in groups:
            observations = sorted(group["observations"], key=lambda item: (item[0].query.zip, item[1].captured_at))
            result, offer = observations[0]
            zips = sorted({item.query.zip for item, _ in observations})
            captured = sorted({item.captured_at for _, item in observations})
            renewable_details = " | ".join(dict.fromkeys(
                value for value in (single_line(offer.renewable_source), single_line(offer.renewable_claim)) if value
            ))
            row = {
                "tps": result.query.supplier,
                "edc_gdc": result.query.utility,
                "commodity": result.query.commodity,
                "test_zip": zips[0],
                "observed_zip_codes": " | ".join(zips),
                "offer_fingerprint": group["fingerprint"],
                "plan_name": offer.name,
                "rate": str(offer.price.value),
                "rate_unit": offer.price.unit,
                "plan_type": offer.rate_structure,
                "term_months": offer.term_months,
                "monthly_fee": offer.monthly_fee,
                "enrollment_fee": offer.enrollment_fee,
                "cancellation_fee": offer.cancellation_fee,
                "intro_rate": str(offer.intro_price.value) if offer.intro_price else None,
                "intro_rate_unit": offer.intro_price.unit if offer.intro_price else None,
                "intro_duration_months": offer.intro_duration_months,
                "intro_duration_billing_cycles": offer.intro_duration_billing_cycles,
                "renewable_percentage": offer.renewable_percentage,
                "renewable_details": renewable_details,
                "deals_and_incentives": " | ".join(single_line(value) for value in offer.incentives),
                "document_count": len({contract_id for _, item in observations for contract_id in item.contract_ids}),
                "source_urls": " | ".join(sorted({item.source_url for _, item in observations})),
                "captured_at": captured[-1],
            }
            writer.writerow(_reader_row(row, columns))


def write_offer_observations(results: list[CollectionResult], path: Path):
    """Write one row per ZIP-level observation mapped to its canonical offer."""
    columns = [
        "tps", "edc_gdc", "commodity", "test_zip", "offer_fingerprint", "offer_key",
        "product_id", "plan_name", "rate", "rate_unit", "term_months", "canonical_observation",
        "duplicate_status", "source_url", "artifact_id", "captured_at",
    ]
    with path.open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, columns)
        writer.writeheader()
        for group in _offer_groups(results):
            observations = sorted(group["observations"], key=lambda item: (item[0].query.zip, item[1].captured_at))
            status = _duplicate_status(observations)
            for index, (result, offer) in enumerate(observations):
                row = {
                    "tps": offer.supplier,
                    "edc_gdc": offer.utility,
                    "commodity": offer.commodity,
                    "test_zip": result.query.zip,
                    "offer_fingerprint": group["fingerprint"],
                    "offer_key": offer.key,
                    "product_id": offer.product_id,
                    "plan_name": offer.name,
                    "rate": offer.price.value,
                    "rate_unit": offer.price.unit,
                    "term_months": offer.term_months,
                    "canonical_observation": index == 0,
                    "duplicate_status": status,
                    "source_url": offer.source_url,
                    "artifact_id": offer.artifact_id,
                    "captured_at": offer.captured_at,
                }
                writer.writerow(_reader_row(row, columns))


def write_compiled_offerings(results: list[CollectionResult], path: Path):
    """Backward-compatible alias for the reader-facing offer-price export."""
    write_offer_prices(results, path)


def write_contract_information(results: list[CollectionResult], path: Path):
    """Write one canonical row per document, consolidating repeated ZIP observations."""
    columns = [
        "tps", "edc_gdc", "commodity", "test_zip", "observed_zip_codes", "zip_count",
        "observation_count", "duplicate_status", "contract_id", "document_kind",
        "parse_status", "media_type", "matched_offer_count", "matched_offer_fingerprints", "matched_offer_keys",
        "matched_product_ids", "matched_plan_names", "match_method", "contract_rate",
        "contract_rate_unit", "contract_rate_structure", "contract_term_months", "monthly_fee",
        "enrollment_fee", "cancellation_fee", "renewable_percentage", "missing_section_count",
        "missing_sections", *LABELS, "contract_url", "source_urls", "warnings",
    ]
    with path.open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, columns)
        writer.writeheader()
        groups = {}
        for result in results:
            if result.replayed or not result.live_data_verified:
                continue
            offers = {offer.key: offer for offer in result.offers}
            for contract in result.contracts:
                matched = [offers[key] for key in contract.matched_offer_keys if key in offers]
                key = (result.query.supplier, result.query.utility, result.query.commodity, contract.id)
                groups.setdefault(key, []).append((result, contract, matched))
        for key, observations in sorted(groups.items(), key=lambda item: (
                item[0][0].casefold(), item[0][2], item[0][1].casefold(), item[0][3])):
            result, contract, _ = observations[0]
            matched = [offer for _, _, offers in observations for offer in offers]
            zips = sorted({item.query.zip for item, _, _ in observations})
            prices = contract.fields.get("prices", [])
            first_price = prices[0] if prices else {}
            row = {
                "tps": result.query.supplier,
                "edc_gdc": result.query.utility,
                "commodity": result.query.commodity,
                "test_zip": zips[0],
                "observed_zip_codes": " | ".join(zips),
                "zip_count": len(zips),
                "observation_count": len(observations),
                "duplicate_status": "consolidated_across_zips" if len(zips) > 1 else ("repeated_observation" if len(observations) > 1 else "unique"),
                "contract_id": contract.id,
                "document_kind": contract.document_kind,
                "parse_status": contract.status,
                "media_type": contract.media_type,
                "matched_offer_count": len({offer_fingerprint(offer) for offer in matched}),
                "matched_offer_fingerprints": " | ".join(sorted({offer_fingerprint(offer) for offer in matched})),
                "matched_offer_keys": " | ".join(sorted({offer.key for offer in matched})),
                "matched_product_ids": " | ".join(sorted({offer.product_id for offer in matched if offer.product_id})),
                "matched_plan_names": " | ".join(sorted({offer.name for offer in matched})),
                "match_method": " | ".join(sorted({item.match_method for _, item, _ in observations if item.match_method})),
                "contract_rate": first_price.get("value"),
                "contract_rate_unit": first_price.get("unit"),
                "contract_rate_structure": contract.fields.get("rate_structure"),
                "contract_term_months": contract.fields.get("term_months"),
                "monthly_fee": contract.fields.get("monthly_fee"),
                "enrollment_fee": contract.fields.get("enrollment_fee"),
                "cancellation_fee": contract.fields.get("cancellation_fee"),
                "renewable_percentage": contract.fields.get("renewable_percentage"),
                "missing_section_count": len(contract.missing_sections),
                "missing_sections": " | ".join(contract.missing_sections),
                **contract.sections,
                "contract_url": contract.url,
                "source_urls": " | ".join(sorted({url for _, item, _ in observations for url in item.source_urls})),
                "warnings": " | ".join(sorted({warning for _, item, _ in observations for warning in item.warnings})),
            }
            writer.writerow(_reader_row(row, columns))


def write_offer_documents(results: list[CollectionResult], path: Path):
    """Write canonical many-to-many links between offers and documents."""
    columns = [
        "tps", "edc_gdc", "commodity", "test_zip", "observed_zip_codes", "observation_count",
        "duplicate_status", "offer_fingerprint", "offer_key", "source_offer_keys", "product_id", "plan_name",
        "rate", "rate_unit", "contract_id", "document_kind", "parse_status", "match_method",
        "contract_url",
    ]
    with path.open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, columns)
        writer.writeheader()
        groups = {}
        for result in results:
            if result.replayed or not result.live_data_verified:
                continue
            offers = {offer.key: offer for offer in result.offers}
            for contract in result.contracts:
                for key in contract.matched_offer_keys:
                    offer = offers.get(key)
                    if offer is None:
                        continue
                    fingerprint = offer_fingerprint(offer)
                    groups.setdefault((fingerprint, contract.id), []).append((result, offer, contract))
        for _, observations in sorted(groups.items(), key=lambda item: (
                item[1][0][1].supplier.casefold(), item[1][0][1].commodity,
                item[1][0][1].utility.casefold(), item[1][0][1].name.casefold(), item[0][1])):
            result, offer, contract = observations[0]
            zips = sorted({item.query.zip for item, _, _ in observations})
            row = {
                "tps": result.query.supplier,
                "edc_gdc": result.query.utility,
                "commodity": result.query.commodity,
                "test_zip": zips[0],
                "observed_zip_codes": " | ".join(zips),
                "observation_count": len(observations),
                "duplicate_status": "consolidated_across_zips" if len(zips) > 1 else ("repeated_observation" if len(observations) > 1 else "unique"),
                "offer_fingerprint": offer_fingerprint(offer),
                "offer_key": offer.key,
                "source_offer_keys": " | ".join(sorted({item.key for _, item, _ in observations})),
                "product_id": offer.product_id,
                "plan_name": offer.name,
                "rate": offer.price.value,
                "rate_unit": offer.price.unit,
                "contract_id": contract.id,
                "document_kind": contract.document_kind,
                "parse_status": contract.status,
                "match_method": contract.match_method,
                "contract_url": contract.url,
            }
            writer.writerow(_reader_row(row, columns))


def write_report(results: list[CollectionResult], root: Path):
    # The caller creates a unique directory; exclusive writes protect previous runs.
    with (root / "results.json").open("x", encoding="utf-8") as handle:
        json.dump([r.model_dump(mode="json") for r in results], handle, indent=2, ensure_ascii=False)
    columns = ["schema_version", "adapter_version", "replayed", "collection_method", "context_verified", "live_data_verified", "key", "offer_fingerprint", "supplier", "utility", "commodity", "zip", "name", "product_id", "rate", "rate_unit", "rate_structure",
               "term_months", "monthly_fee", "enrollment_fee", "cancellation_fee", "renewable_percentage",
               "term_kind", "intro_price", "intro_duration_months", "intro_duration_billing_cycles", "fee_terms",
               "renewable_source", "renewable_claim", "incentives", "contract_ids", "source_kind", "source_url", "artifact_id", "captured_at", "status", "warnings"]
    with (root / "offers.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, columns)
        writer.writeheader()
        for result in results:
            for offer in result.offers:
                data = offer.model_dump(mode="json")
                row = {col: data.get(col) for col in columns}
                row.update(rate=str(offer.price.value), rate_unit=offer.price.unit, status=result.status,
                           offer_fingerprint=offer_fingerprint(offer),
                           schema_version=result.schema_version, adapter_version=result.adapter_version,
                           replayed=result.replayed, collection_method=result.collection_method,
                           context_verified=result.context_verified, live_data_verified=result.live_data_verified,
                           warnings="; ".join(offer.warnings), incentives=" | ".join(offer.incentives),
                           contract_ids=";".join(offer.contract_ids))
                # Spreadsheet formula injection must not execute when the CSV is opened.
                writer.writerow({k: csv_safe(v) for k, v in row.items()})
    with (root / "contracts.csv").open("x", newline="", encoding="utf-8") as handle:
        columns = ["schema_version", "supplier", "utility", "commodity", "zip", "id", "document_kind", "status", "url", "matched_offer_keys", "match_method", "missing_sections", *LABELS, "fields", "warnings"]
        writer = csv.DictWriter(handle, columns)
        writer.writeheader()
        for result in results:
            for contract in result.contracts:
                data = {**contract.model_dump(mode="json"), **contract.sections,
                        "schema_version": result.schema_version, "supplier": result.query.supplier, "utility": result.query.utility,
                        "commodity": result.query.commodity, "zip": result.query.zip}
                writer.writerow({k: csv_safe(data.get(k)) for k in columns})
    with (root / "coverage.csv").open("x", newline="", encoding="utf-8-sig") as handle:
        columns = ["market_key", "supplier", "utility", "commodity", "zip", "adapter", "status", "method", "context_verified", "live_data_verified", "source_offer_count", "offers", "candidates", "documents",
                   "attempts", "completion_issues", "resolution_type", "retryable", "next_action", "warnings", "errors"]
        writer = csv.DictWriter(handle, columns)
        writer.writeheader()
        for result in results:
            remediation = (CONFIG.get("remediation", {}).get(result.query.supplier, {})
                           if result.status in {"blocked", "unsupported", "empty", "failed"} else {})
            data = {**result.query.model_dump(), "status": result.status, "method": result.collection_method,
                    "market_key": f"{result.query.supplier}|{result.query.utility}|{result.query.commodity}",
                    "context_verified": result.context_verified, "live_data_verified": result.live_data_verified,
                    "source_offer_count": result.source_offer_count,
                    "offers": len(result.offers), "candidates": len(result.candidates), "documents": len(result.contracts),
                    "attempts": json.dumps(result.attempts, ensure_ascii=False, sort_keys=True),
                    "completion_issues": " | ".join(result.completion_issues),
                    "resolution_type": remediation.get("resolution_type"),
                    "retryable": remediation.get("retryable"),
                    "next_action": remediation.get("next_action"),
                    "warnings": " | ".join(result.warnings),
                    "errors": " | ".join(f'{error.get("category", "error")}: {error.get("message", "")}' for error in result.errors)}
            writer.writerow(_reader_row(data, columns))
    write_offer_prices(results, root / "offer_prices.csv")
    write_offer_observations(results, root / "offer_observations.csv")
    write_contract_information(results, root / "contract_information.csv")
    write_offer_documents(results, root / "offer_documents.csv")
    write_compiled_offerings(results, root / "compiled_offerings.csv")
    quality_exports = [
        ("offer_completeness.csv", offer_completeness_rows(results),
         ["market_key", "supplier", "utility", "commodity", "zip", "offer_key", "plan_name", "core_complete", "missing_core_fields", "unreported_conditional_fields", "warning_count"]),
        ("contract_completeness.csv", contract_completeness_rows(results),
         ["market_key", "supplier", "utility", "commodity", "zip", "contract_id", "document_kind", "parse_status", "required_section_count", "present_section_count", "missing_section_count", "missing_sections", "derived_distribution_context", "warning_count"]),
        ("document_associations.csv", document_association_rows(results),
         ["market_key", "supplier", "utility", "commodity", "zip", "offer_key", "plan_name", "linked_document_count", "contract_summary_count", "association_status", "association_scope", "contract_ids"]),
        ("plan_count_reconciliation.csv", plan_count_rows(results),
         ["market_key", "supplier", "utility", "commodity", "zip", "source_offer_count", "exported_offer_count", "count_status", "difference"]),
        ("completed_coverage.csv", completed_coverage_rows(results),
         ["utility", "commodity", "completed_supplier_count", "completed_suppliers", "live_supplier_count", "live_suppliers", "target", "remaining_to_target"]),
        ("scraper_alerts.csv", alert_rows(results),
         ["market_key", "supplier", "utility", "commodity", "zip", "severity", "alert_code", "detail"]),
        ("reproducibility.csv", reproducibility_rows(results),
         ["market_key", "supplier", "utility", "commodity", "zip", "run_count", "reproducibility_status", "offer_counts"]),
    ]
    for filename, rows, export_columns in quality_exports:
        write_rows(root / filename, rows, export_columns)
    lines = ["# Collection report", "", "This report distinguishes collected candidates from verified offers. See results.json for evidence and errors.", "",
             "| Supplier | Utility | ZIP | Status | Live ZIP data | Method | Offers | Candidates | Contracts |", "|---|---|---|---|---|---|---:|---:|---:|"]
    for result in results:
        lines.append(f"| {result.query.supplier} | {result.query.utility} | {result.query.zip} | {result.status} | {result.live_data_verified} | {result.collection_method} | {len(result.offers)} | {len(result.candidates)} | {len(result.contracts)} |")
    completed = sum(result.status == "success" and not result.replayed for result in results)
    count_matches = sum(row["count_status"] == "match" for row in plan_count_rows(results))
    association_gaps = sum(row["association_status"] != "complete" for row in document_association_rows(results))
    lines.extend([
        "", "## Completion summary", "",
        f"- Strictly completed live markets: {completed} of {len(results)}.",
        f"- Source/export plan counts reconciled: {count_matches} of {len(results)}.",
        f"- Offers with missing or ambiguous contract-summary associations: {association_gaps}.",
        "- Detailed quality views: `offer_completeness.csv`, `contract_completeness.csv`, `document_associations.csv`, `plan_count_reconciliation.csv`, `completed_coverage.csv`, `scraper_alerts.csv`, and `reproducibility.csv`.",
    ])
    for result in results:
        lines.extend(["", f"## {result.query.supplier} / {result.query.utility} / {result.query.zip}", ""])
        if result.replayed:
            lines.append("Offline replay of saved evidence. This is not a fresh market quote.")
        lines.extend("- " + warning.replace("\n", " ") for warning in result.warnings)
        lines.extend("- " + error.get("category", "error") + ": " + error.get("message", "").replace("\n", " ") for error in result.errors)
        for offer in result.offers:
            lines.extend(f"- {offer.name}: {warning}" for warning in offer.warnings)
        for contract in result.contracts:
            if contract.warnings:
                lines.append(f"- Document {contract.id[:12]} ({contract.document_kind}): " + "; ".join(contract.warnings))
    (root / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_report(root: Path) -> list[str]:
    errors = []
    data = json.loads((root / "results.json").read_text(encoding="utf-8"))
    for item in data:
        result = CollectionResult.model_validate(item)
        artifacts = {a["id"]: a for a in result.artifacts}
        artifact_root = root / slug(result.query) / "artifacts"
        for artifact in result.artifacts:
            path = (artifact_root / artifact["path"]).resolve()
            if path.parent != artifact_root.resolve() or not path.is_file():
                errors.append("Missing/invalid artifact: " + artifact["id"])
            elif hashlib.sha256(path.read_bytes()).hexdigest() != artifact["id"]:
                errors.append("Artifact hash mismatch: " + artifact["id"])
        for offer in result.offers:
            if offer.artifact_id not in artifacts:
                errors.append("Offer lacks artifact: " + offer.key)
            if any(cid not in {c.id for c in result.contracts} for cid in offer.contract_ids):
                errors.append("Offer references missing contract: " + offer.key)
            for cid in offer.contract_ids:
                contract = next((c for c in result.contracts if c.id == cid), None)
                if contract and offer.key not in contract.matched_offer_keys:
                    errors.append("Offer/contract link is not bidirectional: " + offer.key + " -> " + cid)
        for contract in result.contracts:
            if contract.artifact_id not in artifacts:
                errors.append("Contract lacks artifact: " + contract.id)
            if any(key not in {o.key for o in result.offers} for key in contract.matched_offer_keys):
                errors.append("Contract references missing offer: " + contract.id)
            for key in contract.matched_offer_keys:
                offer = next((o for o in result.offers if o.key == key), None)
                if offer and contract.id not in offer.contract_ids:
                    errors.append("Contract/offer link is not bidirectional: " + contract.id + " -> " + key)
    return errors


def slug(query) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9_-]", "_", f"{query.supplier}__{query.utility}__{query.zip}")
