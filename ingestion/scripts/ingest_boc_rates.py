"""
Ingest Bank of Canada policy interest rate via the Valet API.
"""

from pathlib import Path

import duckdb
import pandas as pd
from loguru import logger

from ingestion.config import BOC_VALET_BASE, BOC_POLICY_RATE_SERIES, DUCKDB_PATH
from ingestion.utils import cached_get


def ingest_boc_interest_rates(start_date: str = "2017-01-01") -> pd.DataFrame:
    url = f"{BOC_VALET_BASE}/observations/{BOC_POLICY_RATE_SERIES}/json"
    params = {"start_date": start_date}
    resp = cached_get(url, params=params, description="Bank of Canada policy rate", max_age_hours=24.0)
    data = resp.json()

    observations = data.get("observations", [])
    if not observations:
        raise RuntimeError("No observations returned from BoC Valet API")

    records = []
    for obs in observations:
        date = obs.get("d")
        value = obs.get(BOC_POLICY_RATE_SERIES, {}).get("v")
        if date and value is not None:
            records.append({"date": date, "policy_rate": float(value)})

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    logger.info(f"Fetched {len(df):,} observations from {df['date'].min()} to {df['date'].max()}")
    return df


def load_to_duckdb(df: pd.DataFrame, table_name: str, db_path: Path = DUCKDB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
    count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    con.close()
    logger.info(f"Loaded {count:,} rows into DuckDB: {table_name}")


def main():
    logger.info("=" * 60)
    logger.info("BANK OF CANADA INTEREST RATE INGESTION")
    logger.info("=" * 60)
    df = ingest_boc_interest_rates()
    load_to_duckdb(df, "raw_boc_interest_rates")
    logger.info(f"Sample:\n{df.tail()}")


if __name__ == "__main__":
    main()
