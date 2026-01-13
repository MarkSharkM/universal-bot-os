/**
 * Home.js (v5.0)
 * Main Home Tab orchestrator.
 */

// Ensure namespace exists
window.Pages = window.Pages || {};

window.Pages.Home = {
    render: function () {
        const appData = AppState.getAppData();
        if (!appData) return;

        // Clear Container (Home Page Section)
        const container = document.getElementById('home-page');
        if (!container) return;
        container.innerHTML = '';

        // Add v5 wrapper class for specific styling scope if needed
        container.classList.add('v5-home-wrapper');

        // Logic Data
        const referralCount = AppState.getReferralCount();
        const isTop = (referralCount >= 5);

        // 1. Header
        // Use initDataUnsafe user if available for immediate/correct display name
        const tg = AppState.getTg();
        const initUser = tg?.initDataUnsafe?.user;
        const userToDisplay = initUser || appData.user;

        const header = Components.Header(userToDisplay, isTop);
        container.appendChild(header);

        // 2. Hero (Quest / Dashboard)
        const hero = Components.Hero(isTop, referralCount);
        container.appendChild(hero);

        // 3. Money Math (Your Potential Earnings)
        const moneyMath = Components.MoneyMath();
        container.appendChild(moneyMath);

        // 4. Navigation Cards (Partners / Top Bots)
        const navCards = Components.NavCards();
        container.appendChild(navCards);

        // 5. Footer (About)
        const footer = Components.Footer();
        container.appendChild(footer);

        // Track Event
        if (window.trackEvent) trackEvent('view_home_v5');
    }
};

// Backward compatibility alias if needed by legacy code (though render.js handles it now)
window.Render = window.Render || {};
window.Render.renderHomeV5 = window.Pages.Home.render;

