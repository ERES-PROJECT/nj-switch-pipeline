"""Build a date-scoped catalog of the latest live result per supplier/market."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--date", help="Collection date in YYYY-MM-DD form")
    scope.add_argument("--run", type=Path, help="Use exactly one run directory")
    parser.add_argument("--runs", type=Path, default=Path("data/runs"))
    parser.add_argument("--registry", type=Path, default=Path("src/TPSCompilation/master_third_party_supplier_list.csv"))
    parser.add_argument("--exclude-supplier", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    reports = [args.run / "results.json"] if args.run else list(
        args.runs.glob(f"{args.date.replace('-', '')}*/results.json")
    )
    latest: dict[tuple[str, str, str, str], dict] = {}
    for report in reports:
        for result in json.loads(report.read_text(encoding="utf-8")):
            query = result["query"]
            if query["supplier"] in args.exclude_supplier:
                continue
            key = (query["supplier"], query["utility"], query["commodity"], query["zip"])
            stamp = result.get("finished_at") or result.get("started_at") or ""
            previous = latest.get(key)
            previous_stamp = (previous or {}).get("finished_at") or (previous or {}).get("started_at") or ""
            if previous is None or stamp >= previous_stamp:
                result["_run"] = report.parent.name
                latest[key] = result

    with args.registry.open(encoding="utf-8-sig", newline="") as handle:
        suppliers = sorted({row["supplier_name"] for row in csv.DictReader(handle)
                            if row["supplier_name"] not in args.exclude_supplier})

    offer_rows = []
    supplier_results = defaultdict(list)
    for result in latest.values():
        supplier_results[result["query"]["supplier"]].append(result)
        for offer in result.get("offers", []):
            captured = offer.get("captured_at", "")
            if args.date and not captured.startswith(args.date):
                continue
            price = offer.get("price") or {}
            offer_rows.append({
                "supplier": offer.get("supplier", ""),
                "utility": offer.get("utility", ""),
                "commodity": offer.get("commodity", ""),
                "zip": offer.get("zip", ""),
                "plan": offer.get("name", ""),
                "product_id": offer.get("product_id", ""),
                "rate": price.get("value", ""),
                "rate_unit": price.get("unit", ""),
                "rate_structure": offer.get("rate_structure", ""),
                "term_months": offer.get("term_months", ""),
                "monthly_fee": offer.get("monthly_fee", ""),
                "cancellation_fee": offer.get("cancellation_fee", ""),
                "renewable_percentage": offer.get("renewable_percentage", ""),
                "document_count": len(offer.get("contract_ids", [])) or len(offer.get("documents", [])),
                "source_url": offer.get("source_url", ""),
                "captured_at": captured,
                "result_status": result.get("status", ""),
                "run": result["_run"],
            })
    offer_rows.sort(key=lambda row: (row["supplier"], row["utility"], row["plan"], row["rate"]))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    csv_path = args.output.with_suffix(".csv")
    fields = list(offer_rows[0]) if offer_rows else ["supplier", "utility", "plan", "rate", "rate_unit"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(offer_rows)

    lines = [
        f"# Current offers by scraper — {args.date or args.run.name}",
        "",
        "Latest live result per supplier/utility/commodity/ZIP collected on this date. "
        "A zero means the scraper produced no current offer row; it does not imply the supplier has no offer.",
        "",
        "## Scraper summary",
        "",
        "| Supplier | Markets run | Current offers | Latest statuses |",
        "|---|---:|---:|---|",
    ]
    for supplier in suppliers:
        results = supplier_results.get(supplier, [])
        statuses = Counter(result.get("status", "unknown") for result in results)
        status_text = ", ".join(f"{name}: {count}" for name, count in sorted(statuses.items())) or "not run"
        count = sum(1 for row in offer_rows if row["supplier"] == supplier)
        lines.append(f"| {supplier} | {len(results)} | {count} | {status_text} |")

    lines.extend([
        "",
        "## Gathered offers",
        "",
        "| Supplier | Utility | Plan | Rate | Structure | Term | Documents |",
        "|---|---|---|---:|---|---:|---:|",
    ])
    for row in offer_rows:
        term = row["term_months"] if row["term_months"] not in (None, "") else "—"
        structure = row["rate_structure"] or "—"
        lines.append(
            f'| {row["supplier"]} | {row["utility"]} | {row["plan"]} | '
            f'{row["rate"]} {row["rate_unit"]} | {structure} | {term} | {row["document_count"]} |'
        )
    if not offer_rows:
        lines.append("| — | — | No current offers gathered | — | — | — | — |")
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(offer_rows)} offer rows to {csv_path} and {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
