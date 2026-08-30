# OLX Kerala Car Notifier (Telegram)

Monitors newly listed cars on OLX.in in **Kerala** and sends Telegram notifications.

## Features

- Checks Kerala car listings sorted by newest first
- Sends Telegram alert only for **new** ads (no duplicates)
- Uses Playwright in non-headless mode (helps avoid OLX blocks)
- Runs automatically every 12 minutes

## Setup

### 1. Create Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Copy the **Bot Token**
4. Get your Chat ID:
   - Message **@userinfobot** → it will reply with your ID
   - Or message your own bot and visit:  
     `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and paste your values:

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=987654321
```

### 3. Install

```bash
python -m venv venv

# Linux / Mac
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

### 4. Run

```bash
python main.py
```

A Chromium window will open each time it checks. This is normal and helps avoid getting blocked by OLX.

Press `Ctrl + C` to stop.

## Notes

- Keep the frequency at 10–15 minutes for personal use.
- The first run will notify about current recent listings. After that only brand-new ones are sent.
- If OLX changes its page structure, the selectors in `scraper.py` may need updating.
- This is for personal use only. Respect OLX Terms of Service and do not scrape aggressively.

## Optional later improvements

- Add max price / min year / max km filters
- Extract more accurate Year & KM from detail pages
- Run on a VPS / cloud for 24/7 operation
- Add WhatsApp support
