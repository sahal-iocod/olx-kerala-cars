# storage.py
import json
import os
import time

from config import SEEN_ADS_FILE, SEEN_ADS_MAX_AGE_DAYS


def load_seen_ads() -> dict:
    """
    Returns {ad_id: unix_timestamp_first_seen}.

    Older versions stored a plain list of ids; those are
    migrated by stamping them with the current time.
    """
    if not os.path.exists(SEEN_ADS_FILE):
        return {}
    try:
        with open(SEEN_ADS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            now = time.time()
            return {str(ad_id): now for ad_id in data}

        if isinstance(data, dict):
            return {str(k): float(v) for k, v in data.items()}

        return {}
    except Exception:
        return {}


def prune_seen_ads(seen: dict, max_age_days: int = SEEN_ADS_MAX_AGE_DAYS, now: float | None = None) -> dict:
    if now is None:
        now = time.time()
    cutoff = now - max_age_days * 86400
    return {ad_id: ts for ad_id, ts in seen.items() if ts >= cutoff}


def save_seen_ads(seen: dict):
    pruned = prune_seen_ads(seen)
    with open(SEEN_ADS_FILE, "w", encoding="utf-8") as f:
        json.dump(pruned, f, ensure_ascii=False, indent=2)


def is_new_ad(ad_id: str, seen: dict) -> bool:
    return str(ad_id) not in seen


def mark_as_seen(ad_id: str, seen: dict):
    seen[str(ad_id)] = time.time()
