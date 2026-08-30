# storage.py
import json
import os
from config import SEEN_ADS_FILE


def load_seen_ads() -> set:
    if not os.path.exists(SEEN_ADS_FILE):
        return set()
    try:
        with open(SEEN_ADS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data)
    except Exception:
        return set()


def save_seen_ads(seen: set):
    with open(SEEN_ADS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False, indent=2)


def is_new_ad(ad_id: str, seen: set) -> bool:
    return ad_id not in seen


def mark_as_seen(ad_id: str, seen: set):
    seen.add(ad_id)
