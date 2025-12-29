import pandas as pd
import numpy as np
import pickle
import os
from sentence_transformers import SentenceTransformer

# 1. Load the Datasets
# IMPORTANT: Check if your original file is 'netflix_titles.csv' 
# If it's named something else, change it here!
netflix_file = 'netflix_titles.csv' 

print("📂 Loading files...")
df_netflix = pd.read_csv(netflix_file)
df_movies = pd.read_csv('MoviesOnStreamingPlatforms.csv')
df_tv = pd.read_csv('tv_shows.csv')

def clean_extra_files(df):
    # 1. Force column names to lowercase to avoid "Title" vs "title" issues
    df.columns = [c.lower() for c in df.columns]
    
    # 2. Rename the specific columns we need
    df = df.rename(columns={
        'title': 'title',
        'year': 'release_year',
        'age': 'rating',
        'type': 'type'
    })

    # 3. CLEAN THE TITLES (Remove extra spaces like "Interstellar ")
    df['title'] = df['title'].astype(str).str.strip()
    
    # 4. Map 0/1 to Movie/TV Show
    if 'type' in df.columns:
        df['type'] = df['type'].map({0: 'Movie', 1: 'TV Show', '0': 'Movie', '1': 'TV Show'})
    
    # Ensure all platform columns exist
    for col in ['netflix', 'hulu', 'prime video', 'disney+']:
        actual_col = col.title() # Convert to 'Netflix', 'Hulu', etc.
        if col in df.columns:
            df[actual_col] = df[col]
        elif actual_col not in df.columns:
            df[actual_col] = 0
            
    # Default values for text
    df['description'] = df.get('description', df['title'] + " is available on streaming.")
    df['listed_in'] = df.get('listed_in', 'General')
    df['duration'] = df.get('duration', 'N/A')
    
    cols = ['title', 'type', 'release_year', 'rating', 'description', 'listed_in', 'duration', 'Netflix', 'Hulu', 'Prime Video', 'Disney+']
    return df[cols]

# 2. Standardize and Combine
print("🛠️ Cleaning and merging data...")
df_movies_clean = clean_extra_files(df_movies)
df_tv_clean = clean_extra_files(df_tv)

# Prepare original Netflix data (it's all on Netflix)
df_netflix['Netflix'] = 1
for col in ['Hulu', 'Prime Video', 'Disney+']:
    df_netflix[col] = 0

# Merge everything
full_df = pd.concat([df_netflix, df_movies_clean, df_tv_clean], ignore_index=True)

# --- REPLACE OLD STEP 3 & 4 WITH THIS ---

# 3. Smart Merge: Combine platform data for duplicate titles
print("🔄 Merging platform data for duplicates...")

# Define columns that we want to "combine" (take the highest value, which is 1)
platform_cols = ['Netflix', 'Hulu', 'Prime Video', 'Disney+']

# Group by title and keep the best info for each title
full_df = full_df.groupby('title').agg({
    'type': 'first',
    'release_year': 'first',
    'rating': 'first',
    'description': 'first',
    'listed_in': 'first',
    'duration': 'first',
    'Netflix': 'max',       # If it's a 1 in ANY file, keep it as 1
    'Hulu': 'max',          # If it's a 1 in ANY file, keep it as 1
    'Prime Video': 'max',   # If it's a 1 in ANY file, keep it as 1
    'Disney+': 'max'        # If it's a 1 in ANY file, keep it as 1
}).reset_index()

print(f"✅ Total unique titles: {len(full_df)}")

# 4. Generate AI Embeddings (The rest remains the same)
print("🤖 AI is reading the titles...")
model = SentenceTransformer('all-MiniLM-L6-v2')
full_df['combined_features'] = full_df['title'].fillna('') + " " + full_df['description'].fillna('')
embeddings = model.encode(full_df['combined_features'].tolist(), show_progress_bar=True)
# ----------------------------------------
# 5. Save the final model
with open('netflix_model_v2.pkl', 'wb') as f:
    pickle.dump({'df': full_df, 'embeddings': embeddings}, f)

print("🚀 DONE! netflix_model_v2.pkl is ready for the app.")