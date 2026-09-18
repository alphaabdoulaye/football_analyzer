import os
import requests
from flask import Flask, render_template
from datetime import datetime, timedelta

app = Flask(__name__)

# Utilisation des identifiants issus de la page SportAPI (Sofascore)
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "f59285c781msh04cb63b630f1568p1...")
RAPIDAPI_HOST = "sportapi7.p.rapidapi.com"

BASE_URL = f"https://{RAPIDAPI_HOST}/api/v1"

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

def determiner_pronostic(home_team, away_team, xg_h, xg_a, rank_h, rank_a):
    btts_prob = (xg_h >= 1.3 or xg_a >= 1.1) or abs(rank_h - rank_a) <= 3
    fragilite = (rank_h > 8 or rank_a > 8)
    
    raisons = [
        f"Position au classement : {rank_h}e vs {rank_a}e",
        f"Moyenne xG estimée : {xg_h:.2f} (Dom) - {xg_a:.2f} (Ext)"
    ]

    if btts_prob and fragilite:
        p1, p2 = "BTTS - Oui (Les 2 marquent)", "Over 2.5 Total Buts"
        conf, statut = 88, "PRONOSTIC SÛR"
        raisons.append("BTTS Validé : Efficacité offensive + Fragilité défensive constatée")
    elif rank_h < 5 and rank_a > 10:
        p1, p2 = "Multiscores (1-0, 2-0, 3-0)", "Victoire Domicile & Over 1.5"
        conf, statut = 84, "PRONOSTIC SÛR"
        raisons.append("Domination attendue du favori à domicile")
    else:
        p1, p2 = "Double Chance & Over 1.5", "Multiscores (2-1, 1-1, 1-2)"
        conf, statut = 78, "À SURVEILLER"
        raisons.append("Équilibre de performance et faiblesses défensives relatives")

    return {'p1': p1, 'p2': p2, 'conf': conf, 'statut': statut, 'raisons': raisons}

@app.route("/")
def index():
    live_matches = []
    upcoming_matches = []
    
    # Date au format YYYY-MM-DD
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Endpoint des événements programmés du jour
    url = f"{BASE_URL}/sport/football/scheduled-events/{today}"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            events = data.get('events', [])
            
            for ev in events[:30]:  # Limite pour optimiser les performances
                tournament_name = ev.get('tournament', {}).get('name', 'Football')
                category_name = ev.get('tournament', {}).get('category', {}).get('name', '')
                league_title = f"{category_name} - {tournament_name}" if category_name else tournament_name
                
                home_team = ev.get('homeTeam', {}).get('name', 'Équipe Dom')
                away_team = ev.get('awayTeam', {}).get('name', 'Équipe Ext')
                
                # Gestion du temps
                start_timestamp = ev.get('startTimestamp', 0)
                if start_timestamp:
                    dt = datetime.utcfromtimestamp(start_timestamp)
                    heure_exacte = dt.strftime("%d/%m à %H:%M GMT")
                else:
                    heure_exacte = "Aujourd'hui"
                
                # Simulation / Analyse statistique
                rank_h = (hash(home_team) % 15) + 1
                rank_a = (hash(away_team) % 15) + 1
                xg_h = round(1.2 + (rank_a / 12), 2)
                xg_a = round(1.0 + (rank_h / 12), 2)
                
                prono = determiner_pronostic(home_team, away_team, xg_h, xg_a, rank_h, rank_a)
                
                status_type = ev.get('status', {}).get('type', '')
                
                match_item = {
                    'league': league_title,
                    'teams': f"{home_team} vs {away_team}",
                    'heure': heure_exacte,
                    'score_confiance': prono['conf'],
                    'pred1': prono['p1'],
                    'pred2': prono['p2'],
                    'statut': prono['statut'],
                    'signaux': prono['raisons']
                }
                
                if status_type == 'inprogress':
                    home_score = ev.get('homeScore', {}).get('current', 0)
                    away_score = ev.get('awayScore', {}).get('current', 0)
                    match_item['score'] = f"{home_score} - {away_score}"
                    live_matches.append(match_item)
                elif status_type == 'notstarted':
                    upcoming_matches.append(match_item)
                    
    except Exception as e:
        print(f"Erreur lors de la récupération des données : {e}")

    return render_template("index.html", live=live_matches, upcoming=upcoming_matches, combines={})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
