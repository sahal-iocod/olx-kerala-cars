from urllib.parse import quote

from config import OLX_BASE_URL
from olx_api import normalize_brand
from olx_location import resolve_olx_location


def to_int(value):
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    text = (
        text
        .replace(",", "")
        .replace("₹", "")
        .replace(" ", "")
    )

    try:
        return int(float(text))
    except ValueError:
        return None


def clean_value(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def build_olx_url(filters, location_slug=None):

    # =====================================================
    # LOCATION
    # =====================================================

    location = clean_value(
        filters.get("location")
    )

    # Dynamically resolve (cached after first time):
    #
    # "kochi"
    #     ↓
    # "kochi_g4058873"
    #
    # Empty location:
    #     ↓
    # "kerala_g2001160"

    if location_slug is None:
        location_slug = resolve_olx_location(
            location
        )

    base_url = (
        f"https://www.olx.in/"
        f"{location_slug}/cars_c84"
    )

    # =====================================================
    # KEYWORD (part of the URL path on OLX)
    # =====================================================

    keyword = clean_value(
        filters.get("keyword")
    )

    if keyword:
        base_url += f"/q-{quote(keyword)}"

    print(
        f"📍 Location input: "
        f"{location or 'Kerala'}"
    )

    print(
        f"📍 Resolved location: "
        f"{location_slug}"
    )

    # =====================================================
    # FILTER VALUES
    # =====================================================

    filter_values = []

    # =====================================================
    # BRAND
    # =====================================================

    brand = normalize_brand(
        clean_value(
            filters.get("brand")
        )
    )

    if brand:
        filter_values.append(
            f"make_eq_{brand}"
        )

    # =====================================================
    # MODEL
    # =====================================================

    model = clean_value(
        filters.get("model")
    )

    if model:
        # OLX model slugs are brand-prefixed and hyphenated,
        # e.g. "creta" + brand "hyundai" -> "hyundai-creta"
        model_slug = model.replace(" ", "-")

        if brand and not model_slug.startswith(brand):
            model_slug = f"{brand}-{model_slug}"

        filter_values.append(
            f"model_eq_{model_slug}"
        )

    # =====================================================
    # FUEL
    # =====================================================

    fuel = clean_value(
        filters.get("fuel")
    )

    if fuel:

        fuel_map = {
            "petrol": "petrol",
            "diesel": "diesel",
            "cng": "cng",
            "electric": "electric",
            "hybrid": "hybrid",
            "lpg": "lpg",
        }

        fuel_value = fuel_map.get(
            fuel,
            fuel
        )

        filter_values.append(
            f"petrol_eq_{fuel_value}"
        )

    # =====================================================
    # TRANSMISSION
    # =====================================================

    transmission = clean_value(
        filters.get("transmission")
    )

    if transmission:

        transmission_map = {
            "manual": "manual",
            "automatic": "automatic",
            "auto": "automatic",
            "amt": "amt",
            "cvt": "cvt",
        }

        transmission_value = (
            transmission_map.get(
                transmission,
                transmission
            )
        )

        filter_values.append(
            f"transmission_eq_{transmission_value}"
        )

    # =====================================================
    # PRICE
    # =====================================================

    min_price = to_int(
        filters.get("min_price")
    )

    max_price = to_int(
        filters.get("max_price")
    )

    if (
        min_price is not None
        and max_price is not None
    ):
        filter_values.append(
            f"price_between_{min_price}_to_{max_price}"
        )

    elif min_price is not None:
        filter_values.append(
            f"price_min_{min_price}"
        )

    elif max_price is not None:
        filter_values.append(
            f"price_max_{max_price}"
        )

    # =====================================================
    # YEAR
    # =====================================================

    min_year = to_int(
        filters.get("min_year")
    )

    max_year = to_int(
        filters.get("max_year")
    )

    if (
        min_year is not None
        and max_year is not None
    ):
        filter_values.append(
            f"year_between_{min_year}_to_{max_year}"
        )

    elif min_year is not None:
        filter_values.append(
            f"year_min_{min_year}"
        )

    elif max_year is not None:
        filter_values.append(
            f"year_max_{max_year}"
        )

    # =====================================================
    # MILEAGE
    # =====================================================

    min_km = to_int(
        filters.get("min_km")
    )

    max_km = to_int(
        filters.get("max_km")
    )

    if (
        min_km is not None
        and max_km is not None
    ):
        filter_values.append(
            f"mileage_between_{min_km}_to_{max_km}"
        )

    elif min_km is not None:
        filter_values.append(
            f"mileage_min_{min_km}"
        )

    elif max_km is not None:
        filter_values.append(
            f"mileage_max_{max_km}"
        )

    # =====================================================
    # BUILD FINAL URL
    #
    # sorting=desc-creation (newest first) is always
    # included — it is the whole point of a new-listing
    # alerter, with or without filters.
    # =====================================================

    if not filter_values:

        return (
            f"{base_url}"
            "?sorting=desc-creation"
        )

    filter_string = ",".join(
        filter_values
    )

    encoded_filters = quote(
        filter_string,
        safe=","
    )

    return (
        f"{base_url}"
        f"?filter={encoded_filters}"
        "&sorting=desc-creation"
    )