"""
demo_test.py
------------
Fully automatic demo — no user interaction required.
Runs ONE row each for: Constellation, Direct Energy, Ambit, Think Energy.
Extracts plan rates AND contract summary PDFs/pages automatically.
Outputs: data/demo_results.csv
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import io
import re
import ssl
import zipfile
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import tempfile
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

from nj_scraper import (
    strategy_constellation,
    strategy_direct_energy,
    strategy_ambit,
    strategy_think_energy,
    strategy_nrg,
    strategy_major_energy,
    strategy_xoom_energy,
    generic_parser,
    extract_pdf_data_from_bytes,
    log,
    SCRIPT_DIR,
    DEBUG_DIR,
)

CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "TPSCompilation", "master_third_party_supplier_list.csv"
)
TARGET_SUPPLIERS = [
    ("Constellation Energy", strategy_constellation),
    ("Direct Energy",        strategy_direct_energy),
    ("Ambit Energy",         strategy_ambit),
    ("Think Energy",         strategy_think_energy),
    ("NRG",                  strategy_nrg),
    ("Major Energy",         strategy_major_energy),
    ("Xoom Energy",          strategy_xoom_energy),
]

# Keywords that identify a contract summary link
_CONTRACT_KW = re.compile(
    r"contract[\s_-]?summary|contract|terms[\s_-]?of[\s_-]?service|terms[\s_-]?and[\s_-]?conditions|tandc|disclosure|toc",
    re.IGNORECASE,
)
_CONTRACT_SUMMARY_KW = re.compile(r"contract[\s_-]?summary", re.IGNORECASE)
_PDF_EXT = re.compile(r"\.pdf(\?.*)?$", re.IGNORECASE)


def _absolute_url(href: str, base_url: str) -> str:
    """Resolve a possibly-relative href against the page's base URL."""
    return urllib.parse.urljoin(base_url, href)


def _fetch_url_bytes(url: str) -> bytes | None:
    """Download bytes from url with a browser-like User-Agent. Returns None on error."""
    try:
        # urllib does not accept URLs with unencoded spaces (e.g. "title=Terms of Service").
        # Re-encode path and query components while preserving already-encoded sequences.
        parts = urllib.parse.urlsplit(url)
        safe_url = urllib.parse.urlunsplit((
            parts.scheme,
            parts.netloc,
            urllib.parse.quote(parts.path, safe="/:@"),
            urllib.parse.quote(parts.query, safe="=&+%@#"),
            parts.fragment,
        ))
        req = urllib.request.Request(
            safe_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NJScraper/1.0)"},
        )
        # Some supplier sites (e.g. Major Energy) use certificates that Python's
        # bundled CA store cannot verify on Windows. Fall back to unverified context.
        _ssl_ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=20) as resp:
            return resp.read()
    except Exception as exc:
        log.debug("  CONTRACT  fetch error %s: %s", url, exc)
        return None


def _extract_docx_text(docx_bytes: bytes) -> str:
    """Extract plain text from a DOCX file (Office Open XML zip format)."""
    try:
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
            with z.open("word/document.xml") as f:
                tree = ET.parse(f)
        parts = [el.text for el in tree.iter(f"{{{ns}}}t") if el.text]
        return " ".join(parts)
    except Exception as exc:
        log.debug("  CONTRACT  DOCX parse error: %s", exc)
        return ""


def extract_contract_summaries(page, row) -> list[dict]:
    """
    Given a page already showing plan listings, find all contract-summary links
    and extract rate data from each without any user interaction.

    Strategy (fully automatic):
      1. Parse the current page HTML for <a href> tags whose text or URL
         matches contract-summary keywords.
      2. For each candidate URL:
         a. If it ends in .pdf  → download bytes, parse with pdfplumber.
         b. Otherwise           → open in a new page (context.new_page + goto),
                                  extract text, parse with regex.
      3. Never clicks buttons that could navigate the current page.
    """
    results = []
    supplier, edc = row["supplier_name"], row["edc_name"]
    base_url = page.url

    # Guard: page may still be navigating after a postback (e.g. Xoom ASP.NET).
    # Wait briefly for the load to settle, then try to get content.
    try:
        page.wait_for_load_state("domcontentloaded", timeout=5_000)
    except Exception:
        pass
    try:
        page_html = page.content()
    except Exception as e:
        log.warning("  CONTRACT  cannot read page content (%s) — skipping", type(e).__name__)
        return []
    soup = BeautifulSoup(page_html, "lxml")
    seen_urls: set[str] = set()
    summary_hrefs: list[tuple[str, str]] = []      # (absolute_url, link_text)
    non_summary_hrefs: list[tuple[str, str]] = []  # (absolute_url, link_text)

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        link_text = a.get_text(separator=" ", strip=True)
        abs_url = _absolute_url(href, base_url)
        if abs_url in seen_urls:
            continue
        if _CONTRACT_KW.search(link_text) or _CONTRACT_KW.search(href) or _PDF_EXT.search(href):
            seen_urls.add(abs_url)
            if _CONTRACT_SUMMARY_KW.search(link_text) or _CONTRACT_SUMMARY_KW.search(href):
                summary_hrefs.append((abs_url, link_text))
            else:
                non_summary_hrefs.append((abs_url, link_text))

    # Process all unique contract-summary links first, then a bounded number of
    # other contract-related links (Terms, disclosure, etc.) to avoid over-fetching.
    max_non_summary = 8
    candidate_hrefs = summary_hrefs + non_summary_hrefs[:max_non_summary]

    log.info(
        "  CONTRACT  %d candidate link(s) found for %s (%d summary, %d other; processing %d)",
        len(summary_hrefs) + len(non_summary_hrefs),
        supplier,
        len(summary_hrefs),
        len(non_summary_hrefs),
        len(candidate_hrefs),
    )

    for abs_url, link_text in candidate_hrefs:
        log.info("  CONTRACT  processing: '%s'  →  %s", link_text[:60], abs_url[:80])
        try:
            if _PDF_EXT.search(abs_url):
                # --- Direct PDF download (URL ends in .pdf) ---
                pdf_bytes = _fetch_url_bytes(abs_url)
                if not pdf_bytes:
                    continue
                parsed = extract_pdf_data_from_bytes(pdf_bytes, row)
                for r in parsed:
                    r["data_source"] = "contract_summary_pdf"
                    r["contract_url"] = abs_url
                if parsed:
                    log.info("  CONTRACT  PDF → %d row(s)", len(parsed))
                    results.extend(parsed)
                else:
                    log.warning("  CONTRACT  PDF had no parseable rates")
            else:
                # --- Non-.pdf URL: could be a download or an HTML page ---
                # Try urllib first — it fetches the raw bytes without the browser's
                # "Download is starting" interception that blocks page.goto().
                file_bytes = _fetch_url_bytes(abs_url)
                if file_bytes and file_bytes[:4] == b'%PDF':
                    # Server returns a PDF via Content-Disposition: attachment
                    parsed = extract_pdf_data_from_bytes(file_bytes, row)
                    for r in parsed:
                        r["data_source"] = "contract_summary_pdf"
                        r["contract_url"] = abs_url
                    if parsed:
                        log.info("  CONTRACT  PDF (download) → %d row(s)", len(parsed))
                        results.extend(parsed)
                    else:
                        log.warning("  CONTRACT  PDF (download) had no parseable rates")
                elif file_bytes and file_bytes[:2] == b'PK':
                    # DOCX or other Office Open XML format
                    text = _extract_docx_text(file_bytes)
                    if not text:
                        log.warning("  CONTRACT  DOCX: no text extracted")
                        continue
                    rate_m = (re.search(r"([\d.]+)\s*¢", text)
                              or re.search(r"\$([\d.]+)\s*/\s*[kK][wW][hH]", text)
                              or re.search(r"([\d.]+)\s*cents?\s*/\s*[kK][wW][hH]", text, re.I)
                              or re.search(r"([\d.]+)\s*(?:per\s+)?kWh", text, re.I))
                    if rate_m:
                        term_m = re.search(r"(\d+)[\s-]*month", text, re.I)
                        results.append({
                            "supplier":    supplier,
                            "edc_name":    edc,
                            "commodity":   row["commodity"],
                            "plan_name":   link_text or "N/A",
                            "rate":        rate_m.group(1),
                            "term_months": term_m.group(1) if term_m else "N/A",
                            "plan_type":   "N/A",
                            "source_url":  row["website_url"],
                            "contract_url": abs_url,
                            "data_source": "contract_summary_docx",
                        })
                        log.info("  CONTRACT  DOCX → rate=%s", rate_m.group(1))
                    else:
                        log.warning("  CONTRACT  DOCX had no parseable rates")
                else:
                    # urllib failed or unknown binary — try browser navigation for HTML pages
                    new_page = page.context.new_page()
                    try:
                        new_page.goto(abs_url, wait_until="domcontentloaded", timeout=20_000)
                        new_page.wait_for_load_state("networkidle", timeout=10_000)
                        html = new_page.content()
                        soup2 = BeautifulSoup(html, "lxml")
                        text = soup2.get_text(separator=" ", strip=True)
                        rate_m = (re.search(r"([\d.]+)\s*¢", text)
                                  or re.search(r"\$([\d.]+)\s*/\s*[kK][wW][hH]", text)
                                  or re.search(r"([\d.]+)\s*cents?\s*/\s*[kK][wW][hH]", text, re.I))
                        if rate_m:
                            term_m = re.search(r"(\d+)[\s-]*month", text, re.I)
                            results.append({
                                "supplier":    supplier,
                                "edc_name":    edc,
                                "commodity":   row["commodity"],
                                "plan_name":   link_text or "N/A",
                                "rate":        rate_m.group(1),
                                "term_months": term_m.group(1) if term_m else "N/A",
                                "plan_type":   "N/A",
                                "source_url":  row["website_url"],
                                "contract_url": abs_url,
                                "data_source": "contract_summary_html",
                            })
                            log.info("  CONTRACT  HTML → rate=%s", rate_m.group(1))
                        else:
                            log.warning("  CONTRACT  HTML page had no parseable rates")
                    except Exception as nav_exc:
                        log.debug("  CONTRACT  nav error: %s", nav_exc)
                    finally:
                        try:
                            new_page.close()
                        except Exception:
                            pass
        except Exception as exc:
            log.debug("  CONTRACT  outer error: %s", exc)
            continue

    return results


def run():
    df = pd.read_csv(CSV_PATH, dtype={"test_zip": str})  # preserve leading zeros

    rows_to_test = []
    for name, fn in TARGET_SUPPLIERS:
        match = df[df["supplier_name"] == name]
        if not match.empty:
            rows_to_test.append((match.iloc[0], fn))
        else:
            log.warning("Supplier not found in CSV: %s", name)

    all_results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,   # fully automatic — no browser window
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )

        for row, strategy_fn in rows_to_test:
            supplier = row["supplier_name"]
            edc      = row["edc_name"]

            # Fresh isolated context per supplier
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 900},
                # Silently accept all dialogs automatically
                accept_downloads=True,
            )
            # Auto-dismiss any alert/confirm/prompt dialogs without user input
            ctx.on("dialog", lambda d: d.dismiss())

            page = ctx.new_page()

            log.info("=" * 60)
            log.info("[DEMO] %s / %s", supplier, edc)

            try:
                html, pdf_rows = strategy_fn(page, row)
            except Exception as exc:
                log.error("  strategy crashed: %s", exc)
                html, pdf_rows = None, []

            if html:
                # --- Parse plan listings ---
                plans = generic_parser(html, row)
                log.info("  PLANS: %d found", len(plans))
                for p in plans[:5]:
                    log.info("    plan='%s'  rate=%s  term=%s mo  type=%s",
                             p["plan_name"], p["rate"], p["term_months"], p["plan_type"])
                all_results.extend(plans)

                if not plans:
                    # Dump HTML for offline inspection
                    dump = os.path.join(DEBUG_DIR, f"{supplier.replace(' ','_')}__ZERO_PLANS.html")
                    with open(dump, "w", encoding="utf-8") as fh:
                        fh.write(html)
                    log.warning("  HTML dumped for inspection: %s", dump)

                # --- Contract summary extraction (no user interaction) ---
                contract_rows = extract_contract_summaries(page, row)
                if contract_rows:
                    log.info("  CONTRACT SUMMARIES: %d row(s)", len(contract_rows))
                    for cr in contract_rows[:3]:
                        log.info("    [contract] plan='%s'  rate=%s  src=%s",
                                 cr["plan_name"], cr["rate"], cr["data_source"])
                    all_results.extend(contract_rows)
                else:
                    log.warning("  CONTRACT SUMMARIES: none extracted")

                # Any PDFs / popup rows captured directly by the strategy itself
                all_results.extend(pdf_rows)

            else:
                log.warning("  NO HTML RETURNED by strategy")
                # pdf_rows may still carry plan data (e.g. Ambit popup rows)
                if pdf_rows:
                    log.info("  PLANS (from strategy pdf_rows): %d found", len(pdf_rows))
                    for p in pdf_rows[:5]:
                        log.info("    plan='%s'  rate=%s  term=%s mo  type=%s",
                                 p.get("plan_name"), p.get("rate"),
                                 p.get("term_months"), p.get("plan_type"))
                    all_results.extend(pdf_rows)

            try:
                ctx.close()
            except Exception:
                pass

        browser.close()

    # --- Write output ---
    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "demo_results.csv")

    if all_results:
        df_out = pd.DataFrame(all_results)

        # Deterministic dedupe to suppress repeated rows (e.g., duplicate Xoom plan card).
        dedupe_key = [
            "supplier", "plan_name", "rate", "term_months", "plan_type",
            "source_url", "data_source", "contract_url",
        ]
        available_key = [c for c in dedupe_key if c in df_out.columns]
        before = len(df_out)
        if available_key:
            df_out = df_out.drop_duplicates(subset=available_key, keep="first")
        removed = before - len(df_out)
        if removed > 0:
            log.info("Deduped %d row(s) before CSV write", removed)

        df_out.to_csv(out_path, index=False)
        log.info("Saved %d total rows → %s", len(df_out), out_path)
    else:
        log.warning("No results at all — check debug/ folder for screenshots")


if __name__ == "__main__":
    run()
