from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import os
import requests
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Flask App Setup ---
app = Flask(__name__)
CORS(app)

# --- Firebase Init ---
cred = credentials.Certificate("firebase-admin-key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://YOUR_PROJECT.firebaseio.com'  # replace with yours
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

    # existing scan logic follows...

    results = []
    for item in data.values():
        if item.get("disabled"):
            continue
        url = item["url"]
        title = item.get("title", "")

        try:
            r = requests.get(url, timeout=10)
            html = r.text

            # Get product title if missing
            if not title:
                match = re.search(r'<div class="field[^>]+field--name-field-web-description[^>]*">(.*?)</div>', html)
                if match:
                    title = match.group(1).strip()

            # Detect sale price
            is_on_sale = bool(re.search(r'<div class="pro

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if not set
<<<<<<< HEAD
    app.run(host="0.0.0.0", port=port)

=======
    app.run(host="0.0.0.0", port=port)
>>>>>>> 982d9e6 (Switch to Firebase backend)
