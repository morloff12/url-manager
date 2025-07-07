# app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import os
import json
import base64
import requests
import re
from emailer import send_email_report

# --- Flask App Setup ---
app = Flask(__name__)
CORS(app)

# --- Firebase Initialization ---
firebase_creds_b64 = os.environ.get("FIREBASE_CREDENTIALS_B64")
if not firebase_creds_b64:
    raise Exception("Missing FIREBASE_CREDENTIALS_B64 environment variable")

firebase_creds_json = base64.b64decode(firebase_creds_b64).decode("utf-8")
firebase_creds_dict = json.loads(firebase_creds_json)

cred = credentials.Certificate(firebase_creds_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://url-manager-s98r.firebaseio.com/'  # Replace with your databaseURL
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

# --- Scraper ---
def scrape_product(title, url):
    try:
        r = requests.get(url, timeout=10)
        html = r.text
        regular_price = None
        sale_price = None
        is_on_sale = False

        # Try to extract title if missing
        if not title:
            match = re.search(r'<div class="field[^>]*field--name-field-web-description[^>]*">(.*?)</div>', html)
            if match:
                title = match.group(1).strip()

        # Detect prices
        promo_match = re.search(r'<div class="promo_price">(.*?)</div>', html)
        retail_match = re.search(r'<div class="retail_price">(.*?)</div>', html)
        regular_match = re.search(r'<div class="product_price">\s*(\$[\d.]+)\s*</div>', html)

        if promo_match:
            is_on_sale = True
            sale_price = promo_match.group(1).strip()
            if retail_match:
                regular_price = retail_match.group(1).strip()
        elif regular_match:
            regular_price = regular_match.group(1).strip()

        return {
            "title": title or url,
            "url": url,
            "regular_price": regular_price,
            "sale_price": sale_price,
            "on_sale": is_on_sale
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

# --- Scan Trigger Endpoint ---
@app.route("/run-scan", methods=["POST"])
def run_scan():
    expected_token = os.environ.get("SCAN_TOKEN")
    received_token = request.headers.get("X-Scan-Token")
    if expected_token is None or received_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401

    urls_dict = REF.get() or {}
    results = []

    for entry in urls_dict.values():
        if entry.get("disabled"):
            continue
        url = entry["url"]
        title = entry.get("title", "")

        result = scrape_product(title, url)
        if result and result["on_sale"]:
            results.append(result)

    if results:
        send_email_report(results)

    return jsonify({"results": results, "count": len(results)})

# --- Main ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
