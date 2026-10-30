import io
from decimal import Decimal

from docx import Document

from nj_switch.contracts import LABELS, extract_contract, match_contract, sections_from_rows
from nj_switch.models import DocumentRef
from nj_switch.offers import parse_html


SUMMARY = """Third Party Supplier Information: Example Energy, license ESL-0000
Price Structure: Fixed
Generation/Supply Price: $0.2000/kWh. Monthly fee: $4.95
Statement Regarding Savings: Savings are not guaranteed.
Amount of time required to change: One billing cycle.
Incentives: $50 gift card after three paid bills.
Right to Cancel/Rescind: Seven calendar days from the confirmation notice.
Contract Start Date: Next eligible meter read.
Contract Term/Length: 12 months
Cancellation/Early Termination Fees: $150. See conditions.
Renewal Terms: Variable after expiry unless a new fixed plan is selected.
Distribution Company Information: PSE&G Electric; call the utility for outages.
"""


def test_all_sections_and_evidence():
    contract = extract_contract(SUMMARY.encode(), "https://example.com/contract", "hash")
    assert contract.status == "parsed"
    assert set(contract.sections) == set(LABELS)
    assert contract.fields["term_months"] == 12
    assert contract.fields["rate_structure"] == "fixed"
    assert contract.fields["prices"][0]["unit"] == "USD/kWh"
    assert "Variable after expiry" in contract.sections["renewal"]
    assert contract.raw_text


def test_docx_table_preserved():
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Price Structure"
    table.rows[0].cells[1].text = "Variable; ceiling $0.25/kWh"
    buf = io.BytesIO()
    doc.save(buf)
    result = extract_contract(buf.getvalue(), "https://example.com/doc", "hash")
    assert result.sections["price_structure"] == "Variable; ceiling $0.25/kWh"
    assert result.status == "partial"


def test_html_table():
    data = b'<table><tr><td>Generation/Supply Price</td><td>$1.20/therm</td></tr></table>'
    result = extract_contract(data, "https://example.com/doc", "hash")
    assert result.fields["prices"][0]["unit"] == "USD/therm"


def test_cleansky_contract_summary_label_variants():
    data = b"""Energy Charge: 72.10 cents per Therm
Switch back to Utility/TPS: One full billing cycle.
Contract Term/Length: 6 months
"""
    result = extract_contract(data, "https://example.com/clean-sky-summary", "hash")
    assert "72.10 cents per Therm" in result.sections["supply_price"]
    assert "One full billing cycle" in result.sections["switching_time"]
    assert result.fields["prices"][0]["unit"] == "USD/therm"


def test_xoom_multiline_switching_time_label():
    data = b"""Time required to change from
TPS back to default service or One to two billing cycles.
to another TPS
Incentives Not Applicable
"""
    result = extract_contract(data, "https://example.com/xoom-summary", "hash")
    assert "One to two billing cycles" in result.sections["switching_time"]


def test_empty_document_requires_review():
    assert extract_contract(b"", "https://example.com/doc", "hash").status == "needs_review"


def test_exact_link_match(query):
    offer = parse_html('<div class="product-card plan__wrapper"><h2>Plan</h2>$0.2000/kWh 12 months Fixed</div>', query, query.url, "a")[0]
    contract = extract_contract(SUMMARY.encode(), "https://example.com/doc", "hash")
    match_contract(contract, [DocumentRef(url=contract.url, offer_key=offer.key)], [offer])
    assert offer.contract_ids == ["hash"]
    assert contract.matched_offer_keys == [offer.key]


def test_contract_supplies_missing_offer_rate_structure(query):
    offer = parse_html(
        '<div class="product-card plan__wrapper"><h2>Plan</h2>$0.2000/kWh 12 months</div>',
        query,
        query.url,
        "a",
    )[0]
    assert offer.rate_structure is None
    contract = extract_contract(SUMMARY.encode(), "https://example.com/doc", "hash")
    match_contract(contract, [DocumentRef(url=contract.url, offer_key=offer.key)], [offer])
    assert offer.rate_structure == "fixed"
    assert "Rate structure not explicitly established" not in offer.warnings


def test_contract_price_allows_card_display_rounding(query):
    offer = parse_html(
        '<div class="product-card plan__wrapper"><h2>Plan</h2>$0.8490/therm 12 months Fixed</div>',
        query.model_copy(update={"commodity": "gas", "utility": "PSE&G Gas"}),
        query.url,
        "a",
    )[0]
    summary = SUMMARY.replace("$0.2000/kWh", "$0.8489/therm").replace(
        "PSE&G Electric", "PSE&G Gas"
    )
    contract = extract_contract(summary.encode(), "https://example.com/doc", "hash")
    match_contract(contract, [DocumentRef(url=contract.url, offer_key=offer.key)], [offer])
    assert "Contract price differs from offer price; review both sources" not in offer.warnings


def test_commodity_conflict(query):
    offer = parse_html('<div class="product-card plan__wrapper"><h2>Plan</h2>$0.20/kWh 12 months</div>', query, query.url, "a")[0]
    contract = extract_contract(SUMMARY.replace("$0.2000/kWh", "$1.2/therm").encode(), "https://example.com/doc", "hash")
    match_contract(contract, [DocumentRef(url=contract.url, offer_key=offer.key)], [offer])
    assert not contract.matched_offer_keys
    assert any("Commodity conflict" in w for w in contract.warnings)

