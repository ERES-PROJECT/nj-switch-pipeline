# NJ TPS candidate availability check

Tested September 30, 2026.

## What counts as working

A combination passes only when the supplier's current public site returns a plan, rate, or usable market-specific shopping result for the proposed utility. Being licensed or listed by NJ Power Switch is not enough by itself.

Representative ZIPs:

| Utility | ZIP |
|---|---|
| JCP&L Electric | `07701` |
| PSE&G Electric | `07102` |
| Rockland Electric | `07430` |
| ETG Gas | `07201` |
| NJNG Gas | `07712` |
| PSE&G Gas | `07102` |
| SJG Gas | `08094` |

Some suppliers publish utility-specific rates instead of accepting ZIPs. Those combinations are marked **utility-level pass** because the exact GDC and a current plan were still confirmed.

## Electric results

| Supplier | Utility | ZIP | Result | Evidence |
|---|---|---:|---|---|
| Alpha Gas & Electric | JCP&L | `07701` | **Fail** | Current public NJ rate sheet supports ACE only. |
| Alpha Gas & Electric | PSE&G | `07102` | **Fail** | Current public NJ rate sheet supports ACE only. |
| Alpha Gas & Electric | Rockland | `07430` | **Fail** | Current public NJ rate sheet supports ACE only. |
| Clearview Energy | PSE&G | `07102` | **Pass** | ZIP result returned 12 electric offers. |
| Clearview Energy | Rockland | `07430` | **Pass** | ZIP result returned six ORNJ/Rockland electric offers, including 6-, 9-, 12-, 18-, and 24-month products. The existing parser missed these because it does not yet treat `ORNJ` as Rockland. |
| NJG&E | JCP&L | `07701` | **Pass** | Selecting JCPL returned current Power Lock Green electricity plans. |
| NJG&E | PSE&G | `07102` | **Pass** | Selecting PSEG returned current Power Lock Green electricity plans. |
| NJG&E | Rockland | `07430` | **Pass** | Selecting Rockland Electric returned current Power Lock Green electricity plans. |

### Electric conclusion

| EDC | Current | Confirmed additions | Confirmed total | Still needed |
|---|---:|---|---:|---:|
| ACE | 10 | None needed | 10 | 0 |
| JCP&L | 9 | NJG&E | 10 | 0 |
| PSE&G | 8 | Clearview, NJG&E | 10 | 0 |
| Rockland | 7 | Clearview, NJG&E | 9 | **1** |

Do not develop the Alpha extensions from the original proposal. One replacement supplier is still required for Rockland.

## Gas results

| Supplier | Utility | ZIP | Result | Evidence |
|---|---|---:|---|---|
| IDT Energy | ETG | `07201` | **Fail** | Gas flow did not provide an Elizabethtown utility choice. |
| IDT Energy | SJG | `08094` | **Pass** | ZIP and SJG selection returned four gas offers. |
| Residents Energy | ETG | `07201` | **Fail** | Current NJ comparison page does not publish ETG. |
| NextEra Energy Services | ETG | `07201` | **Fail** | Residential ZIP flow asks for an electric utility only. |
| NextEra Energy Services | NJNG | `07712` | **Fail** | Residential ZIP flow asks for an electric utility only. |
| NextEra Energy Services | PSE&G | `07102` | **Fail** | Residential ZIP flow asks for an electric utility only. |
| NextEra Energy Services | SJG | `08094` | **Fail** | Residential ZIP flow asks for an electric utility only. |
| Mpower Energy | ETG | `07201` | **Utility-level pass** | Current NJ table publishes an ETG gas plan at `$0.890/therm`. |
| Mpower Energy | NJNG | `07712` | **Utility-level pass** | Current NJ table publishes an NJNG gas plan at `$0.890/therm`. |
| Mpower Energy | PSE&G | `07102` | **Utility-level pass** | Current NJ table publishes a PSE&G gas plan at `$0.890/therm`. |
| Mpower Energy | SJG | `08094` | **Utility-level pass** | Current NJ table publishes a South Jersey gas plan at `$0.890/therm`. |
| Nordic Energy Services | ETG | `07201` | **Utility-level pass** | Residential ETG selection returned a 2-month fixed plan at `$0.649/therm`. |
| Nordic Energy Services | NJNG | `07712` | **Utility-level pass** | Residential NJNG selection returned a 2-month fixed plan at `$0.4490/therm`. |
| Nordic Energy Services | PSE&G | `07102` | **Utility-level pass** | Residential PSEG Gas selection returned a 2-month fixed plan at `$0.3490/therm`. |
| Nordic Energy Services | SJG | `08094` | **Utility-level pass** | Residential South Jersey Gas selection returned a 2-month fixed plan at `$0.5490/therm`. |
| Indra Energy | ETG | `07201` | **Pass** | Public ZIP-rate API returned four gas offers, including two for Elizabethtown Gas. |
| Indra Energy | NJNG | `07712` | **Pass** | Public ZIP-rate API returned two NJNG gas offers. |
| Indra Energy | PSE&G | `07102` | **Pass** | Public ZIP-rate API returned two PSE&G gas offers. |
| Indra Energy | SJG | `08094` | **Pass** | Public ZIP-rate API returned two SJG gas offers. |
| Sunsea Energy | ETG | `07201` | **Fail** | ZIP result returned the rate-table headings but no plan rows. |
| Sunsea Energy | NJNG | `07712` | **Fail** | ZIP result returned the rate-table headings but no plan rows. |
| Sunsea Energy | PSE&G | `07102` | **Fail** | ZIP result returned the rate-table headings but no plan rows. |
| Sunsea Energy | SJG | `08094` | **Fail** | ZIP result returned the rate-table headings but no plan rows. |

### Gas conclusion

| GDC | Current | Confirmed additions | Confirmed total | Still needed |
|---|---:|---|---:|---:|
| ETG | 3 | Mpower, Nordic, Indra | 6 | **4** |
| NJNG | 8 | Mpower, Nordic, Indra | 11 | 0 |
| PSE&G | 8 | Mpower, Nordic, Indra | 11 | 0 |
| SJG | 8 | IDT, Mpower, Nordic, Indra | 12 | 0 |

Do not develop NextEra gas, Residents/ETG, IDT/ETG, or Sunsea from the original proposal. Four replacement suppliers are still required for ETG.

## Development shortlist

Proceed with these confirmed combinations:

1. Clearview: PSE&G and Rockland electric.
2. NJG&E: JCP&L, PSE&G, and Rockland electric.
3. IDT: SJG gas.
4. Mpower: all four gas utilities.
5. Nordic: all four gas utilities.
6. Indra: all four gas utilities.

Before scraper implementation can satisfy the original target, test replacement candidates for:

- one additional Rockland electric supplier;
- four additional ETG gas suppliers.

## Sources and retained evidence

- [NJ Power Switch electric supplier list](https://www.nj.gov/njpowerswitch/suppliers/electric/)
- [NJ Power Switch gas supplier list](https://www.nj.gov/njpowerswitch/suppliers/gas/)
- Existing-adapter live run: `data/runs/20260930T131529Z-candidate-availability/`
- [Mpower public rates](https://rates.mpowerenergy.com/)
- [Nordic residential rate selector](https://www.nordicenergy-us.com/)
- [Indra New Jersey rates](https://indraenergy.com/service-areas/new-jersey/)
- [Sunsea public ZIP form](https://www.sunseaenergy.com/)

