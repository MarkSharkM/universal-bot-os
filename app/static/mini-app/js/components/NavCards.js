/**
 * NavCards.js (v5.0)
 * Grid of navigation cards (Partners, Top Bots).
 */

window.Components = window.Components || {};

window.Components.NavCards = function () {
    const grid = document.createElement('div');
    grid.className = 'v5-nav-grid';

    // --- Partners Card ---
    const partnersCard = document.createElement('div');
    partnersCard.className = 'nav-card card-purple-glow';
    partnersCard.onclick = () => window.Navigation?.switchTab('partners');
    partnersCard.innerHTML = `
        <div class="v5-card-header">
            <div class="icon-sq purple-bg">${Icons.Users}</div>
            <div class="badge-pill purple-badge">+ STARS</div>
        </div>
        <div class="v5-card-body">
            <div class="lbl">Browse</div>
            <div class="tit text-purple">Partners</div>
            <div class="desc">Verified Bots & Earn Stars for Actions</div>
        </div>
        <div class="v5-card-footer">
            <div class="arrow-btn">${Icons.ChevronRight}</div>
        </div>
    `;

    // --- TOP Bots Card ---
    const topCard = document.createElement('div');
    topCard.className = 'nav-card card-gold-glow';
    topCard.onclick = () => window.Navigation?.switchTab('top'); // Maps to 'leaders' usually
    topCard.innerHTML = `
        <div class="v5-card-header">
            <div class="icon-sq gold-bg">${Icons.Robot}</div>
            <div class="badge-pill gold-badge">⚡ x7</div>
        </div>
        <div class="v5-card-body">
            <div class="lbl">Browse</div>
            <div class="tit text-gold">TOP Bots</div>
            <div class="desc">Get x3-x7 More Stars</div>
        </div>
        <div class="v5-card-footer">
            <div class="arrow-btn">${Icons.ChevronRight}</div>
        </div>
    `;

    grid.appendChild(partnersCard);
    grid.appendChild(topCard);

    return grid;
};
