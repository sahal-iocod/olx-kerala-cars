# notifier.py
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_telegram_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials missing in .env")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False


def format_seller_line(car: dict) -> str:
    seller = car.get("seller")
    if not seller:
        return ""

    label = "Dealer" if seller == "dealer" else "Individual owner"

    if car.get("verified"):
        label += " ✅ verified"

    return f"👤 Seller: {label}\n"


def format_car_message(car: dict) -> str:
    return (
        f"🚗 <b>New Car in Kerala</b>\n\n"
        f"<b>{car['title']}</b>\n"
        f"💰 Price: {car['price']}\n"
        f"📅 Year: {car.get('year', 'N/A')}\n"
        f"🛣️ KM: {car.get('km', 'N/A')}\n"
        f"📍 Location: {car.get('location', 'Kerala')}\n"
        f"{format_seller_line(car)}"
        f"🕒 Posted: {car.get('posted', 'Recently')}\n\n"
        f"🔗 <a href=\"{car['url']}\">View on OLX</a>"
    )
