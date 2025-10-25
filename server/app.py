from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import base64
import json

try:
    from dotenv import load_dotenv, find_dotenv  # optional
    load_dotenv(find_dotenv())  # finds .env in project root or server/
except Exception:
    pass

import requests

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://127.0.0.1:5173", "http://localhost:5173"]}})


def _extract_base64_from_data_url(data_url: str) -> str:
    if not data_url:
        return ""
    if "," in data_url:
        return data_url.split(",", 1)[1]
    return data_url


def _google_api_key() -> str:
    # Single key used for both Vision OCR and Translate
    return (
        os.getenv("GOOGLE_TRANSLATE_API_KEY")
        or os.getenv("GOOGLE_CLOUD_API_KEY")
        or ""
    )


def call_google_vision_text_detection(image_data_url: str) -> str:
    api_key = _google_api_key()
    if not api_key:
        return ""  # no key → signal caller to mock
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    content_b64 = _extract_base64_from_data_url(image_data_url)
    payload = {
        "requests": [
            {
                "image": {"content": content_b64},
                "features": [{"type": "TEXT_DETECTION"}]
            }
        ]
    }
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    data = r.json()
    try:
        annotations = data["responses"][0].get("fullTextAnnotation")
        return annotations.get("text", "") if annotations else ""
    except Exception:
        return ""


def call_google_translate(text: str, target: str = "en") -> dict:
    api_key = _google_api_key()
    if not api_key:
        return {"translatedText": "", "detectedSourceLanguage": ""}
    url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
    payload = {"q": text, "target": target, "format": "text"}
    r = requests.post(url, data=payload, timeout=20)
    r.raise_for_status()
    data = r.json()
    try:
        tr = data["data"]["translations"][0]
        return {
            "translatedText": tr.get("translatedText", ""),
            "detectedSourceLanguage": tr.get("detectedSourceLanguage", "")
        }
    except Exception:
        return {"translatedText": "", "detectedSourceLanguage": ""}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/analyze", methods=["POST"])
def analyze():
    _ = request.get_json(silent=True) or {}
    response = {
        "landmark": "Demo Landmark",
        "confidence": 0.99,
        "info": "This is a mock recognition result. Replace with Google Vision Landmark Detection for production demos."
    }
    return jsonify(response)


@app.route("/ocr_translate", methods=["POST"])
def ocr_translate():
    body = request.get_json(silent=True) or {}
    image_data_url = body.get("image", "")
    target_lang = (body.get("target") or "en").lower()

    detected_text = ""
    translated_text = ""
    source_lang = ""

    try:
        detected_text = call_google_vision_text_detection(image_data_url)
        if not detected_text:
            # No API key or no text: provide a graceful mock for demo continuity
            detected_text = "Demo text on sign"
        tr = call_google_translate(detected_text, target=target_lang)
        translated_text = tr.get("translatedText") or ("Demo translation → " + detected_text)
        source_lang = tr.get("detectedSourceLanguage") or "auto"
    except Exception:
        detected_text = "Demo text on sign"
        translated_text = "Demo translation → Demo text on sign"
        source_lang = "auto"

    return jsonify({
        "detected_text": detected_text,
        "translated_text": translated_text,
        "source_lang": source_lang,
        "target_lang": target_lang
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)


