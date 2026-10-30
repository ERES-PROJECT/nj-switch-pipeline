# Full live scraper recheck — 2026-10-09

This summary excludes Mpower Energy. Its four parsed rows came from a non-ZIP-qualified rate file with out-of-state linked terms and do not count as New Jersey offers.

## Corrected totals

| Measure | Previous full run | Recovery recheck | Change |
|---|---:|---:|---:|
| Valid supplier scrapers returning offers | 13 | 15 | +2 |
| Canonical current offers | 247 | 259 | +12 |
| ZIP-level offer observations | 252 | 264 | +12 |

## Coverage by EDC/GDC

| EDC/GDC | Previous suppliers | Current suppliers | Current offer observations | Change |
|---|---:|---:|---:|---:|
| ACE Electric | 7 | 8 | 42 | +1 |
| JCP&L Electric | 7 | 9 | 36 | +2 |
| PSE&G Electric | 8 | 9 | 50 | +1 |
| Rockland Electric | 8 | 8 | 45 | 0 |
| ETG Gas | 4 | 4 | 9 | 0 |
| NJNG Gas | 6 | 8 | 19 | +2 |
| PSE&G Gas | 7 | 6 | 30 | -1 |
| SJG Gas | 9 | 9 | 33 | 0 |

## Recovery results

| Priority supplier | Result |
|---|---|
| CleanChoice Energy | Recovered: 3 offers each for ACE, JCP&L, and PSE&G Electric; 9 total |
| Eligo Energy | Recovered: 3 ZIP-qualified NJNG Gas offers |
| Direct Energy | Still failed in all eight configured combinations in the fresh automated Chrome profile |
| Frontier Utilities | Still blocked by the supplier enrollment portal's HTTP 503 response |

## Additional changes observed

- NJG&E succeeded in all five configured territories in this recheck, contributing 10 canonical offers.
- Xoom Energy failed on PSE&G Gas after finding one contract, reducing that territory by one supplier and four offers.
- No valid territory has reached 10 suppliers yet. JCP&L Electric, PSE&G Electric, and SJG Gas are closest at 9 each.
