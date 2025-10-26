# WanderLens

An AR-style, web-first demo for travelers: point your camera at a landmark image, get an overlay with the name and a fun fact, and save it to a "Digital Passport." Includes a minimal Python (Flask) backend so you can hide API keys later and expand easily.

## Quick Start

Prereqs:

- Python 3.9+ installed
- A modern browser (Chrome/Edge/Safari/Firefox). Camera requires a secure context (https or localhost)

1. Backend (Flask)

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

The server runs at `http://127.0.0.1:5001`.

2. Frontend (static web)

Use a simple local server so the camera works (browsers block camera on file://):

```bash
cd web
python3 -m http.server 5173
```

Open `http://127.0.0.1:5173` in your browser.

## What You Can Demo

- Live camera preview (laptop webcam) in a mobile-like layout
- Click "Scan" to send a snapshot to the backend (mock analyze)
- See an overlay with a landmark name + placeholder info
- Click "Add to Passport" to save a card locally (in your browser)

## Project Structure

```
wanderlens/
├─ web/                 # Static frontend (HTML/CSS/JS)
│  ├─ index.html
│  ├─ style.css
│  └─ script.js
├─ server/              # Minimal Flask backend
│  ├─ app.py
│  └─ requirements.txt
├─ .env.example         # Placeholder for API keys (copy to .env)
├─ .gitignore
└─ README.md
```

## Backend API (Dev / Mock)

- `POST /analyze`
  - Body: `{ "image": "data:image/png;base64,..." }`
  - Returns: `{ "landmark": "Demo Landmark", "confidence": 0.99, "info": "Placeholder fun fact." }`

Notes:

- This is a mock for hackathon speed. You can swap in Google Cloud Vision (Landmark Detection) and Wikipedia summary later.
- CORS is enabled for local development.

## Environment Variables

Copy `.env.example` to `.env` (in project root) and fill in as you add real APIs.

Use a single key for both OCR (Vision) and Translate:

```
GOOGLE_TRANSLATE_API_KEY=your_key_here
```

## Future Upgrades (Post-Demo)

- Replace mock `/analyze` with Google Cloud Vision Landmark Detection
- Add `/info?name=...` that queries Wikipedia summary API
- Add OCR + Translate endpoints for sign translation
- Persist the Digital Passport to Firebase or a database

## GitHub Setup (Local -> Remote)

After files exist and you can run the app locally:

```bash
git init
git add .
git commit -m "chore: initial scaffold for WanderLens demo"

# Create a new repo on GitHub (via site or gh CLI). Then:
git remote add origin https://github.com/<your-username>/wanderlens.git
git branch -M main
git push -u origin main
```

## License

MIT
