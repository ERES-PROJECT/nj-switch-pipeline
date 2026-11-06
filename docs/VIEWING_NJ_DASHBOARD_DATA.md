# Viewing the NJ TPS dashboard data

## Database connection

Connect to the Lehigh VPN, then open and leave the SSH tunnel running:

```powershell
ssh -L 3308:127.0.0.1:3306 <your-netid>@python1.cc.lehigh.edu -N
```

In DBeaver, MySQL Workbench, TablePlus, or another MariaDB/MySQL client, use:

| Setting | Value |
|---|---|
| Host | `127.0.0.1` |
| Port | `3308` |
| Database | `EEdb` |
| Username | `EEdb` |
| Password | Use the separately provided EEdb password |

Open the `EEdb` schema and select `nj_tps_dashboard_data`.

## Useful queries

Preview individual offers:

```sql
SELECT
    tps,
    edc_gdc,
    commodity,
    plan_name,
    rate,
    rate_unit,
    plan_type,
    term_months,
    captured_last_utc
FROM nj_tps_dashboard_data
ORDER BY commodity, edc_gdc, tps, rate
LIMIT 100;
```

Summarize the markets:

```sql
SELECT
    edc_gdc,
    commodity,
    COUNT(*) AS offers,
    COUNT(DISTINCT tps) AS suppliers,
    MIN(rate) AS minimum_rate,
    AVG(rate) AS average_rate,
    MAX(rate) AS maximum_rate,
    rate_unit
FROM nj_tps_dashboard_data
GROUP BY edc_gdc, commodity, rate_unit
ORDER BY commodity, edc_gdc;
```

Inspect the original observation rows retained for an offer:

```sql
SELECT
    offer_fingerprint,
    plan_name,
    JSON_PRETTY(offer_observations_json) AS observations
FROM nj_tps_dashboard_data
LIMIT 10;
```

## Streamlit dashboard status

The data is ready for a visual dashboard, but the existing ERES Streamlit app
does not yet contain an NJ module. It currently exposes Pennsylvania-focused
modules. The next dashboard step is a read-only NJ module that queries
`nj_tps_dashboard_data`; the table should not be edited by the dashboard.
