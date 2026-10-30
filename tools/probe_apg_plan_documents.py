"""Safely inspect AP&G's public plan-selection transition for connected documents.

The probe uses PSE&G's public Newark service-center address and stops immediately
after selecting the displayed gas plan.  It never enters customer information or
submits an enrollment application.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import Response, sync_playwright


PUBLIC_ADDRESS = "80 Park Plaza, Newark, NJ 07102"
START_URL = "https://apgpublicsite.azurewebsites.net/locations/new-jersey"
DOCUMENT_WORDS = re.compile(r"contract|terms|disclosure|agreement|\.pdf(?:$|[?#])", re.I)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--channel", default="chrome", choices=("chrome", "msedge", "chromium"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    interesting_responses: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser_type = playwright.chromium
        launch_args: dict[str, object] = {"headless": args.headless}
        if args.channel != "chromium":
            launch_args["channel"] = args.channel
        browser = browser_type.launch(**launch_args)
        context = browser.new_context()
        page = context.new_page()

        def retain_response(response: Response) -> None:
            content_type = response.headers.get("content-type", "")
            if DOCUMENT_WORDS.search(response.url) or "application/pdf" in content_type.lower():
                interesting_responses.append(
                    {
                        "url": response.url,
                        "status": response.status,
                        "content_type": content_type,
                    }
                )

        page.on("response", retain_response)
        page.goto(START_URL, wait_until="domcontentloaded", timeout=30_000)
        # The responsive layout keeps desktop and mobile controls in the DOM;
        # interact only with the currently visible instance.
        address = page.locator("#addressInput:visible").first
        address.wait_for(state="visible", timeout=20_000)
        address.press_sequentially(PUBLIC_ADDRESS, delay=25)
        page.wait_for_function(
            "() => Array.from(document.querySelectorAll(\"[id^='address-suggestion-']\"))"
            ".some(node => node.offsetParent !== null && node.innerText.includes('07102'))",
            timeout=15_000,
        )
        page.locator("[id^='address-suggestion-']").filter(has_text="07102").first.click()
        page.get_by_role("button", name="Find Plans", exact=True).click()
        page.wait_for_url("**/enrollment/plans", wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_function(
            "() => { const s=document.querySelector('#gas-provider'); "
            "return s && Array.from(s.options).filter(o => (o.textContent || '').trim()).length > 1; }",
            timeout=15_000,
        )
        provider = page.locator("#gas-provider:visible").first
        labels = provider.locator("option").all_text_contents()
        pse_label = next(
            label
            for label in labels
            if re.search(r"PSE|PUBLIC\s+SERVICE", label, re.I)
        )
        provider.select_option(label=pse_label)
        residential = page.locator("#residential")
        if residential.count() == 1 and not residential.is_checked():
            residential.check()
        page.get_by_role("button", name="Gas Plans", exact=True).click()
        plan = page.locator("#plans-scroller .plan-item").first
        plan.wait_for(state="visible", timeout=15_000)
        preselection_html = page.content()
        preselection_url = page.url
        selected_plan_text = plan.inner_text().strip()
        plan.get_by_role("button", name="Select Plan", exact=True).click()
        page.wait_for_timeout(2_000)
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            # Blazor circuits may retain an open connection; rendered state is
            # still the evidence needed by this bounded probe.
            pass

        postselection_html = page.content()
        postselection_url = page.url
        page.get_by_role("button", name="Next: Contact Info", exact=True).click()
        page.wait_for_timeout(1_500)
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        contact_page_html = page.content()
        links: list[dict[str, str]] = []
        for item in page.locator("a[href]").all():
            href = item.get_attribute("href") or ""
            text = item.inner_text().strip()
            absolute = urljoin(page.url, href)
            if DOCUMENT_WORDS.search(f"{text} {absolute}"):
                links.append({"text": text, "url": absolute})

        evidence = {
            "public_address": PUBLIC_ADDRESS,
            "preselection_url": preselection_url,
            "postselection_url": postselection_url,
            "contact_page_url": page.url,
            "selected_plan_text": selected_plan_text,
            "document_like_links_after_selection": links,
            "document_like_responses": interesting_responses,
            "stopped_before_customer_information_submission": True,
        }
        (args.output / "preselection.html").write_text(preselection_html, encoding="utf-8")
        (args.output / "postselection.html").write_text(postselection_html, encoding="utf-8")
        (args.output / "contact-page.html").write_text(contact_page_html, encoding="utf-8")
        (args.output / "evidence.json").write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        browser.close()

    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
