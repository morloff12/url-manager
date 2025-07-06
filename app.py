from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

DATA_FILE = "urls.json"

def load_urls():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_urls(urls):
    with open(DATA_FILE, "w") as f:
        json.dump(urls, f)

@app.route("/urls", methods=["GET"])
def get_urls():
    return jsonify(load_urls())

@app.route("/urls", methods=["POST"])
def add_url():
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400

    urls = load_urls()
    next_id = max((item["id"] for item in urls), default=0) + 1
    new_entry = {"id": next_id, "url": url, "disabled": False}
    urls.append(new_entry)
    save_urls(urls)
    return jsonify(new_entry), 201

@app.route("/urls/<int:url_id>", methods=["PUT"])
def update_url(url_id):
    data = request.json
    urls = load_urls()
    updated = False
    for item in urls:
        if item["id"] == url_id:
            if "url" in data:
                item["url"] = data["url"]
            if "disabled" in data:
                item["disabled"] = data["disabled"]
            updated = True
            break
    if not updated:
        return jsonify({"error": "Item not found"}), 404
    save_urls(urls)
    return jsonify({"success": True})

@app.route("/urls/<int:url_id>", methods=["DELETE"])
def delete_url(url_id):
    urls = load_urls()
    urls = [item for item in urls if item["id"] != url_id]
    save_urls(urls)
    return jsonify({"success": True})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if not set
    app.run(host="0.0.0.0", port=port)

