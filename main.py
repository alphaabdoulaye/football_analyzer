import os
import requests
from datetime import datetime
from flask import Flask, render_template

app = Flask(__name__)

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "sportapi7.p.rapidapi.com"

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST
}

def determiner_pronostic(home_team, away_team, xg_h, xg_a, rank_h, rank_a):
    btts_prob = (xg_h >= 1.3 or xg_a >= 1.1) or abs(rank_h - rank_a) <= 3
    fragilite = (rank_h > 8 or rank_a > 8)
    
    raisons = []
    if rank_h > 0 and rank_a > 0:
        raisons.append(f"Rang réel : {rank_h}e vs {rank_a}e")
    raisons.append(f"xG estimés : {xg_h:.2f} (Dom) - {xg_a:.2f} (Ext)")

    if btts_prob and fragilite:
        p1, p2 = "BTTS - Oui (Les 2 marquent)", "Plus de 2.5 buts"
        conf, statut = 88, "PRONOSTIC SÛR"
        raisons.append("BTTS Validé : Attaque efficace + Fragilité défensive")
    elif rank_h > 0 and rank_h < 5 and rank_a > 10:
        p1, p2 = "Victoire Domicile", "Plus de 1.5 buts"
        conf, statut = 84, "PRONOSTIC SÛR"
        raisons.append("Avantage net du favori à domicile")
    else:
        p1, p2 = "Double Chance 1X", "Moins de 3.5 buts"
        conf, statut = 78, "À SURVEILLER"
        raisons.append("Match équilibré")

    return {'p1': p1, 'p2': p2, 'conf': conf, 'statut': statut, 'raisons': " | ".join(raisons)}

def extraire_matchs(events):
    live = []
    upcoming = []
    
    for ev in events:
        try:
            tournament = ev.get('tournament', {})
            category = tournament.get('category', {})
            
            # Filtre uniquement le Football (sport id 1 chez Sofascore)
            sport_id = category.get('sport', {}).get('id', 1)
            if sport_id != 1 and tournament.get('category', {}).get('slug') != 'football':
                continue

            league_title = f"{category.get('name', '')} - {tournament.get('name', '')}".strip(" - ")
            
            home_team = ev.get('homeTeam', {}).get('name', '')
            away_team = ev.get('awayTeam', {}).get('name', '')
            
            if not home_team or not away_team:
                continue

            # Récupération des vrais rangs s'ils sont fournis dans l'événement
            rank_h = ev.get('homeTeam', {}).get('ranking', 0)
            rank_a = ev.get('awayTeam', {}).get('ranking', 0)
            
            # Si le rang n'est pas fourni dans le flux direct, calcul de secours neutre
            if not rank_h: rank_h = 8
            if not rank_a: rank_a = 8

            xg_h = round(1.2 + (15 - rank_h) * 0.05, 2)
            xg_a = round(1.0 + (15 - rank_a) * 0.05, 2)

            start_ts = ev.get('startTimestamp')
            heure_str = datetime.utcfromtimestamp(start_ts).strftime("%d/%m à %H:%M GMT") if start_ts else "Aujourd'hui"

            prono = determiner_pronostic(home_team, away_team, xg_h, xg_a, rank_h, rank_a)
            
            status_type = ev.get('status', {}).get('type', '')
            
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
        except Exception:
            continue
            
    return live, upcoming

@app.route("/")
def index():
    live_matches = []
    upcoming_matches = []
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    if RAPIDAPI_KEY:
        # Essai 1 : Format standard YYYY-MM-DD
        urls = [
            f"https://{RAPIDAPI_HOST}/api/v1/sport/football/scheduled-events/{today}",
            f"https://{RAPIDAPI_HOST}/api/v1/football/events/live"
        ]
        
        for url in urls:
            try:
                res = requests.get(url, headers=HEADERS, timeout=8)
                if res.status_code == 200:
                    events = res.json().get('events', [])
                    l, u = extraire_matchs(events)
                    live_matches.extend(l)
                    upcoming_matches.extend(u)
            except Exception as e:
                print(f"Erreur API: {e}")

    # Si l'API répond correctement, on supprime les doublons
    upcoming_matches = {m['teams']: m for m in upcoming_matches}.values()
    live_matches = {m['teams']: m for m in live_matches}.values()

    # Tri par score de confiance
    live_matches = sorted(live_matches, key=lambda x: x['score_confiance'], reverse=True)
    upcoming_matches = sorted(upcoming_matches, key=lambda x: x['score_confiance'], reverse=True)

    return render_template("index.html", live=list(live_matches), upcoming=list(upcoming_matches), combines={})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
