from decimal import Decimal

from nj_switch.models import CollectionResult, Contract, DocumentRef, Offer, Price, Query
from nj_switch.quality import (
    alert_rows,
    completed_coverage_rows,
    contract_completeness_rows,
    document_association_rows,
    offer_completeness_rows,
    plan_count_rows,
    reproducibility_rows,
)


def _result(*, supplier="Test Supplier", utility="PSE&G Electric", status="success",
            source_offer_count=1, offers=None, contracts=None, zip_code="07102"):
    query = Query(
        supplier=supplier, utility=utility, commodity="electric", zip=zip_code,
        url="https://example.com/plans", adapter="test",
    )
    return CollectionResult(
        query=query, status=status, context_verified=True, live_data_verified=True,
        source_offer_count=source_offer_count, offers=offers or [],
        contracts=contracts or [],
    )


def _offer(*, key="offer-1", product_id="P-1", name="Fixed 12", documents=None):
    return Offer(
        key=key, supplier="Test Supplier", utility="PSE&G Electric", commodity="electric",
        zip="07102", name=name, product_id=product_id,
        price=Price(value=Decimal("0.15"), unit="USD/kWh", raw="$0.15/kWh"),
        rate_structure="fixed", term_months=12, source_url="https://example.com/plans",
        source_kind="html", artifact_id="html-1", documents=documents or [],
    )


def test_offer_completeness_separates_core_and_conditional_fields():
    rows = offer_completeness_rows([_result(offers=[_offer()])])
    assert rows[0]["core_complete"]
    assert "monthly_fee" in rows[0]["unreported_conditional_fields"]


def test_contract_completeness_reports_missing_sections():
    contract = Contract(id="c1", url="https://example.com/c1", artifact_id="a1", media_type="application/pdf")
    rows = contract_completeness_rows([_result(contracts=[contract])])
    assert rows[0]["missing_section_count"] == len(contract.missing_sections)
    assert rows[0]["parse_status"] == "needs_review"


def test_document_association_requires_offer_link_or_market_document():
    rows = document_association_rows([_result(offers=[_offer()])])
    assert rows[0]["association_status"] == "missing_useful_document"
    assert rows[0]["association_scope"] == "none"


def test_document_association_accepts_stable_offer_link():
    ref = DocumentRef(url="https://example.com/c1", offer_key="offer-1")
    contract = Contract(
        id="c1", url=ref.url, artifact_id="a1", media_type="application/pdf", status="parsed",
        document_kind="contract_summary", matched_offer_keys=["offer-1"],
    )
    rows = document_association_rows([_result(offers=[_offer(documents=[ref])], contracts=[contract])])
    assert rows[0]["association_status"] == "complete"
    assert rows[0]["association_scope"] == "offer"


def test_plan_count_rows_marks_match_mismatch_and_unavailable():
    offer = _offer()
    assert plan_count_rows([_result(offers=[offer], source_offer_count=1)])[0]["count_status"] == "match"
    assert plan_count_rows([_result(offers=[offer], source_offer_count=2)])[0]["count_status"] == "mismatch"
    assert plan_count_rows([_result(offers=[offer], source_offer_count=None)])[0]["count_status"] == "unavailable"


def test_completed_coverage_excludes_partial_and_replayed_rows():
    success = _result(offers=[_offer()])
    partial = _result(status="partial", supplier="Partial Supplier", offers=[_offer()])
    replay = _result(supplier="Replay Supplier", offers=[_offer()])
    replay.replayed = True
    rows = completed_coverage_rows([success, partial, replay])
    assert rows[0]["completed_supplier_count"] == 1
    assert rows[0]["completed_suppliers"] == "Test Supplier"


def test_alerts_flag_plan_count_mismatch_as_critical():
    result = _result(offers=[_offer()], source_offer_count=2)
    alerts = alert_rows([result])
    assert any(row["alert_code"] == "plan_count_mismatch" and row["severity"] == "critical" for row in alerts)


def test_alerts_do_not_flag_verified_empty_market_as_live_zero_offers():
    result = _result(status="empty", source_offer_count=0, offers=[])
    alerts = alert_rows([result])
    assert not any(row["alert_code"] == "live_zero_offers" for row in alerts)


def test_reproducibility_rows_match_identical_runs():
    first = _result(offers=[_offer()])
    second = _result(offers=[_offer()])
    row = reproducibility_rows([first, second])[0]
    assert row["reproducibility_status"] == "match"
    assert row["run_count"] == 2


def test_reproducibility_rows_detect_changed_product_identity():
    first = _result(offers=[_offer(product_id="P-1")])
    second = _result(offers=[_offer(product_id="P-2")])
    assert reproducibility_rows([first, second])[0]["reproducibility_status"] == "changed"
