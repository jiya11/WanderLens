# WanderLens 🌍
WanderLens transforms your smartphone camera into an smart travel companion, solving the universal frustration every traveler faces: standing in front of something amazing and wondering "What am I looking at?" or struggling to read a foreign menu. We've all experienced the exhausting app-juggling act—switching between Google Lens, Google Translate, Google Maps, and notes, constantly context-switching and staring at screens instead of actually experiencing the moment. WanderLens changes this with an all-in-one solution that combines computer vision, translation, geolocation, and gesture recognition into a smooth experience. Point your camera to identify landmarks instantly, translate signs in real-time, discover nearby attractions with a gesture, and automatically journal everything to your digital passport, all without breaking your flow or missing the moments you came to capture.

## 📱 Features
1. 🏛️ Lanmark Identification
Point your camera at any monument, building, or landmark and tap "Identify Landmark". Powered by Google Cloud Vision API, the system uses pre-trained deep learning models to instantly recognize famous sites worldwide and displays the name with contextual information. The frontend captures snapshots and sends base64-encoded images to our Flask backend, which processes the Vision API response and returns landmark names.

2. 🌐 Real-Time Translation
Select your target language and tap "Translate to Target" to read anything in a foreign language. The Optical Character Recognition (OCR) engine powered by Google Cloud Vision API extracts text from the camera view, while the Google Cloud Translation API automatically detects the source language and displays translations instantly. Custom filtering algorithms analyze bounding box area ratios to eliminate noise, translating only the meaningful content you actually want to read.

3. 📍 Nearby Discovery
Tap "Discover Near Me" to find attractions and food spots within walking distance. The system uses OpenStreetMap's API to query real-time geospatial data, calculating accurate distances and walking times using the Haversine formula.

4. 📔 Digital Passport
Every landmark you identify and place you discover can be saved to your digital passport, which is a visual journal of your travels. Each entry includes a photo (for landmarks), timestamp and description.

5. ✋ Gesture Control
Use the application hands-free using MediaPipe Gesture Recognizer, which processes video frames in real-time to classify gestures:
✌️ Peace sign: Trigger a 3-second countdown to scan a landmark
👍 Thumbs up: Save the current result to your Digital Passport
👎 Thumbs down: Close overlays or cancel actions
