from nj_scraper import generic_parser
row = {
    'supplier_name': 'Xoom Energy',
    'edc_name': 'PSEandG Electric',
    'commodity': 'Electric',
    'test_zip': '07102',
    'website_url': 'https://xoom.example.com',
}
with open('debug/Xoom_Energy__PSEandG_Electric__xoom_after_continue.html', encoding='utf-8') as f:
    html = f.read()
results = generic_parser(html, row)
print(f'Results: {len(results)} rows')
for r in results:
    print(f"  {r['plan_name']}  rate={r['rate_cents']}  term={r['term_months']}  type={r['plan_type']}")
