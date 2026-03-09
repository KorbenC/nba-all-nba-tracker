# NBA All-NBA Eligibility Tracker

Track top 24 players (All-Star caliber) and 65-game eligibility for All-NBA honors. Data comes from a local Python backend (NBA.com via [nba_api](https://github.com/swar/nba_api)). Eligibility is based on **games missed so far**: if a player has missed 18+ of the games played in the season, they can’t reach 65 and are ineligible.

## Quick start

1. **Start the backend**
   ```bash
   cd backend && python3 -m venv venv && source venv/bin/activate && python3 -m pip install -r requirements.txt && python3 app.py
   ```
   (On Windows use `venv\Scripts\activate` and run `python -m pip` / `python app.py`.)
   Backend runs at http://localhost:5001.

2. **Serve the frontend** (from project root)
   ```bash
   python3 -m http.server 8080
   ```
   Open http://localhost:8080.

## Deploy to Render (frontend + backend in one service)

1. Create a **Web Service**, connect your repo. Leave **Root Directory** blank (use repo root so the app can serve `index.html` and `config.js`).
2. **Build command:** `cd backend && pip install -r requirements.txt`
3. **Start command:** `cd backend && gunicorn app:app`
4. Deploy. The service URL serves the tracker UI at `/` and the API at `/api/leaders` and `/api/health`. Use **Health Check Path** `/api/health` if offered.
5. No need to set `BACKEND_URL` in `config.js` when the frontend is served from the same origin.

## Project layout

- `index.html` — Single-page app (chart only).
- `config.js` — Optional `BACKEND_URL` (create from `config.example.js` if needed).
- `backend/` — Flask app using nba_api; see `backend/README.md`.
