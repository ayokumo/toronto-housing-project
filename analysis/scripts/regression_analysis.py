"""
Statistical Layer — Phase 3
Regression of monthly shelter occupancy on:
  - Temperature (cold weather -> higher demand)
  - Bank of Canada policy rate (higher rates -> housing stress)
  - Time trend (structural growth in demand)
  - Season fixed effects

We are honest about what this model CAN and CANNOT say:
  - CAN: quantify correlations and their uncertainty
  - CANNOT: establish causation (no randomization, many confounders)
"""

from pathlib import Path

import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor

DB_PATH = Path("data/toronto_housing.duckdb")
OUT_DIR = Path("analysis/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data() -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH))
    df = con.execute("""
        SELECT
            f.month_start,
            f.year_number,
            f.month_number,
            f.system_occupancy_rate,
            f.total_occupied,
            f.total_capacity,
            f.avg_policy_rate,
            f.avg_temp_c,
            f.cold_days,
            f.extreme_cold_days,
            f.total_snow_cm,
            d.season
        FROM main_marts.fact_housing_monthly f
        JOIN main_marts.dim_date d
            ON f.month_start = d.date_day
        WHERE f.year_number BETWEEN 2017 AND 2025
            AND f.system_occupancy_rate IS NOT NULL
            AND f.avg_policy_rate IS NOT NULL
            AND f.avg_temp_c IS NOT NULL
        ORDER BY f.month_start
    """).df()
    con.close()
    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    # Time trend: months since start of data
    df["time_trend"] = range(len(df))

    # COVID dummy: 2020 was anomalous (physical distancing reduced capacity)
    df["is_covid"] = (df["year_number"] == 2020).astype(int)

    # Post-2021 structural shift dummy
    df["post_2021"] = (df["year_number"] >= 2021).astype(int)

    # Lag policy rate by 6 months (rate changes take time to affect housing)
    df["policy_rate_lag6"] = df["avg_policy_rate"].shift(6)

    # Season dummies (Winter is reference)
    df["is_spring"] = (df["season"] == "Spring").astype(int)
    df["is_summer"] = (df["season"] == "Summer").astype(int)
    df["is_fall"]   = (df["season"] == "Fall").astype(int)

    return df.dropna()


def run_regression(df: pd.DataFrame):
    """
    OLS regression of system occupancy rate on key predictors.

    Formula uses patsy syntax. We include:
    - avg_temp_c: direct temperature effect
    - policy_rate_lag6: rate effect with 6-month lag
    - time_trend: captures secular growth in demand
    - is_covid: flags the anomalous 2020 period
    - season dummies: seasonal fixed effects
    """
    formula = (
        "system_occupancy_rate ~ "
        "avg_temp_c + "
        "policy_rate_lag6 + "
        "time_trend + "
        "is_covid + "
        "is_spring + is_summer + is_fall"
    )

    model = smf.ols(formula=formula, data=df).fit()
    return model


def plot_actual_vs_fitted(df: pd.DataFrame, model, fitted: pd.Series):
    fig, ax = plt.subplots(figsize=(13, 5))

    ax.plot(df["month_start"], df["system_occupancy_rate"],
            color="#2c7bb6", linewidth=1.8, label="Actual occupancy rate")
    ax.plot(df["month_start"], fitted,
            color="#d7191c", linewidth=1.5, linestyle="--",
            label=f"Model fit (R²={model.rsquared:.2f})")

    ax.axhline(95, color="grey", linewidth=1, linestyle=":",
               label="95% threshold")
    ax.fill_between(df["month_start"],
                    df["system_occupancy_rate"], fitted,
                    alpha=0.1, color="#d7191c", label="Residual")

    ax.set_ylabel("System Occupancy Rate (%)", fontsize=11)
    ax.set_xlabel("Month", fontsize=11)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_title(
        "Toronto Shelter Occupancy — Actual vs Model Fit (2017–2025)",
        fontsize=13, fontweight="bold"
    )
    ax.legend(fontsize=9)
    plt.tight_layout()
    path = OUT_DIR / "regression_fit.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved: {path}")


def plot_coefficients(model):
    """Plot regression coefficients with 95% confidence intervals."""
    # Exclude intercept and dummy vars from main plot
    keep = ["avg_temp_c", "policy_rate_lag6", "time_trend"]
    labels = {
        "avg_temp_c":        "Avg temperature (°C)",
        "policy_rate_lag6":  "Policy rate, 6m lag (%)",
        "time_trend":        "Time trend (months)",
    }

    coefs  = model.params[keep]
    ci_low = model.conf_int()[0][keep]
    ci_hi  = model.conf_int()[1][keep]
    pvals  = model.pvalues[keep]

    fig, ax = plt.subplots(figsize=(8, 4))
    y_pos = range(len(keep))

    for i, var in enumerate(keep):
        color = "#2c7bb6" if pvals[var] < 0.05 else "#aaa"
        ax.barh(i, coefs[var], color=color, alpha=0.85, height=0.5)
        ax.plot([ci_low[var], ci_hi[var]], [i, i],
                color="black", linewidth=2)
        ax.plot([ci_low[var], ci_hi[var]], [i, i],
                "o", color="black", markersize=4)
        sig = "***" if pvals[var] < 0.001 else "**" if pvals[var] < 0.01 else "*" if pvals[var] < 0.05 else ""
        ax.text(ci_hi[var] + 0.05, i, f"{coefs[var]:.3f}{sig}",
                va="center", fontsize=9)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels([labels[v] for v in keep], fontsize=10)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Coefficient (percentage points change in occupancy rate)", fontsize=9)
    ax.set_title(
        "Regression Coefficients with 95% CI\n(blue = p<0.05, grey = not significant)",
        fontsize=11, fontweight="bold"
    )
    plt.tight_layout()
    path = OUT_DIR / "regression_coefficients.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved: {path}")


def check_vif(df: pd.DataFrame, predictors: list) -> pd.DataFrame:
    """Variance inflation factors to check for multicollinearity."""
    X = df[predictors].dropna()
    X = pd.concat([pd.Series(1, index=X.index, name="const"), X], axis=1)
    vif_data = pd.DataFrame()
    vif_data["variable"] = X.columns
    vif_data["VIF"] = [
        variance_inflation_factor(X.values, i) for i in range(X.shape[1])
    ]
    return vif_data[vif_data["variable"] != "const"]


def main():
    print("=" * 60)
    print("PHASE 3 — REGRESSION ANALYSIS")
    print("=" * 60)

    print("\nLoading data...")
    df = load_data()
    print(f"  {len(df)} months loaded (2017–2025)")

    print("\nPreparing features...")
    df = prepare_features(df)
    print(f"  {len(df)} months after dropping NAs (lag removes first 6)")

    print("\nRunning OLS regression...")
    model = run_regression(df)
    fitted = model.fittedvalues

    print("\n" + "=" * 60)
    print(model.summary())
    print("=" * 60)

    print("\nVariance Inflation Factors (VIF > 10 = multicollinearity concern):")
    predictors = ["avg_temp_c", "policy_rate_lag6", "time_trend",
                  "is_covid", "is_spring", "is_summer", "is_fall"]
    vif = check_vif(df, predictors)
    print(vif.to_string(index=False))

    print("\nGenerating charts...")
    plot_actual_vs_fitted(df, model, fitted)
    plot_coefficients(model)

    print("\n" + "=" * 60)
    print("KEY FINDINGS (with honest causal caveats)")
    print("=" * 60)

    temp_coef  = model.params["avg_temp_c"]
    rate_coef  = model.params["policy_rate_lag6"]
    trend_coef = model.params["time_trend"]
    r2         = model.rsquared

    print(f"\nR² = {r2:.3f} — model explains {r2*100:.1f}% of variance in occupancy rate")
    print(f"\nTemperature: {temp_coef:+.3f} pp per °C")
    print(f"  -> A 10°C colder month is associated with a {abs(temp_coef)*10:.1f}pp higher occupancy rate")
    print(f"  -> CORRELATION, not causation. Cold weather likely increases demand")
    print(f"     AND reduces available housing options simultaneously.")
    print(f"\nPolicy rate (6m lag): {rate_coef:+.3f} pp per 1% rate increase")
    print(f"  -> A 1pp rate increase is associated with {rate_coef:+.3f}pp change in occupancy")
    print(f"  -> CONFOUNDED by many factors: rate rises coincided with post-COVID")
    print(f"     housing market stress. Cannot isolate rate effect from other 2022+ changes.")
    print(f"\nTime trend: {trend_coef:+.3f} pp per month")
    print(f"  -> Structural growth of ~{trend_coef*12:.2f}pp per year independent of other factors")
    print(f"  -> This is the most robust finding: demand is growing structurally.")


if __name__ == "__main__":
    main()
