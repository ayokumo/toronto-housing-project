# Decision log

## Rate aware forecast (monthly)

- Target is the monthly system occupancy rate. 2026-07 is dropped because it has only 14 days of data.
- Policy rate is lagged 6 months so it is known at forecast time for a 3 month horizon (lag must be at least the horizon; the code raises an error otherwise).
- First tried a COVID dummy in a differenced SARIMAX. On the validation period (targets before 2024-01) it made SARIMAX about 3 times worse than naive, so I switched to masking the COVID months in the training target. Chosen on validation only.
- Lag 6 was fixed before looking at results. Lags 3, 6, 9, 12 are reported for transparency and none was selected from them.
- Headline numbers use the held out test targets from 2024-01. The result is that the rate does not help; it is reported as measured.
- One error metric everywhere: MAE in percentage points. The earlier README mixed MAE and MAPE and that is fixed.
