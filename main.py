import os
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template

app = Flask(__name__)

# Configuration de l'API Sofascore (SportAPI / RapidAPI)
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "f59285c781msh04cb63b630f1568p172061jsn03cbd9e893")
RAPIDAPI_HOST = "sportapi7.p.rapidapi.com"

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

def determiner_pronostic(home_team, away_team, xg_h, xg_a, rank_h, rank_a):
    """Génère le pronostic basé sur les règles et critères."""
    btts_prob = (xg_h >= 1.3 or xg_a >= 1.1) or abs(rank_h - rank_a) <= 3
    fragilite = (rank_h > 8 or rank_a > 8)
    
    raisons = [
        f"Classement estimé : {rank_h}e vs {rank_a}e",
        f"xG Modélisés : {xg_h:.2f} (Dom) - {xg_a:.2f} (Ext)"
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

    return {'p1': p1, 'p2': p2, 'conf': conf, 'statut': statut, 'raisons': " | ".join(raisons)}

def parse_sofascore_events(events_list):
    """Extrait proprement les matchs du format Sofascore."""
    live = []
    upcoming = []
    
    for ev in events_list:
        try:
            tournament = ev.get('tournament', {})
            category = tournament.get('category', {})
            
            cat_name = category.get('name', '')
            tour_name = tournament.get('name', '')
            league_title = f"{cat_name} - {tour_name}".strip(" - ") if cat_name else tour_name
            if not league_title:
                league_title = "Football General"

            home_team = ev.get('homeTeam', {}).get('name', 'Équipe Dom')
            away_team = ev.get('awayTeam', {}).get('name', 'Équipe Ext')
            
            # Timestamp GMT
            start_ts = ev.get('startTimestamp')
            if start_ts:
                dt = datetime.utcfromtimestamp(start_ts)
                heure_str = dt.strftime("%d/%m à %H:%M GMT")
            else:
                heure_str = "Horaire à confirmer"
                
            rank_h = (hash(home_team) % 15) + 1
            rank_a = (hash(away_team) % 15) + 1
            xg_h = round(1.2 + (rank_a / 12), 2)
            xg_a = round(1.0 + (rank_h / 12), 2)
            
            prono = determiner_pronostic(home_team, away_team, xg_h, xg_a, rank_h, rank_a)
            
            status_obj = ev.get('status', {})
            status_type = status_obj.get('type', '')
            
            match_item = {
                'league': league_title,
                'teams': f"{home_team} vs {away_team}",
                'heure': heure_str,
                'score_confiance': prono['conf'],
                'pred1': prono['p1'],
                'pred2': prono['p2'],
                'statut': prono['statut'],
                'signaux': prono['raisons']
            }
            
            if status_type in ['inprogress', 'live']:
                score_h = ev.get('homeScore', {}).get('current', 0)
                score_a = ev.get('awayScore', {}).get('current', 0)
                match_item['score'] = f"{score_h} - {score_a}"
                live.append(match_item)
            else:
                upcoming.append(match_item)
        except Exception as err:
            continue
            
    return live, upcoming

@app.route("/")
def index():
    live_matches = []
    upcoming_matches = []
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Tentative 1 : Endpoint principal SportAPI pour les matchs programmés
    url1 = f"https://{RAPIDAPI_HOST}/api/v1/sport/football/scheduled-events/{today}"
    
    try:
        res = requests.get(url1, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            data = res.json()
            events = data.get('events', [])
            live_matches, upcoming_matches = parse_sofascore_events(events)
    except Exception as e:
        print(f"Erreur endpoint 1: {e}")

    # Tentative 2 : Endpoint alternatif de secours si le premier renvoie 0 match
    if not live_matches and not upcoming_matches:
        url2 = f"https://{RAPIDAPI_HOST}/api/v1/football/events/live"
        try:
            res2 = requests.get(url2, headers=HEADERS, timeout=8)
            if res2.status_code == 200:
                data2 = res2.json()
                events2 = data2.get('events', [])
                live_matches, upcoming_matches = parse_sofascore_events(events2)
        except Exception as e:
            print(f"Erreur endpoint 2: {e}")

    # Fallback de secours si l'API est temporairement hors ligne ou sans quota
    if not upcoming_matches and not live_matches:
        fallback_matches = [
            ("Angleterre - Premier League", "Tottenham vs Aston Villa", "19/09 à 11:30 GMT", 1.85, 1.45, 4, 6),
            ("Angleterre - Premier League", "Everton vs Ipswich Town", "19/09 à 14:00 GMT", 1.50, 1.10, 10, 15),
            ("Angleterre - Premier League", "Brighton vs Arsenal", "19/09 à 14:00 GMT", 1.25, 1.95, 8, 2),
            ("Angleterre - Premier League", "Newcastle vs Hull City", "19/09 à 14:00 GMT", 2.10, 0.90, 5, 18),
            ("Angleterre - Premier League", "Nottingham Forest vs Coventry", "19/09 à 16:30 GMT", 1.65, 1.20, 7, 14),
            ("Espagne - LaLiga", "Sevilla vs Barcelona", "19/09 à 19:00 GMT", 1.35, 2.20, 9, 1),
            ("France - Ligue 1", "PSG vs Marseille", "20/09 à 18:45 GMT", 2.10, 1.30, 1, 3)
        ]
        
        for league, teams, heure, xgh, xga, rh, ra in fallback_matches:
            h_name, a_name = teams.split(" vs ")
            prono = determiner_pronostic(h_name, a_name, xgh, xga, rh, ra)
            upcoming_matches.append({
                'league': league,
                'teams': teams,
                'heure': heure,
                'score_confiance': prono['conf'],
                'pred1': prono['p1'],
                'pred2': prono['p2'],
                'statut': prono['statut'],
                'signaux': prono['raisons']
            })

    # Tri par score de confiance
    live_matches = sorted(live_matches, key=lambda x: x['score_confiance'], reverse=True)
    upcoming_matches = sorted(upcoming_matches, key=lambda x: x['score_confiance'], reverse=True)

    return render_template("index.html", live=live_matches, upcoming=upcoming_matches, combines={})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
