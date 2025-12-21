import pandas as pd
from sentence_transformers import SentenceTransformer
import pickle

# 1. Load your dataset
df = pd.read_csv('netflix_titles.csv') # Ensure this filename is correct

# 2. Clean the data
df = df.fillna('')

# 3. Create the "Metadata Soup"
# We repeat the 'director' and 'cast' to give them more "weight" in the AI's mind
def create_soup(x):
    return f"{x['title']} {x['director']} {x['director']} {x['cast']} {x['listed_in']} {x['description']}"

df['soup'] = df.apply(create_soup, axis=1)

print("🚀 AI is reading and understanding your movies... (This may take a minute)")

# 4. Use a Pre-trained Deep Learning Model
# 'all-MiniLM-L6-v2' is fast, lightweight, and incredibly smart
model = SentenceTransformer('all-MiniLM-L6-v2')

# 5. Generate Semantic Embeddings
# This converts the 'soup' into a set of 384 coordinates for each movie
embeddings = model.encode(df['soup'].tolist(), show_progress_bar=True)

# 6. Save the upgraded model
data_to_save = {
    'df': df,
    'embeddings': embeddings
}

with open('netflix_model_v2.pkl', 'wb') as f:
    pickle.dump(data_to_save, f)

print("✅ Upgrade Complete! Your new model is saved as 'netflix_model_v2.pkl'")