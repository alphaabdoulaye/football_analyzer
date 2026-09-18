from flask import Flask, render_template

app = Flask(__name__)

def analyser_match(data):
    pre = data.get("pre_match", {})
    live = data.get("live_stats", {})
    minute = data.get("minute", 0)
    score_home = data.get("score", {}).get("home", 0)
    score_away = data.get("score", {}).get("away", 0)
    total_goals = score_home + score_away
    score_confiance = 0
    signaux = []
    
    # Critères de pré-match (BTTS, calendrier)
    if pre.get("btts_historique"):
        score_confiance += 15
        signaux.append("Profil BTTS historique fort")
    if pre.get("calendrier_charge"):
        score_confiance += 15
        signaux.append("Calendrier chargé / Fatigue")
    
    # Critères live (xG, tirs dans la surface)
    total_xg = live.get("xg_home", 0.0) + live.get("xg_away", 0.0)
    if minute >= 50 and total_goals == 0 and total_xg >= 1.40:
        score_confiance += 35
        signaux.append(f"Anomalie xG : {total_xg:.2f} xG à la {minute}' sans but")
    
    tirs_surface = live.get("tirs_surface_home", 0) + live.get("tirs_surface_away", 0)
    if tirs_surface >= 8:
        score_confiance += 20
        signaux.append(f"Pression extrême ({tirs_surface} tirs surface)")
    
    score_confiance = min(score_confiance, 98)
    
    # Prise de décision selon l'indice de confiance
    if score_confiance >= 80:
        decision = "CONFIRMÉ : Over 0.5 / Prochain But Imminent"
    elif score_confiance >= 60:
        decision = "SIGNAL FORT : Tendance BTTS / Over 1.5"
    elif score_confiance >= 40:
        decision = "SURVEILLANCE : Match sous pression"
    else:
        decision = "NEUTRE : Rythme insuffisant"
    
    return {
        "teams": f"{data['teams']['home']} vs {data['teams']['away']}",
        "league": data.get("league", "Ligue Inconnue"),
        "minute": minute,
        "score": f"{score_home} - {score_away}",
        "score_confiance": score_confiance,
        "decision": decision,
        "signaux": signaux
    }

# Données de test
MATCHS_SIMULES = [
    {
        "match_id": 201, "league": "UEFA Champions League",
        "teams": {"home": "Real Madrid", "away": "Manchester City"},
        "minute": 67, "score": {"home": 0, "away": 0},
        "pre_match": {"btts_historique": True, "calendrier_charge": True},
        "live_stats": {"xg_home": 1.55, "xg_away": 0.92, "tirs_surface_home": 6, "tirs_surface_away": 4}
    },
    {
        "match_id": 202, "league": "Premier League",
        "teams": {"home": "Arsenal", "away": "Liverpool"},
        "minute": 74, "score": {"home": 1, "away": 0},
        "pre_match": {"btts_historique": True, "calendrier_charge": True},
        "live_stats": {"xg_home": 1.10, "xg_away": 1.45, "tirs_surface_home": 4, "tirs_surface_away": 7}
    }
]

@app.route("/")
def home():
    analyses = sorted([analyser_match(m) for m in MATCHS_SIMULES], key=lambda x: x["score_confiance"], reverse=True)
    return render_template("index.html", results=analyses)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

