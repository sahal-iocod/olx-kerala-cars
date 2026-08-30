# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# OLX Kerala Cars - newest first
OLX_URL = "https://www.olx.in/kerala_g2001160/cars_c84?sorting=desc-creation"

# How often to check (minutes)
CHECK_INTERVAL_MINUTES = 12

# How many newest listings to check each time
MAX_LISTINGS_TO_CHECK = 25

# File to store already seen ad IDs
SEEN_ADS_FILE = "seen_ads.json"
