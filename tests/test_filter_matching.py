from filters import matches_filters


def test_matches_filters_for_price_year_km_and_location():
    car = {
        "title": "Hyundai Venue SX (O) MT 1.5 Diesel",
        "price": "₹ 9,50,000",
        "year": "2022",
        "km": "59323",
        "location": "Kundayithode",
    }

    filters = {
        "location": "kochi",
        "min_price": "800000",
        "max_price": "1200000",
        "min_year": "2021",
        "max_year": "2024",
        "min_km": "0",
        "max_km": "70000",
        "brand": "hyundai",
        "fuel": "diesel",
        "transmission": "manual",
        "keyword": "venue",
    }

    assert matches_filters(car, filters) is False

    filters["location"] = "kundayithode"
    filters["max_km"] = "70000"
    assert matches_filters(car, filters) is True


def test_matches_filters_when_location_blank_uses_all():
    car = {
        "title": "Maruti Suzuki Swift",
        "price": "₹ 6,25,000",
        "year": "2020",
        "km": "45000",
        "location": "Thiruvananthapuram",
        "fuel": "Diesel",
        "transmission": "Manual",
    }

    filters = {
        "location": "",
        "min_price": "500000",
        "max_price": "800000",
        "min_year": "2019",
        "max_year": "2023",
        "min_km": "0",
        "max_km": "60000",
        "brand": "maruti",
        "fuel": "petrol",
        "transmission": "automatic",
        "keyword": "swift",
    }

    # Structured fields say Diesel/Manual, filter wants petrol/automatic
    assert matches_filters(car, filters) is False

    filters["fuel"] = ""
    filters["transmission"] = ""
    filters["keyword"] = "swift"
    filters["brand"] = "maruti"
    assert matches_filters(car, filters) is True


def test_fuel_filter_does_not_drop_car_without_fuel_info():
    # Title doesn't mention fuel and there is no structured
    # fuel field — the car must NOT be rejected.
    car = {
        "title": "Hyundai Creta 2015",
        "price": "₹ 7,00,000",
        "year": "2015",
        "km": "80000",
        "location": "Kochi",
    }
    filters = {"fuel": "diesel"}

    assert matches_filters(car, filters) is True


def test_fuel_filter_drops_car_with_conflicting_title():
    car = {
        "title": "Hyundai Creta Petrol 2015",
        "price": "₹ 7,00,000",
        "year": "2015",
        "km": "80000",
        "location": "Kochi",
    }
    filters = {"fuel": "diesel"}

    assert matches_filters(car, filters) is False


def test_structured_fuel_field_is_preferred_over_title():
    car = {
        "title": "Hyundai Creta 2015",
        "fuel": "Diesel",
        "price": "₹ 7,00,000",
    }

    assert matches_filters(car, {"fuel": "diesel"}) is True
    assert matches_filters(car, {"fuel": "petrol"}) is False
