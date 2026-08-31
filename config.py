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

def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip())
    except (ValueError, AttributeError):
        return default


# Run browsers without a visible window (needed for VPS / 24-7 use).
# Set HEADLESS=false in .env if OLX starts blocking headless sessions.
HEADLESS = _env_bool("HEADLESS", True)

CHECK_INTERVAL_MINUTES = _env_int("CHECK_INTERVAL_MINUTES", 5)

MAX_LISTINGS_TO_CHECK = _env_int("MAX_LISTINGS_TO_CHECK", 25)

# Seen ads older than this are pruned so seen_ads.json stays bounded.
SEEN_ADS_MAX_AGE_DAYS = _env_int("SEEN_ADS_MAX_AGE_DAYS", 60)


# =========================================================
# File paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

SEEN_ADS_FILE = BASE_DIR / "seen_ads.json"

FILTERS_FILE = BASE_DIR / "filters.json"

LOCATION_CACHE_FILE = BASE_DIR / "location_cache.json"


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