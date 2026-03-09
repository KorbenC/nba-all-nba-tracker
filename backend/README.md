# Backend (Python)

Thin Flask API that uses [nba_api](https://github.com/swar/nba_api) to serve league leaders (points, games played) from NBA.com. No API key required.

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
python3 -m pip install -r requirements.txt
```
(If `pip` isn't in your PATH, use `python3 -m pip`.)

## Run

```bash
python app.py
```

Server runs at **http://localhost:5001** (port 5001 to avoid conflict with macOS AirPlay on 5000). The frontend expects this URL by default; override with `window.BACKEND_URL` in `config.js` if needed.

## Endpoints

- `GET /api/leaders?season=2025` — Top players by points for that season (end year). Returns `{ "data": [ { "name", "team", "gp", "ppg" }, ... ] }`.
- `GET /api/health` — Health check.
