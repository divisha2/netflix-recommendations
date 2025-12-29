from flask import Flask, request, jsonify, render_template
import pandas as pd
import pickle
import requests
import os
from sklearn.metrics.pairwise import cosine_similarity
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
session = requests.Session()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# LOAD MODEL
try:
    with open('netflix_model_v2.pkl', 'rb') as f:
        data = pickle.load(f)
        df, embeddings = data['df'], data['embeddings']
except Exception as e:
    print(f"CRITICAL: Model load failed: {e}")
    df = None

def get_detailed_info(tmdb_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}&append_to_response=watch/providers"
        res = session.get(url, timeout=2.5).json()
        
        return {
            "genres": ", ".join([g['name'] for g in res.get('genres', [])[:3]]) or "Movie",
            "platforms": [p['provider_name'] for p in res.get('watch/providers', {}).get('results', {}).get('US', {}).get('flatrate', [])] or ["Streaming"],
            "runtime": f"{res.get('runtime', '95')} min",
            "overview": res.get('overview', 'No description available.')
        }
    except:
        return {"genres": "Movie", "platforms": ["Streaming"], "runtime": "95 min", "overview": "Description currently being updated."}

def format_movie_data(source, details=None):
    is_dict = isinstance(source, dict)
    title = source.get('title') if is_dict else source['title']
    year = (source.get('release_date', '')[:4]) if is_dict else str(source.get('release_year', 'N/A'))
    rating = source.get('rating', 'PG-13') if not is_dict else "PG-13"
    
    description = details['overview'] if details else (source.get('description') or source.get('overview', 'No description available.'))
    genres = details['genres'] if details else (source.get('listed_in', 'Movie, Drama') if not is_dict else "Movie")
    duration = details['runtime'] if details else (source.get('duration') if not is_dict else "95 min")

    return {
        'title': title, 'year': year, 'rating': rating,
        'duration': duration, 'description': str(description),
        'genres': genres, 'platforms': details['platforms'] if details else ["Streaming"]
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        user_input = request.json.get('title', '').strip()
        if not user_input or df is None:
            return jsonify({'success': False, 'message': 'System initializing. Please wait.'})

        # 1. AMBIGUITY CHECK (Local)
        matches = df[df['title'].str.contains(user_input, case=False, na=False)]
        exact = df[df['title'].str.lower() == user_input.lower()]

        if len(matches) > 1 and exact.empty:
            return jsonify({
                'success': True, 'status': 'ambiguous',
                'matches': [format_movie_data(df.iloc[i]) for i in matches.index[:10]]
            })

        # 2. LOCAL CALCULATION (Exact Match)
        target = exact if not exact.empty else matches.head(1)
        if not target.empty:
            idx = target.index[0]
            # Similarity Calculation:
            # $$similarity = \cos(\theta) = \frac{\mathbf{A} \cdot \mathbf{B}}{\|\mathbf{A}\| \|\mathbf{B}\|}$$
            sim_scores = cosine_similarity(embeddings[idx].reshape(1, -1), embeddings)[0]
            related_indices = sim_scores.argsort()[-7:-1][::-1]
            
            return jsonify({
                'success': True, 'status': 'exact',
                'searched_movie': format_movie_data(target.iloc[0]),
                'recommendations': [format_movie_data(df.iloc[i]) for i in related_indices]
            })

        # 3. WEB ENGINE FALLBACK (Fixed for "Internal Error")
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={user_input}"
        search_res = session.get(search_url).json()
        
        if search_res.get('results'):
            main_id = search_res['results'][0]['id']
            full_data = session.get(f"https://api.themoviedb.org/3/movie/{main_id}?api_key={TMDB_API_KEY}&append_to_response=recommendations").json()
            
            # FIXED: Safe nested access
            recs_container = full_data.get('recommendations', {})
            recs_list = recs_container.get('results', [])[:6] if isinstance(recs_container, dict) else []
            
            with ThreadPoolExecutor(max_workers=7) as executor:
                ids_to_fetch = [main_id] + [r['id'] for r in recs_list]
                all_details = list(executor.map(get_detailed_info, ids_to_fetch))
                
                main_info = all_details[0]
                recs_info = all_details[1:]

            return jsonify({
                'success': True, 'status': 'exact',
                'searched_movie': format_movie_data(full_data, main_info),
                'recommendations': [format_movie_data(recs_list[i], recs_info[i]) for i in range(len(recs_list))]
            })

        return jsonify({'success': False, 'message': 'Movie not found.'})

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({'success': False, 'message': 'An internal error occurred.'})

if __name__ == '__main__':
    app.run(debug=True, port=5001)