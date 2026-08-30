import time

from apscheduler.schedulers.blocking import BlockingScheduler

from config import CHECK_INTERVAL_MINUTES, load_filters
from notifier import format_car_message, send_telegram_message
from scraper import scrape_recent_cars
from storage import is_new_ad, load_seen_ads, mark_as_seen, save_seen_ads
from olx_url import build_olx_url


def check_new_cars():
    print("\n" + "=" * 50)
    print("🔍 Checking for new cars in Kerala...")

    # Load filters configured from web UI
    filters = load_filters()
    print(f"Filter settings: {filters}")

    # Build OLX URL using the current filters
    olx_url = build_olx_url(filters)
    print(f"🔗 OLX URL: {olx_url}")

    # Load already-seen listings
    seen = load_seen_ads()

    # Scrape OLX using the filtered URL
    cars = scrape_recent_cars(olx_url)

    new_count = 0

    for car in cars:
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
        minutes=CHECK_INTERVAL_MINUTES
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Stopped by user")