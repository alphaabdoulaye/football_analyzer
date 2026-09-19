import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Récupération des clés depuis les variables d'environnement
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CX = os.environ.get("GOOGLE_CX")

def search_match_data(team_a, team_b):
    """
    Effectue une recherche Google pour obtenir des infos récentes sur le match.
    """
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        return "Clés API non configurées correctement sur le serveur."

    query = f"{team_a} vs {team_b} stats xG composition blessés calendrier enjeux"
    url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        'key': GOOGLE_API_KEY,
        'cx': GOOGLE_CX,
        'q': query,
        'num': 5
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        snippets = []
        if "items" in data:
            for item in data["items"]:
                snippets.append(item.get("snippet", ""))
        return " ".join(snippets)
    except Exception as e:
        return f"Erreur lors de la recherche : {str(e)}"

def analyze_match_logic(team_a, team_b, search_context, heavy_schedule=False):
    """
    Analyse basée sur vos critères : BTTS, xG, défense, calendrier, enjeux et arbitre.
    """
    analysis = {
        "team_a": team_a,
        "team_b": team_b,
        "btts_probability": "Moyenne",
        "xg_favorite_trend": "Normale",
        "defensive_vulnerability": "Standard",
        "recommendation": "",
        "notes": []
    }

    # Prise en compte du calendrier chargé pour les favoris
    if heavy_schedule:
        analysis["btts_probability"] = "Élevée (Calendrier chargé)"
        analysis["xg_favorite_trend"] = "Baisse d'efficacité attendue"
        analysis["defensive_vulnerability"] = "Accentuée (Fatigue cumulée)"
        analysis["notes"].append("Attention : Match en milieu de semaine détecté / calendrier dense. Exclure les options sans BTTS pour le favori.")
    else:
        analysis["recommendation"] = "Analyse standard : Vérifier les compositions officielles et la tolérance de l'arbitre."

    return analysis

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        team_a = request.form.get('team_a')
        team_b = request.form.get('team_b')
        heavy_schedule = 'heavy_schedule' in request.form

        if team_a and team_b:
            raw_data = search_match_data(team_a, team_b)
            result = analyze_match_logic(team_a, team_b, raw_data, heavy_schedule)
            result["raw_snippets"] = raw_data

    return render_template('index.html', result=result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
