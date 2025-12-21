from flask import Flask, render_template, request, jsonify
import pickle
import pandas as pd
import numpy as np
import os
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# --- INITIALIZATION ---
# Using the updated v2 model with Semantic Embeddings
MODEL_PATH = 'netflix_model_v2.pkl'

if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, 'rb') as f:
        data = pickle.load(f)
        # Reset index to ensure the dataframe rows align perfectly with the embeddings array
        df = data['df'].reset_index(drop=True)
        embeddings = data['embeddings']
    print("✅ System Ready: AI Semantic Model Loaded and Aligned.")
else:
    print(f"❌ Error: {MODEL_PATH} not found!")

def get_movie_details(pos):
    """Helper to get movie data by integer position in the dataframe"""
    row = df.iloc[pos]
    return {
        'title': str(row.get('title', 'Unknown')),
        'genre': str(row.get('listed_in', 'N/A')),
        'description': str(row.get('description', 'No description available.')),
        'year': str(row.get('release_year', 'N/A')),
        'rating': str(row.get('rating', 'NR')),
        'duration': str(row.get('duration', 'N/A'))
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        # Get user input from the JSON request
        data = request.get_json()
        user_query = data.get('title', '').strip()
        
        if not user_query:
            return jsonify({'success': False, 'message': 'Please enter a movie name'})

        # 1. SEARCH LOGIC: Find all titles containing the query
        # We search case-insensitively
        matches = df[df['title'].str.contains(user_query, case=False, na=False)]
        
        if matches.empty:
            return jsonify({'success': False, 'message': 'Movie not found'})

        # 2. AMBIGUITY CHECK: Did the user provide a broad search?
        # If multiple matches found AND user didn't type the EXACT title...
        exact_match = matches[matches['title'].str.lower() == user_query.lower()]
        
        if len(matches) > 1 and exact_match.empty:
            # Return a list of potential matches for the user to choose from
            options = []
            for i in matches.index[:10]: # Limit to top 10 matches to keep it clean
                options.append({
                    'title': df.at[i, 'title'],
                    'year': str(df.at[i, 'release_year']),
                    'type': df.at[i, 'type']
                })
            return jsonify({
                'success': True, 
                'status': 'ambiguous', 
                'matches': options
            })

        # 3. SELECT TARGET: Use the exact match if found, otherwise the first result
        if not exact_match.empty:
            target_idx = exact_match.index[0]
        else:
            target_idx = matches.index[0]

        # Get the integer position for the embeddings array
        idx_pos = df.index.get_loc(target_idx)
        
        # 4. CALCULATE SEMANTIC SIMILARITY
        # current_vector: (1, 384), embeddings: (TotalMovies, 384)
        current_vector = embeddings[idx_pos].reshape(1, -1)
        sim_scores = cosine_similarity(current_vector, embeddings)[0]

        # 5. GENRE BOOSTING
        target_genres_str = df.iloc[idx_pos]['listed_in']
        target_genres = set(target_genres_str.split(', ')) if pd.notna(target_genres_str) else set()

        # Create a copy to modify for boosting
        boosted_scores = sim_scores.copy()

        for i in range(len(boosted_scores)):
            if i == idx_pos:
                boosted_scores[i] = -1 # Ensure we don't recommend the same movie
                continue
            
            curr_genres_str = df.iloc[i]['listed_in']
            if pd.notna(curr_genres_str):
                curr_genres = set(curr_genres_str.split(', '))
                shared = target_genres.intersection(curr_genres)
                if shared:
                    # Apply a 0.1 boost for every matching genre category
                    boosted_scores[i] += (0.1 * len(shared))

        # 6. GET TOP 6 RECOMMENDATIONS
        related_indices = boosted_scores.argsort()[::-1][:6]

        return jsonify({
            'success': True,
            'status': 'results',
            'searched_movie': get_movie_details(idx_pos),
            'recommendations': [get_movie_details(i) for i in related_indices]
        })

    except Exception as e:
        print(f"⚠️ Server Error: {e}")
        return jsonify({'success': False, 'message': 'An internal error occurred.'})

if __name__ == '__main__':
    # Use environment variable for port to satisfy Render's requirements
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host='0.0.0.0', port=port)