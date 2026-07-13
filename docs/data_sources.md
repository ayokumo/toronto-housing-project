# Data Sources — Toronto Housing & Homelessness Analytics Platform

Every dataset used in this project is publicly available. This document records
what each source provides, how we access it, its granularity, and known limitations.

---

## 1. Daily Shelter & Overnight Service Occupancy & Capacity

- **Provider:** City of Toronto, Shelter Support & Housing Administration
- **Portal:** https://open.toronto.ca/dataset/daily-shelter-overnight-service-occupancy-capacity/
- **Access:** CKAN API (JSON) or CSV download
- **Granularity:** Daily, by program/location
- **Coverage:** 2021–present
- **Key fields:** OCCUPANCY_DATE, ORGANIZATION_NAME, SHELTER_GROUP, LOCATION_NAME,
  PROGRAM_NAME, SECTOR (Men/Women/Youth/Families/Co-ed), OVERNIGHT_SERVICE_TYPE,
  CAPACITY_TYPE (Bed/Room), FUNDING_CAPACITY, ACTUAL_CAPACITY, OCCUPANCY,
  UNOCCUPIED_BEDS/ROOMS
- **Limitations:**
  - Weekend/holiday data posted next business day (not missing, just delayed)
  - As of Apr 2024, Red Cross refugee hotel programs added — creates a structural
    break in total capacity numbers
  - Violence Against Women shelters excluded for confidentiality

## 2. Daily Shelter Occupancy (Legacy)

- **Provider:** City of Toronto
- **Portal:** https://open.toronto.ca/dataset/daily-shelter-occupancy/
- **Coverage:** 2017–2020
- **Notes:** Pre-COVID shelter programs only. Different schema from the 2021+ dataset.
  We will use this for longer trend analysis but must handle the schema difference
  and the COVID structural break explicitly.

## 3. CMHC Rental Market Survey

- **Provider:** Canada Mortgage & Housing Corporation
- **Portal:** https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market
- **Access:** Excel download (annual release, typically December/January)
- **Granularity:** Annual, by CMA/zone/neighbourhood for Toronto
- **Key fields:** Vacancy rate (%), average rent ($) by bedroom count, universe count
- **Limitations:**
  - Annual only — we cannot see monthly rent dynamics
  - Survey conducted in first two weeks of October each year
  - Purpose-built rental only in primary tables; secondary market (condos) is separate

## 4. Bank of Canada Interest Rates

- **Provider:** Bank of Canada
- **Access:** Valet API (free, no key required)
  - Base URL: https://www.bankofcanada.ca/valet/
  - Policy rate series: V39079 (target overnight rate)
- **Granularity:** Daily (policy rate changes on 8 fixed dates/year)
- **Coverage:** 1991–present
- **Limitations:** Policy rate is a national macro variable — it affects Toronto
  housing costs but is not Toronto-specific. This is an important caveat for
  any causal claims.

## 5. Statistics Canada Census Profile (2021)

- **Provider:** Statistics Canada
- **Portal:** https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/
- **Access:** CSV bulk download by census tract
- **Granularity:** Census tract (maps roughly to Toronto neighbourhoods)
- **Key variables:** Median household income, % low-income (LICO/LIM),
  housing tenure (own vs rent), shelter-cost-to-income ratio, population
- **Limitations:**
  - Point-in-time (May 2021) — does not capture post-2021 changes
  - Census tracts ≠ exact neighbourhood boundaries but close enough for analysis

## 6. Environment Canada Historical Weather

- **Provider:** Environment and Climate Change Canada
- **Portal:** https://climate.weather.gc.ca/historical_data/search_historic_data_e.html
- **Access:** CSV download per station per year; or `env_canada` Python package
- **Station:** Toronto Pearson Intl A (Climate ID: 6158731, Station ID: 51459)
- **Granularity:** Daily (mean/max/min temperature, precipitation, snow)
- **Coverage:** Complete daily records available
- **Limitations:**
  - Toronto Pearson is ~25 km from downtown — temperature is close but not
    identical to downtown conditions
  - We use daily mean temperature as the primary weather feature; wind chill
    would be better for shelter demand but is less consistently available
