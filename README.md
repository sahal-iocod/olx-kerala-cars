# OLX Kerala Car Notifier (Telegram)

Monitors newly listed cars on OLX.in in **Kerala** and sends Telegram notifications.

## Features

- Checks Kerala car listings sorted by newest first
- Sends Telegram alert only for **new** ads (no duplicates)
- Reads listings from OLX's internal JSON API (captured via Playwright), with HTML parsing as a fallback
- Runs headless by default, so it can run on a server (`HEADLESS=false` to watch the browser)
- Caches resolved location slugs in `location_cache.json` (each city is resolved via browser only once)
- Local filter safety net (`filters.py`) re-checks every listing against your filters before notifying
- `seen_ads.json` is pruned automatically (default: entries older than 60 days)
- Runs automatically every 5 minutes (configurable via `CHECK_INTERVAL_MINUTES`)

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

By default the browser runs headless (invisible). If OLX starts blocking checks, set `HEADLESS=false` in `.env` to run with a visible window.

Press `Ctrl + C` to stop.

Debug files written on each check:

- `olx_api_debug.json` — the raw listings captured from OLX's JSON API (the preferred data source)
- `olx_debug.html` — the rendered page HTML (used by the fallback parser)

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
dd
