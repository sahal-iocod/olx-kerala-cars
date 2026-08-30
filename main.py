# main.py
import time
from apscheduler.schedulers.blocking import BlockingScheduler

from config import CHECK_INTERVAL_MINUTES, load_filters
from filters import matches_filters
from notifier import format_car_message, send_telegram_message
from scraper import scrape_recent_cars
from storage import is_new_ad, load_seen_ads, mark_as_seen, save_seen_ads


def check_new_cars():
    print("\n" + "=" * 50)
    print("🔍 Checking for new cars in Kerala...")

    filters = load_filters()
    print(f"Filter settings: {filters}")

    seen = load_seen_ads()
    cars = scrape_recent_cars()

    new_count = 0
    for car in cars:
        if not matches_filters(car, filters):
            print(f"⏭️ Filtered out: {car['title'][:50]}...")
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

    check_new_cars()

    scheduler = BlockingScheduler()
    scheduler.add_job(check_new_cars, "interval", minutes=CHECK_INTERVAL_MINUTES)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Stopped by user")
