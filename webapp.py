import json
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request

from filters import matches_filters

app = Flask(__name__)
FILTERS_FILE = Path("filters.json")

DEFAULT_FILTERS = {
    "location": "",
    "min_price": "",
    "max_price": "",
    "min_year": "",
    "max_year": "",
    "min_km": "",
    "max_km": "",
    "brand": "",
    "fuel": "",
    "transmission": "",
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
  </style>
</head>
<body>
  <div class="container">
    <h1>OLX Car Filter Manager</h1>
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
        <div class="field"><label>Fuel</label><input name="fuel" placeholder="e.g. petrol, diesel, cng" /></div>
        <div class="field"><label>Transmission</label><input name="transmission" placeholder="e.g. automatic, manual" /></div>
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
