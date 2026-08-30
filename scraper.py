import time
import random
import re
from playwright.sync_api import sync_playwright
from config import OLX_URL, MAX_LISTINGS_TO_CHECK


def extract_ad_id(url: str) -> str | None:
    """
    Extract OLX listing ID from a URL.
    """
    match = re.search(r"iid-(\d+)", url)
    return match.group(1) if match else None


def scrape_recent_cars() -> list[dict]:
    cars = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
        )

        page = context.new_page()

        try:
            print("🌐 Opening OLX Kerala cars page...")

            page.goto(
                OLX_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            time.sleep(random.uniform(4, 7))

            print(f"🔗 Current URL: {page.url}")
            print(f"📄 Page title: {page.title()}")

            # Give dynamically loaded content some time.
            page.wait_for_timeout(5000)

            # Debug information
            body_text = page.locator("body").inner_text()

            print("\n========== PAGE TEXT ==========")
            print(body_text[:3000])
            print("========== END PAGE TEXT ==========\n")

            # Save the HTML so we can inspect the current OLX structure.
            html = page.content()

            with open("olx_debug.html", "w", encoding="utf-8") as f:
                f.write(html)

            print("💾 Saved page HTML to: olx_debug.html")

            # Look for listing links.
            links = page.locator("a").all()

            print(f"🔗 Found {len(links)} links on page")

            for link in links:
                try:
                    href = link.get_attribute("href")

                    if not href:
                        continue

                    if "iid-" not in href:
                        continue

                    full_url = (
                        href
                        if href.startswith("http")
                        else f"https://www.olx.in{href}"
                    )

                    ad_id = extract_ad_id(full_url)

                    if not ad_id:
                        continue

                    title = link.inner_text().strip()

                    if not title:
                        title = "No title"

                    cars.append(
                        {
                            "id": ad_id,
                            "title": title,
                            "price": "Price not found",
                            "year": "N/A",
                            "km": "N/A",
                            "location": "Kerala",
                            "posted": "Recently",
                            "url": full_url,
                        }
                    )

                    if len(cars) >= MAX_LISTINGS_TO_CHECK:
                        break

                except Exception as e:
                    print(f"⚠️ Error reading listing: {e}")

            print(f"📦 Found {len(cars)} possible listings")

        except Exception as e:
            print(f"❌ Scraping error: {e}")

        finally:
            browser.close()

    return cars
