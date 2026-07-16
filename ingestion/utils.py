"""
Shared ingestion utilities: caching, logging, HTTP helpers.
"""

import hashlib
import json
import time
from pathlib import Path

import requests
from loguru import logger

from ingestion.config import CACHE_DIR, LOG_LEVEL

logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""),
    level=LOG_LEVEL,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | {message}",
)


def _cache_key(url: str, params: dict | None = None) -> str:
    raw = url + json.dumps(params or {}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def cached_get(
    url: str,
    params: dict | None = None,
    cache_dir: Path = CACHE_DIR,
    max_age_hours: float = 24.0,
    description: str = "",
) -> requests.Response:
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(url, params)
    cache_path = cache_dir / f"{key}.json"
    meta_path = cache_dir / f"{key}.meta.json"

    if cache_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        age_hours = (time.time() - meta["timestamp"]) / 3600
        if age_hours < max_age_hours:
            logger.info(f"Cache hit ({age_hours:.1f}h old): {description or url}")
            resp = requests.Response()
            resp.status_code = 200
            resp._content = cache_path.read_bytes()
            resp.encoding = "utf-8"
            return resp
        else:
            logger.info(f"Cache stale ({age_hours:.1f}h old): {description or url}")

    logger.info(f"Fetching: {description or url}")
    resp = requests.get(url, params=params, timeout=120)
    resp.raise_for_status()

    cache_path.write_bytes(resp.content)
    meta_path.write_text(
        json.dumps({"timestamp": time.time(), "url": url, "params": params})
    )
    logger.info(f"Cached: {cache_path.name} ({len(resp.content):,} bytes)")
    return resp


def cached_download_csv(
    url: str,
    dest_path: Path,
    cache_dir: Path = CACHE_DIR,
    max_age_hours: float = 24.0,
    description: str = "",
) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(url)
    meta_path = cache_dir / f"{key}.meta.json"

    if dest_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        age_hours = (time.time() - meta["timestamp"]) / 3600
        if age_hours < max_age_hours:
            logger.info(f"Cache hit ({age_hours:.1f}h old): {description or url}")
            return dest_path

    logger.info(f"Downloading: {description or url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(resp.content)
    meta_path.write_text(json.dumps({"timestamp": time.time(), "url": url}))
    logger.info(f"Saved: {dest_path} ({len(resp.content):,} bytes)")
    return dest_path
