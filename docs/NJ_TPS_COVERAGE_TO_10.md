# NJ supplier coverage needed to reach 10 per EDC/GDC

> **Availability update (September 30, 2026):** Live checks invalidated several candidates in the original proposal. Use [NJ TPS candidate availability check](NJ_TPS_CANDIDATE_AVAILABILITY.md) as the current implementation shortlist. Rockland still needs one replacement and ETG still needs four.

## Definitions

- **Working now** means the supplier has at least one offer in `data/runs/20260918-user-confirmed-supplier-coverage-final/coverage.csv` for that utility and commodity.
- **Candidate** means NJ Power Switch lists the supplier for the residential customer class and the utility territory.
- Candidate status does not yet mean that a ZIP currently returns an offer. ZIP and pricing tests are the next step.

Official candidate sources:

- [NJ Power Switch electric suppliers](https://www.nj.gov/njpowerswitch/suppliers/electric/)
- [NJ Power Switch gas suppliers](https://www.nj.gov/njpowerswitch/suppliers/gas/)

Both official pages were last updated July 1, 2026.

## Current gap

| EDC/GDC | Commodity | Working now | More needed to reach 10 |
|---|---|---:|---:|
| ACE Electric | Electric | 10 | 0 |
| JCP&L Electric | Electric | 9 | 1 |
| PSE&G Electric | Electric | 8 | 2 |
| Rockland Electric | Electric | 7 | 3 |
| ETG Gas | Gas | 3 | 7 |
| NJNG Gas | Gas | 8 | 2 |
| PSE&G Gas | Gas | 8 | 2 |
| SJG Gas | Gas | 8 | 2 |

ETG determines the size of the gas expansion. Because it needs seven suppliers, the most efficient plan is to choose seven residential suppliers that NJ Power Switch lists in all four gas territories.

## Existing suppliers compared with proposed additions

### Currently scraped suppliers

These 18 supplier brands already produce at least one offer in the verified coverage run. Reusing one of these brands in another utility territory is an extension, not a new supplier implementation.

| Currently scraped supplier | Utility/commodity combinations already producing offers |
|---|---|
| Alpha Gas & Electric | ACE Electric |
| Ambit Energy | ACE, JCP&L, PSE&G, and Rockland Electric |
| American Power & Gas | PSE&G Gas |
| CleanChoice Energy | ACE, JCP&L, and PSE&G Electric |
| CleanSky Energy | Rockland Electric; ETG, PSE&G, and SJG Gas |
| Clearview Energy | ACE and JCP&L Electric; NJNG and SJG Gas |
| Constellation Energy | ACE, JCP&L, and PSE&G Electric |
| Direct Energy | All four electric and all four gas utilities |
| Eligo Energy | NJNG Gas |
| IDT Energy | JCP&L and Rockland Electric; NJNG and PSE&G Gas |
| Major Energy | ACE and PSE&G Electric; ETG, NJNG, PSE&G, and SJG Gas |
| NextEra Energy Services | ACE Electric |
| NJG&E | NJNG and SJG Gas |
| NRG | ACE, PSE&G, and Rockland Electric; PSE&G and SJG Gas |
| Residents Energy | NJNG, PSE&G, and SJG Gas |
| Smart Energy | ACE, JCP&L, and Rockland Electric |
| Think Energy | JCP&L and PSE&G Electric |
| Xoom Energy | JCP&L, PSE&G, and Rockland Electric; NJNG, PSE&G, and SJG Gas |

### Proposed additions, separated by implementation type

| Classification | Supplier | New utility/commodity combinations to test |
|---|---|---|
| Existing supplier extension | Alpha Gas & Electric | JCP&L, PSE&G, and Rockland Electric |
| Existing supplier extension | Clearview Energy | PSE&G and Rockland Electric |
| Existing supplier extension | NJG&E | Rockland Electric first; PSE&G and JCP&L only as backups |
| Existing supplier extension | IDT Energy | ETG and SJG Gas |
| Existing supplier extension | Residents Energy | ETG Gas only |
| Existing supplier extension | NextEra Energy Services | ETG, NJNG, PSE&G, and SJG Gas |
| **New supplier brand** | **Mpower Energy** | ETG, NJNG, PSE&G, and SJG Gas |
| **New supplier brand** | **Nordic Energy Services** | ETG, NJNG, PSE&G, and SJG Gas |
| **New supplier brand** | **Indra Energy** | ETG, NJNG, PSE&G, and SJG Gas; optional electric backup |
| **New supplier brand** | **Sunsea Energy** | ETG, NJNG, PSE&G, and SJG Gas; optional electric backup |

The only completely new supplier brands in the primary plan are **Mpower, Nordic, Indra, and Sunsea**. Alpha, Clearview, NJG&E, IDT, Residents, and NextEra are already scraped somewhere and should be treated only as territory or commodity extensions.

## Recommended electric additions

Use three suppliers across the electric utilities:

1. **Alpha Gas & Electric**
   - NJ Power Switch territories: ACE, JCP&L, PSE&G, and Rockland.
   - Already produces offers for ACE in the current pipeline.
   - Add JCP&L, PSE&G, and Rockland to its existing adapter.
2. **Clearview Energy**
   - NJ Power Switch territories: ACE, JCP&L, PSE&G, and Rockland.
   - Already produces offers for ACE and JCP&L.
   - Add PSE&G and Rockland to its existing adapter.
3. **New Jersey Gas & Electric (NJG&E)**
   - NJ Power Switch territories: ACE, JCP&L, PSE&G, and Rockland.
   - A gas adapter already exists, so supplier-specific knowledge can be reused.
   - Add an electric path, with Rockland as the essential target.

### Electric result if all three work

| EDC | Current | Added by the shared candidate set | Expected total |
|---|---:|---:|---:|
| ACE | 10 | 0 required | 10 or more |
| JCP&L | 9 | Alpha | 10 or more |
| PSE&G | 8 | Alpha, Clearview, NJG&E | 11 |
| Rockland | 7 | Alpha, Clearview, NJG&E | 10 |

This plan reaches the target with three supplier brands and mostly extends existing adapters.

### Electric backups

If one of the three does not return a current residential offer, test these broad-coverage suppliers next:

1. **Eligo Energy** — officially listed for all four EDCs and already has a gas adapter. An early ZIP check found PSE&G electric offers but no Rockland offer for `07430`, so it is a PSE&G backup rather than the primary Rockland choice.
2. **North American Power** — officially listed for all four EDCs and residential service.
3. **Indra Energy** — officially listed for all four EDCs and residential service.
4. **Mpower Energy** — officially listed for all four EDCs and residential service.
5. **Sunsea Energy** — officially listed for all four EDCs and residential service.
6. **Great American Gas & Electric** — officially listed for all four EDCs and already has an adapter, but the current PSE&G tests did not yield offers.

## Recommended gas additions

Use the following seven suppliers. NJ Power Switch lists every one for residential service in ETG, NJNG, PSE&G, and SJG.

| Priority | Supplier | Existing reuse | Why it is preferred |
|---:|---|---|---|
| 1 | IDT Energy | Existing gas adapter; working in NJNG and PSE&G | Only ETG and SJG territory extensions are needed. |
| 2 | Residents Energy | Existing gas adapter; working in NJNG, PSE&G, and SJG | Only ETG needs to be added. |
| 3 | NextEra Energy Services | Existing electric adapter and navigation work | Reuse the supplier flow for gas before creating a new brand adapter. |
| 4 | Mpower Energy | New adapter | NJ Power Switch links a dedicated public rates site. |
| 5 | Nordic Energy Services | New adapter | NJ Power Switch links a dedicated pricing page and lists all four GDCs. |
| 6 | Indra Energy | New adapter | One supplier can cover all four GDCs and may also serve as an electric backup. |
| 7 | Sunsea Energy | New adapter | Public ZIP form and all-four-territory listing; may also serve as an electric backup. |

### Gas result if the seven candidates work

| GDC | Current | Candidates not already counted there | Expected total |
|---|---:|---|---:|
| ETG | 3 | IDT, Residents, NextEra, Mpower, Nordic, Indra, Sunsea | 10 |
| NJNG | 8 | NextEra, Mpower, Nordic, Indra, Sunsea | 13 |
| PSE&G | 8 | NextEra, Mpower, Nordic, Indra, Sunsea | 13 |
| SJG | 8 | IDT, NextEra, Mpower, Nordic, Indra, Sunsea | 14 |

The seven-supplier plan requires four completely new supplier brands: Mpower, Nordic, Indra, and Sunsea. IDT and Residents are territory extensions, and NextEra reuses an existing supplier adapter from electric collection.

### Gas backups

These are also listed by NJ Power Switch for residential service in all four GDCs:

1. **Ameripro Energy**
2. **Astral Energy**
3. **Interstate Gas Supply / IGS Energy**
4. **Northeastern Power & Gas**
5. **RPA Energy / Green Choice Energy**
6. **South Bay Energy**

Lower-priority candidates:

- **NTHERM** is listed in all four territories, but the NJ Power Switch pricing link currently returns a missing page.
- **Horizon Power and Light** is listed in all four territories, but the official pricing link contains an invalid domain spelling.
- **SmartEnergy** is listed for gas, but the current project review found its public shopping pages publishing electricity offers only.
- **Constellation** is listed in all four gas territories, but existing live checks did not find current gas offers.
- **Eligo** is listed in all four gas territories, but an early check on September 30, 2026 found PSE&G gas offers while representative ETG `07201` and SJG `08094` ZIPs returned no service. Keep it as a PSE&G-only backup until broader testing.

## Recommended testing order

The next phase should test only the candidates needed by the overlap plan:

1. Electric: Alpha in JCP&L, PSE&G, and Rockland.
2. Electric: Clearview in PSE&G and Rockland.
3. Electric: NJG&E in Rockland first, then PSE&G and JCP&L if useful.
4. Gas: Residents and IDT in ETG first because their adapters already work elsewhere.
5. Gas: NextEra in ETG, followed by the other three GDCs.
6. Gas: Mpower, Nordic, Indra, and Sunsea in ETG first. Stop testing a supplier across the other gas territories if ETG fails, because ETG is the binding constraint.
7. Pull replacements from the gas backup list only when a primary candidate fails to show a current residential offer.

This ordering minimizes new scraper development while proving the hardest market first.
