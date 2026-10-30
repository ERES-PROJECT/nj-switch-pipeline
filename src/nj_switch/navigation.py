"""Supplier-specific public shopping flows. No enrollment or forced validation bypass."""
from dataclasses import dataclass, field
from html import escape
import io
import json
from pathlib import Path
import re
from urllib.parse import urlencode, urljoin, urlsplit

from bs4 import BeautifulSoup
import pdfplumber
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .models import Query
from .registry import utility_matches


class NavigationError(RuntimeError):
    pass


class UnsupportedContext(NavigationError):
    """The public shopping source explicitly does not expose this market."""
    pass


class SourceUnavailable(NavigationError):
    """The supplier or its access layer explicitly prevented collection."""
    pass


@dataclass
class NavigationResult:
    html: str = ""
    url: str = ""
    context_verified: bool = False
    live_data_verified: bool = False
    fragments: list[dict] = field(default_factory=list)
    # Public documents captured as the direct result of clicking a visible
    # plan-document action in the supplier's browser flow. These bytes never
    # come from a direct HTTP replay that could bypass the source's policy.
    captured_documents: list[dict] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    disposition: str | None = None


def visible(locator):
    return [locator.nth(i) for i in range(locator.count()) if locator.nth(i).is_visible()]


def click_one(page, selectors: list[str], optional: bool = False, no_wait_after: bool = False):
    for selector in selectors:
        items = visible(page.locator(selector))
        if len(items) == 1:
            items[0].click(no_wait_after=no_wait_after)
            return True
    if not optional:
        raise NavigationError("No unique visible action: " + " | ".join(selectors))
    return False


def fill_zip(page, selector: str, query: Query):
    locator = page.locator(selector)
    locator.first.wait_for(state="attached")
    items = visible(locator)
    if len(items) != 1:
        raise NavigationError("ZIP input is absent or ambiguous")
    items[0].fill(query.zip)


def choose_utility(page, selector: str, query: Query, no_wait_after: bool = False):
    items = visible(page.locator(selector))
    matches = []
    for item in items:
        label = item.inner_text() or item.get_attribute("aria-label") or ""
        if not utility_matches(label, query.utility):
            continue
        context = item.evaluate("el => (el.closest('tr,li') || el.parentElement).innerText")
        if item.locator(".fa-bolt").count() and query.commodity != "electric":
            continue
        if item.locator(".fa-fire").count() and query.commodity != "gas":
            continue
        other = "gas" if query.commodity == "electric" else "electric"
        if re.search(rf"\b{other}\b", context, re.I) and not re.search(rf"\b{query.commodity}\b", context, re.I):
            continue
        matches.append(item)
    if len(matches) != 1:
        raise NavigationError(f"Utility selection ambiguous/absent: {query.utility} ({len(matches)} matches)")
    matches[0].click(no_wait_after=no_wait_after)


def start(page, query: Query, url: str | None = None):
    target = url or query.url
    for attempt in range(2):
        try:
            page.goto(target, wait_until="domcontentloaded", timeout=30000)
            break
        except PlaywrightTimeoutError:
            if attempt:
                raise
    # Dismissal is optional and never accepts contractual enrollment terms.
    click_one(page, ['button.cky-btn-reject', '#onetrust-reject-all-handler',
                     '.onetrust-close-btn-handler', '#location-popupmodal button.close',
                     '#location-popupmodal .close'], optional=True)


def dismiss_cookieyes(page):
    try:
        button = page.locator("button.cky-btn-reject").filter(visible=True)
        button.first.wait_for(state="visible", timeout=4000)
        button.first.click()
        page.locator(".cky-overlay").wait_for(state="hidden")
    except PlaywrightTimeoutError:
        pass


def capture_details(page, result: NavigationResult, selector: str, modal_selector: str):
    links = page.locator(selector)
    for index in range(min(links.count(), 30)):
        link = page.locator(selector).nth(index)
        if not link.is_visible():
            continue
        origin = link.evaluate("el => { const c=el.closest('[data-planid],[data-product-id],[data-productid],.product-card,.myRateData'); return c ? c.outerHTML : ''; }")
        link.click()
        modal = page.locator(modal_selector).filter(visible=True)
        try:
            modal.first.wait_for(state="visible")
            result.fragments.append({"origin": origin, "html": modal.first.inner_html(), "url": page.url})
        except PlaywrightTimeoutError:
            result.notes.append("A detail dialog did not become visible")
            continue
        page.keyboard.press("Escape")
        if modal.first.is_visible():
            close = modal.first.locator('button[aria-label="Close"], .close, .ngdialog-close')
            if close.count() and close.first.is_visible():
                close.first.click()
        try:
            modal.first.wait_for(state="hidden")
        except PlaywrightTimeoutError:
            result.notes.append("Detail dialog remained open; further dialog collection stopped")
            break


def finish(page, result: NavigationResult, selector: str):
    page.locator(selector).first.wait_for(state="attached", timeout=15000)
    result.html, result.url = page.content(), page.url
    return result


def strategy_constellation(page, query: Query) -> NavigationResult:
    signup = (
        "https://www.constellation.com/solutions/for-your-home/"
        f"residential-signup.html?zip={query.zip}"
    )
    start(page, query, signup)

    provider_selector = "#electricity-provider" if query.commodity == "electric" else "#gas-provider"
    provider = page.locator(provider_selector)
    provider.wait_for(state="attached", timeout=20000)
    page.wait_for_function(
        "selector => (document.querySelector(selector)?.options.length || 0) > 1",
        arg=provider_selector,
        timeout=20000,
    )
    options = provider.locator("option").evaluate_all(
        "els => els.map(e => ({label:(e.textContent || '').trim(), value:e.value}))"
    )
    matches = [option for option in options if utility_matches(option["label"], query.utility)]
    if len(matches) != 1:
        raise UnsupportedContext(
            "Requested Constellation utility is absent from the ZIP-specific commodity selector"
        )
    provider.select_option(value=matches[0]["value"])
    selected_label = provider.locator("option:checked").inner_text().strip()
    if not utility_matches(selected_label, query.utility):
        raise NavigationError("Constellation did not retain the requested utility selection")

    page.locator("#signUpFormStepOneSubmit").click(no_wait_after=True)
    container = (
        "#individual-electricity-options"
        if query.commodity == "electric"
        else "#individual-gas-options"
    )
    cards = page.locator(f"{container} > ul > li")
    try:
        cards.first.wait_for(state="attached", timeout=30000)
    except PlaywrightTimeoutError:
        html = page.content()
        if re.search(r"do not have plans|no (?:plans|offers) (?:are )?available", html, re.I):
            return NavigationResult(
                html=html,
                url=page.url,
                context_verified=True,
                live_data_verified=True,
                disposition="empty",
                notes=["Constellation explicitly returned no plans for the selected ZIP and utility"],
            )
        if reason := access_failure(html):
            raise SourceUnavailable(reason)
        raise NavigationError("Constellation did not return live plan cards")

    if query.zip not in page.url:
        raise NavigationError("Constellation plan response lost the requested ZIP context")
    return NavigationResult(
        html=page.content(),
        url=page.url,
        context_verified=True,
        live_data_verified=True,
        notes=["ZIP and commodity-specific utility verified before collecting current plan cards"],
    )


def direct_displayed_plan_count(text: str) -> int | None:
    """Read Direct's own post-expansion plan count from the shopping page."""
    match = re.search(r"Viewing\s+(\d+)\s+plans?", text or "", re.I)
    return int(match.group(1)) if match else None


def direct_rendered_card_count(page, commodity: str) -> int:
    """Count only visible Direct cards for the requested commodity."""
    unit = re.compile(r"/(?:kwh)\b", re.I) if commodity == "electric" else re.compile(r"/(?:therm|ccf|dth)\b", re.I)
    return sum(
        1 for card in visible(page.locator(".product-card"))
        if unit.search(card.inner_text())
    )


def reconcile_direct_plan_counts(displayed: int | None, rendered: int) -> None:
    """Fail closed when Direct's page cannot prove all displayed cards were captured."""
    if displayed is None:
        raise NavigationError("Direct Energy did not expose its displayed plan count")
    if displayed != rendered:
        raise NavigationError(
            f"Direct Energy displayed/rendered plan-count mismatch: {displayed} versus {rendered}"
        )


def expand_direct_plans(page, commodity: str) -> tuple[int, int]:
    """Exhaust Direct's bounded public expansion control and reconcile its UI."""
    for _ in range(4):
        actions = visible(page.get_by_role("button", name=re.compile("View more plans", re.I)))
        if not actions:
            break
        before = direct_rendered_card_count(page, commodity)
        actions[0].click()
        try:
            page.wait_for_function(
                "([before, unit]) => {"
                "const cards=Array.from(document.querySelectorAll('.product-card'))"
                ".filter(card=>card.offsetParent!==null && new RegExp(unit,'i').test(card.innerText));"
                "const more=Array.from(document.querySelectorAll('button'))"
                ".some(button=>button.offsetParent!==null && /view more plans/i.test(button.innerText));"
                "return cards.length > before || !more;}",
                arg=[before, r"/kwh\b" if commodity == "electric" else r"/(therm|ccf|dth)\b"],
                timeout=7000,
            )
        except PlaywrightTimeoutError as exc:
            raise NavigationError("Direct Energy plan expansion made no observable progress") from exc
    text = page.locator("body").inner_text()
    displayed = direct_displayed_plan_count(text)
    rendered = direct_rendered_card_count(page, commodity)
    reconcile_direct_plan_counts(displayed, rendered)
    return displayed, rendered


def strategy_direct_energy(page, query: Query) -> NavigationResult:
    # Begin at the public root so Direct can establish its normal regional
    # session before the ZIP submission redirects to the shopping host.
    start(page, query, "https://www.directenergy.com/")
    if reason := access_failure(page.content()):
        raise SourceUnavailable(reason)
    # Give the late location popup a bounded chance to settle before proceeding.
    popup = page.locator("#location-popupmodal")
    try:
        popup.wait_for(state="visible", timeout=4000)
        region = popup.locator("select#state, select").first
        if region.count():
            # Prefer the native control because it fires the same change event
            # without depending on the current custom-select markup.
            region.select_option("NJ")
            if popup.get_by_role("button", name="Continue", exact=True).is_disabled():
                popup.locator(".select-selected").click()
                popup.locator(".select-items div").filter(has_text="New Jersey").click()
            popup.get_by_role("button", name="Continue", exact=True).click(timeout=4000)
        else:
            popup.get_by_role("button", name="Close", exact=True).click(timeout=4000)
        popup.wait_for(state="hidden", timeout=4000)
    except PlaywrightTimeoutError:
        pass
    click_one(page, ['button:has-text("Midwest/Northeast")', 'a:has-text("Midwest/Northeast")'], optional=True)
    forms = page.locator('form#zipcode-form, form.zipcode-form, form.zip-widget-form')
    forms.first.wait_for(state="attached", timeout=15000)
    visible_forms = visible(forms)
    zip_form = visible_forms[0] if visible_forms else forms.first
    # Submit the exact GET route declared by the current public homepage. This
    # is equivalent to pressing Enter in the ZIP input but avoids the page's
    # duplicate responsive forms and presentation-only validation handlers.
    # The action is re-read and allowlisted on every run; no legacy deep link
    # or hidden enrollment route is maintained here.
    action = zip_form.get_attribute("action") or ""
    action_url = urljoin(page.url, action)
    parts = urlsplit(action_url)
    if parts.scheme != "https" or parts.hostname != "shop.directenergy.com" or parts.path != "/search-for-plans":
        raise NavigationError("Direct Energy homepage ZIP form has an unexpected action")
    page.goto(f"{action_url}?{urlencode({'zipCode': query.zip})}", wait_until="domcontentloaded", timeout=30000)
    try:
        page.locator(".product-card").first.wait_for(state="attached", timeout=30000)
    except PlaywrightTimeoutError:
        if reason := access_failure(page.content()):
            raise SourceUnavailable(reason)
        # The Gatsby transition can occasionally remain on its "Please Wait"
        # shell at either the search or product-chart URL. One clean reload is
        # enough to resume the already-established public ZIP context.
        page.reload(wait_until="domcontentloaded", timeout=30000)
        try:
            page.locator(".product-card").first.wait_for(state="attached", timeout=30000)
        except PlaywrightTimeoutError:
            if reason := access_failure(page.content()):
                raise SourceUnavailable(reason)
            raise
    page.wait_for_function(
        "zip => document.body.innerText.includes(zip) && /Viewing\\s+\\d+\\s+plans/i.test(document.body.innerText)",
        arg=query.zip,
        timeout=15000,
    )
    if query.commodity == "gas":
        gas_actions = visible(page.get_by_role("button", name=re.compile("Continue to Natural Gas Plans", re.I)))
        if not gas_actions:
            gas_actions = visible(page.get_by_role("button", name=re.compile("Natural Gas", re.I)))
        if not gas_actions:
            raise NavigationError("Direct Energy natural-gas plan action is absent")
        try:
            gas_actions[0].click()
        except PlaywrightTimeoutError:
            # Direct sometimes completes the SPA transition and publishes the
            # gas product response while Playwright is still waiting for the
            # click action to settle. Treat that as success only when the page
            # already proves that gas cards rendered; otherwise preserve the
            # timeout as a real navigation failure.
            if not direct_rendered_card_count(page, "gas"):
                raise
        page.wait_for_function(
            "() => { const cards = Array.from(document.querySelectorAll('.product-card')); "
            "return cards.some(card => /\\/(?:therm|ccf|dth)/i.test(card.innerText)); }",
            timeout=15000,
        )
    else:
        page.wait_for_function(
            "() => { const cards = Array.from(document.querySelectorAll('.product-card')); "
            "return cards.some(card => /\\/kwh/i.test(card.innerText)); }",
            timeout=15000,
        )
    displayed_count, rendered_count = expand_direct_plans(page, query.commodity)
    result = finish(page, NavigationResult(), ".product-card")
    # A ZIP can contain multiple utilities; the captured supplier API response
    # remains the authority for utility qualification in profiles.direct_energy.
    # assemble() promotes only products matching that verified utility code.
    result.notes.append(
        "Direct Energy's ordinary homepage ZIP path rendered the requested commodity; utility qualification is verified from the captured get-utilities-by-zip and products responses"
    )
    result.notes.append(
        f"Direct Energy expanded and reconciled {rendered_count} rendered plan card(s) against its displayed count of {displayed_count}"
    )
    # Product API responses provide document URLs; DOM dialogs are a fallback only.
    if not page.url.startswith("https://shop.directenergy.com/"):
        capture_details(page, result, 'button:has-text("Learn more")', '.modal.show, .modal.in')
    return result


def strategy_ambit(page, query: Query) -> NavigationResult:
    # The registry's legacy /servicearea now redirects to this public flow.
    start(page, query, "https://www.ambitenergy.com/")
    fill_zip(page, "#rates-start #zip", query)
    page.locator('#rates-start button:has-text("Get Started")').click()
    page.locator('label[for="rates-house"]:visible, label[for="rates-home"]:visible').first.click()
    page.locator('#rates-start input[type="submit"]').click()
    page.wait_for_url("https://shoppingexp.ambitenergy.com/**", timeout=25000)
    click_one(page, ["#dismiss-btn-lg", "button#dismiss-btn"], optional=True)
    page.locator("label.form-check-label").first.wait_for()
    choose_utility(page, "label.form-check-label", query)
    page.get_by_role("button", name="Submit", exact=True).click()
    if hasattr(page, "capture_stage"):
        page.capture_stage("ambit_after_utility")
    # The new shopping platform no longer has the legacy ngDialog cards.
    return finish(page, NavigationResult(context_verified=True,
                  live_data_verified=True,
                  notes=["Ambit document actions have no stable href; plan-specific document discovery remains incomplete"]), '.ds_plan_item .cost')


def legacy_ambit_details(page, query: Query) -> NavigationResult:
    """Retained parser-navigation fallback for a legacy provider page fixture."""
    page.locator("span.list-group-item").first.wait_for()
    choose_utility(page, "span.list-group-item", query)
    click_one(page, ["#nextButton"], optional=True)
    page.locator('a:has-text("View Plan Info")').first.wait_for(timeout=20000)
    result = NavigationResult(context_verified=True)
    capture_details(page, result, 'a:has-text("View Plan Info")', '.ngdialog-content')
    return finish(page, result, 'a:has-text("View Plan Info")')


def strategy_think_energy(page, query: Query) -> NavigationResult:
    start(page, query)
    dismiss_cookieyes(page)
    fill_zip(page, '#input_1_2, input[placeholder="Zip Code"]', query)
    click_one(page, ['#gform_submit_button_1', 'button:has-text("View Offers")'])
    result = finish(page, NavigationResult(), 'div[font-size="1.8rem"], [data-product-id]')
    result.context_verified = utility_matches(page.locator("body").inner_text(), query.utility)
    result.live_data_verified = result.context_verified
    for button in visible(page.locator('button:has-text("View Details"), a:has-text("View Details")')):
        button.click()
    result.html = page.content()
    return result


def strategy_nrg(page, query: Query) -> NavigationResult:
    start(page, query, "https://www.picknrg.com/en/new-jersey")
    # Third-party assets can keep the page-wide load event pending after the
    # shopping controls are ready. Their absence must not fail collection.
    try:
        page.wait_for_load_state("load", timeout=10000)
    except PlaywrightTimeoutError:
        pass
    fill_zip(page, "#zip", query)
    page.locator("#zip").press("Tab")
    # The handler can open the selection modal before unrelated page activity
    # settles. Observe the modal explicitly below instead of waiting in click().
    shop_buttons = visible(page.locator(
        'button.zipCodeParam, button:has-text("Shop now"):not(.headerDsktpShopNowBtn)'
    ))
    if len(shop_buttons) != 1:
        raise NavigationError(f"NRG ZIP submit action is absent or ambiguous ({len(shop_buttons)} visible)")
    # NRG's fixed responsive header can briefly overlay the visible banner
    # button even though its public handler is ready. Invoke that exact control
    # rather than using force-click coordinates through the overlay.
    shop_buttons[0].evaluate("element => element.click()")
    page.locator('#goToutilityModal:visible, #goToProductChart:visible, .product-card:visible').first.wait_for(timeout=15000)
    result = NavigationResult()
    modal = page.locator("#commodityModalWindow")
    if page.locator("#goToutilityModal").is_visible():
        selector = "#elecCheckBox" if query.commodity == "electric" else "#gasCheckBox"
        box = page.locator(selector)
        if not box.is_checked():
            page.locator(f"label:has({selector})").click(no_wait_after=True)
        if not box.is_checked():
            raise NavigationError("Commodity checkbox did not update after label click")
        # The control updates the modal and some versions also schedule a slow
        # navigation. Continue from the observable next modal instead of making
        # Playwright wait for unrelated page activity.
        # Native click can wait on unrelated page activity after the handler has
        # already fired. Dispatch the public control's click and observe the
        # next modal/URL explicitly below.
        page.locator("#goToutilityModal").evaluate("el => el.click()")
        try:
            # A product-chart navigation can race the utility modal while the
            # page still carries its default PSE&G value. Never accept that
            # navigation as requested-utility proof; wait for the exact utility
            # selector that must be used below.
            page.locator("#goToProductChart:visible").wait_for(timeout=10000)
        except PlaywrightTimeoutError:
            if "/product-chart" not in page.url:
                raise
    utility = page.locator("#modalWindow")
    if page.locator("#goToProductChart").is_visible():
        group = "#showelectric" if query.commodity == "electric" else "#showgas"
        utility_labels = visible(page.locator(f"#modalWindow {group} label"))
        matching_labels = [
            label for label in utility_labels
            if utility_matches(label.inner_text(), query.utility)
        ]
        if len(matching_labels) != 1:
            raise NavigationError(
                f"NRG utility selection ambiguous/absent: {query.utility} "
                f"({len(matching_labels)} matches)"
            )
        selected_label = matching_labels[0].inner_text().strip()
        matching_labels[0].click(no_wait_after=True)
        checked = page.locator(f"#modalWindow {group} input:checked")
        selected_value = checked.first.get_attribute("value") if checked.count() else None
        if not selected_value:
            raise NavigationError("NRG utility label click did not select a utility value")
        result.evidence["nrg_utility_selection"] = {
            "requested_utility": query.utility,
            "selected_label": selected_label,
            "selected_value": selected_value,
        }
        page.locator("#goToProductChart").click(no_wait_after=True)
        result.context_verified = True
        result.live_data_verified = True
    return finish(page, result, '.pc-plan-container[id], .product-card, [data-product-id], .tier-card')


def strategy_major_energy(page, query: Query) -> NavigationResult:
    start(page, query, f"https://signup.majorenergy.com/?zipcode={query.zip}")
    page.locator('a[href*="SelectUtility"]').first.wait_for()
    # The selection has completed once product cards appear; waiting for every
    # analytics/navigation listener can otherwise time out after a valid click.
    choose_utility(page, 'a[href*="SelectUtility"]', query, no_wait_after=True)
    result = finish(
        page,
        NavigationResult(context_verified=True, live_data_verified=True),
        '.card:has(a[href*="SelectProduct"]), [data-product-id], [data-productid], .plan-card, .product-card',
    )
    capture_major_plan_documents(page, result)
    return result


def capture_major_plan_documents(page, result: NavigationResult) -> None:
    """Capture only PDFs opened by Major's visible plan-level TOS actions."""
    links = page.locator('a[href*="/getdocument/"][href*="ProductID="][href*="type=TOS"]')
    seen = set()
    original_page = page
    for index in range(min(links.count(), 40)):
        link = links.nth(index)
        href = urljoin(page.url, link.get_attribute("href") or "")
        match = re.search(r"[?&]ProductID=([^&#]+)", href, re.I)
        product_id = match.group(1) if match else None
        if not href or not product_id or href in seen:
            continue
        seen.add(href)
        if not link.is_visible():
            toggle = page.locator(f'[aria-controls="productDetail-{product_id}"]:visible').first
            if not toggle.count():
                result.notes.append(f"Major plan {product_id} TOS action could not be made visible")
                continue
            toggle.click()
            try:
                link.wait_for(state="visible", timeout=5000)
            except PlaywrightTimeoutError:
                result.notes.append(f"Major plan {product_id} TOS action did not become visible")
                continue
        try:
            # Major serves this visible link as a browser download. Capture the
            # Download generated by the click instead of replaying the URL with
            # an HTTP client or trying to read Chromium's built-in PDF viewer.
            with page.expect_download(timeout=15000) as download_info:
                link.evaluate("el => el.click()")
            download = download_info.value
            path = download.path()
            data = Path(path).read_bytes() if path else b""
            if not data.startswith(b"%PDF"):
                result.notes.append(f"Major plan {product_id} TOS action returned non-PDF content")
                continue
            result.captured_documents.append({
                "url": href,
                "requested_url": href,
                "product_id": product_id,
                "label": "Terms of Service",
                "content_type": "application/pdf",
                "data": data,
            })
        except Exception as exc:
            result.notes.append(
                f"Major plan {product_id} public TOS click could not be captured: {type(exc).__name__}"
            )
        finally:
            for opened in list(page.context.pages):
                if opened is not original_page:
                    try:
                        opened.close()
                    except Exception:
                        pass


def capture_nextera_details(page, result: NavigationResult,
                            required_product_ids: list[str] | None = None) -> None:
    """Capture AJAX-populated plan documents without selecting/enrolling."""
    actions = page.locator(".learnMoreDetails[data-rate]")
    expected_ids = list(required_product_ids or [])
    captured_ids = set()
    document_ids = set()
    for index in range(min(actions.count(), 20)):
        action = actions.nth(index)
        product_id = (action.get_attribute("data-rate") or "").strip()
        if not product_id:
            result.notes.append("NextEra plan-details action had no stable data-rate identity")
            continue
        if product_id not in expected_ids:
            expected_ids.append(product_id)
        if product_id in captured_ids:
            result.notes.append(f"NextEra duplicate plan-details identity ignored: {product_id}")
            continue
        if not action.is_visible():
            result.notes.append(f"NextEra plan {product_id} details action was not visible")
            continue
        origin = action.evaluate(
            "el => { const card=el.closest('.pricing_plan_item.plan_card'); "
            "return card ? card.outerHTML : ''; }"
        )
        # The supplier repeats id="myModal" and id="result" inside every
        # card, but its click handler always writes into the first page-level
        # modal. Waiting inside the clicked card therefore loses every plan
        # after the first. Observe the modal the site actually makes visible.
        modal = page.locator(".modal:visible .modal-content").first
        try:
            action.evaluate("el => el.click()")
            modal.wait_for(state="visible", timeout=7000)
        except PlaywrightTimeoutError:
            result.notes.append(f"NextEra plan {product_id} did not open a visible details modal")
            continue
        result_box = modal.locator("#result")
        try:
            loaded = result_box.evaluate(
                "(el, expected) => new Promise(resolve => {"
                "const ready=()=>Array.from(el.querySelectorAll('a[href]')).some(a => {"
                "try{return decodeURIComponent(a.href).replaceAll(',', '|').includes(expected)}"
                "catch{return false}});"
                "if (ready()) return resolve(true);"
                "const observer=new MutationObserver(()=>{if(ready()){observer.disconnect();resolve(true);}});"
                "observer.observe(el,{childList:true,subtree:true,characterData:true,attributes:true});"
                "setTimeout(()=>{observer.disconnect();resolve(false);},12000);"
                "})",
                product_id,
            )
            if not loaded:
                result.notes.append(f"NextEra plan {product_id} details did not finish loading")
                continue
            detail_html = modal.inner_html()
            result.fragments.append({
                "origin": origin,
                "html": detail_html,
                "url": page.url,
                "product_id": product_id,
            })
            captured_ids.add(product_id)
            if not nextera_detail_has_document(detail_html):
                result.notes.append(
                    f"NextEra plan {product_id} details loaded but exposed no plan document link"
                )
            else:
                document_ids.add(product_id)
        except PlaywrightTimeoutError:
            result.notes.append(f"NextEra plan {product_id} details did not finish loading")
        finally:
            close = modal.locator("button.close, .close_lightbox")
            if close.count() and close.first.is_visible():
                close.first.click()
            else:
                page.keyboard.press("Escape")
            try:
                modal.wait_for(state="hidden", timeout=5000)
            except PlaywrightTimeoutError:
                result.notes.append(f"NextEra plan {product_id} details modal remained open")
                break
    missing = sorted(set(expected_ids) - captured_ids)
    if missing:
        result.notes.append(
            "NextEra details were not captured for product identities: " + ", ".join(missing)
        )
    result.notes.append(
        f"NextEra details reconciliation: {len(captured_ids)}/{len(set(expected_ids))} "
        f"plan panel(s) captured; {len(document_ids)} exposed plan-document links"
    )


def nextera_detail_has_document(html: str) -> bool:
    """Distinguish loaded details with no document from a failed AJAX capture."""
    soup = BeautifulSoup(html or "", "lxml")
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        label = link.get_text(" ", strip=True)
        if re.search(r"\.pdf(?:$|[?#])|contract|terms|disclosure|document", href + " " + label, re.I):
            return True
    return False


def nextera_plan_identities(html: str) -> list[str]:
    """Require one unique composite identity for every rendered plan card."""
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(".pricing_plan_item.plan_card")
    identities = []
    for card in cards:
        action = card.select_one(".learnMoreDetails[data-rate]")
        product_id = action.get("data-rate", "").strip() if action else ""
        if not product_id:
            raise NavigationError("NextEra rendered a plan without a composite data-rate identity")
        identities.append(product_id)
    if not identities:
        raise NavigationError("NextEra rendered no identifiable plan cards")
    if len(set(identities)) != len(identities):
        raise NavigationError("NextEra rendered duplicate composite plan identities")
    return identities


def wait_for_xoom_results(page, timeout: int = 15000) -> bool:
    """Wait for live Xoom cards, reloading the exact result URL once if it stalls."""
    cards = page.locator(".myRateData")
    try:
        cards.first.wait_for(state="attached", timeout=timeout)
        return False
    except PlaywrightTimeoutError:
        # Xoom occasionally reaches the correct ZIP/utility URL while the
        # ASP.NET navigation remains pending. Reload only that already-derived
        # public result URL; never substitute another ZIP, market, or fixture.
        page.reload(wait_until="domcontentloaded", timeout=30000)
        cards.first.wait_for(state="attached", timeout=timeout)
        return True


def recover_njgande_gateway(page, reload_attempts: int = 2) -> bool:
    """Retry NJG&E's exact public page after a transient Azure origin timeout."""
    recovered = False
    for _ in range(reload_attempts):
        html = page.content()
        if not re.search(
            r"(?:504|Gateway Timeout|OriginTimeout|isn't responding to Azure Front Door)",
            BeautifulSoup(html or "", "lxml").get_text(" ", strip=True),
            re.I,
        ):
            return recovered
        page.reload(wait_until="domcontentloaded", timeout=30000)
        recovered = True
    html = page.content()
    if re.search(
        r"(?:504|Gateway Timeout|OriginTimeout|isn't responding to Azure Front Door)",
        BeautifulSoup(html or "", "lxml").get_text(" ", strip=True),
        re.I,
    ):
        raise SourceUnavailable("NJG&E enrollment origin repeatedly returned an Azure Front Door 504 timeout")
    return recovered


def strategy_xoom_energy(page, query: Query) -> NavigationResult:
    start(page, query)
    fill_zip(page, '#cpTopMain_cpMain_txtSearch', query)
    page.locator('#cpTopMain_cpMain_btnSearch').click()
    group = "rptElectric" if query.commodity == "electric" else "rptNatural"
    selector = f'a[href*="{group}"][href*="btnUtility"]'
    page.locator(selector).first.wait_for()
    choose_utility(page, selector, query)
    prefix = "#cpTopMain_cpMain_ucDualMarketModal_"
    panel = page.locator(prefix + "pnlDualEnrollment")
    try:
        panel.wait_for(state="visible", timeout=3000)
    except PlaywrightTimeoutError:
        # Single-market utilities proceed directly to their product cards.
        retried = wait_for_xoom_results(page)
        notes = ["Reloaded the exact ZIP-qualified Xoom result URL after a stalled navigation"] if retried else []
        return finish(page, NavigationResult(context_verified=True, live_data_verified=True, notes=notes), ".myRateData")
    wanted = prefix + ("rblElectricChoice" if query.commodity == "electric" else "rblGasChoice")
    unwanted = prefix + ("rblGasChoice" if query.commodity == "electric" else "rblElectricChoice")
    choose_utility(page, wanted + " a[role=radio]", query)
    choices = visible(page.locator(unwanted + " a[role=radio]"))
    opt_out = [c for c in choices if re.search(r"not interested|don.t want|no thanks|skip", c.get_attribute("aria-label") or c.inner_text(), re.I)]
    if len(opt_out) != 1:
        raise NavigationError("Cannot identify an unambiguous commodity opt-out")
    opt_out[0].click()
    # ASP.NET can complete this postback while Playwright continues waiting
    # for a scheduled navigation that never formally settles. The dedicated
    # result waiter below validates cards and reloads only the exact derived
    # result URL if necessary.
    page.locator(prefix + "btnContinue").click(no_wait_after=True)
    retried = wait_for_xoom_results(page)
    notes = ["Reloaded the exact ZIP-qualified Xoom result URL after a stalled navigation"] if retried else []
    return finish(page, NavigationResult(context_verified=True, live_data_verified=True, notes=notes), ".myRateData")


def strategy_default(page, query: Query) -> NavigationResult:
    start(page, query)
    fill_zip(page, 'input[autocomplete="postal-code"], input[name*="zip" i], input[placeholder*="zip" i]', query)
    click_one(page, ['button:has-text("View Rates")', 'button:has-text("View Plans")',
                     'button:has-text("See Plans")', 'button:has-text("Shop Plans")'])
    return NavigationResult(html=page.content(), url=page.url,
                            notes=["Generic discovery only: no verified supplier/utility adapter"])


def strategy_mpower_energy(page, query: Query) -> NavigationResult:
    raise UnsupportedContext(
        "Mpower's public rate file is not ZIP-qualified and its linked terms are out-of-state; "
        "it is not accepted as a current New Jersey offer source"
    )


def strategy_nordic_energy_services(page, query: Query) -> NavigationResult:
    start(page, query, "https://www.nordicenergy-us.com/")
    page.locator("#customer-type").first.select_option("Residential")
    page.locator("#state-selector").first.select_option("New Jersey")
    utility = page.locator(f"#utility-selector-{query.commodity}")
    options = utility.locator("option").evaluate_all(
        "els => els.map(e => ({label:(e.textContent || '').trim(), value:e.value}))"
    )
    matches = [option for option in options if utility_matches(option["label"], query.utility)]
    if len(matches) != 1:
        raise UnsupportedContext(f"Requested Nordic {query.commodity} utility is absent from the current selector")
    utility.select_option(value=matches[0]["value"])
    page.locator('#state-selector-container input[type="submit"]').click()
    page.wait_for_load_state("domcontentloaded")
    cards = page.locator(f"section.{query.commodity} .utility-offer")
    try:
        cards.first.wait_for(state="visible", timeout=15000)
    except PlaywrightTimeoutError:
        html = page.content()
        if re.search(r"not currently available|no (?:plans|rates)", html, re.I):
            return NavigationResult(html=html, url=page.url, context_verified=True,
                                    live_data_verified=True, disposition="empty")
        raise
    return NavigationResult(html=page.content(), url=page.url,
                            context_verified=True, live_data_verified=True)


def indra_terms_url_valid(url: str) -> bool:
    """Accept only HTTPS documents hosted by Indra or its subdomains."""
    parsed = urlsplit(url or "")
    host = (parsed.hostname or "").casefold()
    return parsed.scheme == "https" and (
        host == "indraenergy.com" or host.endswith(".indraenergy.com")
    ) and bool(parsed.path)


def classify_indra_terms_state(state: dict, seen_product_ids: set[str]) -> tuple[str, str, str]:
    """Classify one completed modal state without inventing document evidence."""
    product_id = str(state.get("productId") or "").strip()
    pdf_url = str(state.get("pdfUrl") or "").strip()
    if not product_id:
        return "missing_product_identity", "", pdf_url
    if product_id in seen_product_ids:
        return "duplicate_product_identity", product_id, pdf_url
    if state.get("error"):
        return "terms_service_error", product_id, pdf_url
    if not pdf_url:
        return "no_document_url", product_id, ""
    if not indra_terms_url_valid(pdf_url):
        return "invalid_document_url", product_id, pdf_url
    return "document", product_id, pdf_url


def capture_indra_terms(page, controller, button, result: NavigationResult,
                        index: int, seen_product_ids: set[str]) -> None:
    """Open one plan modal with one bounded retry for terms-generation failure."""
    last_status = "terms_service_timeout"
    last_product_id = ""
    for attempt in (1, 2):
        button.click()
        modal = page.locator('.indra-modal-panel[role="dialog"]')
        modal.wait_for(state="visible", timeout=7000)
        try:
            page.wait_for_function(
                "() => { const modal=document.querySelector('.indra-modal-panel[role=dialog]'); "
                "if (!modal || modal.offsetParent === null) return false; "
                "const href=modal.querySelector('a[href]')?.getAttribute('href') || ''; "
                "return /^https?:/.test(href) || /not available|unable to load/i.test(modal.innerText); }",
                timeout=12000,
            )
        except PlaywrightTimeoutError:
            pass

        state = controller.evaluate(
            "el => { const d=window.Alpine && window.Alpine.$data(el); "
            "const p=d && d.modalPlan; return {"
            "productId:p && [p.rateCode,(p.sysId || p.id)].filter(Boolean).join('|'), "
            "pdfUrl:(d && d.modalPdfUrl) || '', error:(d && d.modalPdfError) || ''}; }"
        )
        status, product_id, pdf_url = classify_indra_terms_state(state or {}, seen_product_ids)
        last_status, last_product_id = status, product_id
        if product_id and status != "duplicate_product_identity":
            seen_product_ids.add(product_id)
        try:
            if status == "document":
                result.fragments.append({
                    "origin": "",
                    "html": f'<a href="{escape(pdf_url, quote=True)}">Terms and Conditions PDF</a>',
                    "url": page.url,
                    "product_id": product_id,
                })
                capture_indra_plan_document(
                    page, modal, result, product_id, pdf_url
                )
                return
            if status == "duplicate_product_identity":
                result.notes.append(
                    f"Indra detail action {index + 1} repeated product identity {product_id}"
                )
                return
        finally:
            close = modal.get_by_role("button", name="Close", exact=True)
            close.click()
            modal.wait_for(state="hidden", timeout=7000)
        if attempt == 1:
            # The supplier generates terms asynchronously. Reopen this public
            # details action once; never retry enrollment or submit user data.
            seen_product_ids.discard(product_id)

    result.notes.append(
        f"Indra plan {last_product_id or index + 1} document capture ended as {last_status} after 2 attempts"
    )


def capture_indra_plan_document(page, modal, result: NavigationResult,
                                product_id: str, pdf_url: str) -> None:
    """Capture the PDF response caused by Indra's visible modal link."""
    links = modal.locator("a[href]")
    action = None
    for link_index in range(links.count()):
        candidate = links.nth(link_index)
        if candidate.is_visible() and candidate.get_attribute("href") == pdf_url:
            action = candidate
            break
    if action is None:
        result.notes.append(
            f"Indra plan {product_id} generated a terms URL but no matching visible action"
        )
        return
    original_pages = set(page.context.pages)
    captured = {}

    def retain_clicked_response(route):
        # Intercept only the exact request initiated by the visible click so
        # the bytes are retained before Chromium hands the response to its PDF
        # viewer and navigates away from the network resource.
        response = route.fetch()
        captured["data"] = response.body()
        captured["url"] = response.url
        captured["content_type"] = response.headers.get("content-type", "")
        route.fulfill(response=response)

    try:
        page.context.route(pdf_url, retain_clicked_response, times=1)
        with page.context.expect_event(
            "response",
            predicate=lambda response, target=pdf_url: response.url == target,
            timeout=15000,
        ):
            action.evaluate("el => el.click()")
        data = captured.get("data", b"")
        content_type = captured.get("content_type", "")
        if not data.startswith(b"%PDF") and "pdf" not in content_type.casefold():
            result.notes.append(
                f"Indra plan {product_id} visible terms action returned non-PDF content"
            )
            return
        result.captured_documents.append({
            "url": captured.get("url") or pdf_url,
            "requested_url": pdf_url,
            "product_id": product_id,
            "label": "Terms and Conditions PDF",
            "content_type": content_type or "application/pdf",
            "data": data,
        })
    except Exception as exc:
        result.notes.append(
            f"Indra plan {product_id} visible terms action could not be captured: "
            f"{type(exc).__name__}: {str(exc)[:240]}"
        )
    finally:
        try:
            page.context.unroute(pdf_url, retain_clicked_response)
        except Exception:
            pass
        for opened in list(page.context.pages):
            if opened not in original_pages:
                try:
                    opened.close()
                except Exception:
                    pass


def strategy_indra_energy(page, query: Query) -> NavigationResult:
    start(page, query, f"https://indraenergy.com/signup/?zip={query.zip}")
    page.get_by_role("heading", name=re.compile(r"Select Your Utility|Choose Your Plan", re.I)).wait_for(timeout=20000)

    # Indra's rates API is authoritative for the offer fields, but its current
    # terms URL is created only after the public UI opens a plan-details modal.
    # Select the requested commodity/utility in that same UI before collecting
    # any generated document route.
    utility_group = page.locator(
        f'[x-show="store.availableUtilities.{query.commodity}.length > 0"]'
    )
    if utility_group.count():
        options = visible(utility_group.locator(".indra-utility-option"))
        matches = [option for option in options if utility_matches(option.inner_text(), query.utility)]
        if len(matches) != 1:
            raise UnsupportedContext(
                f"Requested Indra {query.commodity} utility is absent or ambiguous ({len(matches)} matches)"
            )
        matches[0].click()
    else:
        body = page.locator("body").inner_text()
        if not any(utility_matches(line, query.utility) for line in body.splitlines()):
            raise UnsupportedContext("Requested Indra utility is absent from the current ZIP response")

    plan_heading = "Electric Plans" if query.commodity == "electric" else "Natural Gas Plans"
    heading = page.get_by_role("heading", name=plan_heading, exact=True)
    if not heading.count() or not heading.first.is_visible():
        continue_actions = visible(page.get_by_role("button", name="Continue", exact=True))
        if len(continue_actions) != 1:
            raise NavigationError("Indra utility selection did not expose a unique Continue action")
        continue_actions[0].click()
    heading.first.wait_for(state="visible", timeout=15000)

    section = heading.first.locator("xpath=parent::*")
    detail_buttons = section.get_by_role("button", name="View Plan Details", exact=True)
    if not detail_buttons.count():
        raise NavigationError(f"Indra returned no {query.commodity} plan-detail actions")

    result = NavigationResult(
        context_verified=True,
        live_data_verified=True,
        notes=[
            "Indra browser flow verified the requested ZIP, commodity, and utility; offer fields originate from its public rates API",
        ],
    )
    controller = page.locator('[x-data="signupForm"]')
    seen_product_ids = set()
    for index in range(min(detail_buttons.count(), 20)):
        capture_indra_terms(
            page, controller, detail_buttons.nth(index), result, index, seen_product_ids
        )

    result.evidence["indra_terms"] = {
        "detail_action_count": detail_buttons.count(),
        "observed_product_ids": sorted(seen_product_ids),
        "document_product_ids": sorted({
            fragment["product_id"] for fragment in result.fragments
            if fragment.get("product_id")
        }),
    }

    result.html, result.url = page.content(), page.url
    return result


def strategy_smart_energy(page, query: Query) -> NavigationResult:
    if query.commodity != "electric":
        raise UnsupportedContext(
            "Smart Energy's current New Jersey shopping site publishes electricity offers only"
        )
    start(page, query)
    click_one(page, ['#modal-offer button[aria-label="Close"]'], optional=True)
    zip_input = page.locator("#home_zip")
    zip_input.wait_for(state="visible")
    form = zip_input.locator("xpath=ancestor::form[1]")
    zip_input.fill(query.zip)
    form.get_by_role("button", name=re.compile(r"view plans|get your plan", re.I)).click()
    page.wait_for_load_state("domcontentloaded")
    try:
        response = json.loads(page.locator("body").inner_text())
    except json.JSONDecodeError as exc:
        raise NavigationError("Smart Energy ZIP response was not valid JSON") from exc
    go_back = response.get("goback")
    if response.get("error") == "open_popup":
        popup = BeautifulSoup(response.get("popup", {}).get("contents", ""), "lxml")
        matches = []
        for radio in popup.select('input[type="radio"][name="ldc"]'):
            container = radio.find_parent(["label", "li", "div"]) or radio.parent
            if utility_matches(container.get_text(" ", strip=True), query.utility):
                matches.append(radio.get("value"))
        if len(matches) != 1:
            raise NavigationError(f"Smart Energy utility selection is absent or ambiguous ({len(matches)} matches)")
        selection = page.request.post(
            urljoin(page.url, "?act=ldc_zip"),
            form={"ldc": matches[0], "fm_wrap": "#signup_new_ldc__1", "_wpcf7": "1"},
        )
        if not selection.ok:
            raise SourceUnavailable(f"Smart Energy utility selection returned HTTP {selection.status}")
        try:
            selected = selection.json()
            go_back = selected.get("goback") or go_back
        except Exception:
            pass
    elif response.get("status") != "submitted":
        raise NavigationError(f"Unexpected Smart Energy ZIP response: {response.get('error') or response.get('status')}")
    if not go_back:
        raise NavigationError("Smart Energy did not provide a public plan destination")
    page.goto(go_back, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_function("document.body && document.body.innerText.trim().length > 100", timeout=20000)
    return NavigationResult(html=page.content(), url=page.url, context_verified=True,
                            live_data_verified=True,
                            notes=["ZIP and electric utility were selected through Smart Energy's public form endpoints"])


def strategy_alpha_gas_and_electric(page, query: Query) -> NavigationResult:
    if query.commodity != "electric" or query.utility != "ACE Electric":
        raise UnsupportedContext("Alpha baseline currently covers its master-list ACE electric market only")
    start(page, query, "https://alphagasandelectric.com/new-jersey-pricing/")
    page.locator('a[href*="New_Jersey_Pricing"][href$=".pdf"]').first.wait_for(state="attached")
    pdf_url = page.locator('a[href*="New_Jersey_Pricing"][href$=".pdf"]').first.get_attribute("href")
    response = page.request.get(pdf_url)
    if not response.ok:
        raise SourceUnavailable(f"Alpha public New Jersey rate sheet returned HTTP {response.status}")
    with pdfplumber.open(io.BytesIO(response.body())) as pdf:
        text = "\n".join(pdf_page.extract_text() or "" for pdf_page in pdf.pages)
    return NavigationResult(
        html=page.content(),
        url=page.url,
        context_verified=False,
        live_data_verified=False,
        disposition="unsupported",
        notes=["Alpha's public New Jersey price source is a sheet dated 2025-01-15; it is retained as evidence but cannot produce a current offer"],
    )


def wait_for_provider_options(page, selector: str, timeout: int = 15000) -> None:
    """Wait for an asynchronously populated provider select, not just its shell."""
    page.wait_for_function(
        "selector => { const select=document.querySelector(selector); "
        "return select && Array.from(select.options).filter(option => "
        "(option.textContent || '').trim()).length > 1; }",
        arg=selector,
        timeout=timeout,
    )


def strategy_american_power_and_gas(page, query: Query) -> NavigationResult:
    if query.commodity != "gas":
        raise UnsupportedContext("American Power & Gas currently supports public New Jersey gas shopping only")
    # A supplier location must be supplied to the public address autocomplete;
    # use a public utility customer-service location, never a customer's address.
    public_service_addresses = {
        "PSE&G Gas": "80 Park Plaza, Newark, NJ 07102",
    }
    address = public_service_addresses.get(query.utility)
    if not address:
        raise UnsupportedContext(
            "American Power & Gas's current public provider selector does not list the requested gas utility"
        )

    start(page, query, "https://apgpublicsite.azurewebsites.net/locations/new-jersey")
    page.locator("#addressInput").first.wait_for(state="attached", timeout=20000)
    address_inputs = visible(page.locator("#addressInput"))
    if len(address_inputs) != 1:
        raise NavigationError(f"American Power & Gas address input is absent or ambiguous ({len(address_inputs)} visible)")
    address_input = address_inputs[0]
    address_input.fill("")
    address_input.press_sequentially(address, delay=25)
    page.wait_for_function(
        "zip => Array.from(document.querySelectorAll(\"[id^='address-suggestion-']\"))"
        ".some(item => item.offsetParent !== null && item.innerText.includes(zip))",
        arg=query.zip,
        timeout=15000,
    )
    suggestions = [item for item in visible(page.locator("[id^='address-suggestion-']"))
                   if query.zip in item.inner_text()]
    if not suggestions:
        raise NavigationError("American Power & Gas did not return an address suggestion for the requested ZIP")
    # The autocomplete may return several normalized variants in the same ZIP;
    # the first result is the supplier's canonical match for the entered address.
    suggestions[0].click()
    page.wait_for_function(
        "() => Array.from(document.querySelectorAll('button')).some(button => "
        "button.offsetParent !== null && button.innerText.trim() === 'Find Plans')",
        timeout=10000,
    )
    find_buttons = visible(page.get_by_role("button", name="Find Plans", exact=True))
    if not find_buttons:
        raise NavigationError("American Power & Gas Find Plans action is absent")
    find_buttons[0].click()
    page.wait_for_url("**/enrollment/plans", wait_until="domcontentloaded", timeout=30000)

    # The selected autocomplete suggestion is the ZIP qualification evidence.
    # The current enrollment page no longer repeats that ZIP in visible body
    # text, so re-checking body text here incorrectly rejects a valid flow.
    # Continue by independently verifying the requested provider in the
    # address-derived selector before collecting any plan.
    page.locator("#gas-provider").first.wait_for(state="attached", timeout=15000)
    wait_for_provider_options(page, "#gas-provider")
    gas_providers = visible(page.locator("#gas-provider"))
    if len(gas_providers) != 1:
        raise NavigationError(f"American Power & Gas gas provider selector is absent or ambiguous ({len(gas_providers)} visible)")
    gas_provider = gas_providers[0]
    labels = gas_provider.locator("option").all_text_contents()
    matches = [label for label in labels if utility_matches(label, query.utility)]
    if len(matches) != 1:
        raise UnsupportedContext(
            "American Power & Gas's current public provider selector does not list the requested gas utility"
        )
    gas_provider.select_option(label=matches[0])
    residential = visible(page.locator("#residential"))
    if len(residential) == 1 and not residential[0].is_checked():
        residential[0].check()
    gas_buttons = visible(page.get_by_role("button", name="Gas Plans", exact=True))
    if not gas_buttons:
        raise NavigationError("American Power & Gas Gas Plans action is absent")
    gas_buttons[0].click()
    page.wait_for_function(
        "() => { const plans = document.querySelector('#plans-scroller'); "
        "return plans && /therms?/i.test(plans.innerText); }",
        timeout=15000,
    )
    page.locator("#plans-scroller .plan-item").first.wait_for(state="visible", timeout=15000)
    html = page.content()
    plan_html = page.locator("#plans-scroller").inner_html()
    notes = [
        "Current residential gas plans collected through the supplier's public address-qualified shopping flow",
        f"Selected public autocomplete suggestion explicitly matched service ZIP {query.zip}",
        "The test input is PSE&G's public Newark customer-service address; no private customer address was used",
    ]
    if not re.search(r"contract|terms.{0,8}(?:service|conditions)|disclosure|\.pdf", plan_html, re.I):
        notes.append(
            "The current selected plan card exposes no plan-connected contract, terms, disclosure, or PDF route; site-wide Terms of Use is not treated as a supply contract"
        )
    return NavigationResult(
        html=html,
        url=page.url,
        context_verified=True,
        live_data_verified=True,
        notes=notes,
    )


def strategy_clearview_energy(page, query: Query) -> NavigationResult:
    start(page, query)
    forms = visible(page.locator("form.zipform"))
    if not forms:
        raise NavigationError("Clearview residential ZIP form is absent")
    # The responsive page currently renders equivalent desktop and mobile
    # forms. Either submits the same public /ZipcodeLookup request.
    form = forms[0]
    form.locator('input[name="zip"]').fill(query.zip)
    # Clearview removed its old #resi/BtnActType control in September 2026.
    # The ZIP result now contains both commodities and tags every product with
    # data-type/data-utilname, which the offline parser scopes below.
    residential = form.locator('#resi, input[name="BtnActType"]')
    if residential.count():
        residential.first.check()
    form.locator('button[type="submit"]').click()
    page.wait_for_load_state("domcontentloaded")
    context_verified = utility_matches(page.locator("body").inner_text(), query.utility)
    return NavigationResult(html=page.content(), url=page.url,
                            context_verified=context_verified, live_data_verified=context_verified)


def strategy_idt_energy(page, query: Query) -> NavigationResult:
    start(page, query, "https://idtenergy.com/get-started/")
    forms = [form for form in visible(page.locator("form#gform_68"))
             if form.locator("#input_68_2").count()]
    if len(forms) != 1:
        raise NavigationError(f"IDT public offer form is absent or ambiguous ({len(forms)} matches)")
    form = forms[0]
    commodity_choice = "choice_68_1_0" if query.commodity == "electric" else "choice_68_1_1"
    form.locator(f'label[for="{commodity_choice}"]').click()
    form.locator("#input_68_2").fill(query.zip)
    form.locator("#gform_submit_button_68").click(no_wait_after=True)
    try:
        page.wait_for_url(lambda url: "get-started" not in url or "find-your-offer" in url,
                          wait_until="domcontentloaded", timeout=20000)
    except PlaywrightTimeoutError:
        page.locator("body").wait_for(state="attached")
    utility_form = page.locator("form#gform_69")
    utility_form.wait_for(state="attached", timeout=15000)
    choices = []
    for select in visible(utility_form.locator("select")):
        options = select.locator("option").all_text_contents()
        matches = [label for label in options if utility_matches(label, query.utility)]
        if len(matches) == 1:
            choices.append((select, matches[0]))
    if len(choices) != 1:
        raise NavigationError(f"IDT utility selection is absent or ambiguous ({len(choices)} matches)")
    choices[0][0].select_option(label=choices[0][1])
    utility_form.locator("#gform_submit_button_69").click(no_wait_after=True)
    try:
        page.wait_for_url(lambda url: "/your-utility/" not in url,
                          wait_until="domcontentloaded", timeout=20000)
    except PlaywrightTimeoutError:
        page.locator("body").wait_for(state="attached")
    context_verified = utility_matches(page.locator("body").inner_text(), query.utility)
    return NavigationResult(html=page.content(), url=page.url,
                            context_verified=context_verified, live_data_verified=context_verified)


def strategy_cleansky_energy(page, query: Query) -> NavigationResult:
    start(page, query, f"https://enroll.cleanskyenergy.com/?customerTypeId=7&zipcode={query.zip}")
    click_one(page, ["#CybotCookiebotDialogBodyButtonDecline", "#CybotCookiebotDialogBodyButtonAccept"], optional=True)
    button = page.locator("#btnHome")
    modal = page.locator("#UtilityModel")
    try:
        modal.first.wait_for(state="visible", timeout=5000)
    except PlaywrightTimeoutError:
        pass
    if not (modal.count() and modal.first.is_visible()) and button.count() and button.first.is_visible():
        loader = page.locator("#divLoader")
        try:
            loader.wait_for(state="hidden", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        # The modal can begin animating between the visibility check and a
        # pointer click. Invoke the button's ordinary click handler directly
        # so its own overlay cannot race and intercept the pointer.
        button.first.evaluate("el => el.click()")
    page.locator("#DivElectricityUtility, #DivGasUtility").first.wait_for(state="visible", timeout=20000)

    requested_selector = "#DivElectricityUtility" if query.commodity == "electric" else "#DivGasUtility"
    other_selector = "#DivGasUtility" if query.commodity == "electric" else "#DivElectricityUtility"

    def select_label(container_selector, predicate):
        container = page.locator(container_selector)
        labels = container.locator("label")
        matches = []
        for index in range(labels.count()):
            label = labels.nth(index)
            text = label.inner_text().strip()
            if predicate(text):
                matches.append(label)
        if len(matches) != 1:
            raise UnsupportedContext(
                f"CleanSky utility choice unavailable or ambiguous in {query.zip}: {query.utility} ({len(matches)} matches)"
            )
        matches[0].click()

    select_label(requested_selector, lambda text: utility_matches(text, query.utility))
    select_label(other_selector, lambda text: bool(re.search(r"not interested|none", text, re.I)))
    # Cookiebot can animate back over the page after the utility modal is
    # completed. Invoke the site's own handler so that late overlay timing
    # cannot intercept an otherwise valid public selection.
    page.locator("#BtnSeeAllPlans").evaluate("el => el.click()")
    cards = page.locator('[id^="PlanDiv_"][data-productid]')
    try:
        cards.first.wait_for(state="attached", timeout=30000)
    except PlaywrightTimeoutError:
        body = page.locator("body").inner_text()
        if re.search(r"no (?:plans|products|offers)|not available", body, re.I):
            return NavigationResult(html=page.content(), url=page.url, context_verified=True, live_data_verified=True,
                                    disposition="empty", notes=["CleanSky explicitly returned no plans"])
        raise
    return NavigationResult(html=page.content(), url=page.url, context_verified=True, live_data_verified=True,
                            notes=["ZIP, commodity and utility selected in the public CleanSky enrollment flow"])


def strategy_residents_energy(page, query: Query) -> NavigationResult:
    if query.commodity != "gas":
        raise UnsupportedContext("Residents baseline currently supports natural-gas offers only")
    start(page, query, "https://residentsenergy.com/new-jersey-price-comparison/")
    body = page.locator("body")
    body.get_by_text("NJ Natural Gas ResiSURE Price Comparison", exact=False).first.wait_for(state="attached")
    text = body.inner_text()
    if not utility_matches(text, query.utility):
        raise UnsupportedContext("Residents comparison page does not list the requested gas utility")
    return NavigationResult(html=page.content(), url=page.url, context_verified=True,
                            notes=["Public New Jersey fixed-rate comparison table; not ZIP-specific enrollment validation"])


def strategy_eligo_energy(page, query: Query) -> NavigationResult:
    supported_utilities = {"NJNG Gas", "PSE&G Gas"}
    if query.commodity != "gas" or query.utility not in supported_utilities:
        raise UnsupportedContext("Eligo baseline currently supports verified NJNG and PSE&G gas routes only")
    start(page, query, "https://www.eligoenergy.com/")
    form = page.locator('form[action="/find_service_zones"]:visible').first
    form.wait_for(state="visible", timeout=15000)
    form.locator("label", has_text="Gas").click()
    form.locator('input[name="lead[zip]"]').fill(query.zip)
    form.locator('input[type="submit"]').click()
    page.wait_for_load_state("domcontentloaded")
    page.locator(".flow-result-card").first.wait_for(state="attached", timeout=20000)
    html = page.content()
    expected_route = f"/rates/{query.zip}"
    context_verified = expected_route in page.url and utility_matches(html, query.utility)
    if not context_verified:
        raise NavigationError("Eligo ZIP flow did not resolve to the requested gas utility")
    return finish(page, NavigationResult(
        context_verified=True,
        live_data_verified=True,
        notes=["ZIP submitted through the official Eligo gas-rate form and resulting utility verified"],
    ), ".flow-result-card")


def submit_nextera_zip(page, zip_code: str) -> None:
    """Submit NextEra's public ZIP form despite its occasionally stale button state."""
    zipcode = page.locator("#Zipcode")
    zipcode.wait_for(state="visible")
    zipcode.fill("")
    # This legacy page normally enables Continue from key events.  It has also
    # been observed leaving the button disabled even after a valid five-digit
    # value, so replay the complete ordinary field lifecycle before falling
    # back to standards-based form submission.
    zipcode.press_sequentially(zip_code)
    zipcode.press("Tab")
    zipcode.evaluate(
        """(element) => {
            for (const type of ['input', 'change', 'blur']) {
                element.dispatchEvent(new Event(type, {bubbles: true}));
            }
            element.dispatchEvent(new KeyboardEvent('keyup', {
                key: '0', code: 'Digit0', keyCode: 48, which: 48, bubbles: true
            }));
        }"""
    )
    submit = page.locator("#btnZipCode")
    try:
        page.wait_for_function(
            "() => { const button = document.querySelector('#btnZipCode'); "
            "return button && !button.disabled; }",
            timeout=4000,
        )
    except PlaywrightTimeoutError:
        # Keep the value assignment and the site's normal submit-button click
        # in one browser task. The button's legacy click handler populates the
        # utility-choice modal before the final /Plans/ViewPlans submission;
        # calling requestSubmit() directly skips that qualification step.
        # Only the stale disabled presentation state is repaired.
        page.locator('form[action="/Plans/ViewPlans"]').evaluate(
            "(form, zip) => {"
            "const field=form.querySelector('#Zipcode');"
            "const button=form.querySelector('#btnZipCode');"
            "if (!field || !button || !/^\\d{5}$/.test(zip)) "
            "throw new Error('NextEra ZIP form is incomplete');"
            "const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;"
            "setter.call(field,zip);"
            "for (const type of ['input','keyup','change','blur']) "
            "field.dispatchEvent(new Event(type,{bubbles:true}));"
            "if (field.value !== zip || !field.checkValidity()) "
            "throw new Error('NextEra ZIP did not pass native validation');"
            "button.disabled=false;"
            "button.classList.remove('not-allowed');"
            "button.click();"
            "}",
            zip_code,
        )
    else:
        submit.click()


def strategy_nextera_energy_services(page, query: Query) -> NavigationResult:
    if query.commodity != "electric":
        raise UnsupportedContext("NextEra residential shopping page advertises electricity only")
    start(page, query, "https://signup.nexteraenergyservices.com/")
    submit_nextera_zip(page, query.zip)
    page.locator('input[type="radio"]').first.wait_for(state="attached", timeout=15000)
    labels = page.locator("label")
    matches = []
    for index in range(labels.count()):
        label = labels.nth(index)
        if label.is_visible() and utility_matches(label.inner_text(), query.utility):
            matches.append(label)
    if len(matches) != 1:
        raise UnsupportedContext(f"NextEra utility choice unavailable or ambiguous: {query.utility}")
    matches[0].click()
    page.locator("#btnSubmit").click(no_wait_after=True)
    try:
        page.locator(".pricing_plan_item.plan_card").first.wait_for(state="attached", timeout=30000)
    except PlaywrightTimeoutError:
        page.locator("body").wait_for(state="attached")
    html = page.content()
    if reason := access_failure(html):
        raise SourceUnavailable(reason)
    text = page.locator("body").inner_text()
    if "do not provide retail electricity service in your area" in text.lower():
        raise UnsupportedContext("NextEra explicitly reports that the configured ZIP is not served")
    if "do not currently have an offer available for web enrollment in your area" in text.lower():
        return NavigationResult(html=html, url=page.url, context_verified=True, live_data_verified=True, disposition="empty",
                                notes=["NextEra explicitly reports no web-enrollment offer for the configured ZIP"])
    context_verified = utility_matches(text, query.utility)
    identities = nextera_plan_identities(html) if context_verified else []
    result = NavigationResult(
        context_verified=context_verified,
        live_data_verified=context_verified,
        notes=[
            "ZIP submitted to NextEra public residential enrollment flow",
            f"NextEra rendered {len(identities)} uniquely identified current plan(s)",
        ],
    )
    if context_verified:
        capture_nextera_details(page, result, identities)
    result.html, result.url = page.content(), page.url
    return result


def strategy_njgande(page, query: Query) -> NavigationResult:
    start(page, query, "https://www.njgande.com/rate-plans")
    gateway_recovered = recover_njgande_gateway(page)
    click_one(page, ['button:has-text("Decline")', 'button:has-text("Reject")',
                     'button[aria-label="Close"]', '.modal button.close'], optional=True)
    home = page.locator("#home")
    if home.count() and not home.is_checked():
        page.locator('label[for="home"]').click()
    zip_inputs = visible(page.locator('input[type="text"], input[type="tel"]'))
    if len(zip_inputs) != 1:
        zip_inputs = [item for item in zip_inputs if re.search(
            r"zip|postal",
            " ".join(filter(None, [item.get_attribute("name"), item.get_attribute("id"),
                                   item.get_attribute("placeholder"), item.get_attribute("aria-label")])),
            re.I,
        )]
    if len(zip_inputs) != 1:
        raise NavigationError(f"NJG&E ZIP input is absent or ambiguous ({len(zip_inputs)} matches)")
    zip_inputs[0].fill(query.zip)
    page.locator("#search-plans-btn").click()
    confirm = page.locator("#pre-confirmation-btn")
    confirm.wait_for(state="visible", timeout=20000)
    confirmation_text = page.locator("body").inner_text()
    if not utility_matches(confirmation_text, query.utility):
        raise UnsupportedContext(f"NJG&E did not offer requested utility for ZIP {query.zip}: {query.utility}")
    confirm.click(no_wait_after=True)
    page.wait_for_url(re.compile(r"Shop-for-Plans-(?:Gas|Electricity)"), timeout=30000)
    if query.commodity == "electric" and "Shop-for-Plans-Gas" in page.url:
        # Dual-commodity ZIPs land on gas first. The site's Back control carries
        # the public, session-qualified electricity URL; follow that route
        # instead of parsing gas cards under an electric registry entry.
        back = page.locator("#backButton")
        back.wait_for(state="attached", timeout=20000)
        electricity_url = back.get_attribute("data-outboundurl")
        if not electricity_url or "Shop-for-Plans-Electricity" not in electricity_url:
            raise NavigationError("NJG&E did not expose the expected public electricity route")
        page.goto(urljoin(page.url, electricity_url), wait_until="commit", timeout=30000)
        utility_modal = page.locator('.modal.show:has-text("Select Utility")').first
        utility_modal.wait_for(state="visible", timeout=20000)
        matching_labels = [
            label for label in utility_modal.locator("label.form-check-label").all()
            if utility_matches(label.inner_text(), query.utility)
        ]
        if len(matching_labels) != 1:
            raise UnsupportedContext(
                f"NJG&E electricity utility selection was absent or ambiguous for {query.utility}"
            )
        matching_labels[0].click()
        submit = utility_modal.get_by_role("button", name="Submit", exact=True)
        submit.click(no_wait_after=True)
    page.locator(".ds_plan_item.item_v1").first.wait_for(state="attached", timeout=30000)
    text = page.locator("body").inner_text()
    context_verified = utility_matches(text, query.utility)
    notes = ["ZIP and preselected utility confirmed in NJG&E public rate flow"]
    if gateway_recovered:
        notes.append("Recovered the exact NJG&E public page after a transient Azure Front Door timeout")
    return NavigationResult(html=page.content(), url=page.url,
                            context_verified=context_verified, live_data_verified=context_verified,
                            notes=notes)


def strategy_green_mountain_energy(page, query: Query) -> NavigationResult:
    start(page, query)
    form = page.locator("form#planlookupForm").first
    form.wait_for(state="visible")
    form.locator('input[name="zipcode"]').fill(query.zip)
    form.get_by_role("button", name="View Plans", exact=True).click()
    page.wait_for_load_state("domcontentloaded")
    try:
        page.locator("#gatsby-focus-wrapper > *").first.wait_for(state="attached", timeout=20000)
    except PlaywrightTimeoutError:
        # The Northeast application occasionally returns an empty Gatsby shell
        # on its first navigation. Retry once; do not infer an empty market.
        page.reload(wait_until="domcontentloaded", timeout=30000)
        page.locator("#gatsby-focus-wrapper > *").first.wait_for(state="attached", timeout=30000)
    page.wait_for_function(
        "!document.querySelector('[data-testid=\"loader-set\"]') || "
        "getComputedStyle(document.querySelector('[data-testid=\"loader-set\"]')).display === 'none'",
        timeout=30000,
    )
    if "zip-code-not-served" in page.url:
        return NavigationResult(html=page.content(), url=page.url, context_verified=True, live_data_verified=True,
                                disposition="unsupported",
                                notes=["Green Mountain explicitly reports that the configured Rockland ZIP is not served"])
    context_verified = utility_matches(page.locator("body").inner_text(), query.utility)
    return NavigationResult(html=page.content(), url=page.url,
                            context_verified=context_verified, live_data_verified=context_verified)


def strategy_great_american(page, query: Query) -> NavigationResult:
    start(page, query)
    form = page.locator("form#gform_13")
    form.locator('label[for="choice_13_8_0"]').click()
    form.locator("#input_13_1").evaluate(
        "(el, value) => { el.value = value; el.dispatchEvent(new Event('change', {bubbles: true})); }",
        query.zip,
    )
    for index, digit in enumerate(query.zip, 1):
        field = form.locator(f"#zip{index}")
        if field.count():
            field.fill(digit)
    if query.utility != "PSE&G Electric":
        raise UnsupportedContext("Great American baseline currently supports PSE&G Electric only")
    # The logo grid is a decorative mirror of this real form control and is
    # frequently hidden by the supplier's own CSS. Update the underlying
    # public field and emit the same change event as the grid's JavaScript.
    form.locator("#input_13_25").evaluate(
        "el => { el.value = 'pseg'; el.dispatchEvent(new Event('change', {bubbles: true})); }"
    )
    form.locator("#gform_next_button_13_3").click()
    page.locator("#gform_page_13_2").wait_for(state="visible", timeout=20000)
    unavailable = form.locator("#field_13_86")
    if unavailable.count() and "do not currently have any products" in unavailable.inner_text().lower():
        return NavigationResult(html=page.content(), url=page.url, context_verified=True, live_data_verified=True,
                                disposition="empty",
                                notes=["Great American explicitly reports no products for the configured PSE&G ZIP"])
    page.locator("#priceTickets").wait_for(state="visible", timeout=15000)
    return NavigationResult(html=page.content(), url=page.url, context_verified=True, live_data_verified=True)


def access_failure(html: str) -> str | None:
    """Identify provider/CDN failure pages before they resemble empty markets."""
    text = BeautifulSoup(html or "", "lxml").get_text(" ", strip=True)
    if re.search(r"HTTP Error 503|Service Unavailable", text, re.I):
        return "Supplier enrollment service returned HTTP 503"
    if re.search(r"403 ERROR|request (?:was )?blocked|could not be satisfied", text, re.I):
        return "Supplier enrollment service returned an access-block page"
    if re.search(r"Request unsuccessful|Incapsula incident ID|Incapsula error", text, re.I):
        return "Supplier enrollment service returned an Incapsula access-block page"
    return None


def strategy_frontier(page, query: Query) -> NavigationResult:
    # Follow Frontier's current New Jersey homepage ZIP form. The enrollment
    # result opens in a new tab and may redirect to the separate portal host.
    start(page, query, "https://www.frontierutilities.com/new-jersey")
    zipcode = page.get_by_role("textbox", name="Enter your zip code", exact=True)
    zipcode.wait_for(state="visible", timeout=15000)
    zipcode.fill("")
    zipcode.press_sequentially(query.zip)
    with page.expect_popup(timeout=15000) as popup_info:
        page.get_by_role("button", name="View Plans", exact=True).click()
    plan_page = popup_info.value
    try:
        plan_page.wait_for_url("**/Enrollment/**", wait_until="domcontentloaded", timeout=20000)
    except PlaywrightTimeoutError:
        plan_page.wait_for_load_state("domcontentloaded")
    html = plan_page.content()
    if reason := access_failure(html):
        raise SourceUnavailable(reason)
    return finish(plan_page, NavigationResult(notes=["ZIP submitted through Frontier's public New Jersey homepage; utility/commodity context still requires verification"]),
                  '.product-card, .plan-card, [data-product-id], [ng-repeat*="product" i]')


def strategy_cleanchoice(page, query: Query) -> NavigationResult:
    if query.commodity != "electric":
        raise UnsupportedContext("CleanChoice public New Jersey flow offers electricity only")
    start(page, query, f"https://cleanchoiceenergy.com/plans?area={query.zip}")
    html = page.content()
    if reason := access_failure(html):
        raise SourceUnavailable(reason)
    page.locator('button[data-testid="select-plan-button"]').first.wait_for(state="attached", timeout=30000)
    html = page.content()
    if reason := access_failure(html):
        raise SourceUnavailable(reason)
    text = page.locator("body").inner_text()
    context_verified = query.zip in text and utility_matches(text, query.utility)
    return NavigationResult(html=html, url=page.url,
                            context_verified=context_verified, live_data_verified=context_verified,
                            notes=["Direct public plan route verified against displayed ZIP and utility"])


STRATEGIES = {name.removeprefix("strategy_"): value for name, value in list(globals().items()) if name.startswith("strategy_")}
