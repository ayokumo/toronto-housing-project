"""
Project-wide configuration: paths, URLs, and constants.

All data source URLs are defined here so there's one place to update
if an endpoint changes. Cache paths ensure we don't re-download on
every run.
"""

from pathlib import Path

# ── Project paths ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
CACHE_DIR = PROJECT_ROOT / "ingestion" / "cache"
DUCKDB_PATH = PROJECT_ROOT / "data" / "toronto_housing.duckdb"

# ── Toronto Open Data (CKAN API) ──────────────────────────────────
CKAN_BASE_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca"

# Package IDs from the Toronto Open Data portal
SHELTER_OCCUPANCY_PACKAGE_ID = "21c83b32-d5a8-4106-a54f-010dbe49f6f2"  # 2021+
SHELTER_LEGACY_PACKAGE_ID = "8a6eceb2-821b-4c39-bc9f-9b15b6e25e3e"     # 2017-2020

# ── Bank of Canada Valet API ──────────────────────────────────────
BOC_VALET_BASE = "https://www.bankofcanada.ca/valet"
BOC_POLICY_RATE_SERIES = "V39079"  # Target for the overnight rate

# ── Environment Canada ────────────────────────────────────────────
# Toronto Pearson Intl A
EC_STATION_ID = 51459
EC_CLIMATE_ID = "6158731"

# ── CMHC ──────────────────────────────────────────────────────────
# CMHC data is Excel download — we store the URL pattern but will
# likely need to download manually and place in data/raw/
CMHC_NOTE = "Download Rental Market Survey Excel tables from cmhc-schl.gc.ca"

# ── StatCan Census ────────────────────────────────────────────────
STATCAN_NOTE = "Download Census Profile 2021 CSV for Toronto CSD from statcan.gc.ca"

# ── Logging ───────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
