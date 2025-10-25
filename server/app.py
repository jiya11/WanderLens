# Flask server for WanderLens
# Provides backend APIs for landmark recognition and nearby place discovery
# Uses OpenStreetMap for location data

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import math

# Initialize Flask app with CORS support
app = Flask(__name__)
# Allow requests only from development servers
CORS(app, resources={r"/*": {"origins": ["http://127.0.0.1:5173", "http://localhost:5173"]}})


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

    # Mock inference for hackathon speed. Replace with Vision API later.
    # You can add simple heuristics here if desired.
    response = {
        "landmark": "Demo Landmark",
        "confidence": 0.99,
        "info": "This is a mock recognition result. Replace with Google Vision Landmark Detection for production demos."
    }
    return jsonify(response)


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


