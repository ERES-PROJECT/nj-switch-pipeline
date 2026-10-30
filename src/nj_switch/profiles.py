"""Profiles promoted only after inspecting real response schemas.

Direct Energy: verified against 2026-09-04 /get-utilities-by-zip and
/eastrest/v1/products responses. Browser bootstrap may still be required.
"""
from decimal import Decimal
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlsplit

from .models import DocumentRef, Offer, Price, Query
from .offers import deduplicate, offer_key
from .registry import utility_matches
from .normalize import attributes

THINK_ENDPOINT = "https://api.thinkenergy.onproton.io/enrollment/get_tdsps_and_offers"
INDRA_ENDPOINT = "https://indraenergy.com/wp-json/indra-energy/v1/rates"
DIRECT_PRODUCTS_ENDPOINT = "/api/eastrest/v1/products"
DIRECT_PRODUCTS_URL = "https://api-oe.directenergy.com" + DIRECT_PRODUCTS_ENDPOINT
DIRECT_UTILITY_URL = (
    "https://api-oam.directenergy.com/api/east/deeast/v1/wcl/"
    "get-utilities-by-zip?zipcode={zip_code}"
)
DIRECT_DOCUMENT_HOST = "directenergydocuments.gesc.com"
DIRECT_DOCUMENT_CODES = {
    "tosURL": ("Contract Summary", "CDS"),
    "tcURL": ("Terms and Conditions", "TsNCs"),
    "eflURL": ("Environmental Disclosure", "EDL"),
}


def think_energy(payloads: list[tuple], query: Query) -> list[Offer]:
    """Observed residential electricity schema; community solar is not TPS supply."""
    if query.commodity != "electric":
        return []
    offers = []
    for payload, url, artifact_id in payloads:
        if url != THINK_ENDPOINT or not isinstance(payload, dict):
            continue
        for utility in payload.get("tdsps", []):
            if utility.get("state_code") != "NJ" or not utility_matches(utility.get("name", ""), query.utility):
                continue
            for product in utility.get("offers", []):
                if product.get("service_type") != "electricity" or product.get("offer_type") != "new":
                    continue
                if not utility_matches(product.get("tdsp", ""), query.utility):
                    continue
                billing = json.loads(product.get("billing") or "{}")
                display = json.loads(product.get("display") or "{}")
                meta = json.loads(product.get("meta_data") or "{}")
                # The public display expresses cents/kWh; cross-check the billing
                # dollars/kWh before using this source-specific conversion.
                value = Decimal(str(billing["commodity_rate"]))
                average = display.get("average_rate", {})
                if not average or any(Decimal(str(v)) != value * 100 for v in average.values()):
                    continue
                months = int(product["term_months"])
                product_id = str(product["rate_id"])
                key = offer_key(query, product["name"], product_id, months)
                raw_claims = "\n".join([product.get("description", ""), display.get("details_header", ""),
                                        *display.get("details_bullets", []), *display.get("summary_bullets", [])])
                attrs = attributes(BeautifulSoup(raw_claims, "lxml").get_text("\n", strip=True))
                if meta.get("green_percentage") is not None:
                    attrs["renewable_percentage"] = Decimal(str(meta["green_percentage"]))
                offer = Offer(key=key, supplier=query.supplier, utility=query.utility, commodity=query.commodity,
                              zip=query.zip, name=product["name"], product_id=product_id,
                              price=Price(value=value, unit="USD/kWh", raw=f"billing.commodity_rate={value}; display={average}"),
                              term_months=months, term_kind="fixed_term", rate_structure=product.get("product_type"),
                              monthly_fee=Decimal(str(billing["monthly_fee"])) if billing.get("monthly_fee") is not None else None,
                              source_url=url, source_kind="verified_api_response", artifact_id=artifact_id,
                              raw_fields=product, **attrs)
                for doc in json.loads(product.get("documents") or "[]"):
                    if doc.get("location"):
                        offer.documents.append(DocumentRef(url=doc["location"], label=doc.get("description", "Document"),
                                                           offer_key=key, product_id=product_id, discovery_artifact_id=artifact_id))
                offers.append(offer)
    return deduplicate(offers)


def direct_energy_evidence(payloads: list[tuple], query: Query) -> dict:
    """Select the latest complete Direct snapshots from this query's traffic."""
    utility_snapshots = []
    for payload, url, artifact_id in payloads:
        if not isinstance(payload, dict) or "get-utilities-by-zip" not in url:
            continue
        parameters = parse_qs(urlsplit(url).query)
        if (parameters.get("zipcode") or parameters.get("zipCode")) != [query.zip]:
            continue
        category = "electricUtility" if query.commodity == "electric" else "gasUtility"
        snapshot_codes = set()
        for utility in payload.get(category, []):
            if utility.get("state", "").upper() == "NJ" and utility_matches(utility.get("name", ""), query.utility):
                if utility.get("utilityCode"):
                    snapshot_codes.add(str(utility["utilityCode"]))
        utility_snapshots.append((snapshot_codes, artifact_id))
    codes, utility_artifact_id = utility_snapshots[-1] if utility_snapshots else (set(), None)

    product_snapshots = []
    for payload, url, artifact_id in payloads:
        if (not isinstance(payload, dict)
                or urlsplit(url).hostname != "api-oe.directenergy.com"
                or urlsplit(url).path != DIRECT_PRODUCTS_ENDPOINT
                or payload.get("statusCode") != "00"):
            continue
        snapshot = payload.get("affiliateOfferList", [])
        if isinstance(snapshot, list):
            product_snapshots.append((snapshot, url, artifact_id))

    products = []
    product_artifact_id = None
    if len(codes) == 1 and product_snapshots:
        # Dual-fuel ZIPs issue separate electricity and gas product requests.
        # Response completion order is nondeterministic, so select the latest
        # snapshot that actually carries the exact verified utility code rather
        # than blindly taking the last /products response.
        matching_snapshots = [
            item for item in product_snapshots
            if any(
                isinstance(product, dict) and product.get("utilityCode") in codes
                for product in item[0]
            )
        ]
        if not matching_snapshots:
            return {
                "codes": codes,
                "products": products,
                "utility_response_count": len(utility_snapshots),
                "product_response_count": len(product_snapshots),
                "utility_artifact_id": utility_artifact_id,
                "product_artifact_id": None,
            }
        snapshot, url, product_artifact_id = matching_snapshots[-1]
        for product in snapshot:
            if not isinstance(product, dict):
                continue
            if product.get("utilityCode") not in codes or product.get("state", "").lower() != "nj" or product.get("customerType") != "residential":
                continue
            if product.get("commodity") != ("electricity" if query.commodity == "electric" else "gas"):
                continue
            products.append((product, url, product_artifact_id))
    return {
        "codes": codes,
        "products": products,
        "utility_response_count": len(utility_snapshots),
        "product_response_count": len(product_snapshots),
        "utility_artifact_id": utility_artifact_id,
        "product_artifact_id": product_artifact_id,
    }


def direct_energy_scope(payloads: list[tuple], query: Query) -> tuple[set[str], list[tuple[dict, str, str]]]:
    """Return products from the latest response joined to the latest exact-ZIP utility response."""
    evidence = direct_energy_evidence(payloads, query)
    codes = evidence["codes"]
    if len(codes) != 1:
        return codes, []
    return codes, evidence["products"]


def direct_document_url_valid(url: str, expected_code: str) -> bool:
    """Accept only Direct's plan-document endpoint with its expected type code."""
    parsed = urlsplit(url or "")
    parameters = {key.casefold(): values for key, values in parse_qs(parsed.query).items()}
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").casefold() == DIRECT_DOCUMENT_HOST
        and parsed.path.rstrip("/").casefold().endswith("/displaydocument.aspx")
        and len(parameters.get("rateid", [])) == 1
        and bool(parameters["rateid"][0].strip())
        and parameters.get("code", [""])[0].casefold() == expected_code.casefold()
    )


def direct_energy_diagnostics(payloads: list[tuple], query: Query) -> dict:
    """Describe source completeness before normalization or deduplication."""
    evidence = direct_energy_evidence(payloads, query)
    codes, products = evidence["codes"], evidence["products"]
    identities = [str(product.get("offerCode") or "").strip() for product, _, _ in products]
    populated = [identity for identity in identities if identity]
    duplicates = sorted({identity for identity in populated if populated.count(identity) > 1})
    invalid_documents = []
    for product, _, _ in products:
        identity = str(product.get("offerCode") or "<missing offerCode>")
        for field, (_, code) in DIRECT_DOCUMENT_CODES.items():
            url = product.get(field)
            if url and not direct_document_url_valid(str(url), code):
                invalid_documents.append(f"{identity}:{field}")
    return {
        "utility_codes": sorted(codes),
        "source_product_count": len(products),
        "missing_offer_code_count": identities.count(""),
        "duplicate_offer_codes": duplicates,
        "invalid_document_fields": sorted(invalid_documents),
        "utility_response_count": evidence["utility_response_count"],
        "product_response_count": evidence["product_response_count"],
        "utility_artifact_id": evidence["utility_artifact_id"],
        "product_artifact_id": evidence["product_artifact_id"],
    }


def direct_energy(payloads: list[tuple], query: Query) -> list[Offer]:
    codes, products = direct_energy_scope(payloads, query)
    if len(codes) != 1:
        return []
    offers = []
    for product, url, artifact_id in products:
        stages = product.get("elecRate" if query.commodity == "electric" else "gasRate") or []
        unit = product.get("unitELEC" if query.commodity == "electric" else "unitGas")
        units = {"kwh": "kWh", "therm": "therm", "ccf": "CCF", "dth": "Dth"}
        if (not stages or not isinstance(stages[0], dict) or stages[0].get("rate") is None
                or str(unit).lower() not in units
                or product.get("currency") not in ("cents", "dollars", "USD")
                or not product.get("offerCode") or not product.get("offerPlanName")):
            continue
        value = Decimal(str(stages[0]["rate"])) / (100 if product["currency"] == "cents" else 1)
        months = int(product["contractTerm"]) if product.get("contractTerm") is not None else None
        product_id = str(product["offerCode"])
        key = offer_key(query, product["offerPlanName"], product_id, months)
        offer = Offer(key=key, supplier=query.supplier, utility=query.utility, commodity=query.commodity,
                      zip=query.zip, name=product["offerPlanName"], product_id=product_id,
                      price=Price(value=value, unit="USD/" + units[str(unit).lower()], raw=f"{stages[0]['rate']} {product['currency']}/{unit}"),
                      term_months=months, term_kind="fixed_term" if months else "month_to_month",
                      rate_structure={"fix": "fixed", "var": "variable"}.get(product.get("planType")),
                      cancellation_fee=Decimal(product["cancelFee"]) if product.get("cancelFee") is not None else None,
                      source_url=url, source_kind="verified_api_response", artifact_id=artifact_id,
                      raw_fields=product)
        # adminFee is kept raw: the payload does not establish its frequency.
        for field, (label, code) in DIRECT_DOCUMENT_CODES.items():
            if product.get(field) and direct_document_url_valid(str(product[field]), code):
                offer.documents.append(DocumentRef(url=product[field], label=label, product_id=product_id,
                                                   offer_key=key, discovery_artifact_id=artifact_id))
            elif product.get(field):
                offer.warnings.append(f"Invalid supplier document route omitted: {field}")
        if product.get("offerIncentives"):
            offer.incentives.append(str(product["offerIncentives"]))
        if len(stages) > 1:
            offer.raw_fields["price_stages"] = stages
            offer.warnings.append("Multiple price stages; first-stage price displayed")
        if product.get("productType") == "GREENOFFER":
            offer.renewable_claim = product.get("cmsProductTagline")
            if product.get("greenFlag") is False:
                offer.warnings.append("API greenFlag=false conflicts with GREENOFFER; consult environmental disclosure")
        offers.append(offer)
    return deduplicate(offers)


def indra_energy(payloads: list[tuple], query: Query) -> list[Offer]:
    """Current public signup-rate schema, scoped to ZIP, commodity, and utility."""
    offers = []
    commodity_code = "E" if query.commodity == "electric" else "G"
    expected_unit = "kWh" if query.commodity == "electric" else "therm"
    for payload, url, artifact_id in payloads:
        if urlsplit(url).scheme != "https" or urlsplit(url).netloc != "indraenergy.com":
            continue
        if urlsplit(url).path != "/wp-json/indra-energy/v1/rates" or not isinstance(payload, dict):
            continue
        params = parse_qs(urlsplit(url).query)
        if params.get("zip") != [query.zip]:
            continue
        data = payload.get("data") if payload.get("success") is True else None
        rates = data.get("rates", {}) if isinstance(data, dict) else {}
        for product in rates.get(query.commodity, []):
            if not isinstance(product, dict):
                continue
            if product.get("state") != "NJ" or product.get("zipCode") != query.zip:
                continue
            if product.get("commodityType") != commodity_code:
                continue
            if not utility_matches(product.get("utilityName") or product.get("utility", ""), query.utility):
                continue
            if product.get("rateUnit") != expected_unit or product.get("initialRate") is None:
                continue
            # The signup UI displays initialRate as cents per unit. The API's
            # utility comparison field is already dollars/unit, confirming the
            # two fields use different scales.
            value = Decimal(str(product["initialRate"])) / 100
            months = int(product["termLength"]) if product.get("termLength") is not None else None
            rate_code = str(product.get("rateCode") or "").strip()
            system_id = str(product.get("sysId") or product.get("id") or "").strip()
            # Indra currently reuses some NJ rateCode values across distinct
            # 6- and 12-month products. Pair it with the API's unique sysId so
            # plan/document association cannot collapse those offers.
            product_id = "|".join(part for part in (rate_code, system_id) if part)
            name = product.get("planName") or product.get("displayName") or product.get("rateType")
            if not name or not product_id:
                continue
            key = offer_key(query, name, product_id, months)
            structure = str(product.get("termType") or "").casefold()
            offer = Offer(
                key=key, supplier=query.supplier, utility=query.utility,
                commodity=query.commodity, zip=query.zip, name=name,
                product_id=product_id,
                price=Price(value=value, unit="USD/" + expected_unit,
                            raw=f"initialRate={product['initialRate']} cents/{expected_unit}"),
                rate_structure=structure if structure in {"fixed", "variable"} else None,
                term_months=months,
                term_kind="fixed_term" if months else "month_to_month",
                enrollment_fee=Decimal(str(product["enrollmentFee"])) if product.get("enrollmentFee") is not None else None,
                cancellation_fee=Decimal(str(product["cancellationFee"])) if product.get("cancellationFee") is not None else None,
                source_url=url, source_kind="verified_api_response",
                artifact_id=artifact_id, raw_fields=product,
            )
            offers.append(offer)
    return deduplicate(offers)


def verified_offers(payloads: list[tuple], query: Query) -> list[Offer]:
    if query.adapter == "direct_energy":
        return direct_energy(payloads, query)
    if query.adapter == "think_energy":
        return think_energy(payloads, query)
    if query.adapter == "nrg":
        return nrg(payloads, query)
    if query.adapter == "indra_energy":
        return indra_energy(payloads, query)
    return []


def nrg(payloads: list[tuple], query: Query) -> list[Offer]:
    utility_slugs = {
        "PSE&G Electric": "pseg", "ACE Electric": "ace", "Rockland Electric": "reco",
        "PSE&G Gas": "pseg_gas", "SJG Gas": "sjersey",
    }
    expected_slug = utility_slugs.get(query.utility)
    if not expected_slug:
        return []
    result = []
    for payload, url, artifact_id in payloads:
        if url != "https://www.picknrg.com/en/electricity-and-gas/loadProductChart" or not isinstance(payload, dict):
            continue
        product_key = "ElectrictProducts" if query.commodity == "electric" else "GasProducts"
        for item in payload.get(product_key, []):
            api, cms = item.get("ApiContent", {}), item.get("CmsContent", {})
            if api.get("StateSlug") != "nj" or api.get("Commodity") != query.commodity or api.get("PremiseType") != "residential" or not api.get("Active"):
                continue
            if api.get("UtilitySlug") != expected_slug:
                continue
            value = Decimal(api["Rate"])
            if api.get("WebRateUnit") != "&cent" or Decimal(api["WebDisplayRate"]) != value * 100:
                continue
            intro = api.get("PeLockType") == "intro"
            months = int(api["PricingTerm"])
            product_id = api["Sku"]
            summary = BeautifulSoup(cms.get("SummaryString", ""), "lxml").get_text("\n", strip=True)
            attrs = attributes(api.get("GreenText", "") + "\n" + summary)
            offer = Offer(key=offer_key(query, api["ProductName"], product_id, None if intro else months),
                          supplier=query.supplier, utility=query.utility, commodity=query.commodity, zip=query.zip,
                          name=api["ProductName"], product_id=product_id,
                          price=Price(value=value, unit="USD/kWh" if query.commodity == "electric" else "USD/therm",
                                      raw=f"Rate={api['Rate']}; WebDisplayRate={api['WebDisplayRate']} cents/{'kWh' if query.commodity == 'electric' else 'therm'}"),
                          rate_structure=api["RateType"], term_months=None if intro else months,
                          term_kind="month_to_month" if intro else "fixed_term",
                          intro_duration_months=months if intro else None,
                          cancellation_fee=Decimal(api["EarlyCancellationFee"]) if api.get("EarlyCancellationFee") is not None else None,
                          raw_fields=item, source_url=url, source_kind="verified_api_response", artifact_id=artifact_id, **attrs)
            # The product-chart UI builds this supplier-owned legal route from
            # the live SKU. Some gas cards are initially collapsed/omitted from
            # the rendered carousel, so relying only on visible DOM links leaves
            # otherwise exported API products without their current TOS. The
            # SKU is the same plan identity used by the legal endpoint.
            offer.documents.append(DocumentRef(
                url=("https://www.picknrg.com/en/getLegalDocument?"
                     f"format=pdf&docType=tos&sku={product_id}"),
                label="Terms of Service",
                product_id=product_id,
                offer_key=offer.key,
                artifact_id=artifact_id,
            ))
            if intro:
                offer.intro_price = offer.price
            offer.incentives = [api.get("PromoDescription", ""), summary]
            result.append(offer)
    return deduplicate(result)
