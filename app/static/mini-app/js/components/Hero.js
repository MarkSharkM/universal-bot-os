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
                <div class="hero-stats-row">
                    <div class="hero-stat-box">
                        <div class="icon-circle-lg">${Icons.Users}</div>
                        <div class="stat-val">${referralCount}</div>
                        <div class="stat-lbl">Friends</div>
                    </div>
                    <div class="hero-stat-box active-box">
                        <div class="icon-circle-lg" style="color:#00E676;background:rgba(0,230,118,0.1);box-shadow:0 0 10px rgba(0,230,118,0.2)">
                            ${Icons.Robot}
                        </div>
                        <div class="stat-lbl-active">TOP PROGRAM<br>ACTIVE</div>
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

                ${!savedLink ? `<div class="input-helper-text" onclick="Actions.openBotForLink()">Де взяти лінку?</div>` : ''}


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
