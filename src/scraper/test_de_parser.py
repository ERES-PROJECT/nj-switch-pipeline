import sys
sys.path.insert(0, r'C:\Users\brian\School\JunSpring\CSB312\nj-switch-pipeline\src\scraper')
from bs4 import BeautifulSoup
import nj_scraper as sc

with open(r'C:\Users\brian\School\JunSpring\CSB312\nj-switch-pipeline\src\scraper\debug\DE_after_learn_more.html', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'lxml')

row = {'supplier_name': 'Direct Energy', 'edc_name': 'PSE&G Electric', 'commodity': 'electric', 'website_url': 'https://www.directenergy.com/new-jersey'}
results = sc._parse_direct_energy_cards(soup, row)
print(f'Electric plans: {len(results)}')
for r in results:
    print(f"  {r['plan_name']}  rate={r['rate']}  term={r['term_months']}  type={r['plan_type']}")
