"""
Ingest Environment Canada historical daily weather for Toronto Pearson.
"""

from pathlib import Path

import duckdb
import pandas as pd
from loguru import logger

from ingestion.config import DATA_RAW, DUCKDB_PATH, EC_STATION_ID
from ingestion.utils import cached_download_csv

EC_BULK_URL = "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"


def ingest_weather(start_year: int = 2017, end_year: int = 2026) -> pd.DataFrame:
    frames = []
    for year in range(start_year, end_year + 1):
        url = (
            f"{EC_BULK_URL}?format=csv&stationID={EC_STATION_ID}"
            f"&Year={year}&Month=1&Day=1&timeframe=2"
        )
        dest = DATA_RAW / f"weather_toronto_{year}.csv"
        try:
            cached_download_csv(url, dest, description=f"Weather {year}", max_age_hours=48.0)
            df = pd.read_csv(dest, encoding="utf-8-sig")
            df["_source_year"] = year
            frames.append(df)
            logger.info(f"  {year}: {len(df):,} rows")
        except Exception as e:
            logger.warning(f"  {year}: failed — {e}")

    if not frames:
        raise RuntimeError("No weather data fetched.")

    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Weather total: {len(combined):,} rows")
    return combined


def load_to_duckdb(df: pd.DataFrame, table_name: str, db_path: Path = DUCKDB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
    count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    con.close()
    logger.info(f"Loaded {count:,} rows into DuckDB: {table_name}")


def main():
    logger.info("=" * 60)
    logger.info("ENVIRONMENT CANADA WEATHER INGESTION")
    logger.info("=" * 60)
    df = ingest_weather()
    load_to_duckdb(df, "raw_weather_daily")
    temp_cols = [c for c in df.columns if "temp" in c.lower()]
    logger.info(f"Temperature columns: {temp_cols}")


if __name__ == "__main__":
    main()
