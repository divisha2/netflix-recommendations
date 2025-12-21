const TMDB_KEY = 'f876e9cbdf0a179da4cec97005be312c';

// Support for "Enter" key
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('user-input');
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') fetchRecommendations();
    });
});

async function getPoster(title) {
    try {
        const res = await fetch(`https://api.themoviedb.org/3/search/multi?api_key=${TMDB_KEY}&query=${encodeURIComponent(title)}`);
        const data = await res.json();
        return (data.results && data.results[0]) ? `https://image.tmdb.org/t/p/w500${data.results[0].poster_path}` : 'https://via.placeholder.com/500x750?text=No+Image';
    } catch { return 'https://via.placeholder.com/500x750?text=Error'; }
}

// UPDATED: Now accepts an optional 'specificTitle' for when a user clicks a choice
async function fetchRecommendations(specificTitle = null) {
    const title = specificTitle || document.getElementById('user-input').value.trim();
    if(!title) return;

    const btn = document.querySelector('.search-box button');
    btn.innerText = "Searching...";

    try {
        const res = await fetch('/recommend', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title: title})
        });
        const result = await res.json();

        if (result.success) {
            // PATH A: Multiple movies found - show the choice grid
            if (result.status === 'ambiguous') {
                renderSelectionGrid(result.matches, title);
            } 
            // PATH B: Direct match found - show the dashboard
            else {
                renderDashboard(result);
            }
        } else {
            alert(result.message || "Title not found!");
            btn.innerText = "Discover";
        }
    } catch (err) {
        console.error(err);
        btn.innerText = "Discover";
    }
}

// NEW FUNCTION: Renders the "Did you mean?" screen
async function renderSelectionGrid(matches, query) {
    document.getElementById('hero').style.display = 'none';
    document.getElementById('background-scroll').style.display = 'none';
    
    // We'll reuse the results container but change the layout slightly
    const resultsDiv = document.getElementById('results');
    resultsDiv.style.display = 'block'; // Change from grid to block for the header
    
    // Get posters for all potential matches (limit to 6 for speed)
    const displayMatches = matches.slice(0, 6);
    const posters = await Promise.all(displayMatches.map(m => getPoster(m.title)));

    let html = `
        <div style="text-align:center; padding: 40px 20px;">
            <h2 class="tagline">Multiple matches for "${query}"</h2>
            <p style="color:#888; margin-bottom:40px;">Click the exact movie you're looking for:</p>
            <div class="grid-layout">
    `;

    displayMatches.forEach((m, i) => {
        html += `
            <div class="minimal-card" style="cursor:pointer" onclick="fetchRecommendations('${m.title.replace(/'/g, "\\'")}')">
                <div class="card-img" style="background-image: url('${posters[i]}')"></div>
                <div class="card-body">
                    <h4 style="margin:0; font-family:'Outfit'; font-size:1.2rem;">${m.title}</h4>
                    <p class="small-badge" style="margin-top:10px;">${m.type} | ${m.year}</p>
                    <button class="back-btn-pill" style="width:100%; margin-top:15px; border-color:var(--accent-red); color:var(--accent-red);">Select This</button>
                </div>
            </div>
        `;
    });

    html += `
            </div>
            <button onclick="window.location.reload()" class="back-btn-pill" style="margin-top:50px;">← Back to Search</button>
        </div>
    `;
    
    resultsDiv.innerHTML = html;
}

async function renderDashboard(data) {
    // Reset display just in case we are coming from the selection grid
    document.getElementById('hero').style.display = 'none';
    document.getElementById('background-scroll').style.display = 'none';
    const resultsDiv = document.getElementById('results');
    resultsDiv.style.display = 'grid'; 
    
    // Reset the innerHTML structure to handle the sidebar/grid layout
    resultsDiv.innerHTML = `
        <aside class="sidebar" id="selection-profile"></aside>
        <main class="content-area">
            <div class="grid-layout" id="rec-grid"></div>
        </main>
    `;

    const all = [data.searched_movie, ...data.recommendations];
    const posters = await Promise.all(all.map(m => getPoster(m.title)));

    const s = data.searched_movie;
    document.getElementById('selection-profile').innerHTML = `
        <div class="identity-poster" style="background-image: url('${posters[0]}')"></div>
        <h2 style="font-family:'Outfit'; font-size:2.5rem; margin:0;">${s.title}</h2>
        <div style="margin:15px 0;">
            <span class="badge">${s.year}</span>
            <span class="badge" style="color:var(--accent-red)">${s.rating}</span>
            <span class="badge">${s.duration}</span>
        </div>
        <p style="color:#888; line-height:1.7;">${s.description}</p>
        <button onclick="window.location.reload()" class="back-btn-pill" style="width:100%; margin-top:20px;">← New Search</button>
    `;

    let html = '';
    data.recommendations.forEach((m, i) => {
        html += `
            <div class="minimal-card">
                <div class="card-img" style="background-image: url('${posters[i+1]}')"></div>
                <div class="card-body">
                    <h4 style="margin:0; font-family:'Outfit'; font-size:1.4rem;">${m.title}</h4>
                    <div class="card-meta-row">
                        <span class="small-badge">${m.year}</span>
                        <span class="small-badge" style="color:var(--accent-red)">${m.rating}</span>
                        <span class="small-badge">${m.duration}</span>
                    </div>
                    <p style="color:var(--accent-red); font-size:0.8rem; font-weight:700; margin:10px 0;">${m.genre}</p>
                    <p class="card-desc">${m.description}</p>
                </div>
            </div>
        `;
    });
    document.getElementById('rec-grid').innerHTML = html;
}

// Populate background wall
fetch(`https://api.themoviedb.org/3/trending/movie/week?api_key=${TMDB_KEY}`)
    .then(r => r.json()).then(data => {
        data.results.forEach(m => {
            const div = document.createElement('div');
            div.className = 'poster-item';
            div.style.backgroundImage = `url('https://image.tmdb.org/t/p/w300${m.poster_path}')`;
            document.getElementById('poster-track').appendChild(div);
        });
    });