import os
import re
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Configuration des clés d'API (Récupérées via variables d'environnement sur Render ou clés par défaut)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyCDq3V7PxKWzDM_s8q_ncyCCyHKMs5IoTY")
GOOGLE_CX = os.getenv("GOOGLE_CX", "91521213dedaa4040")

def search_google(query):
    """Exécute une requête sur l'API Google Custom Search."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": query,
        "num": 5
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            # Concatène les titres et extraits (snippets) renvoyés par Google
            combined_text = " ".join([f"{item.get('title', '')} {item.get('snippet', '')}" for item in items])
            return combined_text
        else:
            print(f"Erreur API Google ({response.status_code}): {response.text}")
            return ""
    except Exception as e:
        print(f"Erreur lors de la requête Google: {e}")
        return ""

def fetch_real_matches_google(league_name, date_str):
    """Recherche dynamique des matchs réels du jour via Google."""
    query = f"programme matchs {league_name} {date_str} calendrier rencontres"
    search_text = search_google(query)
    
    if not search_text:
        return []

    # Regex flexible gérant majuscules, minuscules, tirets, vs, / et caractères accentués
    pattern = r'([A-Za-z0-9À-ÿ\s]{3,20})\s*(?:vs|v|-|/|–|—)\s*([A-Za-z0-9À-ÿ\s]{3,20})'
    raw_matches = re.findall(pattern, search_text, re.IGNORECASE)
    
    matches = []
    seen = set()
    forbidden_words = [
        "match", "direct", "ligue", "premier", "foot", "football", 
        "actu", "live", "vs", "score", "journee", "champions", 
        "calendrier", "classement", "resultat", "resultats"
    ]

    for team_a, team_b in raw_matches:
        t_a = team_a.strip()
        t_b = team_b.strip()
        
        t_a_lower = t_a.lower()
        t_b_lower = t_b.lower()
        
        # Filtre les mots-clés parasites
        if any(w in t_a_lower for w in forbidden_words) or any(w in t_b_lower for w in forbidden_words):
            continue
            
        pair_key = f"{t_a_lower}-{t_b_lower}"
        
        if pair_key not in seen and len(t_a) >= 3 and len(t_b) >= 3:
            seen.add(pair_key)
            matches.append({"team_a": t_a, "team_b": t_b})
            if len(matches) >= 8:
                break

    return matches

def fetch_match_analysis_data(team_a, team_b, league_name):
    """Exécute les 3 requêtes Google dédiées aux statistiques du match."""
    
    # 1. Requête Classement & Points
    req1_query = f"classement {team_a} {team_b} {league_name} points rang"
    text1 = search_google(req1_query)
    
    # 2. Requête Forme récente (Derniers matchs)
    req2_query = f"dernier matchs {team_a} {team_b} forme recente resultats"
    text2 = search_google(req2_query)
    
    # 3. Requête Face-à-face (H2H) & Différence de buts
    req3_query = f"confrontations directes h2h {team_a} vs {team_b} buts"
    text3 = search_google(req3_query)
    
    return {
        "standings_raw": text1 if text1 else "Données de classement non disponibles via Google.",
        "recent_form_raw": text2 if text2 else "Données de forme récente non disponibles via Google.",
        "h2h_raw": text3 if text3 else "Données H2H non disponibles via Google."
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_matches", methods=["POST"])
def get_matches():
    data = request.get_json() or {}
    league = data.get("league", "")
    day = data.get("day", "")

    if not league or not day:
        return jsonify({"status": "error", "message": "Ligue et date requises"}), 400

    matches = fetch_real_matches_google(league, day)
    return jsonify({"status": "success", "matches": matches})

@app.route("/analyze_match", methods=["POST"])
def analyze_match():
    data = request.get_json() or {}
    team_a = data.get("team_a", "")
    team_b = data.get("team_b", "")
    league = data.get("league", "")

    if not team_a or not team_b:
        return jsonify({"status": "error", "message": "Équipes non spécifiées"}), 400

    analysis = fetch_match_analysis_data(team_a, team_b, league)
    return jsonify({
        "status": "success",
        "match": f"{team_a} vs {team_b}",
        "analysis": analysis
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
