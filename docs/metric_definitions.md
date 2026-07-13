# Metric Definitions

Every metric used in this project is defined here. If a number appears in a
dashboard, notebook, or API response, it must trace back to this document.

---

## Shelter System Metrics

### Occupancy Rate
- **Definition:** Occupied units / Actual capacity × 100
- **Unit:** Percentage (0–100+; can exceed 100 if overflow beds used)
- **Grain:** Daily, per program; aggregated up to location, sector, system-wide
- **Source field:** OCCUPANCY / ACTUAL_CAPACITY from shelter occupancy dataset
- **Note:** For room-based programs, "occupied" = rooms in use.
  For bed-based programs, "occupied" = beds in use.
  Total individuals served may exceed occupancy in room-based programs
  (families sharing a room).

### Capacity Utilization
- **Definition:** Actual capacity / Funding capacity × 100
- **Purpose:** Shows how much of the funded capacity is actually operational
  (beds can be offline for maintenance, outbreaks, pest control)
- **Unit:** Percentage

### Unmet Demand (Proxy)
- **Definition:** System-wide occupancy rate when ≥ 95%, flagged as "effectively full"
- **Caveat:** This is a PROXY. True unmet demand would require Central Intake
  call data (number turned away). We note this limitation explicitly.

---

## Housing Market Metrics

### Average Rent
- **Definition:** Average monthly rent for purpose-built rental apartments
- **Source:** CMHC Rental Market Survey (October survey each year)
- **Breakdowns:** By bedroom count (bachelor, 1BR, 2BR, 3BR+)

### Vacancy Rate
- **Definition:** Percentage of purpose-built rental units vacant at time of survey
- **Interpretation:** < 2% = tight (landlord-favourable); ≥ 3% = renter choice
- **Source:** CMHC Rental Market Survey

### Rent-to-Income Ratio
- **Definition:** (Average 1BR rent × 12) / Median household income × 100
- **Purpose:** Affordability indicator
- **Inputs:** CMHC average rent + StatCan census median income
- **Caveat:** Mixing annual rent data with point-in-time census income.
  The ratio is indicative, not precise for any individual household.

### Policy Interest Rate
- **Definition:** Bank of Canada target for the overnight rate
- **Relevance:** Affects mortgage costs → housing prices → rental pressure →
  affordability → potential pathway to homelessness. This is a DISTAL driver,
  not a direct cause. We model the correlation, not causation.

---

## Weather Metric

### Daily Mean Temperature
- **Definition:** (Max temp + Min temp) / 2, in °C
- **Source:** Environment Canada, Toronto Pearson station
- **Relevance:** Cold temperatures increase shelter demand (warming centre
  activation, survival needs). We test this relationship empirically.

---

## Aggregation Rules

- **Daily → Weekly:** ISO week mean (Mon–Sun)
- **Daily → Monthly:** Calendar month mean
- **Program → Location:** Sum of occupancy, sum of capacity, then compute rate
- **Location → System:** Same: sum up, then divide (never average the rates)
