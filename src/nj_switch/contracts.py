"""Extract labeled contract sections, retaining evidence before interpretation."""
import io
import re
from decimal import Decimal

from bs4 import BeautifulSoup
from docx import Document
import pdfplumber

from .models import Contract, DocumentRef, Offer
from .normalize import attributes, compatible, prices, rate_structure, term
from .registry import CONFIG, normalized, utility_matches

LABELS = {
    "supplier_information": r"(?:third party supplier|supplier|TPS)\s+information",
    "price_structure": r"price\s+structure",
    "supply_price": r"(?:generation\s*[/&]\s*supply|generation|supply)\s+price|energy\s+charge",
    "savings": r"statement\s+regarding\s+savings|savings\s+statement",
    "switching_time": r"(?:amount\s+of\s+)?time\s+required\s+to\s+change(?:\s+from\s+TPS\s+back\s+to\s+default\s+service(?:\s+or\s+to\s+another\s+TPS)?)?|switching\s+time|switch\s+back\s+to\s+utility\s*[/&]\s*TPS",
    "incentives": r"incentives(?:\s+and\s+offers)?",
    "rescission": r"right\s+to\s+(?:cancel\s*[/&]\s*rescind|rescind|cancel)|rescission\s+rights?",
    "start_date": r"contract\s+start\s+date",
    "term": r"contract\s+(?:term\s*[/&]\s*length|term|length)",
    "cancellation": r"(?:cancellation\s*[/&]\s*early\s+termination|early\s+termination|cancellation)\s+fees?",
    "renewal": r"renewal\s+terms",
    "distribution_company": r"distribution\s+company\s+information",
}
LABEL_RE = re.compile("|".join(f"(?P<{key}>{pattern})" for key, pattern in LABELS.items()), re.I)

# Verified on the publicly generated Direct Energy NJ contract summary. These
# opaque PDF field IDs are template-specific, not general label guesses.
DIRECT_FORM_FIELDS = {"PRSTRUCT": "price_structure", "RP": "supply_price", "INCENTIVE": "incentives",
                      "GC": "start_date", "IT": "term", "ETF": "cancellation",
                      "RTAEOIT": "renewal", "V1": "distribution_company"}


def pdf_string(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-16" if value.startswith((b"\xfe\xff", b"\xff\xfe")) else "latin1")
    return str(value or "")


def sections_from_text(text: str) -> dict[str, str]:
    # Anchors at line starts prevent renewal prose mentioning a 'contract term'
    # from starting a new section. Table extraction handles split-line headings.
    matches = list(re.finditer(r"(?m)^\s*(?:" + LABEL_RE.pattern + r")\s*:?\s*", text, re.I))
    result = {}
    for index, match in enumerate(matches):
        key = match.lastgroup
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        value = text[match.end():end].strip()
        if value:
            result[key] = result.get(key, "") + ("\n" if key in result else "") + value
    return result


def sections_from_rows(rows: list[list]) -> dict[str, str]:
    result = {}
    current = None
    for row in rows:
        cells = [str(value or "").strip() for value in row]
        if not cells:
            continue
        label = re.sub(r"\s+", " ", cells[0])
        match = LABEL_RE.match(label)
        if match:
            current = match.lastgroup
            value = "\n".join(cells[1:]).strip()
            if value:
                result[current] = value
        elif current and not label:
            result[current] = result.get(current, "") + "\n" + "\n".join(cells[1:])
    return result


def extract_contract(data: bytes, url: str, artifact_id: str, media_type: str = "") -> Contract:
    raw = ""
    table_sections = {}
    form_sections = {}
    form_fields = {}
    contract = Contract(id=artifact_id, url=url, artifact_id=artifact_id, media_type=media_type)
    try:
        if data.startswith(b"%PDF"):
            contract.media_type = "application/pdf"
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                if len(pdf.pages) > 60:
                    raise ValueError("Document exceeds 60-page limit; manual review required")
                texts = []
                for page in pdf.pages:
                    texts.append(page.extract_text() or "")
                    for annotation in page.annots or []:
                        annotation_data = annotation.get("data", {})
                        name, value = pdf_string(annotation_data.get("T")), pdf_string(annotation_data.get("V"))
                        if name and value:
                            form_fields[name] = value
                    for rows in page.extract_tables():
                        for key, value in sections_from_rows(rows).items():
                            table_sections.setdefault(key, value)
                raw = "\n".join(texts)
                if "Direct Energy" in raw and "CONTRACT SUMMARY" in raw:
                    for name, value in form_fields.items():
                        field = DIRECT_FORM_FIELDS.get(name.split("[")[0])
                        if field:
                            form_sections[field] = value
        elif data.startswith(b"PK"):
            contract.media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            doc = Document(io.BytesIO(data))
            parts = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                rows = [[cell.text for cell in row.cells] for row in table.rows]
                table_sections.update(sections_from_rows(rows))
                parts.extend(" | ".join(row) for row in rows)
            raw = "\n".join(parts)
        else:
            contract.media_type = "text/html" if b"<" in data[:200] else "text/plain"
            soup = BeautifulSoup(data.decode("utf-8", errors="replace"), "lxml")
            for table in soup.find_all("table"):
                rows = [[c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])] for row in table.find_all("tr")]
                table_sections.update(sections_from_rows(rows))
            raw = soup.get_text("\n", strip=True)
        contract.raw_text = raw
        contract.sections = sections_from_text(raw)
        contract.sections.update(table_sections)
        contract.sections.update(form_sections)
        if form_sections and form_fields.get("COMMODITY[0]"):
            contract.sections["supplier_information"] = (contract.sections.get("supplier_information", "") + "\n" + form_fields["COMMODITY[0]"]).strip()
        if form_fields:
            contract.raw_text += "\n\nPDF form values:\n" + "\n".join(f"{key}: {value}" for key, value in form_fields.items())
        contract.missing_sections = sorted(set(LABELS) - set(contract.sections))
        if not raw.strip():
            contract.warnings.append("No text layer found; scanned/empty document requires OCR or manual review")
        if not contract.sections:
            contract.warnings.append("No standardized contract sections identified")
            return contract
        supply = contract.sections.get("supply_price", "")
        pricing = prices(supply)
        contract.fields = {"prices": [p.model_dump(mode="json") for p in pricing],
                           "rate_structure": rate_structure(contract.sections.get("price_structure", "")),
                           "term_months": term(contract.sections.get("term", ""))[0],
                           **attributes("\n".join(contract.sections.values()))}
        contract.fields["form_fields"] = form_fields
        # Labels and values may occupy different PDF cells. Restore the label
        # solely for this conservative fee parser, while preserving the original.
        for key, value in attributes("Cancellation Fee: " + contract.sections.get("cancellation", "")).items():
            if value is not None and value != {} and value != []:
                contract.fields[key] = value
        contract.status = "partial" if contract.missing_sections else "parsed"
        if contract.missing_sections:
            contract.warnings.append("Missing sections: " + ", ".join(contract.missing_sections))
    except Exception as exc:
        contract.status = "failed"
        contract.warnings.append(f"Document parsing failed: {type(exc).__name__}: {exc}")
    return contract


def match_contract(contract: Contract, refs: list[DocumentRef], offers: list[Offer]) -> None:
    candidates = [offer for offer in offers if any(
        (ref.offer_key and ref.offer_key == offer.key) or
        (ref.product_id and ref.product_id == offer.product_id) for ref in refs)]
    method = "document_link_on_offer"
    if not candidates and contract.sections:
        method = "unique_price_term_context"
        candidates = [o for o in offers if contract.fields.get("term_months") == o.term_months and
                      any(o.price.value == Decimal(str(p["value"])) and o.price.unit == p["unit"]
                          for p in contract.fields.get("prices", []))]
        # Weak matching must have one result and an explicitly named utility.
        context = contract.sections.get("distribution_company", "")
        if len(candidates) != 1 or not utility_matches(context, candidates[0].utility):
            candidates = []
    if not candidates:
        contract.warnings.append("No unambiguous plan association; document retained for review")
        return
    for offer in candidates:
        named = [name for name in CONFIG["suppliers"] if normalized(name) in normalized(contract.sections.get("supplier_information", ""))]
        if named and offer.supplier not in named:
            contract.warnings.append(f"Supplier conflict for {offer.name}; not matched")
            continue
        prices_in_contract = contract.fields.get("prices", [])
        if prices_in_contract and not any((p["unit"] == "USD/kWh") == (offer.commodity == "electric") for p in prices_in_contract):
            contract.warnings.append(f"Commodity conflict for {offer.name}; not matched")
            continue
        distribution = contract.sections.get("distribution_company", "")
        known_utilities = [u for u in CONFIG["utilities"] if utility_matches(distribution, u)]
        if known_utilities and offer.utility not in known_utilities:
            contract.warnings.append(f"Utility conflict for {offer.name}; not matched")
            continue
        if offer.key not in contract.matched_offer_keys:
            contract.matched_offer_keys.append(offer.key)
        if contract.id not in offer.contract_ids:
            offer.contract_ids.append(contract.id)
        contract_structure = contract.fields.get("rate_structure")
        if not offer.rate_structure and contract_structure in {"fixed", "variable", "indexed", "hybrid"}:
            offer.rate_structure = contract_structure
            offer.warnings = [
                warning for warning in offer.warnings
                if warning != "Rate structure not explicitly established"
            ]
        if prices_in_contract and not any(
            o["unit"] == offer.price.unit
            and abs(Decimal(str(o["value"])) - offer.price.value) <= Decimal("0.0001")
            for o in prices_in_contract
        ):
            offer.warnings.append("Contract price differs from offer price; review both sources")
        if contract.fields.get("term_months") is not None and offer.term_months is not None and contract.fields["term_months"] != offer.term_months:
            offer.warnings.append("Contract term differs from offer term; review both sources")
    contract.match_method = method if contract.matched_offer_keys else None
