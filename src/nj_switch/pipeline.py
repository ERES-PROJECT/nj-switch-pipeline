"""One collection path for the CLI, legacy facade, and offline replay."""
import json
import re
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from bs4 import BeautifulSoup

from .contracts import extract_contract, match_contract
from .evidence import ArtifactStore, MAX_BYTES, redact, safe_url
from .models import CollectionResult, DocumentRef, Query, utc_now
from .navigation import STRATEGIES, NavigationResult, SourceUnavailable, UnsupportedContext
from .offers import deduplicate, document_links, parse_html, parse_json
from .profiles import (DIRECT_PRODUCTS_URL, DIRECT_UTILITY_URL, INDRA_ENDPOINT,
                       THINK_ENDPOINT, direct_energy_diagnostics, verified_offers)
from .registry import utility_matches
from .transport import AccessError, Transport


def add_completion_issue(result: CollectionResult, message: str) -> None:
    """Record a scraper-integrity problem that must prevent strict success."""
    if message not in result.completion_issues:
        result.completion_issues.append(message)
    if message not in result.warnings:
        result.warnings.append(message)


def record_document_download_failure(result: CollectionResult, url: str,
                                     exc: Exception) -> None:
    """Retain a failed document fetch and classify known source-policy blocks."""
    message = str(redact(str(exc)))[:500]
    clean_url = safe_url(url)
    result.errors.append({
        "category": "document_download", "url": clean_url, "message": message,
    })
    if (
        result.query.adapter == "indra_energy"
        and isinstance(exc, AccessError)
        and "robots policy disallows this url" in message.casefold()
    ):
        evidence = result.source_evidence.setdefault("indra_terms", {})
        blocked_urls = set(evidence.get("policy_blocked_urls", []))
        blocked_urls.add(clean_url)
        evidence.update({
            "automated_document_access": "disallowed_by_source_robots_policy",
            "document_access_retryable": False,
            "policy_blocked_urls": sorted(blocked_urls),
        })


def terminal_document_host_failure(exc: Exception) -> bool:
    """Return true only for a host-wide TLS trust failure that retries cannot repair."""
    message = str(exc).casefold()
    return "certificate_verify_failed" in message or "certificate verify failed" in message


def exhausted_document_host_network_failure(exc: Exception) -> bool:
    """Stop repeating a host failure after Transport has exhausted its retries."""
    message = str(exc).casefold()
    return any(marker in message for marker in (
        "getaddrinfo",
        "name or service not known",
        "nodename nor servname",
        "connecterror",
        "connecttimeout",
        "readtimeout",
        "connection refused",
    ))


def finalize_indra_document_access(result: CollectionResult,
                                   refs: list[DocumentRef]) -> None:
    """Summarize Indra discovery separately from permitted document transport."""
    if result.query.adapter != "indra_energy":
        return
    evidence = result.source_evidence.setdefault("indra_terms", {})
    discovered_urls = {safe_url(ref.url) for ref in refs}
    blocked_urls = set(evidence.get("policy_blocked_urls", []))
    downloaded_urls = {
        safe_url(source_url)
        for contract in result.contracts
        for source_url in (contract.source_urls or [contract.url])
    }
    evidence.update({
        "discovered_document_count": len(discovered_urls),
        "downloaded_document_count": len(discovered_urls & downloaded_urls),
        "policy_blocked_document_count": len(discovered_urls & blocked_urls),
    })
    if not discovered_urls:
        evidence["document_access_state"] = "no_documents_discovered"
        evidence["source_absence_rule_applicable"] = False
        evidence["source_absence_evidence_required"] = True
    elif discovered_urls <= blocked_urls:
        evidence["document_access_state"] = "all_discovered_documents_policy_blocked"
        evidence["source_absence_rule_applicable"] = False
    elif discovered_urls <= downloaded_urls:
        evidence["document_access_state"] = "all_discovered_documents_downloaded"
        evidence["source_absence_rule_applicable"] = False
    else:
        evidence["document_access_state"] = "document_access_incomplete"
        evidence["source_absence_rule_applicable"] = False


def nextera_document_product_id(url: str) -> str | None:
    """Recover NextEra's composite product identity from its document route."""
    match = re.search(r"/Document/Get(?:EDL|CSTOS)/([^/?#]+)", url, re.I)
    return unquote(match.group(1)).replace(",", "|") if match else None


def scope_nextera_offer_documents(offers) -> None:
    """Discard links injected into the wrong card by NextEra's duplicate modal IDs."""
    for offer in offers:
        correctly_scoped = []
        for ref in offer.documents:
            route_product_id = nextera_document_product_id(ref.url)
            if route_product_id != offer.product_id:
                continue
            ref.product_id = route_product_id
            ref.offer_key = offer.key
            correctly_scoped.append(ref)
        offer.documents = correctly_scoped


def resolve_direct_renewable_conflicts(result: CollectionResult) -> None:
    """Resolve Direct's API flag conflict only from a connected plan contract."""
    warning = "API greenFlag=false conflicts with GREENOFFER; consult environmental disclosure"
    if result.query.adapter != "direct_energy":
        return
    for offer in result.offers:
        if warning not in offer.warnings:
            continue
        contracts = [
            contract for contract in result.contracts
            if offer.key in contract.matched_offer_keys
            and contract.status in {"parsed", "text_extracted", "retained"}
        ]
        proof = next((
            contract for contract in contracts
            if re.search(
                r"(?:supported\s+)?100%\s+by\s+renewable\s+energy\s+credits|100%\s+renewable",
                "\n".join(contract.sections.values()) + "\n" + contract.raw_text,
                re.I,
            )
        ), None)
        if proof is None:
            continue
        offer.renewable_percentage = Decimal("100")
        offer.renewable_source = "connected supplier contract summary"
        offer.warnings = [item for item in offer.warnings if item != warning]
        offer.raw_fields["green_flag_conflict_resolved_by_contract_id"] = proof.id


def fetch_direct_public_api(transport: Transport, store: ArtifactStore,
                            query: Query, browser_context=None) -> tuple[NavigationResult, list[tuple]]:
    """Replay Direct's observed ZIP GET then utility-specific product POST."""
    payloads = []
    utility_url = DIRECT_UTILITY_URL.format(zip_code=query.zip)
    data, content_type, final_url = transport.request(
        utility_url, browser_context=browser_context
    )
    if "json" not in content_type.casefold():
        raise ValueError(f"Direct public API returned non-JSON content: {content_type}")
    utility_payload = json.loads(data)
    if not isinstance(utility_payload, dict):
        raise ValueError("Direct public API returned a non-object payload")
    utility_artifact = store.save(
        utility_payload, "json", final_url, method="GET", content_type=content_type
    )
    payloads.append((utility_payload, final_url, utility_artifact["id"]))
    utility_evidence = direct_energy_diagnostics(payloads, query)
    if len(utility_evidence["utility_codes"]) != 1:
        raise ValueError("Direct public ZIP API did not prove exactly one requested NJ utility")
    product_body = {
        "district": "",
        "utilityCode": utility_evidence["utility_codes"][0],
        "brand": "deeast",
        "transactionType": "new",
        "channel": "COM",
        "term": "",
    }
    data, content_type, final_url = transport.request(
        DIRECT_PRODUCTS_URL, browser_context=browser_context,
        method="POST", body=product_body,
    )
    if "json" not in content_type.casefold():
        raise ValueError(f"Direct public API returned non-JSON content: {content_type}")
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise ValueError("Direct public API returned a non-object payload")
    artifact = store.save(
        payload, "json", final_url, method="POST", request_body=product_body,
        content_type=content_type,
    )
    payloads.append((payload, final_url, artifact["id"]))

    diagnostics = direct_energy_diagnostics(payloads, query)
    if diagnostics["utility_response_count"] != 1 or len(diagnostics["utility_codes"]) != 1:
        raise ValueError("Direct public ZIP API did not prove exactly one requested NJ utility")
    if diagnostics["product_response_count"] != 1:
        raise ValueError("Direct public products API did not return one valid catalog snapshot")
    offers = verified_offers(payloads, query)
    disposition = None if offers else "empty"
    return NavigationResult(
        url=DIRECT_PRODUCTS_URL,
        context_verified=True,
        live_data_verified=True,
        disposition=disposition,
        evidence={"direct_public_api": {
            "utility_artifact_id": diagnostics["utility_artifact_id"],
            "product_artifact_id": diagnostics["product_artifact_id"],
            "scoped_product_count": diagnostics["source_product_count"],
        }},
        notes=[
            "Direct current offers were fetched from the supplier-owned public ZIP utility and products endpoints with normal robots and transport checks",
        ],
    ), payloads


def media_kind(data: bytes, content_type: str = "") -> str:
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"PK"):
        return "docx"
    return "html" if "html" in content_type or b"<" in data[:200] else "txt"


def add_contract(result, contract, refs):
    labels = " ".join(ref.label for ref in refs).lower()
    if (result.query.adapter in {"major_energy", "indra_energy"} and
            ("terms of service" in labels or "terms and conditions" in labels)):
        # These suppliers explicitly label the plan-linked files as terms, not
        # NJ contract summaries. Do not impose the summary's twelve-section
        # schema merely because comprehensive terms contain several headings.
        contract.document_kind = "terms_or_other"
        if contract.raw_text.strip() and contract.status != "failed":
            contract.status = "text_extracted"
            contract.warnings = [
                warning for warning in contract.warnings
                if warning != "No standardized contract sections identified"
                and not warning.startswith("Missing sections:")
            ]
            contract.missing_sections = []
    elif "summary" in labels or len(contract.sections) >= 3:
        contract.document_kind = "contract_summary"
    else:
        contract.document_kind = "environmental" if "environment" in labels else "promotion" if "promotion" in labels else "terms_or_other"
        # Only contract summaries are required to provide the standardized
        # twelve-section NJ summary. A linked TOS/disclosure remains useful
        # connected evidence even when it contains a subset of those topics.
        if contract.raw_text.strip() and contract.status != "failed":
            contract.status = "text_extracted"
            contract.warnings = [
                warning for warning in contract.warnings
                if warning != "No standardized contract sections identified"
                and not warning.startswith("Missing sections:")
            ]
            contract.missing_sections = []
        elif (contract.media_type == "application/pdf" and
              contract.status == "needs_review" and refs and
              all(ref.offer_key or ref.product_id for ref in refs)):
            # Some supplier-generated disclosures are image-only PDFs. The
            # complete public binary, hash, URL, and stable plan association
            # are still reproducible evidence even when no text layer exists.
            # Record that limitation structurally instead of pretending OCR
            # occurred or rejecting an otherwise collected connected document.
            contract.status = "retained"
            contract.fields["binary_retained_without_text_layer"] = True
            contract.fields["source_limitation"] = "public PDF contains no extractable text layer"
            contract.warnings = []
            contract.missing_sections = []
    if (contract.document_kind == "contract_summary" and result.context_verified and
            result.live_data_verified and "distribution_company" not in contract.sections):
        contract.sections["distribution_company"] = (
            f"Verified collection context: {result.query.utility}"
        )
        contract.missing_sections = [
            section for section in contract.missing_sections if section != "distribution_company"
        ]
        contract.warnings = [
            warning for warning in contract.warnings
            if not warning.startswith("Missing sections:")
        ]
        if contract.missing_sections:
            contract.warnings.append("Missing sections: " + ", ".join(contract.missing_sections))
        elif contract.status == "partial":
            contract.status = "parsed"
    if (contract.document_kind == "contract_summary" and
            result.query.adapter == "cleansky_energy" and
            "supplier_information" not in contract.sections):
        # CleanSky's NJ summary prints the supplier contact block without the
        # standard NJBPU heading. Retain only values explicitly printed in the
        # captured summary instead of inventing an absent labeled section.
        contact_patterns = (
            r"3355 W\. Alabama[^\n]*",
            r"www\.CleanSkyEnergy\.com",
            r"CustomerCare@CleanSkyEnergy\.com",
            r"888-355-6205",
        )
        contacts = [match.group(0) for pattern in contact_patterns
                    if (match := re.search(pattern, contract.raw_text, re.I))]
        if contacts:
            contract.sections["supplier_information"] = "CleanSky Energy\n" + "\n".join(contacts)
            contract.missing_sections = [
                section for section in contract.missing_sections
                if section != "supplier_information"
            ]
            contract.warnings = [
                warning for warning in contract.warnings
                if not warning.startswith("Missing sections:")
            ]
            if contract.missing_sections:
                contract.warnings.append("Missing sections: " + ", ".join(contract.missing_sections))
            elif contract.status == "partial":
                contract.status = "parsed"
    match_contract(contract, refs, result.offers)
    if (contract.document_kind == "contract_summary" and
            contract.missing_sections == ["incentives"] and
            contract.matched_offer_keys):
        linked = [
            offer for offer in result.offers
            if offer.key in contract.matched_offer_keys
        ]
        disclosed = [
            incentive for offer in linked for incentive in offer.incentives
            if incentive.strip()
        ]
        if disclosed:
            contract.sections["incentives"] = "\n".join(dict.fromkeys(disclosed))
        else:
            # A required NJ summary heading can be absent from a supplier's
            # generated form. Record that observed absence explicitly rather
            # than inventing a promotion or permanently failing an otherwise
            # complete, plan-linked source document.
            contract.sections["incentives"] = (
                "No incentive stated in the connected public plan card or contract summary."
            )
            contract.fields.setdefault("source_absent_sections", []).append("incentives")
        contract.missing_sections = []
        contract.warnings = [
            warning for warning in contract.warnings
            if not warning.startswith("Missing sections:")
        ]
        contract.status = "parsed"
    if (not contract.matched_offer_keys and contract.document_kind != "contract_summary" and refs and
            all(not ref.offer_key and not ref.product_id for ref in refs)):
        contract.warnings = [
            warning for warning in contract.warnings
            if warning != "No unambiguous plan association; document retained for review"
        ]
        contract.match_method = "market_level_public_document"
    contract.source_urls = [contract.url]
    previous = next((c for c in result.contracts if c.id == contract.id), None)
    if previous:
        previous.matched_offer_keys = sorted(set(previous.matched_offer_keys + contract.matched_offer_keys))
        previous.source_urls = sorted(set(previous.source_urls + contract.source_urls))
        previous.warnings = sorted(set(previous.warnings + contract.warnings))
    else:
        result.contracts.append(contract)


def scoped_document_refs(query: Query, refs: list[DocumentRef], offers) -> list[DocumentRef]:
    """Keep supplier-owned, in-market documents and prefer plan-scoped links."""
    allowed_domains = {
        "clearview_energy": ("clearviewenergy.com",),
        "njgande": ("njgande.com", "usgande.com"),
        "idt_energy": ("idtenergy.com",),
        "direct_energy": ("directenergy.com", "directenergydocuments.gesc.com"),
        "nextera_energy_services": ("nexteraenergyservices.com",),
        "indra_energy": ("indraenergy.com",),
    }.get(query.adapter)
    offer_ids = {offer.product_id for offer in offers if offer.product_id}
    offer_keys = {offer.key for offer in offers}
    retained = []
    for ref in refs:
        if query.adapter == "idt_energy" and "/get-started/your-offers/environmental-disclosure-labels/" in ref.url:
            ref.url = ref.url.replace(
                "/get-started/your-offers/environmental-disclosure-labels/",
                "/environmental-disclosure-labels/",
            )
        parsed = urlsplit(ref.url)
        host = (parsed.hostname or "").casefold()
        if (query.adapter in {"major_energy", "american_power_and_gas"} and
                not ref.offer_key and not ref.product_id and
                re.search(r"/(?:terms-of-use|privacy-policy|legal-notices-and-terms)/?$", parsed.path, re.I)):
            # Footer/site-use policies do not describe the selected energy
            # product and must never satisfy plan-document completeness.
            continue
        if query.adapter in {"direct_energy", "nextera_energy_services", "indra_energy"} and not (
                ref.offer_key or ref.product_id):
            # These adapters expose plan-specific legal links. Footer/sitewide
            # legal pages cannot stand in for a connected offer document.
            continue
        if allowed_domains and not any(host == domain or host.endswith("." + domain) for domain in allowed_domains):
            continue
        if ref.offer_key and ref.offer_key not in offer_keys:
            continue
        if ref.product_id and ref.product_id not in offer_ids:
            continue
        params = parse_qs(parsed.query)
        product_values = {
            value for key in ("productNum", "productid", "productId", "sku", "rateId")
            for value in params.get(key, [])
        }
        if not ref.offer_key and not ref.product_id and product_values and product_values.isdisjoint(offer_ids):
            continue
        retained.append(ref)

    specific_paths = {
        (urlsplit(ref.url).hostname, urlsplit(ref.url).path)
        for ref in retained if ref.offer_key or ref.product_id
    }
    if query.adapter == "constellation" and specific_paths:
        # The signup page also contains unrelated site-wide legal links. Once
        # plan-scoped contracts exist, only those links describe these offers.
        retained = [ref for ref in retained if ref.offer_key or ref.product_id]
    by_identity = {}
    for ref in retained:
        path_key = (urlsplit(ref.url).hostname, urlsplit(ref.url).path)
        if not ref.offer_key and not ref.product_id and path_key in specific_paths:
            continue
        identity = (ref.url, ref.offer_key or "", ref.product_id or "")
        by_identity.setdefault(identity, ref)
    return list(by_identity.values())


def bind_document_refs(offers, refs: list[DocumentRef]) -> None:
    """Copy already-scoped stable references onto their matching offers."""
    for offer in offers:
        for ref in refs:
            if not (
                (ref.offer_key and ref.offer_key == offer.key) or
                (ref.product_id and ref.product_id == offer.product_id)
            ):
                continue
            ref.offer_key = offer.key
            if not ref.product_id:
                ref.product_id = offer.product_id
            if not any(existing.url == ref.url for existing in offer.documents):
                offer.documents.append(ref)


class NetworkCapture:
    def __init__(self, store: ArtifactStore, result: CollectionResult):
        self.store, self.result = store, result
        self.payloads = []
        self.enabled = True

    def finished(self, request):
        if not self.enabled or len(self.payloads) >= 40 or request.resource_type not in ("xhr", "fetch"):
            return
        host = urlsplit(request.url).hostname or ""
        domains = ("directenergy.com", "picknrg.com", "ambitenergy.com", "thinkenergy.com", "onproton.io", "majorenergy.com", "xoomenergy.com", "constellationrates.com", "ptsrvs.com", "frontierutilities.com", "cleanchoiceenergy.com", "indraenergy.com", "nexteraenergyservices.com")
        if not any(host == d or host.endswith("." + d) for d in domains):
            return
        if re.search(r"auth|ipaddress|analytics|telemetry|settings|cookie|blocklist", request.url, re.I):
            return
        try:
            response = request.response()
            if not response or response.status != 200 or "json" not in response.headers.get("content-type", ""):
                return
            data = response.body()
            if len(data) > MAX_BYTES:
                self.result.warnings.append("Oversized JSON response skipped: " + safe_url(request.url))
                return
            payload = json.loads(data)
            keys = " ".join(payload) if isinstance(payload, dict) else "list"
            if not re.search(r"offer|plan|product|rate|utilit|tdsp|provider|list", keys, re.I):
                return
            request_body = None
            try:
                request_body = request.post_data_json
            except Exception:
                pass
            artifact = self.store.save(payload, "json", request.url, method=request.method, status=response.status,
                                       request_body=request_body)
            self.payloads.append((payload, request.url, artifact["id"]))
            self.result.candidates.append({"url": safe_url(request.url), "method": request.method,
                                           "artifact_id": artifact["id"],
                                           "keys": list(payload)[:25] if isinstance(payload, dict) else ["list"],
                                           "classification": "unverified_json_response"})
        except Exception as exc:
            self.result.warnings.append("JSON capture failed: " + type(exc).__name__)


NRG_PRODUCT_CHART_URL = "https://www.picknrg.com/en/electricity-and-gas/loadProductChart"
NRG_UTILITY_SLUGS = {
    "PSE&G Electric": "pseg",
    "ACE Electric": "ace",
    "Rockland Electric": "reco",
    "PSE&G Gas": "pseg_gas",
    "SJG Gas": "sjersey",
}


def nrg_product_request_evidence(payloads: list[tuple], artifacts: list[dict],
                                 query: Query) -> dict:
    """Validate the exact ZIP/utility context submitted to NRG's product API.

    Some NRG sessions advance directly to the product chart without rendering
    the utility selector.  In that path the captured POST body—not the chart's
    generic visible shell—is the strongest same-request qualification evidence.
    Require one and only one product request, and fail closed on every scoped
    field so a stale or foreign response can never promote offers.
    """
    product_artifact_ids = {
        artifact_id
        for _payload, url, artifact_id in payloads
        if url == NRG_PRODUCT_CHART_URL
    }
    product_artifacts = [
        artifact for artifact in artifacts
        if artifact.get("id") in product_artifact_ids
        and artifact.get("url") == NRG_PRODUCT_CHART_URL
    ]
    evidence = {
        "qualified": False,
        "captured_product_request_count": len(product_artifacts),
        "artifact_ids": sorted(product_artifact_ids),
    }
    if len(product_artifacts) != 1:
        evidence["reason"] = "expected exactly one captured NRG product request"
        return evidence

    artifact = product_artifacts[0]
    body = artifact.get("request_body")
    if artifact.get("method") != "POST" or artifact.get("status") != 200 or not isinstance(body, dict):
        evidence["reason"] = "NRG product request metadata is incomplete"
        return evidence

    expected_slug = NRG_UTILITY_SLUGS.get(query.utility)
    if query.commodity == "electric":
        scoped = {
            "utility_slug": body.get("utilitySlugElectric"),
            "utility_name": body.get("utilitySlugElectricName"),
            "utility_preference": body.get("utilityPref"),
            "only_commodity": body.get("onlyElectricity"),
            "units": body.get("electricUnits"),
        }
        expected_preference, expected_units = "E", "kwh"
    else:
        scoped = {
            "utility_slug": body.get("utilitySlugGas"),
            "utility_name": body.get("utilitySlugGasName"),
            "utility_preference": body.get("utilityPref"),
            "only_commodity": body.get("onlyGas"),
            "units": body.get("gasUnits"),
        }
        expected_preference, expected_units = "G", "thm"

    evidence["request"] = {
        "zip": body.get("zipcode"),
        "state": body.get("stateSlug"),
        **scoped,
    }
    checks = {
        "zip": str(body.get("zipcode") or "") == query.zip,
        "state": str(body.get("stateSlug") or "").casefold() == "nj",
        "utility_slug": bool(expected_slug) and scoped["utility_slug"] == expected_slug,
        "utility_name": utility_matches(str(scoped["utility_name"] or ""), query.utility),
        "utility_preference": scoped["utility_preference"] == expected_preference,
        "only_commodity": scoped["only_commodity"] == "Y",
        "units": str(scoped["units"] or "").casefold() == expected_units,
    }
    evidence["checks"] = checks
    evidence["qualified"] = all(checks.values())
    if not evidence["qualified"]:
        evidence["reason"] = "NRG product request does not exactly match the requested market"
    return evidence


def assemble(result: CollectionResult, nav: NavigationResult, store: ArtifactStore,
             payloads: list[tuple] | None = None,
             allow_replay_offers: bool = False) -> list[DocumentRef]:
    result.context_verified = nav.context_verified
    result.live_data_verified = nav.live_data_verified
    result.warnings.extend(nav.notes)
    result.source_evidence.update(nav.evidence)
    refs = []
    source_offer_keys = set()
    direct_diagnostics = None
    rendered_offer_count = None
    nextera_detail_ids = set()
    nextera_document_ids = set()

    def retain_candidates(offers, classification: str):
        for offer in offers:
            result.candidates.append({
                "classification": classification,
                "supplier": offer.supplier,
                "utility": offer.utility,
                "commodity": offer.commodity,
                "zip": offer.zip,
                "name": offer.name,
                "product_id": offer.product_id,
                "rate": str(offer.price.value),
                "rate_unit": offer.price.unit,
                "source_url": safe_url(offer.source_url),
                "artifact_id": offer.artifact_id,
            })

    if nav.html:
        artifact = store.save(nav.html, "html", nav.url)
        parsed = parse_html(nav.html, result.query, nav.url, artifact["id"])
        if result.query.adapter == "direct_energy":
            rendered_offer_count = len(parsed)
        source_offer_keys.update(offer.key for offer in parsed)
        if nav.live_data_verified or allow_replay_offers:
            result.offers.extend(parsed)
        else:
            retain_candidates(parsed, "current_page_offer_not_zip_verified")
        refs.extend(document_links(nav.html, nav.url, artifact_id=artifact["id"]))
        # Preserve public embedded state separately, with key-based redaction.
        soup = BeautifulSoup(nav.html, "lxml")
        for script in soup.select('script[type="application/json"], script[type="application/ld+json"], script#__NEXT_DATA__'):
            try:
                payload = json.loads(script.string or script.get_text())
                item = store.save(payload, "json", nav.url)
                payloads = (payloads or []) + [(payload, nav.url, item["id"])]
            except (ValueError, TypeError):
                continue
    for fragment in nav.fragments:
        html = fragment["html"]
        artifact = store.save(html, "html", fragment["url"])
        origin_offers = parse_html(fragment.get("origin", ""), result.query, nav.url, artifact["id"])
        # Ambit's offers themselves are inside the temporary dialog.
        dialog_offers = parse_html('<div class="ngdialog-content">' + html + '</div>', result.query, nav.url, artifact["id"]) if result.query.adapter == "ambit" else []
        # NextEra fragments enrich an offer already parsed from the main card;
        # parsing the origin again can create a duplicate when the supplier's
        # AJAX modal text is injected into the card DOM.
        parsed = [] if result.query.adapter == "nextera_energy_services" else origin_offers + dialog_offers
        source_offer_keys.update(offer.key for offer in parsed)
        if nav.live_data_verified or allow_replay_offers:
            result.offers.extend(parsed)
        else:
            retain_candidates(parsed, "current_fragment_offer_not_zip_verified")
        association = origin_offers or dialog_offers
        ref_key = fragment.get("offer_key") or (association[0].key if len(association) == 1 else None)
        product_id = fragment.get("product_id") or (association[0].product_id if len(association) == 1 else None)
        fragment_refs = document_links(html, fragment["url"], product_id, ref_key, artifact["id"])
        if result.query.adapter == "nextera_energy_services":
            for ref in fragment_refs:
                if route_product_id := nextera_document_product_id(ref.url):
                    ref.product_id = route_product_id
                    ref.offer_key = None
        refs.extend(fragment_refs)
        if result.query.adapter == "nextera_energy_services" and product_id:
            nextera_detail_ids.add(product_id)
    trusted = verified_offers(payloads or [], result.query)
    if result.query.adapter == "direct_energy":
        direct_diagnostics = direct_energy_diagnostics(payloads or [], result.query)
        result.source_evidence["direct_api"] = {
            key: direct_diagnostics[key] for key in (
                "utility_response_count", "product_response_count",
                "utility_artifact_id", "product_artifact_id",
            )
        }
        codes = direct_diagnostics["utility_codes"]
        if len(codes) != 1:
            add_completion_issue(result,
                "Direct ZIP utility evidence was absent or ambiguous: "
                f"expected one exact utility code, found {len(codes)}"
            )
        if not direct_diagnostics["product_response_count"]:
            add_completion_issue(result, "Direct product API evidence was not captured for this navigation")
        if direct_diagnostics["missing_offer_code_count"]:
            add_completion_issue(result,
                "Direct source products missing offerCode: "
                f"{direct_diagnostics['missing_offer_code_count']}"
            )
        if direct_diagnostics["duplicate_offer_codes"]:
            add_completion_issue(result,
                "Direct source returned duplicate offerCode values: "
                + ", ".join(direct_diagnostics["duplicate_offer_codes"])
            )
        if direct_diagnostics["invalid_document_fields"]:
            add_completion_issue(result,
                "Direct source returned invalid plan-document routes: "
                + ", ".join(direct_diagnostics["invalid_document_fields"])
            )
    if trusted:
        source_offer_keys = {offer.key for offer in trusted}
    if result.query.adapter == "nrg" and trusted:
        nrg_evidence = nrg_product_request_evidence(
            payloads or [], store.records, result.query
        )
        result.source_evidence["nrg_product_request"] = nrg_evidence
        if nrg_evidence["qualified"]:
            result.context_verified = True
            result.live_data_verified = True
    trusted_context = nav.live_data_verified or allow_replay_offers or (
        result.query.adapter == "direct_energy" and bool(trusted)
    ) or (
        result.query.adapter == "nrg"
        and result.source_evidence.get("nrg_product_request", {}).get("qualified", False)
    )
    if trusted and trusted_context:
        # API identifiers join rendered document links without matching on price.
        for offer in trusted:
            for card in result.offers:
                if card.product_id and card.product_id == offer.product_id:
                    for ref in card.documents:
                        ref.offer_key = offer.key
                        offer.documents.append(ref)
            for ref in refs:
                if ref.product_id and ref.product_id == offer.product_id:
                    ref.offer_key = offer.key
                    if not any(existing.url == ref.url for existing in offer.documents):
                        offer.documents.append(ref)
        # NRG's API carries SKU and its rendered legal links carry the same SKU,
        # even if a card layout no longer yields a parseable DOM price/title.
        if result.query.adapter == "nrg":
            from urllib.parse import parse_qs
            for ref in refs:
                sku = parse_qs(urlsplit(ref.url).query).get("sku", [None])[0]
                for offer in trusted:
                    if sku and sku == offer.product_id:
                        ref.product_id, ref.offer_key = sku, offer.key
                        offer.documents.append(ref)
        result.offers = trusted
        result.context_verified = True
        if not result.replayed:
            result.live_data_verified = True
    elif trusted:
        retain_candidates(trusted, "trusted_product_payload_not_zip_verified")
    for payload, url, artifact_id in payloads or []:
        if trusted:
            break
        candidates = parse_json(payload, result.query, url, artifact_id)
        # A captured response may include plans for multiple utilities. Discovery
        # is evidence, not proof. Only a verified adapter profile can promote it.
        for offer in candidates:
            offer.warnings.append("Unverified JSON offer candidate; compare territory and units before use")
        retain_candidates(candidates, "unverified_json_offer_candidate")
    result.offers = deduplicate(result.offers)
    if direct_diagnostics and direct_diagnostics["product_response_count"]:
        result.source_offer_count = direct_diagnostics["source_product_count"]
        result.source_evidence["direct_api"]["rendered_offer_count"] = rendered_offer_count
        result.source_evidence["direct_api"]["scoped_product_count"] = result.source_offer_count
        if rendered_offer_count != result.source_offer_count:
            add_completion_issue(result,
                "Direct rendered/API plan-count mismatch: "
                f"{rendered_offer_count} rendered offers, {result.source_offer_count} API products"
            )
        if result.source_offer_count != len(result.offers):
            add_completion_issue(result,
                "Direct source/normalized plan-count mismatch: "
                f"{result.source_offer_count} source products, {len(result.offers)} exported offers"
            )
    else:
        result.source_offer_count = len(source_offer_keys) if source_offer_keys else None
    if result.query.adapter == "nextera_energy_services":
        scope_nextera_offer_documents(result.offers)
    for offer in result.offers:
        refs.extend(offer.documents)
    refs = scoped_document_refs(result.query, refs, result.offers)
    # Rebuild offer associations only from fully scoped references. This keeps
    # a rejected foreign/footer link from surviving on the offer even though it
    # was correctly excluded from the document download queue.
    for offer in result.offers:
        offer.documents = []
    bind_document_refs(result.offers, refs)
    if result.query.adapter == "nextera_energy_services":
        offer_ids = {offer.product_id for offer in result.offers if offer.product_id}
        nextera_document_ids = {
            ref.product_id for ref in refs
            if ref.product_id and ref.product_id in offer_ids
        }
        result.source_evidence["nextera_details"] = {
            "offer_product_ids": sorted(offer_ids),
            "captured_detail_product_ids": sorted(nextera_detail_ids),
            "document_product_ids": sorted(nextera_document_ids),
        }
        missing_details = sorted(offer_ids - nextera_detail_ids)
        if missing_details:
            add_completion_issue(result,
                "NextEra offers missing captured detail panels: " + ", ".join(missing_details)
            )
    if result.query.adapter == "indra_energy":
        expected_ids = {offer.product_id for offer in result.offers if offer.product_id}
        evidence = result.source_evidence.setdefault("indra_terms", {})
        observed_ids = set(evidence.get("observed_product_ids", []))
        retained_document_ids = {
            ref.product_id for ref in refs
            if ref.product_id and ref.product_id in expected_ids
        }
        evidence["expected_product_ids"] = sorted(expected_ids)
        evidence["retained_document_product_ids"] = sorted(retained_document_ids)
        missing_details = sorted(expected_ids - observed_ids)
        unexpected_details = sorted(observed_ids - expected_ids)
        missing_documents = sorted(expected_ids - retained_document_ids)
        if missing_details:
            add_completion_issue(result,
                "Indra offers missing rendered detail identity: " + ", ".join(missing_details)
            )
        if unexpected_details:
            add_completion_issue(result,
                "Indra rendered unknown detail identities: " + ", ".join(unexpected_details)
            )
        if missing_documents:
            add_completion_issue(result,
                "Indra offers missing retained terms documents: " + ", ".join(missing_documents)
            )
    result.collection_method = "browser_dom" if result.offers else "discovery_only"
    if trusted:
        result.collection_method = "browser_bootstrap_api"
    return refs


def finalize(result: CollectionResult, store: ArtifactStore, discovery: bool = False):
    resolve_direct_renewable_conflicts(result)
    for offer in result.offers:
        offer.source_url = safe_url(offer.source_url)
        offer.raw_fields = redact(offer.raw_fields)
        for ref in offer.documents:
            ref.url = safe_url(ref.url)
    for contract in result.contracts:
        contract.url = safe_url(contract.url)
        contract.source_urls = [safe_url(url) for url in contract.source_urls]
    result.artifacts = store.records
    result.finished_at = utc_now()
    if result.query.skip_reason:
        result.status = "unsupported"
    elif result.status in ("blocked", "unsupported", "empty"):
        pass
    elif not result.offers and result.candidates:
        result.status = "needs_review"
        result.warnings.append("Offer-like data was retained as evidence but not promoted because ZIP/utility live-data qualification was not proven")
    elif not result.offers:
        result.status = "failed" if result.errors or result.query.adapter != "default" else "unsupported"
        result.warnings.append("No verified offers; this is not evidence the supplier has no plans")
    elif not result.context_verified or not result.live_data_verified:
        result.status = "needs_review"
    elif result.completion_issues or discovery or result.errors or any(
            o.warnings or not (
                any(
                    c.status in ("parsed", "text_extracted", "retained") and o.key in c.matched_offer_keys
                    for c in result.contracts
                ) or any(
                    c.status in ("parsed", "text_extracted", "retained") and
                    c.match_method == "market_level_public_document"
                    for c in result.contracts
                )
            ) for o in result.offers) or any(
                c.status not in ("parsed", "text_extracted", "retained") or c.warnings
                for c in result.contracts
            ):
        result.status = "partial"
    else:
        result.status = "success"


def browser_context_options() -> dict:
    """Build a context without ever reading a user's browser profile."""
    return {"accept_downloads": True, "viewport": {"width": 1360, "height": 900}}


def collect(query: Query, browser, output: Path, discovery: bool = False,
            shared_context=None) -> CollectionResult:
    result = CollectionResult(query=query)
    store = ArtifactStore(output / "artifacts")
    if query.skip_reason:
        result.warnings.append(query.skip_reason)
        finalize(result, store)
        return result
    transport = Transport()
    context = None
    page = None
    owns_context = shared_context is None
    capture = NetworkCapture(store, result)
    try:
        transport.allowed(query.url)
        context = shared_context or browser.new_context(**browser_context_options())
        page = context.new_page()
        page.capture_stage = lambda stage: store.save(page.content(), "html", page.url, stage=stage)
        page.set_default_timeout(7000)
        context.on("requestfinished", capture.finished)
        page.on("dialog", lambda dialog: dialog.dismiss())
        nav = None
        indra_api_nav = None
        direct_api = False
        if query.adapter == "indra_energy":
            try:
                url = f"{INDRA_ENDPOINT}?zip={query.zip}"
                data, _, url = transport.request(url)
                payload = json.loads(data)
                artifact = store.save(payload, "json", url, method="GET")
                scoped = verified_offers([(payload, url, artifact["id"])], query)
                rates = payload.get("data", {}).get("rates", {}) if isinstance(payload, dict) else {}
                commodity_rates = rates.get(query.commodity, []) if isinstance(rates, dict) else []
                target = [item for item in commodity_rates if isinstance(item, dict)
                          and item.get("state") == "NJ"
                          and item.get("zipCode") == query.zip
                          and utility_matches(item.get("utilityName") or item.get("utility", ""), query.utility)]
                if scoped:
                    capture.payloads.append((payload, url, artifact["id"]))
                    indra_api_nav = NavigationResult(
                        url=url, context_verified=True, live_data_verified=True,
                        notes=["Indra public rates API verified the requested ZIP, commodity, and utility"],
                    )
                    direct_api = True
                elif target:
                    nav = NavigationResult(url=url, context_verified=True, live_data_verified=True,
                                           notes=["Indra public API returned no parseable in-scope offers"])
                    result.status = "needs_review"
                    direct_api = True
                elif commodity_rates:
                    nav = NavigationResult(url=url, notes=["Indra public API does not list the requested utility for this ZIP"])
                    result.status = "unsupported"
                    direct_api = True
                else:
                    nav = NavigationResult(url=url, context_verified=True, live_data_verified=True,
                                           notes=["Indra public API returned no offers for this commodity and ZIP"])
                    result.status = "empty"
                    direct_api = True
            except Exception as exc:
                result.warnings.append("Indra public API unavailable; using browser fallback: " + type(exc).__name__)
        if query.adapter == "think_energy" and query.commodity == "electric":
            try:
                body = {"postal_code": query.zip, "promoCode": None, "locale": "en", "sales_channel": ""}
                data, _, url = transport.request(THINK_ENDPOINT, method="POST", body=body)
                payload = json.loads(data)
                artifact = store.save(payload, "json", url, method="POST", request_body=body)
                scoped = verified_offers([(payload, url, artifact["id"])], query)
                utilities = payload.get("tdsps", []) if isinstance(payload, dict) else []
                target = [u for u in utilities if u.get("state_code") == "NJ" and utility_matches(u.get("name", ""), query.utility)]
                if scoped:
                    capture.payloads.append((payload, url, artifact["id"]))
                    nav = NavigationResult(url=url, context_verified=True, live_data_verified=True)
                    direct_api = True
                elif target:
                    nav = NavigationResult(url=url, context_verified=True, live_data_verified=True,
                                           notes=["Think public API returned no in-scope supply offers for this utility"])
                    result.candidates.append({"url": safe_url(url), "method": "POST", "artifact_id": artifact["id"],
                                              "classification": "verified_utility_without_supply_offers"})
                    result.status = "empty"
                    direct_api = True
                elif utilities:
                    nav = NavigationResult(url=url, notes=["Think public API does not list the requested utility"])
                    result.status = "unsupported"
                    direct_api = True
            except Exception as exc:
                result.warnings.append("Direct API unavailable; using browser fallback: " + type(exc).__name__)
        try:
            if indra_api_nav is not None:
                try:
                    nav = STRATEGIES["indra_energy"](page, query)
                except Exception as exc:
                    # Current offers remain reproducible from the ZIP-qualified
                    # public rates API even if the optional terms service or
                    # rendered enrichment path is temporarily unavailable.
                    result.warnings.append(
                        "Indra rendered document enrichment unavailable: " + type(exc).__name__
                    )
                    nav = indra_api_nav
            elif nav is None:
                nav = STRATEGIES.get(query.adapter, STRATEGIES["default"])(page, query)
        except UnsupportedContext as exc:
            result.status = "unsupported"
            result.warnings.append(str(exc))
            nav = NavigationResult()
        except SourceUnavailable as exc:
            result.status = "blocked"
            result.errors.append({"category": "source_unavailable", "message": str(exc)})
            nav = NavigationResult()
        except Exception as exc:
            result.errors.append({"category": "navigation", "type": type(exc).__name__, "message": str(redact(str(exc)))[:1800]})
            try:
                nav = NavigationResult(html=page.content(), url=page.url)
            except Exception:
                nav = NavigationResult()
        capture.enabled = False
        if nav.disposition in {"empty", "unsupported", "blocked"}:
            result.status = nav.disposition
        refs = assemble(result, nav, store, capture.payloads)
        if direct_api:
            result.collection_method = "browser_enriched_api" if nav.html else "direct_http_api"
        if not discovery:
            by_url = {}
            for ref in refs:
                by_url.setdefault(ref.url, []).append(ref)
            browser_captured_urls = set()
            for document in nav.captured_documents:
                requested_url = document["requested_url"]
                same_url_refs = by_url.get(requested_url, [])
                if not same_url_refs:
                    add_completion_issue(
                        result,
                        "Browser-captured Major document had no retained plan reference: "
                        + safe_url(requested_url),
                    )
                    continue
                data = document["data"]
                content_type = document.get("content_type", "application/pdf")
                final_url = document.get("url") or requested_url
                kind = media_kind(data, content_type)
                artifact = store.save(data, kind, final_url, content_type=content_type)
                contract = extract_contract(data, safe_url(final_url), artifact["id"], content_type)
                add_contract(result, contract, same_url_refs)
                browser_captured_urls.add(requested_url)
            if nav.captured_documents:
                browser_evidence = {
                    "capture_method": "visible_plan_terms_click",
                    "captured_document_count": len(browser_captured_urls),
                    "captured_product_ids": sorted({
                        document["product_id"] for document in nav.captured_documents
                        if document.get("requested_url") in browser_captured_urls
                    }),
                }
                if result.query.adapter == "indra_energy":
                    result.source_evidence.setdefault("indra_terms", {}).update(browser_evidence)
                else:
                    result.source_evidence["major_browser_documents"] = browser_evidence
            terminal_host_failures = {}
            for url, same_url_refs in list(by_url.items())[:40]:
                if url in browser_captured_urls:
                    continue
                host = (urlsplit(url).hostname or "").casefold()
                if host in terminal_host_failures:
                    record_document_download_failure(
                        result, url, RuntimeError(
                            "Document fetch skipped after a terminal access failure on the same host: "
                            + terminal_host_failures[host]
                        )
                    )
                    continue
                try:
                    data, content_type, final_url = transport.get(url, context)
                    kind = media_kind(data, content_type)
                    content = data.decode("utf-8", errors="replace") if kind in ("html", "txt") else data
                    artifact = store.save(content, kind, final_url, content_type=content_type)
                    contract = extract_contract(data, safe_url(final_url), artifact["id"], content_type)
                    add_contract(result, contract, same_url_refs)
                except Exception as exc:
                    record_document_download_failure(result, url, exc)
                    if host and (
                        terminal_document_host_failure(exc)
                        or exhausted_document_host_network_failure(exc)
                    ):
                        terminal_host_failures[host] = str(redact(str(exc)))[:300]
            finalize_indra_document_access(result, refs)
        if result.errors:
            result.warnings.append("Failure HTML captured. Raw browser traces/screenshots disabled to avoid storing session or personal data.")
    except AccessError as exc:
        result.status = "blocked"
        result.errors.append({"category": "access_policy", "message": str(exc)})
    except Exception as exc:
        result.errors.append({"category": "collection", "type": type(exc).__name__, "message": str(redact(str(exc)))[:1000]})
    finally:
        capture.enabled = False
        if context:
            try:
                context.remove_listener("requestfinished", capture.finished)
            except Exception:
                pass
            try:
                if owns_context:
                    context.close()
                elif page:
                    page.close()
            except Exception as exc:
                result.errors.append({"category": "cleanup", "type": type(exc).__name__, "message": "Browser cleanup failed; run browser will be closed"})
        transport.close()
    finalize(result, store, discovery)
    return result


def replay(fixture: Path, output: Path) -> CollectionResult:
    """Offline fixture format is documented in the manual verification guide."""
    data = json.loads(fixture.read_text(encoding="utf-8"))
    query = Query.model_validate(data["query"])
    result = CollectionResult(query=query, replayed=True)
    if data.get("disposition") in {"empty", "unsupported", "blocked"}:
        result.status = data["disposition"]
    store = ArtifactStore(output / "artifacts")
    payloads = []
    for payload in data.get("payloads", []):
        artifact = store.save(payload["body"], "json", payload.get("url", query.url))
        payloads.append((payload["body"], payload.get("url", query.url), artifact["id"]))
    nav = NavigationResult(html=data.get("html", ""), url=data.get("source_url", query.url),
                           context_verified=data.get("context_verified", False),
                           live_data_verified=data.get("live_data_verified", data.get("context_verified", False)),
                           fragments=data.get("fragments", []),
                           evidence=data.get("evidence", {}))
    refs = assemble(result, nav, store, payloads, allow_replay_offers=True)
    for document in data.get("documents", []):
        if "path" in document:
            path = (fixture.parent / document["path"]).resolve()
            if not path.is_relative_to(fixture.parent.resolve()):
                raise ValueError("Fixture document path must stay inside its fixture directory")
            raw = path.read_bytes()
            kind = media_kind(raw)
            artifact = store.save(raw, kind, document["url"])
        else:
            raw = document["text"].encode()
            artifact = store.save(document["text"], "txt", document["url"])
        contract = extract_contract(raw, document["url"], artifact["id"])
        add_contract(result, contract, [r for r in refs if safe_url(r.url) == safe_url(document["url"])])
    for offer in result.offers:
        offer.captured_at = data.get("captured_at", "offline-synthetic-fixture")
    finalize(result, store)
    return result
