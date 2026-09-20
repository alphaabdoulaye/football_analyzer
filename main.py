import os
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Token API Football-Data
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "934b6fce2a73484791292a5d7318a83b")

# Codes des compétitions pour la version gratuite
LEAGUE_CODES = {
    "Ligue 1": "FL1",
    "Premier League": "PL",
    "La Liga": "PD",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "Champions League": "CL"
}

headers = {
    "X-Auth-Token": FOOTBALL_DATA_API_KEY
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_matches", methods=["POST"])
def get_matches():
    data = request.get_json() or {}
    league_name = data.get("league", "")
    
    code = LEAGUE_CODES.get(league_name, "PL")
    url = f"https://api.football-data.org/v4/competitions/{code}/matches?status=SCHEDULED"
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            matches_data = res.json().get("matches", [])
            matches = []
            for m in matches_data[:10]:
                matches.append({
                    "team_a": m["homeTeam"]["name"],
                    "team_b": m["awayTeam"]["name"],
                    "date": m["utcDate"]
                })
            return jsonify({"status": "success", "matches": matches})
        else:
            return jsonify({"status": "error", "message": f"Erreur API ({res.status_code})"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/analyze_match", methods=["POST"])
def analyze_match():
    data = request.get_json() or {}
    team_a = data.get("team_a", "")
    team_b = data.get("team_b", "")
    league_name = data.get("league", "")

    code = LEAGUE_CODES.get(league_name, "PL")
    url_standings = f"https://api.football-data.org/v4/competitions/{code}/standings"
    
    try:
        res = requests.get(url_standings, headers=headers, timeout=10)
        standings_info = "Données de classement non disponibles."
        
        if res.status_code == 200:
            tables = res.json().get("standings", [])
            if tables:
                table = tables[0].get("table", [])
                standings_lines = []
                for team in table:
                    t_name = team["team"]["name"]
                    pos = team["position"]
                    pts = team["points"]
                    played = team["playedGames"]
                    gf = team["goalsFor"]
                    ga = team["goalsAgainst"]
                    gd = team["goalDifference"]
                    form = team.get("form", "N/A")
                    
                    if team_a.lower() in t_name.lower() or team_b.lower() in t_name.lower():
                        standings_lines.append(
                            f"Pos {pos}: {t_name} | Pts: {pts} | J: {played} | BP: {gf} | BC: {ga} | Diff: {gd} | Forme: {form}"
                        )
                
                if standings_lines:
                    standings_info = "\n".join(standings_lines)
                else:
                    standings_info = "Équipes non trouvées dans le classement actuel."

        return jsonify({
            "status": "success",
            "match": f"{team_a} vs {team_b}",
            "analysis": {
                "standings_raw": standings_info,
                "recent_form_raw": "Détails de forme inclus dans le classement ci-dessus.",
                "h2h_raw": f"Match de la compétition {league_name}."
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
