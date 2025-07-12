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
from urllib.parse import urlparse

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
    if not url or not title:
        return jsonify({"error": "Missing 'url' or 'title'"}), 400
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
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")

        reg_price = None
        sale_price = None
        promotion = None

        if "liquormarts.ca" in domain:
            reg = soup.find(class_="retail_price")
            if reg:
                reg_price = reg.get_text(strip=True)

            sale = soup.find(class_="promo_price")
            if sale:
                sale_price = sale.get_text(strip=True)

            promo = soup.find(class_="bonus_miles_number")
            if promo:
                promotion = promo.get_text(strip=True)

        if reg_price == sale_price:
            sale_price = None

        return reg_price, sale_price, promotion
    except Exception as e:
        print(f"[SCRAPER ERROR] {e}")
        return None, None, None

@app.route("/send-email", methods=["POST"])
def send_email():
    expected_token = os.environ.get("EMAIL_SECRET")
    received_token = request.headers.get("X-Secret")

    if expected_token is None or received_token != expected_token:
        return jsonify({"error": "Forbidden"}), 403

    try:
        data = db.reference('urls').get() or {}
        active_items = [entry for entry in data.values() if not entry.get("disabled", False)]

        sorted_items = sorted(
            active_items,
            key=lambda x: (
                not any(scrape_price_from_url(x.get("url"))[1:]),  # False if has sale/promo
                x.get("title", "")
            )
        )

        html_rows = ""
        for entry in sorted_items:
            reg_price, sale_price, promo = scrape_price_from_url(entry.get("url"))
            title = entry.get("title", "(no title)")
            url = entry.get("url")
            html_rows += f"<tr><td><a href='{url}'>{title}</a></td><td align='right'>{reg_price or ''}</td><td align='right'>{sale_price or ''}</td><td align='right'>{promo or ''}</td></tr>"

        html_body = f"""
        <html>
        <head>
            <meta charset='UTF-8'>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; }}
                th, td {{ padding: 6px 12px; border: 1px solid #ccc; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <p>Watchlist Items as of {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC:</p>
            <table>
              <thead>
                <tr>
                  <th align="left">Title</th>
                  <th align="right">Regular Price</th>
                  <th align="right">Sale Price</th>
                  <th align="right">Promotions</th>
                </tr>
              </thead>
              <tbody>
                {html_rows}
              </tbody>
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
