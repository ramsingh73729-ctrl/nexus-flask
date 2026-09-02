# NEXUS — Flask gaming platform

An immersive gaming platform landing page built with Python/Flask and a Motion-powered frontend.

## Run locally on macOS

```bash
cd nexus-flask
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Included

- Retro-futuristic neon design on a dark background
- CSS-built 3D hero core and floating scene
- Motion entrance, scroll, carousel, and ambient animations
- Interactive game showcase carousel with autoplay and controls
- Community, events, and download sections
- Trailer modal with Escape-key support
- Flask contact and download API endpoints
- JSON health check and games endpoint

Motion is loaded in `static/js/main.js` using its browser ESM build. Flask is the backend and template renderer.
