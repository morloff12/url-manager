from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from datetime import datetime
import requests
from bs4 import BeautifulSoup

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

def scrape_price_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        reg_price = None
        sale_price = None

        reg = soup.find(class_="field--name-commerce-price")
        if reg:
            reg_price = reg.get_text(strip=True)

        sale = soup.find(class_="price--without-tax")
        if sale:
            sale_price = sale.get_text(strip=True)

        return reg_price, sale_price
    except Exception as e:
        return None, None

@app.route("/send-email", methods=["POST"])
def send_email():
    expected_token = os.environ.get("EMAIL_SECRET")
    received_token = request.headers.get("X-Secret")

    if expected_token is None or received_token != expected_token:
        return jsonify({"error": "Forbidden"}), 403

    try:
        data = db.reference('urls').get() or {}
        active_items = [entry for entry in data.values() if not entry.get("disabled", False)]
        if not active_items:
            return jsonify({"message": "No active items to include in email"}), 200

        html_rows = ""
        for entry in active_items:
            reg_price, sale_price = scrape_price_from_url(entry.get("url"))
            title = entry.get("title", "(no title)")
            url = entry.get("url")
            html_rows += f"<tr><td><strong>{title}</strong></td><td><a href='{url}'>{url}</a></td><td>{reg_price or ''}</td><td>{sale_price or ''}</td></tr>"

        html_body = f"""
        <html>
        <body>
            <p>Watchlist Items as of {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC:</p>
            <table border='1' cellpadding='6' cellspacing='0'>
                <tr><th>Title</th><th>URL</th><th>Regular Price</th><th>Sale Price</th></tr>
                {html_rows}
            </table>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg['Subject'] = 'URL Manager: Items on Sale'
        msg['From'] = os.environ.get("SMTP_FROM")
        msg['To'] = os.environ.get("SMTP_TO")
        msg.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS"))
        server.send_message(msg)
        server.quit()

        return jsonify({"message": "Email sent"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ping-firebase")
def ping():
    try:
        snapshot = REF.get()
        return jsonify({"status": "success", "count": len(snapshot) if snapshot else 0})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/healthcheck")
def healthcheck():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
