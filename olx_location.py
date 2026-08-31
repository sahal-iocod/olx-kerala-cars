import json
import re

from playwright.sync_api import sync_playwright

from config import LOCATION_CACHE_FILE


DEFAULT_LOCATION = "kerala_g2001160"


def load_location_cache() -> dict:
    if not LOCATION_CACHE_FILE.exists():
        return {}
    try:
        with LOCATION_CACHE_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def save_location_cache(cache: dict):
    with LOCATION_CACHE_FILE.open("w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2, ensure_ascii=False)


def extract_location_slug(url):
    """
    Extract OLX location slug.

    Example:

    https://www.olx.in/kochi_g4058873/cars_c84

    returns:

    kochi_g4058873
    """

    match = re.search(
        r"olx\.in/(?:en-in/)?([^/]+_g\d+)",
        url,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(1).lower()

    return None


def resolve_olx_location(location):
    """
    Dynamically resolve an OLX location.

    Examples:

        ""       -> kerala_g2001160
        "kochi"  -> kochi_g4058873
        "Kochi"  -> kochi_g4058873
    """

    location = str(location or "").strip()

    # =====================================================
    # Empty location = Kerala
    # =====================================================

    if not location:
        print("📍 No location specified")
        print("📍 Using Kerala")

        return DEFAULT_LOCATION

    # =====================================================
    # Cached location = no browser needed
    # =====================================================

    cache_key = location.lower()
    cache = load_location_cache()

    if cache_key in cache:
        print(
            f"📍 Location from cache: "
            f"{location} -> {cache[cache_key]}"
        )
        return cache[cache_key]

    print(
        f"📍 Resolving OLX location: {location}"
    )

    slug = _resolve_via_browser(location)

    cache[cache_key] = slug
    save_location_cache(cache)

    return slug


def _resolve_via_browser(location):

    from scraper import launch_browser

    with sync_playwright() as p:

        browser = launch_browser(p)

        context = browser.new_context(
            viewport={
                "width": 1280,
                "height": 800,
            }
        )

        page = context.new_page()

        try:

            # =================================================
            # Open OLX
            # =================================================

            url = (
                "https://www.olx.in/"
                "kerala_g2001160/cars_c84"
            )

            print(
                f"🌐 Opening OLX: {url}"
            )

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(5000)

            # =================================================
            # Find the location search input
            # =================================================

            print(
                "🔎 Looking for OLX location selector..."
            )

            location_input = page.locator(
                'input[placeholder="Search city, area or locality"]'
            )

            if location_input.count() > 0:

                print(
                    "✅ Location input already available"
                )

            else:

                print(
                    "ℹ️ Location input not visible yet"
                )

                # ---------------------------------------------
                # Find likely location selector
                # ---------------------------------------------

                candidates = page.locator(
                    "button, [role='button'], div"
                )

                clicked = False

                for i in range(
                    min(candidates.count(), 300)
                ):

                    try:

                        element = candidates.nth(i)

                        if not element.is_visible():
                            continue

                        text = (
                            element.inner_text(
                                timeout=500
                            )
                            or ""
                        ).strip()

                        if not text:
                            continue

                        # Keep this generic.
                        # We don't assume current city.
                        if (
                            len(text) < 80
                            and (
                                "," in text
                                or "location" in text.lower()
                            )
                        ):

                            box = element.bounding_box()

                            if not box:
                                continue

                            # Location selector is normally
                            # near the top-left of OLX.
                            if (
                                box["y"] < 220
                                and box["x"] < 450
                            ):

                                print(
                                    f"🔘 Trying location "
                                    f"selector: {text}"
                                )

                                element.click(
                                    timeout=2000
                                )

                                page.wait_for_timeout(
                                    1000
                                )

                                location_input = page.locator(
                                    'input[placeholder="Search city, area or locality"]'
                                )

                                if (
                                    location_input.count()
                                    > 0
                                ):

                                    clicked = True

                                    print(
                                        "✅ Location selector opened"
                                    )

                                    break

                    except Exception:
                        continue

                if not clicked:

                    raise RuntimeError(
                        "Could not open OLX location selector"
                    )

            # =================================================
            # Make sure input is visible
            # =================================================

            location_input = location_input.first

            location_input.wait_for(
                state="visible",
                timeout=5000,
            )

            print(
                "✅ Location search input found"
            )

            # =================================================
            # Enter location
            # =================================================

            print(
                f"⌨️ Searching location: {location}"
            )

            location_input.fill(location)

            page.wait_for_timeout(2000)

            # =================================================
            # Take screenshot for debugging
            # =================================================

            page.screenshot(
                path="olx_location_debug.png",
                full_page=False,
            )

            print(
                "📸 Saved: olx_location_debug.png"
            )

            # =================================================
            # Find location suggestion
            # =================================================

            print(
                "🔎 Looking for location suggestion..."
            )

            # First try exact location text.
            suggestion = page.get_by_text(
                re.compile(
                    rf"^{re.escape(location)}"
                    r"(?:,|\s|$)",
                    flags=re.IGNORECASE,
                )
            )

            if suggestion.count() == 0:

                # Try text containing location.
                suggestion = page.get_by_text(
                    re.compile(
                        re.escape(location),
                        flags=re.IGNORECASE,
                    )
                )

            if suggestion.count() == 0:

                raise RuntimeError(
                    f"OLX did not show a suggestion "
                    f"for '{location}'. "
                    f"Check olx_location_debug.png"
                )

            # =================================================
            # Click first useful suggestion
            # =================================================

            clicked_suggestion = False

            for i in range(
                suggestion.count()
            ):

                try:

                    item = suggestion.nth(i)

                    if not item.is_visible():
                        continue

                    text = (
                        item.inner_text(
                            timeout=1000
                        )
                        or ""
                    ).strip()

                    print(
                        f"📍 Suggestion: {text}"
                    )

                    item.click(
                        timeout=3000
                    )

                    clicked_suggestion = True

                    break

                except Exception:
                    continue

            if not clicked_suggestion:

                raise RuntimeError(
                    f"Could not click OLX location "
                    f"suggestion for '{location}'"
                )

            # =================================================
            # Wait for OLX to update
            # =================================================

            print(
                "⏳ Waiting for OLX to update location..."
            )

            page.wait_for_timeout(4000)

            current_url = page.url

            print(
                f"🔗 Current OLX URL: {current_url}"
            )

            # =================================================
            # Extract location
            # =================================================

            location_slug = extract_location_slug(
                current_url
            )

            if location_slug:

                print(
                    f"✅ Resolved location: "
                    f"{location_slug}"
                )

                return location_slug

            # =================================================
            # If URL didn't change to location path
            # =================================================

            print(
                "⚠️ OLX URL did not contain a "
                "location slug."
            )

            raise RuntimeError(
                "OLX location was selected, but "
                "the resulting URL did not contain "
                "a location ID."
            )

        finally:

            browser.close()