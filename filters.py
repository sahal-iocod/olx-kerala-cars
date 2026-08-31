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

    # NOTE: the location filter is deliberately NOT checked here.
    # It is already enforced server-side via the resolved location
    # slug (e.g. kozhikode_g4058877) in both the page URL and the
    # API query. Listings report their sublocality ("Feroke",
    # "Palazhi", ...), which rarely contains the city name, so a
    # local text match would wrongly reject nearly everything.

    # For brand/fuel/transmission, prefer the structured field
    # from the API listing when present; the title alone often
    # doesn't mention fuel or transmission, and filtering on it
    # would wrongly drop valid cars.
    brand_filter = normalize_text(filters.get("brand", ""))
    if brand_filter:
        from olx_api import normalize_brand

        brand_value = normalize_text(car.get("brand") or "")
        haystack = brand_value if brand_value else title

        # Compare with spaces/hyphens squashed so "maruthi"
        # (normalized to "maruti-suzuki") matches a brand
        # field or title saying "Maruti Suzuki".
        def squash(text):
            return re.sub(r"[\s-]+", "", text)

        if squash(normalize_brand(brand_filter)) not in squash(haystack):
            return False

    model_filter = normalize_text(filters.get("model", ""))
    if model_filter:
        model_value = normalize_text(car.get("model") or "")
        # Match against the structured model field plus the
        # title — "creta" matches model "Creta" or a title
        # like "Hyundai Creta 1.6 SX".
        haystack = f"{model_value} {title}".strip()
        if not text_matches_any(haystack, [model_filter]):
            return False

    fuel_filter = normalize_text(filters.get("fuel", ""))
    if fuel_filter:
        fuel_value = normalize_text(car.get("fuel") or "")
        if fuel_value:
            if not text_matches_any(fuel_value, transmission_aliases(fuel_filter)):
                return False
        # No structured fuel data: only reject when the title
        # explicitly names a different fuel type.
        elif title and not text_matches_any(title, transmission_aliases(fuel_filter)):
            other_fuels = {"petrol", "diesel", "cng", "electric", "hybrid", "lpg"} - {fuel_filter}
            if any(f in title for f in other_fuels):
                return False

    transmission_filter = normalize_text(filters.get("transmission", ""))
    if transmission_filter:
        transmission_value = normalize_text(car.get("transmission") or "")
        if transmission_value:
            if not text_matches_any(transmission_value, transmission_aliases(transmission_filter)):
                return False

    # Seller filter — uses the structured flags from the API
    # (is_business / dealer_showroom_enabled -> "dealer",
    # is_kyc_verified_user -> verified). Cars from the HTML
    # fallback have no seller info; those pass rather than
    # being wrongly rejected.
    seller_filter = normalize_text(filters.get("seller_type", ""))
    if seller_filter and seller_filter != "any":
        seller = car.get("seller")        # "owner" / "dealer" / None
        verified = car.get("verified")    # True / False / None

        if seller_filter == "owner" and seller == "dealer":
            return False
        if seller_filter == "dealer" and seller == "owner":
            return False
        if seller_filter == "verified" and verified is False:
            return False
        if seller_filter == "verified_owner":
            if seller == "dealer" or verified is False:
                return False

    keyword_filter = normalize_text(filters.get("keyword", ""))
    if keyword_filter and not text_matches_any(f"{title} {location}", [keyword_filter]):
        return False

    return True
