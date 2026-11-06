from bs4 import BeautifulSoup
from pathlib import Path
import re

# --- Constellation ---
print("=== CONSTELLATION ===")
path = Path(__file__).resolve().parent / "debug/Constellation_Energy__PSEandG_Electric__utility_not_found.html"
with path.open(encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'lxml')

print("All links with pdf/contract/summary/efl:")
for a in soup.find_all('a', href=True):
    h = a.get('href', '')
    t = a.get_text(strip=True)
    if any(kw in h.lower() or kw in t.lower() for kw in ['pdf', 'contract', 'efl', 'summary', 'disclosure', 'terms']):
        print(f'  {repr(t[:60])} -> {h[:100]}')

print("\nData attrs in rate cards:")
for el in soup.find_all(attrs={'data-rate': True}):
    print(f'  tag={el.name} data-rate={el.get("data-rate")} data-product-plan={el.get("data-product-plan")} classes={el.get("class")}')
    for a in el.find_all('a', href=True):
        print(f'    link: {repr(a.get_text(strip=True)[:40])} -> {a["href"][:80]}')

print("\nAll buttons in rate cards:")
for el in soup.find_all(attrs={'data-rate': True}):
    for btn in el.find_all('button'):
        print(f'  btn: {repr(btn.get_text(strip=True)[:60])}')
    for a in el.find_all('a'):
        print(f'  a: {repr(a.get_text(strip=True)[:60])} href={a.get("href","")[:60]}')

# Find plan detail links anywhere
print("\nAll 'Plan Details' or 'More Info' links on page:")
for a in soup.find_all('a'):
    t = a.get_text(strip=True)
    if re.search(r'plan.?detail|more.?info|learn.?more|see.?details', t, re.I):
        print(f'  {repr(t)} href={a.get("href","")[:80]}')
