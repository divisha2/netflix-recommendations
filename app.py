from flask import Flask, render_template, request, jsonify
import pickle
import pandas as pd
import numpy as np
import os
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# --- INITIALIZATION ---
MODEL_PATH = 'netflix_model.pkl'

if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, 'rb') as f:
        data = pickle.load(f)
        df = data['df'].reset_index(drop=True)  # CRITICAL: Reset index to match array positions
        pca_features = data['pca_features']
    print("✅ System Ready: Index and Features Aligned.")
else:
    print("❌ Error: netflix_model.pkl not found!")

def get_movie_details(pos):
    """Helper to get movie data by integer position"""
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
        user_query = request.get_json().get('title', '').strip().lower()
        
        # 1. Find the movie - search across titles
        match = df[df['title'].str.lower().str.contains(user_query, na=False)]
        
        if match.empty:
            return jsonify({'success': False, 'message': 'Movie not found'})

        # 2. Get the INTEGER POSITION (Important for matching with pca_features array)
        # We take the first match found
        idx_pos = df.index.get_loc(match.index[0])
        
        # 3. Calculate Cosine Similarity
        # current_vector shape: (1, n_features), pca_features shape: (n_movies, n_features)
        current_vector = pca_features[idx_pos].reshape(1, -1)
        sim_scores = cosine_similarity(current_vector, pca_features)[0]

        # 4. Apply Genre Boosting
        target_genres_str = df.iloc[idx_pos]['listed_in']
        target_genres = set(target_genres_str.split(', ')) if pd.notna(target_genres_str) else set()

        # We create a copy to avoid modifying the original similarity scores directly in a bad way
        boosted_scores = sim_scores.copy()

        for i in range(len(boosted_scores)):
            if i == idx_pos:
                continue
            
            curr_genres_str = df.iloc[i]['listed_in']
            if pd.notna(curr_genres_str):
                curr_genres = set(curr_genres_str.split(', '))
                shared = target_genres.intersection(curr_genres)
                if shared:
                    # Give a 0.1 boost for each matching genre
                    boosted_scores[i] += (0.1 * len(shared))

        # 5. Get Top Recommendations
        # Sort indices by boosted similarity scores in descending order
        related_indices = boosted_scores.argsort()[::-1]
        
        # Filter out the searched movie and get top 6
        final_indices = [i for i in related_indices if i != idx_pos][:6]

        return jsonify({
            'success': True,
            'searched_movie': get_movie_details(idx_pos),
            'recommendations': [get_movie_details(i) for i in final_indices]
        })

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({'success': False, 'message': str(e)})

# Change the loading section in your app.py to this:
MODEL_PATH = 'netflix_model_v2.pkl'

if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, 'rb') as f:
        data = pickle.load(f)
        df = data['df'].reset_index(drop=True)
        # We now use 'embeddings' instead of 'pca_features'
        embeddings = data['embeddings']
    print("✅ AI Semantic Model Loaded.")

# Update the 'recommend' function logic:
# current_vector = embeddings[idx_pos].reshape(1, -1)
# sim_scores = cosine_similarity(current_vector, embeddings)[0]

if __name__ == '__main__':
    app.run(debug=True, port=5001)