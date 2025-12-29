const TMDB_API_KEY = 'f876e9cbdf0a179da4cec97005be312c';

// --- 1. FLOATING POSTER ANIMATION ---
document.addEventListener('DOMContentLoaded', () => {
    const track = document.getElementById('poster-track');
    if (!track) return;
    // FIXED: Changed TMDB_KEY to TMDB_API_KEY
    fetch(`https://api.themoviedb.org/3/trending/movie/week?api_key=${TMDB_API_KEY}`)
        .then(r => r.json()).then(data => {
            if(!data.results) return;
            // Create the infinite horizontal loop
            [...data.results, ...data.results].forEach(movie => {
                const div = document.createElement('div');
                div.className = 'poster-item';
                div.style.backgroundImage = `url('https://image.tmdb.org/t/p/w200${movie.poster_path}')`;
                track.appendChild(div);
            });
        });
});

// --- 2. POSTER FETCHING LOGIC ---
async function getPoster(title) {
    try {
        // FIXED: Changed TMDB_KEY to TMDB_API_KEY
        const res = await fetch(`https://api.themoviedb.org/3/search/movie?api_key=${TMDB_API_KEY}&query=${encodeURIComponent(title)}`);
        const data = await res.json();
        const path = data.results?.[0]?.poster_path;
        return path ? `https://image.tmdb.org/t/p/w500${path}` : 'https://via.placeholder.com/500x750?text=No+Poster';
    } catch { return 'https://via.placeholder.com/500x750'; }
}

// --- 3. CORE SEARCH FUNCTION ---
async function fetchRecommendations(specificTitle = null) {
    const query = specificTitle || document.getElementById('user-input').value.trim();
    if(!query) return;

    const btn = document.querySelector('.search-box button');
    btn.innerHTML = "SEARCHING...";
    btn.disabled = true;

    try {
        const res = await fetch('/recommend', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title: query})
        });
        const result = await res.json();
        if (result.success) {
            result.status === 'ambiguous' ? renderSelectionGrid(result.matches, query) : renderDashboard(result);
        } else {
            alert(result.message);
        }
    } catch (err) { console.error("Search failed:", err); }
    finally { btn.innerHTML = "DISCOVER"; btn.disabled = false; }
}

// --- 4. UI RENDER: DASHBOARD ---
async function renderDashboard(data) {
    document.getElementById('hero').style.display = 'none';
    document.getElementById('background-scroll').style.display = 'none';
    const resultsDiv = document.getElementById('results');
    resultsDiv.style.display = 'grid'; 

    const movieArray = [data.searched_movie, ...data.recommendations];
    const posters = await Promise.all(movieArray.map(m => getPoster(m.title)));

    const s = data.searched_movie;
    resultsDiv.innerHTML = `
        <aside class="sidebar">
            <div class="identity-poster" style="background-image: url('${posters[0]}')"></div>
            <h1 class="main-title">${s.title}</h1>
            <div class="card-meta-row">
                <span class="badge">${s.year}</span>
                <span class="badge highlight" style="color:#e50914; border-color:#e50914;">${s.rating}</span>
                <span class="badge">${s.duration}</span>
            </div>
            <p class="card-desc">${s.description}</p>
            <button onclick="location.reload()" class="back-btn-pill" style="margin-top:20px; width:100%;">↺ NEW SEARCH</button>
        </aside>
        <main class="content-area">
            <h2 class="section-heading">RECOMMENDATIONS</h2>
            <div class="grid-layout" id="rec-grid"></div>
        </main>`;

    document.getElementById('rec-grid').innerHTML = data.recommendations.map((m, i) => `
        <div class="minimal-card">
            <div class="card-img" style="background-image: url('${posters[i+1]}')"></div>
            <div class="card-body">
                <h3>${m.title}</h3>
                <div class="card-meta-row">
                    <span class="small-badge">${m.year}</span>
                    <span class="small-badge" style="color:#ff4d4d; border-color:#ff4d4d;">${m.rating}</span>
                    <span class="small-badge">${m.duration}</span>
                </div>
                <div class="genres-row" style="color: #e50914; font-weight: bold; font-size: 0.85rem; margin: 8px 0; text-transform: uppercase;">
                    ${m.genres}
                </div>
                <p class="card-desc">${m.description}</p>
            </div>
        </div>`).join('');
}

// --- 5. UI RENDER: AMBIGUITY GRID ---
async function renderSelectionGrid(matches, query) {
    document.getElementById('hero').style.display = 'none';
    const resDiv = document.getElementById('results');
    resDiv.style.display = 'block';
    resDiv.innerHTML = `<div style="text-align:center; padding:40px;"><h2 class="tagline">Results for "${query}"</h2><div class="grid-layout" id="grid-inner"></div><button onclick="location.reload()" class="back-btn-pill" style="margin-top:30px;">← BACK</button></div>`;
    
    const posters = await Promise.all(matches.map(m => getPoster(m.title)));
    document.getElementById('grid-inner').innerHTML = matches.map((m, i) => `
        <div class="minimal-card" onclick="fetchRecommendations('${m.title.replace(/'/g, "\\'")}')" style="cursor:pointer">
            <div class="card-img" style="background-image: url('${posters[i]}')"></div>
            <div class="card-body"><h3>${m.title}</h3><p class="small-badge">${m.year}</p></div>
        </div>`).join('');
}

// --- 6. EVENT LISTENERS ---
document.getElementById('user-input').addEventListener('keypress', e => {
    if (e.key === 'Enter') fetchRecommendations();
});