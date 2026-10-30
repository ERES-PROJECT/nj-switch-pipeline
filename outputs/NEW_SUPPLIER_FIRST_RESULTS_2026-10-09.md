# New supplier first-result pass — 2026-10-09

This is a breadth-first pass: one current attempt per supplier. It records offer rows where the public route produced them and records the concrete live-source disposition otherwise. Repeatability and full-field completeness are intentionally deferred.

| Supplier | Test market | Current first result | Offers | Current data found | Next scraper action |
|---|---|---:|---:|---|---|
| Mpower Energy | ETG Gas / `07201` | Partial | 1 | `$0.890/therm`, fixed, 12 months; official NJ terms/disclosure links captured | Add the other three GDC rows; decide how to label utility-table eligibility because the source does not request ZIP |
| Nordic Energy Services | ETG Gas / `07201` | Success | 1 | `$0.549/therm`, fixed, 2 months; product ID `4808`; two connected documents captured | Add the other three GDC rows |
| Indra Energy | ETG Gas / `07201` | Blocked | 0 | ZIP form loaded, but the current signup page crashed after the ZIP action | Implement its public rate API directly instead of depending on the crashing page |
| North American Power | Rockland Electric / `07430` | Needs adapter | 0 | ZIP form loaded, but the current form did not advance in the automated/browser attempt | Trace the ZIP form/AJAX request and implement that route |
| Ameripro Energy | ETG Gas / `07201` | Empty public pricing page | 0 | Official pricing URL loaded but exposed no numeric residential offer | Inspect its scripts/network calls; do not count it yet |
| Astral Energy | ETG Gas / `07201` | Blocked | 0 | Official rates route returned a Cloudflare block page | Try a normal visible-browser route or a permitted official feed |
| IGS Energy | ETG Gas / `07201` | Needs adapter | 0 | Official gas shopping page loaded, but the generic collector did not reach a ZIP-qualified result | Trace the `Check Rates & Availability` flow/API |
| Northeastern Power & Gas | ETG Gas / `07201` | Blocked | 0 | `www.nepower.com` failed hostname certificate verification in the collector | Test the canonical non-`www` host and then trace the ZIP route |
| RPA Energy / Green Choice Energy | ETG Gas / `07201` | No public numeric offer | 0 | Current site describes fixed/variable products but exposes only contact/call enrollment, not rates | Do not count unless a supplier-owned public price route is found |
| South Bay Energy | ETG Gas / `07201` | Dead pricing route | 0 | NJ Power Switch's supplier pricing URL returned `404 Not Found` | Resolve a replacement official pricing route before adapter work |

## Output locations

- Parsed Mpower and Nordic offer rows: `data/runs/20261009-new-suppliers-offers-first-output/offers.csv`
- Full Mpower and Nordic evidence: `data/runs/20261009-new-suppliers-offers-first-output/`
- First-pass evidence for all ten routes: `data/runs/20261009-new-suppliers-first-results-live/`

