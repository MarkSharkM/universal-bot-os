/**
 * Hero.js (v5.0)
 * Main Quest/Dashboard area.
 */

window.Components = window.Components || {};

window.Components.Hero = function (isTop, referralCount) {
    const container = document.createElement('div');
    container.className = 'v5-hero-card';

    if (isTop) {
        // --- TOPASHBOARD (Active) ---
        container.classList.add('is-top');
        const savedLink = AppState.getTgrLink() || AppState.getAppData()?.user?.custom_data?.tgr_link;

        container.innerHTML = `
            <div class="hero-top-content">
                <div class="top-status-badge">
                    ${Icons.Robot} <span>TOP PROGRAM ACTIVE</span>
                </div>
                <div class="top-stats-grid">
                    <div class="stat-item">
                        <div class="val">${referralCount}</div>
                        <div class="lbl">Friends</div>
                    </div>
                    <div class="stat-item">
                        <div class="val text-green">Active</div>
                        <div class="lbl">Status</div>
                    </div>
                </div>
                
                <div class="tgr-link-section">
                     ${savedLink
                ? `<div class="link-active">✅ Link Connected</div>`
                : `<div class="tgr-input-group">
                       <div class="tgr-input-icon">🔗</div>
                       <input type="text" id="tgr-link-input" class="tgr-input" placeholder="Paste your 7% link here...">
                       <button class="tgr-save-btn" onclick="Actions.saveTgrLink()">Save</button>
                   </div>`
            }
                </div>

                 <button class="cta-btn green-glow" onclick="Actions.shareReferralLink()">
                    ${Icons.RocketFilled}
                    <span>SHARE YOUR LINK</span>
                </button>
            </div>
        `;

    } else {
        // --- STARTER QUEST (Unlock TOP) ---
        const goal = 5;
        const current = Math.min(referralCount, 5);
        const progressSegments = Array.from({ length: 5 }).map((_, i) => {
            const isActive = i < current;
            return `<div class="seg ${isActive ? 'filled' : ''}"></div>`;
        }).join('');

        container.innerHTML = `
            <div class="hero-title">Unlock TOP Status</div>
            <div class="hero-subtitle">Invite 5 friends to unlock exclusive rewards</div>
            
            <div class="progress-segments">
                ${progressSegments}
            </div>
            
            <div class="progress-labels">
                <span>${current} invited</span>
                <span class="text-gold">GOAL: ${goal}</span>
            </div>
            
            <button class="cta-btn green-glow" onclick="Actions.shareReferralLink()">
                ${Icons.RocketFilled}
                <span>INVITE & EARN</span>
            </button>
        `;
    }

    return container;
};
