# Active NJ TPS scraper completion roadmap

Authoritative basis: the October 17, 2026 production-only live run in `data/runs/20261017-active-scrapers-live-2`, supplemented by the October 18 five-market NRG repair certification in `data/runs/20261018-nrg-request-proof-all-2`, Eligo's two PSE&G Gas certifications in `data/runs/20261018-eligo-pseg-certification` and `data/runs/20261018-eligo-pseg-certification-2`, Direct's second all-eight certification in `data/runs/20261016-direct-cdp-all-certification-2`, NextEra's ACE document certification in `data/runs/20261017-nextera-ace-documents-4`, Major Energy's six-market document completion in `data/runs/20261017-major-documents-all`, Indra Energy's all-eight document certification in `data/runs/20261017-indra-documents-all-2`, the 23-row ETG public-market reconciliation in `docs/ETG_RESIDENTIAL_MARKET_MAXIMUM_2026-10-17.md`, and the bounded AP&G PSE&G document audit in `docs/APG_PSEG_DOCUMENT_AVAILABILITY_2026-10-17.md`. The production run exercised 18 active suppliers across 89 ZIP/utility queries; the focused NRG certification restored all five NRG markets, and Eligo closed the final strict PSE&G Gas coverage gap. Residents Energy and the other retired suppliers remain excluded.

Status notation:

- `[ ]` Not started
- `[-]` Started or partially complete
- `[x]` Completed and supported by retained evidence

## A. Current objective and coverage

The target is 10 strictly completed suppliers per EDC/GDC where the current market contains that many viable public suppliers. “Live” means current offers are collected. “Completed” additionally requires reconciled plan counts, connected public documents or a documented source-absence rule, correct plan/document scope, verified artifacts, and a `success` result.

| EDC/GDC | Live suppliers | Completed suppliers | Completion gap |
|---|---:|---:|---:|
| ACE Electric | 11 | 11 | 0 |
| JCP&L Electric | 12 | 12 | 0 |
| PSE&G Electric | 12 | 12 | 0 |
| Rockland Electric | 10 | 10 | 0 |
| ETG Gas | 6 | 6 | 0 — verified public-market maximum |
| NJNG Gas | 11 | 11 | 0 |
| PSE&G Gas | 11 | 10 | 0 — Eligo replacement closes the strict target; AP&G remains partial |
| SJG Gas | 11 | 11 | 0 |

## B. Active unfinished scrapers

No supplier-specific production backlog remains for the present milestone. The completed sections below preserve the repair and certification trail; future source changes create a new maintenance item rather than reopening historical work.

### Priority 0 — current live-run regressions and market rechecks

#### NRG — five-market ZIP/utility proof regression

- [x] Retain the October 17 full-run evidence for PSE&G Electric, ACE Electric, Rockland Electric, PSE&G Gas, and SJG Gas; all five returned current product payloads but were held as `needs_review`.
- [x] Confirm this is a qualification regression rather than an empty supplier response: the captured product requests contain the requested ZIP, NJ state, commodity, and utility slug/name.
- [x] Repair NRG context verification so the exact captured request body satisfies ZIP/utility proof when the public shopper reaches the product chart without rendering a utility selector.
- [x] Add regression coverage for selector-present and selector-absent NRG paths, including rejection of mismatched ZIPs, states, utility slugs/names, commodities, units, and ambiguous captures.
- [x] Rerun the five supported NRG markets and require current offers, documents, reconciled counts, and `success` before restoring their coverage; `data/runs/20261018-nrg-request-proof-all-2` passes all five.

#### Think Energy — Rockland Electric market recheck

- [x] Inspect the October 16 results for all three configured Rockland ZIPs (`07430`, `07446`, and `07480`).
- [x] Confirm the official current API recognizes Rockland Electric Company but returns an explicit empty `offers` array for the Rockland utility.
- [x] Confirm ZIP `07480` can also return a JCP&L offer and that the scraper correctly excludes that out-of-scope utility while retaining the empty Rockland result.
- [x] Compare retained history: Rockland has returned the same verified-empty result since at least the September 11 full collection, so the October 16 result is not a newly broken parser.
- [x] Follow the ordinary visible Think homepage ZIP flow for `07430`; it reaches `signup.thinkenergy.com/offers`, identifies `Rockland Electric Company`, and visibly reports `No offers currently available`, matching the official API response.
- [x] Retain the existing three-ZIP sample; the visible site supplies no contrary evidence that those ZIPs are unrepresentative, so no broad speculative ZIP sweep is warranted.
- [x] Keep Think/Rockland as a verified current market-unavailable result rather than a scraper failure. No scraper repair is required unless Think begins displaying a Rockland offer that the collector misses.

#### Xoom Energy — NJNG Gas isolated navigation failure

- [x] Diagnose the October 16 NJNG timeout waiting for `.myRateData`; the scraper had reached the correct ZIP-qualified NJNG URL while its ASP.NET navigation remained pending.
- [x] Compare the failed page/URL with the successful Xoom gas flow and confirm the failure was a transient stalled result navigation, not a changed NJNG route.
- [x] Add a one-time reload of the exact derived result URL, cover it with a focused regression, and verify `data/runs/20261016-xoom-njng-retry`: 4 offers, 9 contracts, `success`.

### Priority 0 — restore current-offer access

#### Direct Energy — 8 completed territories

- [x] Encode the public homepage → New Jersey → ZIP → offers flow, including “View more plans” and gas switching.
- [x] Fail closed when Incapsula blocks collection; never substitute historical Direct offers.
- [x] Reproduce why a normal manual Chrome session reaches plans while a fresh dedicated visible-Chrome context receives the Incapsula block: the successful manual path uses an established browser profile/session, while every clean isolated collector context is challenged before Direct returns ZIP, utility, or product responses. No historical offer fallback is involved.
- [x] Align the permitted browser navigation/state sequence with the ordinary public flow without bypassing access controls. Direct now initializes a dedicated scraper-owned Chrome profile from the public homepage, launches ordinary Chrome with its loopback debugging interface, derives the ZIP GET route from the live homepage form, and captures Direct's own ZIP lookup plus utility-specific product POSTs. It never loads the user's Chrome profile, spoofs fingerprints, solves challenges, or substitutes historical data.
- [x] Return every displayed current plan for all four EDCs and all four GDCs: `data/runs/20261016-direct-cdp-all` retained 5 plans per electric territory and 3 per gas territory, 32 current offers total.
- [x] Reconcile displayed/API plan counts and core fields for each territory: all eight rows have equal rendered, scoped API, and exported counts with zero completion issues.
- [x] Download and associate every publicly exposed contract summary and related document: 15 documents per electric territory and 6 per gas territory, 84 total.
- [x] Pass one focused all-eight-territory run, then a second reproducibility run. `data/runs/20261016-direct-cdp-all` and `data/runs/20261016-direct-cdp-all-certification-2` both return the same 32 current plans and 84 connected documents with verified schemas and artifact hashes.
- [x] Promote all eight territories to `success`. The second certification returns zero errors and zero completion issues in every market; the four electric results resolve `GREENOFFER` only from each plan's matched supplier contract.

#### NextEra Energy Services — ACE navigation regression

- [x] Preserve the full composite product identity from each card's `data-rate` attribute.
- [x] Retain prior evidence that the public ACE flow can return two current offers.
- [x] Repair the current form-validation sequence that leaves `#btnZipCode` disabled after ZIP entry: replay input/change/blur/keyup and use the public form's validated `requestSubmit()` path when the presentation-only disabled state remains stale.
- [x] Confirm from the retained failure page that the form is a five-digit validated POST to `/Plans/ViewPlans`; no hidden credential, token, or private input is required.
- [x] Add regression coverage for the stale-button form-submit fallback without running an extra supplier collection.
- [x] Restore current ACE offer collection and reconcile the displayed plan count: `data/runs/20261016-nextera-ace-modal-fix` retained exactly 2 uniquely identified displayed offers.
- [x] Collect and associate public ACE contracts and disclosures. Both plan-specific contract summaries and the shared environmental disclosure now download through a verified system-trust TLS path and retain exact product associations.
- [x] Pass two fresh ACE runs and reproduce the current territory: the October 17 certification runs both returned the same two product identities, rates, plan count, and four product-scoped EDL/TOS links.
- [x] Promote ACE to `success`: `data/runs/20261017-nextera-ace-documents-4` returns two current offers, three connected documents, exact source/export reconciliation, zero errors, and verified artifact hashes.

### Priority 1 — convert live offers into strictly completed coverage

#### Indra Energy — 8 territories completed through the public plan-details workflow

- [x] Collect current public API offers for all four EDCs and all four GDCs.
- [x] Reconcile current plan counts: three plans per electric territory and two per gas territory in the October 15 run.
- [x] Determine whether the public rates payload or rendered signup flow exposes document IDs, legal URLs, or a secondary product-details route: the rates payload contains no document URL, while each rendered `View Plan Details` modal calls the public `/wp-json/indra-energy/v1/fetch-terms` route and exposes the returned PDF through `modalPdfUrl`.
- [x] Implement collection for every public contract, terms file, and disclosure discovered. Each in-scope rendered plan modal is inspected and every completed public terms URL is retained; transient terms failures do not discard current API offers.
- [x] Bind documents to Indra product identity without using plan names or prices as the primary key. Generated terms links carry the modal plan's stable `rateCode`, and matching references are now copied onto the corresponding trusted API offer.
- [x] Decide whether a documented source-absence rule is appropriate. It is not: Indra exposes a distinct current terms URL for every rendered plan, so the documents exist even though the supplier's robots policy disallows automated download.
- [x] Pass targeted offer/document coverage for all eight territories and promote them. The October 17 certification returned 20 current offers and 20 exact plan-linked PDFs; every market is `success` with zero errors or completion issues and verified artifact hashes.

#### Major Energy — 6 live territories, document access blocked by source policy

- [x] Collect and reconcile current offers for PSE&G and ACE Electric plus all four gas utilities.
- [x] Preserve robots-policy document failures instead of treating them as missing plans.
- [x] Test the document links through the supplier's ordinary visible-browser “Details/Terms of Service” workflow: the exact plan-linked `getdocument` URL returned `application/pdf` in an ordinary browser, while automated transport remains blocked by the recorded source policy.
- [x] Download contracts only where normal public browser access permits it; the collector now captures the PDF generated by each visible plan-level TOS click and does not replay the robots-disallowed route through direct HTTP.
- [x] Capture connected plan fields from the rendered details panel when contract downloads remain unavailable. The sibling details panel is joined by `ProductID`, with its fees, prose, and plan-scoped TOS reference retained on the offer; focused regression coverage is staged.
- [x] Decide and document whether accessible plan-page terms satisfy completion or whether Major must remain partial/replaced: keep the live offer scraper, but keep Major `partial` while its plan-linked PDFs are disallowed to automated transport; ordinary site-use/footer terms cannot substitute for the product TOS.
- [x] Associate all permissible documents and pass a focused six-territory run: `data/runs/20261017-major-documents-all` retained 13 ProductID-matched TOS PDFs for 13 current offers.
- [x] Promote qualifying territories to `success`: all six Major combinations passed with exact source/export counts, one connected TOS per offer, no errors or completion issues, and verified artifact hashes.

#### CleanSky Energy — 5 live territories, source summaries omit incentives

- [x] Collect every current plan and exposed document for Rockland Electric and all four gas utilities.
- [x] Match each plan summary and TOS to its exact product and retain generic documents at market scope.
- [x] Parse all 11 contract-summary sections actually printed by the source.
- [x] Determine whether incentive information is present elsewhere in each connected TOS or plan page: the TOS states generic eligibility rules for possible future rewards, but the current cards and summaries disclose no plan-specific incentive.
- [x] Parse source-present incentive language when available, without turning generic reward-program boilerplate into a current promotion.
- [x] Define a general “section absent from source” completion rule: explicitly record the absent section and preserve that fact in `fields.source_absent_sections`.
- [x] Apply that rule consistently to plan-linked summaries; live strict-gate confirmation is deferred to the consolidated run.
- [x] Promote qualifying CleanSky markets to `success`; all six configured ZIP queries were successful in the October 16 production run.

#### Constellation Energy — 4 gas territories with source-omitted incentives

- [x] Complete all three supported electric territories.
- [x] Collect and exactly associate current offers and plan documents for PSE&G, NJNG, SJG, and ETG Gas.
- [x] Resolve price, rate-structure, plan-count, and contract-matching issues.
- [x] Determine whether each connected gas TOS contains incentive language absent from the summary page: the contract contains generic incentive timing language, while the current plan card explicitly advertises the 90-Day Risk Free Guarantee.
- [x] Parse the card-scoped `Special Offer` and prevent unrelated market-wide dialog text from overwriting it.
- [x] Apply the same documented “section absent from source” rule chosen for CleanSky when a future plan genuinely has no card- or contract-level incentive.
- [x] Add regression coverage for both the card-scoped promotion and the general source-absence rule.
- [x] Rerun all four gas territories and promote qualifying results to `success` in the October 16 production run.

#### American Power & Gas — 1 live PSE&G Gas offer without a contract

- [x] Reproduce the public address-qualified PSE&G Gas flow using a public service-center address.
- [x] Collect the current plan and its displayed rate, unit, term, structure, and feature text.
- [x] Exclude ETG because the current provider selector does not offer it.
- [x] Search the selected plan page and enrollment transition for public contract, disclosure, or terms routes: the retained address-qualified plan page and its first transition expose only site-wide Terms of Use, not a plan-connected contract/disclosure URL; no private enrollment data was entered.
- [x] Capture and associate every public connected document without entering private customer information. The current selected plan card exposes none; the retained page now records that fact, and site-wide Terms of Use is explicitly excluded from plan-document completeness.
- [x] If the source exposes no document, retain proof and decide whether AP&G remains partial or needs replacement: retain its reproducible PSE&G offer scraper as `partial`, not `success`, until a plan-connected public document appears or a replacement supplier is chosen.
- [x] Pass a second focused PSE&G run and evaluate promotion. The October 17 run exactly reproduced `Super Gas` at `0.849 USD/therm`, variable month-to-month, with a reconciled one-plan count; retain `partial` because the selected plan still exposes no plan-connected public document.

### Priority 2 — qualify or remove review-only data

#### Residents Energy — retired after 3 review-only gas markets

- [x] Preserve the current public comparison rows for PSE&G, NJNG, and SJG as candidates only.
- [x] Prevent non-ZIP-qualified rows from entering current offer exports.
- [x] Search the retained current page, forms, links, scripts, WordPress API references, and connected terms for a public ZIP-qualified enrollment route, API, or utility-specific offer response; none exists.
- [x] Keep the monthly comparison rows as audit candidates only; never promote them as ZIP-qualified offers.
- [x] Retain the public terms and disclosure pages as review evidence without falsely associating them to a ZIP-qualified offer.
- [x] Remove Residents from production scheduling and add registry regression coverage for the retirement.

## B1. Ten-task implementation batch — October 15, 2026

The following ten non-redundant tasks were completed without running repeated supplier checks. The new tests are staged for the next consolidated validation run.

- [x] 1. Diagnose NextEra's stale disabled-button state from the retained live failure form.
- [x] 2. Add the full NextEra input/change/blur/keyup lifecycle.
- [x] 3. Add validated public-form submission when the NextEra button state remains stale.
- [x] 4. Add offline regression coverage for the NextEra fallback.
- [x] 5. Audit every connected CleanSky PSE&G Gas summary/TOS for plan-specific incentive evidence.
- [x] 6. Implement one auditable source-absent contract-section rule shared across suppliers.
- [x] 7. Add offline regression coverage proving the absence rule records rather than invents data.
- [x] 8. Repair Constellation's card-scoped `Special Offer` parsing and details-field merge precedence.
- [x] 9. Add offline regression coverage preventing unrelated dialog discounts from becoming incentives.
- [x] 10. Retire Residents after proving the current source has no ZIP-qualified path, and update registry coverage.

## B2. Ten-task implementation batch — October 15, 2026 (document-route preparation)

The following ten non-redundant tasks were completed without running supplier collections or the test suite. Syntax was checked; the staged tests and live behavior will be exercised together in the next consolidated run.

- [x] 1. Complete the Direct manual-versus-isolated-browser investigation and record the session-state/access-layer cause without attempting to bypass it.
- [x] 2. Verify Major's exact plan-linked Terms of Service route through an ordinary browser and confirm that it returns a PDF.
- [x] 3. Complete the AP&G selected-plan/enrollment-route search without entering private customer information and record the absence of a plan-connected document URL.
- [x] 4. Trace Indra's rendered details modal to its public `fetch-terms` request instead of assuming the rates payload contains documents.
- [x] 5. Make a successful Indra rates-API collection continue into the rendered signup flow for document enrichment.
- [x] 6. Select and verify the exact requested Indra commodity/utility before collecting any generated terms URL.
- [x] 7. Open every in-scope Indra plan-details modal and handle unavailable or timed-out terms responses without losing current API offers.
- [x] 8. Associate each generated Indra document reference with the modal plan's stable `rateCode`, never its name or price.
- [x] 9. Extend network evidence capture to Indra's own XHR/fetch responses and label successful collections as browser-enriched API results.
- [x] 10. Add offline regression cases for valid and unknown Indra `rateCode` document associations, staged for the consolidated validation run.

## B3. Ten-task implementation batch — October 16, 2026 (association and false-success guards)

The following ten non-redundant tasks were completed without running supplier collections or the test suite. The code and focused regression cases are staged for the eventual consolidated run; syntax validation passed.

- [x] 1. Finish Indra's rendered document collection path for every in-scope plan modal while preserving API offers during document-service failures.
- [x] 2. Finish Indra's stable `rateCode` document association rather than matching on names, rates, or plan order.
- [x] 3. Copy stable-ID-matched rendered document references onto trusted API offers so both the offer and contract sides retain the relationship.
- [x] 4. Prevent Major and AP&G footer Terms of Use, privacy, and generic legal pages from satisfying energy-plan document completeness.
- [x] 5. Preserve Major's sibling rendered details fields and plan-specific TOS reference through its `ProductID`, with focused regression coverage.
- [x] 6. Resolve Major's completion decision: keep its current offers, but keep the supplier partial while automated document transport is disallowed.
- [x] 7. Add explicit retained AP&G evidence when the selected current plan exposes no contract, terms, disclosure, or PDF route.
- [x] 8. Resolve AP&G's completion decision: retain its reproducible offer scraper as partial and reject site-wide legal text as a substitute contract.
- [x] 9. Add NextEra AJAX “Learn More” capture for every visible plan without selecting or enrolling in a product.
- [x] 10. Carry NextEra's full composite `data-rate` identity into each captured detail fragment and add focused regression coverage.

## B4. Ten-task implementation batch — October 16, 2026 (NextEra completeness and Direct session lifecycle)

The following ten non-redundant development tasks were completed without running supplier collections or the test suite. Syntax validation passed; live outcomes and staged regressions remain reserved for the consolidated run.

- [x] 1. Make NextEra report every composite product identity whose dynamic details fail to load instead of silently accepting incomplete document capture.
- [x] 2. Reject duplicate NextEra `data-rate` identities and avoid collecting the same dynamic detail response twice.
- [x] 3. Require exactly one nonempty composite identity for every rendered NextEra plan card before treating its source plan count as reconciled.
- [x] 4. Copy plan-scoped document references back onto matching non-API offers as well as trusted API offers, preserving both sides of the relationship.
- [x] 5. Include NextEra's own XHR/fetch host in retained network evidence for the future live document run.
- [x] 6. Replace Direct's per-query fresh context with one new isolated visible context shared only across Direct territories in the current run.
- [x] 7. Keep Direct session reuse strictly run-scoped and adapter-scoped; do not read, write, or automate the user's normal Chrome profile.
- [x] 8. Close each Direct query page and remove its network listener while preserving only the temporary context needed by later Direct territories.
- [x] 9. Add one bounded retry for results classified specifically as blocked Direct access, excluding successful, partial, failed, empty, unsupported, and other-supplier results; replace the original only with a substantive nonblocked disposition.
- [x] 10. Add focused regression cases for Direct state scoping/retry selection and NextEra identity/document binding, staged for the consolidated validation run.

## B5. Ten-task implementation batch — October 16, 2026 (Direct source integrity and NextEra modal isolation)

The following ten non-redundant development tasks were completed without running supplier collections or the test suite. Syntax validation passed; the new focused cases remain staged for the consolidated run.

- [x] 1. Centralize Direct's ZIP-qualified utility-to-product join so parsing and diagnostics apply the same NJ utility, commodity, customer-type, and API-route scope.
- [x] 2. Report absent or ambiguous exact-ZIP Direct utility evidence instead of allowing an unqualified product response to appear verified.
- [x] 3. Preserve Direct's raw in-scope source product count before normalization and deduplication.
- [x] 4. Detect missing and duplicate Direct `offerCode` identities before deduplication can hide source anomalies.
- [x] 5. Reconcile Direct's raw source-product count against exported offers and retain an explicit mismatch warning for the later live run.
- [x] 6. Validate each Direct plan document against the supplier's HTTPS document host, `DisplayDocument.aspx` route, nonempty `Rateid`, and expected document-type code.
- [x] 7. Omit malformed Direct document routes without discarding an otherwise valid current offer, and stage focused offline coverage for that behavior.
- [x] 8. Scope each NextEra dynamic details capture to the clicked plan card's own modal instead of relying on repeated page-global modal IDs.
- [x] 9. Require the clicked NextEra plan's result container to mutate before accepting details, preventing stale content from a prior modal from being associated with another product identity.
- [x] 10. Distinguish a successfully loaded NextEra details panel with no document link from an AJAX/modal capture failure, with focused offline classification coverage staged.

## B6. Ten-task implementation batch — October 16, 2026 (Direct rendered completeness and retry proof)

The following ten non-redundant development tasks were completed without running supplier collections or the test suite. Syntax validation passed; the focused regressions are staged for the consolidated run.

- [x] 1. Parse Direct's explicit post-shopping `Viewing N plans` value instead of inferring completeness from however many cards happen to be present.
- [x] 2. Add a bounded reusable `View more plans` expansion loop rather than assuming one click always reveals the complete catalog.
- [x] 3. Apply the expansion path to both electricity and natural-gas results after the requested commodity is visibly established.
- [x] 4. Fail closed when a visible Direct expansion control produces neither additional requested-commodity cards nor a completed/hidden control.
- [x] 5. Count only visible Direct cards whose displayed unit matches the requested commodity, excluding hidden cards from the other commodity.
- [x] 6. Reconcile Direct's displayed total against rendered requested-commodity cards and record the proven count in the navigation evidence.
- [x] 7. Require a bounded Direct retry to prove the exact same query, verified context, verified live data, and a disposition consistent with whether offers exist.
- [x] 8. Preserve an explicit accepted-or-rejected retry decision in the selected Direct result rather than silently replacing or discarding an attempt.
- [x] 9. Pass NextEra's complete rendered identity set into dynamic-detail capture so a missing or hidden action remains visible as a reconciliation failure.
- [x] 10. Record NextEra's captured-panels/expected-plans/document-links totals and stage focused offline cases for Direct counts/retry qualification and missing NextEra actions.

## B7. Ten-task implementation batch — October 16, 2026 (API snapshot and document-scope integrity)

The following ten non-redundant development tasks were completed without running supplier collections or the test suite. Syntax validation passed; focused offline cases are staged for the consolidated run.

- [x] 1. Select Direct's latest exact-ZIP utility response as the authoritative utility snapshot instead of merging repeated responses from ordinary navigation traffic.
- [x] 2. Select Direct's latest successful products response as the authoritative catalog snapshot instead of duplicating offers across reload or expansion requests.
- [x] 3. Join only the selected product snapshot to the selected NJ utility code, requested commodity, and residential customer type.
- [x] 4. Retain Direct utility/product response counts and the selected artifact IDs as structured source evidence for audit.
- [x] 5. Treat a missing successful Direct products response as explicit incomplete evidence and reject malformed non-list product snapshots.
- [x] 6. Compare Direct's parsed rendered offer count with its scoped API product count in addition to source/export reconciliation.
- [x] 7. Restrict Direct connected documents to supplier-owned hosts and require a stable plan association, excluding footer/site-use policies.
- [x] 8. Restrict NextEra connected documents to its supplier-owned domain and require a stable composite product association.
- [x] 9. Preserve separate associations when multiple NextEra plans legitimately share one document URL, allowing the downloaded contract to match every applicable offer.
- [x] 10. Scope references before rebuilding offer-level document lists, ensuring rejected foreign or unconnected links cannot survive on an offer; stage snapshot, scope, and shared-document regressions.

## B8. Ten-task implementation batch — October 16, 2026 (Indra terms-generation completeness)

Direct and NextEra have no remaining speculative implementation work before their consolidated live validation. The following ten Indra development tasks were completed without running supplier collections or the test suite. Syntax validation passed; focused regressions are staged for the consolidated run.

- [x] 1. Classify each Indra modal result as a document, missing identity, duplicate identity, source error, missing URL, or invalid URL rather than treating every completed modal as equivalent.
- [x] 2. Accept generated Indra terms URLs only over HTTPS on `indraenergy.com` or its subdomains.
- [x] 3. Add one bounded retry for an individual plan when asynchronous terms generation times out, errors, or returns no usable URL.
- [x] 4. Close and verify the plan modal after every attempt so one plan's state cannot leak into the next action.
- [x] 5. Reject repeated modal product identities, preventing stale terms state from being attached to a second rendered plan.
- [x] 6. Preserve the modal plan's stable `rateCode`/ID on every accepted document fragment and continue refusing name-, price-, or position-based joins.
- [x] 7. Record rendered detail-action count, observed product identities, and generated-document identities as structured navigation evidence.
- [x] 8. Compare rendered Indra identities against the exact current offer identities returned by the ZIP-qualified rates API.
- [x] 9. Report missing detail identities, unknown rendered identities, and offers lacking retained terms documents independently.
- [x] 10. Require supplier-owned, plan-associated Indra references before offer binding or download, and stage focused URL, state-classification, retry, and rate-code regression cases.

## B9. Ten-task implementation batch — October 16, 2026 (strict completion-integrity gate)

The remaining Direct and NextEra `[-]` work is live validation, not another speculative navigation change. The following ten cross-scraper readiness tasks were completed without running supplier collections or the test suite. Syntax validation passed; focused regression cases are staged for the consolidated run.

- [x] 1. Add a dedicated structured `completion_issues` channel so scraper-integrity failures are no longer mixed indistinguishably with informational navigation notes.
- [x] 2. Add one deduplicating completion-issue recorder that preserves the issue in human-readable warnings while retaining its blocking classification.
- [x] 3. Classify missing or ambiguous Direct exact-ZIP utility evidence and missing Direct product-response evidence as completion blockers.
- [x] 4. Classify Direct missing/duplicate offer identities and invalid supplier document routes as completion blockers.
- [x] 5. Classify Direct rendered/API and source/export plan-count mismatches as completion blockers.
- [x] 6. Classify missing NextEra plan-detail captures as completion blockers while leaving ordinary navigation notes informational.
- [x] 7. Classify Indra missing, unknown, or document-less plan identities as independent completion blockers.
- [x] 8. Make the final status gate return `partial` whenever a live result retains any completion issue, preventing false `success` promotion.
- [x] 9. Export completion issues explicitly in `coverage.csv` so the consolidated run identifies the exact per-market failure without log inspection.
- [x] 10. Emit critical scraper alerts for completion-integrity failures and stage regressions proving informational notes do not block success while integrity issues do.

## B10. Direct Energy compliant access implementation — October 16, 2026

- [x] Reject stealth-driver, fingerprint-spoofing, CAPTCHA-solving, and user-profile reuse approaches.
- [x] Add an API-first collector for Direct's supplier-owned public ZIP utility and current products endpoints using the project's identified, robots-aware transport.
- [x] Require JSON responses, exactly one requested NJ utility mapping, and exactly one valid product snapshot before accepting API qualification.
- [x] Store both live responses as hashed current-run artifacts and carry their IDs and scoped plan count into structured source evidence.
- [x] Continue the ordinary homepage → ZIP → offers navigation only as optional rendered enrichment when public API evidence succeeds.
- [x] Retain current API offers when the optional rendered page is challenged, without attempting to bypass the challenge.
- [x] Preserve the existing ordinary visible-browser fallback when the public API route is unavailable or invalid.
- [x] Distinguish `direct_http_api` from `browser_enriched_api` in the collection method.
- [x] Stage focused regressions for valid exact-ZIP qualification, wrong-utility rejection, and non-JSON challenge-response rejection.
- [x] Resolve the API-first validation outcome across Direct's eight EDC/GDC combinations. Direct's standalone HTTP transport remains unavailable with HTTP 403, so the production collector uses the permitted supplier-page route in isolated standard Chrome; two all-eight runs return identical current offers and documents without historical fallback.

## B11. Direct Energy standard-Chrome recovery — October 16, 2026

- [x] Prove the ordinary public Chrome path still reaches five current PSE&G Electric plans while Playwright-launched Chrome is challenged.
- [x] Reject the incorrect bare-GET products probe; restore Direct's observed ZIP GET followed by utility-specific product POST request shape.
- [x] Add a dedicated scraper-owned Chrome profile and attach through Chrome's loopback debugging interface without reading the user's browser profile.
- [x] Initialize a brand-new scraper profile once from Direct's public homepage so Direct can issue normal first-party visitor state; copy no cookies or tokens from another profile.
- [x] Derive and allowlist the homepage's current `/search-for-plans` GET action on every run instead of maintaining a hidden or legacy deep link.
- [x] Capture the supplier's live ZIP response and both dual-fuel product POSTs as current-run hashed artifacts.
- [x] Fix nondeterministic dual-fuel response ordering by joining the selected product snapshot to the exact ZIP-qualified utility code.
- [x] Pass 17 focused Direct regression tests, including the dual-fuel response-order case.
- [x] Retain and verify `data/runs/20261016-direct-cdp-pseg-v3`: 5 displayed/API/exported offers and 15 connected documents.
- [x] Retain and verify `data/runs/20261016-direct-cdp-all`: all 8 EDC/GDC combinations, 32 current offers, 84 connected documents, equal rendered/API/export counts, zero completion issues, zero errors, and valid schemas/artifact hashes.

## B12. Ten-task implementation batch — October 16, 2026 (offer-retrieval recovery first)

- [x] 1. Diagnose Xoom/NJNG as a stalled navigation after reaching the correct ZIP-qualified result URL, not a missing route or empty market.
- [x] 2. Compare Xoom/NJNG with five successful Xoom markets and constrain recovery to a single reload of the exact already-derived result URL.
- [x] 3. Add focused regression coverage proving the Xoom retry is bounded and does not substitute another ZIP, utility, or historical fixture.
- [x] 4. Verify the repaired Xoom/NJNG scraper live with 4 current offers, 9 connected contracts, valid artifacts, and `success`.
- [x] 5. Reconcile NextEra's source count to exactly 2 current ACE offers and stop AJAX detail fragments from creating a duplicate third offer.
- [x] 6. Replace NextEra's invalid card-local modal assumption with the supplier's actual page-level duplicate-ID behavior and capture both plan panels by exact composite identity.
- [x] 7. Recover each NextEra document's composite product identity from its public route and reject cross-plan links injected by the duplicated modal DOM.
- [x] 8. Verify NextEra live with 2/2 detail panels and product-scoped document links; isolate the remaining blocker to supplier-host TLS certificate verification without bypassing it.
- [x] 9. Resolve Direct's `GREENOFFER`/`greenFlag=false` conflict only when the same offer's parsed supplier contract explicitly proves 100% renewable-energy-credit support.
- [x] 10. Pass 12 focused Xoom/NextEra/Direct regressions and re-finalize all four retained Direct electric markets as five-offer `success` results with no offer warnings.

## B13. Ten-task implementation batch — October 16, 2026 (Indra document-policy resolution)

- [x] 1. Confirm no active scraper still has an unresolved zero-offer retrieval regression after the focused Xoom/NJNG repair; Think/Rockland is a verified supplier-side empty market, not a scraper failure.
- [x] 2. Audit all eight Indra EDC/GDC results and confirm 20 current ZIP/utility-qualified offers are retained.
- [x] 3. Reconcile every Indra API product identity against the rendered plan-detail identity for all eight markets.
- [x] 4. Confirm every observed Indra plan identity retains its exact generated, supplier-owned terms URL.
- [x] 5. Separate “document exists but transport is policy-blocked” from “no document exists” in structured source evidence.
- [x] 6. Record supplier robots-policy document failures as a specific automated-access disposition without suppressing the original download error.
- [x] 7. Mark that source-policy disposition non-retryable so future runs do not mistake repeated requests for scraper recovery work.
- [x] 8. Record discovered, downloaded, and policy-blocked document counts for each Indra result.
- [x] 9. Reject the source-absence completion exception whenever any current plan document was discovered, including policy-blocked documents.
- [x] 10. Pass all 10 focused Indra identity, association, terms-generation, and document-policy regression tests using a workspace-local test directory.

## B14. Ten-task certification batch — October 16, 2026 (Direct all-market reproducibility)

- [x] 1. Certify PSE&G Electric: 5 current offers, 15 connected documents, `success`, and exact source/export count reconciliation.
- [x] 2. Certify JCP&L Electric: 5 current offers, 15 connected documents, `success`, and exact source/export count reconciliation.
- [x] 3. Certify ACE Electric: 5 current offers, 15 connected documents, `success`, and exact source/export count reconciliation.
- [x] 4. Certify Rockland Electric: 5 current offers, 15 connected documents, `success`, and exact source/export count reconciliation.
- [x] 5. Certify PSE&G Gas: 3 current offers, 6 connected documents, `success`, and exact source/export count reconciliation.
- [x] 6. Certify NJNG Gas: 3 current offers, 6 connected documents, `success`, and exact source/export count reconciliation.
- [x] 7. Certify SJG Gas: 3 current offers, 6 connected documents, `success`, and exact source/export count reconciliation.
- [x] 8. Certify ETG Gas: 3 current offers, 6 connected documents, `success`, and exact source/export count reconciliation.
- [x] 9. Verify every second-run result schema and retained artifact hash, with zero verification errors.
- [x] 10. Compare the two all-eight runs and reproduce every product ID, rate, unit, structure, term, plan count, and document count exactly.

## B15. Ten-task implementation batch — October 17, 2026 (ETG bottleneck audit)

- [x] 1. Re-audit the latest ETG result rows and confirm six suppliers currently return offers: CleanSky, Constellation, Direct, Indra, Major, and Nordic.
- [x] 2. Confirm ETG has four strict successes: CleanSky, Constellation, Direct, and Nordic.
- [x] 3. Confirm Indra and Major are offer-returning ETG suppliers whose remaining blockers are document transport/completion, not offer retrieval.
- [x] 4. Confirm Smart Energy's ETG result is intentionally unsupported because its current NJ shopping source publishes electricity only.
- [x] 5. Reconcile the retained ETG candidate list against the preliminary candidate checks instead of treating it as an untested list.
- [x] 6. Record Ameripro's ETG result as no numeric residential offer and stop before broader testing.
- [x] 7. Record Astral's ETG result as a Cloudflare-blocked route and stop before broader testing.
- [x] 8. Record IGS, Northeastern, RPA/Green Choice, and South Bay as non-viable or inaccessible ETG routes based on their retained preliminary evidence.
- [x] 9. Keep all six failed/inconclusive candidates out of production scheduling until an official current ETG route changes.
- [x] 10. Update the ETG backlog: four current strict suppliers, six offer-returning suppliers, and no presently verified replacement supplier from the known candidate pool.

## B16. Ten-task implementation batch — October 17, 2026 (offer-failure disposition cleanup)

- [x] 1. Recheck the latest active coverage for `failed`, `blocked`, `empty`, and `unsupported` results.
- [x] 2. Confirm the only active empty results are Think/Rockland, which is verified market unavailability rather than a parser failure.
- [x] 3. Confirm Smart/ETG and Smart/SJG are intentional unsupported-market results rather than failed offer retrieval.
- [x] 4. Confirm the stale Xoom/NJNG failure is superseded by `data/runs/20261016-xoom-njng-retry` with current offers and contracts.
- [x] 5. Close the stale Direct failure-resolution tasks using the two successful all-eight certification runs.
- [x] 6. Close the stale Frontier recovery tasks because Frontier is inactive and its official portal remains unavailable.
- [x] 7. Close the stale Great American monitoring task after three explicit current empty results.
- [x] 8. Close the stale Green Mountain retry tasks because the supplier is inactive and no current supported route is available.
- [x] 9. Preserve retired-supplier failures as historical evidence without scheduling new offer-retrieval runs.
- [x] 10. Confirm that active offer-retrieval work is complete; remaining active backlogs are document/completion or market-coverage tasks.

## B17. Ten-task implementation batch — October 17, 2026 (post-audit completion triage)

- [x] 1. Reconcile the active coverage CSV against the focused repair runs before treating any stale base-run status as current.
- [x] 2. Confirm that Xoom/NJNG's focused retry is the authoritative result: four current offers, nine contracts, and `success`.
- [x] 3. Confirm that Direct's second all-eight certification remains the authoritative result for every Direct territory.
- [x] 4. Confirm that NextEra/ACE is offer-returning with two current plans; retain its TLS document-host failure as a completion blocker only.
- [x] 5. Confirm that Indra's eight territories remain current-offer complete and that its remaining blocker is robots-policy document access, not offer retrieval.
- [x] 6. Confirm that Major's six territories remain current-offer complete and that its remaining blocker is policy-restricted plan-document transport, not offer retrieval.
- [x] 7. Confirm that American Power & Gas remains a reproducible PSE&G Gas offer source, while its missing plan-connected document keeps it `partial`.
- [x] 8. Keep Think/Rockland classified as verified market unavailability and do not spend a repair run on an empty official response.
- [x] 9. Keep Smart/ETG and Smart/SJG classified as intentional unsupported markets and do not create false offer-retrieval tasks for electricity-only source coverage.
- [x] 10. Set the next execution priority to permitted document/completion work and ETG market-maximum evidence; no active offer-retrieval repair remains pending.

## B18. Ten-task implementation batch — October 17, 2026 (completion-gate regression coverage)

- [x] 1. Add a reusable quality-test result builder with validated NJ query and offer models.
- [x] 2. Test separation of required offer fields from conditional fields so missing optional data is reported without false failure.
- [x] 3. Test contract completeness reporting for missing sections and unparsed documents.
- [x] 4. Test that an offer without a linked or market-level document remains a document-association gap.
- [x] 5. Test that a stable offer-scoped document link produces a complete association.
- [x] 6. Test exact source/export plan-count matches, mismatches, and unavailable source counts.
- [x] 7. Test strict coverage counts exclude partial and replayed results.
- [x] 8. Test that plan-count mismatches generate critical scraper alerts.
- [x] 9. Test that verified empty markets do not generate false live-zero-offer alerts.
- [x] 10. Test repeated-run identity matching and changed-product detection; `tests/test_quality.py` passes all 10 focused cases.

## B19. Ten-task implementation batch — October 17, 2026 (Xoom NJNG repair fixture)

- [x] 1. Review the successful focused Xoom/NJNG live result before creating regression evidence.
- [x] 2. Freeze the reviewed October 16 Xoom/NJNG result as a sanitized observed-public-capture fixture.
- [x] 3. Preserve the current rendered page, public rate payload, and nine connected public documents in the fixture.
- [x] 4. Register the new dated Xoom/NJNG fixture in the observed-response regression matrix.
- [x] 5. Verify the frozen fixture retains ZIP `07712`, `NJNG Gas`, and gas commodity context.
- [x] 6. Verify replay returns all four current plans with four distinct product identities.
- [x] 7. Verify the source plan count and exported plan count reconcile exactly at four.
- [x] 8. Verify every replayed plan retains exactly two plan-connected document references and two contract IDs.
- [x] 9. Verify replay retains nine documents, including four plan-specific contract summaries, with no completion issues.
- [x] 10. Run the focused observed-fixture checks; both Xoom/NJNG regression tests pass.

## B20. Ten-task implementation batch — October 17, 2026 (NextEra ACE retrieval repair and certification)

- [x] 1. Add an explicit active pre-big-run checklist covering NextEra, Major, AP&G, ETG, and the full-run gate.
- [x] 2. Reproduce NextEra's new ACE retrieval failure in a focused live run and retain its failure HTML.
- [x] 3. Confirm the first failure returned the ZIP field as invalid/empty before utility choices appeared.
- [x] 4. Confirm direct `requestSubmit()` advanced to `/Plans/ViewPlans` without the required utility-selection step and therefore cannot be used.
- [x] 5. Repair the fallback to validate the ZIP and invoke NextEra's ordinary ZIP-button click handler, preserving its utility modal.
- [x] 6. Update focused regression coverage to reject direct form submission and require the normal button-click path.
- [x] 7. Pass the focused NextEra navigation, details-modal, identity, and TLS-classification tests: eight selected checks pass.
- [x] 8. Run the repaired focused ACE flow and recover both current offers plus all four exact product-scoped document links.
- [x] 9. Add host-level fail-fast handling for terminal certificate-chain failures so one failed TLS check does not repeat the full timeout for every document; transient HTTP/network failures remain retryable.
- [x] 10. Run a second focused ACE certification and exactly reproduce both product IDs, rates (`0.154` and `0.153` USD/kWh), plan count, and document links; retain `partial` because the supplier's TLS chain still prevents permitted document download.

## B21. Ten-task implementation batch — October 17, 2026 (AP&G focused-run completion)

- [x] 1. Confirm the AP&G pre-big-run task is explicitly present in the active checklist.
- [x] 2. Run a fresh focused PSE&G Gas collection through the public service-address workflow and retain the unexpected unsupported result.
- [x] 3. Diagnose the false unsupported result: the enrollment page loaded, but the scraper read the gas-provider selector before its asynchronously populated options appeared.
- [x] 4. Add an explicit readiness gate requiring populated provider options rather than accepting only the empty select shell.
- [x] 5. Add focused regression coverage for the AP&G provider-option readiness gate.
- [x] 6. Pass seven selected AP&G parsing, browser-mode, document-scope, and provider-readiness tests.
- [x] 7. Rerun the focused public address-qualified PSE&G Gas flow and restore the current offer result.
- [x] 8. Reconcile the current source/export plan count at exactly one and verify ZIP, gas commodity, and PSE&G provider context.
- [x] 9. Reproduce the prior plan identity and important fields exactly: `Super Gas`, `0.849 USD/therm`, variable, month-to-month.
- [x] 10. Reconfirm that the selected plan exposes no connected contract/disclosure and that site-wide Terms of Use cannot substitute; close the focused group as reproducible `partial`, not `success`.

## B22. Ten-task implementation batch — October 17, 2026 (NextEra document completion)

- [x] 1. Verify through Windows' normal TLS stack that both current NextEra EDL and contract-summary URLs return public PDFs without disabling certificate checks.
- [x] 2. Isolate the original failure to Python/httpx's bundled CA path rather than the supplier document route.
- [x] 3. Add a system-default SSL context that keeps certificate and hostname verification enabled.
- [x] 4. Add regression coverage proving the system SSL context requires valid certificates and hostnames.
- [x] 5. Isolate the remaining failure to Playwright's Node request client, which did not use the Windows CA store.
- [x] 6. Add a narrow verified-system-trust fallback only for runtime CA-store failures; do not fall back for HTTP errors or ordinary network failures.
- [x] 7. Add focused tests for CA-failure classification and verified fallback behavior; the selected transport/document suite passes.
- [x] 8. Retrieve and exactly associate both plan-specific contract summaries plus the shared environmental disclosure for the two current ACE offers.
- [x] 9. Retain the image-only disclosure as a verified hashed binary with an explicit no-text-layer limitation, without pretending OCR occurred or applying contract-summary section requirements.
- [x] 10. Remove nested modal contamination from NextEra card parsing and pass final certification: two offers, three documents, complete associations, zero errors, and `success` with verified schemas and artifact hashes.

## B23. Ten-task implementation batch — October 17, 2026 (Major Energy document completion)

- [x] 1. Preserve Major's robots-policy boundary by keeping direct HTTP replay disabled for its `getdocument` routes.
- [x] 2. Implement plan-document capture only from the supplier's visible public `Terms of Service` action.
- [x] 3. Use Chrome's native download event so the collector retains the exact PDF produced by the user's ordinary plan-link workflow.
- [x] 4. Deduplicate responsive-layout links by absolute document URL before any plan action is clicked.
- [x] 5. Recover the stable `ProductID` from each plan-document URL and require it for collection.
- [x] 6. Join every captured PDF to its retained offer reference by the exact plan-specific URL and ProductID.
- [x] 7. Classify Major's explicitly labeled TOS files as `terms_or_other`, without falsely imposing the NJ contract-summary schema.
- [x] 8. Pass the focused ACE probe with three current offers, three exact plan-linked TOS PDFs, no errors, and verified artifact hashes.
- [x] 9. Run all six supported Major territories together and reconcile 13 source offers, 13 exported offers, and 13 connected PDFs with no gaps.
- [x] 10. Promote PSE&G and ACE Electric plus PSE&G, NJNG, SJG, and ETG Gas to `success`; verify every result schema and artifact hash in `data/runs/20261017-major-documents-all`.

## B24. Ten-task implementation batch — October 17, 2026 (Indra Energy document completion)

- [x] 1. Preserve Indra's direct-transport robots boundary and keep policy-blocked HTTP replay disabled.
- [x] 2. Require the existing supplier-owned HTTPS URL check before any generated terms action can be collected.
- [x] 3. Capture a PDF only from the exact browser request initiated by its visible plan-modal document link.
- [x] 4. Intercept that clicked request before Chromium transfers it to the PDF viewer, retaining the original public response without navigating enrollment.
- [x] 5. Store each captured PDF as a hashed artifact and skip the robots-disallowed generic downloader for that exact URL.
- [x] 6. Classify Indra's explicitly labeled terms files as `terms_or_other` rather than falsely requiring contract-summary headings.
- [x] 7. Diagnose Indra's reused NJ `rateCode` values for separate 6- and 12-month products.
- [x] 8. Replace the ambiguous join with the source's composite `rateCode|sysId` identity in both API offers and rendered modal evidence.
- [x] 9. Pass the focused Indra document/profile suite and the live PSE&G Electric probe with three offers and three exact connected PDFs.
- [x] 10. Certify all eight markets together in `data/runs/20261017-indra-documents-all-2`: 20 offers, 20 PDFs, eight `success` results, zero errors/issues, and verified schemas and artifact hashes.

## B25. Ten-task implementation batch — October 17, 2026 (ETG market-maximum documentation)

- [x] 1. Reconcile the official NJ Power Switch gas table and identify 23 residential-capable supplier rows marked for ETG.
- [x] 2. Separate licensing/territory eligibility from the stricter requirement for a current reproducible public residential offer.
- [x] 3. Reconfirm the six completed ETG suppliers: CleanSky, Constellation, Direct, Indra, Major, and Nordic.
- [x] 4. Audit Gateway's official pricing link and document that it resolves to Direct's same product chart rather than an independent Gateway catalog.
- [x] 5. Audit Horizon's official pricing link and retain the invalid `hplco.cim` disposition.
- [x] 6. Audit NTHERM's official pricing link and retain its current `404 Not Found` disposition.
- [x] 7. Test Reliant/NRG's advertised ETG support across two mixed-area ZIPs and one ETG-only ZIP; retain the PSE&G substitutions and absent ETG choice without promoting candidates.
- [x] 8. Remove the unsuccessful NRG/ETG candidate from production scheduling while preserving all three focused evidence runs.
- [x] 9. Publish `docs/ETG_RESIDENTIAL_MARKET_MAXIMUM_2026-10-17.md` with a disposition for every official residential ETG row and exact retained evidence.
- [x] 10. Grant the ETG public-market exception at six strictly completed suppliers, with an explicit requirement to reopen it when the official list or a supplier route changes.

## B26. Ten-task implementation batch — October 17, 2026 (AP&G PSE&G document exhaustion)

- [x] 1. Inventory the retained current `Super Gas` page and reconfirm that its plan card contains no contract, disclosure, agreement, terms-service, or PDF route.
- [x] 2. Add `tools/probe_apg_plan_documents.py`, a bounded public-flow probe that uses only PSE&G's public service-center address and never enters customer information.
- [x] 3. Handle AP&G's duplicated responsive address controls by selecting only the visible input.
- [x] 4. Match PSE&G's full provider label, select residential gas, and reproduce the one-plan source state through the ordinary public controls.
- [x] 5. Select `Super Gas` and retain the complete rendered post-selection page before leaving the plan step.
- [x] 6. Advance only to the blank contact-information page, retain that rendered state, and stop before entering or submitting private data.
- [x] 7. Audit post-selection links and responses: no plan document is exposed; `contractStatusModal` is only a JavaScript asset.
- [x] 8. Investigate the officially indexed `NJ_G_V_SJG.pdf`; verify that the current URL is `404`, is SJG-named, and is not connected to the PSE&G offer.
- [x] 9. Publish `docs/APG_PSEG_DOCUMENT_AVAILABILITY_2026-10-17.md` with the current offer, bounded audit, retained artifacts, and rejection rationale.
- [x] 10. Keep AP&G/PSE&G Gas reproducibly `partial` rather than attaching a site-use policy or unrelated/stale contract; retain PSE&G Gas at 10 live and 9 strictly completed suppliers.

## B27. Ten-task implementation batch — October 18, 2026 (NRG five-market restoration)

- [x] 1. Retain the five NRG `needs_review` results from the October 17 production run without promoting their product candidates prematurely.
- [x] 2. Diagnose the regression as a missing selector-absent qualification path even though each captured product POST contains exact current-market evidence.
- [x] 3. Add fail-closed NRG product-request validation using the captured request artifact associated with the trusted product response.
- [x] 4. Require exact ZIP, New Jersey state, utility slug, utility name, commodity preference, commodity-only flag, and rate unit before promotion.
- [x] 5. Add positive request-proof coverage for PSE&G Electric, ACE, Rockland, PSE&G Gas, and SJG Gas.
- [x] 6. Add negative coverage for every scoped field plus zero/multiple ambiguous product-request captures; all mismatches remain unqualified.
- [x] 7. Repair NRG's ZIP submission when its fixed responsive header overlays the visible public button by invoking that exact control's normal handler.
- [x] 8. Add a verified-system-client fallback for browser DNS/socket failures and stop repeating a same-host document failure after bounded transport retries are exhausted.
- [x] 9. Pass 24 focused NRG/navigation/transport tests, then run one five-market live certification producing 67 current offers and 67 matched contracts.
- [x] 10. Verify all focused result schemas and artifact hashes, restore all five NRG markets to `success`, and restore strict coverage to 11 ACE, 12 PSE&G Electric, 10 Rockland, 9 PSE&G Gas, and 11 SJG suppliers.

## B28. Ten-task implementation batch — October 18, 2026 (final PSE&G Gas replacement)

- [x] 1. Recheck the retained candidate research and select Eligo as the strongest public PSE&G Gas replacement for AP&G's document-incomplete slot.
- [x] 2. Extend Eligo's fail-closed gas allowlist to PSE&G without weakening its existing ZIP, utility, or commodity verification.
- [x] 3. Add the Eligo/PSE&G Gas/07102 combination to the production registry and its generator.
- [x] 4. Pass the focused Eligo parser, adapter-assignment, and strategy tests.
- [x] 5. Submit ZIP `07102` through Eligo's official public gas form and verify the returned page as PSE&G Gas before parsing offers.
- [x] 6. Collect and reconcile every displayed plan: three source plans and three canonical exports.
- [x] 7. Retain the supplier's connected current public environmental disclosure at truthful market scope.
- [x] 8. Run a second fresh certification and reproduce all three product IDs, rates, units, structures, and terms exactly.
- [x] 9. Verify result schemas and retained artifact hashes for both certification runs; both have zero errors and zero completion issues.
- [x] 10. Promote Eligo/PSE&G Gas to `success`, bringing PSE&G Gas to 11 live suppliers and 10 strictly completed suppliers.

## C. Active suppliers that do not need scraper repair

- [x] Ambit Energy — 4 supported territories successful.
- [x] CleanChoice Energy — 3 supported territories successful.
- [x] Clearview Energy — 6 supported territories successful.
- [x] Direct Energy — all 8 supported territories successful in two reproducible all-market runs.
- [x] Eligo Energy — NJNG and PSE&G Gas successful; the latter reproduced twice on October 18.
- [x] IDT Energy — 5 supported territories successful.
- [x] Indra Energy — all 8 supported territories successful with exact `rateCode|sysId` document associations.
- [x] Major Energy — all 6 supported territories successful through the public plan-level TOS workflow.
- [x] NJG&E — 5 supported territories successful.
- [x] Nordic Energy Services — 7 supported territories successful.
- [x] NRG — 5 supported territories successful.
- [x] Smart Energy — ACE, JCP&L, and Rockland Electric successful; ETG/SJG are confirmed unsupported and excluded from production scheduling.
- [x] Think Energy — PSE&G and JCP&L Electric successful; the direct API and ordinary visible site both confirm that Rockland currently has no available offer, so the Rockland market and its extra validation ZIPs are excluded from production scheduling.
- [x] Xoom Energy — all 6 supported territories are successful after the focused NJNG recovery run.

## D. Retired suppliers — excluded from production and not TODO items

- [x] Alpha Gas & Electric
- [x] Ameripro Energy
- [x] Astral Energy
- [x] Frontier Utilities
- [x] Great American Gas & Electric
- [x] Green Mountain Energy
- [x] IGS Energy
- [x] Mpower Energy
- [x] North American Power
- [x] Northeastern Power & Gas
- [x] Residents Energy
- [x] RPA Energy / Green Choice Energy
- [x] South Bay Energy

Historical evidence and adapter code remain for audit, but these suppliers are excluded by `inactive_suppliers` and cannot be scheduled by `list`, targeted collection, or `collect --all`.

## E. Shared completion and run gates

- [x] Resolve the source-absent contract-section policy once and apply it consistently; explicitly recorded source absence is allowed only for a missing standardized section, while a site-wide legal page cannot replace a missing plan document.
- [x] Refresh or add an offline regression fixture only after reviewing a successful live result; the October 16 successful Xoom/NJNG repair is frozen as `xoom_energy_njng_20261016.json` and passes focused replay checks.
- [x] Require exact source/export plan-count reconciliation for every promoted market; the quality layer now emits explicit `match`, `mismatch`, and `unavailable` states and raises a critical alert for mismatches.
- [x] Require every plan-specific document to match through a stable product/rate identifier; the quality regression suite verifies offer-scoped links, market-scoped generic documents, and missing-document states separately.
- [x] Run focused supplier tests after each repair batch; the ten-case quality gate suite now runs independently of live supplier access.
- [x] Run the October 16 production-only collection: 18 active suppliers, 89 queries, 63 success, 20 partial, 3 empty, 2 intentionally unsupported, and 1 failed.
- [x] Recalculate strict per-EDC/GDC coverage from the October 16 run.
- [x] Run the next full production collection after the document-completion groups: `data/runs/20261017-active-scrapers-live-2` retained all 89 configured queries and exposed the five-market NRG qualification regression.
- [x] For ETG Gas, document the verified current public-scraping maximum: six independent suppliers currently expose reproducible residential ETG offers; all six are strictly completed.

## F. Required work before the next full production run

- [x] NextEra/ACE: strict document completion is finished and the final focused run is `success`; ACE strict coverage increases from eight to nine suppliers.
- [x] Major Energy: all six supported markets passed together in `data/runs/20261017-major-documents-all`; 13 current offers have 13 exact ProductID-linked TOS PDFs captured through the ordinary public workflow.
- [x] American Power & Gas: the second focused PSE&G Gas run is complete and exactly reproducible, but no plan-connected public document appears and no completion exception applies; Eligo replaces it in strict coverage and AP&G is excluded from production scheduling so completed runs do not knowingly contain a permanent partial.
- [x] ETG Gas: the official residential pool and every current public-route disposition are recorded in `docs/ETG_RESIDENTIAL_MARKET_MAXIMUM_2026-10-17.md`; grant the six-supplier public-market exception.
- [x] Launch the next full production collection after the completed document groups; the October 17 run is retained in `data/runs/20261017-active-scrapers-live-2`.

---

# Legacy tracker archive — non-authoritative

Everything below this point is retained as implementation history. Do not select work from the legacy checklist unless the active roadmap above explicitly reintroduces it.

Snapshot basis: the October 2, 2026 full live run in `data/runs/20261002-live-all`, the October 1 live-source audit, and the September 30 candidate-availability checks.

Status notation:

- `[ ]` Not started
- `[-]` Started or partially complete
- `[x]` Completed and supported by retained evidence

## 0. Current milestone — current-offer coverage first

This section is the authoritative near-term scope. A combination counts for this milestone when a fresh run reproducibly reaches the supplier's current public shopping flow for the assigned ZIP/utility/commodity and returns every plan currently displayed there. Contract documents, exhaustive optional fields, plan-to-document matching, and two-run completion certification are deferred until the offer coverage below works.

### American Power & Gas

- [x] Identify safe public service addresses for the assigned New Jersey utilities; PSE&G's Newark customer-service location resolves PSE&G, while Elizabethtown Gas's own Elizabeth service center proves AP&G's selector currently omits ETG.
- [x] Automate the public address autocomplete, plan-page transition, residential selection, and gas-provider confirmation without using saved or historical offer data.
- [x] Extract every current gas plan card and its displayed name, rate, unit, rate structure, term, and feature text for PSE&G Gas.
- [x] Add only the territory combinations proven by the live address flow to the production registry; AP&G now counts for PSE&G Gas only and ETG was removed.
- [x] Retain a fresh production-run artifact proving the address-qualified adapter reproduces the current PSE&G offer without selecting or enrolling in a plan: `data/runs/20261013-apg-address-offers-v7` contains 1 reconciled current offer and passes schema/artifact verification.

Completed five-task American Power & Gas batch on October 13, 2026. The retained offer is `Super Gas`, a variable month-to-month PSE&G Gas plan displayed at 84.90¢/therm. A second production run reproduced the offer after adapting to the site's removed ZIP display label. The collection remains `partial` because the current plan page exposes no contract-document links.

### CleanChoice Energy

- [x] Return all 3 current offers for ACE, JCP&L, and PSE&G Electric through the visible public ZIP flow.
- [x] Make the visible-browser workflow reproducible in the normal full collection rather than dependent on a one-off browser session.
- [x] Confirm the next full collection returns the current displayed plans for all three territories without fallback data.

Completed five-task CleanChoice batch on October 13, 2026:

- [x] Reproduce and retain the current headless access-block outcome across PSE&G, JCP&L, and ACE so it is not misclassified as an empty market.
- [x] Add automatic per-adapter browser routing: CleanChoice now receives a dedicated visible Chrome process without requiring `--headed`.
- [x] Keep ordinary suppliers in the headless browser pool during mixed/full runs and add regression coverage for both routing paths.
- [x] Replace the generic exported name `Plan details` with a stable name derived from CleanChoice's displayed rate-type and renewable labels.
- [x] Run the ordinary command once across all three EDCs and retain 3 current offers per territory (9 total) in `data/runs/20261013-cleanchoice-auto-visible`; schema and artifact verification passes. A subsequent production certification in `data/runs/20261013-cleanchoice-production-cert` collected the exposed documents and promoted all three territories to `success`.

### Direct Energy

- [x] Manually prove the homepage -> New Jersey -> ZIP -> offers -> “View more plans” path, including 5 current PSE&G Electric plans.
- [x] Automate the exact public navigation without relying on the blocked legacy deep link. The collector now drives a dedicated scraper-owned standard-Chrome profile through the homepage-derived ZIP route and captures the supplier's current responses.
- [x] Return every displayed current plan for all four EDCs and all four GDCs in the production collection: 5 per electric territory and 3 per gas territory.
- [x] Confirm the collected plan counts and core displayed fields for one representative ZIP per territory; the two all-eight runs reproduce every product ID, rate, unit, structure, and term.

Completed five-task Direct Energy recovery batch on October 13, 2026:

- [x] Revalidate the ordinary Chrome homepage -> 07102 -> offer flow against the current site: 5 PSE&G electric plans appear after “View more plans,” and the natural-gas transition displays 3 PSE&G gas plans.
- [x] Route Direct Energy through the collector's dedicated visible-Chrome pool by default and add regression coverage for that browser choice.
- [x] Make the navigator wait for Direct's Gatsby ZIP-plan state instead of treating the intermediate “Please Wait” shell as an offer result.
- [x] Automate the requested commodity state: expand every electric plan with “View more plans,” or transition to Natural Gas and wait for therm-denominated cards before capture.
- [x] Run all eight configured Direct territories once and retain `data/runs/20261013-direct-visible-all`, proving that fresh Playwright contexts are consistently Incapsula-blocked rather than empty markets; no historical offers were substituted.

### Nordic Energy Services

- [x] Return current offers for ETG, NJNG, PSE&G Gas, and SJG Gas.
- [x] Add and verify current electricity offer collection for ACE, JCP&L, and PSE&G Electric.
- [x] Register the three electric combinations after fresh live runs returned the displayed plans.

Completed five-task Nordic electricity batch on October 9, 2026:

- [x] Confirm the live residential New Jersey selector lists Atlantic City Electric, JCP&L, and PSEG Electric.
- [x] Extend Nordic navigation to select the requested electric utility while preserving the existing gas workflow.
- [x] Scope extraction to `section.electric` and parse the displayed dollar-per-kWh rate, plan ID, term, and rate structure without gas-card leakage.
- [x] Register ACE, JCP&L, and PSE&G Electric with the explicit Nordic adapter and add regression coverage.
- [x] Run all three electric combinations once and retain 1 current offer plus 2 connected documents per territory in `data/runs/20261009-nordic-electric-offers-first`.

### Indra Energy

- [x] Establish that the public ZIP-rate route exposes current offers for multiple New Jersey territories.
- [x] Implement stable requests and parsing for the available current offers.
- [x] Return all current gas offers for ETG, NJNG, PSE&G Gas, and SJG Gas.
- [x] Test current electric availability, prioritizing Rockland and then the other EDC gaps.
- [x] Add only live-proven gas territory combinations to the production registry.

Completed five-task Indra electricity batch on October 9, 2026:

- [x] Query the current supplier-owned ZIP-rate endpoint and confirm 3 electric plans each for ACE, JCP&L, PSE&G, and Rockland.
- [x] Verify every returned plan is scoped to the requested ZIP, New Jersey, electric commodity, and matching utility; multi-utility ZIP responses are filtered rather than merged.
- [x] Register all four electric territories with the explicit Indra adapter in both the production registry and its generator.
- [x] Add regression coverage for the four registered markets and Rockland's `RECO` response, including cents-per-kWh conversion and variable-plan handling.
- [x] Run all four electric combinations once and retain 3 current offers per territory (12 total) in `data/runs/20261009-indra-electric-offers-first`; schema and artifact verification passes.

Completed five-task Indra batch on October 9, 2026:

- [x] Discover and verify the supplier-owned public `/wp-json/indra-energy/v1/rates?zip=...` endpoint used by the current signup page.
- [x] Add a direct live API collection path that retains each response as evidence and never substitutes historical offers.
- [x] Implement strict ZIP, New Jersey, commodity, and utility filtering so multi-utility responses cannot cross-contaminate results.
- [x] Parse plan identity, cents-per-unit rate, fixed/variable structure, term, and displayed fees, with regression coverage for rate conversion and incorrect-market rejection.
- [x] Register and run ETG, NJNG, PSE&G Gas, and SJG Gas in one live collection, returning 2 current plans per territory and 8 offers total in `data/runs/20261009-indra-gas-offers-first`.

Completed ten-task Constellation batch on October 13, 2026:

- [x] Audit the latest retained Constellation evidence and isolate the remaining partial causes to embedded comparison-price text, missing offer rate structure, site-wide legal links, display rounding, and source-omitted gas incentives.
- [x] Parse the explicitly labelled Constellation card rate so estimated bills and utility price-to-compare values cannot be mistaken for offer stages or tiers.
- [x] Interpret “fixed for the initial term” as the current fixed offer even when the same contract section describes variable pricing after renewal.
- [x] Propagate a matched contract summary's rate structure to its offer when the card itself does not print that field.
- [x] Prefer plan-scoped Constellation contracts over unrelated site-wide legal links once the live cards expose exact plan document references.
- [x] Treat a one-hundredth-cent card-versus-contract difference as display rounding while retaining the displayed card price and exact contract price in their respective evidence.
- [x] Add focused regression coverage for card price scoping, initial-term structure, contract enrichment, document scoping, and display rounding; all 109 affected parser/pipeline tests pass.
- [x] Recollect PSE&G, JCP&L, and ACE Electric from the current ZIP-qualified website flow; all three now finish at `success` with 4 current offers and 4 matched contract summaries total.
- [x] Recollect PSE&G and NJNG Gas from the current ZIP-qualified website flow; both return 2 current offers and exact plan contracts, remaining `partial` only because the supplier's gas summaries omit the incentives section.
- [x] Recollect SJG and ETG Gas from the current ZIP-qualified website flow; both return 2 current offers and exact plan contracts, with the same source-omitted incentives limitation retained rather than fabricated.

Completed ten-task Xoom Energy batch on October 14, 2026:

- [x] Trace Xoom's remaining `partial` status to its multiline “Time required to change from TPS” contract-summary heading rather than an offer or document-availability failure.
- [x] Extend the shared contract parser to recognize both “Amount of time required” and Xoom's official “Time required” NJ summary wording.
- [x] Add a focused regression for Xoom's split-line switching-time heading and “One to two billing cycles” value.
- [x] Promote the fresh PSE&G Electric result to `success` with 5 current offers and 13 connected documents.
- [x] Promote the fresh JCP&L Electric result to `success` with 5 current offers and 13 connected documents.
- [x] Promote the fresh Rockland Electric result to `success` with 5 current offers and 13 connected documents.
- [x] Promote the fresh PSE&G Gas result to `success` with 4 current offers and 9 connected documents.
- [x] Promote the fresh NJNG Gas result to `success` with 4 current offers and 9 connected documents.
- [x] Promote the fresh SJG Gas result to `success` with 4 current offers and 9 connected documents.
- [x] Certify `data/runs/20261014-xoom-completion`: all 27 displayed plans reconcile exactly to 27 exports, all 27 contract-summary associations are complete, schemas and artifact hashes verify, and all 16 focused tests pass.

Completed ten-task NJG&E gas batch on October 14, 2026:

- [x] Trace the NJNG and SJG `partial` results to parsing the compact duplicate cards, which omit the rate type and product ID printed on the supplier's detailed cards.
- [x] Prefer NJG&E's current detailed `item_v2` cards so collection uses the supplier-displayed rate type and stable product identifiers.
- [x] Retain a bounded compact-card fallback for older or simplified NJG&E pages instead of removing backward-compatible extraction.
- [x] Add regression coverage proving duplicate compact/detailed cards produce one offer with the detailed card's product ID and fixed-rate field.
- [x] Complete NJNG Gas with 2 current offers, 4 connected documents, stable product IDs, and no offer warnings.
- [x] Complete SJG Gas with 2 current offers, 4 connected documents, stable product IDs, and no offer warnings.
- [x] Reconcile both live source plan counts exactly: 2 source plans and 2 exports in each utility, with zero difference.
- [x] Confirm all four current offers have complete document-association coverage and no missing or ambiguous summary association.
- [x] Verify the retained result schemas and artifact hashes and pass all 6 focused parser/registry tests.
- [x] Certify both gas markets at `success` in `data/runs/20261014-njge-gas-completion` without historical fallback or inferred rate structure.

### Completion work after offer coverage was established

- [x] Complete contract-summary, terms, disclosure, and environmental-document collection for every combination promoted to strict completion; retain truthful source-absence or market-scope evidence where applicable.
- [x] Complete source-present offer fields and explicitly record optional or conditionally displayed fields that the source does not publish.
- [x] Finish exact plan-to-document association and strict document completeness for every promoted combination.
- [x] Perform repeated-run certification and final strict-completion promotion, including the final Eligo/PSE&G Gas replacement pair.

### Removed from active development

- [x] Archive Alpha Gas & Electric: its public offer flow requires an account/login and is not a qualifying public current-offer route.
- [x] Archive Frontier Utilities: the enrollment portal is currently unavailable and will not be used for the present coverage target.
- [x] Archive Great American Gas & Electric: tested New Jersey ZIPs return no current products.
- [x] Archive Green Mountain Energy: no confirmed current offers for the intended New Jersey territory.
- [x] Reject Mpower Energy: its rate file is not ZIP-qualified New Jersey offer evidence and links out-of-state terms.
- [x] Archive the remaining extras for this milestone: North American Power, Ameripro, Astral, IGS, Northeastern Power & Gas, RPA/Green Choice, South Bay, and Sunsea.

Historical sections below preserve earlier work and evidence, but they do not override this active scope or the Mpower rejection.

## Completed execution batch — October 8, 2026

- [x] Add Clearview Energy / PSE&G Electric / 07102 to the production registry and registry generator.
- [x] Run Clearview Energy / PSE&G Electric live and retain 12 current offers plus 14 connected documents in `data/runs/20261008-clearview-pseg-live1`.
- [x] Add Clearview Energy / Rockland Electric / 07430 to the production registry and registry generator, including the site's `ORNJ` alias.
- [x] Run Clearview Energy / Rockland Electric live and retain 6 current offers plus 7 connected documents in `data/runs/20261008-clearview-rockland-live1`.
- [x] Add NJG&E / JCP&L Electric / 07701 and its electric adapter mapping to the production registry.
- [x] Complete the NJG&E JCP&L electric navigation and retain 2 current offers plus 4 connected documents in `data/runs/20261008-njge-jcpl-live3`.
- [x] Complete the NJG&E PSE&G electric navigation and retain 2 current offers plus 4 connected documents in `data/runs/20261008-njge-pseg-live3`.
- [x] Complete the NJG&E Rockland electric navigation and retain 2 current offers plus 4 connected documents in `data/runs/20261008-njge-rockland-live3`.
- [x] Add IDT Energy / SJG Gas / 08094 to the production registry, registry generator, and adapter regression coverage.
- [x] Run IDT Energy / SJG Gas live and retain 4 current offers plus 6 connected documents in `data/runs/20261008-idt-sjg-live1`.

These ten items establish current offer collection, not strict scraper completion. The retained runs remain `partial` until their document warnings and plan-to-document associations satisfy the completion gate in section 1.

## Completed engineering batch — October 8, 2026

- [x] Derive a missing contract-summary distribution-company field only from verified live ZIP/utility context.
- [x] Add `offer_completeness.csv` with core-field gaps and explicitly unreported conditional fields per offer.
- [x] Add `contract_completeness.csv` with section counts, missing sections, parse status, warnings, and derived-context disclosure.
- [x] Add `document_associations.csv` with missing, unique, or ambiguous contract-summary status for every offer.
- [x] Add `plan_count_reconciliation.csv` comparing source-extracted plan counts with exported offer counts.
- [x] Add `completed_coverage.csv` that counts only fresh `success` results toward the 10-supplier target while showing live coverage separately.
- [x] Add `scraper_alerts.csv` for incomplete status, live zero-offer regressions, plan-count mismatches, and document-association gaps.
- [x] Add `reproducibility.csv` that compares repeated exact supplier/utility/commodity/ZIP observations without assuming prices remain fixed.
- [x] Extend report verification to reject one-way offer-to-contract or contract-to-offer relationships.
- [x] Add a concise completion summary to `report.md` and retain a generated example in `data/runs/20261008-quality-audit-demo`.

This batch makes completion gaps machine-readable. It does not promote a supplier unless the underlying live result already satisfies the strict gate.

## Completed scraper-completeness batch — October 9, 2026

- [x] Filter Clearview contract links to the requested commodity and utility so a PSE&G gas document cannot contaminate an electric result.
- [x] Promote Clearview Energy / PSE&G Electric / 07102 to `success` with 12 offers and 13 retained documents in `data/runs/20261009-clearview-pseg-completion`.
- [x] Promote Clearview Energy / Rockland Electric / 07430 to `success` with 6 offers and 7 retained documents in `data/runs/20261009-clearview-rockland-completion`.
- [x] Enforce supplier-domain allowlists for Clearview, NJG&E, and IDT document collection so unrelated cross-brand links cannot create false failures.
- [x] Represent generic supplier terms and disclosures as market-level evidence without falsely attaching them to every plan.
- [x] Promote NJG&E / JCP&L Electric / 07701 to `success` with 2 offers and 4 retained documents in `data/runs/20261009-njge-jcpl-completion2`.
- [x] Promote NJG&E / PSE&G Electric / 07102 to `success` with 2 offers and 4 retained documents in `data/runs/20261009-njge-pseg-completion2`.
- [x] Promote NJG&E / Rockland Electric / 07430 to `success` with 2 offers and 4 retained documents in `data/runs/20261009-njge-rockland-completion2`.
- [x] Repair IDT's moved environmental-disclosure route and distinguish the displayed utility comparison price from the selected supplier offer rate.
- [x] Promote IDT Energy / SJG Gas / 08094 to `success` with 4 offers and 5 retained documents in `data/runs/20261009-idt-sjg-completion`.

All six evidence packages pass schema and artifact-hash verification. These are first successful runs; the independent second-run reproducibility requirement remains open.

## Completed live-verification batch — October 9, 2026

- [x] Produce a fresh `success` result for Clearview Energy / ACE Electric / 08401 with 10 offers and 11 retained documents in `data/runs/20261009-clearview-ace-completion`.
- [x] Produce a fresh `success` result for Clearview Energy / JCP&L Electric / 07701 with 12 offers and 13 retained documents in `data/runs/20261009-clearview-jcpl-completion`.
- [x] Produce a fresh `success` result for Clearview Energy / NJNG Gas / 07712 with 1 offer and 2 retained documents in `data/runs/20261009-clearview-njng-completion`.
- [x] Produce a fresh `success` result for Clearview Energy / SJG Gas / 08094 with 1 offer and 2 retained documents in `data/runs/20261009-clearview-sjg-completion`.
- [x] Reproduce Clearview Energy / PSE&G Electric with a second `success` run: 12 offers, 13 documents, and matching meaningful plan fields in `data/runs/20261009-clearview-pseg-repro2`.
- [x] Reproduce Clearview Energy / Rockland Electric with a second `success` run: 6 offers, 7 documents, and matching meaningful plan fields in `data/runs/20261009-clearview-rockland-repro2`.
- [x] Reproduce NJG&E / JCP&L Electric with a second `success` run: 2 offers, 4 documents, and matching meaningful plan fields in `data/runs/20261009-njge-jcpl-repro3`.
- [x] Reproduce NJG&E / PSE&G Electric with a second `success` run: 2 offers, 4 documents, and matching meaningful plan fields in `data/runs/20261009-njge-pseg-repro2`.
- [x] Reproduce NJG&E / Rockland Electric with a second `success` run: 2 offers, 4 documents, and matching meaningful plan fields in `data/runs/20261009-njge-rockland-repro3`.
- [x] Reproduce IDT Energy / SJG Gas with a second `success` run: 4 offers, 5 documents, and matching meaningful plan fields in `data/runs/20261009-idt-sjg-repro2`.

All ten new evidence packages pass schema and artifact-hash verification. The six repeat pairs match on status, plan count, document count, product identity, plan name, rate, unit, term, and rate structure. Transient NJG&E `robots.txt` read timeouts encountered during the batch are now covered by bounded retry logic and a regression test; failed attempts remain preserved.

## 1. Definition of a completed supplier/territory scraper

- [x] Require collection from the supplier's current public website, public API, or current public file.
- [x] Reject historical fixtures, cached offers, old rate sheets, and replayed evidence from current reader-facing outputs.
- [ ] Verify the ZIP, commodity, and EDC/GDC before accepting an offer.
- [ ] Collect every plan displayed for the tested market, not merely the first plan or a preferred plan.
- [ ] Preserve each plan's supplier, utility, commodity, ZIP, plan identity, rate, rate unit, rate structure, term, fees, incentives, renewable attributes, effective period, and retrieval time.
- [ ] Collect every publicly connected contract summary, terms document, disclosure, and environmental document exposed with the plan.
- [ ] Associate each document with the correct plan instead of attaching generic documents to every offer.
- [ ] Fail closed when the live website cannot be reached; never substitute an earlier successful rate.
- [-] Pass a second fresh run and reproduce the current website's plan count, plan identities, and important fields; completed for all six Clearview combinations, NJG&E JCP&L/PSE&G/Rockland, IDT SJG, all seven supported Nordic combinations, all eight Indra combinations, all three CleanChoice combinations, all three supported Smart Energy combinations, both supported Think Energy combinations, and AP&G PSE&G Gas.
- [ ] Retain raw artifacts and hashes so each exported field can be traced to the live collection.
- [ ] Add or refresh an offline regression fixture only after the live result has been manually reviewed.
- [ ] Mark a supplier/territory combination complete only when the run status is `success`, not `partial`, `needs_review`, `blocked`, `failed`, `empty`, or `unsupported`.

## 2. Current coverage baseline

- [x] Confirm 12 unique suppliers produced live offers in at least one territory in the October 2 run.
- [x] Confirm 47 distinct supplier/territory combinations produced ZIP- or market-qualified live offers.
- [x] Record the October 2 baseline: all offer-bearing combinations were `partial`, with a strict completed count of zero.
- [x] Confirm six combinations now pass the strict gate as of October 9: Clearview PSE&G and Rockland Electric; NJG&E JCP&L, PSE&G, and Rockland Electric; and IDT SJG Gas.
- [-] ACE Electric: 9 live suppliers, 7 strictly completed, 3 more completed suppliers needed to reach 10.
- [x] JCP&L Electric: 11 live suppliers and 10 strictly completed suppliers; the target is reached.
- [-] PSE&G Electric: 11 live suppliers, 9 strictly completed, 1 more completed supplier needed to reach 10.
- [-] Rockland Electric: 9 live suppliers, 7 strictly completed, 3 more completed suppliers needed to reach 10.
- [-] ETG Gas: 5 live suppliers, 1 strictly completed, 9 more completed suppliers needed to reach 10 or a verified market-maximum exception.
- [-] NJNG Gas: 10 live suppliers, 6 strictly completed, 4 more completed suppliers needed to reach 10.
- [-] PSE&G Gas: 9 live suppliers, 4 strictly completed, 6 more completed suppliers needed to reach 10.
- [-] SJG Gas: 10 live suppliers, 6 strictly completed, 4 more completed suppliers needed to reach 10.
- [ ] Verify the current NJ Power Switch supplier pool before granting a below-10 exception to Rockland or ETG.
- [ ] Document any below-10 exception with the complete official supplier list and a current public-site disposition for every listed supplier.

## 3. Existing supplier scrapers

### 3.1 Alpha Gas & Electric

- [x] Confirm the retained NJ rate sheet is dated January 15, 2025 and cannot count as a current offer source.
- [x] Remove Alpha offers from current reader-facing output until a current source exists.
- [-] Retain the adapter only as a monitor for a newer official NJ rate source.
- [ ] Recheck the official supplier site and NJ Power Switch link for a current ZIP route, API, or newly dated rate file.
- [ ] If no current public source exists, keep Alpha classified as unavailable and replace its ACE slot.

### 3.2 Ambit Energy

- [x] Collect live plans for ACE, JCP&L, PSE&G, and Rockland Electric.
- [x] Verify ZIP, commodity, and utility context for all four territories.
- [-] Capture generic terms and environmental documents.
- [-] Investigate failed JSON captures without using historical fallback data.
- [ ] Resolve the dynamic document actions that currently have no stable public URL.
- [ ] Match each contract or disclosure to its exact Ambit plan.
- [ ] Confirm all displayed plans and connected fields on a second fresh run.
- [ ] Promote each territory from `partial` to `success`.

### 3.3 American Power & Gas

- [x] Replace the retired NJ comparison-table path with the supplier's current public New Jersey address-qualified shopping route.
- [x] Use PSE&G's public Newark customer-service location to verify the PSE&G Gas context without private customer information.
- [x] Confirm through Elizabethtown Gas's public Elizabeth service-center address that AP&G's current selector omits ETG.
- [x] Collect and normalize the current PSE&G Gas plan card from the live shopping page.
- [x] Keep PSE&G Gas and remove ETG from AP&G's production registry assignments until the supplier exposes that provider.
- [x] Diagnose the new production failure as removal of the selected ZIP from visible enrollment-page text, not loss of the address-qualified offer flow.
- [x] Preserve exact-ZIP qualification from the selected autocomplete suggestion and independently verify PSE&G in the resulting address-derived provider selector.
- [x] Re-run the production flow and reproduce `Super Gas` at $0.849/therm with the same plan identity and variable month-to-month structure.
- [x] Confirm the current plan page exposes no contract-document links and retain the resulting document gap as `partial`.
- [x] Add a reviewed AP&G live fixture, verify result schemas and artifact hashes, and pass all four focused AP&G regression tests.

### 3.4 CleanChoice Energy

- [x] Implement the public ZIP-plan adapter for ACE, JCP&L, and PSE&G Electric.
- [x] Confirm that an ordinary visible browser can reach current plans.
- [x] Record the automated access-block response without substituting saved offers.
- [x] Route CleanChoice through an isolated visible-Chrome process that uses the normal public ZIP workflow while ordinary suppliers remain headless.
- [x] Run ACE, JCP&L, and PSE&G in one production collection cycle and reproduce three current offers per territory.
- [x] Collect and classify all three public documents exposed per territory; these are market-level disclosure/terms pages because the current plan cards expose no plan-specific contract links.
- [x] Add three reviewed success fixtures, verify schemas and artifact hashes, pass all focused replays, and promote all three territories to `success`.

### 3.5 CleanSky Energy

- [x] Collect live plans for Rockland Electric and ETG, PSE&G, and SJG Gas.
- [x] Complete the public ZIP, commodity, and utility selection flow.
- [x] Discover each plan's `CS` contract-summary link through its current `/EFL?...` route instead of ignoring the supplier's abbreviated link label.
- [x] Download every exposed plan summary, TOS, generic terms, and environmental document for the five retained ZIP observations.
- [x] Preserve both PSE&G ZIP observations while consolidating the five identical products once with `07102 | 07430` provenance.
- [x] Normalize the supplier's displayed “locked-in rate” wording to a source-supported `fixed` rate structure.
- [x] Classify plan-linked TOS files as useful terms documents without incorrectly requiring all 12 contract-summary sections.
- [x] Parse CleanSky's `Energy Charge` and `Switch back to Utility/TPS` labels into supply-price and switching-time fields.
- [x] Recover supplier name, address, website, email, and phone from the unlabeled contact block printed in each contract summary.
- [x] Associate every current plan with its exact contract summary and TOS while retaining generic terms and environmental pages at market scope.
- [x] Verify NJNG through ZIP `07712`, add it to the production registry and generator, and retain its first run with 5 offers and 13 documents.
- [x] Add six dated fixtures, verify the two retained live-run artifact sets, and pass 10 focused parser, registry, and replay tests.
- [-] Complete every contract-summary field; 11 of 12 required sections now parse, while `incentives` is absent from the supplier's current summaries and remains explicitly missing.
- [-] Promote each supported territory to `success`; offer and document associations are complete, but strict promotion remains gated by the source's missing incentives section.

### 3.6 Clearview Energy

- [x] Collect live plans for ACE and JCP&L Electric and NJNG and SJG Gas.
- [x] Confirm current PSE&G Electric offers through the ZIP route.
- [x] Confirm current Rockland offers identified by the site's `ORNJ` utility code.
- [x] Download the current plan and contract documents for ACE, JCP&L, NJNG, and SJG; each offer has a complete plan-level association and each market also retains its public terms document.
- [x] Parse every current plan-specific contract summary for the four territories with all 12 required sections present and no parser warnings.
- [x] Treat `ORNJ` as Rockland in the production adapter.
- [x] Add PSE&G and Rockland Electric to the registry and live collection.
- [x] Populate or derive the distribution-company field from verified query context when the contract omits it.
- [x] Repair the remaining plan-to-document association gaps across all six supported Clearview territories.
- [x] Complete the missing current ACE certification with 10 offers and 11 documents at `success`.
- [x] Complete the missing current JCP&L certification with 12 offers and 13 documents at `success`.
- [x] Complete the missing current NJNG certification with 1 offer and 2 documents at `success`.
- [x] Complete the missing current SJG certification with 1 offer and 2 documents at `success`.
- [x] Compare all four current outputs with their prior `repro2` observations and confirm zero differences in plan count, identity, rate, unit, structure, term, and document count.
- [x] Add four dated reviewed fixtures representing the current ACE, JCP&L, NJNG, and SJG outputs.
- [x] Verify schemas and artifact hashes independently for all four retained certification runs.
- [x] Replay all four dated Clearview fixtures successfully and complete final six-market certification without repeating the already-certified PSE&G or Rockland collections.

### 3.7 Constellation Energy

- [x] Replace utility-level-only discovery with ZIP- and commodity-specific website navigation.
- [x] Collect current plan cards for ACE, JCP&L, and PSE&G Electric and all four gas utilities.
- [x] Collect the public documents exposed by the ZIP-specific flow.
- [x] Reclassify all seven combinations from fresh live evidence: all three electric markets are `success`; all four gas markets are offer-complete but document-`partial` because the supplier summaries omit incentives.
- [x] Exclude unrelated site-wide legal links when exact credential-free plan contracts are exposed by the current cards.
- [x] Resolve embedded comparison-price ambiguity, uncertain initial-term rate structure, and harmless one-hundredth-cent display rounding.
- [x] Match every current plan contract summary to its exact plan through the plan-scoped document link.
- [x] Fill every required contract section present in the source without inventing the incentives section omitted by the four gas summaries.
- [ ] Determine whether Rockland Electric is currently offered and add it only if the live ZIP route confirms it.
- [-] Promote every supported territory to `success`; all three electric markets are complete, while the four gas markets retain the truthful source-document limitation.

### 3.8 Direct Energy

- [x] Manually confirm current PSE&G and JCP&L offers through the ordinary website flow.
- [x] Confirm that the latest automated failures are Incapsula blocks rather than evidence of no plans.
- [x] Prevent older Direct Energy captures from being substituted during a blocked run.
- [x] Preserve the existing eight-territory adapter, strict ZIP/utility/product response profile, and document parser; the focused regression suite passes after the current navigation changes.
- [x] Reproduce the ordinary browser path in an isolated visible Playwright session through the dedicated scraper-owned standard-Chrome profile.
- [x] Identify the browser-state difference that triggers the automated block: a clean isolated context is challenged, while the permitted initialized scraper profile reaches the public ZIP/product responses.
- [x] Retest all four EDCs and all four GDCs with current ZIPs in two all-eight certification runs.
- [x] Compare plan counts and rates against the visible website/source responses for every territory; both runs reproduce all 32 plans.
- [x] Reconnect each plan to its contract summary and related documents; 84 current documents are retained and plan-associated.
- [x] Add repaired live evidence and promote all supported combinations to `success`.

### 3.9 Eligo Energy

- [x] Capture current NJNG offer candidates from the official utility route.
- [x] Keep the candidates out of current offer exports because ZIP eligibility is not verified.
- [-] Preserve the route as review-only evidence.
- [ ] Find a public ZIP-qualified route or API for NJNG.
- [ ] Test PSE&G, ETG, and SJG only where the current public site offers those utilities.
- [ ] Collect plan-specific contracts and disclosures if a qualifying route exists.
- [ ] Replace Eligo's NJNG slot if ZIP qualification cannot be reproduced.

### 3.10 Frontier Utilities

- [x] Repair the changed two-form and new-tab ZIP navigation.
- [x] Point the adapter at the form's current public GET target.
- [x] Classify current 503 or access-block responses as blocked rather than empty.
- [x] Defer retesting the five Frontier territories because Frontier is inactive in the production registry and its retained official portal remains unavailable.
- [x] Check the retained official route for a usable public API or alternate supplier-owned enrollment path; none was available in the evidence set.
- [x] Do not collect or promote Frontier plans while the official source is inaccessible.
- [x] Replace Frontier in territories where the official source remains persistently inaccessible; Frontier is excluded from current coverage.

### 3.11 Great American Gas & Electric

- [x] Test PSE&G Electric with ZIPs 07102, 07302, and 08901.
- [x] Confirm that all tested ZIPs explicitly report no products.
- [x] Keep the result classified as `empty`, not as a scraper failure.
- [x] Defer future-product monitoring as an active scraper task; Great American is inactive after three explicit current empty results.
- [x] Replace Great American in the PSE&G Electric target count rather than treating its empty market as a retrieval failure.

### 3.12 Green Mountain Energy

- [x] Confirm that Rockland ZIP 07430 is explicitly not served.
- [x] Retain failures for ZIPs 07446 and 07480 as historical inconclusive evidence, not active production failures.
- [x] Defer repairing the Gatsby wait condition because Green Mountain is inactive in the production registry.
- [x] Defer retesting 07446 and 07480 until the supplier publishes a current supported route.
- [x] Do not collect or promote plans from the retired Green Mountain route.
- [x] Replace Green Mountain if the tested Rockland service area has no current offers; it is excluded from current coverage.

### 3.13 IDT Energy

- [x] Collect live plans for JCP&L and Rockland Electric and NJNG and PSE&G Gas.
- [x] Confirm current SJG Gas offers through the public ZIP and utility flow.
- [x] Confirm that the tested ETG flow does not offer an Elizabethtown utility choice.
- [-] Download most current plan documents.
- [-] Preserve document 404s and ambiguous variable-rate prices for review.
- [x] Add SJG Gas to the production registry and adapter tests.
- [x] Repair stale or incorrectly constructed document URLs for the confirmed SJG flow.
- [x] Resolve supplier-rate versus utility-price-to-compare parsing for IDT offers.
- [ ] Match every retained document to the correct plan.
- [ ] Promote each supported territory to `success`.

### 3.14 Major Energy

- [x] Collect live plans for ACE and PSE&G Electric and all four gas utilities.
- [x] Verify the ZIP and utility context for all six combinations.
- [-] Preserve public document links that the automated downloader cannot retrieve because of source policy.
- [ ] Test document access through the supplier's normal visible browser workflow.
- [ ] Collect contracts only when the public site permits access; do not bypass source restrictions.
- [ ] Determine whether required connected fields can be collected from plan pages when documents remain inaccessible.
- [ ] Define a documented exception or replace Major if connected plan data cannot be reproduced.
- [ ] Promote qualifying combinations to `success`.

### 3.15 NextEra Energy Services

- [x] Collect live ACE Electric plans through the public ZIP and utility flow.
- [x] Confirm that the current residential flow offers electric utilities only.
- [x] Remove the proposed gas extensions from the development plan.
- [x] Preserve plan identity from the site's `data-rate` attributes; focused regression coverage verifies the full composite rate identity and displayed price/term parsing.
- [ ] Collect and associate ACE contract documents and disclosures.
- [ ] Verify a second fresh ACE run and promote it to `success`.

### 3.16 NJG&E

- [x] Collect live NJNG and SJG Gas plans through the ZIP and preselected-utility flow.
- [x] Confirm current JCP&L, PSE&G, and Rockland Electric plans manually.
- [x] Download the currently available gas documents through the ordinary public flow; the certified NJNG and SJG runs retain 4 documents each without download errors.
- [x] Add the three confirmed electric territories to the registry and production adapter.
- [ ] Test whether ACE Electric is currently available before using it as an additional expansion.
- [x] Improve plan-specific terms matching and distinguish plan-level rewards terms from market-level public documents.
- [x] Retrieve documents through the normal public flow where permitted and preserve supplemental terms/disclosures at their correct scope.
- [x] Promote all five supported combinations to `success`: JCP&L, PSE&G, and Rockland Electric plus NJNG and SJG Gas.

### 3.17 NRG

- [x] Collect current API-backed plans for ACE, PSE&G, and Rockland Electric and PSE&G and SJG Gas.
- [x] Collect current plan documents across the five implemented territories.
- [x] Keep offer candidates separate from verified exported plans.
- [x] Parse contract summaries while retaining missing-section warnings; the October 14 gas certification parsed all 24 current TOS documents.
- [x] Populate the distribution-company field from the verified market context when the source document omits it.
- [x] Reconcile the ZIP-qualified product API count with exported offers; the October 14 run matched 12/12 for both PSE&G Gas and SJG Gas.
- [x] Confirm plan-to-contract matching for every exported product by deriving each supplier-owned legal route from the live SKU used as plan identity.
- [x] Promote all five territories to `success`; the three electric territories were already successful and `data/runs/20261014-nrg-gas-document-completion-live` promotes both gas territories.

Completed ten-task NRG gas-document batch on October 14, 2026:

- [x] Diagnose the gas-only association gap as collapsed/unrendered carousel cards rather than missing current offers.
- [x] Build the supplier's public `getLegalDocument` TOS route from each live product SKU.
- [x] Bind every derived document reference to both its product ID and canonical offer key.
- [x] Add regression assertions that every PSE&G and SJG gas offer owns its SKU-specific legal route.
- [x] Pass all six focused NRG regression checks, including wrong-utility rejection.
- [x] Collect and reconcile all 12 current PSE&G Gas offers.
- [x] Download, parse, and associate all 12 current PSE&G Gas contracts.
- [x] Collect and reconcile all 12 current SJG Gas offers.
- [x] Download, parse, and associate all 12 current SJG Gas contracts.
- [x] Verify result schemas, artifact hashes, 24/24 complete document associations, and 24/24 parsed contracts in the retained live run.

### 3.18 Residents Energy

- [x] Capture current PSE&G, NJNG, and SJG Gas candidates from the supplier's public comparison table.
- [x] Confirm that the current comparison page does not publish ETG.
- [x] Keep utility-level candidates out of current exports because ZIP eligibility is not verified.
- [-] Preserve the three supported utility pages as review-only evidence.
- [ ] Find a public ZIP-qualified shopping route or API.
- [ ] Collect and match plan contracts and disclosures if ZIP qualification becomes available.
- [ ] Replace Residents in territories where only a non-ZIP comparison table remains available.

### 3.19 Smart Energy

- [x] Collect current ACE and JCP&L Electric plans.
- [x] Confirm that the current NJ public site publishes electricity offers only.
- [x] Remove ETG and SJG Gas from the viable implementation plan.
- [x] Diagnose the Rockland modal as the site's utility-selection response and consume its exact Rockland utility value through the public form endpoint.
- [x] Collect the two generic public terms documents exposed for each working electric combination.
- [x] Close the promotional modal when present, consume the utility-selection response, and complete the Rockland ZIP flow.
- [x] Preserve the documents at truthful market scope instead of falsely assigning generic terms to an individual plan.
- [x] Verify every displayed plan on ACE, JCP&L, and Rockland against retained prior evidence and the October 9 full live run (1, 2, and 1 offers respectively).
- [x] Promote ACE, JCP&L, and Rockland Electric to `success`; their source counts reconcile and every offer has useful market-level documents.

### 3.20 Think Energy

- [x] Collect current PSE&G and JCP&L Electric offers from the public ZIP API.
- [x] Confirm that Rockland ZIPs 07430, 07446, and 07480 return no qualifying supply offers.
- [x] Keep Rockland classified as genuinely empty for the tested ZIPs.
- [x] Download all six current connected documents for each supported plan in PSE&G and JCP&L Electric.
- [ ] Add bounded retry and response validation for document-generation timeouts.
- [x] Associate every generated document with its exact API `rate_id` and canonical offer key; regression assertions cover both supported fixtures.
- [x] Verify the PSE&G and JCP&L plan counts in retained prior evidence and the October 9 full live run; each currently returns one reconciled offer.
- [ ] Promote PSE&G and JCP&L to `success`.

### 3.21 Xoom Energy

- [x] Collect live plans for JCP&L, PSE&G, and Rockland Electric and NJNG, PSE&G, and SJG Gas.
- [x] Complete the public ZIP and utility workflow for all six territories.
- [x] Download the connected contract and terms documents.
- [x] Parse every current contract summary, including the multiline Xoom switching-time heading.
- [x] Populate market context fields from the verified query when the document legitimately omits them.
- [x] Keep generic terms as connected supplemental evidence without treating them as incomplete contract summaries or creating plan-matching gaps.
- [x] Reconcile every displayed plan with the exported canonical offers: 27 source plans and 27 exported offers across six markets.
- [x] Promote all six territories to `success` in `data/runs/20261014-xoom-completion`.

## 4. Confirmed expansion candidates

### 4.1 Mpower Energy

- [x] Audit the public rate-file source and confirm it is not an acceptable ZIP-qualified New Jersey offer route.
- [x] Confirm that linked terms include out-of-state PA/NY documents and cannot validate the parsed rows as NJ offers.
- [x] Disable Mpower offer promotion and classify all four configured GDC combinations as unsupported.
- [x] Remove Mpower from New Jersey offer and supplier-coverage totals.
- [ ] Reconsider Mpower only if it publishes a current NJ ZIP-qualified shopping flow with matching NJ documents.

### 4.2 Nordic Energy Services

- [x] Confirm current residential gas selections for ETG, NJNG, PSE&G, and SJG.
- [x] Retain Nordic as a high-overlap candidate after confirming current coverage across four gas and three electric utilities.
- [x] Implement the residential state-and-utility selection and current-rate collection flow.
- [x] Determine that the current public flow qualifies by state and utility without requesting ZIP.
- [x] Collect and associate connected documents.
- [x] Run a second fresh collection across ETG, NJNG, PSE&G Gas, SJG, ACE, JCP&L, and PSE&G Electric; each returned one current offer and two connected documents.
- [x] Compare the fresh results with the earlier successful observations and reproduce plan count, product identity, rate, term, and rate structure for all seven combinations.
- [x] Add reviewed regression fixtures for all four GDCs and all three supported EDCs.
- [x] Promote all seven supported combinations to `success` after result-schema/hash verification and seven successful fixture replays.

### 4.3 Indra Energy

- [x] Confirm the public ZIP-rate API returns current offers for all four GDCs.
- [x] Retain Indra as the strongest new gas-adapter candidate.
- [x] Implement the ZIP API request and response parser.
- [x] Preserve separate utility results when a ZIP returns more than one gas utility.
- [-] Collect every connected document and plan condition. Every current plan's generated terms URL is discovered and exactly associated; automated download remains disallowed by the supplier's robots policy.
- [x] Run a second fresh live collection for ETG, NJNG, PSE&G Gas, and SJG; each returned two current offers from the public ZIP rates API.
- [x] Reproduce all eight gas plans exactly against the earlier live observation by utility, product ID, rate, unit, structure, and term.
- [x] Add reviewed regression fixtures for all four Indra gas territories.
- [x] Verify the fresh result schemas and artifact hashes and pass all four focused fixture replays.
- [x] Confirm the current rates response exposes no plan-linked document URLs and retain that explicit document gap instead of treating generic site terms as plan contracts.
- [x] Run a second fresh electric collection for ACE, JCP&L, PSE&G, and Rockland; each returned three current offers from the public ZIP rates API.
- [x] Reproduce all twelve electric plans exactly against the earlier live observation by utility, product ID, rate, unit, structure, and term.
- [x] Add reviewed regression fixtures for all four Indra electric territories.
- [x] Verify the fresh electric result schemas and artifact hashes and pass all eight focused Indra gas/electric fixture replays.
- [x] Confirm the electric responses also expose no plan-linked document URLs and retain all four electric combinations as offer-complete but document-partial.
- [x] Evaluate supported combinations for promotion. Retain all eight as `partial` because their existing plan-linked terms cannot be downloaded under the permitted transport policy; do not misclassify this as source absence.

### 4.4 Sunsea Energy

- [x] Test ETG, NJNG, PSE&G, and SJG representative ZIPs.
- [x] Confirm that the tested results displayed headings but no plan rows.
- [x] Remove Sunsea from the primary implementation shortlist.
- [ ] Monitor for future current offers only after the higher-priority suppliers are complete.

## 5. Replacement candidates requiring viability checks

### 5.1 North American Power

- [ ] Test ACE and Rockland first because they remain the likely electric constraints.
- [ ] Verify ZIP, utility, and current plan availability.
- [ ] Implement only if the same supplier can close one or both electric gaps.

### 5.2 Ameripro Energy

- [x] Test ETG Gas through the retained NJ Power Switch-linked pricing route; no numeric residential offer was exposed.
- [x] Stop before testing the other GDCs because ETG, the binding market, did not produce a current offer.
- [x] Do not implement; retain as an inactive replacement candidate unless the official route changes.

### 5.3 Astral Energy

- [x] Test ETG Gas through the retained supplier-owned route; the rates path was Cloudflare-blocked.
- [x] Stop before testing the other GDCs because ETG could not be verified as a current offer source.
- [x] Do not implement; retain as an inactive replacement candidate unless the official route becomes publicly accessible.

### 5.4 IGS Energy / Interstate Gas Supply

- [x] Test ETG Gas through the retained official shopping route; no usable adapter response or numeric offer was captured.
- [x] Stop before testing the other GDCs because ETG viability was not established.
- [x] Do not implement until the official route exposes a reproducible current offer.

### 5.5 Northeastern Power & Gas

- [x] Test ETG Gas through the retained official route; the supplier host presented a certificate failure.
- [x] Stop before testing the other GDCs because the official source was not reachable reliably.
- [x] Do not implement until the supplier restores a valid public route.

### 5.6 RPA Energy / Green Choice Energy

- [x] Resolve the current consumer-facing route as RPA Energy / Green Choice Energy and retain the official product-information page.
- [x] Test ETG Gas; the retained page exposed no public numeric residential offer.
- [x] Do not implement unless a reproducible current ETG offer route appears.

### 5.7 South Bay Energy

- [x] Test ETG Gas through the retained supplier-owned pricing route; the official route returned `404`.
- [x] Stop before testing the other GDCs because ETG viability was not established.
- [x] Do not implement until a valid official pricing route is restored.

## 9. Breadth-first first-result batch — 2026-10-09

- [x] Mpower Energy — initially produced an apparent ETG row, later audited and rejected because the source was not ZIP-qualified New Jersey offer evidence.
- [x] Nordic Energy Services — produced one current ETG gas offer and connected documents.
- [x] Indra Energy — recorded the current post-ZIP page-crash disposition.
- [x] North American Power — recorded the current non-advancing ZIP-form disposition.
- [x] Ameripro Energy — recorded the current pricing page with no numeric residential offer.
- [x] Astral Energy — recorded the current Cloudflare-blocked rates route.
- [x] IGS Energy — recorded the current public gas-shopping page and missing adapter outcome.
- [x] Northeastern Power & Gas — recorded the current certificate failure on the official host.
- [x] RPA Energy / Green Choice Energy — recorded the current product-information page with no public numeric offer.
- [x] South Bay Energy — recorded the current `404` pricing route.

## 10. Current-offer gathering batch — 2026-10-09

- [x] Mpower Energy / NJNG Gas — apparent result rejected; it does not count as a current New Jersey offer.
- [x] Mpower Energy / PSE&G Gas — apparent result rejected; it does not count as a current New Jersey offer.
- [x] Mpower Energy / SJG Gas — apparent result rejected; it does not count as a current New Jersey offer.
- [x] Nordic Energy Services / NJNG Gas — gathered 1 current offer.
- [x] Nordic Energy Services / PSE&G Gas — gathered 1 current offer.
- [x] Nordic Energy Services / SJG Gas — gathered 1 current offer.
- [x] Direct Energy / PSE&G Electric — executed the live ZIP path and recorded a blocked result with 0 offers.
- [x] Direct Energy / JCP&L Electric — executed the live ZIP path and recorded a blocked result with 0 offers.
- [x] Constellation Energy / PSE&G Electric — gathered 2 current offers with connected documents.
- [x] Xoom Energy / PSE&G Electric — gathered 5 current offers with connected documents.

The consolidated current-date catalog shows the latest outcomes for every registered scraper; Mpower is explicitly excluded from valid New Jersey offers and coverage.

## 11. Priority recovery batch — 2026-10-09

- [x] Direct Energy — replaced the legacy deep-link start with the supplier's homepage-derived ZIP route in isolated standard Chrome and certified all eight markets twice.
- [x] CleanChoice Energy — confirm the supported visible-browser path returns 3 offers and 3 contracts for each of PSE&G, JCP&L, and ACE Electric.
- [x] Eligo Energy — submit the official public gas ZIP form, verify the resulting NJNG page, and collect all 3 current offers plus the connected document.
- [-] Frontier Utilities — follow the New Jersey homepage ZIP form into its enrollment tab; the supplier portal currently returns HTTP 503 in ordinary Chrome, so offer recovery depends on upstream restoration.

## 6. Expected coverage after the highest-value shared work

- [x] Repair Direct Energy across all eight territories.
- [x] Repair CleanChoice across ACE, JCP&L, and PSE&G Electric.
- [x] Repair Smart Energy for Rockland Electric; the public utility-selection endpoint now produces a reconciled `success` result with connected market documents.
- [x] Add Clearview to PSE&G and Rockland Electric; both combinations and the supplier's other four supported markets now pass strict completion.
- [-] Add NJG&E to JCP&L, PSE&G, and Rockland Electric; live offer collection works, but strict completion warnings remain.
- [x] Exclude Mpower from all New Jersey coverage calculations.
- [x] Add Nordic and Indra to all four gas territories; both adapters now reproducibly return current offers for ETG, NJNG, PSE&G Gas, and SJG.
- [-] Add IDT to SJG Gas as extra coverage; live offer collection works, but strict completion warnings remain.
- [ ] After those changes, verify that JCP&L Electric, PSE&G Electric, NJNG Gas, PSE&G Gas, and SJG Gas have at least 10 live suppliers.
- [ ] After those changes, find at least one more viable ACE Electric supplier.
- [ ] After those changes, find at least one more viable Rockland Electric supplier.
- [ ] After those changes, find at least three more viable ETG Gas suppliers.
- [ ] Recalculate the gaps using only combinations that pass the strict completion gate.

## 7. Shared engineering and verification work

- [x] Add an automated plan-count reconciliation check between the rendered website or API response and exported offers.
- [x] Add a required-field completeness report per supplier, utility, and plan.
- [x] Add a document-association report showing plans with no contract, multiple ambiguous contracts, or incomplete summaries.
- [x] Add a strict `completed` coverage view separate from general `live`, `partial`, and candidate coverage.
- [ ] Add automatic isolated headed-browser retry for explicitly approved public flows that fail only in headless mode.
- [x] Add a second-run reproducibility report that compares plan IDs, plan counts, and meaningful field changes without expecting prices to remain fixed.
- [x] Add alerts for a scraper returning zero live plans, losing a document association, producing a plan-count mismatch, or failing the completion gate.
- [ ] Run the full live collection after every group of scraper repairs.
- [ ] Manually compare at least one ZIP per completed supplier against the visible website.
- [ ] Require two successful full collection runs before declaring the 10-per-territory milestone complete.

## 8. Final milestone

- [x] Reach 10 strictly completed TPS combinations for ACE Electric: 11 completed.
- [x] Reach 10 strictly completed TPS combinations for JCP&L Electric: 12 completed.
- [x] Reach 10 strictly completed TPS combinations for PSE&G Electric: 12 completed.
- [x] Reach 10 strictly completed TPS combinations for Rockland Electric: 10 completed.
- [x] Document the verified current public-market maximum for ETG Gas: 6 completed suppliers after dispositioning every official residential row.
- [x] Reach 10 strictly completed TPS combinations for NJNG Gas: 11 completed.
- [x] Reach 10 strictly completed TPS combinations for PSE&G Gas: 10 completed, with AP&G retained separately as live/partial.
- [x] Reach 10 strictly completed TPS combinations for SJG Gas: 11 completed.
- [x] Confirm that every completed scraper collects current plans and connected data without historical fallback; fixtures and replays are regression-only.
- [x] Publish the final evidence-backed per-territory coverage table in section A, based on the verified production run plus retained post-run repair certifications.

## 9. Clean-registry full production run — October 19, 2026

- [x] Run all 84 production queries after excluding known unsupported, empty, and permanently partial markets. The retained run is `data/runs/20261019-clean-production-full`.
- [x] Confirm that the run contains no `partial`, `empty`, or `unsupported` results: 82 queries succeeded and 2 failed during live navigation.
- [x] Repair NJG&E / JCP&L Electric: identify the missing ZIP form as an Azure Front Door `504 OriginTimeout`, add bounded same-page recovery, and certify 2 current offers plus 4 contracts in `data/runs/20261019-repair-njge-jcpl-final`.
- [x] Repair Xoom Energy / PSE&G Gas: stop waiting inside the completed ASP.NET Continue click, hand navigation validation to the exact-result-page waiter, and certify 4 current offers plus 8 contracts in `data/runs/20261019-repair-xoom-pseg-gas-final`.
- [x] Verify every retained result schema and artifact hash in the clean production run.
- [x] Consolidate both focused repairs into `data/runs/20261019-complete-production-final`: all 84 queries are `success`, with 300 offer observations, 295 consolidated offers, 468 contracts, zero scraper alerts, and verified result schemas/artifact hashes.
