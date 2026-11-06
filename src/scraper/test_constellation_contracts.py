"""
Quick test: run Constellation strategy, then run extract_contract_summaries,
and print all candidates/results with full debug.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")

from playwright.sync_api import sync_playwright
import nj_scraper as ns
import demo_test as dt

import pandas as pd
_df = pd.read_csv(
    SCRIPT_DIR.parent / "TPSCompilation/master_third_party_supplier_list.csv",
    dtype={'test_zip': str}
)
ROW = _df[_df['supplier_name'] == 'Constellation Energy'].iloc[0]

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(accept_downloads=True)
    page = ctx.new_page()
    
    print("--- Running strategy_constellation ---")
    html, extras = ns.strategy_constellation(page, ROW)
    print(f"HTML length: {len(html) if html else 0}")
    
    if html:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        print("\n--- All PDF links in page ---")
        import re
        PDF_RE = re.compile(r'\.pdf(\?.*)?$', re.I)
        for a in soup.find_all('a', href=True):
            if PDF_RE.search(a['href']):
                print(f"  {repr(a.get_text(strip=True)[:50])} -> {a['href'][:100]}")
        
        print("\n--- All 'terms' links ---")
        for a in soup.find_all('a', href=True):
            t = a.get_text(strip=True)
            h = a['href']
            if re.search(r'terms|contract|disclosure|tandc', h+t, re.I):
                print(f"  {repr(t[:50])} -> {h[:100]}")
        
        print("\n--- Running extract_contract_summaries ---")
        results = dt.extract_contract_summaries(page, ROW)
        print(f"Results: {len(results)}")
        for r in results:
            print(f"  {r}")
    
    ctx.close()
    browser.close()
