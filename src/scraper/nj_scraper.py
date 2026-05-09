"""
nj_scraper.py
-------------
Web scraper for New Jersey Third-Party Supplier (TPS) electricity and gas rates.
Driven by master_third_party_supplier_list.csv. Uses Playwright for browser
automation, BeautifulSoup for HTML parsing, and pdfplumber for PDF contract
summary extraction.

Debug artefacts (screenshot + HTML dump) are saved to debug/ on every failure
so exact page state can be inspected without re-running.
"""

import io
import os
import re
import logging
import tempfile
import urllib.request

import pandas as pd
import pdfplumber
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH   = os.path.join(SCRIPT_DIR, "scraper.log")
DEBUG_DIR  = os.path.join(SCRIPT_DIR, "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging — writes to file AND console
# ---------------------------------------------------------------------------
_fmt = "%(asctime)s  %(levelname)-8s  %(message)s"
logging.basicConfig(
    level=logging.DEBUG,
    format=_fmt,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(),          # also print to terminal
    ],
)
# Silence noisy third-party loggers
logging.getLogger("pdfminer").setLevel(logging.WARNING)
logging.getLogger("pdfplumber").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scraper type → supplier name mapping (applied when column absent in CSV)
# ---------------------------------------------------------------------------
SCRAPER_TYPE_MAP = {
    "Constellation Energy": "constellation",
    "Direct Energy":        "direct_energy",
    "Ambit Energy":         "ambit",
    "Think Energy":         "think_energy",
    "NRG":                  "nrg",
}

# Constellation's <select id="utility"> shows different labels than our CSV EDC names.
# This map translates CSV edc_name → the exact <option> label on the site.
CONSTELLATION_EDC_MAP: dict[str, str] = {
    "PSE&G Electric":   "PSEG",
    "PSE&G Gas":        "PSEG",
    "JCP&L Electric":   "Jersey Central (JCPL)",
    "ACE Electric":     "Atlantic City Electric",
    "Rockland Electric": "Rockland Electric",
    # Gas-only utilities — Constellation NJ page may not offer gas plans;
    # these will gracefully fall through to save_debug_artefacts if absent.
    "NJNG Gas":         "NJ Natural Gas",
    "SJG Gas":          "South Jersey Gas",
    "ETG Gas":          "Elizabethtown Gas",
}

# ---------------------------------------------------------------------------
# Compiled regex patterns (reused everywhere)
# ---------------------------------------------------------------------------
_PRICE_PATTERN = re.compile(
    r"(\d{1,3}(?:\.\d{1,4})?)\s*(?:¢|cents?)?\s*(?:per\s+)?(?:kWh|therm|ccf|dekatherm|dth)",
    re.IGNORECASE,
)
_CENT_PATTERN  = re.compile(r"(\d{1,3}(?:\.\d{1,4})?)\s*[¢¢]")
_TERM_PATTERN  = re.compile(r"(\d{1,3})\s*[-–]?\s*[Mm]onth")
_TYPE_PATTERN  = re.compile(r"\b(Fixed|Variable|Indexed)\b", re.IGNORECASE)
_PLAN_CLASSES  = re.compile(
    r"\b(?:plan|offer|rate|product|card|package|deal)\b", re.IGNORECASE
)
# Matches dollar-per-unit rates like "$0.15490 per kWh" or "$0.06591 per therm"
# (Major Energy format).  Must be normalised to ¢ before _PRICE_PATTERN runs.
_DOLLAR_KWH_PATTERN = re.compile(
    r'\$\s*(0\.\d{2,6})\s*(?:per\s+|/\s*)?(kWh|therm|ccf|dekatherm|dth)',
    re.IGNORECASE,
)


def _normalize_dollar_rates(text: str) -> str:
    """Replace '$0.15490 per kWh' with '15.49¢/kWh' so _PRICE_PATTERN can match it."""
    def _repl(m: re.Match) -> str:
        cents = float(m.group(1)) * 100
        return f"{cents:.4f}\u00a2/{m.group(2)}"
    return _DOLLAR_KWH_PATTERN.sub(_repl, text)
# Heading candidates that are navigation / UI chrome — skip them in the div fallback
_NAV_TEXT = re.compile(
    r"\b(?:support|question|contact|menu|login|sign\s*in|about|home|privacy|terms|"
    r"faq|help|cart|account|chat|call|toll.free|subscribe|newsletter|back|close|"
    r"next|previous|submit|cancel|agree|continue|description|details|overview|summary)\b",
    re.IGNORECASE,
)


# ===========================================================================
# Debug helpers
# ===========================================================================

def _safe_tag(supplier: str, edc: str) -> str:
    """Return a filesystem-safe string for use in debug filenames."""
    tag = f"{supplier}__{edc}".replace(" ", "_").replace("/", "-").replace("&", "and")
    return re.sub(r"[^A-Za-z0-9_\-]", "", tag)[:80]


def save_debug_artefacts(page, supplier: str, edc: str, step: str) -> None:
    """Save a screenshot and full HTML dump to the debug/ directory."""
    tag   = _safe_tag(supplier, edc)
    stem  = os.path.join(DEBUG_DIR, f"{tag}__{step}")
    try:
        page.screenshot(path=f"{stem}.png", full_page=True)
        with open(f"{stem}.html", "w", encoding="utf-8") as fh:
            fh.write(page.content())
        log.debug("DEBUG  saved artefacts → %s.[png|html]", stem)
    except Exception as inner:
        log.debug("DEBUG  could not save artefacts: %s", inner)


# ===========================================================================
# PDF utilities
# ===========================================================================

def extract_pdf_data_from_bytes(pdf_bytes: bytes, row) -> list[dict]:
    """
    Extract rate data from a PDF contract summary (raw bytes).
    Uses pdfplumber to pull all text from the first two pages,
    then applies the same regex patterns as the HTML parser.
    """
    results = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "\n".join(
                (page.extract_text() or "") for page in pdf.pages[:3]
            )
        log.debug("PDF  extracted %d chars of text", len(text))
        results = _parse_text_block(text, row, source="pdf")
    except Exception as exc:
        log.error("PDF_PARSE_ERROR  %s / %s | %s", row["supplier_name"], row["edc_name"], exc)
    return results


def download_pdf_from_url(url: str) -> bytes | None:
    """Download a PDF from a URL and return raw bytes, or None on error."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NJScraper/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read()
    except Exception as exc:
        log.error("PDF_DOWNLOAD_ERROR  %s | %s", url, exc)
        return None


def intercept_and_extract_pdf(page, row, trigger_fn) -> list[dict]:
    """
    Call trigger_fn() (e.g. clicking a PDF link), capture the downloaded file
    via Playwright's download event, and extract rate data from it.

    Returns parsed plan list (may be empty if PDF had no rate data).
    """
    results = []
    try:
        with page.expect_download(timeout=20_000) as dl_info:
            trigger_fn()
        download = dl_info.value
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        download.save_as(tmp_path)
        with open(tmp_path, "rb") as fh:
            pdf_bytes = fh.read()
        os.unlink(tmp_path)
        results = extract_pdf_data_from_bytes(pdf_bytes, row)
    except Exception as exc:
        log.error("PDF_INTERCEPT_ERROR  %s / %s | %s", row["supplier_name"], row["edc_name"], exc)
    return results


# ===========================================================================
# Strategy functions
# Each takes (page, row) and returns (html_content, pdf_records).
#   html_content  — full page HTML string (or None)
#   pdf_records   — list of plan dicts extracted directly from PDFs (may be [])
# ===========================================================================

def _step(label: str, supplier: str, edc: str) -> None:
    """Log a numbered step inside a strategy."""
    log.info("  STEP  [%s]  %s / %s", label, supplier, edc)


def strategy_constellation(page, row) -> tuple[str | None, list]:
    """
    Constellation Energy workflow:
      1. Navigate to the site.
      2. Select the utility from the <select id="utility"> dropdown.
      3. Fill the zip code input.
      4. Click Continue.
      5. Wait for the plan table/rate cards and return HTML.

    Key findings from debug HTML:
      - Utility selector is <select name="Utility" id="utility"> with options
        ['Atlantic City Electric', 'Jersey Central (JCPL)', 'PSEG'].
      - Plans render in a <table> (thead: Plan Name / Length / Rate / Special Offer)
        AND in divs with class 'rateCost'.
      - There is NO 'See All Plans' button needed — selecting the utility and
        clicking Continue is sufficient.
    """
    supplier, edc = row["supplier_name"], row["edc_name"]
    try:
        _step("goto", supplier, edc)
        page.goto(row["website_url"], wait_until="domcontentloaded", timeout=30_000)

        # Map our CSV EDC name to the exact label in the <select> dropdown
        option_label = CONSTELLATION_EDC_MAP.get(edc)
        if not option_label:
            log.warning("  no CONSTELLATION_EDC_MAP entry for %s — trying raw EDC name", edc)
            option_label = re.sub(r"\s+(Electric|Gas)\s*$", "", edc, flags=re.IGNORECASE).strip()

        _step(f"select utility={option_label}", supplier, edc)
        try:
            page.wait_for_selector("select#utility", timeout=15_000)
            page.select_option("select#utility", label=option_label)
            log.debug("  selected utility option: %s", option_label)
        except Exception as sel_exc:
            save_debug_artefacts(page, supplier, edc, "utility_select_failed")
            log.error("  FAIL  could not select utility '%s': %s", option_label, sel_exc)
            return None, []

        _step("fill zip", supplier, edc)
        # The zip input is a React-controlled field (class='zip undefined' when hidden).
        # select_option fires the change event, but React may need a brief tick to update.
        # We wait up to 8s for visibility; if still hidden we force-fill and dispatch
        # synthetic input/change events so React registers the value.
        page.wait_for_timeout(600)  # give React time to process the select_option change
        zip_loc = page.locator('input[name="zip"]')
        try:
            zip_loc.wait_for(state="visible", timeout=8_000)
            zip_loc.fill(str(row["test_zip"]).zfill(5))
        except PlaywrightTimeoutError:
            # React hasn't shown the field yet — force-fill and fire synthetic events
            zip_loc.fill(str(row["test_zip"]).zfill(5), force=True)
            page.evaluate(
                """(val) => {
                    const el = document.querySelector('input[name="zip"]');
                    if (!el) return;
                    const nativeSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(el, val);
                    el.dispatchEvent(new Event('input',  {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                    el.dispatchEvent(new Event('blur',   {bubbles: true}));
                }""",
                str(row["test_zip"]).zfill(5),
            )
            page.wait_for_timeout(800)  # give React time to validate and show Continue
            log.debug("  zip force-filled via React synthetic event")

        _step("click Continue", supplier, edc)
        # The Continue button may still be hidden until React processes the zip value.
        # Give React a brief tick then click with force=True so it fires even if not visible.
        page.wait_for_timeout(500)
        # First try normal click; if button is still hidden (React hasn't un-hid it yet),
        # fall back to JavaScript click which bypasses CSS display:none.
        try:
            page.click(
                'button:has-text("Continue"), button:has-text("See All Plans"), '
                'button:has-text("Submit"), button:has-text("Go")',
                timeout=5_000,
            )
        except PlaywrightTimeoutError:
            log.debug("  Continue button not visible — clicking via JS")
            page.evaluate(
                """() => {
                    const btn = Array.from(document.querySelectorAll('button'))
                        .find(b => /continue|see all plans|submit|go/i.test(b.textContent.trim()));
                    if (btn) btn.click();
                }"""
            )
            page.wait_for_timeout(500)

        # Plans are rendered as divs with data-rate="true" / data-product-plan="true".
        # The site pre-renders plan cards on page load; after the JS click, React may
        # replace them briefly — wait for attached state so we don't need visibility.
        _step("wait for plan results", supplier, edc)
        page.wait_for_selector(
            '[data-rate="true"], [data-product-plan="true"], table tbody tr',
            state="attached",
            timeout=25_000,
        )

        # --- Click each "Plan Details" link to collect Terms & Conditions PDF URLs ---
        # Constellation renders T&C PDF links only inside a per-plan modal that opens
        # when "Plan Details" is clicked.  The modal is shared (single element replaced
        # per click), so we must capture the PDF href after each click.
        _step("collect T&C PDFs via Plan Details modals", supplier, edc)
        contract_rows: list[dict] = []
        seen_contract_urls: set[str] = set()
        plan_detail_links = page.locator('a:has-text("Plan Details")')
        pd_count = plan_detail_links.count()
        log.debug("  found %d 'Plan Details' link(s)", pd_count)
        for i in range(pd_count):
            try:
                plan_detail_links.nth(i).click(force=True)
                page.wait_for_timeout(1_500)  # allow modal to render
                # Find Terms and Conditions PDF link in the open modal
                tc_a = page.query_selector(
                    "a:has-text('Terms and Conditions'), a[href*='tandc'], a[href*='.pdf']"
                )
                if tc_a:
                    tc_url = tc_a.get_attribute("href") or ""
                    if tc_url and tc_url not in seen_contract_urls:
                        seen_contract_urls.add(tc_url)
                        pdf_bytes = download_pdf_from_url(tc_url)
                        if pdf_bytes and pdf_bytes[:4] == b"%PDF":
                            parsed = extract_pdf_data_from_bytes(pdf_bytes, row)
                            for r in parsed:
                                r["data_source"] = "contract_summary_pdf"
                                r["contract_url"] = tc_url
                            contract_rows.extend(parsed)
                            log.debug("  plan %d T&C PDF → %d row(s)", i, len(parsed))
                        else:
                            log.debug("  plan %d T&C URL is not a PDF: %s", i, tc_url[:80])
                # Close modal so next click opens fresh
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(400)
                except Exception:
                    pass
            except Exception as pd_exc:
                log.debug("  'Plan Details' click %d failed: %s", i, pd_exc)

        log.info("  collected %d contract row(s) from Constellation modals", len(contract_rows))
        return page.content(), contract_rows

    except Exception as exc:
        save_debug_artefacts(page, supplier, edc, "error")
        log.error("constellation | %s / %s | %s", supplier, edc, exc)
        return None, []


def strategy_direct_energy(page, row) -> tuple[str | None, list]:
    """
    Direct Energy workflow:

    Key findings from debug HTML:
      - Zip input: <input id="txtZipCode" name="zipCode" class="input-with-left-icon">
      - A location popup modal (#location-popupmodal) appears on load and must
        be dismissed BEFORE filling the zip input.
      - After 'Shop now' click the page navigates to /new-jersey/plans/?
        and plan cards are in elements with class 'planlookup'.
      - 'View More Plans' button may appear to load additional plans.
    """
    supplier, edc = row["supplier_name"], row["edc_name"]
    try:
        _step("goto", supplier, edc)
        page.goto(row["website_url"], wait_until="domcontentloaded", timeout=30_000)

        # --- Dismiss location popup and cookie banners ---
        _step("dismiss overlays", supplier, edc)
        for dismiss_sel in [
            '#location-popupmodal .close',
            '#location-popupmodal button.close',
            '[aria-label="Close"]',
            'button:has-text("No Thanks")',
            'button:has-text("Accept")',
            'button:has-text("Close")',
        ]:
            try:
                btn = page.query_selector(dismiss_sel)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(600)
                    log.debug("  dismissed overlay: %s", dismiss_sel)
                    break
            except Exception:
                pass
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception:
            pass

        # --- Fill zip using the known input ID ---
        _step("fill zip (#txtZipCode)", supplier, edc)
        page.wait_for_selector("#txtZipCode", timeout=15_000)
        page.fill("#txtZipCode", str(row["test_zip"]).zfill(5))

        # --- Click the shop button (various labels used across pages) ---
        _step("click Shop/Shop now", supplier, edc)
        for btn_sel in [
            'button:has-text("Shop Plans")',
            'button:has-text("Shop now")',
            'button:has-text("Shop Now")',
            'button[type="submit"]',
        ]:
            try:
                page.click(btn_sel, timeout=6_000, force=True)
                log.debug("  clicked shop button: %s", btn_sel)
                break
            except PlaywrightTimeoutError:
                continue

        # networkidle is unreliable on directenergy.com; fall back to 'load'
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except PlaywrightTimeoutError:
            page.wait_for_load_state("load", timeout=10_000)

        # --- Click 'View More Plans' if present ---
        _step("click View More Plans (optional)", supplier, edc)
        try:
            # Use locator (not ElementHandle) so it re-queries after navigation and avoids stale element errors
            view_more_loc = page.locator(
                'button:has-text("View More Plans"), a:has-text("View More Plans")'
            ).first
            view_more_loc.wait_for(timeout=8_000)
            view_more_loc.click()
            page.wait_for_load_state("networkidle", timeout=15_000)
        except PlaywrightTimeoutError:
            log.debug("  'View More Plans' not present (ok)")

        # --- Wait for plan listing (.product-card / .plan__wrapper is the Direct Energy plan container) ---
        # NOTE: .planlookup was removed from HTML element classes on the current site;
        # it only exists in CSS rules now.  The actual plan divs have class 'product-card'.
        _step("wait for plan cards", supplier, edc)
        try:
            page.wait_for_selector(
                '.product-card, [class*="product-id-"], .plan__wrapper, .planlookup',
                timeout=20_000,
            )
        except PlaywrightTimeoutError:
            # Fallback: take whatever's on the page — parser will find what it can
            save_debug_artefacts(page, supplier, edc, "no_planlookup")
            log.warning("  .product-card not found — returning page as-is")

        # --- Click each 'Learn more' button, collect Contract Summary PDF URLs ---
        # The modal is shared (single element whose content changes per plan), so we must
        # capture the Contract Summary href after each click rather than reading the final DOM.
        _step("collect contract PDFs via Learn more modals", supplier, edc)
        contract_rows: list[dict] = []
        seen_contract_urls: set[str] = set()
        learn_btns = page.locator('button:has-text("Learn more"), button:has-text("Learn More")')
        btn_count = learn_btns.count()
        log.debug("  found %d 'Learn more' button(s)", btn_count)
        for i in range(btn_count):
            try:
                learn_btns.nth(i).click(force=True)
                page.wait_for_timeout(1_500)  # wait for modal JS to populate
                # Grab Contract Summary href from the open modal
                contract_a = page.query_selector("a:has-text('Contract Summary')")
                if contract_a:
                    contract_url = contract_a.get_attribute("href") or ""
                    if contract_url and contract_url not in seen_contract_urls:
                        seen_contract_urls.add(contract_url)
                        pdf_bytes = download_pdf_from_url(contract_url)
                        if pdf_bytes and pdf_bytes[:4] == b"%PDF":
                            parsed = extract_pdf_data_from_bytes(pdf_bytes, row)
                            for r in parsed:
                                r["data_source"] = "contract_summary_pdf"
                                r["contract_url"] = contract_url
                            contract_rows.extend(parsed)
                            log.debug("  plan %d contract PDF → %d row(s)", i, len(parsed))
                        else:
                            log.debug("  plan %d contract URL is not a PDF: %s", i, contract_url[:80])
                # Close modal so next click opens fresh
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(400)
                except Exception:
                    pass
            except Exception as btn_exc:
                log.debug("  'Learn more' click %d failed: %s", i, btn_exc)

        log.info("  collected %d contract row(s) from DE modals", len(contract_rows))
        return page.content(), contract_rows

    except Exception as exc:
        save_debug_artefacts(page, supplier, edc, "error")
        log.error("direct_energy | %s / %s | %s", supplier, edc, exc)
        return None, []


def strategy_ambit(page, row) -> tuple[str | None, list]:
    """
    Ambit Energy workflow:

    Key findings from debug HTML:
      - Zip input: <input name="ZipCode" id="ZipCode">
      - After filling zip, click <input type="button" id="nextButton"> to advance.
      - Customer type buttons are <button class="btn btn-enrollment ambitRadio ...">
        with text 'Residential' / 'Commercial'.
      - Dwelling type buttons appear after Residential click (House / Apt).
      - Utility provider buttons appear after dwelling selection.

    IMPORTANT: 'text=Residential' is a Playwright-specific selector, NOT valid CSS.
    Mixing it with CSS selectors in a single comma-separated string causes a
    parse error. Each selector must be tried separately.
    """
    supplier, edc = row["supplier_name"], row["edc_name"]
    try:
        _step("goto", supplier, edc)
        page.goto(row["website_url"], wait_until="domcontentloaded", timeout=30_000)

        _step("fill zip (#ZipCode)", supplier, edc)
        page.wait_for_selector("#ZipCode", timeout=15_000)
        page.fill("#ZipCode", str(row["test_zip"]).zfill(5))

        _step("click Next (#nextButton)", supplier, edc)
        page.wait_for_selector("#nextButton", timeout=8_000)
        page.click("#nextButton")
        page.wait_for_timeout(800)

        # --- Click Residential (each selector tried separately to avoid CSS parse error) ---
        _step("click Residential", supplier, edc)
        residential_clicked = False
        for sel in [
            "button.ambitRadio:has-text('Residential')",
            "button:has-text('Residential')",
            "label:has-text('Residential')",
        ]:
            try:
                page.wait_for_selector(sel, timeout=8_000)
                page.click(sel)
                residential_clicked = True
                log.debug("  clicked Residential with: %s", sel)
                page.wait_for_timeout(500)
                break
            except PlaywrightTimeoutError:
                continue
        if not residential_clicked:
            save_debug_artefacts(page, supplier, edc, "residential_not_found")
            log.error("  FAIL  Residential button not found")
            return None, []

        # --- Click House ---
        _step("click House", supplier, edc)
        house_clicked = False
        for sel in [
            "button.ambitRadio:has-text('House')",
            "button:has-text('House')",
            "label:has-text('House')",
        ]:
            try:
                page.wait_for_selector(sel, timeout=8_000)
                page.click(sel)
                house_clicked = True
                log.debug("  clicked House with: %s", sel)
                page.wait_for_timeout(500)
                break
            except PlaywrightTimeoutError:
                continue
        if not house_clicked:
            save_debug_artefacts(page, supplier, edc, "house_not_found")
            log.error("  FAIL  House button not found")
            return None, []

        # --- Click Next again to advance from dwelling-type step to utility step ---
        _step("click Next (after dwelling type)", supplier, edc)
        try:
            page.wait_for_selector("#nextButton", timeout=5_000)
            page.click("#nextButton")
            page.wait_for_timeout(1_500)
        except PlaywrightTimeoutError:
            pass  # may not be needed on all zip codes

        # --- Select the utility provider ---
        _step(f"click utility={edc}", supplier, edc)
        edc_short = re.sub(r"\s+(Electric|Gas)\s*$", "", edc, flags=re.IGNORECASE).strip()
        util_clicked = False
        # Ambit uses <span class="list-group-item"> for utility options, not buttons.
        # Text may include suffix e.g. "PSE&G Utility" so use partial has-text match.
        for sel in [
            f"span.list-group-item:has-text('{edc_short}')",
            f"button:has-text('{edc_short}')",
            f"label:has-text('{edc_short}')",
            f"img[alt*='{edc_short}']",
        ]:
            try:
                page.wait_for_selector(sel, timeout=8_000)
                page.click(sel)
                util_clicked = True
                log.debug("  clicked utility with: %s", sel)
                break
            except PlaywrightTimeoutError:
                continue
        if not util_clicked:
            save_debug_artefacts(page, supplier, edc, "utility_not_found")
            log.error("  FAIL  utility button not found for %s", edc_short)
            return None, []

        # --- After selecting utility, submit the provider form to load plan offers ---
        # Ambit's AngularJS SPA requires a #nextButton click to transition from the
        # provider-selection view to the plan-offers view. Without this, page.content()
        # returns the utility-selection form (no prices).
        page.wait_for_timeout(600)
        try:
            page.wait_for_selector("#nextButton", timeout=5_000)
            page.click("#nextButton")
            log.debug("  clicked Next to submit provider selection")
        except PlaywrightTimeoutError:
            log.debug("  #nextButton not found after utility click — continuing")

        # --- Wait until plan prices appear in the rendered page text ---
        # Using wait_for_function avoids dependency on obfuscated AngularJS class names.
        _step("wait for offer cards", supplier, edc)
        try:
            page.wait_for_function(
                r"() => /\d+\.\d+\s*[¢¢\u00a2]|\d+\.\d+.*?per\s*kWh/i.test(document.body.innerText)",
                timeout=20_000,
            )
            log.debug("  plan prices detected in page text")
        except PlaywrightTimeoutError:
            save_debug_artefacts(page, supplier, edc, "no_plan_prices")
            log.warning("  no plan prices found after provider submit — returning HTML for inspection")

        # --- Click each "View Plan Info" link, parse each popup inline, then close ---
        # The ngDialog popup is replaced on each click, so we must extract plan data
        # from each dialog before moving to the next one.  Returning pdf_rows directly
        # bypasses the generic parser (which can't see closed dialogs).
        _step("click View Plan Info (each plan)", supplier, edc)
        plan_rows: list[dict] = []
        try:
            view_plan_sel = "a:has-text('View Plan Info'), a.ng-binding:has-text('View Plan Info')"
            page.wait_for_selector(view_plan_sel, timeout=8_000)
            view_links = page.locator(view_plan_sel)
            count = view_links.count()
            log.debug("  found %d 'View Plan Info' link(s)", count)

            for i in range(count):
                try:
                    # Re-query links fresh each iteration: AngularJS may re-render
                    # plan cards after a dialog closes, making stale locators detach.
                    fresh_links = page.locator(view_plan_sel)
                    if i >= fresh_links.count():
                        log.debug("  only %d links visible at iteration %d — stopping",
                                  fresh_links.count(), i)
                        break
                    fresh_links.nth(i).click(force=True)
                    # Wait for the ngDialog to open
                    page.wait_for_selector(".ngdialog-content", timeout=5_000)
                    page.wait_for_timeout(300)

                    # Save debug artefact on first popup only
                    if i == 0:
                        save_debug_artefacts(page, supplier, edc, "first_popup")

                    # Parse dialog HTML inline
                    dialog_html = page.locator(".ngdialog-content").first.inner_html()
                    ds = BeautifulSoup(dialog_html, "lxml")
                    dialog_text = ds.get_text(separator=" ", strip=True)

                    # Plan name from the h5 header
                    h5 = ds.find("h5", class_="ng-binding")
                    plan_name = h5.get_text(strip=True) if h5 else "N/A"

                    # Rate using the shared normalise + pattern helpers
                    norm_text = _normalize_dollar_rates(dialog_text)
                    price_m = _PRICE_PATTERN.search(norm_text) or _CENT_PATTERN.search(norm_text)
                    rate = price_m.group(1) if price_m else "N/A"

                    # Term from "N Months" text (dt/dd pair for "Term:")
                    term_m = _TERM_PATTERN.search(dialog_text)
                    term = term_m.group(1) if term_m else "0"

                    # Plan type (Fixed / Variable / Indexed)
                    type_m = _TYPE_PATTERN.search(dialog_text)
                    plan_type = type_m.group(1).capitalize() if type_m else "Fixed"

                    plan_rows.append({
                        "supplier":    supplier,
                        "edc_name":    edc,
                        "commodity":   row["commodity"],
                        "plan_name":   plan_name,
                        "rate":        rate,
                        "term_months": term,
                        "plan_type":   plan_type,
                        "source_url":  row["website_url"],
                        "data_source": "html_popup",
                        "contract_url": "",
                    })
                    log.debug("  popup %d: plan=%s  rate=%s  term=%s mo",
                              i, plan_name, rate, term)

                    # Close dialog and wait for it to fully disappear before continuing
                    page.keyboard.press("Escape")
                    try:
                        page.wait_for_selector(".ngdialog-content",
                                               state="hidden", timeout=3_000)
                    except PlaywrightTimeoutError:
                        page.wait_for_timeout(600)

                except Exception as exc:
                    log.debug("  popup %d failed: %s", i, exc)

        except PlaywrightTimeoutError:
            log.debug("  'View Plan Info' links not found — no plan rows captured")

        return None, plan_rows

    except Exception as exc:
        save_debug_artefacts(page, supplier, edc, "error")
        log.error("ambit | %s / %s | %s", supplier, edc, exc)
        return None, []


def strategy_think_energy(page, row) -> tuple[str | None, list]:
    """
    Think Energy workflow:

    Key findings from debug HTML:
      - A CookieYes consent banner (div.cky-overlay) blocks all clicks.
        Must accept it BEFORE filling the zip form.
      - Zip input: <input name="input_2" id="input_1_2" placeholder="Zip Code">
      - Submit: <input type="submit" id="gform_submit_button_1" value="View Offers">
        (This is an <input type="submit">, not a <button>.)
      - After submission the page navigates to a results page with offer rows
        carrying class 'thinkenergy-plus-header' / 'thinkenergy-header-row'.
    """
    supplier, edc = row["supplier_name"], row["edc_name"]
    try:
        _step("goto", supplier, edc)
        page.goto(row["website_url"], wait_until="domcontentloaded", timeout=30_000)

        # --- Dismiss CookieYes banner (div.cky-overlay blocks all other clicks) ---
        _step("accept cookie consent", supplier, edc)
        for cookie_sel in [
            "button.cky-btn-accept",
            "button.cky-btn-reject",
            ".cky-consent-bar button",
        ]:
            try:
                btn = page.wait_for_selector(cookie_sel, timeout=6_000)
                btn.click()
                page.wait_for_timeout(600)
                log.debug("  dismissed cookie banner: %s", cookie_sel)
                break
            except PlaywrightTimeoutError:
                continue

        # --- Fill zip using the known input ID ---
        _step("fill zip (#input_1_2)", supplier, edc)
        page.wait_for_selector("#input_1_2", timeout=12_000)
        page.fill("#input_1_2", str(row["test_zip"]).zfill(5))

        # --- Click the submit input (NOT a <button>) ---
        _step("click View Offers (#gform_submit_button_1)", supplier, edc)
        page.wait_for_selector("#gform_submit_button_1", timeout=8_000)
        page.click("#gform_submit_button_1")
        # networkidle never fires on thinkenergy.com due to background polling;
        # both domcontentloaded and load fire successfully — use load instead.
        page.wait_for_load_state("load", timeout=15_000)

        # --- Wait for Think Energy offer rows ---
        _step("wait for offer rows", supplier, edc)
        try:
            page.wait_for_selector(
                ".thinkenergy-plus-header, .thinkenergy-header-row, "
                "[class*='thinkenergy'], [class*='offer'], [class*='plan']",
                timeout=15_000,
            )
        except PlaywrightTimeoutError:
            save_debug_artefacts(page, supplier, edc, "no_offer_rows")
            log.warning("  no offer rows found after View Offers")

        # --- Expand all 'View Details +' accordion sections ---
        _step("expand View Details accordions", supplier, edc)
        details_buttons = page.query_selector_all(
            "button:has-text('View Details'), a:has-text('View Details'), "
            "button:has-text('Details +'), a:has-text('Details +')"
        )
        log.debug("  found %d detail-expand buttons", len(details_buttons))
        for btn in details_buttons:
            try:
                if btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(400)
            except Exception:
                pass

        return page.content(), []

    except Exception as exc:
        save_debug_artefacts(page, supplier, edc, "error")
        log.error("think_energy | %s / %s | %s", supplier, edc, exc)
        return None, []


def strategy_nrg(page, row) -> tuple[str | None, list]:
    """
    NRG / PickNRG workflow (picknrg.com):

    Key findings from debug HTML:
      - There is a state <select> that must be set to 'New Jersey' first.
      - Zip input: <input type="tel" name="zip" id="zip" placeholder="Enter zip code">
      - Submit button text: 'Shop now' (class 'continuebutton headerDsktpShopNowBtn')
    """
    supplier, edc = row["supplier_name"], row["edc_name"]
    try:
        _step("goto", supplier, edc)
        page.goto(row["website_url"], wait_until="domcontentloaded", timeout=30_000)

        # --- Dismiss OneTrust cookie banner if present ---
        try:
            page.click(".onetrust-close-btn-handler", timeout=5_000)
            page.wait_for_timeout(400)
        except PlaywrightTimeoutError:
            pass

        # --- Select New Jersey from the custom nice-select dropdown ---
        # The native <select> is hidden (display:none); click the styled div UI instead.
        _step("select state New Jersey", supplier, edc)
        try:
            page.wait_for_selector("div.nice-select.niceselect", timeout=8_000)
            page.click("div.nice-select.niceselect", timeout=5_000)       # open dropdown
            page.wait_for_timeout(400)
            page.click(
                "div.nice-select.niceselect ul.list li.option:has-text('New Jersey')",
                timeout=5_000,
            )
            # selectState() navigates to the NJ state page — wait for it
            page.wait_for_load_state("load", timeout=20_000)
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except PlaywrightTimeoutError:
                pass
            log.debug("  selected New Jersey via nice-select UI")
        except Exception as e:
            log.warning("  could not select state: %s", e)

        # --- Fill zip using the known input id ---
        # Use JS to set the value and dispatch input/change events so that
        # setBannerZipCode() reads the correct value (page.fill() alone may not
        # trigger the event listener that the NRG JS reads before navigating).
        _step("fill zip (#zip)", supplier, edc)
        page.wait_for_selector("#zip", timeout=10_000)
        zip_val = str(row["test_zip"]).zfill(5)
        page.evaluate(
            """zip => {
                var inp = document.getElementById('zip');
                inp.value = zip;
                inp.dispatchEvent(new Event('input',  {bubbles: true}));
                inp.dispatchEvent(new Event('change', {bubbles: true}));
            }""",
            zip_val,
        )
        # Triple-click (select-all) + type as belt-and-suspenders so the value is definitely set
        page.click("#zip", click_count=3)
        page.keyboard.type(zip_val)
        log.debug("  filled zip: %s", zip_val)

        # --- Click 'Shop now' and wait for navigation to plans page ---
        _step("click Shop now", supplier, edc)
        clicked = False
        for btn_sel in [
            "button.zipCodeParam",                   # banner form submit (tied to #zip)
            "button.primaryYellowButton",            # same button, alternate selector
            "button:has-text('Shop plans')",         # alternate text used on some pages
            "button:has-text('Shop now'):not(.headerDsktpShopNowBtn)",
        ]:
            try:
                # setBannerZipCode() navigates to a plans URL — use expect_navigation
                # so we don't proceed until the page transition is complete.
                try:
                    with page.expect_navigation(timeout=20_000):
                        page.click(btn_sel, timeout=6_000)
                except Exception:
                    # Navigation may not be detected on some page variants; still try
                    pass
                log.debug("  clicked shop button: %s", btn_sel)
                clicked = True
                break
            except PlaywrightTimeoutError:
                continue

        if clicked:
            page.wait_for_load_state("domcontentloaded", timeout=20_000)
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except PlaywrightTimeoutError:
                pass
            page.wait_for_timeout(2_000)

        # --- Handle commodity/utility modals when NRG requires additional choices ---
        # Some ZIPs (including 07102) open a commodity modal, then a utility modal,
        # before offers are shown. If we don't complete this flow, no plan cards render.
        try:
            commodity = str(row.get("commodity", "electric")).lower()

            # Give modal scripts time to attach and render dynamic content.
            try:
                page.wait_for_selector(
                    "#commodityModalWindow, #modalWindow, #goToutilityModal, #goToProductChart",
                    timeout=8_000,
                )
            except Exception:
                pass

            # Step 1: commodity modal (electric vs gas)
            commodity_modal = page.locator("#commodityModalWindow")
            if commodity_modal.count():
                _step("handle commodity modal", supplier, edc)
                commodity_checkbox = "#elecCheckBox" if commodity != "gas" else "#gasCheckBox"
                try:
                    page.click(commodity_checkbox, timeout=5_000, force=True)
                except Exception:
                    # Fallback: set checkbox directly when modal animation/layout makes
                    # labels non-clickable in headless mode.
                    page.evaluate(
                        """sel => {
                            const cb = document.querySelector(sel);
                            if (cb) {
                                cb.checked = true;
                                cb.dispatchEvent(new Event('input', { bubbles: true }));
                                cb.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            const btn = document.querySelector('#goToutilityModal');
                            if (btn) btn.disabled = false;
                        }""",
                        commodity_checkbox,
                    )

                page.wait_for_timeout(300)
                try:
                    page.click("#goToutilityModal", timeout=7_000, force=True)
                    page.wait_for_timeout(1_000)
                except Exception:
                    try:
                        page.evaluate(
                            """() => {
                                const btn = document.querySelector('#goToutilityModal');
                                if (btn) {
                                    btn.disabled = false;
                                    btn.click();
                                }
                            }"""
                        )
                        page.wait_for_timeout(1_000)
                    except Exception:
                        pass

            # Step 2: utility modal (choose PSE&G electric)
            utility_modal = page.locator("#modalWindow")
            if utility_modal.count():
                _step("handle utility modal", supplier, edc)
                for util_sel in [
                    "#modalWindow #showelectric label:has-text('PSE&G')",
                    "#modalWindow #showelectric div:has-text('PSE&G')",
                    "#modalWindow label:has-text('PSE&G')",
                    "#modalWindow div:has-text('PSE&G')",
                ]:
                    try:
                        if page.locator(util_sel).count():
                            page.locator(util_sel).first.click(timeout=4_000, force=True)
                            break
                    except Exception:
                        continue

                try:
                    page.wait_for_function(
                        "() => { const b = document.querySelector('#goToProductChart'); return b && !b.disabled; }",
                        timeout=7_000,
                    )
                except Exception:
                    pass

                try:
                    page.click("#goToProductChart", timeout=8_000, force=True)
                except Exception:
                    page.evaluate(
                        """() => {
                            const btn = document.querySelector('#goToProductChart');
                            if (btn) {
                                btn.disabled = false;
                                btn.click();
                            }
                        }"""
                    )
                page.wait_for_load_state("domcontentloaded", timeout=20_000)
                try:
                    page.wait_for_load_state("networkidle", timeout=10_000)
                except PlaywrightTimeoutError:
                    pass
                page.wait_for_timeout(1_500)
        except Exception as modal_exc:
            log.debug("  nrg modal flow skipped/failed: %s", modal_exc)

        _step("wait for plan results", supplier, edc)
        try:
            page.wait_for_selector(
                ".product-card, .imgCardLink, [class*='product-card'], "
                "[class*='imgCard'], [class*='plan-card'], [class*='offer-card'], "
                "[class*='planCard'], .rateCard, .tier-card",
                timeout=15_000,
            )
        except PlaywrightTimeoutError:
            save_debug_artefacts(page, supplier, edc, "ZERO_PLANS")
            log.warning("  no plan cards visible after Shop now")

        return page.content(), []

    except Exception as exc:
        save_debug_artefacts(page, supplier, edc, "error")
        log.error("nrg | %s / %s | %s", supplier, edc, exc)
        return None, []


# Map our CSV edc_name → (text fragment to match on Major Energy's page, commodity keyword)
MAJOR_EDC_MAP: dict[str, tuple[str, str]] = {
    "PSE&G Electric":    ("Public Service", "electric"),
    "PSE&G Gas":         ("Public Service", "gas"),
    "ACE Electric":      ("Atlantic City",  "electric"),
    "JCP&L Electric":    ("Jersey Central",  "electric"),
    "SJG Gas":           ("South Jersey Gas", "gas"),
    "ETG Gas":           ("Elizabethtown",   "gas"),
    "NJNG Gas":          ("New Jersey Natural", "gas"),
}


def strategy_major_energy(page, row) -> tuple[str | None, list]:
    """
    Major Energy signup flow (signup.majorenergy.com).

    The enrollment site accepts a zipcode query parameter and immediately shows
    a utility-selection page.  Each utility is a plain <a> link.  For PSE&G
    territory the same company name appears twice (electric row and gas row),
    so we disambiguate using row["commodity"].
    """
    supplier, edc = row["supplier_name"], row["edc_name"]
    zip_code = str(row["test_zip"]).zfill(5)
    commodity = str(row.get("commodity", "electric")).lower()

    try:
        signup_url = f"https://signup.majorenergy.com/?zipcode={zip_code}"
        _step("goto signup page", supplier, edc)
        page.goto(signup_url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_load_state("load", timeout=15_000)

        # --- Find all utility selection links ---
        _step("select utility", supplier, edc)
        try:
            page.wait_for_selector("a[href*='SelectUtility']", timeout=15_000)
        except PlaywrightTimeoutError:
            save_debug_artefacts(page, supplier, edc, "no_utility_links")
            log.warning("  no utility links found on Major Energy signup page")
            return page.content(), []

        edc_hint = MAJOR_EDC_MAP.get(edc)
        name_frag = edc_hint[0] if edc_hint else edc.split()[0]

        # Collect all matching links; for ambiguous cases (PSE&G appears twice),
        # prefer the one closest to a commodity keyword in the surrounding text.
        links = page.locator(f"a[href*='SelectUtility']:has-text('{name_frag}')")
        count = links.count()
        log.debug("  found %d utility link(s) matching '%s'", count, name_frag)

        chosen = None
        if count == 1:
            chosen = links.nth(0)
        elif count > 1:
            # Try to find the link whose surrounding context mentions the commodity
            for i in range(count):
                lnk = links.nth(i)
                # Check parent container text for commodity keyword
                parent_text = lnk.evaluate("el => el.closest('li,div,td,tr') ? el.closest('li,div,td,tr').innerText : ''")
                if commodity in parent_text.lower():
                    chosen = lnk
                    log.debug("  disambiguated by commodity '%s' at index %d", commodity, i)
                    break
            if chosen is None:
                # Default to first match
                chosen = links.nth(0)
                log.debug("  could not disambiguate — using first match")

        if chosen is None:
            save_debug_artefacts(page, supplier, edc, "utility_not_matched")
            log.error("  FAIL  no utility link matched for %s", edc)
            return None, []

        chosen.click()
        page.wait_for_load_state("load", timeout=20_000)
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except PlaywrightTimeoutError:
            pass

        # --- Wait for plan cards / offer containers ---
        _step("wait for plan offers", supplier, edc)
        try:
            page.wait_for_selector(
                "[class*='plan'], [class*='offer'], [class*='rate'], [class*='product'], "
                "table tbody tr",
                timeout=15_000,
            )
        except PlaywrightTimeoutError:
            save_debug_artefacts(page, supplier, edc, "no_plan_cards")
            log.warning("  no plan cards found after utility selection")

        return page.content(), []

    except Exception as exc:
        save_debug_artefacts(page, supplier, edc, "error")
        log.error("major_energy | %s / %s | %s", supplier, edc, exc)
        return None, []


def strategy_xoom_energy(page, row) -> tuple[str | None, list]:
    """
    Xoom Energy NJ shopping flow (xoomenergy.com).

    User-documented flow:
      1. Enter zip and press Go
      2. Click the bar for the electric or gas company
      3. Popup: radio buttons for electric utility AND gas utility
         (must select one in each section to enable Continue, but can opt out)
      4. Press Continue → offers page
      5. Click Details dropdown → Contract Summary

    The popup requires a selection in BOTH utility sections.  For the
    commodity we're NOT shopping for, we click the "I don't want [commodity]
    offers" / "skip" option if present, otherwise pick any radio button.
    """
    supplier, edc = row["supplier_name"], row["edc_name"]
    zip_code  = str(row["test_zip"]).zfill(5)
    commodity = str(row.get("commodity", "electric")).lower()

    try:
        _step("goto", supplier, edc)
        page.goto(row["website_url"], wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_load_state("load", timeout=20_000)

        # --- Fill zip and submit ---
        _step("fill zip and Go", supplier, edc)
        zip_sel = (
            'input[placeholder*="zip" i], input[name*="zip" i], '
            'input[id*="zip" i], input[type="tel"][maxlength="5"]'
        )
        try:
            page.wait_for_selector(zip_sel, timeout=15_000)
            page.fill(zip_sel, zip_code)
        except PlaywrightTimeoutError:
            save_debug_artefacts(page, supplier, edc, "no_zip_input")
            log.warning("  no zip input found on Xoom page")
            return page.content(), []

        go_sel = (
            'button:has-text("Go"), button:has-text("Shop"), '
            'button:has-text("See Plans"), button:has-text("Get Started"), '
            'input[type="submit"]'
        )
        try:
            page.click(go_sel, timeout=8_000)
        except PlaywrightTimeoutError:
            # Try pressing Enter in the zip field
            page.locator(zip_sel).press("Enter")

        page.wait_for_load_state("load", timeout=20_000)
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except PlaywrightTimeoutError:
            pass

        # --- Click the utility/company bar for our commodity ---
        _step("click utility bar", supplier, edc)
        # Xoom shows bars for each electric/gas company by name.
        # Try clicking a bar that contains a keyword from the edc name.
        edc_keyword = edc.replace(" Electric", "").replace(" Gas", "").strip()
        bar_sel = (
            f"[class*='bar']:has-text('{edc_keyword}'), "
            f"[class*='tile']:has-text('{edc_keyword}'), "
            f"[class*='card']:has-text('{edc_keyword}'), "
            f"[class*='utility']:has-text('{edc_keyword}'), "
            f"button:has-text('{edc_keyword}'), "
            f"a:has-text('{edc_keyword}')"
        )
        try:
            page.wait_for_selector(bar_sel, timeout=10_000)
            page.click(bar_sel)
            page.wait_for_timeout(1_000)
            log.debug("  clicked utility bar for '%s'", edc_keyword)
        except PlaywrightTimeoutError:
            save_debug_artefacts(page, supplier, edc, "no_utility_bar")
            log.warning("  utility bar not found — saving debug artefacts")
            return page.content(), []

        # --- Handle popup: select radio buttons for both electric and gas ---
        _step("handle utility popup", supplier, edc)
        # Xoom uses ASP.NET WebForms "prettyradio" — real <input type="radio"> is
        # display:none; the visible clickable element is <a role="radio">.
        # Two separate tables exist: one for electric utility, one for gas.
        # First option in each table = the actual utility; last = "not interested".
        ELEC_TABLE = "#cpTopMain_cpMain_ucDualMarketModal_rblElectricChoice"
        GAS_TABLE  = "#cpTopMain_cpMain_ucDualMarketModal_rblGasChoice"
        try:
            # Wait for the modal popup div (not the hidden input)
            page.wait_for_selector(
                "#cpTopMain_cpMain_ucDualMarketModal_pnlDualEnrollment, "
                "[class*='dual-market-modal']",
                timeout=10_000,
            )
            if commodity == "electric":
                # Select our utility in the electric table
                page.locator(f"{ELEC_TABLE} a[role='radio']").first.click()
                page.wait_for_timeout(300)
                # Opt out of gas
                page.locator(f"{GAS_TABLE} a[role='radio']").last.click()
            else:
                # Opt out of electric
                page.locator(f"{ELEC_TABLE} a[role='radio']").last.click()
                page.wait_for_timeout(300)
                # Select our utility in the gas table
                page.locator(f"{GAS_TABLE} a[role='radio']").first.click()

            page.wait_for_timeout(400)
            # Use expect_navigation so we wait for the ASP.NET form postback to
            # fully replace the page before reading content.
            try:
                with page.expect_navigation(timeout=30_000):
                    page.click("#cpTopMain_cpMain_ucDualMarketModal_btnContinue", timeout=8_000)
            except Exception as nav_e:
                log.warning("  popup Continue nav error (may be same-page postback): %s", nav_e)
                # Still try to click even if navigation detection failed
                try:
                    page.click("#cpTopMain_cpMain_ucDualMarketModal_btnContinue", timeout=5_000)
                except Exception:
                    pass
            page.wait_for_load_state("domcontentloaded", timeout=20_000)
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except PlaywrightTimeoutError:
                pass
            # Give ASP.NET time to finish rendering offers
            page.wait_for_timeout(3_000)
            log.debug("  handled Xoom dual-market popup OK")

        except PlaywrightTimeoutError:
            save_debug_artefacts(page, supplier, edc, "no_popup_modal")
            log.warning("  popup modal not found — continuing with current page")

        # --- Wait for offer cards ---
        # Xoom renders plans in div.myRateData elements (one per plan).
        # Do NOT use [class*='plan'] here — .search-plan-container exists on the
        # utility selection page and would fire too early.
        _step("wait for offers", supplier, edc)
        try:
            page.wait_for_selector(
                ".myRateData, .utility-choice-row, [class*='plan-category']",
                timeout=20_000,
            )
        except PlaywrightTimeoutError:
            # Plans may still be in the DOM — try JS poll as a last resort
            try:
                page.wait_for_function(
                    "() => document.querySelectorAll('.myRateData').length > 0",
                    timeout=10_000,
                )
            except Exception:
                # Save always so we can inspect what the offers page looks like
                save_debug_artefacts(page, supplier, edc, "xoom_after_continue")
                log.warning("  no Xoom offer cards found; debug saved for inspection")

        return page.content(), []

    except Exception as exc:
        save_debug_artefacts(page, supplier, edc, "error")
        log.error("xoom_energy | %s / %s | %s", supplier, edc, exc)
        return None, []


def strategy_default(page, row) -> tuple[str | None, list]:
    supplier, edc = row["supplier_name"], row["edc_name"]
    try:
        _step("goto", supplier, edc)
        page.goto(row["website_url"], wait_until="domcontentloaded", timeout=30_000)

        # Broader zip input selector set
        zip_sel = (
            'input[placeholder*="zip" i], input[name*="zip" i], '
            'input[id*="zip" i], input[placeholder*="postal" i], '
            'input[type="text"][maxlength="5"], input[autocomplete="postal-code"]'
        )
        _step("find zip input", supplier, edc)

        zip_found = False
        try:
            page.wait_for_selector(zip_sel, timeout=15_000)
            zip_found = True
        except PlaywrightTimeoutError:
            save_debug_artefacts(page, supplier, edc, "no_zip_input")
            log.warning("  no zip input found — returning raw page HTML")
            return page.content(), []   # return whatever loaded; parser may still find data

        if zip_found:
            page.fill(zip_sel, str(row["test_zip"]))

        submit_sel = (
            'button:has-text("View Rates"), button:has-text("See Plans"), '
            'button:has-text("Shop Plans"), button:has-text("Get Started"), '
            'button:has-text("Shop Now"), button:has-text("Go"), '
            'button:has-text("Submit"), button:has-text("Continue"), '
            'button:has-text("Search"), button:has-text("Find Plans"), '
            'input[type="submit"]'
        )
        _step("click submit", supplier, edc)
        try:
            page.click(submit_sel, timeout=8_000)
            page.wait_for_load_state("networkidle", timeout=20_000)
        except PlaywrightTimeoutError:
            save_debug_artefacts(page, supplier, edc, "no_submit_btn")
            log.warning("  no submit button found — returning page as-is")

        return page.content(), []

    except Exception as exc:
        save_debug_artefacts(page, supplier, edc, "error")
        log.error("default | %s / %s | %s", supplier, edc, exc)
        return None, []


# ===========================================================================
# Parsers
# ===========================================================================

def _parse_text_block(text: str, row, source: str = "html") -> list[dict]:
    """
    Core extraction logic shared by HTML and PDF parsers.
    Returns a list of plan dicts.
    """
    results = []
    text = _normalize_dollar_rates(text)
    price_match = _PRICE_PATTERN.search(text) or _CENT_PATTERN.search(text)
    if not price_match:
        return results

    # Collect all prices found in this block
    all_prices = _PRICE_PATTERN.findall(text) or _CENT_PATTERN.findall(text)
    seen: set[str] = set()

    for price in all_prices:
        if price in seen:
            continue
        seen.add(price)

        term_match = _TERM_PATTERN.search(text)
        type_match = _TYPE_PATTERN.search(text)

        results.append({
            "supplier":    row["supplier_name"],
            "edc_name":    row["edc_name"],
            "commodity":   row["commodity"],
            "plan_name":   "N/A",
            "rate":        price,
            "term_months": term_match.group(1) if term_match else "N/A",
            "plan_type":   type_match.group(1).capitalize() if type_match else "N/A",
            "source_url":  row["website_url"],
            "data_source": source,
        })

    return results


_TERM_MO_PATTERN = re.compile(r"(\d{1,3})\s*mo\.?", re.IGNORECASE)


def _parse_constellation_divs(soup: BeautifulSoup, row) -> list[dict]:
    """
    Constellation (current live site) renders plan cards as divs with
    data-single="true" data-planid="..." data-term="N" attributes.
    Each card contains [data-rate="true"] and [data-product-plan="true"] children.
    """
    results = []
    seen: set[str] = set()
    cards = soup.find_all(attrs={"data-single": "true", "data-planid": True})
    for card in cards:
        rate_el = card.find(attrs={"data-rate": "true"})
        plan_el = card.find(attrs={"data-product-plan": "true"})
        if not rate_el or not plan_el:
            continue
        rate_m = re.search(r"([\d.]+)", rate_el.get_text())
        if not rate_m:
            continue
        rate = rate_m.group(1)
        if rate in seen:
            continue
        seen.add(rate)
        plan_p = plan_el.find("p")
        plan_name = plan_p.get_text(strip=True) if plan_p else plan_el.get_text(strip=True)
        term_raw = card.get("data-term", "")
        term = term_raw if term_raw.isdigit() else "N/A"
        type_m = _TYPE_PATTERN.search(plan_name)
        plan_type = type_m.group(1).capitalize() if type_m else "Fixed"
        results.append({
            "supplier":    row["supplier_name"],
            "edc_name":    row["edc_name"],
            "commodity":   row["commodity"],
            "plan_name":   plan_name,
            "rate":        rate,
            "term_months": term,
            "plan_type":   plan_type,
            "source_url":  row["website_url"],
            "data_source": "html_div",
        })
    return results


def _parse_constellation_table(soup: BeautifulSoup, row) -> list[dict]:
    """
    Constellation (legacy table layout) renders plans in a <table> with columns:
      Plan Name | Length | Rate | Special Offer
    Parse each <tbody> row directly for reliable extraction.
    """
    results = []
    seen: set[str] = set()
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            plan_name  = tds[0].get_text(strip=True)
            length_txt = tds[1].get_text(strip=True)   # e.g. "6 mo."
            rate_txt   = tds[2].get_text(strip=True)   # e.g. "21.59¢"

            # Extract numeric rate (strip ¢)
            rate_m = re.search(r"([\d.]+)", rate_txt)
            if not rate_m:
                continue
            rate = rate_m.group(1)
            if rate in seen:
                continue
            seen.add(rate)

            # Extract term in months
            term_m = _TERM_MO_PATTERN.search(length_txt) or _TERM_PATTERN.search(length_txt)
            term = term_m.group(1) if term_m else "N/A"

            type_m = _TYPE_PATTERN.search(plan_name)
            plan_type = type_m.group(1).capitalize() if type_m else "Fixed"

            results.append({
                "supplier":    row["supplier_name"],
                "edc_name":    row["edc_name"],
                "commodity":   row["commodity"],
                "plan_name":   plan_name,
                "rate":        rate,
                "term_months": term,
                "plan_type":   plan_type,
                "source_url":  row["website_url"],
                "data_source": "html_table",
            })
    return results


def _parse_xoom_cards(soup: BeautifulSoup, row) -> list[dict]:
    """
    Xoom Energy renders plans in div.myRateData elements with:
      - div.utility-choice-title  → plan name
      - div.utility-choice-rate   → term (e.g. "12 months", "Monthly")
      - div.utility-choice-price  → rate in $0.XXXXX/kWh format
      - img[alt]                  → plan type ("Fixed", "Variable", "Renewable Electric")
    """
    results = []
    cards = soup.find_all("div", class_="myRateData")
    if not cards:
        return []
    for card in cards:
        title_el = card.find(class_="utility-choice-title")
        rate_el  = card.find(class_="utility-choice-price")
        term_el  = card.find(class_="utility-choice-rate")
        if not title_el or not rate_el:
            continue
        plan_name = title_el.get_text(strip=True)
        raw_price = rate_el.get_text(separator=" ", strip=True)
        # Rate is in dollar format: "$0.1989/kWh" or "Intro: $0.1729/kWh*"
        normalized = _normalize_dollar_rates(raw_price)
        price_m = _PRICE_PATTERN.search(normalized) or _CENT_PATTERN.search(normalized)
        if not price_m:
            continue
        price = price_m.group(1)
        # Term from utility-choice-rate div: "12 months" → "12", "Monthly" → "N/A"
        term_text = term_el.get_text(strip=True) if term_el else ""
        term_m = _TERM_PATTERN.search(term_text)
        term_val = term_m.group(1) if term_m else ("0" if "month" in term_text.lower() else "N/A")
        # Plan type from img alt
        type_img = card.find("img")
        type_val = type_img["alt"].split()[0].capitalize() if type_img and type_img.get("alt") else "N/A"
        results.append({
            "supplier":    row["supplier_name"],
            "edc_name":    row["edc_name"],
            "commodity":   row["commodity"],
            "plan_name":   plan_name,
            "rate":        price,
            "term_months": term_val,
            "plan_type":   type_val,
            "source_url":  row["website_url"],
            "data_source": "html_div",
        })
    return results


def _parse_think_energy_cards(soup: BeautifulSoup, row) -> list[dict]:
    """
    Think Energy uses React styled-components where plan names are rendered in
    divs with a literal HTML attribute font-size="1.8rem" and rates in divs
    with font-size="4.5rem".  Random generated class names make CSS matching
    unreliable, but these custom props are stable.
    """
    # Plan name divs (e.g. "Think Clean 12")
    name_divs = soup.find_all("div", {"font-size": "1.8rem"})
    # Rate divs — only keep ones whose text looks like a decimal number
    rate_divs = [
        d for d in soup.find_all("div", {"font-size": "4.5rem"})
        if re.match(r"^\d{1,3}\.\d{2}$", d.get_text(strip=True))
    ]
    if not name_divs or not rate_divs:
        return []

    results = []
    for i, name_div in enumerate(name_divs):
        plan_name = name_div.get_text(strip=True)
        if not plan_name or len(plan_name) < 3:
            continue
        if i >= len(rate_divs):
            break
        rate = rate_divs[i].get_text(strip=True)

        # Walk up ancestors to find the card container that holds term info
        ancestor = name_div
        card_text = ""
        for _ in range(10):
            ancestor = ancestor.parent
            if ancestor is None:
                break
            card_text = ancestor.get_text(separator=" ", strip=True)
            if _TERM_PATTERN.search(card_text):
                break

        term_m = _TERM_PATTERN.search(card_text)
        type_m = _TYPE_PATTERN.search(card_text)
        results.append({
            "supplier":    row["supplier_name"],
            "edc_name":    row["edc_name"],
            "commodity":   row["commodity"],
            "plan_name":   plan_name,
            "rate":        rate,
            "term_months": term_m.group(1) if term_m else "N/A",
            "plan_type":   type_m.group(1).capitalize() if type_m else "N/A",
            "source_url":  row["website_url"],
            "data_source": "html_div",
        })
    return results


def _parse_direct_energy_cards(soup: BeautifulSoup, row) -> list[dict]:
    """
    Direct Energy plan cards are `.product-card.plan__wrapper` divs.
    Each card contains: plan name, rate (¢/kWh for electric, $/THERM for gas),
    term (N Months), type (Fixed/Variable).  Filter by commodity so gas cards
    don't appear in electric results and vice versa.
    """
    commodity = row.get("commodity", "electric").lower()
    cards = soup.select(".product-card.plan__wrapper")
    if not cards:
        return []

    results = []
    for card in cards:
        text = card.get_text(separator=" ", strip=True)
        # Skip cards that don't match the requested commodity
        has_therm = bool(re.search(r"/\s*THERM", text, re.IGNORECASE))
        has_kwh   = bool(re.search(r"/\s*kWh", text, re.IGNORECASE))
        if commodity == "electric" and has_therm and not has_kwh:
            continue
        if commodity == "gas" and has_kwh and not has_therm:
            continue

        # Plan name: first text child that looks like a real plan name
        name_el = card.select_one(".plan__title, .product-name, h2, h3, h4")
        plan_name = name_el.get_text(strip=True) if name_el else ""
        if not plan_name:
            # Fallback: first non-trivial text segment
            segs = [s for s in text.split(" | ") if len(s) > 4 and not re.match(r'^[\d.¢$]+$', s)]
            plan_name = segs[0] if segs else ""

        # Rate: prefer ¢/kWh digit, else $/THERM decimal
        rate_m = re.search(r"([\d.]+)\s*[¢\u00a2]\s*/\s*kWh", text, re.IGNORECASE)
        if not rate_m:
            rate_m = re.search(r"\$\s*([\d.]+)\s*/\s*(?:THERM|therm|ccf|CCF)", text)
        if not rate_m:
            continue
        rate = rate_m.group(1)

        term_m = _TERM_PATTERN.search(text)
        type_m = _TYPE_PATTERN.search(text)

        results.append({
            "supplier":    row["supplier_name"],
            "edc_name":    row["edc_name"],
            "commodity":   row["commodity"],
            "plan_name":   plan_name,
            "rate":        rate,
            "term_months": term_m.group(1) if term_m else "N/A",
            "plan_type":   type_m.group(1).capitalize() if type_m else "N/A",
            "source_url":  row["website_url"],
            "data_source": "html_div",
        })
    return results


def generic_parser(html_content: str, row) -> list[dict]:
    """
    Extract structured rate plan data from page HTML using BeautifulSoup.

    Strategy:
      1. Try Constellation-specific table parser first (fast, precise).
      2. Search for plan-like container divs by CSS class name.
      3. Fallback to scanning the entire document.
    """
    soup = BeautifulSoup(html_content, "lxml")
    results = []

    # --- 0. Supplier-specific parsers first (before any generic/constellation ones) ---
    # Xoom Energy: plans in div.myRateData with dollar-format rates
    if "xoom" in row.get("supplier_name", "").lower():
        xoom_results = _parse_xoom_cards(soup, row)
        if xoom_results:
            log.debug("  parser: xoom card mode → %d rows", len(xoom_results))
            return xoom_results

    # Think Energy: styled-components use font-size prop as plan-name marker
    if "think" in row.get("supplier_name", "").lower():
        think_results = _parse_think_energy_cards(soup, row)
        if think_results:
            log.debug("  parser: think_energy card mode → %d rows", len(think_results))
            return think_results

    # Direct Energy: plan cards are .product-card.plan__wrapper; filter by commodity
    if "direct" in row.get("supplier_name", "").lower():
        de_results = _parse_direct_energy_cards(soup, row)
        if de_results:
            log.debug("  parser: direct_energy card mode → %d rows", len(de_results))
            return de_results

    # --- 1. Try Constellation-specific parsers (div cards first, then legacy table) ---
    div_results = _parse_constellation_divs(soup, row)
    if div_results:
        log.debug("  parser: constellation div mode → %d rows", len(div_results))
        return div_results
    table_results = _parse_constellation_table(soup, row)
    if table_results:
        log.debug("  parser: table mode → %d rows", len(table_results))
        return table_results

    # --- 2. Plan container divs ---
    plan_containers = soup.find_all(
        lambda tag: tag.name in {"div", "article", "section", "li"}
        and any(_PLAN_CLASSES.search(cls) for cls in tag.get("class", []))
    )

    # --- 3. Fallback: whole document ---
    if not plan_containers:
        plan_containers = [soup]

    seen_prices: set[str] = set()

    for container in plan_containers:
        text = _normalize_dollar_rates(container.get_text(separator=" ", strip=True))

        price_match = _PRICE_PATTERN.search(text) or _CENT_PATTERN.search(text)
        if not price_match:
            continue
        price = price_match.group(1)

        if price in seen_prices:
            continue
        seen_prices.add(price)

        term_match = _TERM_PATTERN.search(text)
        type_match = _TYPE_PATTERN.search(text)
        heading    = container.find(["h1", "h2", "h3", "h4", "h5", "strong", "b"])
        # Fallback: try any div/span whose text looks like a plan name (short, no numbers)
        if not heading:
            for el in container.find_all(["div", "span", "p"]):
                el_text = el.get_text(strip=True)
                if (
                    2 < len(el_text) < 60
                    and not re.search(r"[\d¢$%]", el_text)
                    and len(el_text.split()) >= 2
                    and not _NAV_TEXT.search(el_text)
                ):
                    heading = el
                    break

        plan_name = heading.get_text(strip=True) if heading else "N/A"
        # Skip containers whose only heading is a UI/nav label (e.g. "Description",
        # "Details", "Summary" inside Bootstrap collapse panels)
        if plan_name != "N/A" and _NAV_TEXT.search(plan_name):
            continue

        results.append({
            "supplier":    row["supplier_name"],
            "edc_name":    row["edc_name"],
            "commodity":   row["commodity"],
            "plan_name":   plan_name,
            "rate":        price,
            "term_months": term_match.group(1) if term_match else "N/A",
            "plan_type":   type_match.group(1).capitalize() if type_match else "N/A",
            "source_url":  row["website_url"],
            "data_source": "html",
        })

    return results


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    csv_path   = os.path.join(SCRIPT_DIR, "..", "TPSCompilation", "master_third_party_supplier_list.csv")
    output_dir = os.path.join(SCRIPT_DIR, "..", "..", "data")
    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_csv(csv_path, dtype={"test_zip": str})  # preserve leading zeros

    if "scraper_type" not in df.columns:
        df["scraper_type"] = df["supplier_name"].map(SCRAPER_TYPE_MAP).fillna("default")
        df.loc[df["scraper_status"] == "manual_check_required", "scraper_type"] = "skip"

    electric_results: list[dict] = []
    gas_results:      list[dict] = []
    total = len(df)

    strategy_map = {
        "constellation": strategy_constellation,
        "direct_energy": strategy_direct_energy,
        "ambit":         strategy_ambit,
        "think_energy":  strategy_think_energy,
        "nrg":           strategy_nrg,
        "major_energy":  strategy_major_energy,
        "xoom_energy":   strategy_xoom_energy,
    }

    for index, row in df.iterrows():
        supplier     = row["supplier_name"]
        edc          = row["edc_name"]
        scraper_type = row["scraper_type"]

        if scraper_type == "skip":
            log.info("[%d/%d]  SKIP  %s / %s", index + 1, total, supplier, edc)
            continue

        log.info("=" * 70)
        log.info("[%d/%d]  START  %s / %s  (%s)", index + 1, total, supplier, edc, scraper_type)

        html_content  = None
        pdf_records: list[dict] = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    strategy_fn = strategy_map.get(scraper_type, strategy_default)
                    html_content, pdf_records = strategy_fn(page, row)
                finally:
                    browser.close()

        except Exception as exc:
            log.error("BROWSER_ERROR  %s / %s | %s", supplier, edc, exc)
            continue

        # ---- Accumulate results -------------------------------------------
        all_parsed: list[dict] = list(pdf_records)  # PDF results first

        if html_content:
            html_parsed = generic_parser(html_content, row)
            all_parsed.extend(html_parsed)
        else:
            log.warning("  NO_HTML_CONTENT  %s / %s", supplier, edc)

        if all_parsed:
            log.info("  OK  %d plan(s) found  (html=%d  pdf=%d)",
                     len(all_parsed), len(all_parsed) - len(pdf_records), len(pdf_records))
            if row["commodity"] == "electric":
                electric_results.extend(all_parsed)
            else:
                gas_results.extend(all_parsed)
        else:
            log.warning("  NO_PLANS  %s / %s", supplier, edc)

    # ---- Export -----------------------------------------------------------
    pd.DataFrame(electric_results).to_csv(
        os.path.join(output_dir, "nj_electric_scraped.csv"), index=False
    )
    pd.DataFrame(gas_results).to_csv(
        os.path.join(output_dir, "nj_gas_scraped.csv"), index=False
    )

    log.info("=" * 70)
    log.info("DONE  electric=%d  gas=%d  debug_dir=%s",
             len(electric_results), len(gas_results), DEBUG_DIR)


if __name__ == "__main__":
    main()
