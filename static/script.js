
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

async function fetchRecommendations() {
    const title = document.getElementById('user-input').value.trim();
    if(!title) return;

    const btn = document.querySelector('.search-box button');
    btn.innerText = "Searching...";

    const res = await fetch('/recommend', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title: title})
    });
    const result = await res.json();

    if(result.success) renderDashboard(result);
    else {
        alert("Title not found!");
        btn.innerText = "Discover";
    }
}

async function renderDashboard(data) {
    document.getElementById('hero').style.display = 'none';
    document.getElementById('background-scroll').style.display = 'none';
    document.getElementById('results').style.display = 'grid';

    const all = [data.searched_movie, ...data.recommendations];
    const posters = await Promise.all(all.map(m => getPoster(m.title)));

    // 1. Sidebar (Searched Movie) - Remains the same
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
    `;

    // 2. Grid Content (Recommendations) - UPDATED with more details
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