import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


# =========================================================
# Telegram
# =========================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# =========================================================
# OLX
# =========================================================

OLX_BASE_URL = (
    "https://www.olx.in/kerala_g2001160/cars_c84"
)


# =========================================================
# Scraper settings
# =========================================================

CHECK_INTERVAL_MINUTES = 12

MAX_LISTINGS_TO_CHECK = 25


# =========================================================
# File paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

SEEN_ADS_FILE = BASE_DIR / "seen_ads.json"

FILTERS_FILE = BASE_DIR / "filters.json"


# =========================================================
# Default filters
# =========================================================

DEFAULT_FILTERS = {
    "location": "",
    "min_price": "",
    "max_price": "",
    "min_year": "",
    "max_year": "",
    "min_km": "",
    "max_km": "",
    "brand": "",
    "model": "",
    "fuel": "",
    "transmission": "",
    "keyword": "",
}


# =========================================================
# Load filters
# =========================================================

def load_filters():
    if not FILTERS_FILE.exists():
        return DEFAULT_FILTERS.copy()

    try:
        with FILTERS_FILE.open(
            "r",
            encoding="utf-8"
        ) as fh:

            data = json.load(fh)

        if not isinstance(data, dict):
            return DEFAULT_FILTERS.copy()

        filters = DEFAULT_FILTERS.copy()
        filters.update(data)

        return filters

    except (
        json.JSONDecodeError,
        OSError,
        TypeError,
    ):
        return DEFAULT_FILTERS.copy()


# =========================================================
# Save filters
# =========================================================

def save_filters(filters):
    with FILTERS_FILE.open(
        "w",
        encoding="utf-8"
    ) as fh:

        json.dump(
            filters,
            fh,
            indent=2,
            ensure_ascii=False,
        )