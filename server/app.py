# Flask server for WanderLens
# Provides backend APIs for landmark recognition and nearby place discovery
# Uses OpenStreetMap for location data

from flask import Flask, request, jsonify
from flask_cors import CORS


try:
    from dotenv import load_dotenv, find_dotenv  # optional
    load_dotenv(find_dotenv())  # finds .env in project root or server/
except Exception:
    pass

import requests
from google.cloud import vision
from dotenv import load_dotenv
import base64
import os
import requests
import json
import math

load_dotenv()

# Initialize Flask app with CORS support
app = Flask(__name__)
# Development: allow all origins so the frontend (served from any local dev server)
# can call the API without CORS issues. Remove or restrict this in production.
CORS(app)

VISION_API_KEY = os.environ.get("VISION_API_KEY")
if not VISION_API_KEY:
    print("Warning: No VISION_API_KEY found in environment! Please set it.")

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


def _compute_box_area(vertices: list) -> float:
    if not vertices:
        return 0.0
    xs = [v.get("x", 0) for v in vertices]
    ys = [v.get("y", 0) for v in vertices]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    return max(width, 0) * max(height, 0)


def _collect_image_dims(pages: list) -> tuple:
    max_x = 0
    max_y = 0
    for p in pages or []:
        for b in p.get("blocks", []):
            verts = (b.get("boundingBox") or {}).get("vertices", [])
            for v in verts:
                max_x = max(max_x, v.get("x", 0))
                max_y = max(max_y, v.get("y", 0))
    return (max_x or 1, max_y or 1)


def _extract_filtered_text(full_text_anno: dict, min_block_area_ratio: float = 0.01, min_confidence: float = 0.6) -> str:
    if not full_text_anno:
        return ""
    pages = full_text_anno.get("pages", [])
    img_w, img_h = _collect_image_dims(pages)
    img_area = float(img_w * img_h) if img_w and img_h else 1.0

    collected_lines = []
    for p in pages:
        for b in p.get("blocks", []):
            box = (b.get("boundingBox") or {}).get("vertices", [])
            area = _compute_box_area(box)
            area_ratio = (area / img_area) if img_area else 0.0
            conf = b.get("confidence", 1.0)
            if area_ratio < min_block_area_ratio or conf < min_confidence:
                continue
            # Reconstruct text from paragraphs/words/symbols
            block_lines = []
            for para in b.get("paragraphs", []):
                words = []
                for w in para.get("words", []):
                    symbols = [s.get("text", "") for s in w.get("symbols", [])]
                    word = "".join(symbols)
                    if word:
                        words.append(word)
                if words:
                    block_lines.append(" ".join(words))
            if block_lines:
                collected_lines.append("\n".join(block_lines))

    # Fallback: if filtering removed everything, return the raw full text
    if not collected_lines:
        return full_text_anno.get("text", "") or ""
    return "\n\n".join(collected_lines)


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
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    }
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    data = r.json()
    try:
        full = data["responses"][0].get("fullTextAnnotation")
        return _extract_filtered_text(full, min_block_area_ratio=0.01, min_confidence=0.65)
    except Exception:
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
    """Health check endpoint to verify server status"""
    return jsonify({"status": "ok"})

@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Analyzes an image for landmark recognition
    
    Currently implements a mock response for development
    TODO: Replace with actual Vision API integration
    
    Request body:
    {
        "image": "base64 encoded image data"
    }
    
    Returns:
    {
        "landmark": "name of recognized landmark",
        "confidence": float between 0-1,
        "info": "description or additional information"
    }
    """
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
@app.route("/attractions", methods=["GET"])
def get_attractions():
    """
    Fetches nearby tourist attractions using OpenStreetMap data
    
    Query parameters:
    - lat (float): Latitude of center point
    - lon (float): Longitude of center point
    - radius (int): Search radius in meters (default: 1000)
    
    Returns:
    - List of attractions with:
        - name
        - location
        - distance
        - estimated walking time
        - address (if available)
        - additional details from OSM tags
    
    Error responses:
    - 400: Missing required parameters
    - 500: OpenStreetMap API errors
    """
    # Get and validate query parameters
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', 1000, type=int)  # meters, default 1km
    
    if not lat or not lon:
        return jsonify({"error": "lat and lon parameters required"}), 400
    
    # OpenStreetMap Overpass API query - refined for better tourist attractions
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    (
      node["tourism"="attraction"](around:{radius},{lat},{lon});
      node["tourism"="museum"](around:{radius},{lat},{lon});
      node["tourism"="gallery"](around:{radius},{lat},{lon});
      node["tourism"="zoo"](around:{radius},{lat},{lon});
      node["tourism"="theme_park"](around:{radius},{lat},{lon});
      node["tourism"="monument"](around:{radius},{lat},{lon});
      node["tourism"="memorial"](around:{radius},{lat},{lon});
      node["tourism"="viewpoint"](around:{radius},{lat},{lon});
      node["historic"="monument"](around:{radius},{lat},{lon});
      node["historic"="castle"](around:{radius},{lat},{lon});
      node["historic"="palace"](around:{radius},{lat},{lon});
      node["historic"="ruins"](around:{radius},{lat},{lon});
    );
    out;
    """
    
    try:
        response = requests.post(overpass_url, data=query)
        response.raise_for_status()
        data = response.json()
        
        # Process and format the results
        attractions = []
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            attraction_lat = element.get('lat')
            attraction_lon = element.get('lon')
            # Skip elements without coordinates (e.g., ways/relations or incomplete data)
            if attraction_lat is None or attraction_lon is None:
                continue
            
            # Calculate distance in meters using Haversine formula
            def calculate_distance(lat1, lon1, lat2, lon2):
                R = 6371000  # Earth's radius in meters
                dlat = math.radians(lat2 - lat1)
                dlon = math.radians(lon2 - lon1)
                a = (math.sin(dlat/2) * math.sin(dlat/2) + 
                     math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
                     math.sin(dlon/2) * math.sin(dlon/2))
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                return R * c
            
            distance_m = calculate_distance(lat, lon, attraction_lat, attraction_lon)
            distance_km = round(distance_m / 1000, 1)
            walking_time = round(distance_m / 83.33)  # Average walking speed: 5 km/h = 83.33 m/min
            
            # Format address
            address_parts = []
            if tags.get('addr:housenumber'):
                address_parts.append(tags.get('addr:housenumber'))
            if tags.get('addr:street'):
                address_parts.append(tags.get('addr:street'))
            if tags.get('addr:city'):
                address_parts.append(tags.get('addr:city'))
            address = ', '.join(address_parts) if address_parts else 'Address not available'
            
            # Skip unnamed attractions
            name = tags.get('name', '').strip()
            if not name:
                continue

            attractions.append({
                'id': element.get('id'),
                'name': name,
                'type': tags.get('tourism', tags.get('historic', tags.get('amenity', 'attraction'))),
                'lat': attraction_lat,
                'lon': attraction_lon,
                'address': address,
                'distance_km': distance_km,
                'walking_time_min': walking_time,
                'description': tags.get('description', ''),
                'website': tags.get('website', ''),
                'opening_hours': tags.get('opening_hours', '')
            })
        
        # Sort by quality and distance, then limit to 6 results
        def attraction_priority(attraction):
            # Priority scoring: museums, galleries, monuments get higher priority
            type_priority = {
                'museum': 3,
                'gallery': 3,
                'monument': 2,
                'memorial': 2,
                'attraction': 1,
                'viewpoint': 1,
                'artwork': 1
            }
            priority = type_priority.get(attraction['type'], 0)
            # Lower distance = higher priority (multiply by -1)
            return (priority, -attraction['distance_km'])
        
        attractions.sort(key=attraction_priority, reverse=True)
        attractions = attractions[:6]  # Limit to 6 attractions max
        
        return jsonify({
            'attractions': attractions,
            'count': len(attractions),
            'center': {'lat': lat, 'lon': lon},
            'radius': radius
        })
        
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to fetch attractions: {str(e)}"}), 500


@app.route("/food", methods=["GET"])
def get_food_spots():
    # Get query parameters
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', 1000, type=int)  # meters, default 1km
    
    if not lat or not lon:
        return jsonify({"error": "lat and lon parameters required"}), 400
    
    # OpenStreetMap Overpass API query for food spots
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="restaurant"](around:{radius},{lat},{lon});
      node["amenity"="cafe"]["cuisine"!~"coffee_shop"](around:{radius},{lat},{lon});
      node["amenity"="bar"](around:{radius},{lat},{lon});
    );
    out;
    """
    
    try:
        response = requests.post(overpass_url, data=query)
        response.raise_for_status()
        data = response.json()
        
        # Process and format the results
        food_spots = []
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            spot_lat = element.get('lat')
            spot_lon = element.get('lon')
            # Skip elements without coordinates (e.g., ways/relations or incomplete data)
            if spot_lat is None or spot_lon is None:
                continue
            
            # Calculate distance in meters using Haversine formula
            def calculate_distance(lat1, lon1, lat2, lon2):
                R = 6371000  # Earth's radius in meters
                dlat = math.radians(lat2 - lat1)
                dlon = math.radians(lon2 - lon1)
                a = (math.sin(dlat/2) * math.sin(dlat/2) + 
                     math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
                     math.sin(dlon/2) * math.sin(dlon/2))
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                return R * c
            
            distance_m = calculate_distance(lat, lon, spot_lat, spot_lon)
            distance_km = round(distance_m / 1000, 1)
            walking_time = round(distance_m / 83.33)  # Average walking speed: 5 km/h = 83.33 m/min
            
            # Format address
            address_parts = []
            if tags.get('addr:housenumber'):
                address_parts.append(tags.get('addr:housenumber'))
            if tags.get('addr:street'):
                address_parts.append(tags.get('addr:street'))
            if tags.get('addr:city'):
                address_parts.append(tags.get('addr:city'))
            address = ', '.join(address_parts) if address_parts else 'Address not available'

            # Get cuisine type and amenity
            cuisine = tags.get('cuisine', '').replace(';', ', ').title()
            amenity = tags.get('amenity', '').lower()
            
            # Skip fast food and coffee shops
            if amenity in ['fast_food'] or 'coffee' in cuisine.lower():
                continue
                
            name = tags.get('name', '').strip()
            if not name:
                continue

            description_parts = []
            if cuisine:
                description_parts.append(f"Cuisine: {cuisine}")
            if tags.get('description'):
                description_parts.append(tags.get('description'))
            
            description = ' | '.join(description_parts) if description_parts else ''
            
            food_spots.append({
                'id': element.get('id'),
                'name': name,
                'type': amenity.replace('_', ' ').title(),
                'cuisine': cuisine,
                'lat': spot_lat,
                'lon': spot_lon,
                'address': address,
                'distance_km': distance_km,
                'walking_time_min': walking_time,
                'description': description,
                'website': tags.get('website', ''),
                'opening_hours': tags.get('opening_hours', '')
            })
        
        # Sort by quality and distance, then limit to 6 results
        def food_priority(food_spot):
            # Priority scoring: restaurants with cuisine info get higher priority
            priority = 0
            if food_spot.get('cuisine'):
                priority += 2
            if food_spot.get('website'):
                priority += 1
            if food_spot.get('opening_hours'):
                priority += 1
            # Lower distance = higher priority (multiply by -1)
            return (priority, -food_spot['distance_km'])
        
        food_spots.sort(key=food_priority, reverse=True)
        food_spots = food_spots[:6]  # Limit to 6 food spots max
        
        return jsonify({
            'food_spots': food_spots,
            'food_count': len(food_spots),
            'center': {'lat': lat, 'lon': lon},
            'radius': radius
        })
        
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to fetch food spots: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)


