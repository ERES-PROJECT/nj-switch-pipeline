"""Inspect Direct Energy HTML for any hidden EFL/PDF URL patterns"""
from bs4 import BeautifulSoup
import re, json

with open(r'C:\Users\brian\School\JunSpring\CSB312\nj-switch-pipeline\src\scraper\debug\Direct_Energy__PSEandG_Electric__no_planlookup.html', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'lxml')

# Search raw HTML for pdf URLs
print("=== PDF URLs in raw HTML ===")
pdf_urls = re.findall(r'https?://[^\s"\'<>]+\.pdf[^\s"\'<>]*', html)
for u in sorted(set(pdf_urls)):
    print(' ', u[:120])

# Search for EFL or efl patterns
print("\n=== EFL references ===")
efl_matches = re.findall(r'[^\s"\'<>]*efl[^\s"\'<>]*', html, re.I)
for m in sorted(set(efl_matches))[:20]:
    print(' ', m[:100])

# Search for 'content/dam' (common Adobe AEM CMS pattern for PDFs)
print("\n=== content/dam patterns ===")
dam_matches = re.findall(r'[^\s"\'<>]*content/dam[^\s"\'<>]*', html, re.I)
for m in sorted(set(dam_matches))[:20]:
    print(' ', m[:100])

# Search for any script with product IDs
print("\n=== Script blocks with product data ===")
for script in soup.find_all('script'):
    t = script.string or ''
    if 'product' in t.lower() and ('pdf' in t.lower() or 'url' in t.lower() or 'efl' in t.lower()):
        print(' Script (first 300 chars):', t[:300])
        print()

# Look for JSON data embedded in page
print("\n=== JSON-LD or data attributes with URLs ===")
for el in soup.find_all(attrs={'data-product': True}):
    print('  data-product:', el.get('data-product', '')[:200])
for el in soup.find_all(type='application/json'):
    print('  JSON:', str(el)[:300])
for el in soup.find_all(type='application/ld+json'):
    print('  LD+JSON:', str(el)[:300])
