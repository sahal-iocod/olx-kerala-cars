import re

import pytest

from scraper import parse_listing_card, parse_year_km


def test_parse_year_km_from_olx_subtitle():
    year, km = parse_year_km("2023 - 70,000 km")

    assert year == "2023"
    assert km == "70000"


def test_parse_listing_card_from_real_olx_structure():
    html = """
    <a href="/item/cars-c84-used-toyota-vellfire-in-ernakulam-hpo-kochi-iid-1852799001">
        <span data-aut-id="itemPrice">₹ 99,99,999</span>
        <div data-aut-id="itemSubTitle">2023 - 70,000 km</div>
        <h3 data-aut-id="itemTitle">Toyota VELLFIRE</h3>
        <div data-aut-id="itemDetails"><span>Ernakulam HPO</span><span>17 Aug</span></div>
    </a>
    """

    car = parse_listing_card(html, "https://www.olx.in/item/cars-c84-used-toyota-vellfire-in-ernakulam-hpo-kochi-iid-1852799001")

    assert car["id"] == "1852799001"
    assert car["title"] == "Toyota VELLFIRE"
    assert car["price"] == "₹ 99,99,999"
    assert car["year"] == "2023"
    assert car["km"] == "70000"
    assert car["location"] == "Ernakulam HPO"
    assert car["url"] == "https://www.olx.in/item/cars-c84-used-toyota-vellfire-in-ernakulam-hpo-kochi-iid-1852799001"
