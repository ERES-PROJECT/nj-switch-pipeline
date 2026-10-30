"""Conservative value extraction. Missing information stays missing."""
from decimal import Decimal
import re

from .models import Price

PRICE_RE = re.compile(
    r"(?P<dollar>\$)?\s*(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<cents>¢|cents?)?\s*(?:/|per\s+)\s*"
    r"(?P<unit>kwh|therms?|thm|ccf|dth|dekatherms?)\b", re.I)


def prices(text: str) -> list[Price]:
    result = []
    for match in PRICE_RE.finditer(text):
        # A numeric consumption quantity is not a monetary rate.
        if not (match["dollar"] or match["cents"]):
            continue
        unit = match["unit"].lower()
        canonical = "kWh" if unit == "kwh" else "therm" if unit.startswith("therm") or unit == "thm" else "CCF" if unit == "ccf" else "Dth"
        value = Decimal(match["value"]) / (100 if match["cents"] else 1)
        result.append(Price(value=value, unit=f"USD/{canonical}", raw=match.group(0).strip()))
    return result


def compatible(price: Price, commodity: str) -> bool:
    return (price.unit == "USD/kWh") == (commodity == "electric")


def term(text: str) -> tuple[int | None, str | None]:
    match = re.search(r"\b(\d{1,3})\s*[-–]?\s*(?:monthly\s+billing\s+cycles?|months?|mo\.?)\b", text, re.I)
    if match:
        return int(match[1]), "fixed_term"
    if re.search(r"month[- ]to[- ]month", text, re.I):
        return None, "month_to_month"
    return None, None


def rate_structure(text: str) -> str | None:
    # A contract can describe a fixed initial offer and its variable renewal in
    # the same section. The marketed initial plan remains a fixed product.
    if re.search(
        r"\bfixed\b[\s\S]{0,400}\b(?:after (?:the )?initial term|upon (?:expiration|renewal))\b"
        r"[\s\S]{0,300}\bvariable\b",
        text,
        re.I,
    ):
        return "fixed"
    found = set(re.findall(r"\b(fixed|variable|indexed|hybrid)\b", text.lower()))
    if len(found) == 1:
        return found.pop()
    if re.search(r"fixed.{0,80}(?:then|followed by).{0,40}variable", text, re.I):
        return "hybrid"
    return None


def attributes(text: str) -> dict:
    result: dict = {"fee_terms": {}, "incentives": []}
    for name, label in [("monthly_fee", r"(?:monthly\s+(?:service\s+)?(?:fee|charge)|base\s+fee)"),
                        ("enrollment_fee", r"(?:enrollment|enrolment|sign[- ]up)\s+(?:fee|charge)"),
                        ("cancellation_fee", r"(?:(?:early\s+termination|(?:early\s+)?cancellation|cancel)\s+(?:fee|charge)|ETF)")]:
        # Capture the evidence even when a conditional fee cannot be one number.
        match = re.search(rf"(?:no\s+)?{label}\s*:?\s*[^\n;]{{0,220}}", text, re.I)
        if not match:
            continue
        raw = match[0].strip()
        result["fee_terms"][name] = raw
        if re.search(r"\bif\b|unless|except|waiv", raw, re.I):
            continue
        if re.search(r"^no\b|:\s*(?:none|no|\$?0(?:\.00)?)\b", raw, re.I):
            result[name] = Decimal(0)
        else:
            amount = re.search(r"\$\s*(\d+(?:\.\d+)?)", raw)
            if amount and not re.search(r"per\s+(?:remaining\s+)?month|up to|whichever|prorat|waiv", raw, re.I):
                result[name] = Decimal(amount[1])
    green = re.search(r"(?:((?:\d+(?:\.\d+)?))\s*%\s*(?:renewable|green|wind|solar|clean)|"
                      r"(?:renewable|green|wind|solar|clean)(?:\s+content)?\s*:?\s*((?:\d+(?:\.\d+)?))\s*%)", text, re.I)
    green_value = Decimal(green[1] or green[2]) if green else None
    if green_value is not None and 0 <= green_value <= 100:
        result["renewable_percentage"] = green_value
    if re.search(r"\brenewable|\bgreen|\bclean energy", text, re.I):
        result["renewable_claim"] = next((line.strip() for line in text.splitlines() if re.search(r"renewable|green|clean energy", line, re.I)), text)[:1000]
    sources = sorted(set(re.findall(r"\b(wind|solar|hydro(?:power)?|biomass|geothermal)\b", text, re.I)))
    if sources:
        result["renewable_source"] = ", ".join(sources)
    result["incentives"] = [line.strip() for line in text.splitlines()
                            if re.search(r"cash\s?back|gift\s?card|reward|discount|bonus|incentive|rebate|\d+\s*%\s+off", line, re.I)][:20]
    return result
