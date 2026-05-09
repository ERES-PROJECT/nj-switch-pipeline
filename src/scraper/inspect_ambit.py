"""Inspect Ambit ZERO_PLANS HTML - look for plan popup content, term data, and contract links"""
from bs4 import BeautifulSoup
import re

# Try the most recent ambit debug files
import os
debug_dir = r'C:\Users\brian\School\JunSpring\CSB312\nj-switch-pipeline\src\scraper\debug'
ambit_files = [f for f in os.listdir(debug_dir) if 'ambit' in f.lower() or 'Ambit' in f]
print("Ambit debug files:", ambit_files)

for fname in ambit_files:
    if not fname.endswith('.html'):
        continue
    path = os.path.join(debug_dir, fname)
    with open(path, encoding='utf-8') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'lxml')
    print(f"\n=== {fname} ({len(html)} bytes) ===")
    
    # Look for plan info containers
    plan_containers = soup.find_all(class_=lambda c: c and any(kw in str(c).lower() for kw in ['plan', 'offer', 'rate', 'term', 'contract']))
    print(f"  Elements with plan/offer/rate/term: {len(plan_containers)}")
    
    # Look for term data
    term_matches = re.findall(r'(\d+)\s*(?:-\s*)?[Mm]onth|\bterm\b.*?(\d+)', html, re.I)
    print(f"  Term mentions: {term_matches[:10]}")
    
    # Look for price / rate data
    rates = re.findall(r'[\d.]+\s*[¢¢\u00a2]|[\d.]+\s*/\s*kWh|\$[\d.]+', html, re.I)
    print(f"  Rate patterns: {rates[:10]}")
    
    # Look for PDF or contract links
    print("  Contract/PDF links:")
    for a in soup.find_all('a', href=True):
        h = a.get('href', '')
        t = a.get_text(strip=True)
        if re.search(r'pdf|contract|terms|summary|disclosure', h+t, re.I):
            print(f"    {repr(t[:50])} -> {h[:100]}")
    
    # Look for ng-* directives (Angular data binding for term)
    ng_shows = soup.find_all(attrs={'ng-show': re.compile(r'term', re.I)})
    if ng_shows:
        print(f"  ng-show with 'term': {[str(e)[:200] for e in ng_shows[:3]]}")
    
    # Look for plan detail container
    details = soup.find_all(id=re.compile(r'plan|detail|modal|popup', re.I))
    if details:
        for d in details[:3]:
            print(f"  Detail container #{d.get('id')}: {str(d)[:300]}")
