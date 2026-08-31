import time

from scraper import parse_api_listing
from storage import prune_seen_ads


def test_parse_api_listing_full_item():
    item = {
        "id": "1852799001",
        "title": "Toyota VELLFIRE",
        "price": {"value": {"raw": 9999999, "display": "₹ 99,99,999"}},
        "main_info": "2023 - 70,000 km",
        "display_date": "Today",
        "locations_resolved": {
            "SUBLOCALITY_LEVEL_1_name": "Ernakulam HPO",
            "ADMIN_LEVEL_3_name": "Kochi",
            "ADMIN_LEVEL_1_name": "Kerala",
        },
        "parameters": [
            {"key": "make", "value_name": "Toyota"},
            {"key": "model", "value_name": "Vellfire"},
            {"key": "year", "value_name": "2023"},
            {"key": "mileage", "value_name": "70,000 km"},
            {"key": "petrol", "value_name": "Diesel"},
            {"key": "transmission", "value_name": "Automatic"},
        ],
    }

    car = parse_api_listing(item)

    assert car["id"] == "1852799001"
    assert car["title"] == "Toyota VELLFIRE"
    assert car["price"] == "₹ 99,99,999"
    assert car["year"] == "2023"
    assert car["km"] == "70000"
    assert car["fuel"] == "Diesel"
    assert car["transmission"] == "Automatic"
    assert car["brand"] == "Toyota"
    assert car["location"] == "Ernakulam HPO"
    assert car["posted"] == "Today"


def test_parse_api_listing_minimal_item_uses_fallbacks():
    car = parse_api_listing(
        {
            "id": 42,
            "title": "Maruti Swift",
            "main_info": "2019 - 45,000 km",
        }
    )

    assert car["id"] == "42"
    assert car["year"] == "2019"
    assert car["km"] == "45000"
    assert car["price"] == "Price not found"
    assert car["location"] == "Kerala"
    assert car["url"] == "https://www.olx.in/item/iid-42"


def test_parse_api_listing_rejects_garbage():
    assert parse_api_listing(None) is None
    assert parse_api_listing({}) is None
    assert parse_api_listing({"id": 1}) is None  # no title


def test_prune_seen_ads_drops_old_entries():
    now = time.time()
    seen = {
        "fresh": now - 86400,          # 1 day old
        "stale": now - 100 * 86400,    # 100 days old
    }

    pruned = prune_seen_ads(seen, max_age_days=60, now=now)

    assert "fresh" in pruned
    assert "stale" not in pruned


def test_location_ids_extracted_and_strictly_matched():
    from scraper import in_selected_location

    item = {
        "id": 7,
        "title": "Maruti Swift",
        "locations": [
            {"region_id": "2001160", "city_id": "4058877", "district_id": "99"}
        ],
        "locations_resolved": {"ADMIN_LEVEL_3_id": "123", "ADMIN_LEVEL_3_name": "Kozhikode"},
    }

    car = parse_api_listing(item)

    assert "4058877" in car["location_ids"]
    assert "2001160" in car["location_ids"]

    # In Kozhikode -> kept; a Malappuram car -> dropped
    assert in_selected_location(car, "4058877") is True
    malappuram = dict(car, location_ids=["2001160", "4058900"])
    assert in_selected_location(malappuram, "4058877") is False
    # Kerala-wide search keeps both
    assert in_selected_location(malappuram, "2001160") is True
    # No filter / no data -> pass
    assert in_selected_location(car, None) is True
    assert in_selected_location({"title": "x"}, "4058877") is True
