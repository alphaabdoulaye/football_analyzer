import os
from flask import Flask, render_template
import requests

app = Flask(__name__)

def analyser_marche(home_score, away_score, minute_num, state):
    """Analyse le match et retourne le marché exact à jouer ainsi que le niveau de confiance."""
    total_goals = home_score + away_score
    
    # 1. Marché Over 0.5 (Matchs nuls 0-0 en 2nde mi-temps)
    if minute_num >= 55 and total_goals == 0:
        return {
            'marche': "OVER 0.5 (Prochain But)",
            'confiance': 85,
            'statut_surete': "MATCH SÛR",
            'raison': "0-0 après la 55' : probabilité très élevée d'au moins 1 but d'ici la fin."
        }
    
    # 2. Marché BTTS (Les deux équipes marquent)
    elif minute_num <= 65 and (home_score == 0 or away_score == 0) and total_goals == 1:
        return {
            'marche': "BTTS - OUI (Les 2 équipes marquent)",
            'confiance': 78,
            'statut_surete': "MATCH SÛR",
            'raison': "Score 1-0 ou 0-1 : forte pression de l'équipe menée pour égaliser."
        }
        
    # 3. Marché Over 2.5
    elif total_goals >= 2 and minute_num <= 50:
        return {
            'marche': "OVER 2.5 (Total Buts)",
            'confiance': 80,
            'statut_surete': "MATCH SÛR",
            'raison': "Rythme très offensif : au moins 2 buts inscrits en 1ère mi-temps."
        }

    # 4. Marché Opportunité modérée
    elif minute_num >= 35 and total_goals == 0:
        return {
            'marche': "OVER 0.5 Mi-Temps / Fin de match",
            'confiance': 68,
            'statut_surete': "À SURVEILLER",
            'raison': "Fin de 1ère mi-temps sans but, intensité à suivre."
        }

    # Par défaut
    return {
        'marche': "PAS DE MARCHÉ SÛR (Observer)",
        'confiance': 50,
        'statut_surete': "NE PAS JOUER",
        'raison': "Conditions statistiques non réunies pour un pari à forte confiance."
    }

@app.route("/")
def index():
    results = []
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        for event in data.get('events', []):
            competition = event.get('league', {}).get('name', 'Football')
            status_info = event.get('status', {})
            clock = status_info.get('displayClock', '0\'')
            state = status_info.get('type', {}).get('state', '')
            
            competitors = event.get('competitions', [{}])[0].get('competitors', [])
            if len(competitors) >= 2:
                home = competitors[0]
                away = competitors[1]
                
                home_name = home.get('team', {}).get('displayName', 'Domicile')
                away_name = away.get('team', {}).get('displayName', 'Extérieur')
                
                home_score = int(home.get('score', 0))
                away_score = int(away.get('score', 0))
                
                try:
                    minute_num = int(clock.replace("'", "").split("+")[0])
                except:
                    minute_num = 0

                if state == "in":
                    analyse = analyser_marche(home_score, away_score, minute_num, state)
                    
                    results.append({
                        'league': competition,
                        'minute': clock,
                        'teams': f"{home_name} vs {away_name}",
                        'score': f"{home_score} - {away_score}",
                        'score_confiance': analyse['confiance'],
                        'decision': f"{analyse['statut_surete']} : {analyse['marche']}",
                        'signaux': [
                            f"Marché conseillé : {analyse['marche']}",
                            f"Analyse : {analyse['raison']}"
                        ]
                    })
        
        # Tri : afficher les matchs sûrs en premier
        results = sorted(results, key=lambda x: x['score_confiance'], reverse=True)

    except Exception as e:
        print(f"Erreur : {e}")

    return render_template("index.html", results=results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
