"""Deterministic quality views for live scraper results."""
from __future__ import annotations

from collections import defaultdict

from .contracts import LABELS
from .models import CollectionResult


CORE_OFFER_FIELDS = (
    "supplier", "utility", "commodity", "zip", "name", "price", "rate_structure",
    "source_url", "source_kind", "artifact_id", "captured_at",
)
CONDITIONAL_OFFER_FIELDS = (
    "product_id", "term_months", "term_kind", "monthly_fee", "enrollment_fee",
    "cancellation_fee", "renewable_percentage", "renewable_source", "renewable_claim",
)


def _present(value) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def offer_completeness_rows(results: list[CollectionResult]) -> list[dict]:
    rows = []
    for result in results:
        for offer in result.offers:
            missing_core = [field for field in CORE_OFFER_FIELDS if not _present(getattr(offer, field))]
            unreported = [field for field in CONDITIONAL_OFFER_FIELDS if not _present(getattr(offer, field))]
            rows.append({
                "market_key": f"{offer.supplier}|{offer.utility}|{offer.commodity}",
                "supplier": offer.supplier, "utility": offer.utility, "commodity": offer.commodity,
                "zip": offer.zip, "offer_key": offer.key, "plan_name": offer.name,
                "core_complete": not missing_core, "missing_core_fields": " | ".join(missing_core),
                "unreported_conditional_fields": " | ".join(unreported),
                "warning_count": len(offer.warnings),
            })
    return rows


def contract_completeness_rows(results: list[CollectionResult]) -> list[dict]:
    rows = []
    for result in results:
        for contract in result.contracts:
            rows.append({
                "market_key": f"{result.query.supplier}|{result.query.utility}|{result.query.commodity}",
                "supplier": result.query.supplier, "utility": result.query.utility,
                "commodity": result.query.commodity, "zip": result.query.zip,
                "contract_id": contract.id, "document_kind": contract.document_kind,
                "parse_status": contract.status, "required_section_count": len(LABELS),
                "present_section_count": len(set(LABELS) & set(contract.sections)),
                "missing_section_count": len(contract.missing_sections),
                "missing_sections": " | ".join(contract.missing_sections),
                "derived_distribution_context": contract.sections.get("distribution_company", "").startswith("Verified collection context:"),
                "warning_count": len(contract.warnings),
            })
    return rows


def document_association_rows(results: list[CollectionResult]) -> list[dict]:
    rows = []
    for result in results:
        market_documents = [
            contract for contract in result.contracts
            if contract.match_method == "market_level_public_document" and
            contract.status in ("parsed", "text_extracted", "retained")
        ]
        for offer in result.offers:
            linked = [contract for contract in result.contracts if offer.key in contract.matched_offer_keys]
            summaries = [contract for contract in linked if contract.document_kind == "contract_summary"]
            useful = [contract for contract in linked if contract.status in ("parsed", "text_extracted", "retained")]
            status = (
                "ambiguous_summaries" if len(summaries) > 1 else
                "complete" if len(summaries) == 1 or useful or market_documents else
                "missing_useful_document"
            )
            scope = "offer" if linked else "market" if market_documents else "none"
            rows.append({
                "market_key": f"{offer.supplier}|{offer.utility}|{offer.commodity}",
                "supplier": offer.supplier, "utility": offer.utility, "commodity": offer.commodity,
                "zip": offer.zip, "offer_key": offer.key, "plan_name": offer.name,
                "linked_document_count": len(linked), "contract_summary_count": len(summaries),
                "association_status": status, "association_scope": scope,
                "contract_ids": " | ".join(sorted(contract.id for contract in linked)),
            })
    return rows


def plan_count_rows(results: list[CollectionResult]) -> list[dict]:
    rows = []
    for result in results:
        exported = len(result.offers)
        source = result.source_offer_count
        status = "unavailable" if source is None else "match" if source == exported else "mismatch"
        rows.append({
            "market_key": f"{result.query.supplier}|{result.query.utility}|{result.query.commodity}",
            "supplier": result.query.supplier, "utility": result.query.utility,
            "commodity": result.query.commodity, "zip": result.query.zip,
            "source_offer_count": source, "exported_offer_count": exported,
            "count_status": status, "difference": "" if source is None else exported - source,
        })
    return rows


def completed_coverage_rows(results: list[CollectionResult]) -> list[dict]:
    grouped = defaultdict(list)
    for result in results:
        grouped[(result.query.utility, result.query.commodity)].append(result)
    rows = []
    for (utility, commodity), items in sorted(grouped.items()):
        completed = sorted({item.query.supplier for item in items if item.status == "success" and not item.replayed})
        live = sorted({item.query.supplier for item in items if item.live_data_verified and item.offers and not item.replayed})
        rows.append({
            "utility": utility, "commodity": commodity,
            "completed_supplier_count": len(completed), "completed_suppliers": " | ".join(completed),
            "live_supplier_count": len(live), "live_suppliers": " | ".join(live),
            "target": 10, "remaining_to_target": max(0, 10 - len(completed)),
        })
    return rows


def alert_rows(results: list[CollectionResult]) -> list[dict]:
    rows = []
    for result in results:
        base = {
            "market_key": f"{result.query.supplier}|{result.query.utility}|{result.query.commodity}",
            "supplier": result.query.supplier, "utility": result.query.utility,
            "commodity": result.query.commodity, "zip": result.query.zip,
        }
        alerts = []
        if result.status != "success":
            alerts.append(("warning", "not_completed", f"status={result.status}"))
        if result.live_data_verified and not result.offers and result.status not in {"empty", "unsupported"}:
            alerts.append(("critical", "live_zero_offers", "Live-qualified collection returned zero offers"))
        if result.source_offer_count is not None and result.source_offer_count != len(result.offers):
            alerts.append(("critical", "plan_count_mismatch", f"source={result.source_offer_count}; exported={len(result.offers)}"))
        for issue in result.completion_issues:
            alerts.append(("critical", "completion_integrity_issue", issue))
        missing = sum(row["association_status"] != "complete" for row in document_association_rows([result]))
        if missing:
            alerts.append(("warning", "document_association_gap", f"offers_with_gap={missing}"))
        for severity, code, detail in alerts:
            rows.append({**base, "severity": severity, "alert_code": code, "detail": detail})
    return rows


def _offer_identity(result: CollectionResult) -> set[tuple]:
    return {
        (offer.product_id or offer.name.casefold(), str(offer.price.value), offer.price.unit,
         offer.term_months, offer.rate_structure)
        for offer in result.offers
    }


def reproducibility_rows(results: list[CollectionResult]) -> list[dict]:
    grouped = defaultdict(list)
    for result in results:
        grouped[(result.query.supplier, result.query.utility, result.query.commodity, result.query.zip)].append(result)
    rows = []
    for key, items in sorted(grouped.items()):
        identities = [_offer_identity(item) for item in items]
        status = "insufficient_history" if len(items) < 2 else "match" if all(value == identities[0] for value in identities[1:]) else "changed"
        rows.append({
            "market_key": "|".join(key[:3]), "supplier": key[0], "utility": key[1],
            "commodity": key[2], "zip": key[3], "run_count": len(items),
            "reproducibility_status": status,
            "offer_counts": " | ".join(str(len(item.offers)) for item in items),
        })
    return rows
