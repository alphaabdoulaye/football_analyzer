import os
from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/")
def index():
    results = []
    
    # URL d'un flux de matchs en direct sans clé
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        for event in data.get('events', []):
            competition = event.get('league', {}).get('name', 'Football')
            status = event.get('status', {}).get('type', {}).get('shortDetail', '')
            
            competitors = event.get('competitions', [{}])[0].get('competitors', [])
            if len(competitors) >= 2:
                home = competitors[0]
                away = competitors[1]
                
                home_name = home.get('team', {}).get('displayName', 'Domicile')
                away_name = away.get('team', {}).get('displayName', 'Extérieur')
                
                home_score = home.get('score', '0')
                away_score = away.get('score', '0')
                
                results.append({
                    'league': competition,
                    'minute': status,
                    'teams': f"{home_name} vs {away_name}",
                    'score': f"{home_score} - {away_score}",
                    'score_confiance': 65,
                    'decision': "Analyse des données réelles...",
                    'signaux': [
                        f"Match en direct / Statut : {status}",
                        "Données récupérées en temps réel"
                    ]
                })
    except Exception as e:
        print(f"Erreur : {e}")

    return render_template("index.html", results=results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
