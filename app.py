import os
import json
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db

# Load Firebase admin credentials from environment variable
FIREBASE_KEY_B64 = os.getenv("FIREBASE_ADMIN_BASE64")
if not FIREBASE_KEY_B64:
    raise ValueError("Missing FIREBASE_ADMIN_BASE64 environment variable")

firebase_key = base64.b64decode(FIREBASE_KEY_B64)
service_account_info = json.loads(firebase_key)

# Initialize Firebase
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://url-manager-ae427-default-rtdb.firebaseio.com'
})

REF = db.reference("/urls")

# Setup Flask
app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return "URL Manager API is running", 200

@app.route("/ping-firebase")
def ping_firebase():
    try:
        data = db.reference("/").get()
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/urls", methods=["GET"])
def get_urls():
    try:
        data = REF.get()
        return jsonify(data or {}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/urls", methods=["POST"])
def add_url():
    try:
        url_data = request.json
        if not url_data:
            raise ValueError("Missing JSON body")
        new_ref = REF.push()
        new_ref.set(url_data)
        return jsonify({"success": True, "id": new_ref.key}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/urls/<key>", methods=["DELETE"])
def delete_url(key):
    try:
        REF.child(key).delete()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/urls/<key>", methods=["PATCH"])
def update_url(key):
    try:
        updates = request.json
        if not updates:
            raise ValueError("Missing JSON body")
        REF.child(key).update(updates)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
