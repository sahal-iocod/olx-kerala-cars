import json
import random
import re
import time
from html import unescape

from playwright.sync_api import sync_playwright

from config import BROWSER_STATE_FILE, HEADLESS, MAX_LISTINGS_TO_CHECK
from olx_api import build_api_query

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def launch_browser(p):
    """
    Launch the real installed Chrome when available.

    OLX blocks Playwright's bundled headless build at the
    connection level (HTTP2 errors); real Chrome with a
    normal user agent passes even in headless mode.
    """
    try:
        return p.chromium.launch(
            headless=HEADLESS,
            channel="chrome",
        )
    except Exception:
        return p.chromium.launch(
            headless=HEADLESS,
        )


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    text = unescape(value)
    text = text.replace("\xa0", " ")

    # Remove HTML tags
    text = re.sub(r"<.*?>", " ", text, flags=re.S)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def strip_html_fragment(value: str | None) -> str:
    if not value:
        return ""

    return clean_text(value)


def extract_ad_id(url: str) -> str | None:
    """
    Extract OLX listing ID from a URL.
    Example:
    https://www.olx.in/item/...-iid-123456789
    """

    match = re.search(r"iid-(\d+)", url)

    return match.group(1) if match else None


def parse_year_km(
    subtitle: str | None,
) -> tuple[str | None, str | None]:

    if not subtitle:
        return None, None

    cleaned = strip_html_fragment(subtitle)

    match = re.search(
        r"(\d{4})\s*[-–]\s*([0-9,]+)\s*km",
        cleaned,
        flags=re.I,
    )

    if match:
        year = match.group(1)
        km = match.group(2).replace(",", "")

        return year, km

    return None, None


def extract_span_texts(html: str) -> list[str]:
    """
    Extract text from span elements.
    """

    spans = re.findall(
        r"<span[^>]*>(.*?)</span>",
        html,
        flags=re.S | re.I,
    )

    results = []

    for text in spans:
        cleaned = strip_html_fragment(text)

        if cleaned:
            results.append(cleaned)

    return results


def parse_listing_card(
    card_html: str,
    url: str,
) -> dict:

    # -------------------------
    # Price
    # -------------------------

    price_match = re.search(
        r'<span[^>]*data-aut-id=["\']itemPrice["\'][^>]*>(.*?)</span>',
        card_html,
        flags=re.S | re.I,
    )

    price = (
        strip_html_fragment(price_match.group(1))
        if price_match
        else None
    )

    # -------------------------
    # Title
    # -------------------------

    title_match = re.search(
        r'<h3[^>]*data-aut-id=["\']itemTitle["\'][^>]*>(.*?)</h3>',
        card_html,
        flags=re.S | re.I,
    )

    title = (
        strip_html_fragment(title_match.group(1))
        if title_match
        else "No title"
    )

    # -------------------------
    # Subtitle
    # -------------------------

    subtitle_match = re.search(
        r'<div[^>]*data-aut-id=["\']itemSubTitle["\'][^>]*>(.*?)</div>',
        card_html,
        flags=re.S | re.I,
    )

    subtitle = (
        strip_html_fragment(subtitle_match.group(1))
        if subtitle_match
        else ""
    )

    year, km = parse_year_km(subtitle)

    # -------------------------
    # Details
    # -------------------------

    details_match = re.search(
        r'<div[^>]*data-aut-id=["\']itemDetails["\'][^>]*>(.*?)</div>',
        card_html,
        flags=re.S | re.I,
    )

    details_html = (
        details_match.group(1)
        if details_match
        else ""
    )

    span_values = extract_span_texts(details_html)

    # -------------------------
    # Location / Posted
    # -------------------------

    location = "Kerala"
    posted = "Recently"

    if span_values:

        for value in span_values:

            if value and not re.fullmatch(
                r"(?:Today|Yesterday|\d{1,2}\s+[A-Za-z]{3,})",
                value,
                flags=re.I,
            ):
                location = value
                break

        for value in span_values:

            if re.fullmatch(
                r"(?:Today|Yesterday|\d{1,2}\s+[A-Za-z]{3,})",
                value,
                flags=re.I,
            ):
                posted = value
                break

    # -------------------------
    # Fallback location
    # -------------------------

    if not location or location == "Kerala":

        location_match = re.search(
            r"<span[^>]*>(.*?)</span>",
            details_html,
            flags=re.S | re.I,
        )

        if location_match:
            location = strip_html_fragment(
                location_match.group(1)
            )

    # -------------------------
    # Ad ID
    # -------------------------

    ad_id = extract_ad_id(url)

    if not ad_id:
        ad_id = "unknown"

    # -------------------------
    # Return listing
    # -------------------------

    return {
        "id": ad_id,
        "title": title,
        "price": price or "Price not found",
        "year": year or "N/A",
        "km": km or "N/A",
        "location": location or "Kerala",
        "posted": posted or "Recently",
        "url": url,
    }


def parse_api_listing(item: dict) -> dict | None:
    """
    Parse one listing from OLX's internal search API
    (api/relevance/.../search). This is structured JSON,
    so no regex over HTML is involved.

    Field names are read defensively — if OLX renames
    them, we return None and the HTML fallback kicks in.
    """

    if not isinstance(item, dict):
        return None

    ad_id = item.get("ad_id") or item.get("id")

    if ad_id is None:
        return None

    ad_id = str(ad_id)

    title = clean_text(str(item.get("title") or ""))

    if not title:
        return None

    # ---- price ----
    price = None
    price_obj = item.get("price")
    if isinstance(price_obj, dict):
        value = price_obj.get("value")
        if isinstance(value, dict):
            price = value.get("display")
            if not price and value.get("raw") is not None:
                price = f"₹ {value['raw']}"

    # ---- structured attributes from parameters ----
    year = None
    km = None
    fuel = None
    transmission = None
    brand = None
    model = None

    for param in item.get("parameters") or []:
        if not isinstance(param, dict):
            continue
        key = param.get("key")
        value = param.get("value_name") or param.get("value")
        if value is None:
            continue
        if key == "year":
            year = str(value)
        elif key in ("mileage", "kms_driven", "mileage_v2"):
            km = str(value).replace(",", "").replace(" km", "")
        elif key in ("petrol", "fuel", "fueltype"):
            # OLX calls the fuel-type parameter "petrol"
            fuel = str(value)
        elif key == "transmission":
            transmission = str(value)
        elif key == "make":
            brand = str(value)
        elif key == "model":
            model = str(value)

    if year is None or km is None:
        info_year, info_km = parse_year_km(str(item.get("main_info") or ""))
        year = year or info_year
        km = km or info_km

    # ---- location ----
    location = None
    locations_resolved = item.get("locations_resolved")
    if isinstance(locations_resolved, dict):
        for key in (
            "SUBLOCALITY_LEVEL_1_name",
            "ADMIN_LEVEL_3_name",
            "ADMIN_LEVEL_1_name",
        ):
            if locations_resolved.get(key):
                location = locations_resolved[key]
                break

    # ---- seller info ----
    is_dealer = bool(
        item.get("is_business")
    ) or bool(
        item.get("dealer_showroom_enabled")
    )

    seller = "dealer" if is_dealer else "owner"
    verified = bool(item.get("is_kyc_verified_user"))

    # ---- posted date ----
    posted = (
        item.get("display_date")
        or item.get("created_at_first")
        or item.get("created_at")
        or "Recently"
    )

    return {
        "id": ad_id,
        "title": title,
        "price": price or "Price not found",
        "year": year or "N/A",
        "km": km or "N/A",
        "fuel": fuel,
        "transmission": transmission,
        "brand": brand,
        "model": model,
        "seller": seller,
        "verified": verified,
        "location": location or "Kerala",
        "posted": str(posted),
        "url": f"https://www.olx.in/item/iid-{ad_id}",
    }


def fetch_api_listings(page, filters, location_slug):
    """
    Call OLX's internal search API from inside the already
    loaded page. Returns the raw listing dicts ([] when the
    API worked but nothing matches the filters), or None on
    failure (the HTML fallback then takes over).
    """

    try:
        query = build_api_query(
            filters or {},
            location_slug or "",
        )

        print(f"📡 Calling OLX search API: {query}")

        result = page.evaluate(
            """async (qs) => {
                const res = await fetch(
                    '/api/relevance/v4/search?' + qs,
                    { headers: { Accept: 'application/json' } }
                );
                if (!res.ok) return null;
                return await res.json();
            }""",
            query,
        )

        if not isinstance(result, dict):
            return None

        data = result.get("data")

        if isinstance(data, list):
            # May legitimately be [] — the API worked and
            # nothing matches the filters right now.
            return data

        return None

    except Exception as e:
        print(f"⚠️ OLX API call failed: {e}")
        return None


def scrape_recent_cars(
    url: str,
    filters: dict | None = None,
    location_slug: str | None = None,
) -> list[dict]:
    """
    Scrape recent cars from the supplied OLX URL.

    Preferred source: OLX's internal JSON API, called from
    inside the loaded page (structured data, no regex).
    Fallback: parsing the listing cards out of the HTML.
    """

    cars = []

    # Listings captured passively from OLX's internal JSON
    # API while the page loads (e.g. on pagination).
    api_items = []

    with sync_playwright() as p:

        browser = launch_browser(p)

        # Reuse cookies/session between runs so OLX sees a
        # consistent returning visitor instead of a fresh
        # unknown browser every few minutes.
        context_kwargs = {
            "viewport": {
                "width": 1280,
                "height": 800,
            },
            "user_agent": USER_AGENT,
            "locale": "en-IN",
        }

        if BROWSER_STATE_FILE.exists():
            context_kwargs["storage_state"] = str(BROWSER_STATE_FILE)

        context = browser.new_context(**context_kwargs)

        page = context.new_page()

        def capture_api_response(response):
            try:
                if (
                    "api/relevance" in response.url
                    and "search" in response.url
                ):
                    body = response.json()
                    data = body.get("data")
                    if isinstance(data, list) and data:
                        api_items.extend(data)
                        print(
                            f"📡 Captured {len(data)} listings "
                            f"from OLX API"
                        )
            except Exception:
                pass

        page.on("response", capture_api_response)

        try:

            # -------------------------
            # Open filtered OLX URL
            # -------------------------

            print("🌐 Opening OLX filtered cars page...")
            print(f"🔗 URL: {url}")

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            # Give OLX some time to load listings
            time.sleep(
                random.uniform(4, 7)
            )

            print(
                f"🔗 Current URL: {page.url}"
            )

            print(
                f"📄 Page title: {page.title()}"
            )

            # Additional wait for dynamic content
            page.wait_for_timeout(5000)

            # -------------------------
            # Save debug HTML
            # -------------------------

            html = page.content()

            with open(
                "olx_debug.html",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(html)

            print(
                "💾 Saved page HTML to: olx_debug.html"
            )

            # -------------------------
            # Find listing links
            # (also used to give API listings
            # their real URLs)
            # -------------------------

            links = page.locator(
                "a[href*='iid-']"
            ).all()

            print(
                f"🔗 Found {len(links)} OLX listing links on page"
            )

            # Map ad id -> real listing URL from the DOM
            url_by_id = {}

            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    full = (
                        href
                        if href.startswith("http")
                        else f"https://www.olx.in{href}"
                    )
                    link_id = extract_ad_id(full)
                    if link_id and link_id not in url_by_id:
                        url_by_id[link_id] = full
                except Exception:
                    continue

            # -------------------------
            # Preferred path: call the
            # JSON API from inside the
            # page (structured data)
            # -------------------------

            # The explicit call carries our filters, so it
            # always takes priority. Passively captured
            # responses (requests the page made on its own,
            # not necessarily filtered) are only a backup.
            if filters is not None:
                explicit_items = fetch_api_listings(
                    page,
                    filters,
                    location_slug,
                )

                # None = the call failed (fall through to
                # passive items / HTML). [] = the API worked
                # and nothing matches the filters — that IS
                # the answer; parsing the page instead would
                # return unfiltered listings.
                if explicit_items is not None:
                    if not explicit_items:
                        print(
                            "📭 OLX API: no listings match "
                            "the current filters"
                        )
                        return []

                    api_items = explicit_items

            if api_items:

                with open(
                    "olx_api_debug.json",
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(
                        api_items,
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

                print(
                    "💾 Saved API listings to: olx_api_debug.json"
                )

                seen_ids = set()

                for item in api_items:

                    car = parse_api_listing(item)

                    if not car:
                        continue

                    if car["id"] in seen_ids:
                        continue

                    seen_ids.add(car["id"])

                    # Use the real URL from the DOM
                    # when we have it
                    if car["id"] in url_by_id:
                        car["url"] = url_by_id[car["id"]]

                    cars.append(car)

                parsed_count = len(cars)

                # Apply the local filters BEFORE capping, so
                # filters the API can't handle server-side
                # (model, transmission) don't starve the
                # results — e.g. 19 Swifts hiding past a cap
                # of 25 raw listings.
                if filters is not None:
                    from filters import matches_filters

                    cars = [
                        car
                        for car in cars
                        if matches_filters(car, filters)
                    ]

                cars = cars[:MAX_LISTINGS_TO_CHECK]

                print(
                    f"📦 OLX API: {parsed_count} parsed, "
                    f"{len(cars)} match the filters"
                )

                return cars

            # -------------------------
            # Fallback: parse listing
            # cards out of the HTML
            # -------------------------

            print(
                "⚠️ No API response captured — "
                "falling back to HTML parsing"
            )

            seen_ids = set()

            for link in links:

                try:

                    href = link.get_attribute(
                        "href"
                    )

                    if not href:
                        continue

                    # Convert relative URL to absolute URL
                    full_url = (
                        href
                        if href.startswith("http")
                        else f"https://www.olx.in{href}"
                    )

                    # Extract listing ID
                    ad_id = extract_ad_id(
                        full_url
                    )

                    if not ad_id:
                        continue

                    # Avoid duplicate listing cards
                    if ad_id in seen_ids:
                        continue

                    seen_ids.add(ad_id)

                    # Get HTML for listing element
                    card_html = link.evaluate(
                        "el => el.outerHTML"
                    )

                    # Parse listing
                    car = parse_listing_card(
                        card_html,
                        full_url,
                    )

                    if (
                        car["title"]
                        and car["title"] != "No title"
                    ):
                        cars.append(car)

                    # Stop after required number
                    if (
                        len(cars)
                        >= MAX_LISTINGS_TO_CHECK
                    ):
                        break

                except Exception as e:

                    print(
                        f"⚠️ Error reading listing: {e}"
                    )

            print(
                f"📦 Found {len(cars)} real OLX listings"
            )

        except Exception as e:

            print(
                f"❌ Scraping error: {e}"
            )

            # Let the caller see the failure so it can
            # back off instead of retrying full-speed.
            raise

        finally:

            try:
                context.storage_state(
                    path=str(BROWSER_STATE_FILE)
                )
            except Exception:
                pass

            browser.close()

    return cars