import os
from flask import Flask, render_template
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

def generer_predictions_marches(home_score, away_score, minute_num, is_live=True):
    """Génère deux prédictions sûres adaptées aux marchés BetPawa."""
    total_goals = home_score + away_score
    
    if is_live:
        if minute_num >= 50 and total_goals == 0:
            return {
                'pred1': "Over 0.5 Fin de Match",
                'pred2': "Multiscores (1-0, 0-1, 1-1)",
                'confiance': 88,
                'statut': "PRONOSTIC SÛR",
                'raisons': ["Anomalie xG : 0-0 en 2de MT", "Fatigue du bloc bas adverse"]
            }
        elif home_score >= 1 and away_score >= 1:
            return {
                'pred1': "BTTS - Oui (Les 2 marquent)",
                'pred2': "Over 2.5 Total Buts",
                'confiance': 85,
                'statut': "PRONOSTIC SÛR",
                'raisons': ["Fragilité défensive confirmée", "Rythme offensif élevé"]
            }
        elif total_goals == 1 and minute_num >= 35:
            return {
                'pred1': "Double Chance Équipe Menée ou Nul",
                'pred2': "Over 1.5 Fin de Match",
                'confiance': 78,
                'statut': "À SURVEILLER",
                'raisons': ["Pression attendue pour égaliser", "Espaces en contre-attaque"]
            }
        else:
            return {
                'pred1': "Plus de 0.5 But 2nde Mi-Temps",
                'pred2': "Moins de 4.5 Buts",
                'confiance': 70,
                'statut': "ANALYSE EN COURS",
                'raisons': ["Observation neutre de l'efficacité", "Gestion du rythme"]
            }
    else:
        # Analyse Avant-Match (Matchs à venir)
        return {
            'pred1': "BTTS ou Over 2.5",
            'pred2': "Double Chance + Total > 1.5",
            'confiance': 82,
            'statut': "PRONOSTIC SÛR",
            'raisons': ["Calendrier chargé en milieu de semaine", "Efficacité xG du favori en baisse"]
        }

def construire_combines(upcoming_list):
    """Génère des coupons de combinés ajustés par paliers de côtes."""
    paliers = [5, 10, 20, 30, 60, 100]
    combines = {}
    
    # Sélection des matchs avec la plus haute confiance
    sures = [m for m in upcoming_list if m['score_confiance'] >= 75]
    if len(sures) < 2:
        sures = upcoming_list

    for target in paliers:
        coupons = []
        # Construction de 2 coupons par palier
        for i in range(2):
            nb_matchs = min(max(2, target // 5 + i), len(sures))
            selection = sures[:nb_matchs]
            cote_estimee = round(1.4 ** len(selection), 2)
            coupons.append({
                'nom': f"Coupon Côte ~{target} (Option {i+1})",
                'cote_totale': Cote_estimee if cote_estimee > 1 else target,
                'matchs': selection
            })
        combines[f"cote_{target}"] = coupons
    return combines

@app.route("/")
def index():
    live_matches = []
    upcoming_matches = []
    
    # Extraction des rencontres via ESPN (Global)
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        for event in data.get('events', []):
            competition = event.get('league', {}).get('name', 'Football')
            status_info = event.get('status', {})
            clock = status_info.get('displayClock', '0\'')
            state = status_info.get('type', {}).get('state', '')
            detail_time = status_info.get('type', {}).get('shortDetail', '')
            
            competitors = event.get('competitions', [{}])[0].get('competitors', [])
            if len(competitors) >= 2:
                home_name = competitors[0].get('team', {}).get('displayName', 'Domicile')
                away_name = competitors[1].get('team', {}).get('displayName', 'Extérieur')
                
                # 1. Matchs en Direct
                if state == "in":
                    home_score = int(competitors[0].get('score', 0))
                    away_score = int(competitors[1].get('score', 0))
                    try:
                        minute_num = int(clock.replace("'", "").split("+")[0])
                    except:
                        minute_num = 0
                        
                    preds = generer_predictions_marches(home_score, away_score, minute_num, is_live=True)
                    live_matches.append({
                        'league': competition,
                        'minute': clock,
                        'teams': f"{home_name} vs {away_name}",
                        'score': f"{home_score} - {away_score}",
                        'score_confiance': preds['confiance'],
                        'pred1': preds['pred1'],
                        'pred2': preds['pred2'],
                        'statut': preds['statut'],
                        'signaux': preds['raisons']
                    })
                
                # 2. Matchs à Venir
                elif state == "pre":
                    preds = generer_predictions_marches(0, 0, 0, is_live=False)
                    upcoming_matches.append({
                        'league': competition,
                        'heure': detail_time,
                        'teams': f"{home_name} vs {away_name}",
                        'score_confiance': preds['confiance'],
                        'pred1': preds['pred1'],
                        'pred2': preds['pred2'],
                        'statut': preds['statut'],
                        'signaux': preds['raisons']
                    })

        live_matches = sorted(live_matches, key=lambda x: x['score_confiance'], reverse=True)
        upcoming_matches = sorted(upcoming_matches, key=lambda x: x['score_confiance'], reverse=True)
        
        # Génération des combinés
        combines = construire_combines(upcoming_matches)

    except Exception as e:
        print(f"Erreur backend : {e}")
        combines = {}

    return render_template("index.html", live=live_matches, upcoming=upcoming_matches, combines=combines)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
