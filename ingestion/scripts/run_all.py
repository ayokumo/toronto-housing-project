"""
Master ingestion runner.

Usage:
    python -m ingestion.scripts.run_all
    python -m ingestion.scripts.run_all shelter
    python -m ingestion.scripts.run_all boc
    python -m ingestion.scripts.run_all weather
"""

import sys
from loguru import logger


def run_shelter():
    from ingestion.scripts.ingest_shelter import main as m
    m()

def run_boc():
    from ingestion.scripts.ingest_boc_rates import main as m
    m()

def run_weather():
    from ingestion.scripts.ingest_weather import main as m
    m()


RUNNERS = {
    "shelter": run_shelter,
    "boc": run_boc,
    "weather": run_weather,
}


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(RUNNERS.keys())
    for target in targets:
        if target not in RUNNERS:
            logger.error(f"Unknown target: {target}. Options: {list(RUNNERS.keys())}")
            continue
        try:
            RUNNERS[target]()
        except Exception as e:
            logger.error(f"FAILED: {target} — {e}")
    logger.info("Ingestion complete.")


if __name__ == "__main__":
    main()
