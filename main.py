import time

from apscheduler.schedulers.blocking import BlockingScheduler

from config import CHECK_INTERVAL_MINUTES, load_filters
from filters import matches_filters
from notifier import format_car_message, send_telegram_message
from scraper import scrape_recent_cars
from storage import is_new_ad, load_seen_ads, mark_as_seen, save_seen_ads
from olx_url import build_olx_url
from olx_location import resolve_olx_location


# Consecutive failed checks — used to back off politely
# instead of hammering OLX when it is refusing us.
_failure_count = 0


def check_new_cars():
    global _failure_count

    if _failure_count > 0:
        # Back off: skip cycles after failures
        # (1 failure = skip 1 cycle, 2 = skip 3, 3+ = skip 7).
        skip = min(2 ** _failure_count - 1, 7)
        if getattr(check_new_cars, "_skipped", 0) < skip:
            check_new_cars._skipped = getattr(check_new_cars, "_skipped", 0) + 1
            print(
                f"⏸️ Backing off after {_failure_count} failed "
                f"check(s) — skipping cycle "
                f"({check_new_cars._skipped}/{skip})"
            )
            return
        check_new_cars._skipped = 0

    print("\n" + "=" * 50)
    print("🔍 Checking for new cars in Kerala...")

    # Load filters configured from web UI
    filters = load_filters()
    print(f"Filter settings: {filters}")

    try:
        # Resolve the location once (cached in
        # location_cache.json after the first time)
        location_slug = resolve_olx_location(
            (filters.get("location") or "").strip().lower()
        )

        # Build OLX URL using the current filters
        olx_url = build_olx_url(filters, location_slug=location_slug)
        print(f"🔗 OLX URL: {olx_url}")

        # Scrape OLX — structured API data first,
        # HTML parsing as fallback
        cars = scrape_recent_cars(
            olx_url,
            filters=filters,
            location_slug=location_slug,
        )

    except Exception as e:
        _failure_count += 1
        print(
            f"❌ Check failed ({e}) — will back off "
            f"before the next attempt"
        )
        return

    _failure_count = 0

    # Load already-seen listings
    seen = load_seen_ads()

    new_count = 0

    for car in cars:
        # Local safety net on top of OLX's server-side
        # filters: drops mislabeled results OLX lets
        # through (wrong price band, fuel type, etc.)
        if not matches_filters(car, filters):
            print(f"🚫 Filtered out: {car['title'][:50]}")
            mark_as_seen(car["id"], seen)
            continue

        if is_new_ad(car["id"], seen):
            message = format_car_message(car)

            success = send_telegram_message(message)

            if success:
                print(f"✅ Notified: {car['title'][:50]}...")
                mark_as_seen(car["id"], seen)
                new_count += 1
                time.sleep(1.5)
            else:
                print("❌ Failed to send Telegram message")

        else:
            print(f"⏭️ Already seen: {car['id']}")

    save_seen_ads(seen)

    print(f"✨ Done. New cars notified: {new_count}")
    print("=" * 50)


if __name__ == "__main__":
    print("🚀 OLX Kerala Car Notifier started")
    print(f"⏱️ Checking every {CHECK_INTERVAL_MINUTES} minutes")

    # Run immediately
    check_new_cars()

    # Then run periodically
    scheduler = BlockingScheduler()

    scheduler.add_job(
        check_new_cars,
        "interval",
        minutes=CHECK_INTERVAL_MINUTES,
        # Random +/- up to 90s per run so checks don't fire
        # at robotic exact intervals.
        jitter=90,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Stopped by user")