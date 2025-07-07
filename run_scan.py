# run_scan.py

import os
import json
import base64
import requests
import firebase_admin
from firebase_admin import credentials, db

# Load Firebase credentials
FIREBASE_KEY_B64 = os.getenv("FIREBASE_ADMIN_BASE64")
if not FIREBASE_KEY_B64:
    raise ValueError("Missing FIREBASE_ADMIN_BASE64 environment variable")

firebase_key = base64.b64decode(FIREBASE_KEY_B64)
service_account_info = json.loads(firebase_key)

# Initialize Firebase
if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate(service_account_info), {
        'databaseURL': 'https://url-manager-ae427.firebaseio.com'
    })

REF = db.reference("/urls")

def scrape_title(url):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            tag = soup.find("div", class_="field field--name-field-web-description field--type-string field--label-hidden field__item")
            return tag.get_text(strip=True) if tag else "No title found"
        return "Failed to load page"
    except Exception as e:
        return f"Error: {e}"

def run_scan():
    urls = REF.get() or {}
    for key, value in urls.items():
        url = value.get("url")
        if url:
            title = scrape_title(url)
            REF.child(key).update({"title": title})

if __name__ == "__main__":
    run_scan()
    print("Scan complete.")
