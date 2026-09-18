import os
from flask import Flask, render_template
import requests

app = Flask(__name__)

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
            period = status_info.get('period', 0)
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
                total_goals = home_score + away_score
                
                # Récupération de la minute numérique
                try:
                    minute_num = int(clock.replace("'", "").split("+")[0])
                except:
                    minute_num = 0

                # Calcul dynamique selon l'avancement du match
                score_confiance = 50
                decision = "Match sous observation"
                signaux = []

                if state == "in": # Match en cours
                    signaux.append(f"Match en direct ({clock})")
                    
                    if minute_num >= 55 and total_goals == 0:
                        score_confiance = 82
                        decision = "CONFIRMÉ : Over 0.5 / Prochain But Imminent"
                        signaux.append("Anomalie : 0-0 après la 55' minute")
                        signaux.append("Pression offensive en hausse")
                    elif minute_num >= 35 and total_goals == 0:
                        score_confiance = 68
                        decision = "À SURVEILLER : Pression avant mi-temps"
                        signaux.append("Match fermé, opportunité d'ouverture")
                    elif total_goals >= 2:
                        score_confiance = 75
                        decision = "CONFIRMÉ : Match ouvert (Over 2.5)"
                        signaux.append(f"Rythme élevé : {total_goals} buts déjà marqués")
                    else:
                        score_confiance = 55
                        decision = "ANALYSE : Observation phase initiale"
                else:
                    signaux.append(f"Statut : {status_info.get('type', {}).get('shortDetail', 'Programmé')}")

                results.append({
                    'league': competition,
                    'minute': clock if state == "in" else "FIN",
                    'teams': f"{home_name} vs {away_name}",
                    'score': f"{home_score} - {away_score}",
                    'score_confiance': score_confiance,
                    'decision': decision,
                    'signaux': signaux
                })
    except Exception as e:
        print(f"Erreur : {e}")

    return render_template("index.html", results=results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
