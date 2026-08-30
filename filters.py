import re


def to_int(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace("₹", "").replace(" ", "")
    try:
        return int(float(text))
    except ValueError:
        return None


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def text_matches_any(text: str, values):
    if not values:
        return True
    haystack = normalize_text(text)
    if not haystack:
        return False
    for value in values:
        item = normalize_text(value)
        if item and item in haystack:
            return True
    return False


def transmission_aliases(value):
    v = normalize_text(value)
    if not v:
        return []
    aliases = {
        "manual": ["manual", "mt"],
        "automatic": ["automatic", "at", "cvt", "amt", "auto"],
        "auto": ["automatic", "at", "cvt", "amt", "auto"],
        "diesel": ["diesel"],
        "petrol": ["petrol"],
        "cng": ["cng"],
        "hybrid": ["hybrid"],
    }
    return aliases.get(v, [v])


def matches_filters(car: dict, filters: dict) -> bool:
    if not car:
        return False

    value_price = to_int(car.get("price", "0"))
    value_year = to_int(car.get("year"))
    value_km = to_int(car.get("km"))
    location = normalize_text(car.get("location", ""))
    title = normalize_text(car.get("title", ""))

    min_price = to_int(filters.get("min_price"))
    max_price = to_int(filters.get("max_price"))
    min_year = to_int(filters.get("min_year"))
    max_year = to_int(filters.get("max_year"))
    min_km = to_int(filters.get("min_km"))
    max_km = to_int(filters.get("max_km"))

    if min_price is not None and value_price is not None and value_price < min_price:
        return False
    if max_price is not None and value_price is not None and value_price > max_price:
        return False
    if min_year is not None and value_year is not None and value_year < min_year:
        return False
    if max_year is not None and value_year is not None and value_year > max_year:
        return False
    if min_km is not None and value_km is not None and value_km < min_km:
        return False
    if max_km is not None and value_km is not None and value_km > max_km:
        return False

    location_filter = normalize_text(filters.get("location", ""))
    if location_filter and not text_matches_any(f"{location} {title}", [location_filter]):
        return False

    brand_filter = normalize_text(filters.get("brand", ""))
    if brand_filter and not text_matches_any(title, [brand_filter]):
        return False

    fuel_filter = normalize_text(filters.get("fuel", ""))
    if fuel_filter and not text_matches_any(title, transmission_aliases(fuel_filter)):
        return False

    transmission_filter = normalize_text(filters.get("transmission", ""))
    if transmission_filter and not text_matches_any(title, transmission_aliases(transmission_filter)):
        return False

    keyword_filter = normalize_text(filters.get("keyword", ""))
    if keyword_filter and not text_matches_any(f"{title} {location}", [keyword_filter]):
        return False

    return True
