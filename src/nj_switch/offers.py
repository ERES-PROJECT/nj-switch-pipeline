"""Offer parsers operate offline on captured evidence, never on browser state."""
import hashlib
import json
import re
from decimal import Decimal
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup

from .models import DocumentRef, Offer, Query
from .evidence import redact
from .normalize import attributes, compatible, prices, rate_structure, term
from .registry import utility_matches

DOCUMENT_WORDS = re.compile(r"contract|terms.{0,8}(?:service|conditions)|\btos\b|\befl\b|disclosure|tandc|\.pdf(?:\?|$)|getdocument", re.I)


def offer_key(query: Query, name: str, product_id: str | None, months: int | None) -> str:
    parts = [query.supplier, query.utility, query.commodity, query.zip, product_id or name.strip().casefold(), str(months)]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]


def document_links(html: str, base_url: str, product_id: str | None = None,
                   key: str | None = None, artifact_id: str | None = None) -> list[DocumentRef]:
    soup = BeautifulSoup(html, "lxml")
    result = []
    seen = set()
    for link in soup.select("a[href]"):
        href = link["href"].strip()
        label = link.get_text(" ", strip=True) or " ".join(
            image.get("alt", "") for image in link.select("img[alt]")
        ).strip()
        if href.startswith(("#", "javascript:", "mailto:", "tel:")) or not DOCUMENT_WORDS.search(label + " " + href):
            continue
        url = urljoin(base_url, href)
        if url not in seen and url.startswith(("https://", "http://")):
            result.append(DocumentRef(url=url, label=label or "Contract document", product_id=product_id,
                                      offer_key=key, discovery_artifact_id=artifact_id))
            seen.add(url)
    return result


def _make(query: Query, name: str, text: str, product_id: str | None, url: str,
          artifact_id: str, source_kind: str, raw_fields: dict | None = None) -> Offer | None:
    found = [p for p in prices(text) if compatible(p, query.commodity)]
    if not name or not found:
        return None
    months, kind = term(text)
    warning = []
    distinct = {(p.value, p.unit) for p in found}
    if len(distinct) > 1:
        warning.append("Multiple prices in offer; review price stages/tiers against raw text")
    result = Offer(key=offer_key(query, name, product_id, months), supplier=query.supplier,
                   utility=query.utility, commodity=query.commodity, zip=query.zip, name=name,
                   product_id=product_id, price=found[0], term_months=months, term_kind=kind,
                   rate_structure=rate_structure(text), source_url=url, source_kind=source_kind,
                   artifact_id=artifact_id, raw_fields=redact(raw_fields or {"text": text}), warnings=warning,
                   **attributes(text))
    if re.search(r"\bintro(?:ductory)?\b", text, re.I):
        result.intro_price = found[0]
        period = re.search(r"(?:first|introductory.{0,15})\s*(\d+)\s*months?", text, re.I)
        if period:
            result.intro_duration_months = int(period[1])
    if not result.rate_structure:
        result.warnings.append("Rate structure not explicitly established")
    if result.price.value <= 0:
        result.warnings.append("Nonpositive rate requires review")
    return result


def parse_html(html: str, query: Query, url: str, artifact_id: str) -> list[Offer]:
    soup = BeautifulSoup(html, "lxml")
    if query.adapter == "mpower_energy":
        heading = next((item for item in soup.find_all("h1")
                        if item.get_text(" ", strip=True) == "New Jersey Pricing"), None)
        block = heading.find_parent(class_="content-block") if heading else None
        columns = block.select(".table > div") if block else []
        if len(columns) < 3:
            return []
        utilities = [item.get_text(" ", strip=True) for item in columns[0].select(".text-block-3")][1:]
        prices_by_kind = {}
        for column in columns[1:]:
            cells = [item.get_text(" ", strip=True) for item in column.select(".text-block-3")]
            if cells:
                prices_by_kind[cells[0].casefold()] = cells[1:]
        indexes = [index for index, utility in enumerate(utilities) if utility_matches(utility, query.utility)]
        price_rows = next((values for label, values in prices_by_kind.items() if "gas price" in label), [])
        if len(indexes) != 1 or indexes[0] >= len(price_rows) or price_rows[indexes[0]].casefold() == "n/a":
            return []
        raw_rate = price_rows[indexes[0]]
        name = "Mpower New Jersey 12 Month Fixed Gas"
        text = f"{name}\n${raw_rate}/therm\n12 months\nFixed rate"
        offer = _make(query, name, text, f"mpower-nj-{utilities[indexes[0]]}-gas-12", url,
                      artifact_id, "html", {"utility_table": utilities, "displayed_rate": raw_rate})
        if offer and block:
            offer.documents = document_links(str(block), url, offer.product_id, offer.key, artifact_id)
        return [offer] if offer else []
    if query.adapter == "american_power_and_gas":
        # Preserve replay support for the supplier's retired comparison table,
        # but prefer current address-qualified shopping cards when present.
        live_cards = soup.select("#plans-scroller .plan-item")
        if live_cards:
            cards = live_cards
        else:
            cards = []
        heading = next((item for item in soup.find_all("h2")
                        if item.get_text(" ", strip=True).casefold() == "rates - gas"), None)
        grid = heading.find_next("div", class_=lambda value: value and "grid-cols-4" in value) if heading else None
        cells = [cell.get_text(" ", strip=True) for cell in grid.find_all("div", recursive=False)] if grid else []
        if live_cards:
            cells = []
        tiers = []
        for index in range(4, len(cells) - 3, 4):
            label, usage, utility_total, supplier_total = cells[index:index + 4]
            if "residential" not in label.casefold() or not utility_matches(label, query.utility):
                continue
            try:
                tiers.append({"label": label, "usage_therms": Decimal(usage),
                              "utility_total": Decimal(utility_total), "supplier_total": Decimal(supplier_total)})
            except Exception:
                continue
        if not tiers and not live_cards:
            return []
        if live_cards:
            # Continue through the shared card parser below.
            pass
        else:
            unit_rates = {tier["supplier_total"] / tier["usage_therms"] for tier in tiers}
            if len(unit_rates) != 1:
                return []
            rate = unit_rates.pop()
            name = "AP&G New Jersey Residential Variable Gas"
            product_id = "apg-" + re.sub(r"[^a-z0-9]+", "-", query.utility.casefold()).strip("-") + "-variable-gas"
            text = f"{name}\n${rate}/therm\nVariable rate\nmonth-to-month\nNo cancellation fee: $0"
            offer = _make(query, name, text, product_id, url, artifact_id, "html",
                          {"displayed_bill_examples": tiers, "derived_unit_rate": str(rate)})
            if offer:
                offer.tiers = [{key: str(value) for key, value in tier.items()} for tier in tiers]
                return [offer]
            return []
    selectors = {
        "constellation": '#individual-electricity-options > ul > li, #individual-gas-options > ul > li, div[data-planid][data-term]',
        "direct_energy": '.product-card.plan__wrapper, .product-card[class*="product-id-"]',
        "ambit": '.ngdialog-content',
        "xoom_energy": 'div.myRateData',
        "think_energy": '[data-offer], [data-product-id]',
        "major_energy": '[data-productid], [data-product-id], .plan-card, .product-card, .card:has(a[href*="SelectProduct"])',
        "nrg": '[data-productid], [data-product-id], .product-card, .plan-card, .tier-card, .pc-plan-container[id]',
        "clearview_energy": 'label.pricing-label',
        "idt_energy": 'table.rate-table tbody > tr:not(.more-info)',
        "smart_energy": '.plan-card',
        "alpha_gas_and_electric": '.alpha-offer',
        "eligo_energy": '.flow-result-card',
        "nextera_energy_services": '.pricing_plan_item.plan_card',
        "cleansky_energy": '[id^="PlanDiv_"][data-productid]',
        "njgande": '.ds_plan_item.item_v2',
        "nordic_energy_services": f'section.{query.commodity} .utility-offer',
        "american_power_and_gas": '#plans-scroller .plan-item',
        "default": '[data-offer][data-product-id]',
    }
    cards = soup.select(selectors.get(query.adapter, selectors["default"]))
    if query.adapter == "constellation":
        live_selector = (
            "#individual-electricity-options > ul > li"
            if query.commodity == "electric"
            else "#individual-gas-options > ul > li"
        )
        cards = soup.select(live_selector) or soup.select('div[data-planid][data-term]')
    if query.adapter == "cleanchoice":
        cards = []
        for button in soup.select('button[data-testid="select-plan-button"]'):
            candidate = button.parent
            while candidate and candidate.name != "body":
                if (len(candidate.select('button[data-testid="select-plan-button"]')) == 1
                        and prices(candidate.get_text(" ", strip=True))
                        and term(candidate.get_text(" ", strip=True))[0] is not None):
                    cards.append(candidate)
                    break
                candidate = candidate.parent
    if query.adapter == "ambit" and not cards:
        # New public shopping platform has pre-rendered detail panels. Each
        # panel preserves its title, price, rate type, term and fee together.
        cards = soup.select('.ds_plan_item.item_v2')
        if not cards:
            cards = soup.select('.ds_plan_item')
    if query.adapter == "njgande" and not cards:
        # The current shopping page renders a compact item_v1 card and a
        # detailed item_v2 card for the same product. Prefer item_v2 because it
        # carries the supplier product ID and explicit Rate Type; retain the
        # compact selector only for older/simplified captures.
        cards = soup.select('.ds_plan_item.item_v1')
    if query.adapter == "think_energy" and not cards:
        for title in soup.select('div[font-size="1.8rem"]'):
            # Keep title/rate association local, never zip two independent lists.
            for parent in title.parents:
                if parent.select_one('div[font-size="4.5rem"]'):
                    if len(parent.select('div[font-size="1.8rem"]')) == 1:
                        cards.append(parent)
                    break
    if query.adapter == "constellation" and not cards:
        for table in soup.find_all("table"):
            headers = table.get_text(" ", strip=True).lower()
            if all(label in headers for label in ("plan name", "length", "rate")):
                cards.extend(tr for tr in table.find_all("tr") if len(tr.find_all("td")) >= 3)
    if query.adapter == "residents_energy":
        cards = []
        for table in soup.find_all("table"):
            if "NJ Natural Gas ResiSURE Price Comparison" not in table.get_text(" ", strip=True):
                continue
            gas_section = False
            for row in table.find_all("tr"):
                row_text = row.get_text(" ", strip=True)
                if "NJ Natural Gas ResiSURE Price Comparison" in row_text:
                    gas_section = True
                    continue
                if not gas_section:
                    continue
                cells = row.find_all("td", recursive=False)
                if len(cells) >= 5 and utility_matches(cells[0].get_text(" ", strip=True), query.utility):
                    cards.append(row)
    results = []
    for card in cards:
        text = card.get_text("\n", strip=True)
        if query.adapter == "nextera_energy_services":
            # NextEra repeats plan-detail modals inside card markup. Those
            # modals can contain a different plan's price and term, so exclude
            # them from primary offer parsing; document capture handles each
            # modal separately through its stable data-rate identity.
            scoped_card = BeautifulSoup(str(card), "lxml")
            for modal in scoped_card.select(".modal"):
                modal.decompose()
            text = scoped_card.get_text("\n", strip=True)
        idt_name = None
        idt_product = None
        idt_details = None
        if query.adapter == "residents_energy":
            cells = card.find_all("td", recursive=False)
            utility_label, rate, supply, cycles = [cell.get_text(" ", strip=True) for cell in
                                                    (cells[0], cells[2], cells[3], cells[4])]
            name = f"Residents ResiSURE {supply} {cycles} Bill Cycles"
            product_id = f"{utility_label}-{supply}-{cycles}-{rate}".lower().replace(" ", "-")
            text = f"{name}\n${rate}/therm\n{cycles} monthly billing cycles\nFixed rate"
        if query.adapter == "nordic_energy_services":
            utility_name = card.select_one('[data-bind="text:utilityName"]')
            if not utility_name or not utility_matches(utility_name.get_text(" ", strip=True), query.utility):
                continue
            rate = card.select_one('[data-bind="text:promotionPrice"]')
            unit = card.select_one('[data-bind="text:unitOfMeasure"]')
            months = card.select_one('[data-bind="text:promotionDuration"]')
            kind = card.select_one('[data-bind="text:rateType"]')
            if not all((rate, unit, months, kind)):
                continue
            commodity_name = "Electric" if query.commodity == "electric" else "Gas"
            name = f"Nordic {utility_name.get_text(' ', strip=True)} {months.get_text(' ', strip=True)} Month {kind.get_text(' ', strip=True)} {commodity_name}"
            product_id = card.get("data-id")
            text = f"{name}\n${rate.get_text(' ', strip=True)}/{unit.get_text(' ', strip=True)}\n{months.get_text(' ', strip=True)} months\n{kind.get_text(' ', strip=True)} rate"
        if query.adapter == "idt_energy":
            enrollment = card.select_one('a[href*="filter_offerid"]')
            if not enrollment:
                continue
            parameters = parse_qs(urlsplit(enrollment.get("href", "")).query)
            utility = parameters.get("filter_utility", [""])[0]
            commodity = parameters.get("filter_commodity", [""])[0]
            commodity_code = "E" if query.commodity == "electric" else "G"
            if not utility_matches(utility, query.utility) or commodity.upper() != commodity_code:
                continue
            idt_product = parameters.get("filter_offerid", [None])[0]
            rate = parameters.get("filter_rate", [None])[0]
            rate_type = parameters.get("filter_ratetype", [""])[0]
            energy_type = parameters.get("filter_energytype", [""])[0]
            detail_row = card.find_next_sibling("tr", class_="more-info")
            idt_details = detail_row.get_text("\n", strip=True) if detail_row else ""
            if rate:
                unit = "kWh" if query.commodity == "electric" else "therm"
                text = f"${rate}/{unit}\n" + text
            text += "\n" + idt_details
            green = "100% Renewable" if re.search(r"100|green|renewable", energy_type, re.I) else "Standard Renewable Mix"
            structure = "Variable" if re.search(r"variable|month", rate_type, re.I) else "Fixed"
            idt_name = f"IDT {green} {structure} Offer"
        if query.adapter == "clearview_energy":
            product = card.select_one("input.price-card__input")
            commodity_code = "E" if query.commodity == "electric" else "G"
            if not product or product.get("data-type") != commodity_code or not utility_matches(product.get("data-utilname", ""), query.utility):
                continue
            displayed = card.select_one(".price-card__head-price")
            if displayed:
                unit = "kWh" if query.commodity == "electric" else "therm"
                text += "\n" + displayed.get_text(strip=True) + f" cents/{unit}"
        heading = card.select_one('[data-product-plan] p, [id^="PlanName"], .name-above-plan, .utility-choice-title, .plan__title, .product-name, .price-card__head-utility, .flow-card-title, h2, h3, h4, h5')
        if not heading and query.adapter == "think_energy":
            heading = card.select_one('div[font-size="1.8rem"]')
        if not heading and card.name == "tr":
            heading = card.find("td")
        if query.adapter not in ("residents_energy", "nordic_energy_services"):
            name = heading.get_text(" ", strip=True) if heading else card.get("data-plan-name", "")
            product_id = card.get("data-planid") or card.get("data-productid") or card.get("data-product-id")
        if query.adapter == "american_power_and_gas":
            product_id = "apg-" + re.sub(
                r"[^a-z0-9]+", "-", f"{query.utility}-{name}".casefold()
            ).strip("-")
            if re.search(r"Term:\s*Monthly", text, re.I):
                text += "\nmonth-to-month"
        if query.adapter == "cleanchoice":
            # The current cards use "Plan details" as their only heading. Use
            # the supplier's displayed rate-type label as the plan identity so
            # exports distinguish fixed and introductory products meaningfully.
            displayed_type = re.search(r"Rate type:\s*([^\n]+)", text, re.I)
            if displayed_type:
                name = f"CleanChoice {displayed_type[1].strip()} 100% Renewable"
        if query.adapter == "constellation" and not product_id:
            selection = card.select_one("[data-selected-plan]")
            if selection:
                product_id = selection.get("data-selected-plan")
            if not product_id:
                contract = card.select_one('a[href*="GetPlanContractPDF"]')
                parameters = parse_qs(urlsplit(contract.get("href", "")).query) if contract else {}
                product_id = parameters.get("planId", [None])[0]
        if query.adapter == "nextera_energy_services":
            rate_identity = card.select_one("[data-rate]")
            product_id = rate_identity.get("data-rate") if rate_identity else product_id
            if name and not term(text)[0]:
                title_term = re.search(r"\b(\d{1,3})\b", name)
                if title_term:
                    text += f"\n{title_term[1]} months"
        if query.adapter == "cleansky_energy":
            product_id = card.get("data-productid") or product_id
            explicit = card.select_one('[data-energychargedollar]')
            if explicit and not prices(text):
                unit = "kWh" if query.commodity == "electric" else "therm"
                text += f'\n${explicit.get("data-energychargedollar")}/{unit}'
            raw_term = card.get("data-termfilter") or (explicit.get("data-term") if explicit else None)
            if raw_term and str(raw_term).isdigit() and not term(text)[0]:
                text += f"\n{raw_term} months"
        if query.adapter == "idt_energy":
            name, product_id = idt_name, idt_product
        if query.adapter == "clearview_energy" and product:
            product_id = product.get("id")
        if query.adapter == "nrg":
            product_id = product_id or card.get("id")
        if query.adapter == "eligo_energy":
            enrollment = card.select_one('a[href*="/signup/"]')
            parameters = parse_qs(urlsplit(enrollment.get("href", "")).query) if enrollment else {}
            product_id = "-".join(parameters.get(key, [""])[0] for key in ("z", "t", "p", "g")) or None
        rate_attributes = card.select_one('[data-rateid][data-ratetermlength]') if query.adapter == "xoom_energy" else None
        if rate_attributes:
            product_id = rate_attributes["data-rateid"]
        if query.adapter == "major_energy":
            enrollment = card.select_one('a[href*="SelectProduct"]')
            if enrollment:
                product_id = parse_qs(urlsplit(enrollment["href"]).query).get("productid", [None])[0]
            # Details are a sibling collapse panel, not a second offer. Keep
            # price-to-compare prose outside the primary price extraction.
            detail = soup.select_one(f'#productDetail-{product_id}') if product_id else None
        elif query.adapter == "constellation":
            # Plan disclosures and legal URLs live in a sibling dialog whose
            # identifier carries the card's product ID.
            detail = soup.select_one(f'#dialog{product_id}') if product_id else None
        else:
            detail = None
        if query.adapter == "constellation":
            labeled_rate = re.search(r"Rate per (kWh|therm)\s*:?\s*([\d.]+)\s*(¢|\$)", text, re.I)
            if labeled_rate and not prices(text):
                text += f"\n{labeled_rate[2]}{labeled_rate[3]}/{labeled_rate[1]}"
            rate = card.select_one('[data-rate]')
            # The unit is explicit on the card/table; do not infer gas from query.
            if rate and re.search(r"kwh", text, re.I) and not prices(text):
                text += "\n" + rate.get_text(strip=True).replace("¢", "") + " cents/kWh"
            if card.get("data-term", "").isdigit():
                text = card["data-term"] + " months\n" + text
        if query.adapter == "think_energy" and not prices(text):
            rate = card.select_one('div[font-size="4.5rem"]')
            if rate and re.search(r"kwh", text, re.I) and re.search(r"¢|cents", text, re.I):
                text += "\n" + rate.get_text(strip=True) + " cents/kWh"
        for icon in card.select("img[alt]"):
            text += "\n" + icon["alt"]
        offer = _make(query, name, text, product_id, url, artifact_id, "html")
        if offer:
            if query.adapter == "constellation":
                # The signup card embeds market-wide disclaimers and utility
                # comparison rates inside each <li>. The explicitly labelled
                # card rate is the offer price, not one stage of a tiered plan.
                primary = card.select_one(".individual-cost")
                primary_prices = prices(primary.get_text(" ", strip=True)) if primary else []
                if not primary_prices:
                    labeled = re.search(
                        r"Rate per (kWh|therm)\s*:?\s*([\d.]+)\s*(¢|\$)", text, re.I
                    )
                    primary_prices = prices(
                        f"{labeled[2]}{labeled[3]}/{labeled[1]}"
                    ) if labeled else []
                compatible_primary = [
                    price for price in primary_prices if compatible(price, query.commodity)
                ]
                if len(compatible_primary) == 1:
                    offer.price = compatible_primary[0]
                    offer.warnings = [
                        warning for warning in offer.warnings
                        if warning != "Multiple prices in offer; review price stages/tiers against raw text"
                    ]
                # Keep the explicitly labelled offer on the plan card.  The
                # sibling dialog contains market-wide/site-wide prose whose
                # incidental words (for example "discount") are not this
                # plan's incentive.
                special_offer = re.search(
                    r"Special Offer\s*:\s*([^\n]+)", text, re.I
                )
                if special_offer:
                    value = special_offer.group(1).strip()
                    if value and value.casefold() not in {"none", "n/a", "not applicable"}:
                        offer.incentives = [value]
            if query.adapter == "idt_energy":
                # The card deliberately shows both the selected supplier rate
                # and the utility price-to-compare. The enrollment query is the
                # authoritative offer rate/type, so the comparison price is not
                # a second price tier and must not trigger ambiguity.
                offer.warnings = [
                    warning for warning in offer.warnings
                    if warning not in {
                        "Multiple prices in offer; review price stages/tiers against raw text",
                        "Rate structure not explicitly established",
                    }
                ]
                offer.rate_structure = "variable" if structure == "Variable" else "fixed"
            if query.adapter == "cleansky_energy" and offer.term_months:
                if not offer.rate_structure and re.search(r"locked[- ]in rate", text, re.I):
                    offer.rate_structure = "fixed"
                    offer.warnings = [
                        warning for warning in offer.warnings
                        if warning != "Rate structure not explicitly established"
                    ]
                named_term = re.search(r"\b(\d{1,3})\b", name)
                if named_term and int(named_term[1]) != offer.term_months:
                    offer.warnings.append(
                        f"Displayed plan name says {named_term[1]} months but supplier term metadata says {offer.term_months}; metadata retained"
                    )
            if rate_attributes:
                label = rate_attributes["data-ratetermlength"]
                months, kind = (None, "month_to_month") if label.lower() == "monthly" else term(label + (" months" if label.isdigit() else ""))
                offer.term_months, offer.term_kind = months, kind
                offer.rate_structure = rate_structure(rate_attributes.get("data-ratetype", ""))
                offer.key = offer_key(query, name, product_id, months)
                offer.raw_fields["offer_attributes"] = dict(rate_attributes.attrs)
                intro = re.search(r"first\s+(\d+)\s+(?:bill\s+cycles?|bills?)", text, re.I)
                if offer.intro_price and intro:
                    offer.intro_duration_billing_cycles = int(intro[1])
            offer.documents = document_links(str(card), url, product_id, offer.key, artifact_id)
            if query.adapter == "idt_energy" and idt_details:
                offer.raw_fields["details"] = idt_details
                detail_row = card.find_next_sibling("tr", class_="more-info")
                if detail_row:
                    offer.documents.extend(document_links(str(detail_row), url, product_id, offer.key, artifact_id))
            if detail:
                detail_text = detail.get_text("\n", strip=True)
                offer.raw_fields["details"] = detail_text
                for field, value in attributes(detail_text).items():
                    if not value:
                        continue
                    if field == "fee_terms":
                        offer.fee_terms.update(value)
                    elif field == "incentives":
                        # Card-scoped incentive text is stronger evidence than
                        # incidental matches in a broad details dialog.
                        if not offer.incentives:
                            offer.incentives = value
                    elif getattr(offer, field, None) is None:
                        setattr(offer, field, value)
                offer.documents.extend(document_links(str(detail), url, product_id, offer.key, artifact_id))
            offer.documents = list({document.url: document for document in offer.documents}.values())
            results.append(offer)
    return deduplicate(results)


def parse_json(payload: object, query: Query, url: str, artifact_id: str) -> list[Offer]:
    """Discover explicit public offer objects; ambiguous units are never guessed.

    Supplier-specific profiles can normalize an observed payload into these aliases.
    This generic candidate parser alone does not prove territory or API suitability.
    """
    results = []
    if isinstance(payload, list):
        for child in payload:
            results.extend(parse_json(child, query, url, artifact_id))
    elif isinstance(payload, dict):
        keys = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k, v in payload.items()}
        def pick(*names):
            return next((keys[n] for n in names if n in keys and keys[n] is not None), None)
        name = pick("planname", "productname", "offername")
        rate = pick("ratedisplay", "formattedrate", "price", "rate", "commodityrate", "supplyprice")
        unit = pick("rateunit", "priceunit", "unit")
        currency = pick("currency", "currencyunit")
        if isinstance(name, str) and isinstance(rate, (str, int, float)):
            formatted = str(rate)
            if unit:
                currency_name = str(currency or "").lower()
                if currency_name in ("usd", "dollars", "dollar"):
                    formatted = f"${rate}/{str(unit).removeprefix('USD/')}"
                elif currency_name in ("cents", "cent", "¢"):
                    formatted = f"{rate} cents/{unit}"
                elif str(unit).startswith("USD/"):
                    formatted = f"${rate}/{str(unit)[4:]}"
                else:
                    formatted += " " + str(unit)
            months = pick("termmonths", "contractterm", "termlength")
            lines = [name, formatted]
            if months is not None:
                lines.append(f"{months} months")
            for key, value in payload.items():
                if isinstance(value, (str, int, float, bool)):
                    lines.append(re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(key)) + ": " + str(value))
            product = pick("productid", "planid", "rateid", "offerid")
            offer = _make(query, name, "\n".join(lines), str(product) if product is not None else None,
                          url, artifact_id, "json_candidate", payload)
            if offer:
                for key, value in payload.items():
                    if isinstance(value, str) and value.startswith(("http://", "https://", "/")) and DOCUMENT_WORDS.search(key + value):
                        offer.documents.append(DocumentRef(url=urljoin(url, value), label=key, product_id=offer.product_id,
                                                           offer_key=offer.key, discovery_artifact_id=artifact_id))
                results.append(offer)
        for value in payload.values():
            if isinstance(value, (dict, list)):
                results.extend(parse_json(value, query, url, artifact_id))
    return deduplicate(results)


def deduplicate(offers: list[Offer]) -> list[Offer]:
    # Price is not identity. Conflicting observations remain visible for review.
    result: dict[str, Offer] = {}
    for offer in offers:
        previous = result.get(offer.key)
        if previous:
            if previous.price != offer.price:
                previous.warnings.append("Conflicting observations for this product: " + offer.price.raw)
            known = {d.url for d in previous.documents}
            previous.documents.extend(d for d in offer.documents if d.url not in known)
        else:
            result[offer.key] = offer
    return list(result.values())
