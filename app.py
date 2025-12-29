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

# 1. FETCH API KEY (Crucial for Render)
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# --- DATA LOAD ---
try:
    with open('netflix_model_v2.pkl', 'rb') as f:
        data = pickle.load(f)
        df, embeddings = data['df'], data['embeddings']
    print("✅ Model and Database loaded successfully.")
except Exception as e:
    print(f"❌ CRITICAL: Model load failed: {e}")
    df = None

def get_detailed_info(tmdb_id):
    """Fetches high-quality metadata and poster path from TMDB."""
    if not TMDB_API_KEY:
        return {"genres": "Movie", "platforms": ["Streaming"], "runtime": "95 min", "overview": "API Key missing.", "poster": ""}
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}&append_to_response=watch/providers"
        res = session.get(url, timeout=5).json()
        poster_path = res.get('poster_path')
        
        return {
            "genres": ", ".join([g['name'] for g in res.get('genres', [])[:3]]) or "Movie",
            "platforms": [p['provider_name'] for p in res.get('watch/providers', {}).get('results', {}).get('US', {}).get('flatrate', [])] or ["Streaming"],
            "runtime": f"{res.get('runtime', '95')} min",
            "overview": res.get('overview', 'No description available.'),
            "poster": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/500x750?text=No+Poster"
        }
    except Exception as e:
        print(f"TMDB Detail Error: {e}")
        return {"genres": "Movie", "platforms": ["Streaming"], "runtime": "95 min", "overview": "Details unavailable.", "poster": ""}

def format_movie_data(source, details=None):
    """Standardizes movie object for the frontend."""
    is_dict = isinstance(source, dict)
    title = source.get('title') if is_dict else source['title']
    year = (source.get('release_date', '')[:4]) if is_dict else str(source.get('release_year', 'N/A'))
    
    poster = details['poster'] if details else "https://via.placeholder.com/500x750?text=Movie"
    
    return {
        'title': title, 'year': year, 'rating': source.get('rating', 'PG-13') if not is_dict else "PG-13",
        'duration': details['runtime'] if details else (source.get('duration') if not is_dict else "95 min"),
        'description': str(details['overview'] if details else (source.get('description') or "No description.")),
        'genres': details['genres'] if details else "Movie",
        'poster': poster
    }

@app.route('/api/trending')
def get_trending():
    if not TMDB_API_KEY: return jsonify([])
    try:
        res = session.get(f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API_KEY}").json()
        movies = res.get('results', [])
        return jsonify([{"poster": f"https://image.tmdb.org/t/p/w200{m['poster_path']}"} for m in movies if m.get('poster_path')])
    except: return jsonify([])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        user_input = request.json.get('title', '').strip()
        if not user_input:
            return jsonify({'success': False, 'message': 'Please enter a movie title.'})

        # --- STEP 1: LOCAL SEARCH ---
        matches = df[df['title'].str.contains(user_input, case=False, na=False)] if df is not None else pd.DataFrame()
        exact = df[df['title'].str.lower() == user_input.lower()] if df is not None else pd.DataFrame()

        # Handle Multiple Local Matches (Ambiguity)
        if len(matches) > 1 and exact.empty:
            match_list = []
            for i in matches.index[:10]:
                m_data = format_movie_data(df.iloc[i])
                # Quick poster fetch for the selection grid
                s_res = session.get(f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={m_data['title']}").json()
                p_path = s_res['results'][0]['poster_path'] if s_res.get('results') else None
                m_data['poster'] = f"https://image.tmdb.org/t/p/w500{p_path}" if p_path else "https://via.placeholder.com/500x750"
                match_list.append(m_data)
            return jsonify({'success': True, 'status': 'ambiguous', 'matches': match_list})

        # Handle Local Exact Match
        target = exact if not exact.empty else matches.head(1)
        if not target.empty:
            idx = target.index[0]
            sim_scores = cosine_similarity(embeddings[idx].reshape(1, -1), embeddings)[0]
            related_indices = sim_scores.argsort()[-7:-1][::-1]
            
            # Fetch posters for recommendations
            rec_data = []
            for i in related_indices:
                m_title = df.iloc[i]['title']
                s_res = session.get(f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={m_title}").json()
                p_path = s_res['results'][0]['poster_path'] if s_res.get('results') else None
                m_obj = format_movie_data(df.iloc[i])
                m_obj['poster'] = f"https://image.tmdb.org/t/p/w500{p_path}" if p_path else "https://via.placeholder.com/500x750"
                rec_data.append(m_obj)

            # High quality info for main movie
            s_res = session.get(f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={target.iloc[0]['title']}").json()
            main_id = s_res['results'][0]['id'] if s_res.get('results') else None
            details = get_detailed_info(main_id) if main_id else None

            return jsonify({
                'success': True, 'status': 'exact',
                'searched_movie': format_movie_data(target.iloc[0], details),
                'recommendations': rec_data
            })

        # --- STEP 2: GLOBAL WEB FALLBACK (If not in CSV) ---
        print(f"Movie '{user_input}' not in CSV. Trying TMDB Global Search...")
        search_res = session.get(f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={user_input}").json()
        
        if search_res.get('results'):
            main_id = search_res['results'][0]['id']
            full_data = session.get(f"https://api.themoviedb.org/3/movie/{main_id}?api_key={TMDB_API_KEY}&append_to_response=recommendations").json()
            recs_list = full_data.get('recommendations', {}).get('results', [])[:6]
            
            with ThreadPoolExecutor(max_workers=7) as executor:
                ids_to_fetch = [main_id] + [r['id'] for r in recs_list]
                all_details = list(executor.map(get_detailed_info, ids_to_fetch))
                
            return jsonify({
                'success': True, 'status': 'exact',
                'searched_movie': format_movie_data(full_data, all_details[0]),
                'recommendations': [format_movie_data(recs_list[i], all_details[i+1]) for i in range(len(recs_list))]
            })

        return jsonify({'success': False, 'message': f'Could not find "{user_input}" anywhere.'})

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({'success': False, 'message': 'Internal Server Error. Check Render Logs.'})

if __name__ == '__main__':
    app.run(debug=False)