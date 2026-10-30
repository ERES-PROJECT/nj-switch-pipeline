# Full live scraper run — 2026-10-09

One headless live pass was run across all 105 registered supplier/utility/ZIP combinations. No retry runs or historical offer fallback were used.

## Run totals

| Measure | Result |
|---|---:|
| Registered combinations attempted | 105 |
| Supplier scrapers returning offers | 14 |
| Supplier scrapers returning no offers | 17 |
| Canonical current offers | 251 |
| ZIP-level offer observations | 256 |
| Successful or partial queries | 61 |
| Blocked queries | 16 |
| Failed queries | 12 |
| Empty queries | 6 |
| Needs-review queries | 5 |
| Unsupported queries | 5 |

## Scrapers returning current offers

Counts below are canonical offers after duplicate observations were consolidated.

| Supplier | Current offers | Run status |
|---|---:|---|
| Ambit Energy | 16 | success / partial |
| CleanSky Energy | 18 | partial |
| Clearview Energy | 42 | success |
| Constellation Energy | 12 | partial |
| IDT Energy | 24 | success |
| Major Energy | 13 | partial |
| Mpower Energy | 4 | partial |
| NextEra Energy Services | 2 | partial |
| NJG&E | 6 | mixed: success / partial / failed |
| Nordic Energy Services | 4 | success |
| NRG | 77 | success / partial |
| Smart Energy | 4 | success on electric; unsupported on gas |
| Think Energy | 2 | success on PSE&G and JCP&L; empty on Rockland |
| Xoom Energy | 27 | partial |

## Scrapers returning no offers

| Supplier | Outcome in this run | Next classification |
|---|---|---|
| Alpha Gas & Electric | unsupported | No public offer route without account access |
| American Power & Gas | needs review / unsupported | Review public route and market eligibility |
| Ameripro Energy | failed | Implement or repair collection path |
| Astral Energy | failed | Access-blocked route needs investigation |
| CleanChoice Energy | blocked | Headless/browser-access repair |
| Direct Energy | blocked | Repair automated browser path; manually verifiable |
| Eligo Energy | needs review | Documents found, but no verified ZIP-qualified offer |
| Frontier Utilities | blocked | Repair automated browser path |
| Great American Gas & Electric | empty | Documents found, but no offers displayed |
| Green Mountain Energy | failed / unsupported | Reassess Rockland ZIP workflow |
| IGS Energy | failed | Implement or repair collection path |
| Indra Energy | failed | Repair post-ZIP/API collection path |
| North American Power | failed | Repair or complete Rockland path |
| Northeastern Power & Gas | failed | Official-host access failure |
| Residents Energy | needs review | Utility-level material is not ZIP-qualified |
| RPA Energy / Green Choice Energy | failed | Locate a current public numeric-offer route |
| South Bay Energy | failed | Current configured pricing route is unavailable |

## Territory coverage in this run

| EDC/GDC | Suppliers returning offers | ZIP-level offers |
|---|---:|---:|
| ACE Electric | 7 | 39 |
| JCP&L Electric | 7 | 31 |
| PSE&G Electric | 8 | 47 |
| Rockland Electric | 8 | 45 |
| ETG Gas | 5 | 10 |
| NJNG Gas | 7 | 15 |
| PSE&G Gas | 8 | 35 |
| SJG Gas | 10 | 34 |

## Important interpretation

- `partial` means current offers were gathered but the scraper still has document, field-completeness, or reconciliation work.
- `blocked` and `failed` describe this automated run, not proof that the supplier has no current offers.
- `empty` means the public route completed but returned no verified offer for the tested ZIP.
- NJG&E returned offers in three territories but failed for JCP&L and NJNG during this full run, so it belongs in the reliability-repair queue.
