from olx_url import build_olx_url


def test_url_without_filters_sorts_by_newest():
    url = build_olx_url({})
    assert url == (
        "https://www.olx.in/kerala_g2001160/cars_c84"
        "?sorting=desc-creation"
    )


def test_url_with_filters_still_sorts_by_newest():
    url = build_olx_url(
        {
            "brand": "hyundai",
            "min_price": "200000",
            "max_price": "600000",
        }
    )

    assert "filter=make_eq_hyundai" in url
    assert "price_between_200000_to_600000" in url
    assert "sorting=desc-creation" in url


def test_keyword_goes_into_url_path():
    url = build_olx_url({"keyword": "swift vdi"})
    assert "/cars_c84/q-swift%20vdi" in url
    assert "sorting=desc-creation" in url


def test_build_api_query_maps_filters_to_api_params():
    from olx_api import build_api_query, location_id_from_slug

    assert location_id_from_slug("kochi_g4058873") == "4058873"
    assert location_id_from_slug("kerala_g2001160") == "2001160"
    assert location_id_from_slug("") is None

    query = build_api_query(
        {
            "brand": "Hyundai",
            "fuel": "Diesel",
            "keyword": "creta",
            "min_price": "2,00,000",
            "max_price": "600000",
            "min_year": "2018",
            "max_km": "60000",
        },
        "kochi_g4058873",
    )

    assert "category=84" in query
    assert "location=4058873" in query
    assert "sorting=desc-creation" in query
    assert "make=hyundai" in query
    assert "petrol=diesel" in query
    assert "query=creta" in query
    assert "price_min=200000" in query
    assert "price_max=600000" in query
    assert "year_min=2018" in query
    assert "mileage_max=60000" in query


def test_build_api_query_empty_filters():
    from olx_api import build_api_query

    query = build_api_query({}, "kerala_g2001160")

    assert "location=2001160" in query
    assert "make" not in query
    assert "price_min" not in query


def test_model_slug_is_brand_prefixed_and_hyphenated():
    url = build_olx_url({"brand": "hyundai", "model": "creta"})
    assert "model_eq_hyundai-creta" in url

    url = build_olx_url({"brand": "maruti", "model": "grand vitara"})
    assert "model_eq_maruti-suzuki-grand-vitara" in url

    url = build_olx_url({"model": "hyundai-creta", "brand": "hyundai"})
    assert "model_eq_hyundai-creta" in url


def test_brand_is_normalized_to_olx_slug():
    from olx_api import build_api_query, normalize_brand

    assert normalize_brand("maruthi") == "maruti-suzuki"
    assert normalize_brand("Maruti Suzuki") == "maruti-suzuki"
    assert normalize_brand("hyundai") == "hyundai"
    assert normalize_brand("land rover") == "land-rover"

    query = build_api_query({"brand": "maruthi"}, "kochi_g4058873")
    assert "make=maruti-suzuki" in query

    url = build_olx_url({"brand": "maruthi"})
    assert "make_eq_maruti-suzuki" in url
