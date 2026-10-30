import json
from pathlib import Path
import pytest

from nj_switch.cli import (browser_plan, browser_state_key, direct_retry_indexes,
                           direct_retry_is_substantive, main, select_direct_retry)
from nj_switch.contracts import extract_contract
from nj_switch.evidence import ArtifactStore
from nj_switch.models import CollectionResult, Contract, DocumentRef, Query
from nj_switch.pipeline import (NRG_PRODUCT_CHART_URL, add_contract, assemble,
                                browser_context_options, finalize,
                                bind_document_refs, fetch_direct_public_api,
                                exhausted_document_host_network_failure,
                                finalize_indra_document_access,
                                nextera_document_product_id, replay,
                                nrg_product_request_evidence,
                                record_document_download_failure,
                                terminal_document_host_failure,
                                resolve_direct_renewable_conflicts,
                                scope_nextera_offer_documents,
                                scoped_document_refs)
from nj_switch.transport import AccessError
from nj_switch.quality import alert_rows, document_association_rows
from nj_switch.reporting import (slug, verify_report, write_offer_observations,
                                 write_offer_prices, write_report)
from nj_switch.navigation import (STRATEGIES, NavigationError, NavigationResult, access_failure,
                                  capture_nextera_details, nextera_detail_has_document,
                                  direct_displayed_plan_count, nextera_plan_identities,
                                  reconcile_direct_plan_counts,
                                  recover_njgande_gateway,
                                  submit_nextera_zip, wait_for_provider_options,
                                  wait_for_xoom_results)
from nj_switch.profiles import (direct_document_url_valid, direct_energy,
                                direct_energy_diagnostics)
from nj_switch.registry import load_registry, utility_matches

FIXTURE = Path(__file__).parent / "fixtures/manual_demo.json"
DIRECT_FIXTURE = Path(__file__).parent / "fixtures/observed/direct_energy_electric.json"


def _indra_result():
    return CollectionResult(query=Query(
        supplier="Indra Energy", utility="PSE&G Electric", commodity="electric",
        zip="07102", url="https://indraenergy.com/signup/", adapter="indra_energy",
    ))


def test_indra_robots_block_is_structured_and_nonretryable():
    result = _indra_result()
    url = "https://indraenergy.com/wp-content/uploads/terms/current.pdf"

    record_document_download_failure(
        result, url, AccessError("Source robots policy disallows this URL")
    )

    evidence = result.source_evidence["indra_terms"]
    assert evidence["automated_document_access"] == "disallowed_by_source_robots_policy"
    assert evidence["document_access_retryable"] is False
    assert evidence["policy_blocked_urls"] == [url]
    assert result.errors[0]["category"] == "document_download"


def test_indra_document_access_summary_rejects_source_absence_exception():
    result = _indra_result()
    url = "https://indraenergy.com/wp-content/uploads/terms/current.pdf"
    refs = [DocumentRef(url=url, product_id="RATE-1")]
    record_document_download_failure(
        result, url, AccessError("Source robots policy disallows this URL")
    )

    finalize_indra_document_access(result, refs)

    evidence = result.source_evidence["indra_terms"]
    assert evidence["discovered_document_count"] == 1
    assert evidence["downloaded_document_count"] == 0
    assert evidence["policy_blocked_document_count"] == 1
    assert evidence["document_access_state"] == "all_discovered_documents_policy_blocked"
    assert evidence["source_absence_rule_applicable"] is False


def test_nonpolicy_document_failure_is_not_misclassified():
    result = _indra_result()
    url = "https://indraenergy.com/wp-content/uploads/terms/current.pdf"

    record_document_download_failure(result, url, RuntimeError("connection reset"))
    finalize_indra_document_access(result, [DocumentRef(url=url, product_id="RATE-1")])

    evidence = result.source_evidence["indra_terms"]
    assert "automated_document_access" not in evidence
    assert evidence["document_access_state"] == "document_access_incomplete"
    assert evidence["source_absence_rule_applicable"] is False


def test_only_terminal_tls_trust_failures_stop_same_host_document_retries():
    assert terminal_document_host_failure(RuntimeError(
        "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate"
    ))
    assert not terminal_document_host_failure(RuntimeError("connection reset"))
    assert not terminal_document_host_failure(RuntimeError("HTTP 503 fetching public resource"))


def test_exhausted_network_failure_stops_repeating_same_document_host():
    assert exhausted_document_host_network_failure(
        RuntimeError("ConnectError: getaddrinfo failed")
    )
    assert exhausted_document_host_network_failure(
        RuntimeError("ReadTimeout while fetching public resource")
    )
    assert not exhausted_document_host_network_failure(
        RuntimeError("HTTP 503 fetching public resource")
    )


def test_indra_no_discovered_documents_still_requires_source_absence_evidence():
    result = _indra_result()

    finalize_indra_document_access(result, [])

    evidence = result.source_evidence["indra_terms"]
    assert evidence["discovered_document_count"] == 0
    assert evidence["document_access_state"] == "no_documents_discovered"
    assert evidence["source_absence_rule_applicable"] is False
    assert evidence["source_absence_evidence_required"] is True


class _RecordedDirectTransport:
    def __init__(self, *, content_type="application/json"):
        capture = json.loads(DIRECT_FIXTURE.read_text(encoding="utf-8"))
        self.payloads = [
            item for item in capture["payloads"]
            if "get-utilities-by-zip" in item["url"] or item["url"].endswith("/products")
        ]
        self.content_type = content_type

    def request(self, url, browser_context=None, method="GET", body=None):
        matches = [item for item in self.payloads if item["url"] == url]
        if method == "POST":
            matches = [
                item for item in matches
                if body.get("utilityCode") in {
                    product.get("utilityCode")
                    for product in item.get("body", {}).get("affiliateOfferList", [])
                }
            ]
        payload = matches[-1]["body"]
        return json.dumps(payload).encode(), self.content_type, url


def test_replay_and_verify(tmp_path):
    result = replay(FIXTURE, tmp_path / "Example_Energy__PSE_G_Electric__07102")
    assert result.status == "success"
    assert len(result.offers) == len(result.contracts) == 1
    assert result.source_offer_count == 1
    assert result.offers[0].contract_ids
    write_report([result], tmp_path)
    import csv
    with (tmp_path / "compiled_offerings.csv").open(encoding="utf-8-sig", newline="") as handle:
        compiled = list(csv.DictReader(handle))
    assert compiled == []
    with (tmp_path / "offer_prices.csv").open(encoding="utf-8-sig", newline="") as handle:
        offer_prices = list(csv.DictReader(handle))
    with (tmp_path / "contract_information.csv").open(encoding="utf-8-sig", newline="") as handle:
        contract_information = list(csv.DictReader(handle))
    with (tmp_path / "offer_documents.csv").open(encoding="utf-8-sig", newline="") as handle:
        offer_documents = list(csv.DictReader(handle))
    with (tmp_path / "offer_observations.csv").open(encoding="utf-8-sig", newline="") as handle:
        offer_observations = list(csv.DictReader(handle))
    with (tmp_path / "coverage.csv").open(encoding="utf-8-sig", newline="") as handle:
        coverage = list(csv.DictReader(handle))
    assert offer_prices == compiled
    assert contract_information == []
    assert offer_documents == []
    assert coverage[0]["adapter"] == "direct_energy"
    assert coverage[0]["completion_issues"] == ""
    assert offer_observations == []
    for filename in ("offer_prices.csv", "offer_observations.csv", "contract_information.csv", "offer_documents.csv", "coverage.csv"):
        rows = (tmp_path / filename).read_text(encoding="utf-8-sig").splitlines()
        expected = {"offer_prices.csv": 1, "offer_observations.csv": 1, "contract_information.csv": 1,
                    "offer_documents.csv": 1, "coverage.csv": 2}[filename]
        assert len(rows) == expected
    quality_files = {
        "offer_completeness.csv", "contract_completeness.csv", "document_associations.csv",
        "plan_count_reconciliation.csv", "completed_coverage.csv", "scraper_alerts.csv",
        "reproducibility.csv",
    }
    assert all((tmp_path / filename).is_file() for filename in quality_files)
    with (tmp_path / "plan_count_reconciliation.csv").open(encoding="utf-8-sig", newline="") as handle:
        reconciliation = list(csv.DictReader(handle))
    assert reconciliation[0]["count_status"] == "match"
    with (tmp_path / "document_associations.csv").open(encoding="utf-8-sig", newline="") as handle:
        associations = list(csv.DictReader(handle))
    assert associations[0]["association_status"] == "complete"
    with (tmp_path / "reproducibility.csv").open(encoding="utf-8-sig", newline="") as handle:
        reproducibility = list(csv.DictReader(handle))
    assert reproducibility[0]["reproducibility_status"] == "insufficient_history"
    assert "## Completion summary" in (tmp_path / "report.md").read_text(encoding="utf-8")
    assert verify_report(tmp_path) == []
    artifact = next((tmp_path / slug(result.query) / "artifacts").iterdir())
    artifact.write_text("tampered", encoding="utf-8")
    assert any("hash mismatch" in error for error in verify_report(tmp_path))


def test_cli_replay(tmp_path):
    assert main(["replay", str(FIXTURE), "--output", str(tmp_path / "run")]) == 0
    assert main(["verify", str(tmp_path / "run")]) == 0


def test_cleanchoice_uses_dedicated_visible_chrome_by_default():
    query = next(q for q in load_registry() if q.supplier == "CleanChoice Energy")
    assert browser_plan(query, False, "chromium") == ("visible", False, "chrome")
    assert browser_plan(query, True, "chromium") == ("primary", False, None)


def test_american_power_and_gas_uses_visible_chrome_for_address_autocomplete():
    query = Query(
        supplier="American Power & Gas", utility="PSE&G Gas", commodity="gas",
        zip="07102", url="https://apgpublicsite.azurewebsites.net/locations/new-jersey",
        adapter="american_power_and_gas",
    )
    assert browser_plan(query, False, "chromium") == ("visible", False, "chrome")


def test_apg_waits_for_provider_options_not_only_the_select_shell():
    from unittest.mock import MagicMock

    page = MagicMock()
    wait_for_provider_options(page, "#gas-provider")
    script, = page.wait_for_function.call_args.args
    assert "select.options" in script
    page.wait_for_function.assert_called_once_with(
        script, arg="#gas-provider", timeout=15000
    )


def _nrg_request_artifact(query, artifact_id="nrg-products"):
    if query.commodity == "electric":
        body = {
            "utilitySlugElectric": {
                "PSE&G Electric": "pseg", "ACE Electric": "ace",
                "Rockland Electric": "reco",
            }[query.utility],
            "utilitySlugElectricName": query.utility,
            "stateSlug": "nj", "zipcode": query.zip,
            "utilityPref": "E", "onlyElectricity": "Y", "electricUnits": "kwh",
        }
    else:
        body = {
            "utilitySlugGas": {"PSE&G Gas": "pseg_gas", "SJG Gas": "sjersey"}[query.utility],
            "utilitySlugGasName": query.utility,
            "stateSlug": "nj", "zipcode": query.zip,
            "utilityPref": "G", "onlyGas": "Y", "gasUnits": "Thm",
        }
    return {
        "id": artifact_id, "url": NRG_PRODUCT_CHART_URL, "method": "POST",
        "status": 200, "request_body": body,
    }


@pytest.mark.parametrize("utility,commodity,zip_code", [
    ("PSE&G Electric", "electric", "07102"),
    ("ACE Electric", "electric", "08401"),
    ("Rockland Electric", "electric", "07430"),
    ("PSE&G Gas", "gas", "07102"),
    ("SJG Gas", "gas", "08094"),
])
def test_nrg_exact_product_request_qualifies_selector_absent_path(
        utility, commodity, zip_code):
    query = Query(
        supplier="NRG", utility=utility, commodity=commodity, zip=zip_code,
        url="https://www.picknrg.com/en/", adapter="nrg",
    )
    artifact = _nrg_request_artifact(query)
    evidence = nrg_product_request_evidence(
        [({}, NRG_PRODUCT_CHART_URL, artifact["id"])], [artifact], query
    )
    assert evidence["qualified"] is True
    assert all(evidence["checks"].values())


@pytest.mark.parametrize("field,bad_value", [
    ("zipcode", "99999"),
    ("stateSlug", "pa"),
    ("utilitySlugElectric", "ace"),
    ("utilitySlugElectricName", "Atlantic City Electric"),
    ("utilityPref", "G"),
    ("onlyElectricity", "N"),
    ("electricUnits", "therm"),
])
def test_nrg_product_request_rejects_every_mismatched_scope(field, bad_value):
    query = Query(
        supplier="NRG", utility="PSE&G Electric", commodity="electric", zip="07102",
        url="https://www.picknrg.com/en/", adapter="nrg",
    )
    artifact = _nrg_request_artifact(query)
    artifact["request_body"][field] = bad_value
    evidence = nrg_product_request_evidence(
        [({}, NRG_PRODUCT_CHART_URL, artifact["id"])], [artifact], query
    )
    assert evidence["qualified"] is False
    assert evidence["reason"] == "NRG product request does not exactly match the requested market"


def test_nrg_product_request_requires_one_unambiguous_capture():
    query = Query(
        supplier="NRG", utility="PSE&G Electric", commodity="electric", zip="07102",
        url="https://www.picknrg.com/en/", adapter="nrg",
    )
    assert nrg_product_request_evidence([], [], query)["qualified"] is False
    first = _nrg_request_artifact(query, "first")
    second = _nrg_request_artifact(query, "second")
    evidence = nrg_product_request_evidence(
        [({}, NRG_PRODUCT_CHART_URL, "first"), ({}, NRG_PRODUCT_CHART_URL, "second")],
        [first, second], query,
    )
    assert evidence["qualified"] is False
    assert evidence["captured_product_request_count"] == 2


def test_nrg_exact_captured_request_promotes_trusted_products(tmp_path):
    observed = json.loads(
        (Path(__file__).parent / "fixtures/observed/nrg_electric.json").read_text(encoding="utf-8")
    )
    query = Query.model_validate(observed["query"])
    product = next(item for item in observed["payloads"] if item["url"] == NRG_PRODUCT_CHART_URL)
    store = ArtifactStore(tmp_path / "artifacts")
    record = store.save(
        product["body"], "json", NRG_PRODUCT_CHART_URL, method="POST", status=200,
        request_body=_nrg_request_artifact(query)["request_body"],
    )
    result = CollectionResult(query=query)
    assemble(
        result, NavigationResult(url="https://www.picknrg.com/en/electricity-and-gas/product-chart"),
        store, [(product["body"], NRG_PRODUCT_CHART_URL, record["id"])],
    )
    assert result.context_verified and result.live_data_verified
    assert result.source_evidence["nrg_product_request"]["qualified"] is True
    assert len(result.offers) == 18


def test_direct_energy_uses_visible_chrome_for_ordinary_homepage_path():
    query = next(q for q in load_registry() if q.supplier == "Direct Energy")
    assert browser_plan(query, False, "chromium") == ("direct_cdp", False, "chrome")


def test_direct_public_api_path_qualifies_exact_zip_utility_and_current_products(tmp_path):
    query = next(
        q for q in load_registry()
        if q.supplier == "Direct Energy" and q.utility == "PSE&G Electric"
    )
    nav, payloads = fetch_direct_public_api(
        _RecordedDirectTransport(), ArtifactStore(tmp_path / "artifacts"), query
    )
    assert nav.context_verified and nav.live_data_verified
    assert nav.disposition is None
    assert len(payloads) == 2
    assert nav.evidence["direct_public_api"]["scoped_product_count"] > 0


def test_direct_public_api_path_fails_closed_without_exact_utility(tmp_path):
    query = next(
        q for q in load_registry()
        if q.supplier == "Direct Energy" and q.utility == "PSE&G Electric"
    ).model_copy(update={"utility": "ACE Electric"})
    with pytest.raises(ValueError, match="exactly one requested NJ utility"):
        fetch_direct_public_api(
            _RecordedDirectTransport(), ArtifactStore(tmp_path / "artifacts"), query
        )


def test_direct_public_api_path_rejects_non_json_response(tmp_path):
    query = next(
        q for q in load_registry()
        if q.supplier == "Direct Energy" and q.utility == "PSE&G Electric"
    )
    with pytest.raises(ValueError, match="non-JSON"):
        fetch_direct_public_api(
            _RecordedDirectTransport(content_type="text/html"),
            ArtifactStore(tmp_path / "artifacts"), query,
        )


def test_only_direct_reuses_run_scoped_public_site_state():
    direct = next(q for q in load_registry() if q.supplier == "Direct Energy")
    cleanchoice = next(q for q in load_registry() if q.supplier == "CleanChoice Energy")
    assert browser_state_key(direct) == "direct_energy"
    assert browser_state_key(cleanchoice) is None


def test_browser_context_does_not_load_a_user_profile():
    options = browser_context_options()
    assert options["accept_downloads"] is True
    assert options["viewport"] == {"width": 1360, "height": 900}
    assert set(options) == {"accept_downloads", "viewport"}


def test_direct_retry_queue_excludes_nonblocked_and_other_suppliers(tmp_path):
    blocked = replay(FIXTURE, tmp_path / "blocked")
    blocked.query.adapter = "direct_energy"
    blocked.status = "blocked"
    successful_direct = blocked.model_copy(deep=True)
    successful_direct.status = "success"
    other = blocked.model_copy(deep=True)
    other.query.adapter = "cleanchoice"
    assert direct_retry_indexes([successful_direct, blocked, other]) == [1]


def test_direct_retry_requires_verified_same_market_evidence(tmp_path):
    previous = replay(FIXTURE, tmp_path / "previous")
    previous.query.adapter = "direct_energy"
    previous.status = "blocked"
    retry = previous.model_copy(deep=True)
    retry.status = "partial"
    retry.context_verified = retry.live_data_verified = True
    assert direct_retry_is_substantive(previous, retry)

    wrong_market = retry.model_copy(deep=True)
    wrong_market.query.zip = "08401"
    assert not direct_retry_is_substantive(previous, wrong_market)
    unverified = retry.model_copy(deep=True)
    unverified.context_verified = False
    assert not direct_retry_is_substantive(previous, unverified)


def test_direct_rejected_retry_preserves_initial_blocked_result(tmp_path):
    previous = replay(FIXTURE, tmp_path / "previous")
    previous.query.adapter = "direct_energy"
    previous.status = "blocked"
    retry = previous.model_copy(deep=True)
    retry.status = "failed"
    retry.offers = []
    selected = select_direct_retry(previous, retry)
    assert selected is previous
    assert previous.attempts[-1] == {
        "kind": "bounded_direct_retry", "status": "failed", "offers": 0,
        "errors": len(retry.errors), "selected": False,
        "reason": "retry did not prove a verified live same-market disposition",
    }


def test_direct_displayed_plan_count_is_explicit_and_not_inferred():
    assert direct_displayed_plan_count("Viewing 7 plans") == 7
    assert direct_displayed_plan_count("Seven plans may be available") is None
    reconcile_direct_plan_counts(7, 7)
    with pytest.raises(NavigationError, match="displayed/rendered plan-count mismatch"):
        reconcile_direct_plan_counts(7, 6)


def test_nextera_requires_one_unique_composite_identity_per_card():
    html = """
    <div class="pricing_plan_item plan_card"><span class="learnMoreDetails" data-rate="A|B|C|1"></span></div>
    <div class="pricing_plan_item plan_card"><span class="learnMoreDetails" data-rate="A|B|C|2"></span></div>
    """
    assert nextera_plan_identities(html) == ["A|B|C|1", "A|B|C|2"]
    with pytest.raises(NavigationError, match="duplicate composite"):
        nextera_plan_identities(html.replace("A|B|C|2", "A|B|C|1"))


def test_stable_document_reference_is_copied_onto_offer(tmp_path):
    result = replay(FIXTURE, tmp_path / "offer")
    offer = result.offers[0]
    offer.documents = []
    ref = DocumentRef(
        url="https://example.com/plan-terms.pdf",
        label="Terms of Service",
        product_id=offer.product_id,
    )
    bind_document_refs([offer], [ref])
    assert offer.documents == [ref]
    assert ref.offer_key == offer.key


def test_normal_suppliers_remain_headless_in_mixed_runs():
    query = next(q for q in load_registry() if q.supplier == "Indra Energy")
    assert browser_plan(query, False, "chromium") == ("primary", True, None)
    assert browser_plan(query, False, "msedge") == ("primary", True, "msedge")


def test_verified_market_context_fills_only_missing_distribution_company(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    result.replayed = False
    result.context_verified = result.live_data_verified = True
    text = ("Third Party Supplier Information: Example Energy\nPrice Structure: Fixed\n"
            "Generation/Supply Price: $0.199/kWh\nStatement Regarding Savings: None\n"
            "Amount of time required to change: One cycle\nIncentives: None\n"
            "Right to Cancel/Rescind: Seven days\nContract Start Date: Meter read\n"
            "Contract Term/Length: 12 months\nCancellation/Early Termination Fees: $0\n"
            "Renewal Terms: Month to month")
    contract = extract_contract(text.encode(), "https://example.com/missing-utility", "context-hash")
    add_contract(result, contract, [DocumentRef(
        url=contract.url, label="Contract Summary", offer_key=result.offers[0].key
    )])
    added = next(item for item in result.contracts if item.id == "context-hash")
    assert added.sections["distribution_company"] == "Verified collection context: PSE&G Electric"
    assert "distribution_company" not in added.missing_sections
    assert added.status == "parsed"


def test_source_absent_incentives_are_recorded_without_inventing_a_promotion(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    result.replayed = False
    result.context_verified = result.live_data_verified = True
    result.offers[0].incentives = []
    text = ("Third Party Supplier Information: Example Energy\nPrice Structure: Fixed\n"
            "Generation/Supply Price: $0.199/kWh\nStatement Regarding Savings: None\n"
            "Amount of time required to change: One cycle\n"
            "Right to Cancel/Rescind: Seven days\nContract Start Date: Meter read\n"
            "Contract Term/Length: 12 months\nCancellation/Early Termination Fees: $0\n"
            "Renewal Terms: Month to month\nDistribution Company Information: PSE&G")
    contract = extract_contract(text.encode(), "https://example.com/summary", "absent-incentive")
    add_contract(result, contract, [DocumentRef(
        url=contract.url, label="Contract Summary", offer_key=result.offers[0].key
    )])
    added = next(item for item in result.contracts if item.id == "absent-incentive")
    assert added.status == "parsed"
    assert added.missing_sections == []
    assert added.fields["source_absent_sections"] == ["incentives"]
    assert added.sections["incentives"].startswith("No incentive stated")


def test_completion_issue_prevents_false_success_but_information_note_does_not(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    assert result.status == "success"
    result.warnings.append("Informational navigation note")
    finalize(result, ArtifactStore(tmp_path / "informational-artifacts"))
    assert result.status == "success"

    result.completion_issues.append("Stable plan identities did not reconcile")
    finalize(result, ArtifactStore(tmp_path / "blocked-artifacts"))
    assert result.status == "partial"


def test_direct_green_flag_conflict_is_resolved_only_by_connected_contract(tmp_path):
    from decimal import Decimal

    result = replay(FIXTURE, tmp_path / "base")
    result.query.adapter = "direct_energy"
    offer = result.offers[0]
    warning = "API greenFlag=false conflicts with GREENOFFER; consult environmental disclosure"
    offer.warnings = [warning]
    result.contracts = [Contract(
        id="direct-summary", url="https://directenergydocuments.gesc.com/summary",
        artifact_id="summary-artifact", media_type="application/pdf",
        document_kind="contract_summary", status="parsed",
        matched_offer_keys=[offer.key],
        sections={"price_structure": (
            "You are purchasing a Renewable Energy Product that is supported "
            "100% by renewable energy credits."
        )},
    )]

    resolve_direct_renewable_conflicts(result)

    assert offer.renewable_percentage == Decimal("100")
    assert offer.renewable_source == "connected supplier contract summary"
    assert offer.warnings == []
    assert offer.raw_fields["green_flag_conflict_resolved_by_contract_id"] == "direct-summary"


def test_completion_issue_is_exported_as_critical_scraper_alert(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    result.completion_issues.append("API and rendered plan counts disagree")
    alerts = alert_rows([result])
    assert any(
        row["alert_code"] == "completion_integrity_issue"
        and row["detail"] == "API and rendered plan counts disagree"
        for row in alerts
    )


def test_nextera_zip_falls_back_to_validated_form_submission_when_button_stays_disabled():
    from unittest.mock import MagicMock
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    page = MagicMock()
    zipcode = MagicMock()
    submit = MagicMock()
    form = MagicMock()
    page.locator.side_effect = lambda selector: {
        "#Zipcode": zipcode,
        "#btnZipCode": submit,
        'form[action="/Plans/ViewPlans"]': form,
    }[selector]
    page.wait_for_function.side_effect = PlaywrightTimeoutError("button remained disabled")

    submit_nextera_zip(page, "08401")

    zipcode.press_sequentially.assert_called_once_with("08401")
    zipcode.press.assert_called_once_with("Tab")
    zipcode.evaluate.assert_called_once()
    form.evaluate.assert_called_once()
    script, submitted_zip = form.evaluate.call_args.args
    assert "button.click()" in script
    assert "requestSubmit" not in script
    assert "field.checkValidity()" in script
    assert submitted_zip == "08401"
    submit.click.assert_not_called()


def test_sitewide_legal_pages_cannot_satisfy_major_or_apg_plan_documents(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    result.query.adapter = "major_energy"
    result.offers[0].product_id = "148074"
    refs = [
        DocumentRef(url="https://majorenergy.com/terms-of-use/", label="Terms of Use"),
        DocumentRef(
            url="https://signup.majorenergy.com/getdocument/?getproductpdf=1&ProductID=148074&type=TOS",
            label="Terms of Service",
            product_id="148074",
            offer_key=result.offers[0].key,
        ),
    ]
    scoped = scoped_document_refs(result.query, refs, result.offers)
    assert [ref.url for ref in scoped] == [refs[1].url]

    result.query.adapter = "american_power_and_gas"
    refs = [DocumentRef(
        url="https://americanpowerandgas.com/terms-of-use/",
        label="Terms and Conditions",
    )]
    assert scoped_document_refs(result.query, refs, result.offers) == []


def test_major_plan_tos_is_useful_connected_evidence_not_a_contract_summary():
    result = CollectionResult(query=Query(
        supplier="Major Energy", utility="ACE Electric", commodity="electric",
        zip="08401", url="https://signup.majorenergy.com/", adapter="major_energy",
    ))
    contract = Contract(
        id="major-tos", url="https://signup.majorenergy.com/getdocument/?ProductID=123&type=TOS",
        artifact_id="artifact", media_type="application/pdf", raw_text="Public plan terms",
        sections={"price": "12 cents", "term": "12 months", "fees": "$0"},
        missing_sections=["supplier_information"], warnings=["Missing sections: supplier_information"],
        status="partial",
    )
    add_contract(result, contract, [DocumentRef(
        url=contract.url, label="Terms of Service", product_id="123",
    )])

    assert contract.document_kind == "terms_or_other"
    assert contract.status == "text_extracted"
    assert contract.missing_sections == []
    assert not any(warning.startswith("Missing sections:") for warning in contract.warnings)


def test_nextera_detail_capture_preserves_stable_product_identity():
    from unittest.mock import MagicMock

    page = MagicMock()
    page.url = "https://signup.nexteraenergyservices.com/Plans/ViewPlans"
    action = MagicMock()
    actions = MagicMock()
    actions.count.return_value = 1
    actions.nth.return_value = action
    action.is_visible.return_value = True
    action.get_attribute.return_value = "7561|3887|1033|36136"
    action.evaluate.return_value = '<div class="pricing_plan_item plan_card"></div>'
    modal = MagicMock()
    modal.first = modal
    result_box = MagicMock()
    close = MagicMock()
    result_box.evaluate.return_value = True
    modal.inner_html.return_value = (
        '<a href="https://signup.nexteraenergyservices.com/Documents/TOS.pdf">Terms of Service</a>'
    )
    close.count.return_value = 1
    close.first.is_visible.return_value = True
    modal.locator.side_effect = lambda selector: result_box if selector == "#result" else close
    page.locator.side_effect = lambda selector: (
        actions if selector == ".learnMoreDetails[data-rate]" else modal
    )
    result = NavigationResult(url="https://signup.nexteraenergyservices.com/Plans/ViewPlans")

    capture_nextera_details(page, result)

    assert result.fragments == [{
        "origin": '<div class="pricing_plan_item plan_card"></div>',
        "html": '<a href="https://signup.nexteraenergyservices.com/Documents/TOS.pdf">Terms of Service</a>',
        "url": result.url,
        "product_id": "7561|3887|1033|36136",
    }]
    assert action.evaluate.call_count == 2
    page.locator.assert_any_call(".modal:visible .modal-content")
    assert result.notes[-1] == (
        "NextEra details reconciliation: 1/1 plan panel(s) captured; "
        "1 exposed plan-document links"
    )


def test_nextera_required_identity_cannot_disappear_with_missing_action():
    from unittest.mock import MagicMock

    page = MagicMock()
    page.locator.return_value.count.return_value = 0
    result = NavigationResult(url="https://signup.nexteraenergyservices.com/Plans/ViewPlans")
    capture_nextera_details(page, result, ["A|B|C|1"])
    assert "NextEra details were not captured for product identities: A|B|C|1" in result.notes
    assert result.notes[-1].startswith("NextEra details reconciliation: 0/1")


def test_nextera_loaded_details_distinguish_document_presence():
    assert nextera_detail_has_document(
        '<a href="/Documents/TOS.pdf">Terms of Service</a>'
    )
    assert not nextera_detail_has_document(
        "<p>Your selected renewable plan details are available above.</p>"
    )


def _direct_payloads(query, products, utility_zip=None):
    utility = {
        "electricUtility": [{
            "state": "NJ", "name": query.utility, "utilityCode": "PSE",
        }],
    }
    return [
        (utility,
         "https://api-oam.directenergy.com/api/east/deeast/v1/wcl/"
         f"get-utilities-by-zip?zipcode={utility_zip or query.zip}", "utility-artifact"),
        ({"statusCode": "00", "affiliateOfferList": products},
         "https://api-oe.directenergy.com/api/eastrest/v1/products", "product-artifact"),
    ]


def _direct_product(**changes):
    product = {
        "utilityCode": "PSE", "state": "nj", "customerType": "residential",
        "commodity": "electricity", "elecRate": [{"rate": "15.25"}],
        "unitELEC": "kwh", "currency": "cents", "contractTerm": 12,
        "offerCode": "882509", "offerPlanName": "Direct 12", "planType": "fix",
        "tosURL": "https://directenergydocuments.gesc.com//DisplayDocument.aspx?Rateid=882509&Code=CDS",
    }
    product.update(changes)
    return product


def test_direct_scope_requires_the_requested_zip_utility_evidence():
    query = next(q for q in load_registry() if q.supplier == "Direct Energy" and q.commodity == "electric")
    diagnostics = direct_energy_diagnostics(
        _direct_payloads(query, [_direct_product()], utility_zip="99999"), query
    )
    assert diagnostics["utility_codes"] == []
    assert diagnostics["source_product_count"] == 0


def test_direct_diagnostics_preserve_raw_count_and_source_anomalies():
    query = next(q for q in load_registry() if q.supplier == "Direct Energy" and q.commodity == "electric")
    products = [
        _direct_product(),
        _direct_product(tosURL="https://example.com/not-a-direct-contract.pdf"),
        _direct_product(offerCode="", offerPlanName="Malformed"),
    ]
    diagnostics = direct_energy_diagnostics(_direct_payloads(query, products), query)
    assert diagnostics["source_product_count"] == 3
    assert diagnostics["duplicate_offer_codes"] == ["882509"]
    assert diagnostics["missing_offer_code_count"] == 1
    assert diagnostics["invalid_document_fields"] == ["882509:tosURL"]


def test_direct_uses_latest_successful_product_snapshot_without_duplication():
    query = next(q for q in load_registry() if q.supplier == "Direct Energy" and q.commodity == "electric")
    payloads = _direct_payloads(query, [_direct_product(offerCode="old")])
    payloads.append((
        {"statusCode": "00", "affiliateOfferList": [_direct_product(offerCode="current")]},
        "https://api-oe.directenergy.com/api/eastrest/v1/products",
        "current-product-artifact",
    ))
    diagnostics = direct_energy_diagnostics(payloads, query)
    offers = direct_energy(payloads, query)
    assert diagnostics["product_response_count"] == 2
    assert diagnostics["source_product_count"] == 1
    assert diagnostics["product_artifact_id"] == "current-product-artifact"
    assert [offer.product_id for offer in offers] == ["current"]


def test_direct_dual_fuel_response_order_cannot_replace_requested_utility():
    query = next(q for q in load_registry() if q.supplier == "Direct Energy" and q.commodity == "electric")
    payloads = _direct_payloads(query, [_direct_product(offerCode="electric-current")])
    payloads.append((
        {"statusCode": "00", "affiliateOfferList": [{
            "utilityCode": "PSG", "state": "nj", "customerType": "residential",
            "commodity": "gas", "offerCode": "gas-current",
        }]},
        "https://api-oe.directenergy.com/api/eastrest/v1/products",
        "later-gas-artifact",
    ))
    diagnostics = direct_energy_diagnostics(payloads, query)
    offers = direct_energy(payloads, query)
    assert diagnostics["product_response_count"] == 2
    assert diagnostics["product_artifact_id"] == "product-artifact"
    assert [offer.product_id for offer in offers] == ["electric-current"]


def test_direct_latest_exact_zip_utility_snapshot_is_authoritative():
    query = next(q for q in load_registry() if q.supplier == "Direct Energy" and q.commodity == "electric")
    payloads = _direct_payloads(query, [_direct_product()])
    payloads.append((
        {"electricUtility": []},
        "https://api-oam.directenergy.com/api/east/deeast/v1/wcl/"
        f"get-utilities-by-zip?zipcode={query.zip}",
        "latest-empty-utility-artifact",
    ))
    diagnostics = direct_energy_diagnostics(payloads, query)
    assert diagnostics["utility_response_count"] == 2
    assert diagnostics["utility_artifact_id"] == "latest-empty-utility-artifact"
    assert diagnostics["utility_codes"] == []
    assert direct_energy(payloads, query) == []


def test_direct_document_route_requires_supplier_host_rate_and_type():
    assert direct_document_url_valid(
        "https://directenergydocuments.gesc.com//DisplayDocument.aspx?Rateid=882509&Code=CDS",
        "CDS",
    )
    assert not direct_document_url_valid(
        "https://example.com/DisplayDocument.aspx?Rateid=882509&Code=CDS", "CDS"
    )
    assert not direct_document_url_valid(
        "https://directenergydocuments.gesc.com/DisplayDocument.aspx?Code=CDS", "CDS"
    )


def test_direct_parser_omits_malformed_document_without_losing_offer():
    query = next(q for q in load_registry() if q.supplier == "Direct Energy" and q.commodity == "electric")
    offers = direct_energy(
        _direct_payloads(query, [_direct_product(tosURL="https://example.com/terms.pdf")]), query
    )
    assert len(offers) == 1
    assert offers[0].documents == []
    assert offers[0].warnings == ["Invalid supplier document route omitted: tosURL"]


def test_direct_document_scope_rejects_unconnected_sitewide_legal_link(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    result.query.adapter = "direct_energy"
    result.offers[0].product_id = "882509"
    refs = [
        DocumentRef(
            url="https://directenergydocuments.gesc.com/DisplayDocument.aspx?Rateid=882509&Code=CDS",
            label="Contract Summary", product_id="882509",
        ),
        DocumentRef(
            url="https://www.directenergy.com/terms-of-use",
            label="Terms of Use",
        ),
    ]
    assert scoped_document_refs(result.query, refs, result.offers) == [refs[0]]


def test_nextera_document_scope_requires_supplier_owned_plan_link(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    result.query.adapter = "nextera_energy_services"
    result.query.supplier = "NextEra Energy Services"
    result.offers[0].supplier = result.query.supplier
    result.offers[0].product_id = "A|B|C|1"
    refs = [
        DocumentRef(
            url="https://signup.nexteraenergyservices.com/Documents/TOS.pdf",
            label="Terms of Service", product_id="A|B|C|1",
        ),
        DocumentRef(
            url="https://signup.nexteraenergyservices.com/terms-of-use/",
            label="Terms of Use",
        ),
        DocumentRef(
            url="https://foreign.example/Documents/TOS.pdf",
            label="Terms of Service", product_id="A|B|C|1",
        ),
    ]
    scoped = scoped_document_refs(result.query, refs, result.offers)
    assert scoped == [refs[0]]


def test_shared_nextera_document_keeps_each_plan_association(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    result.query.adapter = "nextera_energy_services"
    first = result.offers[0]
    first.product_id = "A|B|C|1"
    second = first.model_copy(deep=True)
    second.product_id = "A|B|C|2"
    second.key = "second-offer-key"
    url = "https://signup.nexteraenergyservices.com/Documents/TOS.pdf"
    refs = [
        DocumentRef(url=url, label="Terms", product_id=first.product_id, offer_key=first.key),
        DocumentRef(url=url, label="Terms", product_id=second.product_id, offer_key=second.key),
    ]
    scoped = scoped_document_refs(result.query, refs, [first, second])
    assert {(ref.offer_key, ref.product_id) for ref in scoped} == {
        (first.key, first.product_id), (second.key, second.product_id),
    }


def test_nextera_document_route_restores_composite_product_identity():
    assert nextera_document_product_id(
        "https://signup.nexteraenergyservices.com/Document/GetCSTOS/7561%2c3630%2c1033%2c36205"
    ) == "7561|3630|1033|36205"
    assert nextera_document_product_id(
        "https://signup.nexteraenergyservices.com/terms-of-use/"
    ) is None


def test_nextera_duplicate_modal_links_cannot_cross_plan_boundaries(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    offer = result.offers[0]
    offer.product_id = "7561|3887|1033|36136"
    offer.documents = [
        DocumentRef(
            url="https://signup.nexteraenergyservices.com/Document/GetCSTOS/7561%2c3887%2c1033%2c36136",
            product_id=offer.product_id,
        ),
        DocumentRef(
            url="https://signup.nexteraenergyservices.com/Document/GetCSTOS/7561%2c3630%2c1033%2c36205",
            product_id=offer.product_id,
        ),
    ]

    scope_nextera_offer_documents([offer])

    assert len(offer.documents) == 1
    assert offer.documents[0].product_id == offer.product_id
    assert offer.documents[0].offer_key == offer.key


def test_document_scope_rejects_cross_brand_and_cross_commodity_links(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    query = result.query.model_copy(update={"supplier": "Clearview Energy", "adapter": "clearview_energy"})
    result.offers[0].supplier = "Clearview Energy"
    result.offers[0].product_id = "E12"
    refs = [
        DocumentRef(url="https://www.clearviewenergy.com/documents/tos/?productNum=E12", label="TOS"),
        DocumentRef(url="https://www.clearviewenergy.com/documents/tos/?productNum=G12", label="TOS"),
        DocumentRef(url="https://foreign.example/terms.pdf", label="Terms"),
        DocumentRef(url="https://www.clearviewenergy.com/disclosures/", label="Disclosures"),
    ]
    scoped = scoped_document_refs(query, refs, result.offers)
    assert {ref.url for ref in scoped} == {
        "https://www.clearviewenergy.com/documents/tos/?productNum=E12",
        "https://www.clearviewenergy.com/disclosures/",
    }


def test_idt_stale_disclosure_route_is_rewritten_to_current_supplier_route(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    query = result.query.model_copy(update={"supplier": "IDT Energy", "adapter": "idt_energy"})
    refs = [DocumentRef(
        url="https://idtenergy.com/get-started/your-offers/environmental-disclosure-labels/",
        label="Environmental Disclosure Labels",
    )]
    scoped = scoped_document_refs(query, refs, result.offers)
    assert scoped[0].url == "https://idtenergy.com/environmental-disclosure-labels/"


def test_constellation_prefers_plan_contracts_over_sitewide_legal_links(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    query = result.query.model_copy(update={"supplier": "Constellation Energy", "adapter": "constellation"})
    result.offers[0].supplier = "Constellation Energy"
    result.offers[0].product_id = "15115"
    refs = [
        DocumentRef(
            url="https://www.constellation.com/bin/residential/GetPlanContractPDF?planId=15115",
            label="Terms and conditions",
            product_id="15115",
            offer_key=result.offers[0].key,
        ),
        DocumentRef(
            url="https://www.constellation.com/refer-a-friend/terms---conditions.html",
            label="Terms and conditions",
        ),
    ]
    scoped = scoped_document_refs(query, refs, result.offers)
    assert [ref.url for ref in scoped] == [refs[0].url]


def test_generic_public_document_is_retained_as_market_level_evidence(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    result.replayed = False
    result.context_verified = result.live_data_verified = True
    contract = extract_contract(b"General supplier terms for all residential customers.",
                                "https://example.com/terms", "market-terms")
    add_contract(result, contract, [DocumentRef(url=contract.url, label="Terms of Service")])
    added = next(item for item in result.contracts if item.id == "market-terms")
    assert added.document_kind == "terms_or_other"
    assert added.status == "text_extracted"
    assert added.match_method == "market_level_public_document"
    assert added.warnings == []
    result.contracts = [added]
    result.offers[0].contract_ids = []
    result.offers[0].warnings = []
    class Store:
        records = []
    finalize(result, Store())
    assert result.status == "success"


def test_plan_scoped_image_only_environmental_pdf_is_retained_without_fake_ocr(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    offer = result.offers[0]
    result.contracts = []
    contract = Contract(
        id="image-edl", url="https://example.com/environmental.pdf",
        artifact_id="image-edl", media_type="application/pdf",
        status="needs_review",
        warnings=["No text layer found; scanned/empty document requires OCR or manual review"],
    )
    add_contract(result, contract, [DocumentRef(
        url=contract.url, label="Environmental Disclosure Label",
        product_id=offer.product_id, offer_key=offer.key,
    )])
    retained = result.contracts[0]
    assert retained.document_kind == "environmental"
    assert retained.status == "retained"
    assert retained.fields["binary_retained_without_text_layer"] is True
    assert retained.missing_sections == []
    assert retained.warnings == []
    assert retained.matched_offer_keys == [offer.key]
    association = document_association_rows([result])[0]
    assert association["association_status"] == "complete"
    assert association["association_scope"] == "offer"


def test_plan_linked_terms_document_is_not_held_to_contract_summary_sections(tmp_path):
    result = replay(FIXTURE, tmp_path / "base")
    result.replayed = False
    result.context_verified = result.live_data_verified = True
    contract = extract_contract(
        b"Generation/Supply Price: Price is stated in the linked plan card.",
        "https://example.com/tos?productId=123",
        "linked-terms",
    )
    add_contract(result, contract, [DocumentRef(
        url=contract.url,
        label="TOS",
        offer_key=result.offers[0].key,
        product_id=result.offers[0].product_id,
    )])
    added = next(item for item in result.contracts if item.id == "linked-terms")
    assert added.document_kind == "terms_or_other"
    assert added.status == "text_extracted"
    assert added.missing_sections == []
    assert added.warnings == []


def test_verify_report_rejects_one_way_offer_contract_links(tmp_path):
    result = replay(FIXTURE, tmp_path / "evidence")
    write_report([result], tmp_path)
    import json
    path = tmp_path / "results.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data[0]["contracts"][0]["matched_offer_keys"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    assert any("not bidirectional" in error for error in verify_report(tmp_path))


def test_cli_consolidates_retry_evidence(tmp_path):
    base, retry, combined = tmp_path / "base", tmp_path / "retry", tmp_path / "combined"
    assert main(["replay", str(FIXTURE), "--output", str(base)]) == 0
    assert main(["replay", str(FIXTURE), "--output", str(retry)]) == 0
    assert main(["consolidate", str(base), "--retry", str(retry), "--output", str(combined)]) == 0
    assert main(["verify", str(combined)]) == 0
    assert (combined / "offer_prices.csv").is_file()


def test_reader_exports_consolidate_same_offer_across_zips(tmp_path):
    import csv

    first = replay(FIXTURE, tmp_path / "first")
    first.replayed = False
    first.live_data_verified = True
    second = first.model_copy(deep=True)
    second.query.zip = "07302"
    second.offers[0].zip = "07302"
    second.offers[0].key = "second-zip-observation"
    second.contracts[0].matched_offer_keys = [second.offers[0].key]

    write_offer_prices([first, second], tmp_path / "prices.csv")
    write_offer_observations([first, second], tmp_path / "observations.csv")
    with (tmp_path / "prices.csv").open(encoding="utf-8-sig", newline="") as handle:
        prices = list(csv.DictReader(handle))
    with (tmp_path / "observations.csv").open(encoding="utf-8-sig", newline="") as handle:
        observations = list(csv.DictReader(handle))

    assert len(prices) == 1
    assert prices[0]["observed_zip_codes"] == "07102 | 07302"
    assert prices[0]["offer_fingerprint"]
    assert {"source_urls", "captured_at"}.issubset(prices[0])
    assert not {
        "zip_count", "observation_count", "duplicate_status", "same_rate_offer_count",
        "same_rate_status", "offer_key", "source_offer_keys", "product_id",
        "rate_cents_per_unit", "source_url", "first_captured_at", "last_captured_at",
    }.intersection(prices[0])
    assert len(observations) == 2
    assert sum(row["canonical_observation"] == "True" for row in observations) == 1


def test_same_rate_different_product_ids_remain_distinct(tmp_path):
    import csv

    first = replay(FIXTURE, tmp_path / "first")
    first.replayed = False
    first.live_data_verified = True
    different = first.model_copy(deep=True)
    different.offers[0].product_id = "DEMO-DIFFERENT"
    different.offers[0].key = "different-product"
    write_offer_prices([first, different], tmp_path / "prices.csv")
    with (tmp_path / "prices.csv").open(encoding="utf-8-sig", newline="") as handle:
        prices = list(csv.DictReader(handle))

    assert len(prices) == 2
    assert len({row["offer_fingerprint"] for row in prices}) == 2
    assert "same_rate_status" not in prices[0]
    assert "same_rate_offer_count" not in prices[0]


def test_reader_exports_sort_electric_before_gas_then_supplier(tmp_path):
    import csv

    electric_b = replay(FIXTURE, tmp_path / "electric_b")
    electric_b.replayed = False
    electric_b.live_data_verified = True
    electric_b.query.supplier = electric_b.offers[0].supplier = "Zulu Electric"
    electric_a = electric_b.model_copy(deep=True)
    electric_a.query.supplier = electric_a.offers[0].supplier = "Alpha Electric"
    electric_a.offers[0].product_id = "ALPHA-E"
    gas = electric_b.model_copy(deep=True)
    gas.query.supplier = gas.offers[0].supplier = "Aardvark Gas"
    gas.query.commodity = gas.offers[0].commodity = "gas"
    gas.offers[0].price.unit = "USD/therm"
    gas.offers[0].product_id = "AARDVARK-G"
    write_offer_prices([gas, electric_b, electric_a], tmp_path / "sorted.csv")
    with (tmp_path / "sorted.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [(row["commodity"], row["tps"]) for row in rows] == [
        ("electric", "Alpha Electric"), ("electric", "Zulu Electric"), ("gas", "Aardvark Gas")
    ]


def test_next_supplier_adapters_are_explicit():
    adapters = {q.supplier: q.adapter for q in load_registry()
                if q.supplier in {"Frontier Utilities", "CleanChoice Energy"}}
    assert adapters == {"CleanChoice Energy": "cleanchoice"}
    assert "cleanchoice" in STRATEGIES


def test_inactive_suppliers_are_excluded_from_production_registry():
    from nj_switch.registry import CONFIG

    inactive = set(CONFIG["inactive_suppliers"])
    assert inactive == {
        "Alpha Gas & Electric", "American Power & Gas", "Ameripro Energy", "Astral Energy",
        "Frontier Utilities", "Great American Gas & Electric",
        "Green Mountain Energy", "IGS Energy", "Mpower Energy",
        "North American Power", "Northeastern Power & Gas",
        "Residents Energy", "RPA Energy / Green Choice Energy",
        "South Bay Energy",
    }
    assert not ({query.supplier for query in load_registry()} & inactive)


def test_inactive_markets_are_excluded_from_production_registry():
    from nj_switch.registry import CONFIG

    inactive = set(CONFIG["inactive_markets"])
    active = {
        f"{query.supplier}|{query.utility}|{query.commodity}"
        for query in load_registry()
    }
    assert inactive == {
        "Smart Energy|SJG Gas|gas",
        "Smart Energy|ETG Gas|gas",
        "Think Energy|Rockland Electric|electric",
    }
    assert not (active & inactive)


def test_baseline_adapter_scope_matches_supported_commodities():
    suppliers = {
        "Smart Energy": "smart_energy",
        "Clearview Energy": "clearview_energy",
        "IDT Energy": "idt_energy",
        "CleanSky Energy": "cleansky_energy",
    }
    rows = [query for query in load_registry() if query.supplier in suppliers]
    for supplier, adapter in suppliers.items():
        electric = [query for query in rows if query.supplier == supplier and query.commodity == "electric"]
        assert electric and all(query.adapter == adapter for query in electric)
        gas = [query for query in rows if query.supplier == supplier and query.commodity == "gas"]
        expected_gas = adapter if supplier in {"Smart Energy", "Clearview Energy", "IDT Energy", "CleanSky Energy"} else "default"
        assert all(query.adapter == expected_gas for query in gas)
    assert set(suppliers.values()) <= STRATEGIES.keys()


def test_new_supplier_adapters_replace_generic_fallbacks():
    expected = {
        "NextEra Energy Services": "nextera_energy_services",
        "Residents Energy": "residents_energy",
        "NJG&E": "njgande",
        "Eligo Energy": "eligo_energy",
    }
    rows = [query for query in load_registry() if query.supplier in expected]
    assert rows
    assert all(query.adapter == expected[query.supplier] for query in rows)
    assert set(expected.values()) <= STRATEGIES.keys()


def test_confirmed_expansion_markets_are_registered_with_explicit_adapters():
    expected = {
        ("Clearview Energy", "PSE&G Electric", "electric"): "clearview_energy",
        ("Clearview Energy", "Rockland Electric", "electric"): "clearview_energy",
        ("NJG&E", "JCP&L Electric", "electric"): "njgande",
        ("NJG&E", "PSE&G Electric", "electric"): "njgande",
        ("NJG&E", "Rockland Electric", "electric"): "njgande",
        ("IDT Energy", "SJG Gas", "gas"): "idt_energy",
    }
    actual = {
        (query.supplier, query.utility, query.commodity): query.adapter
        for query in load_registry()
        if (query.supplier, query.utility, query.commodity) in expected
    }
    assert actual == expected


def test_indra_gas_markets_are_registered_with_explicit_adapter():
    expected = {"ETG Gas", "NJNG Gas", "PSE&G Gas", "SJG Gas"}
    rows = [query for query in load_registry()
            if query.supplier == "Indra Energy" and query.commodity == "gas"]
    assert {query.utility for query in rows} == expected
    assert all(query.adapter == "indra_energy" for query in rows)
    assert "indra_energy" in STRATEGIES


def test_indra_electric_markets_are_registered_with_explicit_adapter():
    expected = {"ACE Electric", "JCP&L Electric", "PSE&G Electric", "Rockland Electric"}
    rows = [query for query in load_registry()
            if query.supplier == "Indra Energy" and query.commodity == "electric"]
    assert {query.utility for query in rows} == expected
    assert all(query.adapter == "indra_energy" for query in rows)


def test_nordic_electric_markets_are_registered_with_explicit_adapter():
    expected = {"ACE Electric", "JCP&L Electric", "PSE&G Electric"}
    rows = [query for query in load_registry()
            if query.supplier == "Nordic Energy Services" and query.commodity == "electric"]
    assert {query.utility for query in rows} == expected
    assert all(query.adapter == "nordic_energy_services" for query in rows)


def test_ornj_is_a_rockland_alias_only():
    assert utility_matches("ORNJ", "Rockland Electric")
    assert not utility_matches("ORNJ", "PSE&G Electric")


def test_additional_market_zips_are_targeted_not_global():
    rows = load_registry()
    selected = {(query.supplier, query.utility): set() for query in rows}
    for query in rows:
        selected[(query.supplier, query.utility)].add(query.zip)
    assert ("Think Energy", "Rockland Electric") not in selected
    assert selected[("CleanSky Energy", "PSE&G Gas")] == {"07102", "07430"}
    assert selected[("CleanSky Energy", "NJNG Gas")] == {"07712"}
    assert selected[("Direct Energy", "PSE&G Electric")] == {"07102"}


def test_supplier_access_failure_pages_are_not_empty_markets():
    access = Path(__file__).parent / "fixtures/access"
    assert "503" in access_failure((access / "frontier_503.html").read_text(encoding="utf-8"))
    assert "access-block" in access_failure((access / "cleanchoice_403.html").read_text(encoding="utf-8"))
    assert "Incapsula" in access_failure("<html><body>Request unsuccessful. Incapsula incident ID: 123</body></html>")
    assert access_failure("<main><h1>Available plans</h1></main>") is None


@pytest.mark.parametrize("name,status", [
    ("think_energy_rockland_electric", "empty"),
    ("constellation_pseg_gas", "unsupported"),
    ("constellation_njng_gas", "unsupported"),
    ("constellation_sjg_gas", "unsupported"),
    ("constellation_etg_gas", "unsupported"),
    ("frontier_pseg_electric", "blocked"),
    ("frontier_jcpl_electric", "blocked"),
    ("frontier_pseg_gas", "blocked"),
    ("frontier_njng_gas", "blocked"),
    ("frontier_etg_gas", "blocked"),
    ("cleanchoice_pseg_electric", "blocked"),
    ("cleanchoice_jcpl_electric", "blocked"),
    ("cleanchoice_ace_electric", "blocked"),
    ("cleansky_energy_rockland_electric", "blocked"),
    ("green_mountain_energy_rockland_electric", "unsupported"),
    ("great_american_pseg_electric", "empty"),
    ("nextera_ace_electric", "empty"),
    ("njgande_njng_gas", "blocked"),
])
def test_replay_preserves_explicit_disposition(name, status, tmp_path):
    fixture = Path(__file__).parent / f"fixtures/observed/{name}.json"
    result = replay(fixture, tmp_path / name)
    assert result.status == status
    assert result.offers == []


def test_navigation_start_retries_one_transient_timeout(monkeypatch):
    import json
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from nj_switch import navigation
    from nj_switch.models import Query

    query = Query.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8"))["query"])

    class Page:
        attempts = 0

        def goto(self, *args, **kwargs):
            self.attempts += 1
            if self.attempts == 1:
                raise PlaywrightTimeoutError("transient")

    page = Page()
    monkeypatch.setattr(navigation, "click_one", lambda *args, **kwargs: False)
    navigation.start(page, query)
    assert page.attempts == 2


def test_xoom_result_wait_reloads_exact_result_page_once():
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    class Cards:
        calls = 0

        @property
        def first(self):
            return self

        def wait_for(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise PlaywrightTimeoutError("stalled result navigation")

    class Page:
        def __init__(self):
            self.cards = Cards()
            self.reloads = []

        def locator(self, selector):
            assert selector == ".myRateData"
            return self.cards

        def reload(self, **kwargs):
            self.reloads.append(kwargs)

    page = Page()
    assert wait_for_xoom_results(page, timeout=25) is True
    assert page.cards.calls == 2
    assert page.reloads == [{"wait_until": "domcontentloaded", "timeout": 30000}]


def test_njgande_gateway_recovery_reloads_exact_page_until_form_returns():
    class Page:
        def __init__(self):
            self.responses = [
                "<title>Service unavailable</title><h1>504</h1><p>OriginTimeout from Azure Front Door</p>",
                '<form><input aria-label="ZIP code"></form>',
            ]
            self.index = 0
            self.reloads = []

        def content(self):
            return self.responses[self.index]

        def reload(self, **kwargs):
            self.reloads.append(kwargs)
            self.index += 1

    page = Page()
    assert recover_njgande_gateway(page) is True
    assert page.reloads == [{"wait_until": "domcontentloaded", "timeout": 30000}]
