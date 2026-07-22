"""
Phase 4 — Shelter Demand Forecasting
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import duckdb
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller
from prophet import Prophet
import warnings
warnings.filterwarnings("ignore")

DB_PATH = Path("data/toronto_housing.duckdb")
OUT_DIR = Path("forecasting/evaluation")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_weekly_data():
    con = duckdb.connect(str(DB_PATH))
    df = con.execute("""
        SELECT
            date_trunc('week', occupancy_date)::date AS week_start,
            ROUND(SUM(occupancy)::float
                / NULLIF(SUM(capacity_actual), 0) * 100, 2) AS system_occupancy_rate,
            SUM(occupancy) AS total_occupied,
            SUM(capacity_actual) AS total_capacity,
            COUNT(DISTINCT occupancy_date) AS days_in_week
        FROM main_marts.fact_shelter_daily
        WHERE year_number BETWEEN 2021 AND 2025
            AND occupancy IS NOT NULL
            AND capacity_actual IS NOT NULL
            AND capacity_actual > 0
        GROUP BY 1
        HAVING COUNT(DISTINCT occupancy_date) >= 5
        ORDER BY 1
    """).df()
    con.close()
    df["week_start"] = pd.to_datetime(df["week_start"])
    df = df.set_index("week_start").asfreq("W-MON")
    df["system_occupancy_rate"] = df["system_occupancy_rate"].interpolate()
    print(f"  {len(df)} weeks ({df.index.min().date()} to {df.index.max().date()})")
    return df


def check_stationarity(series, name="series"):
    result = adfuller(series.dropna(), autolag="AIC")
    print(f"\n  ADF test on {name}:")
    print(f"    Statistic: {result[0]:.4f}, p-value: {result[1]:.4f}")
    print(f"    Stationary: {'YES' if result[1] < 0.05 else 'NO'}")
    return result[1] < 0.05


def naive_forecast(train, horizon):
    idx = pd.date_range(train.index[-1] + pd.Timedelta(weeks=1),
                        periods=horizon, freq="W-MON")
    return pd.Series(train.iloc[-1], index=idx, name="naive")


def seasonal_naive_forecast(train, horizon, season_length=52):
    idx = pd.date_range(train.index[-1] + pd.Timedelta(weeks=1),
                        periods=horizon, freq="W-MON")
    values = []
    for i in range(horizon):
        lb = len(train) - season_length + (i % season_length)
        values.append(train.iloc[lb] if 0 <= lb < len(train) else train.iloc[-1])
    return pd.Series(values, index=idx, name="seasonal_naive")


def sarima_forecast(train, horizon):
    print("  Fitting SARIMA...")
    try:
        model = SARIMAX(train, order=(1,1,1), seasonal_order=(1,1,1,52),
                        enforce_stationarity=False, enforce_invertibility=False)
        fit = model.fit(disp=False, maxiter=200)
        fc = fit.forecast(steps=horizon)
        fc.name = "sarima"
        print(f"    AIC: {fit.aic:.1f}")
        return fc
    except Exception as e:
        print(f"  Full SARIMA failed ({e}), trying simpler...")
        model = SARIMAX(train, order=(1,1,1), seasonal_order=(0,1,1,52),
                        enforce_stationarity=False, enforce_invertibility=False)
        fit = model.fit(disp=False, maxiter=200)
        fc = fit.forecast(steps=horizon)
        fc.name = "sarima"
        return fc


def prophet_forecast(train, horizon):
    print("  Fitting Prophet...")
    pdf = pd.DataFrame({"ds": train.index, "y": train.values})
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                daily_seasonality=False, changepoint_prior_scale=0.05)
    m.fit(pdf)
    future = m.make_future_dataframe(periods=horizon, freq="W-MON")
    fc = m.predict(future).set_index("ds")["yhat"].iloc[-horizon:]
    fc.name = "prophet"
    return fc


def rolling_origin_cv(series, min_train=104, horizon=12, step=4):
    n = len(series)
    fold = 0
    for start in range(min_train, n - horizon + 1, step):
        fold += 1
        yield fold, series.iloc[:start], series.iloc[start:start+horizon]


def evaluate_forecasts(actual, forecasts):
    results = {}
    for name, fc in forecasts.items():
        common = actual.index.intersection(fc.index)
        if len(common) == 0:
            continue
        a, f = actual[common], fc[common]
        mae = np.mean(np.abs(a - f))
        mape = np.mean(np.abs((a - f) / a)) * 100
        results[name] = {"MAE": round(mae, 3), "MAPE": round(mape, 2)}
    return results


def run_cv(series):
    print("\n  Rolling-origin CV (min_train=104w, horizon=12w, step=4w)...")
    all_results = {m: {"MAE": [], "MAPE": []}
                   for m in ["naive", "seasonal_naive", "sarima", "prophet"]}

    for fold, train, test in rolling_origin_cv(series):
        print(f"\n  Fold {fold}: train={len(train)}w, test={len(test)}w")
        forecasts = {
            "naive": naive_forecast(train, len(test)),
            "seasonal_naive": seasonal_naive_forecast(train, len(test)),
            "sarima": sarima_forecast(train, len(test)),
            "prophet": prophet_forecast(train, len(test)),
        }
        metrics = evaluate_forecasts(test, forecasts)
        for name, m in metrics.items():
            all_results[name]["MAE"].append(m["MAE"])
            all_results[name]["MAPE"].append(m["MAPE"])
            print(f"    {name:15s} MAE={m['MAE']:.3f}  MAPE={m['MAPE']:.2f}%")

    summary = {}
    for name in all_results:
        if all_results[name]["MAE"]:
            summary[name] = {
                "mean_MAE": round(np.mean(all_results[name]["MAE"]), 3),
                "mean_MAPE": round(np.mean(all_results[name]["MAPE"]), 2),
                "std_MAE": round(np.std(all_results[name]["MAE"]), 3),
                "n_folds": len(all_results[name]["MAE"]),
            }
    return summary


def plot_cv_results(summary):
    models = list(summary.keys())
    maes = [summary[m]["mean_MAE"] for m in models]
    stds = [summary[m]["std_MAE"] for m in models]
    colors = {"naive":"#888","seasonal_naive":"#aaa","sarima":"#2c7bb6","prophet":"#e63946"}

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar([m.replace("_"," ").title() for m in models], maes,
                  yerr=stds, color=[colors.get(m,"#666") for m in models],
                  alpha=0.85, width=0.5, capsize=5)
    for bar, mae, m in zip(bars, maes, models):
        mape = summary[m]["mean_MAPE"]
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
                f"MAE={mae:.2f}\nMAPE={mape:.1f}%", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Mean Absolute Error (pp)", fontsize=11)
    ax.set_title("Forecast Model Comparison — Rolling-Origin CV", fontsize=12, fontweight="bold")
    plt.tight_layout()
    path = OUT_DIR / "forecast_model_comparison.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"\nSaved: {path}")


def plot_final_forecast(series, horizon=12):
    print("\nFinal forecast (full training set)...")
    fc_sarima = sarima_forecast(series, horizon)
    fc_prophet = prophet_forecast(series, horizon)

    fig, ax = plt.subplots(figsize=(13, 5))
    recent = series.iloc[-52:]
    ax.plot(recent.index, recent.values, color="#2c7bb6", linewidth=2, label="Actual")
    ax.plot(fc_sarima.index, fc_sarima.values, color="#e63946", linewidth=2,
            linestyle="--", label="SARIMA forecast", marker="o", markersize=4)
    ax.plot(fc_prophet.index, fc_prophet.values, color="#f4a261", linewidth=1.5,
            linestyle=":", label="Prophet forecast")
    ax.axhline(95, color="grey", linewidth=1, linestyle=":", alpha=0.6)
    ax.axvline(series.index[-1], color="grey", linewidth=1, alpha=0.4)
    ax.set_ylabel("System Occupancy Rate (%)", fontsize=11)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_title("Toronto Shelter Occupancy — 12-Week Forecast", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    plt.tight_layout()
    path = OUT_DIR / "final_forecast.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved: {path}")


def main():
    print("=" * 60)
    print("PHASE 4 — TIME-SERIES FORECASTING")
    print("=" * 60)

    print("\nLoading weekly data...")
    df = load_weekly_data()
    series = df["system_occupancy_rate"]

    print("\nStationarity checks:")
    is_stat = check_stationarity(series, "level")
    if not is_stat:
        check_stationarity(series.diff().dropna(), "1st diff")

    summary = run_cv(series)

    print("\n" + "=" * 60)
    print("CV RESULTS")
    print("=" * 60)
    for model, m in sorted(summary.items(), key=lambda x: x[1]["mean_MAE"]):
        print(f"  {model:15s} MAE={m['mean_MAE']:.3f} (+/-{m['std_MAE']:.3f}) "
              f"MAPE={m['mean_MAPE']:.2f}% ({m['n_folds']} folds)")

    plot_cv_results(summary)
    plot_final_forecast(series)

    best = min(summary.items(), key=lambda x: x[1]["mean_MAE"])
    print(f"\n  Best model: {best[0]} (MAE={best[1]['mean_MAE']:.3f})")


if __name__ == "__main__":
    main()
