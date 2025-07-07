from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import os
import json
import requests
import re
from emailer import send_email_report

# --- Flask App Setup ---
app = Flask(__name__)
CORS(app)

# --- Firebase Init from ENV ---
firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS")
if not firebase_creds_json:
    raise RuntimeError("FIREBASE_CREDENTIALS not found in environment variables")

firebase_creds_dict = json.loads(firebase_creds_json)
cred = credentials.Certificate(firebase_creds_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://url-manager-ae427.firebaseio.com'  # replace with your actual DB URL
})

REF = db.reference("/urls")

# --- Routes: CRUD ---
@app.route("/urls", methods=["GET"])
def get_urls():
    data = REF.get()
    return jsonify(list(data.values()) if data else [])

@app.route("/urls", methods=["POST"])
def add_url():
    data = request.json
    url = data.get("url")
    title = data.get("title", "")
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400
    new_ref = REF.push()
    item = {
        "id": new_ref.key,
        "url": url,
        "title": title,
        "disabled": False
    }
    new_ref.set(item)
    return jsonify(item), 201

@app.route("/urls/<string:url_id>", methods=["PUT"])
def update_url(url_id):
    updates = request.json
    item_ref = REF.child(url_id)
    if not item_ref.get():
        return jsonify({"error": "Not found"}), 404
    item_ref.update(updates)
    return jsonify({"success": True})

@app.route("/urls/<string:url_id>", methods=["DELETE"])
def delete_url(url_id):
    REF.child(url_id).delete()
    return jsonify({"success": True})

# --- /run-scan ---
@app.route("/run-scan", methods=["POST"])
def run_scan():
    expected_token = os.environ.get("SCAN_TOKEN")
    received_token = request.headers.get("X-Scan-Token")
    if expected_token is None or received_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401

    data = REF.get() or {}
    results = []

    for item in data.values():
        if item.get("disabled"):
            continue

        url = item["url"]
        title = item.get("title", "")

        try:
            r = requests.get(url, timeout=10)
            html = r.text

            # Auto-scrape title if missing
            if not title:
                match = re.search(r'<div class="field[^>]*field--name-field-web-description[^>]*">(.*?)</div>', html)
                if match:
                    title = match.group(1).strip()

            # Detect sale
            sale_match = re.search(r'<div class="product_price">.*?<div class="retail_price">(.*?)</div>.*?<div class="promo_price">(.*?)</div>', html, re.DOTALL)
            if sale_match:
                regular_price = sale_match.group(1).strip()
                sale_price = sale_match.group(2).strip()
                results.append({
                    "title": title or url,
                    "url": url,
                    "regular_price": regular_price,
                    "sale_price": sale_price,
                    "on_sale": True
                })

        except Exception as e:
            print(f"Error scraping {url}: {e}")

    if results:
        send_email_report(results)

    return jsonify({"results": results})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
