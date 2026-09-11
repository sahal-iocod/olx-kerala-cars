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
# On the VPS this works because the systemd unit runs under xvfb-run,
# which provides a virtual display for headed Chrome.
HEADLESS = _env_bool("HEADLESS", True)

CHECK_INTERVAL_MINUTES = _env_int("CHECK_INTERVAL_MINUTES", 15)

MAX_LISTINGS_TO_CHECK = _env_int("MAX_LISTINGS_TO_CHECK", 25)


# =========================================================
# Proxy (optional)
# =========================================================
#
# OLX's edge (Akamai) scores datacenter IP ranges as bots, so a
# VPS can be blocked no matter how the browser is configured.
# Routing Chrome through a residential/mobile proxy gives it an
# IP that passes. Leave PROXY_SERVER empty to go direct.
#
#   PROXY_SERVER=http://gate.example-proxy.com:8000
#   PROXY_USERNAME=...
#   PROXY_PASSWORD=...

PROXY_SERVER = (os.getenv("PROXY_SERVER") or "").strip()
PROXY_USERNAME = (os.getenv("PROXY_USERNAME") or "").strip()
PROXY_PASSWORD = (os.getenv("PROXY_PASSWORD") or "").strip()


def get_proxy_config() -> dict | None:
    """
    Playwright proxy dict, or None when no proxy is configured.
    """
    if not PROXY_SERVER:
        return None

    proxy: dict = {"server": PROXY_SERVER}

    if PROXY_USERNAME:
        proxy["username"] = PROXY_USERNAME
        proxy["password"] = PROXY_PASSWORD

    return proxy

# Seen ads older than this are pruned so seen_ads.json stays bounded.
SEEN_ADS_MAX_AGE_DAYS = _env_int("SEEN_ADS_MAX_AGE_DAYS", 60)


# =========================================================
# File paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

SEEN_ADS_FILE = BASE_DIR / "seen_ads.json"

FILTERS_FILE = BASE_DIR / "filters.json"

LOCATION_CACHE_FILE = BASE_DIR / "location_cache.json"

# Legacy cookie jar, superseded by BROWSER_PROFILE_DIR below.
# Still named here so older installs can be cleaned up.
BROWSER_STATE_FILE = BASE_DIR / "browser_state.json"

# Full Chrome profile reused between runs.
#
# A storage_state snapshot replayed into a fresh browser is
# itself a bot signal: Akamai's _abck cookie is meant to be
# refreshed in place by the browser that earned it, not
# restored from a file. Keeping the real profile directory lets
# that cookie age normally and carries localStorage/IndexedDB
# along with it.
BROWSER_PROFILE_DIR = BASE_DIR / "browser_profile"


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
    "seller_type": "",
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