# netflix-recommendations
WhatNext is a full-stack web application that uses Natural Language Processing (NLP) to provide intelligent movie recommendations. Unlike traditional search engines that rely on exact keyword matches, this project implements Semantic Search to understand the deeper themes, genres, and "vibe" of a movie.

The Core InnovationThe engine is powered by a Deep Learning Transformer model (all-MiniLM-L6-v2). By converting movie descriptions, cast lists, and directors into 384-dimensional vector embeddings, the application creates a mathematical map of the Netflix library.When a user selects a movie, the system calculates the "distance" between that movie and every other title in the database using Cosine Similarity results are movies that share the same thematic DNA, not just the same words.

Key FeaturesSemantic Intelligence: Understands context (e.g., recognizing that "Outer Space" and "Galaxy" are related concepts).Real-time Processing: Instantly generates top recommendations from a dataset of 8,000+ titles.Full-Stack Architecture: A seamless connection between a Python-based AI backend and a clean, responsive web frontend.Mobile-First Design: Fully optimized UI for browsing on any device, from desktops to smartphones.

Technical Stack
Language: Python 3.10AI
Machine Learning: Sentence-Transformers, Scikit-Learn
Data Processing: Pandas, NumPy
Web Framework: Flask (Python)
Frontend: HTML5, CSS3 (Modern Flexbox/Grid)
Deployment: Render, Git/GitHub
