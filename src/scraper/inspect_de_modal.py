"""Inspect DE_after_learn_more.html to understand modal structure"""
from bs4 import BeautifulSoup
from pathlib import Path
import re

path = Path(__file__).resolve().parent / "debug/DE_after_learn_more.html"
with path.open(encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'lxml')

# Count plan modals (are all 8 pre-rendered in DOM?)
modals = soup.find_all(class_=lambda c: c and 'modal' in str(c).lower())
print(f"Total elements with 'modal' in class: {len(modals)}")

# Find all Contract Summary links across all modals
print("\nAll 'Contract Summary' / 'Terms and Conditions' links:")
for a in soup.find_all('a', href=True):
    t = a.get_text(strip=True)
    h = a['href']
    if re.search(r'contract|terms.and.cond|tandc|RatePlanSummary|TCPage', t+h, re.I):
        print(f"  {repr(t[:50])} -> {h[:120]}")

# Find all RateID values in the HTML
print("\nAll RateID values in raw HTML:")
rate_ids = re.findall(r'RateID=(\d+)', html)
print(f"  {sorted(set(rate_ids))}")

# Find all Doc= values in TCPage URLs
docs = re.findall(r'Doc=([A-Z0-9]+)', html)
print(f"\nAll Doc= values: {sorted(set(docs))}")

# Check if modals for all 8 plans are in DOM
print("\nModal div details:")
for m in modals[:5]:
    links = [(a.get_text(strip=True), a['href']) for a in m.find_all('a', href=True) if re.search(r'RatePlan|TCPage', a['href'], re.I)]
    if links:
        print(f"  {m.get('class')}: {links}")
