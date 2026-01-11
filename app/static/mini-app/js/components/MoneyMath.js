/**
 * MoneyMath.js (v5.0)
 * Earnings potential visualization.
 */

window.Components = window.Components || {};

window.Components.MoneyMath = function () {
    const container = document.createElement('div');
    container.className = 'v5-money-math';
    const t = AppState.getAppData()?.translations || {};

    container.innerHTML = `
        <div class="math-header">
            ${Icons.Wallet} 
            <span>${t.potential_earnings || 'Your Potential Earnings'}</span>
        </div>
        
        <div class="math-grid">
            <!-- Tier 1 -->
            <div class="math-card">
                <div class="tier-lbl">1 USER</div>
                <div class="tier-val">0.7€</div>
                <div class="tier-bar active-20"></div>
            </div>
            
            <!-- Tier 2 -->
            <div class="math-card">
                <div class="tier-lbl">10 USERS</div>
                <div class="tier-val">7.0€</div>
                <div class="tier-bar active-50"></div>
            </div>
            
            <!-- Tier 3 -->
            <div class="math-card">
                <div class="tier-lbl">100 USERS</div>
                <div class="tier-val">70€+</div>
                <div class="tier-bar active-100"></div>
            </div>
        </div>
        
        <div class="math-footer">
            ${t.estimates_desc || 'Estimates based on average active user engagement.'}
        </div>
    `;

    return container;
};
