"""
Rate aware shelter occupancy forecast (monthly).

Question: does the Bank of Canada policy rate, used as an exogenous input,
reduce forecast error for the monthly system occupancy rate?

Specification (fixed before looking at results, see docs/decision_log.md):
  target        system_occupancy_rate (percent), monthly, 2017-01 to 2026-06
  dropped       2026-07, only 14 days of data (partial month)
  exogenous     avg_policy_rate lagged 6 months (lag >= horizon, so no leakage)
  covid months  2020-03 to 2020-12 set to missing in the training target
                (SARIMAX skips missing values), same for both SARIMAX models.
                A dummy variable was tried first and rejected on the
                validation period (it distorts a differenced model)
  models        naive (last value), SARIMAX(1,1,1),
                SARIMAX(1,1,1) + lagged policy rate
  evaluation    rolling origin, min train 48 months, horizon 3, step 1
  split         choices made on validation targets before 2024-01; headline
                numbers are on the held out test targets from 2024-01
  metric        MAE in percentage points (one metric everywhere)

Lag sensitivity (3, 6, 9, 12) is reported for transparency but the headline
lag was not chosen from it.
"""

from pathlib import Path
import warnings

import duckdb
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

DB_PATH = Path("data/toronto_housing.duckdb")
OUT_DIR = Path("forecasting/evaluation")

HEADLINE_LAG = 6
LAG_SENSITIVITY = (3, 6, 9, 12)
HORIZON = 3
MIN_TRAIN = 48
ORDER = (1, 1, 1)
COVID_START, COVID_END = "2020-03-01", "2020-12-01"
TEST_START = "2024-01-01"
COVID_MODE = "mask"  # "mask" or "dummy"
MIN_DAYS_FULL_MONTH = 28


def load_monthly(db_path=DB_PATH):
    """Monthly series with a full month of data only."""
    con = duckdb.connect(str(db_path), read_only=True)
    df = con.execute(
        """
        SELECT h.month_start, h.system_occupancy_rate, h.avg_policy_rate,
               d.days
        FROM main_marts.fact_housing_monthly h
        JOIN (
            SELECT date_trunc('month', occupancy_date)::date AS month_start,
                   COUNT(DISTINCT occupancy_date) AS days
            FROM main_marts.fact_shelter_daily GROUP BY 1
        ) d USING (month_start)
        ORDER BY 1
        """
    ).df()
    con.close()
    df["month_start"] = pd.to_datetime(df["month_start"])
    df = df[df["days"] >= MIN_DAYS_FULL_MONTH].drop(columns="days")
    return df.set_index("month_start").astype(float)


def build_frame(df, lag):
    out = pd.DataFrame({"y": df["system_occupancy_rate"]})
    out["covid"] = (
        (out.index >= COVID_START) & (out.index <= COVID_END)
    ).astype(float)
    out["rate_lag"] = df["avg_policy_rate"].shift(lag)
    return out


def _fit_forecast(y, exog, exog_future):
    if COVID_MODE == "mask":
        y = y.copy()
        y[(y.index >= COVID_START) & (y.index <= COVID_END)] = np.nan
        exog = exog.drop(columns="covid")
        exog_future = exog_future.drop(columns="covid")
    model = SARIMAX(
        y, exog=exog, order=ORDER, trend="n",
        enforce_stationarity=False, enforce_invertibility=False,
    )
    res = model.fit(disp=False, maxiter=200)
    return np.asarray(res.forecast(len(exog_future), exog=exog_future))


def rolling_origin(df, lag=HEADLINE_LAG, horizon=HORIZON, min_train=MIN_TRAIN):
    """Return one row per (origin, step) with each model's forecast."""
    if lag < horizon:
        raise ValueError("lag must be at least the horizon to avoid leakage")
    f = build_frame(df, lag).dropna()  # first `lag` months have no lagged rate
    rows = []
    for end in range(min_train, len(f) - horizon + 1):
        train, test = f.iloc[:end], f.iloc[end:end + horizon]
        naive = np.repeat(train["y"].iloc[-1], horizon)
        uni = _fit_forecast(train["y"], train[["covid"]], test[["covid"]])
        rate = _fit_forecast(
            train["y"], train[["covid", "rate_lag"]], test[["covid", "rate_lag"]]
        )
        for k in range(horizon):
            rows.append({
                "origin": train.index[-1], "target": test.index[k], "step": k + 1,
                "actual": test["y"].iloc[k], "naive": naive[k],
                "sarimax": uni[k], "sarimax_rate": rate[k],
            })
    return pd.DataFrame(rows)


MODELS = ("naive", "sarimax", "sarimax_rate")


def mae_table(res, start=None, end=None):
    r = res
    if start is not None:
        r = r[r["target"] >= start]
    if end is not None:
        r = r[r["target"] < end]
    return pd.Series(
        {m: float(np.mean(np.abs(r["actual"] - r[m]))) for m in MODELS}
    ), len(r)


def pct_change(new, base):
    """Percent change in error of `new` versus `base`. Negative is better."""
    return (new - base) / base * 100.0


def summarize(res):
    out = {}
    scopes = {
        "validation": (None, TEST_START),
        "test": (TEST_START, None),
        "all": (None, None),
    }
    for name, (a, b) in scopes.items():
        m, n = mae_table(res, a, b)
        out[name] = {
            "n_forecasts": n,
            **{f"mae_{k}": v for k, v in m.items()},
            "pct_vs_naive": pct_change(m["sarimax_rate"], m["naive"]),
            "pct_vs_univariate": pct_change(m["sarimax_rate"], m["sarimax"]),
        }
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_monthly()
    print(f"Months used: {len(df)} ({df.index.min():%Y-%m} to {df.index.max():%Y-%m})")

    res = rolling_origin(df)
    res.to_csv(OUT_DIR / "rate_forecast_folds.csv", index=False)
    summ = summarize(res)

    lag_rows = []
    for lag in LAG_SENSITIVITY:
        r = rolling_origin(df, lag=lag)
        m, _ = mae_table(r, TEST_START)
        lag_rows.append({
            "lag_months": lag, "mae_naive": m["naive"],
            "mae_sarimax": m["sarimax"],
            "mae_sarimax_rate": m["sarimax_rate"],
            "pct_vs_naive": pct_change(m["sarimax_rate"], m["naive"]),
            "pct_vs_univariate": pct_change(m["sarimax_rate"], m["sarimax"]),
        })
    lag_df = pd.DataFrame(lag_rows).round(3)
    lag_df.to_csv(OUT_DIR / "rate_forecast_lag_sensitivity.csv", index=False)

    rows = []
    for scope, d in summ.items():
        rows.append({"scope": scope, **d})
    pd.DataFrame(rows).round(3).to_csv(OUT_DIR / "rate_forecast_results.csv", index=False)

    for scope, d in summ.items():
        print(f"\n[{scope}] n={d['n_forecasts']}")
        for m in MODELS:
            print(f"  MAE {m:20s} {d['mae_' + m]:.3f} pp")
        print(f"  rate model vs naive:      {d['pct_vs_naive']:+.1f}%")
        print(f"  rate model vs univariate: {d['pct_vs_univariate']:+.1f}%")
    print("\nLag sensitivity (test period):")
    print(lag_df.to_string(index=False))

    one = res[res["step"] == 1].set_index("target")
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(one.index, one["actual"], "k-", label="Actual")
    ax.plot(one.index, one["naive"], "--", color="gray", label="Naive")
    ax.plot(one.index, one["sarimax"], color="tab:blue", label="SARIMAX")
    ax.plot(one.index, one["sarimax_rate"], color="tab:red", label="SARIMAX + policy rate")
    ax.set_ylabel("System occupancy rate (%)")
    ax.set_title("One month ahead forecasts, rolling origin")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "rate_forecast_comparison.png", dpi=130)


if __name__ == "__main__":
    main()
