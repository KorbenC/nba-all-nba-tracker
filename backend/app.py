"""
Thin backend for NBA All-NBA Tracker.
Uses nba_api (NBA.com) for leaders data; no API key required.
"""
import os
import time
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# In-memory cache: key -> (response_dict, expiry_time)
_LEADERS_CACHE = {}
CACHE_TTL_SECONDS = 10 * 60  # 10 minutes

# Previous 2 seasons' All-NBA selections (so we always show them even if out of the running this year)
# 2023-24: NBA.com 2023-24 All-NBA Teams
# 2024-25: NBA.com 2024-25 All-NBA Teams
_ALL_NBA_NAMES = (
    "Nikola Jokić", "Shai Gilgeous-Alexander", "Luka Dončić", "Giannis Antetokounmpo", "Jayson Tatum",
    "Jalen Brunson", "Anthony Edwards", "Kevin Durant", "Kawhi Leonard", "Anthony Davis",
    "LeBron James", "Stephen Curry", "Domantas Sabonis", "Tyrese Haliburton", "Devin Booker",
    "Donovan Mitchell", "Evan Mobley", "Cade Cunningham", "James Harden", "Karl-Anthony Towns", "Jalen Williams",
)


def _normalize_name(name):
    """Strip and collapse whitespace so API variants match our list."""
    if not name or not isinstance(name, str):
        return ""
    return " ".join(str(name).strip().split())


# Set of normalized names for fast lookup (handles "Jayson  Tatum" etc.)
ALL_NBA_PREVIOUS_2_SEASONS = frozenset(_normalize_name(n) for n in _ALL_NBA_NAMES)


def season_end_year_to_nba(season_end_year: int) -> str:
    """Convert season end year (e.g. 2025) to NBA API format (e.g. '2024-25')."""
    start = season_end_year - 1
    end_short = str(season_end_year)[-2:]
    return f"{start}-{end_short}"


def current_season_end_year() -> int:
    """Current NBA season end year (Oct → next calendar year)."""
    from datetime import datetime
    now = datetime.now()
    return now.year + 1 if now.month >= 10 else now.year


def _get_position_map(season_str):
    """Fetch PLAYER_ID -> POSITION from PlayerIndex for the season."""
    try:
        from nba_api.stats.endpoints import playerindex
        idx = playerindex.PlayerIndex(season=season_str)
        pdf = idx.get_data_frames()[0]
        if pdf is None or pdf.empty or "PERSON_ID" not in pdf.columns or "POSITION" not in pdf.columns:
            return {}
        return {str(k): str(v).strip() for k, v in pdf.set_index("PERSON_ID")["POSITION"].items()}
    except Exception:
        return {}


def _row_to_player(row, team_games_played_map, position_map=None):
    position_map = position_map or {}
    gp = int(row.get("GP", 0) or 0)
    team_abbr = str(row.get("TEAM_ABBREVIATION", "") or "")
    team_gp = team_games_played_map.get(team_abbr, gp)
    missed = max(0, team_gp - gp)
    pts = float(row.get("PTS", 0) or 0)
    reb = float(row.get("REB", 0) or 0)
    ast = float(row.get("AST", 0) or 0)
    ppg = round(pts / gp, 1) if gp > 0 else 0.0
    rpg = round(reb / gp, 1) if gp > 0 else 0.0
    apg = round(ast / gp, 1) if gp > 0 else 0.0
    pid = str(row.get("PLAYER_ID", ""))
    return {
        "player_id": pid,
        "name": str(row.get("PLAYER_NAME", "")),
        "team": team_abbr,
        "gp": gp,
        "team_games_played": team_gp,
        "missed": missed,
        "ppg": ppg,
        "rpg": rpg,
        "apg": apg,
        "position": position_map.get(pid, "").strip() or "",
    }


@app.route("/api/leaders")
def leaders():
    """Return top players by stat (pts, reb, ast, or composite). Optional position. Cached 10 min."""
    try:
        raw_season = request.args.get("season")
        if raw_season is not None and str(raw_season).strip() != "":
            season_param = int(raw_season)
            if season_param < 2000 or season_param > 2100:
                season_param = current_season_end_year()
        else:
            season_param = current_season_end_year()
        season_str = season_end_year_to_nba(season_param)
        raw_limit = request.args.get("limit")
        limit = 24
        if raw_limit is not None and str(raw_limit).strip() != "":
            try:
                limit = min(max(1, int(raw_limit)), 50)
            except (TypeError, ValueError):
                pass
        stat = (request.args.get("stat") or "pts").strip().lower()
        if stat not in ("pts", "reb", "ast", "composite"):
            stat = "pts"
    except (TypeError, ValueError):
        season_param = current_season_end_year()
        season_str = season_end_year_to_nba(season_param)
        limit = 24
        stat = "pts"

    cache_key = f"{season_str}:{limit}:{stat}"
    now = time.time()
    if cache_key in _LEADERS_CACHE:
        cached_resp, expiry = _LEADERS_CACHE[cache_key]
        if now < expiry:
            return jsonify(cached_resp)

    try:
        from nba_api.stats.endpoints import leaguedashplayerstats

        dash = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season_str,
            season_type_all_star="Regular Season",
        )
        df = dash.league_dash_player_stats.get_data_frame()
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    if df is None or df.empty:
        out = {"data": [], "season_games_played": 0, "games_remaining": 82, "season": season_str}
        return jsonify(out)

    # Per-team games played (max GP on that team) — "missed" is team_gp - player_gp
    team_games_played_map = df.groupby("TEAM_ABBREVIATION")["GP"].max().to_dict()
    season_games_played = int(df["GP"].max()) if "GP" in df.columns else 0
    games_remaining = max(0, 82 - season_games_played)

    # Position map from PlayerIndex (PLAYER_ID in dash is PERSON_ID in index)
    position_map = _get_position_map(season_str)

    full_df = df.copy()
    if stat == "composite":
        top_pts = set(df.nlargest(limit, "PTS")["PLAYER_ID"].astype(str))
        top_reb = set(df.nlargest(limit, "REB")["PLAYER_ID"].astype(str))
        top_ast = set(df.nlargest(limit, "AST")["PLAYER_ID"].astype(str))
        composite_ids = top_pts | top_reb | top_ast
        df = df[df["PLAYER_ID"].astype(str).isin(composite_ids)].copy()
        df = df.sort_values("PTS", ascending=False)
    else:
        sort_col = {"pts": "PTS", "reb": "REB", "ast": "AST"}[stat]
        df = df.sort_values(sort_col, ascending=False).head(limit)

    # Add previous 2 seasons' All-NBA selections not already in the list (normalize names for matching)
    in_list = set(df["PLAYER_ID"].astype(str))
    full_df_normalized = full_df.copy()
    full_df_normalized["_name_norm"] = full_df["PLAYER_NAME"].astype(str).apply(_normalize_name)
    notable_rows = full_df[
        full_df_normalized["_name_norm"].isin(ALL_NBA_PREVIOUS_2_SEASONS)
        & ~full_df["PLAYER_ID"].astype(str).isin(in_list)
    ]
    if not notable_rows.empty:
        df = pd.concat([df, notable_rows], ignore_index=True)
        sort_col = {"pts": "PTS", "reb": "REB", "ast": "AST"}.get(stat, "PTS")
        df = df.sort_values(sort_col, ascending=False)

    rows = [_row_to_player(row, team_games_played_map, position_map) for _, row in df.iterrows()]

    out = {
        "data": rows,
        "season_games_played": season_games_played,
        "games_remaining": games_remaining,
        "season": season_str,
        "stat": stat,
    }
    _LEADERS_CACHE[cache_key] = (out, now + CACHE_TTL_SECONDS)
    return jsonify(out)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
