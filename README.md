# Toronto Housing & Homelessness Analytics Platform

An end-to-end data platform linking **macro-financial indicators** (Bank of Canada policy rate, rental market stress) to social infrastructure demand — built to demonstrate production-grade data engineering, statistical modeling, and time-series forecasting.

> **Finance relevance:** This project treats shelter occupancy as an *alternative data signal* for housing market stress — the same analytical pattern used by real estate investment teams, credit risk analysts, and macro research desks to monitor affordability and forecast demand.

---

## What This Project Does

**Three questions, three analytical layers:**

| Question | Method | Key Finding |
|----------|--------|-------------|
| Where is the shelter system under most stress? | Descriptive analytics, geographic concentration (Folium) | 79% of programs at 95%+ occupancy since 2023. Stress concentrated in downtown core. |
| How do macro-financial forces relate to shelter demand? | OLS regression: BoC policy rate, temperature, time trend | Policy rate has a +0.64pp effect per 1% increase (6-month lag, p=0.059). Demand is structural, not seasonal. |
| Can we forecast shelter demand accurately? | SARIMA, Prophet, rolling-origin CV (37 folds) | System is saturated at 97-99% — naive baseline wins (MAE of 0.32 percentage points). The forecast IS the finding: no slack remains. |

---

## Architecture

Data Sources --> Python Ingestion + Caching --> DuckDB Warehouse --> dbt Core Star Schema --> Analysis (statsmodels, SARIMA, Prophet) --> Outputs (Folium Map, Matplotlib Charts)

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Warehouse** | DuckDB | Columnar analytics engine — same SQL as Snowflake/BigQuery, zero infrastructure |
| **Transformation** | dbt Core | Tested star schema (18 tests passing), staging to mart pattern |
| **Ingestion** | Python, requests | Cached API pulls with TTL, idempotent load-and-replace |
| **Statistical** | statsmodels (OLS) | Regression with VIF diagnostics, Durbin-Watson, confidence intervals |
| **Forecasting** | SARIMA, Prophet | Rolling-origin CV (not k-fold — temporal data leakage prevention) |
| **Visualization** | Folium, Matplotlib | Interactive satellite map with sector filters + publication-quality charts |
| **Testing** | pytest (8 tests), dbt tests (18) | Cache behavior, DuckDB load semantics, not_null/unique/accepted_values |

---

## Data Sources

All public, all verified, all documented in docs/data_sources.md.

| Source | Provider | Finance Relevance |
|--------|----------|-------------------|
| Daily Shelter Occupancy | City of Toronto Open Data | Demand signal — leading indicator of housing market pressure |
| Bank of Canada Policy Rate | Bank of Canada Valet API | Macro transmission channel: rates to mortgage costs to affordability |
| CMHC Rental Market Survey | CMHC | Vacancy rates + avg rents — core housing affordability metrics |
| Census Income/Demographics | Statistics Canada | Income distribution, rent-to-income burden ratios |
| Historical Weather | Environment Canada | Exogenous feature for demand forecasting (cold = higher demand) |

---

## Key Results

### 1. System Saturation
Toronto shelter system has operated at **97-99% occupancy** every week since 2022. Multiple programs have been at **100% capacity every single day** for 4 consecutive years.

![Annual Occupancy Trend](analysis/outputs/annual_occupancy_trend.png)

![Most Stressed Shelters](analysis/outputs/most_stressed_shelters.png)

### 2. Macro-Financial Transmission
The Bank of Canada policy rate shows a **+0.64 percentage point** increase in shelter occupancy per 1% rate hike, with a 6-month lag (p=0.059). This is the expected direction from housing affordability theory: rate increases lead to higher mortgage/rent costs lead to increased housing stress.

**Causal caveat:** This is a correlation in an observational study. Rate hikes coincided with post-COVID housing market stress — we cannot isolate the rate effect from other simultaneous changes. Documented honestly throughout.

![Regression Fit](analysis/outputs/regression_fit.png)

![Regression Coefficients](analysis/outputs/regression_coefficients.png)

### 3. Forecasting at Saturation
The naive baseline (forecast = last weeks value) beats SARIMA and Prophet because the system is **pinned at its capacity ceiling**. The series barely moves — an MAE of 0.32 percentage points means the weekly forecast is off by less than a third of a percentage point. MAE in percentage points is the only error metric used in this README.

**Finance analogy:** A portfolio running at its risk limit is highly predictable day-to-day but has zero buffer for shocks. The forecast tells you the system is stable; the lack of slack tells you it is fragile.

![Forecast Model Comparison](forecasting/evaluation/forecast_model_comparison.png)

![Final Forecast](forecasting/evaluation/final_forecast.png)

### 4. Does the Bank of Canada rate help? (monthly, rate as an exogenous input)
`forecasting/models/rate_forecast.py` asks whether the policy rate, lagged 6 months so it is always known at forecast time, reduces forecast error for the monthly system occupancy rate. Setup: 114 full months (2017-01 to 2026-06, the partial 2026-07 is dropped), rolling origin, 3 months ahead, minimum 48 months of training, COVID months (2020-03 to 2020-12) masked in training. Modelling choices were made on targets before 2024-01; the headline is the held out period from 2024-01.

| Model (held out test, 87 forecasts) | MAE (pp) | Change vs naive |
|---|---|---|
| Naive (last value) | 0.422 | baseline |
| SARIMAX(1,1,1) | 0.420 | -0.5% |
| SARIMAX(1,1,1) + policy rate lagged 6 months | 0.425 | +0.6% |

**Result: the rate did not reduce error.** The rate model is 0.6% worse than naive and 1.0% worse than the same model without the rate. Lags of 3, 6, 9 and 12 months all land within about 3% of naive in either direction (`forecasting/evaluation/rate_forecast_lag_sensitivity.csv`), which is noise at this sample size. The 6 month lag was fixed in advance, not picked from that table. This agrees with section 3: the system is at its ceiling, so there is little left to forecast. Details and the folds are in `forecasting/evaluation/`.

Limits: only 9 years of monthly data, one rate regime change, and the series sits near 98%, so any model has little room to beat naive.

![Rate forecast comparison](forecasting/evaluation/rate_forecast_comparison.png)

---

## Star Schema (dbt)

- **dim_date** — 3,484 days (2017-2026) with season, quarter, weekend flags
- **dim_shelter** — 148 unique shelter locations with FSA, organization, sector
- **fact_shelter_daily** — 433,362 rows, grain = program + day. Occupancy rate, capacity, stress flags.
- **fact_housing_monthly** — 115 months joining shelter aggregates + BoC rate + weather

All models tested: dbt test produces 18/18 passing. Schema documented in staging.yml.

---

## Project Structure

- **ingestion/** — Python scripts: CKAN API, BoC Valet, ECCC weather, cached with TTL
- **dbt_project/** — dbt Core + DuckDB: 5 staging views, 4 mart tables
- **analysis/** — Descriptive trends, interactive map, OLS regression
- **forecasting/** — SARIMA, Prophet, rolling-origin cross-validation (37 folds), plus a monthly SARIMAX with the BoC rate as an exogenous input
- **docs/** — data_sources.md (every dataset), metric_definitions.md (every formula)

---

## How to Run

1. Clone and set up: git clone, python3 -m venv .venv, pip install -r requirements.txt
2. Ingest data: python3 -m ingestion.scripts.run_all shelter boc weather
3. Build dbt: cd dbt_project && dbt deps && dbt run && dbt test
4. Analysis: python3 -m analysis.scripts.occupancy_trends
5. Map: python3 -m analysis.scripts.shelter_map
6. Regression: python3 -m analysis.scripts.regression_analysis
7. Forecasting: python3 -m forecasting.models.shelter_forecast
8. Rate forecast: python3 -m forecasting.models.rate_forecast
9. Tests: python3 -m pytest forecasting/tests

---

## Metric Definitions

Every number in this project traces to docs/metric_definitions.md. Key metrics:

- **Occupancy Rate** = Occupied / Actual Capacity x 100 (not funding capacity)
- **Effectively Full** = Program running at 95%+ occupancy rate
- **System Occupancy Rate** = total occupied across all programs / total actual capacity (never average the rates)

---

## Data Quality Issues Encountered and Resolved

- **2-digit year dates** from CKAN API (2021-2022 resources returned 21-xx-xx instead of 2021-xx-xx) — fixed in ingestion with regex date repair
- **Mixed date formats** in legacy shelter data (2017-2019 ISO format, 2020 MM/DD/YYYY) — handled with CASE statement in dbt staging
- **Empty strings in numeric columns** (OCCUPIED_BEDS) — resolved with try_cast in dbt
- **DuckDB UNION ALL type resolution** mangling dates across strptime and cast — fixed with explicit ::date cast

---

## Related project

[Toronto Shelter Overdose Spatial Analysis](https://github.com/ayokumo/toronto-overdose-spatial) is a companion analysis of overdose incidents in the same shelter system. It covers spatial regression across Toronto's 158 neighbourhoods and a cluster analysis of incident locations.

---

## Author

**Ayokunmi Lawal**, York University, Data Science
[GitHub](https://github.com/ayokumo)
