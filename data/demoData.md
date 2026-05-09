# NJ Switch Pipeline — Demo Results
**Utility:** PSE&G Electric | **Zip:** 07102 | **Date scraped:** 2026-05-01  
**Total rows in CSV:** 36 | **Suppliers scraped:** 7

> Row counts: each supplier contributes both plan rows (from HTML) and contract rows (from PDF/page).  
> "Plans" = HTML-parsed plan cards. "Contracts" = `contract_summary_pdf` rows scraped separately.

---

## Summary Table

| Supplier | Plan Rows | Contract Rows | Total CSV Rows | Status |
|---|---|---|---|---|
| Constellation Energy | 3 | 3 | 6 | ✅ Full |
| Direct Energy | 5 | 0 | 5 | ✅ Plans only (blank contract PDFs) |
| Ambit Energy | 4 | 0 | 4 | ✅ All terms correct |
| Think Energy | 1 | 1 | 2 | ✅ Full |
| NRG | 0 | 0 | 0 | ❌ No plans returned |
| Major Energy | 4 | 4 | 8 | ✅ Full |
| Xoom Energy | 5 | 6 | 11 | ✅ Full |

---

## Constellation Energy
**Status:** ✅ 3 plans + 3 contract PDFs  
**Source:** `constellationrates.com/state/new-jersey/`  
**Parser:** `_parse_constellation_divs()` (div card mode)

| Plan Name | Rate (¢/kWh) | Term | Type | Contract PDF |
|---|---|---|---|---|
| 6 Month Power Plan | 21.59 | 6 mo | Fixed | [T&C](https://s3.amazonaws.com/origin.static.ptsrvs.com/terms_and_conditions/CONSTEL_RATES/PSEAG/7897-tandc.pdf) |
| 18 Month Power Plan | 23.59 | 18 mo | Fixed | [T&C](https://s3.amazonaws.com/origin.static.ptsrvs.com/terms_and_conditions/CONSTEL_RATES/PSEAG/8564-tandc.pdf) |
| 12 Month Power Plan | 24.49 | 12 mo | Fixed | [T&C](https://s3.amazonaws.com/origin.static.ptsrvs.com/terms_and_conditions/CONSTEL_RATES/PSEAG/3906-tandc.pdf) |

---

## Direct Energy
**Status:** ✅ 5 plans (no contract rows)  
**Source:** `directenergy.com/new-jersey`  
**Parser:** `_parse_direct_energy_cards()` (commodity-filtered `.product-card`)  
**Note:** Contract PDFs (`RatePlanSummary.aspx`) are blank server-side templates with no embedded rate data.

| Plan Name | Rate (¢/kWh) | Term | Type |
|---|---|---|---|
| Live Brighter® 6 | 20.09 | 6 mo | Fixed |
| Live Brighter® 12 | 22.69 | 12 mo | Fixed |
| Live Brighter® 18 | 22.49 | 18 mo | Fixed |
| Live Brighter® 24 | 23.19 | 24 mo | Fixed |
| Go Green Lights 24 | 24.89 | 24 mo | Fixed |

---

## Ambit Energy
**Status:** ✅ 4 plans; all terms correctly parsed  
**Source:** `customer.ambitenergy.com/servicearea`  
**Parser:** Inline popup parser — each `View Plan Info` ngDialog opened, parsed with BeautifulSoup, closed (Escape), then next. Fresh locator re-query each iteration handles AngularJS DOM re-renders. Strategy returns `(None, plan_rows)`; `demo_test.py` now emits `pdf_rows` even when `html=None`.  
**Note:** Each plan card has two `View Plan Info` links (desktop + mobile); only the visible even-indexed link succeeds per plan — odd-indexed failures are expected.

| Plan Name | Rate (¢/kWh) | Term | Type |
|---|---|---|---|
| Winter Break 24 | 25.99 | 24 mo | Variable |
| Winter Break 12 | 25.49 | 12 mo | Variable |
| Ultimate Perks 12 | 21.69 | 12 mo | Fixed |
| Garden State Select 12 Month Term | 21.19 | 12 mo | Variable |

---

## Think Energy
**Status:** ✅ 1 plan + 1 contract summary PDF  
**Source:** `thinkenergy.com/home-nj/`  
**Parser:** `_parse_think_energy_cards()` + `extract_contract_summaries()`  
**Note:** CookieYes banner dismissed before zip fill; page uses `<input type="submit">` (not `<button>`).

| Plan Name | Rate (¢/kWh) | Term | Type | Contract PDF |
|---|---|---|---|---|
| Think Clean 12 | 19.90 | 12 mo | Fixed | [Contract Summary](https://api.thinkenergy.onproton.io/enrollment/document?template_bucket=thinkenergy-product-templates&template_file=nj/CS_NJ.docx&commodity_rate=0.199000&term_months=12&rate_id=234597) |

---

## NRG
**Status:** ❌ 0 plans — commodity + utility modals navigated but plan cards do not render  
**Source:** NRG residential shopping page  
**Debug file:** `src/scraper/debug/NRG__ZERO_PLANS.html`  
**Known blocker:** `#commodityModalWindow` checkbox requires JS `.click()` to register; `#goToutilityModal` button stays disabled. Utility modal navigation added but product chart still not loading. Deferred — fix after Ambit backlog cleared.

---

## Major Energy
**Status:** ✅ 4 plans + 4 contract PDFs (Terms of Service)  
**Source:** `majorenergy.com/areas/nj/`  
**Parser:** `_parse_major_energy_cards()` (dollar-per-kWh normalised to ¢) + `extract_contract_summaries()`

| Plan Name | Rate (¢/kWh) | Term | Type | Contract PDF |
|---|---|---|---|---|
| Simple Choice 3 | 15.49 | 3 mo | Fixed | [ToS](https://signup.majorenergy.com/getdocument/?getproductpdf=1&ProductID=152625&type=TOS) |
| Select 12 | 15.99 | 12 mo | Fixed | [ToS](https://signup.majorenergy.com/getdocument/?getproductpdf=1&ProductID=148074&type=TOS) |
| Simple Choice 8 | 16.99 | 8 mo | Fixed | [ToS](https://signup.majorenergy.com/getdocument/?getproductpdf=1&ProductID=152626&type=TOS) |
| Simple Choice 12 | 17.89 | 12 mo | Fixed | [ToS](https://signup.majorenergy.com/getdocument/?getproductpdf=1&ProductID=147594&type=TOS) |

---

## Xoom Energy
**Status:** ✅ 5 plans + 6 contract summary PDFs  
**Source:** `xoomenergy.com/en/residential/new-jersey`  
**Parser:** `_parse_xoom_cards()` (`.myRateData` div, dollar-format rates) + `extract_contract_summaries()`  
**Note:** Dual-market utility popup handled via `strategy_xoom_energy`; 6th contract PDF covers an additional plan variant.

| Plan Name | Rate (¢/kWh) | Term | Type | Contract PDFs |
|---|---|---|---|---|
| SimpleFlex | 16.79 | 0 mo | Variable | ✅ |
| SureLock 12 | 19.89 | 12 mo | Fixed | ✅ |
| RescueLock 12 | 21.09 | 12 mo | Fixed | ✅ |
| SimpleClean 12 | 20.09 | 12 mo | Renewable | ✅ |
| SureLock 24 | 20.69 | 24 mo | Fixed | ✅ |

---

## Run Command

```powershell
cd "C:\Users\brian\School\JunSpring\CSB312\nj-switch-pipeline\src\scraper"
c:\python313\python.exe demo_test.py 2>&1
```

Output CSV: `nj-switch-pipeline\data\demo_results.csv`

---

## Known Issues

| Issue | Status | Details |
|---|---|---|
| NRG — 0 plans | ❌ Active | Commodity + utility modal navigation added; plan cards still not rendering after `#goToProductChart`. Next: inspect JS network calls to find direct product chart endpoint. |
| Direct Energy — blank contract PDFs | ⚠️ Accepted | `RatePlanSummary.aspx` returns blank template; no rate data available from contract source. Plan rows are complete. |
| Ambit — term=0 on first 3 plans | ✅ Resolved | Inline popup parsing with fresh locator re-query each iteration. |
| Xoom duplicate row | ✅ Resolved | Deterministic dedupe before CSV write (`drop_duplicates` on key columns). |

---

## Next Steps (Progress Tracker)

**Last updated:** 2026-05-01

| Priority | Task | Status | Notes |
|---|---|---|---|
| P0 | Fix Xoom contract coverage (was 3/6) | ✅ Completed | `extract_contract_summaries()` now processes all Contract Summary links first (no cap); 6/6 captured |
| P0 | Restore NRG offer capture (0 plans) | ⚠️ In Progress | Modal handling added; plan cards still not loading. Next: capture JS network requests to find direct product chart URL, bypass modal automation |
| P1 | Fix Ambit term=0 on first 3 plans | ✅ Completed | Inline popup parsing per plan; `force=True` + fresh locator re-query; `pdf_rows` emitted when `html=None` |
| P1 | Remove Xoom duplicate plan row | ✅ Completed | Deterministic dedupe on key column subset before CSV write |
| P1 | Improve Think Energy resilience | 🔲 Queued | Prefer explicit offer-row selectors first, then card fallback; current single-plan result is fragile |
| P2 | Per-supplier metrics block in demo output | 🔲 Queued | Emit `plan_count`, `contract_count`, `parse_fail_count`, runtime per supplier |
| P2 | Regression check script | 🔲 Queued | Lightweight validator: fail if any supplier drops to 0 plans unless in known-exceptions list |

### Priority Order
1. ~~Ambit term fix~~ ✅
2. NRG restore (P0 — in progress)
3. Think Energy resilience (P1)
4. Per-supplier metrics + regression script (P2)
