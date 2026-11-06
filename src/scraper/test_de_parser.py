import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from bs4 import BeautifulSoup
import nj_scraper as sc

with (SCRIPT_DIR / "debug/DE_after_learn_more.html").open(encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'lxml')

row = {'supplier_name': 'Direct Energy', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'website_url': 'https://www.directenergy.com/new-jersey'}
results = sc._parse_direct_energy_cards(soup, row)
print(f'Electric plans: {len(results)}')
for r in results:
    print(f"  {r['plan_name']}  rate={r['rate']}  term={r['term_months']}  type={r['plan_type']}")
