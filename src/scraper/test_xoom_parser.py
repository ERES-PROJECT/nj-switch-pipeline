"""Opt-in offline diagnostic; automated regression coverage lives in tests/."""
import argparse
from pathlib import Path
from nj_scraper import generic_parser


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path, help="A saved Xoom offer page")
    args = parser.parse_args()
    row = {"supplier_name": "Xoom Energy", "edc_name": "PSE&G Electric",
           "commodity": "electric", "test_zip": "07102",
           "website_url": "https://xoomenergy.com/en/residential/new-jersey"}
    results = generic_parser(args.html.read_text(encoding="utf-8"), row)
    print(f"Results: {len(results)} offers")
    for result in results:
        print(f"{result['plan_name']}: {result['rate']} {result['rate_unit']}; term={result['term_months']}; type={result['plan_type']}")


if __name__ == "__main__":
    main()
