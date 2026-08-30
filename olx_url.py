from urllib.parse import quote

from config import OLX_BASE_URL
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


def build_olx_url(filters):
    location = filters.get("location", "")
    
    filter_values = []

    # =====================================================
    # BRAND
    # Example:
    # make_eq_hyundai
    # =====================================================

    brand = clean_value(filters.get("brand"))

    if brand:
        filter_values.append(
            f"make_eq_{brand}"
        )

    # =====================================================
    # MODEL
    # Example:
    # model_eq_hyundai-accent
    # =====================================================

    model = clean_value(filters.get("model"))

    if model:
        filter_values.append(
            f"model_eq_{model}"
        )

    # =====================================================
    # FUEL
    # Example:
    # petrol_eq_petrol
    # =====================================================

    fuel = clean_value(filters.get("fuel"))

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

        transmission_value = transmission_map.get(
            transmission,
            transmission
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
    # MILEAGE / KM
    #
    # Example from your OLX URL:
    # mileage_between_25000_to_49999
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
    # KEYWORD
    #
    # Keyword handling is intentionally left out for now.
    # OLX can represent keyword searches differently from
    # normal filter parameters.
    # =====================================================

    # =====================================================
    # BUILD URL
    # =====================================================

    if not filter_values:

        return (
            f"{OLX_BASE_URL}"
            "?sorting=desc-creation"
        )

    filter_string = ",".join(
        filter_values
    )

    return (
        f"{OLX_BASE_URL}"
        f"?filter={quote(filter_string, safe=',')}"
    )