import csv
import json
import re
from pathlib import Path

from .models import Query

CONFIG = json.loads(Path(__file__).with_name("config.json").read_text(encoding="utf-8"))
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = PROJECT_ROOT / "src/TPSCompilation/master_third_party_supplier_list.csv"


def normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def utility_matches(text: str, utility: str) -> bool:
    candidate = normalized(text)
    return any(normalized(alias) in candidate for alias in CONFIG["utilities"][utility])


def load_registry(path: Path = REGISTRY) -> list[Query]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    results = []
    inactive_suppliers = set(CONFIG.get("inactive_suppliers", []))
    inactive_markets = set(CONFIG.get("inactive_markets", []))
    for row in rows:
        # Preserve retired suppliers in the historical master CSV and fixtures,
        # but never schedule them in `list`, targeted collection, or `--all`.
        if row["supplier_name"] in inactive_suppliers:
            continue
        market_key = f'{row["supplier_name"]}|{row["edc_name"]}|{row["commodity"].lower()}'
        # A supplier may remain active elsewhere while a particular
        # utility/commodity combination is confirmed unavailable. Do not run
        # known-empty or unsupported markets in production collections.
        if market_key in inactive_markets:
            continue
        # Known supplier assignments in validated configuration supersede stale
        # `default` values retained in the historical registry CSV.
        scoped = f'{row["supplier_name"]}|{row["commodity"].lower()}'
        adapter = CONFIG.get("supplier_commodity", {}).get(
            scoped, CONFIG["suppliers"].get(row["supplier_name"], row.get("scraper_type") or "default")
        )
        skip = adapter == "skip" or row.get("scraper_status") == "manual_check_required"
        zips = [row["test_zip"], *CONFIG.get("additional_test_zips", {}).get(market_key, [])]
        for zip_code in dict.fromkeys(zips):
            results.append(Query(supplier=row["supplier_name"], utility=row["edc_name"],
                                 commodity=row["commodity"].lower(), zip=zip_code,
                                 url=row["website_url"], adapter=adapter,
                                 skip_reason=(row.get("notes") or "Registry marks this combination as skipped") if skip else None))
    return results
