import json
from pathlib import Path
from unittest.mock import MagicMock

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from nj_switch.navigation import (NavigationResult, capture_indra_terms,
                                  classify_indra_terms_state,
                                  indra_terms_url_valid)
from nj_switch.pipeline import replay


FIXTURE = Path(__file__).parent / "fixtures" / "observed" / "indra_pseg_electric_20261013.json"


def _fixture_with_fragment(tmp_path, *, product_id, document_url):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["fragments"] = [{
        "origin": "",
        "html": f'<a href="{document_url}">Terms and Conditions PDF</a>',
        "url": "https://indraenergy.com/signup/?zip=07102",
        "product_id": product_id,
    }]
    data["documents"] = [{
        "url": document_url,
        "text": "Indra Energy residential terms and conditions for the selected current plan.",
    }]
    output = tmp_path / "indra-document-fixture.json"
    output.write_text(json.dumps(data), encoding="utf-8")
    return output


def test_indra_generated_terms_bind_by_rate_code(tmp_path):
    product_id = "PSEG-ELE_NA_INTMONOCTR_02_ALL_DSC_N100_XX|72920"
    document_url = "https://indraenergy.com/wp-content/uploads/terms/pseg-variable.pdf"
    fixture = _fixture_with_fragment(
        tmp_path, product_id=product_id, document_url=document_url
    )

    result = replay(fixture, tmp_path / "run")

    matched = next(offer for offer in result.offers if offer.product_id == product_id)
    assert matched.contract_ids
    contract = next(item for item in result.contracts if item.id in matched.contract_ids)
    assert contract.url == document_url
    assert contract.matched_offer_keys == [matched.key]
    assert contract.match_method == "document_link_on_offer"


def test_indra_generated_terms_reject_unknown_rate_code(tmp_path):
    fixture = _fixture_with_fragment(
        tmp_path,
        product_id="NOT-A-CURRENT-RATE-CODE",
        document_url="https://indraenergy.com/wp-content/uploads/terms/unknown.pdf",
    )

    result = replay(fixture, tmp_path / "run")

    assert len(result.contracts) == 1
    assert result.contracts[0].matched_offer_keys == []
    assert all(not offer.contract_ids for offer in result.offers)


def test_indra_terms_url_requires_supplier_owned_https_route():
    assert indra_terms_url_valid(
        "https://indraenergy.com/wp-content/uploads/terms/current.pdf"
    )
    assert indra_terms_url_valid("https://documents.indraenergy.com/terms/current")
    assert not indra_terms_url_valid("http://indraenergy.com/terms/current.pdf")
    assert not indra_terms_url_valid("https://foreign.example/terms/current.pdf")


def test_indra_modal_state_classifies_identity_error_and_document():
    assert classify_indra_terms_state({}, set())[0] == "missing_product_identity"
    assert classify_indra_terms_state({"productId": "RATE-1"}, {"RATE-1"})[0] == "duplicate_product_identity"
    assert classify_indra_terms_state({"productId": "RATE-1", "error": "unavailable"}, set())[0] == "terms_service_error"
    assert classify_indra_terms_state({"productId": "RATE-1"}, set())[0] == "no_document_url"
    assert classify_indra_terms_state({
        "productId": "RATE-1", "pdfUrl": "https://foreign.example/terms.pdf",
    }, set())[0] == "invalid_document_url"
    assert classify_indra_terms_state({
        "productId": "RATE-1", "pdfUrl": "https://indraenergy.com/terms/current.pdf",
    }, set())[0] == "document"


def test_indra_terms_generation_retries_once_then_preserves_rate_code():
    page = MagicMock()
    controller = MagicMock()
    button = MagicMock()
    modal = MagicMock()
    page.locator.return_value = modal
    page.wait_for_function.side_effect = [PlaywrightTimeoutError("slow"), None]
    controller.evaluate.side_effect = [
        {"productId": "RATE-1", "pdfUrl": "", "error": "unable to load"},
        {"productId": "RATE-1", "pdfUrl": "https://indraenergy.com/terms/current.pdf", "error": ""},
    ]
    result = NavigationResult(url="https://indraenergy.com/signup/?zip=07102")
    seen = set()

    capture_indra_terms(page, controller, button, result, 0, seen)

    assert button.click.call_count == 2
    assert seen == {"RATE-1"}
    assert result.fragments[0]["product_id"] == "RATE-1"
    assert "https://indraenergy.com/terms/current.pdf" in result.fragments[0]["html"]
