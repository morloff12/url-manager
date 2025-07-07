import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, jsonify
from flask_cors import CORS

# Load Firebase credentials from base64 string
firebase_creds_json = os.environ.get('FIREBASE_ADMIN_BASE64')
if not firebase_creds_json:
    raise ValueError("Missing FIREBASE_ADMIN_BASE64 environment variable")

firebase_creds_dict = json.loads(base64.b64decode(firebase_creds_json))
cred = credentials.Certificate(firebase_creds_dict)

# Initialize Firebase Admin SDK with correct database URL
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://url-manager-ae427.firebaseio.com'
})

REF = db.reference('urls')

# Flask app setup
app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return "URL Manager API is running", 200

@app.route('/urls', methods=['GET'])
def get_urls():
    try:
        data = REF.get()
        if data is None:
            return jsonify([]), 200
        # Convert dict to list with ID included
        formatted = [{"id": k, **v} for k, v in data.items()]
        return jsonify(formatted), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/urls', methods=['POST'])
def add_url():
    try:
        url_data = request.json
        new_ref = REF.push()
        new_ref.set(url_data)
        return jsonify({"id": new_ref.key}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/urls/<url_id>', methods=['PUT'])
def update_url(url_id):
    try:
        url_data = request.json
        REF.child(url_id).update(url_data)
        return jsonify({"status": "updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/urls/<url_id>', methods=['DELETE'])
def delete_url(url_id):
    try:
        REF.child(url_id).delete()
        return jsonify({"status": "deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/run-scan', methods=['POST'])
def run_scan():
    token = request.headers.get("Authorization")
    expected = f"Bearer {os.environ.get('SCAN_TOKEN')}"
    if token != expected:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Placeholder: real scan logic goes here
        print("Running scan on URLs...")
        return jsonify({"status": "Scan complete"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
