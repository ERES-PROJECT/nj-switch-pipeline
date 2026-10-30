"""Compatibility entry points for the evidence-first collector.

Use `python -m nj_switch.cli` for structured CollectionResult output.
The original implementation is preserved in git and data/legacy/pre-v2-baseline.
Diagnostic tuple functions return offer rows only, never PDF-derived pseudo-plans.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import sys

from nj_switch.cli import main as cli_main
from nj_switch.contracts import extract_contract
from nj_switch.evidence import ArtifactStore
from nj_switch.models import Query
from nj_switch.navigation import STRATEGIES
from nj_switch.offers import parse_html
from nj_switch.pipeline import collect
from nj_switch.registry import CONFIG, PROJECT_ROOT
from nj_switch.reporting import slug, write_report
from nj_switch.transport import Transport

log = logging.getLogger(__name__)
SCRIPT_DIR = str(Path(__file__).parent)
DEBUG_DIR = str(PROJECT_ROOT / "data/runs")
SCRAPER_TYPE_MAP = CONFIG["suppliers"]


def query_from_row(row, adapter=None):
    supplier = row["supplier_name"]
    utility = row["edc_name"].replace("PSEandG", "PSE&G")
    return Query(supplier=supplier, utility=utility, commodity=row["commodity"].lower(),
                 zip=row["test_zip"], url=row["website_url"],
                 adapter=adapter or row.get("scraper_type") or SCRAPER_TYPE_MAP.get(supplier, "default"))


def _legacy_row(offer):
    result = offer.model_dump(mode="json")
    # Preserve the old diagnostic rate convention, but make its unit explicit.
    result.update(plan_name=offer.name, edc_name=offer.utility,
                  rate=str(offer.price.value * 100), rate_unit=offer.price.unit.replace("USD/", "cents/"),
                  plan_type=offer.rate_structure, data_source=offer.source_kind,
                  contract_url=offer.documents[0].url if offer.documents else "")
    return result


def _strategy(page, row, adapter):
    query = query_from_row(row, adapter)
    root = PROJECT_ROOT / "data/runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    root.mkdir(parents=True)
    # Reuse the caller's browser, with a fresh isolated context managed by collect.
    result = collect(query, page.context.browser, root / slug(query))
    write_report([result], root)
    log.warning("Compatibility call: %s; evidence saved to %s", result.status, root)
    return None, [_legacy_row(offer) for offer in result.offers]


def strategy_constellation(page, row):
    return _strategy(page, row, "constellation")


def strategy_direct_energy(page, row):
    return _strategy(page, row, "direct_energy")


def strategy_ambit(page, row):
    return _strategy(page, row, "ambit")


def strategy_think_energy(page, row):
    return _strategy(page, row, "think_energy")


def strategy_nrg(page, row):
    return _strategy(page, row, "nrg")


def strategy_major_energy(page, row):
    return _strategy(page, row, "major_energy")


def strategy_xoom_energy(page, row):
    return _strategy(page, row, "xoom_energy")


def strategy_frontier(page, row):
    return _strategy(page, row, "frontier")


def strategy_cleanchoice(page, row):
    return _strategy(page, row, "cleanchoice")


def strategy_default(page, row):
    return _strategy(page, row, "default")


def generic_parser(html_content, row):
    query = query_from_row(row)
    return [_legacy_row(offer) for offer in parse_html(html_content or "", query, query.url, "diagnostic-not-persisted")]


def download_pdf_from_url(url):
    transport = Transport()
    try:
        return transport.get(url)[0]
    finally:
        transport.close()


def extract_pdf_data_from_bytes(pdf_bytes, row):
    """Return a contract record, not a plan synthesized from every number in a PDF."""
    query = query_from_row(row)
    store = ArtifactStore(PROJECT_ROOT / "data/runs" / ("document-" + uuid4().hex) / "artifacts")
    artifact = store.save(pdf_bytes, "pdf", query.url)
    contract = extract_contract(pdf_bytes, query.url, artifact["id"])
    return [{"record_type": "contract", **contract.model_dump(mode="json")}]


def main():
    args = sys.argv[1:]
    commands = {"list", "backup", "collect", "discover", "replay", "verify", "freeze-fixture"}
    return cli_main(args if args and args[0] in commands else ["collect", *args])


if __name__ == "__main__":
    raise SystemExit(main())
