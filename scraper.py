import time
import random
import re
from html import unescape

from playwright.sync_api import sync_playwright

from config import OLX_URL, MAX_LISTINGS_TO_CHECK


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = unescape(value)
    text = text.replace("\xa0", " ")
    text = re.sub(r"<.*?>", " ", text, flags=re.S)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_html_fragment(value: str | None) -> str:
    if not value:
        return ""
    return clean_text(value)


def extract_ad_id(url: str) -> str | None:
    """
    Extract OLX listing ID from a URL.
    """
    match = re.search(r"iid-(\d+)", url)
    return match.group(1) if match else None


def parse_year_km(subtitle: str | None) -> tuple[str | None, str | None]:
    if not subtitle:
        return None, None

    cleaned = strip_html_fragment(subtitle)
    match = re.search(r"(\d{4})\s*[-–]\s*([0-9,]+)\s*km", cleaned, flags=re.I)
    if match:
        year = match.group(1)
        km = match.group(2).replace(",", "")
        return year, km

    return None, None


def extract_span_texts(html: str) -> list[str]:
    spans = re.findall(r"<span[^>]*>(.*?)</span>", html, flags=re.S | re.I)
    return [strip_html_fragment(text) for text in spans if strip_html_fragment(text)]


def parse_listing_card(card_html: str, url: str) -> dict:
    price = strip_html_fragment(
        re.search(r'<span[^>]*data-aut-id=["\']itemPrice["\'][^>]*>(.*?)</span>', card_html, flags=re.S | re.I)
        .group(1)
        if re.search(r'<span[^>]*data-aut-id=["\']itemPrice["\'][^>]*>(.*?)</span>', card_html, flags=re.S | re.I)
        else None
    )

    title_match = re.search(r'<h3[^>]*data-aut-id=["\']itemTitle["\'][^>]*>(.*?)</h3>', card_html, flags=re.S | re.I)
    title = strip_html_fragment(title_match.group(1)) if title_match else "No title"

    subtitle_match = re.search(r'<div[^>]*data-aut-id=["\']itemSubTitle["\'][^>]*>(.*?)</div>', card_html, flags=re.S | re.I)
    subtitle = strip_html_fragment(subtitle_match.group(1)) if subtitle_match else ""
    year, km = parse_year_km(subtitle)

    details_match = re.search(r'<div[^>]*data-aut-id=["\']itemDetails["\'][^>]*>(.*?)</div>', card_html, flags=re.S | re.I)
    details_html = details_match.group(1) if details_match else ""
    details_text = strip_html_fragment(details_html)
    span_values = extract_span_texts(details_html)

    location = "Kerala"
    posted = "Recently"

    if span_values:
        for value in span_values:
            if value and not re.fullmatch(r"(?:Today|Yesterday|\d{1,2}\s+[A-Za-z]{3,})", value, flags=re.I):
                location = value
                break
        for value in span_values:
            if re.fullmatch(r"(?:Today|Yesterday|\d{1,2}\s+[A-Za-z]{3,})", value, flags=re.I):
                posted = value
                break

    if not location or location == "Kerala":
        location_match = re.search(r"<span[^>]*>(.*?)</span>", details_html, flags=re.S | re.I)
        if location_match:
            location = strip_html_fragment(location_match.group(1))

    ad_id = extract_ad_id(url)
    if not ad_id:
        ad_id = "unknown"

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

            page.wait_for_timeout(5000)

            html = page.content()

            with open("olx_debug.html", "w", encoding="utf-8") as f:
                f.write(html)

            print("💾 Saved page HTML to: olx_debug.html")

            links = page.locator("a[href*='iid-']").all()

            print(f"🔗 Found {len(links)} OLX listing links on page")

            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue

                    full_url = href if href.startswith("http") else f"https://www.olx.in{href}"
                    ad_id = extract_ad_id(full_url)
                    if not ad_id:
                        continue

                    card_html = link.evaluate("el => el.outerHTML")
                    car = parse_listing_card(card_html, full_url)
                    if car["title"] and car["title"] != "No title":
                        cars.append(car)

                    if len(cars) >= MAX_LISTINGS_TO_CHECK:
                        break

                except Exception as e:
                    print(f"⚠️ Error reading listing: {e}")

            print(f"📦 Found {len(cars)} real OLX listings")

        except Exception as e:
            print(f"❌ Scraping error: {e}")

        finally:
            browser.close()

    return cars
