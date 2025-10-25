from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://127.0.0.1:5173", "http://localhost:5173"]}})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    image_data_url = data.get("image", "")

    # Mock inference for hackathon speed. Replace with Vision API later.
    # You can add simple heuristics here if desired.
    response = {
        "landmark": "Demo Landmark",
        "confidence": 0.99,
        "info": "This is a mock recognition result. Replace with Google Vision Landmark Detection for production demos."
    }
    return jsonify(response)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)


