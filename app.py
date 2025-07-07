from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

# Firebase Init
firebase_creds_json = os.environ.get("FIREBASE_ADMIN_BASE64")
if not firebase_creds_json:
    raise ValueError("Missing FIREBASE_ADMIN_BASE64 environment variable")

import base64
import json
firebase_creds_dict = json.loads(base64.b64decode(firebase_creds_json))
cred = credentials.Certificate(firebase_creds_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://url-manager-ae427.firebaseio.com'
})

app = Flask(__name__)
CORS(app)

REF = db.reference("/urls")

@app.route("/urls", methods=["GET"])
def get_urls():
    data = REF.get()
    if not data:
        return jsonify({})
    return jsonify(data)

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

@app.route("/urls/<string:url_id>", methods=["PATCH"])
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

@app.route("/send-email", methods=["POST"])
def send_email():
    expected_token = os.environ.get("EMAIL_SECRET")
    received_token = request.headers.get("X-Secret")

    if expected_token is None or received_token != expected_token:
        return jsonify({"error": "Forbidden"}), 403

    try:
        print("Token validated")
        data = db.reference('urls').get() or {}
        print(f"Data retrieved: {len(data)} items")

        active_items = [entry for entry in data.values() if not entry.get("disabled", False)]
        if not active_items:
            print("No active items")
            return jsonify({"message": "No active items to include in email"}), 200

        body = "\n".join([f"- {entry.get('title', '(no title)')}: {entry.get('url')}" for entry in active_items])
        print("Body composed")

        msg = MIMEText(body)
        msg['Subject'] = 'URL Manager: Items on Watchlist'
        msg['From'] = os.environ.get("SMTP_FROM")
        msg['To'] = os.environ.get("SMTP_TO")

        print("Connecting to SMTP")
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS"))
        print("Logged in")
        server.send_message(msg)
        server.quit()
        print("Email sent")

        return jsonify({"message": "Email sent"}), 200

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/ping-firebase")
def ping():
    try:
        snapshot = REF.get()
        return jsonify({"status": "success", "count": len(snapshot) if snapshot else 0})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
