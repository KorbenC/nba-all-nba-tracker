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

## Project layout

- `index.html` — Single-page app (chart only).
- `config.js` — Optional `BACKEND_URL` (create from `config.example.js` if needed).
- `backend/` — Flask app using nba_api; see `backend/README.md`.
