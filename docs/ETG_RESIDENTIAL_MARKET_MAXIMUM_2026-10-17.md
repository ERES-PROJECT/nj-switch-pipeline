# ETG residential public-scraping market maximum — October 17, 2026

## Decision

For the current milestone, the verified maximum is **six independent residential TPS suppliers with reproducible public ETG offers**. All six now satisfy the strict completion gate. The project therefore records an ETG exception to the nominal target of ten.

This is a public-scraping maximum, not a claim that only six companies hold licenses. The official NJ Power Switch gas list contains 23 residential-capable rows marked for ETG, but licensing and an ETG territory mark do not prove that a supplier currently publishes a residential ETG offer through a reproducible public route.

Official source: [NJ Power Switch — Suppliers by Gas Distribution Company](https://www.nj.gov/njpowerswitch/suppliers/gas/) (page states “Last Updated: 7/1/2026”). Current project evidence is anchored by `data/runs/20261016-active-scrapers-live`, followed by the October 17 Major and Indra document certifications.

## Official residential ETG pool and current disposition

| Official supplier row | Current public-route disposition | Counts toward maximum? | Evidence |
|---|---|---:|---|
| Ameripro Energy | Public pricing page produced no numeric residential ETG offer. | No | `data/runs/20261015-all-scrapers-live`; B15 audit |
| Astral Energy | Official pricing route remained blocked by its access layer; no current ETG offer could be reproduced. | No | `data/runs/20261015-all-scrapers-live`; B15 audit |
| Constellation | Current ETG ZIP flow returns two plans and three connected documents. | **Yes** | `data/runs/20261016-active-scrapers-live` |
| Direct Energy Services | Current ETG ZIP/API flow returns three plans and six connected documents. | **Yes** | `data/runs/20261016-direct-cdp-all-certification-2` |
| Eligo Energy | Representative ETG ZIP returns no service; the working gas route remains NJNG-only in production. | No | `docs/NJ_TPS_CANDIDATE_AVAILABILITY.md` |
| Gateway Energy Services | NJ Power Switch pricing link resolves to Direct Energy's same public product chart, not an independent Gateway residential catalog. It cannot be counted as a second supplier scraper from identical Direct evidence. | No | NJ Power Switch pricing link; October 17 link audit |
| Horizon Power and Light | NJ Power Switch's official pricing link uses the invalid `hplco.cim` host and does not reach a public offer route. | No | NJ Power Switch pricing link; `docs/NJ_SUPPLIER_AND_SCHEMA_FINDINGS.md` |
| IDT Energy | Current gas flow does not expose an Elizabethtown utility choice. | No | `data/runs/20260930T131529Z-candidate-availability` |
| IGS Energy | Current public route did not produce a ZIP-qualified numeric ETG offer. | No | `data/runs/20261015-all-scrapers-live`; B15 audit |
| Major Energy | Current ETG flow returns one plan and its exact ProductID-linked TOS PDF. | **Yes** | `data/runs/20261017-major-documents-all` |
| Mpower Energy | Rejected source is an unqualified/out-of-state file rather than current ZIP-qualified New Jersey offer evidence. | No | `data/runs/20261015-all-scrapers-live` |
| NextEra Energy Services | Current residential flow exposes electricity only and does not offer an ETG gas path. | No | `data/runs/20260930T131529Z-candidate-availability` |
| Nordic Energy Services | Current residential ETG selector returns one plan and two connected documents. | **Yes** | `data/runs/20261016-active-scrapers-live` |
| Northeastern Power & Gas | Official host presents a certificate-hostname mismatch; no permitted current ETG offer route was reproducible. | No | `data/runs/20261015-all-scrapers-live`; B15 audit |
| NTHERM | NJ Power Switch's official `/pricing` link returns `404 Not Found`. | No | NJ Power Switch pricing link; October 17 link audit |
| Palmco / Indra Energy | Current ETG ZIP-qualified API returns two plans; visible modal clicks return two exact rateCode/sysId-linked PDFs. | **Yes** | `data/runs/20261017-indra-documents-all-2` |
| Reliant / NRG Home | NRG advertises ETG generally, but its public shopper submitted PSE&G Gas for mixed-area ZIPs `07201` and `07083`; ETG-only ZIP `07860` exposed no ETG choice. No ETG catalog was returned. | No | `data/runs/20261017-nrg-etg-candidate`, `data/runs/20261017-nrg-etg-07083`, `data/runs/20261017-nrg-etg-07860` |
| Residents Energy | Public comparison rows are not ZIP-qualified and the current page exposes no public ETG enrollment/offer route. | No | retirement audit in active TODO |
| RPA / Green Choice Energy | Current public route did not produce a ZIP-qualified numeric ETG offer. | No | `data/runs/20261015-all-scrapers-live`; B15 audit |
| SmartEnergy | Current New Jersey public shopping source publishes electricity offers only. | No | `data/runs/20261016-active-scrapers-live` |
| South Bay Energy | Official pricing route returned no usable current offer page. | No | `data/runs/20261015-all-scrapers-live`; B15 audit |
| Sunsea Energy | ETG ZIP result displayed rate-table headings but no plan rows. | No | `data/runs/20260930T131529Z-candidate-availability` |
| Titan Gas / CleanSky Energy | Current ETG ZIP flow returns five plans and thirteen connected documents. | **Yes** | `data/runs/20261016-active-scrapers-live` |

## Count reconciliation

| Measure | Count |
|---|---:|
| Official residential-capable ETG rows reviewed | 23 |
| Independent suppliers with current reproducible public ETG offers | 6 |
| Strictly completed ETG scrapers | 6 |
| Remaining attainable gap based on the reviewed public pool | 0 |

The exception must be reopened if NJ Power Switch changes the ETG list or any rejected supplier begins returning a current residential ETG offer from its public pricing route.
