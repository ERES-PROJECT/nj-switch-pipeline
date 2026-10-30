# American Power & Gas PSE&G document availability — October 17, 2026

## Decision

The current American Power & Gas (AP&G) PSE&G Gas offer remains a reproducible
`partial` result.  The public flow exposes the current offer, but it does not
expose a plan-connected contract, disclosure, or terms document before customer
information is required.  The scraper must not substitute AP&G's site-wide Terms
of Use or a stale/unrelated agreement.

## Current offer

| Field | Observed value |
|---|---|
| Supplier | American Power & Gas |
| Utility | PSE&G Gas |
| ZIP evidence | `07102`, selected through PSE&G's public Newark service-center address |
| Plan | Super Gas |
| Rate | `0.849 USD/therm` |
| Structure | Variable |
| Term | Month-to-month |
| Plan count | One source plan and one exported plan |

The offer was reproduced in
`data/runs/20261017-apg-pseg-certification-3` and the plan-selection transition
was inspected in `data/runs/20261017-apg-document-transition-probe-5`.

## Bounded public-flow audit

The retained probe follows only these public steps:

1. Enter PSE&G's public Newark service-center address in AP&G's public address
   autocomplete.
2. Select the returned `07102` suggestion and verify the address-derived PSE&G
   gas provider option.
3. Display the current residential gas plan and select `Super Gas`.
4. Advance to `/enrollment/customer-contact-info` without entering or submitting
   any customer information.
5. Inspect rendered links and responses for contract, agreement, disclosure,
   terms, or PDF evidence.

The selected plan remains on `/enrollment/plans`, then the ordinary next action
opens `/enrollment/customer-contact-info`.  Neither rendered state contains a
document-like link.  The only document-like network name is the site's
`contractStatusModal` JavaScript asset; it is application code, not a customer
agreement or disclosure.

Retained evidence:

- `data/runs/20261017-apg-document-transition-probe-5/evidence.json`
- `data/runs/20261017-apg-document-transition-probe-5/preselection.html`
- `data/runs/20261017-apg-document-transition-probe-5/postselection.html`
- `data/runs/20261017-apg-document-transition-probe-5/contact-page.html`
- `tools/probe_apg_plan_documents.py`

## Other apparent documents rejected

AP&G's footer “Terms and Conditions” is a site-use policy.  It is not the retail
gas supply agreement for `Super Gas`, so it cannot satisfy plan-document
completeness.

Web search also indexed an AP&G-owned file named `NJ_G_V_SJG.pdf`, described as
a New Jersey variable-gas sales agreement revised `2025-09-12`.  A fresh request
to that official URL now returns `404 Not Found`.  More importantly, the file is
named for SJG and is not linked by the current PSE&G shopping flow.  It therefore
cannot be silently attached to the PSE&G offer even if an archived copy exists.

## Completion consequence

AP&G remains live and useful for current-offer coverage, but it does not count as
strictly completed PSE&G Gas coverage under the project's evidence rules.  PSE&G
Gas therefore remains at 10 live suppliers and 9 strictly completed suppliers.
Reconsider AP&G only when its current public flow exposes a plan-connected
agreement before private enrollment data is required, or replace this strict
coverage slot with another supplier that does.
