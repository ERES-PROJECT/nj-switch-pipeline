# Offer identity and ZIP sampling

## Purpose

The collector may query more than one representative ZIP for a supplier/utility market. ZIP-level evidence must remain auditable, but the purchasing table must not count the same plan as several unique offers merely because it appeared in several ZIPs.

## Data layers

1. `results.json` and `offers.csv` retain every raw ZIP-level observation and its hashed artifact reference.
2. `offer_observations.csv` maps every observation to an `offer_fingerprint`. It keeps the observation ZIP, source URL, artifact ID, capture time, supplier product ID, observation-specific `offer_key`, and duplicate diagnostics.
3. `offer_prices.csv` contains one canonical row per fingerprint. It lists the observed ZIPs while leaving observation keys, counts, and duplicate diagnostics to the observation layer.
4. `contract_information.csv` consolidates identical document hashes within the same supplier/utility/commodity market while retaining observed ZIPs and observation counts.
5. `coverage.csv` remains ZIP-level because an empty, blocked, or unsupported result in one ZIP is meaningful evidence and must not be hidden by another ZIP.

## Canonical offer fingerprint

ZIP, capture time, source URL, artifact ID, and document links are excluded from the fingerprint. The fingerprint includes:

- supplier, utility, and commodity;
- supplier product ID when present, otherwise normalized plan name;
- rate and rate unit;
- rate structure, term length, and term kind;
- monthly, enrollment, and cancellation fees;
- introductory rate and duration;
- renewable percentage, source, and claim;
- incentives and structured fee terms.

Therefore, an identical plan found in three ZIPs becomes one canonical row with three observations. Two plans with the same rate remain distinct when their product IDs or purchasing terms differ.

## Observation-layer status columns

- `duplicate_status = unique`: one observation supports the canonical offer.
- `duplicate_status = consolidated_across_zips`: materially identical observations from more than one ZIP were consolidated.
- `duplicate_status = repeated_observation`: the same canonical offer was observed more than once in one ZIP.

These statuses are present in `offer_observations.csv`, not the canonical purchasing CSV.

Distinct canonical rows can legitimately share a rate. They remain separate because their purchasing fingerprints include product identity and material plan terms; the canonical CSV does not add a redundant same-rate status or count.

## Representative ZIP policy

Additional ZIPs are configured only for markets whose empty or unsupported result needs stronger territory-level evidence. They are not applied to every supplier automatically. The initial expanded markets are Great American Gas & Electric in PSE&G Electric and Think Energy and Green Mountain Energy in Rockland Electric.

PSE&G publishes the municipalities in its electric and gas service territory. Orange & Rockland states that its New Jersey electric subsidiary serves communities in Bergen, Passaic, and Sussex counties. Representative ZIPs should be reviewed if utility boundaries or supplier eligibility change.

- PSE&G service territory: https://nj.pseg.com/serviceterritory
- Orange & Rockland corporate/service-area facts: https://www.oru.com/en/about-us/media-center/corporate-facts
- New Jersey electric utility territory GIS layer: https://mapsdep.nj.gov/arcgis/rest/services/Features/Utilities/MapServer/10

## Database recommendation

Use `offer_fingerprint` as the sole identity column in the canonical purchasing CSV, and use `offer_key` as the ZIP-level observation key in the observation/technical data. Store observations in a child table rather than duplicating canonical offer rows. Do not use rate alone as a unique key.

The fingerprint intentionally changes when a purchasing term changes. A future historical database should add a separate product lineage key if the project needs to follow the same supplier product through rate or contract changes over time.
