"""
Test what clicking 'Learn more' does on Direct Energy plan cards.
Captures what URL/modal appears after clicking the first plan's button.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEBUG_DIR = SCRIPT_DIR / "debug"
sys.path.insert(0, str(SCRIPT_DIR))
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from playwright.sync_api import sync_playwright
import pandas as pd
import nj_scraper as ns
from bs4 import BeautifulSoup
import re

_df = pd.read_csv(
    SCRIPT_DIR.parent / "TPSCompilation/master_third_party_supplier_list.csv",
    dtype={'test_zip': str}
)
ROW = _df[_df['supplier_name'] == 'Direct Energy'].iloc[0]

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)  # visible so we can see what happens
    ctx = browser.new_context(accept_downloads=True, viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    print("--- Running strategy_direct_energy ---")
    html, _ = ns.strategy_direct_energy(page, ROW)
    print(f"Page URL after strategy: {page.url}")

    if html:
        soup = BeautifulSoup(html, 'lxml')
        cards = soup.find_all('div', class_='product-card')
        print(f"Found {len(cards)} product-card divs")

        # Now try clicking the first 'Learn more' button and see what happens
        print("\n--- Clicking 'Learn more' on first plan ---")
        learn_btns = page.query_selector_all('button:has-text("Learn more"), button:has-text("Learn More")')
        print(f"Found {len(learn_btns)} 'Learn more' buttons")

        if learn_btns:
            # Listen for new page opens
            new_page_url = [None]
            def on_page(p):
                new_page_url[0] = p.url
                print(f"  NEW PAGE opened: {p.url}")
                # Save HTML from new page
                p.wait_for_load_state("domcontentloaded")
                with (DEBUG_DIR / "DE_learn_more_newpage.html").open('w', encoding='utf-8') as f:
                    f.write(p.content())

            ctx.on("page", on_page)

            learn_btns[0].click()
            page.wait_for_timeout(3000)

            if new_page_url[0]:
                print(f"  Navigation was to new page: {new_page_url[0]}")
            else:
                print(f"  Same page URL: {page.url}")
                # Check for modal/overlay
                new_html = page.content()
                new_soup = BeautifulSoup(new_html, 'lxml')
                # Save for inspection
                with (DEBUG_DIR / "DE_after_learn_more.html").open('w', encoding='utf-8') as f:
                    f.write(new_html)
                print("  Saved HTML to DE_after_learn_more.html")

                # Look for modals
                for cls_kw in ['modal', 'overlay', 'popup', 'detail', 'efl', 'pdf']:
                    els = new_soup.find_all(class_=lambda c: c and cls_kw in str(c).lower())
                    if els:
                        print(f"  Found {len(els)} elements with '{cls_kw}' in class")

                # Look for PDF links that appeared
                print("\n  PDF links in post-click HTML:")
                for a in new_soup.find_all('a', href=True):
                    h = a['href']
                    t = a.get_text(strip=True)
                    if re.search(r'\.pdf|contract|efl|summary|terms', h+t, re.I):
                        print(f"    {repr(t[:50])} -> {h[:100]}")

    input("Press Enter to close browser...")
    ctx.close()
    browser.close()
