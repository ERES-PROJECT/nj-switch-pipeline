from bs4 import BeautifulSoup
from pathlib import Path
import re

path = Path(__file__).resolve().parent / "debug/Direct_Energy__PSEandG_Electric__no_planlookup.html"
with path.open(encoding='utf-8') as f:
    html = f.read()
    soup = BeautifulSoup(html, 'lxml')

# Look for any script tags with plan/contract/PDF data
for script in soup.find_all('script'):
    text = script.string or ''
    if 'contract' in text.lower() or 'pdf' in text.lower() or 'efl' in text.lower():
        print('SCRIPT with contract/pdf/efl:', text[:500])
        print('---')

# All links with pdf or contract
print('\nALL links with pdf or contract in href/text:')
for a in soup.find_all('a', href=True):
    h = a.get('href', '')
    t = a.get_text(strip=True)
    if 'pdf' in h.lower() or 'contract' in t.lower() or 'efl' in t.lower() or 'summary' in t.lower():
        print(' ', repr(t), '->', h[:120])

# Product IDs from class names
print('\nProduct cards and IDs:')
cards = soup.find_all('div', class_='product-card')
for c in cards[:8]:
    classes = c.get('class', [])
    pid = next((cl for cl in classes if cl.startswith('product-id-')), None)
    name_el = c.find('h2')
    name = name_el.text if name_el else '?'
    print(f'  {pid}: {name}')
