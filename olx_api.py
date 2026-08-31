"""
Query-string builder for OLX's internal search API
(/api/relevance/v4/search).

The API is called from inside a Playwright page (so the
request carries a real browser TLS fingerprint and cookies —
calling it with plain requests/curl gets blocked).

Verified working parameters (2026-08):

    category=84                cars
    location=<numeric id>      from the location slug, e.g. 2001160
    sorting=desc-creation      newest first
    make=<slug>                e.g. hyundai
    petrol=<fuel>              fuel type (OLX's name for it)
    price_min / price_max
    year_min / year_max
    mileage_min / mileage_max
    query=<keyword>            free-text search

`model` and `transmission` are NOT reliably filterable via
the API — they are enforced locally by filters.matches_filters
using the structured fields the API returns.
"""

import re
from urllib.parse import urlencode


def location_id_from_slug(slug: str) -> str | None:
    """
    "kerala_g2001160" -> "2001160"
    """
    if not slug:
        return None
    match = re.search(r"_g(\d+)$", slug.strip())
    return match.group(1) if match else None


def _to_int(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("₹", "").replace(" ", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def build_api_query(filters: dict, location_slug: str, size: int = 50) -> str:
    """
    Build the query string for /api/relevance/v4/search
    from the web-UI filters.
    """

    location_id = location_id_from_slug(location_slug) or "2001160"

    params = {
        "category": "84",
        "location": location_id,
        "platform": "web-desktop",
        "size": str(size),
        "sorting": "desc-creation",
    }

    def clean(key):
        value = filters.get(key)
        return str(value).strip().lower() if value else ""

    make = clean("brand")
    if make:
        params["make"] = make

    fuel = clean("fuel")
    if fuel:
        params["petrol"] = fuel

    keyword = clean("keyword")
    if keyword:
        params["query"] = keyword

    for filter_key, param_key in (
        ("min_price", "price_min"),
        ("max_price", "price_max"),
        ("min_year", "year_min"),
        ("max_year", "year_max"),
        ("min_km", "mileage_min"),
        ("max_km", "mileage_max"),
    ):
        value = _to_int(filters.get(filter_key))
        if value is not None:
            params[param_key] = str(value)

    return urlencode(params)
