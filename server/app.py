from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import vision
from dotenv import load_dotenv
import requests
import base64
import os

load_dotenv()

app = Flask(__name__)
# Development: allow all origins so the frontend (served from any local dev server)
# can call the API without CORS issues. Remove or restrict this in production.
CORS(app)

VISION_API_KEY = os.environ.get("VISION_API_KEY")
if not VISION_API_KEY:
    print("Warning: No VISION_API_KEY found in environment! Please set it.")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    image_data_url = data.get("image", "")

    if not image_data_url:
        return jsonify({"error": "No image provided"}), 400

    if image_data_url.startswith("data:image"):
        image_data_url = image_data_url.split(",")[1]

    try:
        image_bytes = base64.b64decode(image_data_url)
    except Exception:
        return jsonify({"error": "Invalid base64 image"}), 400

    if not VISION_API_KEY:
        return jsonify({"error": "missing_api_key", "message": "Set VISION_API_KEY in environment"}), 500

    try:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        url = f"https://vision.googleapis.com/v1/images:annotate?key={VISION_API_KEY}"
        payload = {
            "requests": [
                {
                    "image": {"content": b64},
                    "features": [{"type": "LANDMARK_DETECTION", "maxResults": 5}]
                }
            ]
        }
        r = requests.post(url, json=payload, timeout=30)
        if not r.ok:
            return jsonify({"error": "vision_api_error", "message": r.text}), 502

        resp_json = r.json()
        resp0 = resp_json.get("responses", [])[0] if resp_json.get("responses") else {}
        landmarks = resp0.get("landmarkAnnotations", [])

        if not landmarks:
            return jsonify({"landmark": None, "info": "No landmark detected."})

        landmark = landmarks[0]
        return jsonify({
            "landmark": landmark.get("description"),
            "confidence": landmark.get("score"),
            "info": f"Detected landmark: {landmark.get('description')}"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "vision_api_error", "message": str(e)}), 502

    else:
        # Use service-account backed client
        image = vision.Image(content=image_bytes)
        try:
            response = vision_client.landmark_detection(image=image)
            landmarks = response.landmark_annotations
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": "vision_api_error", "message": str(e)}), 502

    if not landmarks:
        return jsonify({
            "landmark": None,
            "confidence": 0,
            "info": "No landmark detected."
        })
    
    #Take top result
    landmark = landmarks[0]

    response = {
        "landmark": landmark.description,
        "confidence": landmark.score,
        "locations": [
            {"lat": loc.lat_lng.latitude, "lng": loc.lat_lng.longitude}
            for loc in landmark.locations
        ],
        "info": f"Detected landmark: {landmark.description}"
    }
    return jsonify(response)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)


