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
        raisons.append(f"Rang : {rank_h}e vs {rank_a}e")
    raisons.append(f"xG : {xg_h:.2f} (Dom) - {xg_a:.2f} (Ext)")

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

def analyser_evenement(ev):
    try:
        tournament = ev.get('tournament', {})
        category = tournament.get('category', {})
        league_title = f"{category.get('name', '')} - {tournament.get('name', '')}".strip(" - ")
        
        home_team = ev.get('homeTeam', {}).get('name', '')
        away_team = ev.get('awayTeam', {}).get('name', '')
        
        if not home_team or not away_team:
            return None, None

        rank_h = ev.get('homeTeam', {}).get('ranking', 8) or 8
        rank_a = ev.get('awayTeam', {}).get('ranking', 8) or 8

        xg_h = round(1.2 + (15 - rank_h) * 0.05, 2)
        xg_a = round(1.0 + (15 - rank_a) * 0.05, 2)

        start_ts = ev.get('startTimestamp')
        heure_str = datetime.utcfromtimestamp(start_ts).strftime("%d/%m à %H:%M GMT") if start_ts else "Aujourd'hui"

        prono = determiner_pronostic(home_team, away_team, xg_h, xg_a, rank_h, rank_a)
        status_type = ev.get('status', {}).get('type', '')
        
        match_item = {
            'league': league_title if league_title else "Football",
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
            return match_item, 'live'
        else:
            return match_item, 'upcoming'
    except Exception:
        return None, None

@app.route("/")
def index():
    live_matches = []
    upcoming_matches = []
    debug_msg = ""

    if not RAPIDAPI_KEY:
        debug_msg = "Clé API non trouvée dans les variables d'environnement."
    else:
        # Test direct sur l'endpoint des matchs en direct et programmés
        urls = [
            f"https://{RAPIDAPI_HOST}/api/v1/sport/football/events/live",
            f"https://{RAPIDAPI_HOST}/api/v1/sport/football/scheduled-events/{datetime.utcnow().strftime('%Y-%m-%d')}"
        ]
        
        for url in urls:
            try:
                res = requests.get(url, headers=HEADERS, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    events = data.get('events', [])
                    for ev in events:
                        item, m_type = analyser_evenement(ev)
                        if item:
                            if m_type == 'live':
                                live_matches.append(item)
                            else:
                                upcoming_matches.append(item)
                else:
                    debug_msg += f" HTTP {res.status_code} sur {url}."
            except Exception as e:
                debug_msg += f" Erreur: {str(e)}."

    # Déduplication
    unique_upcoming = list({m['teams']: m for m in upcoming_matches}.values())
    unique_live = list({m['teams']: m for m in live_matches}.values())

    return render_template(
        "index.html", 
        live=unique_live, 
        upcoming=unique_upcoming, 
        combines={},
        debug=debug_msg
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
