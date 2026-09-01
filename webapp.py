import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request

from filters import matches_filters

load_dotenv()

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
FILTERS_FILE = BASE_DIR / "filters.json"
BOT_LOG_FILE = BASE_DIR / "bot.log"

# The notifier (main.py) run as a child process of the web app,
# so everything is controlled from one place.
_bot_process = None


def bot_running() -> bool:
    return _bot_process is not None and _bot_process.poll() is None


def start_bot() -> str:
    global _bot_process

    if bot_running():
        return "Bot is already running."

    log = BOT_LOG_FILE.open("a", encoding="utf-8")
    log.write("\n===== bot started from web UI =====\n")
    log.flush()

    # -u: unbuffered output so the log view updates live.
    # start_new_session: the bot gets its own process group so
    # stop_bot() can also kill any Chrome it has open mid-scrape.
    _bot_process = subprocess.Popen(
        [sys.executable, "-u", str(BASE_DIR / "main.py")],
        cwd=str(BASE_DIR),
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    return "Bot started."


def stop_bot() -> str:
    global _bot_process

    if not bot_running():
        _bot_process = None
        return "Bot is not running."

    # Signal the whole group (bot + any headless Chrome).
    def _signal_group(sig):
        try:
            os.killpg(os.getpgid(_bot_process.pid), sig)
        except (ProcessLookupError, PermissionError):
            _bot_process.send_signal(sig)

    _signal_group(signal.SIGTERM)
    try:
        _bot_process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        _signal_group(signal.SIGKILL)
        _bot_process.wait(timeout=5)

    _bot_process = None
    return "Bot stopped."


def bot_log_tail(lines: int = 25) -> str:
    if not BOT_LOG_FILE.exists():
        return ""
    try:
        content = BOT_LOG_FILE.read_text(encoding="utf-8", errors="replace")
        return "\n".join(content.splitlines()[-lines:])
    except Exception:
        return ""

DEFAULT_FILTERS = {
    "location": "",
    "min_price": "",
    "max_price": "",
    "min_year": "",
    "max_year": "",
    "min_km": "",
    "max_km": "",
    "brand": "",
    "model": "",
    "fuel": "",
    "transmission": "",
    "seller_type": "",
    "keyword": "",
}


def load_filters():
    if not FILTERS_FILE.exists():
        return DEFAULT_FILTERS.copy()
    try:
        with FILTERS_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            merged = DEFAULT_FILTERS.copy()
            merged.update(data)
            return merged
    except Exception:
        return DEFAULT_FILTERS.copy()


def save_filters(filters):
    with FILTERS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(filters, fh, indent=2)


HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>OLX Filter Manager</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f4f7fb; color: #1d2b36; margin: 0; padding: 32px; }
    .container { max-width: 900px; margin: 0 auto; background: white; border-radius: 14px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,.08); }
    h1 { margin-top: 0; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
    .field { display: flex; flex-direction: column; gap: 8px; }
    label { font-size: 13px; font-weight: 600; }
    input, select { padding: 10px 12px; border: 1px solid #dfe6ee; border-radius: 8px; font-size: 14px; }
    .actions { display: flex; gap: 12px; margin-top: 24px; flex-wrap: wrap; }
    button { border: none; background: #0a7cc3; color: white; padding: 12px 18px; border-radius: 8px; font-weight: 700; cursor: pointer; }
    button.secondary { background: #475569; }
    .status { margin-top: 16px; font-weight: 600; }
    .note { color: #4b5563; margin-top: 8px; }
    .bot-panel { border: 1px solid #dfe6ee; border-radius: 10px; padding: 16px; margin-bottom: 24px; background: #f8fafc; }
    .bot-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
    .dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
    .dot.on { background: #16a34a; box-shadow: 0 0 0 4px rgba(22,163,74,.15); }
    .dot.off { background: #9ca3af; }
    .bot-log { background: #0f172a; color: #cbd5e1; border-radius: 8px; padding: 12px; font-size: 12px; line-height: 1.5; max-height: 220px; overflow: auto; white-space: pre-wrap; margin: 12px 0 0; }
    .bot-log:empty { display: none; }
  </style>
</head>
<body>
  <div class="container">
    <h1>OLX Car Filter Manager</h1>

    <div class="bot-panel">
      <div class="bot-row">
        <span id="botDot" class="dot off"></span>
        <span id="botState">Checking…</span>
        <button type="button" id="startBtn">Start Bot</button>
        <button type="button" class="secondary" id="stopBtn">Stop Bot</button>
      </div>
      <pre id="botLog" class="bot-log"></pre>
    </div>
    <form id="filterForm">
      <div class="grid">
        <div class="field"><label>Location</label><input name="location" placeholder="e.g. kochi, thrissur, kollam" /></div>
        <div class="field"><label>Min Price</label><input name="min_price" type="number" min="0" /></div>
        <div class="field"><label>Max Price</label><input name="max_price" type="number" min="0" /></div>
        <div class="field"><label>Min Year</label><input name="min_year" type="number" min="1990" max="2035" /></div>
        <div class="field"><label>Max Year</label><input name="max_year" type="number" min="1990" max="2035" /></div>
        <div class="field"><label>Min KM</label><input name="min_km" type="number" min="0" /></div>
        <div class="field"><label>Max KM</label><input name="max_km" type="number" min="0" /></div>
        <div class="field"><label>Brand</label><input name="brand" placeholder="e.g. hyundai, maruti, toyota" /></div>
        <div class="field"><label>Model</label><input name="model" placeholder="e.g. creta, swift, venue" /></div>
        <div class="field"><label>Fuel</label><input name="fuel" placeholder="e.g. petrol, diesel, cng" /></div>
        <div class="field"><label>Transmission</label><input name="transmission" placeholder="e.g. automatic, manual" /></div>
        <div class="field"><label>Seller Type</label>
          <select name="seller_type">
            <option value="">Any seller</option>
            <option value="owner">Individual owner (no dealers)</option>
            <option value="verified">Verified seller</option>
            <option value="verified_owner">Verified individual owner</option>
            <option value="dealer">Dealer only</option>
          </select>
        </div>
        <div class="field"><label>Keyword</label><input name="keyword" placeholder="e.g. venue, city, swift" /></div>
      </div>
      <div class="actions">
        <button type="submit">Save Filters</button>
        <button type="button" class="secondary" id="resetBtn">Reset</button>
      </div>
      <div class="status" id="status"></div>
      <div class="note">These filters are stored in the project and used by the scraper run flow.</div>
    </form>
  </div>

  <script>
    const form = document.getElementById('filterForm');
    const statusBox = document.getElementById('status');

    const loadFilters = async () => {
      const response = await fetch('/api/filters');
      const data = await response.json();
      Object.entries(data).forEach(([key, value]) => {
        const field = form.elements.namedItem(key);
        if (field) field.value = value ?? '';
      });
    };

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const payload = Object.fromEntries(formData.entries());
      const response = await fetch('/api/filters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const result = await response.json();
      statusBox.textContent = result.message || 'Saved';
    });

    document.getElementById('resetBtn').addEventListener('click', async () => {
      const response = await fetch('/api/filters/reset', { method: 'POST' });
      const result = await response.json();
      statusBox.textContent = result.message || 'Reset';
      await loadFilters();
    });

    // ---- bot controls ----
    const botDot = document.getElementById('botDot');
    const botState = document.getElementById('botState');
    const botLog = document.getElementById('botLog');

    const refreshBot = async () => {
      try {
        const response = await fetch('/api/bot/status');
        const data = await response.json();
        botDot.className = 'dot ' + (data.running ? 'on' : 'off');
        botState.textContent = data.running ? 'Bot is running' : 'Bot is stopped';
        const atBottom = botLog.scrollTop + botLog.clientHeight >= botLog.scrollHeight - 10;
        botLog.textContent = data.log || '';
        if (atBottom) botLog.scrollTop = botLog.scrollHeight;
      } catch (e) {
        botState.textContent = 'Web app unreachable';
      }
    };

    document.getElementById('startBtn').addEventListener('click', async () => {
      const response = await fetch('/api/bot/start', { method: 'POST' });
      const result = await response.json();
      statusBox.textContent = result.message;
      await refreshBot();
    });

    document.getElementById('stopBtn').addEventListener('click', async () => {
      const response = await fetch('/api/bot/stop', { method: 'POST' });
      const result = await response.json();
      statusBox.textContent = result.message;
      await refreshBot();
    });

    refreshBot();
    setInterval(refreshBot, 4000);

    loadFilters();
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/api/filters")
def get_filters():
    return jsonify(load_filters())


@app.route("/api/filters", methods=["POST"])
def save_filters_route():
    payload = request.get_json(silent=True) or {}
    current = load_filters()
    current.update({k: str(v).strip() if v is not None else "" for k, v in payload.items()})
    save_filters(current)
    return jsonify({"message": "Filters saved successfully."})


@app.route("/api/filters/reset", methods=["POST"])
def reset_filters():
    save_filters(DEFAULT_FILTERS.copy())
    return jsonify({"message": "Filters reset to default."})


@app.route("/api/bot/start", methods=["POST"])
def bot_start_route():
    return jsonify({"message": start_bot(), "running": bot_running()})


@app.route("/api/bot/stop", methods=["POST"])
def bot_stop_route():
    return jsonify({"message": stop_bot(), "running": bot_running()})


@app.route("/api/bot/status")
def bot_status_route():
    return jsonify({"running": bot_running(), "log": bot_log_tail()})


@app.route("/api/test-match")
def test_match():
    sample = {
        "title": "Hyundai Venue SX (O) MT 1.5 Diesel",
        "price": "₹ 9,50,000",
        "year": "2022",
        "km": "59323",
        "location": "Kundayithode",
    }
    filters = load_filters()
    return jsonify({"match": matches_filters(sample, filters)})


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


# On a server (systemd) the bot should come up with the web app
# rather than waiting for someone to press "Start Bot".
if _env_bool("BOT_AUTOSTART", False):
    print(start_bot())


if __name__ == "__main__":
    # Port 5000 is taken by macOS AirPlay Receiver, so default to 5001.
    port = int(os.getenv("WEBAPP_PORT", "5001"))
    # Bind to localhost by default; on a VPS put nginx (with
    # basic auth) in front — this app has no login of its own.
    host = os.getenv("WEBAPP_HOST", "127.0.0.1")
    # No reloader: it would restart the app on code edits and
    # orphan the bot child process.
    app.run(
        host=host,
        port=port,
        debug=_env_bool("FLASK_DEBUG", False),
        use_reloader=False,
    )
