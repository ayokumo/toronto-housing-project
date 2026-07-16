from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
CACHE_DIR = PROJECT_ROOT / "ingestion" / "cache"
DUCKDB_PATH = PROJECT_ROOT / "data" / "toronto_housing.duckdb"

CKAN_BASE_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
SHELTER_OCCUPANCY_PACKAGE_ID = "21c83b32-d5a8-4106-a54f-010dbe49f6f2"
SHELTER_LEGACY_PACKAGE_ID = "8a6eceb2-821b-4961-a29d-758f3087732d"

BOC_VALET_BASE = "https://www.bankofcanada.ca/valet"
BOC_POLICY_RATE_SERIES = "V39079"

EC_STATION_ID = 51459
EC_CLIMATE_ID = "6158731"

LOG_LEVEL = "INFO"
