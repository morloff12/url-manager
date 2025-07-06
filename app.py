# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import os

from scraping import scrape_product
from emailer import send_email_report

# --- Flask App Setup ---
app = Flask(__name__)
CORS(app)

# --- Firebase Init ---
cred = credentials.Certificate("firebase-admin-key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://url-manager-ae427.firebaseio.com'  # Replace with your actual URL
})
REF = db.reference("/urls")

# --- API Routes ---

# Get all URLs
@app.route("/urls", methods=["GET"])
def get_urls():
    data = REF.get()
    return jsonify(list(data.values()) if data else [])

# Add new URL
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

# Update existing URL
@app.route("/urls/<string:url_id>", methods=["PUT"])
def update_url(url_id):
    updates = request.json
    item_ref = REF.child(url_id)
    if not item_ref.get():
        return jsonify({"error": "Not found"}), 404
    item_ref.update(updates)
    return jsonify({"success": True})

# Delete URL
@app.route("/urls/<string:url_id>", methods=["DELETE"])
def delete_url(url_id):
    REF.child(url_id).delete()
    return jsonify({"success": True})

# Run product scan and email if sales detected
@app.route("/run-scan", methods=["POST"])
def run_scan():
    expected_token = os.environ.get("SCAN_TOKEN")
    received_token = request.headers.get("X-Scan-Token")
    if expected_token is None or received_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401

    data = REF.get() or {}
    results = []

    for key, entry in data.items():
        if entry.get("disabled"):
            continue

        url = entry["url"]
        title = entry.get("title", "").strip()

        try:
            result = scrape_product(title, url)
            if result and result.get("on_sale"):
                results.append(result)
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")

    if results:
        send_email_report(results)

    return jsonify({"found_sales": len(results)})

# --- App Runner ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
