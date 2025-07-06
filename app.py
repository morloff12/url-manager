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
        return jsonify({"error": "Missing 'url' field"}), 400
    urls = load_urls()
    urls.append(url)
    save_urls(urls)
    return jsonify({"success": True, "url": url})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if not set
    app.run(host="0.0.0.0", port=port)

