# Toronto Housing & Homelessness Analytics Platform

An end-to-end data platform exploring what drives shelter demand in Toronto and whether we can forecast it well enough to inform capacity planning.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌───────────────────┐    ┌──────────────┐
│  Data Sources│───▶│  Ingestion   │───▶│  dbt / DuckDB     │───▶│  Streamlit   │
│  (APIs/CSV)  │    │  (Python)    │    │  (star schema)    │    │  App         │
└─────────────┘    └──────────────┘    └───────────────────┘    └──────────────┘
                                              │                        │
                                              ▼                        ▼
                                       ┌──────────────┐    ┌──────────────────┐
                                       │  Analysis &   │    │  FastAPI /forecast│
                                       │  Forecasting  │    │  endpoint        │
                                       └──────────────┘    └──────────────────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │  Power BI     │
                                       │  Dashboard    │
                                       └──────────────┘
```

## Three Core Questions

1. **What drives shelter occupancy and where is the system under most stress?**
   Descriptive analytics: trends by year, season, program type, geography. Which shelters/areas carry the load?

2. **How do housing-market forces relate to homelessness indicators over time?**
   Statistical layer: regression of demand on rents, vacancy rates, interest rates, income, weather. Quantified uncertainty and honest causal framing.

3. **Can we forecast near-term shelter demand well enough to inform capacity planning?**
   Time-series forecasting: SARIMA, Prophet, rolling-origin CV, exogenous features.

## Data Sources

| Source | Provider | Granularity | Access |
|--------|----------|-------------|--------|
| Daily Shelter Occupancy & Capacity | City of Toronto Open Data | Daily, program-level | CKAN API |
| Shelter Occupancy (Legacy) | City of Toronto Open Data | Daily, 2017–2020 | CSV download |
| Rental Market Survey | CMHC | Annual, Toronto CMA | Excel download |
| Interest Rates (policy rate) | Bank of Canada | Daily | Valet API |
| Census Income & Demographics | Statistics Canada | Census tract, 2021 | CSV download |
| Historical Weather (temperature) | Environment Canada | Daily, Toronto Pearson | CSV download |

## Project Structure

```
toronto-housing-project/
├── ingestion/          # Python scripts to pull & cache raw data
│   ├── scripts/
│   ├── cache/
│   └── tests/
├── dbt_project/        # dbt Core + DuckDB: staging → star schema → marts
├── analysis/           # Descriptive stats, regression, maps
│   ├── notebooks/
│   ├── scripts/
│   └── outputs/
├── forecasting/        # Time-series models (SARIMA, Prophet)
│   ├── models/
│   ├── evaluation/
│   └── tests/
├── app/                # Streamlit multi-page app
│   ├── pages/
│   └── utils/
├── dashboards/         # Power BI files & exports
├── docs/               # Architecture diagrams, findings memo
│   ├── architecture/
│   └── findings/
├── data/               # Local data (gitignored except schema docs)
│   ├── raw/
│   └── processed/
└── tests/              # Cross-cutting integration tests
```

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize dbt
cd dbt_project && dbt debug
```

## Tech Stack

- **Warehouse:** DuckDB (local dev) — designed to port to Snowflake/BigQuery
- **Transformation:** dbt Core with dbt-duckdb adapter
- **Languages:** Python (pandas, PySpark for one transform), SQL
- **Forecasting:** statsmodels (SARIMA), Prophet
- **API:** FastAPI + Docker
- **App:** Streamlit
- **BI:** Power BI Desktop
- **Testing:** pytest, dbt tests (not_null, unique, custom)

## Author

[ayokumo](https://github.com/ayokumo) — York University, Data Science (Honours) + Finance Minor
