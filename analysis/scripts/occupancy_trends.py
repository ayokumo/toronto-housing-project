"""
Occupancy Trends Analysis
Descriptive layer — Phase 3

Answers:
- How has system-wide occupancy changed from 2017 to 2026?
- Which sectors (Men/Women/Youth/Families) show the most stress?
- Is there seasonal variation? (hypothesis: winter = higher demand)

Outputs saved to analysis/outputs/
"""

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

DB_PATH = Path("data/toronto_housing.duckdb")
OUT_DIR = Path("analysis/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    return duckdb.connect(str(DB_PATH))


# ── 1. Annual system-wide trend ───────────────────────────────────
def plot_annual_trend():
    con = get_connection()
    df = con.execute("""
        SELECT
            year_number,
            ROUND(AVG(system_occupancy_rate), 1) as avg_occupancy_rate,
            SUM(total_occupied)                  as total_occupied,
            SUM(total_capacity)                  as total_capacity
        FROM main_marts.fact_housing_monthly
        WHERE year_number BETWEEN 2017 AND 2026
        GROUP BY year_number
        ORDER BY year_number
    """).df()
    con.close()

    fig, ax1 = plt.subplots(figsize=(12, 5))

    bars = ax1.bar(
        df["year_number"], df["avg_occupancy_rate"],
        color="#2c7bb6", alpha=0.85, width=0.6
    )
    ax1.set_xlabel("Year", fontsize=12)
    ax1.set_ylabel("Average Occupancy Rate (%)", fontsize=12)
    ax1.set_ylim(0, 110)
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax1.axhline(95, color="#d7191c", linewidth=1.5,
                linestyle="--", label="95% threshold (effectively full)")
    ax1.axvline(2020.5, color="grey", linewidth=1, linestyle=":",
                label="Schema change (legacy → current)")

    for bar, val in zip(bars, df["avg_occupancy_rate"]):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f"{val}%", ha="center", va="bottom", fontsize=9)

    ax1.set_title(
        "Toronto Shelter System — Annual Average Occupancy Rate (2017–2026)",
        fontsize=13, fontweight="bold"
    )
    ax1.legend(fontsize=10)
    plt.tight_layout()
    path = OUT_DIR / "annual_occupancy_trend.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved: {path}")
    return df


# ── 2. Seasonal pattern ───────────────────────────────────────────
def plot_seasonal_pattern():
    con = get_connection()
    df = con.execute("""
        SELECT
            d.season,
            ROUND(AVG(f.system_occupancy_rate), 1) as avg_rate,
            COUNT(*) as months
        FROM main_marts.fact_housing_monthly f
        JOIN main_marts.dim_date d
            ON f.month_start = d.date_day
        WHERE f.year_number BETWEEN 2017 AND 2025
        GROUP BY d.season
        ORDER BY avg_rate DESC
    """).df()
    con.close()

    season_order = ["Winter", "Spring", "Summer", "Fall"]
    df["season"] = pd.Categorical(df["season"], categories=season_order, ordered=True)
    df = df.sort_values("season")

    colors = {"Winter": "#2c7bb6", "Spring": "#abdda4",
              "Summer": "#fdae61", "Fall": "#d7191c"}

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(
        df["season"],
        df["avg_rate"],
        color=[colors[s] for s in df["season"]],
        alpha=0.9, width=0.5
    )
    ax.set_ylabel("Average Occupancy Rate (%)", fontsize=12)
    ax.set_ylim(0, 110)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.axhline(95, color="#d7191c", linewidth=1.5,
               linestyle="--", label="95% threshold")

    for bar, val in zip(bars, df["avg_rate"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{val}%", ha="center", va="bottom", fontsize=11)

    ax.set_title(
        "Shelter Occupancy by Season (2017–2025)",
        fontsize=13, fontweight="bold"
    )
    ax.legend(fontsize=10)
    plt.tight_layout()
    path = OUT_DIR / "seasonal_occupancy.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved: {path}")
    return df


# ── 3. Sector breakdown ───────────────────────────────────────────
def plot_sector_trend():
    con = get_connection()
    df = con.execute("""
        SELECT
            year_number,
            sector,
            ROUND(AVG(occupancy_rate), 1) as avg_rate
        FROM main_marts.fact_shelter_daily
        WHERE year_number BETWEEN 2017 AND 2025
            AND occupancy_rate IS NOT NULL
            AND sector IN ('MEN', 'WOMEN', 'YOUTH', 'FAMILIES')
        GROUP BY year_number, sector
        ORDER BY year_number, sector
    """).df()
    con.close()

    sector_colors = {
        "MEN":      "#2c7bb6",
        "WOMEN":    "#d7191c",
        "YOUTH":    "#fdae61",
        "FAMILIES": "#1a9641",
    }

    fig, ax = plt.subplots(figsize=(12, 5))
    for sector, group in df.groupby("sector"):
        ax.plot(
            group["year_number"], group["avg_rate"],
            marker="o", linewidth=2,
            color=sector_colors.get(sector, "grey"),
            label=sector.capitalize()
        )

    ax.axhline(95, color="grey", linewidth=1, linestyle="--",
               label="95% threshold")
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Average Occupancy Rate (%)", fontsize=12)
    ax.set_ylim(0, 115)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_title(
        "Shelter Occupancy Rate by Sector (2017–2025)",
        fontsize=13, fontweight="bold"
    )
    ax.legend(fontsize=10)
    plt.tight_layout()
    path = OUT_DIR / "sector_occupancy_trend.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved: {path}")
    return df


# ── 4. Most stressed shelters ─────────────────────────────────────
def top_stressed_shelters():
    con = get_connection()
    df = con.execute("""
        SELECT
            location_name,
            sector,
            ROUND(AVG(occupancy_rate), 1)          as avg_occupancy_rate,
            COUNT(*) filter (where is_effectively_full)  as days_full,
            COUNT(*)                                as total_days,
            ROUND(
                COUNT(*) filter (where is_effectively_full)::float
                / COUNT(*) * 100, 1
            )                                       as pct_days_full
        FROM main_marts.fact_shelter_daily
        WHERE year_number >= 2023
            AND occupancy_rate IS NOT NULL
        GROUP BY location_name, sector
        HAVING COUNT(*) > 100
        ORDER BY avg_occupancy_rate DESC
        LIMIT 15
    """).df()
    con.close()

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(
        df["location_name"] + " (" + df["sector"].str.capitalize() + ")",
        df["avg_occupancy_rate"],
        color="#d7191c", alpha=0.8
    )
    ax.set_xlabel("Average Occupancy Rate (%)", fontsize=11)
    ax.axvline(95, color="grey", linewidth=1.5, linestyle="--",
               label="95% threshold")
    ax.set_title(
        "Top 15 Most Stressed Shelters (2023–2025)",
        fontsize=13, fontweight="bold"
    )
    ax.legend(fontsize=10)
    ax.invert_yaxis()
    plt.tight_layout()
    path = OUT_DIR / "most_stressed_shelters.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved: {path}")
    return df


def main():
    print("=" * 60)
    print("PHASE 3 — OCCUPANCY TRENDS ANALYSIS")
    print("=" * 60)

    print("\n1. Annual trend...")
    annual = plot_annual_trend()
    print(annual.to_string(index=False))

    print("\n2. Seasonal pattern...")
    seasonal = plot_seasonal_pattern()
    print(seasonal.to_string(index=False))

    print("\n3. Sector breakdown...")
    plot_sector_trend()

    print("\n4. Most stressed shelters (2023+)...")
    stressed = top_stressed_shelters()
    print(stressed[["location_name", "sector", "avg_occupancy_rate",
                     "pct_days_full"]].to_string(index=False))

    print("\nAll outputs saved to analysis/outputs/")


if __name__ == "__main__":
    main()
