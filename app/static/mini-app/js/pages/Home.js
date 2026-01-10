/**
 * Home.js (v5.0)
 * Main Home Tab orchestrator.
 */

window.Render = window.Render || {};

window.Render.renderHomeV5 = function () {
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
    // Logic: TOP if >= 5 referrals OR previously unlocked (though logic says >=5)
    // We stick to simple referral check or explicit flag
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

    // 3. Navigation Cards (Partners / Top Bots)
    const navCards = Components.NavCards();
    container.appendChild(navCards);

    // 4. Money Math
    const moneyMath = Components.MoneyMath();
    container.appendChild(moneyMath);

    // 5. Footer (About)
    const footer = Components.Footer();
    container.appendChild(footer);

    // Track Event
    if (window.trackEvent) trackEvent('view_home_v5');
};
