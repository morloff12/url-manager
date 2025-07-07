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
    'databaseURL': 'https://url-manager-ae427-default-rtdb.firebaseio.com'
})

app = Flask(__name__)
CORS(app)

REF = db.reference("/urls")

@app.route("/urls", methods=["GET"])
def get_urls():
    data = REF.get()
    return jsonify(data or {})

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
        print("Forbidden: Secret mismatch")
        return jsonify({"error": "Forbidden"}), 403

    try:
        print("Token validated")

        data = db.reference('urls').get()
        if data is None:
            print("No data returned from Firebase")
            return jsonify({"message": "No data in Firebase"}), 200

        active_items = [entry for entry in data.values() if not entry.get("disabled", False)]
        print(f"Active items: {len(active_items)}")

        if not active_items:
            return jsonify({"message": "No active items to include in email"}), 200

        body = "\n".join([f"- {entry.get('title', '(no title)')}: {entry.get('url')}" for entry in active_items])
        print(f"Composed body:\n{body}")

        msg = MIMEText(body)
        msg['Subject'] = 'URL Manager: Items on Watchlist'
        msg['From'] = os.environ.get("SMTP_FROM")
        msg['To'] = os.environ.get("SMTP_TO")

        smtp_user = os.environ.get("SMTP_USER")
        smtp_pass = os.environ.get("SMTP_PASS")

        if not all([smtp_user, smtp_pass, msg['From'], msg['To']]):
            raise ValueError("Missing SMTP credentials or email headers")

        print("Connecting to SMTP server...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()

        print("Email sent successfully.")
        return jsonify({"message": "Email sent"}), 200

    except Exception as e:
        import traceback
        print("EMAIL ERROR:", str(e))
        traceback.print_exc()
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
