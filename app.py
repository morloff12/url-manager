from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
import os

app = Flask(__name__)
CORS(app)

# Initialize Firebase Admin
cred = credentials.Certificate("firebase-admin-key.json")
firebase_admin.initialize_app(cred, {
<<<<<<< HEAD
    'databaseURL': 'https://YOUR_PROJECT_ID.firebaseio.com'  # <- REPLACE THIS
=======
    'databaseURL': 'https://url-manager-ae427.firebaseio.com'  # <- REPLACE THIS
>>>>>>> 982d9e6 (Switch to Firebase backend)
})

REF = db.reference("/urls")

# Fetch all URLs
@app.route("/urls", methods=["GET"])
def get_urls():
    data = REF.get()
    if not data:
        return jsonify([])
    return jsonify(list(data.values()))

# Add a new URL
@app.route("/urls", methods=["POST"])
def add_url():
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400

    new_ref = REF.push()
    new_data = {
        "id": new_ref.key,
        "url": url,
        "disabled": False
    }
    new_ref.set(new_data)
    return jsonify(new_data), 201

# Update URL (edit or toggle disabled)
@app.route("/urls/<string:url_id>", methods=["PUT"])
def update_url(url_id):
    updates = request.json
    item_ref = REF.child(url_id)
    if not item_ref.get():
        return jsonify({"error": "Item not found"}), 404
    item_ref.update(updates)
    return jsonify({"success": True})

# Delete a URL
@app.route("/urls/<string:url_id>", methods=["DELETE"])
def delete_url(url_id):
    item_ref = REF.child(url_id)
    if not item_ref.get():
        return jsonify({"error": "Item not found"}), 404
    item_ref.delete()
    return jsonify({"success": True})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if not set
<<<<<<< HEAD
    app.run(host="0.0.0.0", port=port)

=======
    app.run(host="0.0.0.0", port=port)
>>>>>>> 982d9e6 (Switch to Firebase backend)
