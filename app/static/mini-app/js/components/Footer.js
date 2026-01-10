/**
 * Footer.js (v5.0)
 * About, Links, and Copyright.
 */

window.Components = window.Components || {};

window.Components.Footer = function () {
    const container = document.createElement('div');
    container.className = 'v5-footer';

    // Copy Text
    const aboutText = `
        EarnHub is an aggregator of referral programs, offering bonuses for network growth. 
        Benefit from 7% Telegram monetization and maximize returns through our partner bots.
    `;
    const disclaimer = `Disclaimer: EarnHub is not a financial institution.`;

    container.innerHTML = `
        <div class="footer-header">
            <div class="tit">About EarnHub</div>
            <div class="ver">V1.2.0</div>
        </div>
        
        <div class="footer-text">
            ${aboutText}
        </div>
        
        <div class="footer-disclaimer">
            ${disclaimer}
        </div>
        
        <div class="footer-links-grid">
            <button class="link-card" onclick="window.Render.renderTerms()">
                <div class="icon-circle">${Icons.Document}</div>
                <span>Terms of Use</span>
            </button>
            
            <button class="link-card" onclick="window.Render.renderPrivacy()">
                <div class="icon-circle">${Icons.Shield}</div>
                <span>Privacy Policy</span>
            </button>
            
            <button class="link-card" onclick="Telegram.WebApp.openTelegramLink('https://t.me/HubAggregatorBot')">
                <div class="icon-circle">${Icons.Headphones}</div>
                <span>Support</span>
            </button>
        </div>
    `;

    return container;
};
