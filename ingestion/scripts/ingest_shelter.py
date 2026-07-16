"""
Ingest Toronto Daily Shelter & Overnight Service Occupancy & Capacity data.
"""

from pathlib import Path

import duckdb
import pandas as pd
from loguru import logger

from ingestion.config import CKAN_BASE_URL, DATA_RAW, DUCKDB_PATH
from ingestion.utils import cached_download_csv, cached_get

LEGACY_DATASTORE_RESOURCES = {
    2017: "afe951ad-b0de-41af-bcc2-8635610626c4",
    2018: "c93028b7-d043-437c-a3ae-cde81b559ada",
    2019: "49fafe18-9e07-4729-88bf-27fee5518b89",
    2020: "800cc97f-34b3-4d4d-9bc1-6e2ce2d6f44a",
}

LEGACY_CSV_RESOURCES = {
    2017: "c07041d2-633f-43cf-8372-8133474bf4f4",
    2018: "af47a4d4-4339-446d-bf53-7983f78a80bc",
    2019: "3ea9d9ba-f05f-4055-bcc3-333f699c5e77",
    2020: "9e076fe4-2f86-48d7-a6e4-93710ca715ae",
}

CURRENT_PACKAGE_ID = "21c83b32-d5a8-4106-a54f-010dbe49f6f2"


def _fetch_datastore_page(resource_id: str, offset: int = 0, limit: int = 10000) -> dict:
    url = f"{CKAN_BASE_URL}/api/3/action/datastore_search"
    params = {"id": resource_id, "offset": offset, "limit": limit}
    resp = cached_get(url, params=params, description=f"datastore offset={offset}", max_age_hours=12.0)
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"CKAN API error: {data}")
    return data["result"]


def _fetch_legacy_via_datastore(resource_id: str, year: int) -> pd.DataFrame:
    offset, frames = 0, []
    while True:
        result = _fetch_datastore_page(resource_id, offset=offset)
        records = result.get("records", [])
        if not records:
            break
        frames.append(pd.DataFrame(records))
        total = result.get("total", 0)
        offset += len(records)
        logger.info(f"  {year}: fetched {offset:,} / {total:,}")
        if offset >= total:
            break
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    if "_id" in df.columns:
        df = df.drop(columns=["_id"])
    return df


def _fetch_legacy_via_csv(resource_id: str, year: int) -> pd.DataFrame:
    url = (
        f"{CKAN_BASE_URL}/dataset/8a6eceb2-821b-4961-a29d-758f3087732d"
        f"/resource/{resource_id}/download/daily-shelter-occupancy-{year}.csv"
    )
    dest = DATA_RAW / f"shelter_occupancy_legacy_{year}.csv"
    cached_download_csv(url, dest, description=f"Legacy shelter {year}")
    return pd.read_csv(dest)


def ingest_legacy_shelter_data() -> pd.DataFrame:
    frames = []
    for year in sorted(LEGACY_DATASTORE_RESOURCES.keys()):
        df = pd.DataFrame()

        try:
            logger.info(f"Trying datastore API for legacy {year}...")
            df = _fetch_legacy_via_datastore(LEGACY_DATASTORE_RESOURCES[year], year)
        except Exception as e:
            logger.warning(f"  Datastore failed for {year}: {e}")

        if df.empty and year in LEGACY_CSV_RESOURCES:
            try:
                logger.info(f"Trying CSV download for legacy {year}...")
                df = _fetch_legacy_via_csv(LEGACY_CSV_RESOURCES[year], year)
            except Exception as e:
                logger.warning(f"  CSV download failed for {year}: {e}")

        manual_path = DATA_RAW / f"shelter_occupancy_legacy_{year}.csv"
        if df.empty and manual_path.exists():
            logger.info(f"Found manually placed file: {manual_path}")
            df = pd.read_csv(manual_path)

        if df.empty:
            logger.error(f"Could not fetch legacy {year}. Place CSV at: {manual_path}")
            continue

        df["_source_year"] = year
        frames.append(df)
        logger.info(f"  {year}: {len(df):,} rows")

    if not frames:
        raise RuntimeError("Could not fetch any legacy shelter data.")

    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Legacy total: {len(combined):,} rows")
    return combined


def _get_current_resource_ids() -> list:
    url = f"{CKAN_BASE_URL}/api/3/action/package_show"
    resp = cached_get(url, params={"id": CURRENT_PACKAGE_ID}, description="Shelter package metadata", max_age_hours=24.0)
    package = resp.json()["result"]
    resource_ids = []
    for r in package.get("resources", []):
        fmt = (r.get("format") or "").upper()
        if fmt == "CSV" and r.get("datastore_active", False):
            resource_ids.append(r["id"])
            logger.info(f"  Found datastore resource: {r.get('name', 'unnamed')} ({r['id']})")
    if not resource_ids:
        for r in package.get("resources", []):
            if (r.get("format") or "").upper() == "CSV":
                resource_ids.append(r["id"])
                logger.info(f"  Found CSV resource: {r.get('name', 'unnamed')} ({r['id']})")
    return resource_ids


def ingest_current_shelter_data() -> pd.DataFrame:
    resource_ids = _get_current_resource_ids()
    if not resource_ids:
        raise RuntimeError("No CSV resources found in shelter occupancy package")

    all_frames = []
    for rid in resource_ids:
        logger.info(f"Fetching resource: {rid}")
        offset, resource_frames = 0, []
        while True:
            result = _fetch_datastore_page(rid, offset=offset)
            records = result.get("records", [])
            if not records:
                break
            resource_frames.append(pd.DataFrame(records))
            total = result.get("total", 0)
            offset += len(records)
            logger.info(f"  Fetched {offset:,} / {total:,}")
            if offset >= total:
                break
        if resource_frames:
            df = pd.concat(resource_frames, ignore_index=True)
            if "_id" in df.columns:
                df = df.drop(columns=["_id"])
            all_frames.append(df)
            logger.info(f"  Resource {rid}: {len(df):,} rows")

    if not all_frames:
        raise RuntimeError("No records fetched.")

    combined = pd.concat(all_frames, ignore_index=True)
    pre_dedup = len(combined)
    combined = combined.drop_duplicates()
    if len(combined) < pre_dedup:
        logger.info(f"  Removed {pre_dedup - len(combined):,} duplicates")
    logger.info(f"Current total: {len(combined):,} rows")
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
    logger.info("SHELTER OCCUPANCY INGESTION")
    logger.info("=" * 60)

    logger.info("--- Legacy data (2017-2020) ---")
    legacy_df = ingest_legacy_shelter_data()
    load_to_duckdb(legacy_df, "raw_shelter_occupancy_legacy")

    logger.info("--- Current data (2021+) ---")
    current_df = ingest_current_shelter_data()
    load_to_duckdb(current_df, "raw_shelter_occupancy")

    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info(f"  Legacy columns:  {legacy_df.columns.tolist()}")
    logger.info(f"  Current columns: {current_df.columns.tolist()}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
