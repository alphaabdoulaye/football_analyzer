import os
import requests
from datetime import datetime
from flask import Flask, render_template

app = Flask(__name__)

# Cache en mémoire pour éviter de surcharger les requêtes de classement
CACHE_STANDINGS = {}

def obtenir_rang_et_xg(team_name, league_id):
    """
    Récupère le vrai rang et calcule l'xG basé sur la moyenne de buts
    """
    if not league_id:
        return 8, 1.25
        
    if league_id not in CACHE_STANDINGS:
        try:
            url = f"https://site.api.espn.com/apis/v2/sports/soccer/{league_id}/standings"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                standings = {}
                children = data.get('children', [])
                entries = []
                if children:
                    entries = children[0].get('standings', {}).get('entries', [])
                else:
                    entries = data.get('standings', {}).get('entries', [])

                for idx, entry in enumerate(entries, 1):
                    t_name = entry.get('team', {}).get('displayName', '').lower()
                    stats = {s.get('name'): s.get('value', 0) for s in entry.get('stats', [])}
                    
                    matches = stats.get('gamesPlayed', 1) or 1
                    goals_for = stats.get('pointsFor', 0) or stats.get('goalsFor', 0)
                    xg_est = round(max(0.8, min(2.8, goals_for / matches)), 2)
                    
                    standings[t_name] = {'rank': idx, 'xg': xg_est}
                
                CACHE_STANDINGS[league_id] = standings
            else:
                CACHE_STANDINGS[league_id] = {}
        except Exception:
            CACHE_STANDINGS[league_id] = {}

    league_data = CACHE_STANDINGS.get(league_id, {})
    team_clean = team_name.lower()
    
    # Recherche exacte ou partielle de l'équipe
    for key, val in league_data.items():
        if key in team_clean or team_clean in key:
            return val['rank'], val['xg']
            
    return 8, 1.25

def determiner_pronostic(home_team, away_team, xg_h, xg_a, rank_h, rank_a):
    btts_prob = (xg_h >= 1.3 or xg_a >= 1.1) or abs(rank_h - rank_a) <= 3
    fragilite = (rank_h > 8 or rank_a > 8)
    
    raisons = []
    if rank_h > 0 and rank_a > 0:
        raisons.append(f"Rang réel : {rank_h}e vs {rank_a}e")
    raisons.append(f"xG réels/est. : {xg_h:.2f} (Dom) - {xg_a:.2f} (Ext)")

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

def recuperer_matchs_du_jour():
    live_matches = []
    upcoming_matches = []
    
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            events = data.get('events', [])
            
            for ev in events:
                league_info = ev.get('league', {})
                league_name = league_info.get('name', 'Football')
                league_id = league_info.get('slug', '')
                
                status = ev.get('status', {}).get('type', {}).get('state', '')
                
                competitors = ev.get('competitions', [{}])[0].get('competitors', [])
                if len(competitors) < 2:
                    continue
                
                home_team, away_team = "", ""
                score_h, score_a = "0", "0"
                
                for c in competitors:
                    if c.get('homeAway') == 'home':
                        home_team = c.get('team', {}).get('displayName', '')
                        score_h = c.get('score', '0')
                    else:
                        away_team = c.get('team', {}).get('displayName', '')
                        score_a = c.get('score', '0')
                
                if not home_team or not away_team:
                    continue
                
                # Récupération des vrais rangs et vrais xG calculés sur la saison
                rank_h, xg_h = obtenir_rang_et_xg(home_team, league_id)
                rank_a, xg_a = obtenir_rang_et_xg(away_team, league_id)
                
                date_str = ev.get('date', '')
                heure_display = "Aujourd'hui"
                if date_str:
                    try:
                        dt = datetime.strptime(date_str[:16], "%Y-%m-%dT%H:%M")
                        heure_display = dt.strftime("%d/%m à %H:%M GMT")
                    except:
                        pass
                
                prono = determiner_pronostic(home_team, away_team, xg_h, xg_a, rank_h, rank_a)
                
                match_item = {
                    'league': league_name,
                    'teams': f"{home_team} vs {away_team}",
                    'heure': heure_display,
                    'score_confiance': prono['conf'],
                    'pred1': prono['p1'],
                    'pred2': prono['p2'],
                    'statut': prono['statut'],
                    'signaux': prono['raisons']
                }
                
                if status == 'in':
                    match_item['score'] = f"{score_h} - {score_a}"
                    live_matches.append(match_item)
                else:
                    upcoming_matches.append(match_item)
                    
    except Exception as e:
        print(f"Erreur : {e}")
        
    return live_matches, upcoming_matches

@app.route("/")
def index():
    live, upcoming = recuperer_matchs_du_jour()
    
    upcoming = sorted(upcoming, key=lambda x: x['score_confiance'], reverse=True)
    live = sorted(live, key=lambda x: x['score_confiance'], reverse=True)
    
    return render_template("index.html", live=live, upcoming=upcoming, combines={})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
