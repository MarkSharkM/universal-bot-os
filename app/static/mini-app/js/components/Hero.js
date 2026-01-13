/**
 * Hero.js (v5.0)
 * Main Quest/Dashboard area.
 */

window.Components = window.Components || {};

window.Components.Hero = function (isTop, referralCount) {
    const container = document.createElement('div');
    container.className = 'v5-hero-card';
    const appData = AppState.getAppData();
    const t = appData?.translations || {};

    if (isTop) {
        // --- TOPASHBOARD (Active) ---
        container.classList.add('is-top');
        const savedLink = AppState.getTgrLink() || appData?.user?.custom_data?.tgr_link;

        container.innerHTML = `
            <div class="hero-top-content">
                <div class="hero-stats-row">
                    <div class="hero-stat-box">
                        <div class="icon-circle-lg">${Icons.Users}</div>
                        <div class="stat-val">${referralCount}</div>
                        <div class="stat-lbl">${t.stat_friends || 'Friends'}</div>
                    </div>
                    <div class="hero-stat-box active-box">
                        <div class="icon-circle-lg" style="color:#00E676;background:rgba(0,230,118,0.1);box-shadow:0 0 10px rgba(0,230,118,0.2)">
                            ${Icons.Robot}
                        </div>
                        <div class="stat-lbl-active">${t.top_program_active || 'TOP PROGRAM<br>ACTIVE'}</div>
                    </div>
                </div>
                
                <div class="tgr-link-section">
                     ${savedLink
                ? `<div class="link-active">${t.link_connected || '✅ Link Connected'}</div>`
                : `<div class="tgr-input-group">
                       <div class="tgr-input-icon">🔗</div>
                       <input type="text" id="tgr-link-input" class="tgr-input" placeholder="${t.paste_link_placeholder || 'Paste your 7% link here...'}">
                       <button class="tgr-save-btn" onclick="Actions.saveTgrLink()">${t.save || 'Save'}</button>
                   </div>`
            }
                </div>

                ${!savedLink ? `<div class="input-helper-text" style="cursor: pointer; padding: 10px;" onclick="Actions.showActivate7Instructions()">${t.where_to_get_link || 'Де взяти лінку?'}</div>` : ''}


                 <button class="cta-btn green-glow" onclick="Actions.shareReferralLink()">
                    ${Icons.RocketFilled}
                    <span>${t.share_your_link || 'SHARE YOUR LINK'}</span>
                </button>
            </div>
        `;

    } else {
        // --- STARTER QUEST (Unlock TOP) ---
        const goal = appData?.earnings?.required_invites || 5;
        const current = Math.min(referralCount, goal);
        const progressSegments = Array.from({ length: goal }).map((_, i) => {
            const isActive = i < current;
            return `<div class="seg ${isActive ? 'filled' : ''}"></div>`;
        }).join('');

        const invitedLabel = (t.invited_count || '{{count}} invited').replace('{{count}}', current);
        const goalLabel = (t.goal_text || 'GOAL: {{goal}}').replace('{{goal}}', goal);

        container.innerHTML = `
            <div class="hero-title">${t.unlock_top_status || 'Unlock TOP Status'}</div>
            <div class="hero-subtitle">${t.invite_5_subtitle || 'Invite 5 friends to unlock exclusive rewards'}</div>
            
            <div class="progress-segments">
                ${progressSegments}
            </div>
            
            <div class="progress-labels">
                <span>${invitedLabel}</span>
                <span class="text-gold">${goalLabel}</span>
            </div>
            
            <button class="cta-btn green-glow" onclick="Actions.shareReferralLink()">
                ${Icons.RocketFilled}
                <span>${t.invite_and_earn || 'INVITE & EARN'}</span>
            </button>
        `;
    }

    return container;
};
