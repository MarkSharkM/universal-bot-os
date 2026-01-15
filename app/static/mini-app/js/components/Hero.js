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
                
                <div class="tgr-link-section" style="max-width:100%; overflow:hidden;">
                     ${savedLink && !AppState.getIsEditingTgrLink()
                ? `<div style="display:flex; flex-direction:column; gap:6px;">
                       <div class="tgr-input-group saved-state" style="display:flex; align-items:center; gap:8px; padding:14px 16px;">
                           <div class="tgr-input-icon" 
                                onclick="navigator.clipboard.writeText('${savedLink}').then(() => { const trans = AppState.getAppData()?.translations || {}; if (typeof Toast !== 'undefined') Toast.success(trans.link_copied || 'Скопійовано!'); })" 
                                style="cursor:pointer; flex-shrink:0; font-size:18px; opacity:0.7; transition:all 0.2s;" 
                                onmouseover="this.style.opacity='1'" 
                                onmouseout="this.style.opacity='0.7'"
                                title="Copy">🔗</div>
                           <div class="tgr-link-display" 
                                onclick="Actions.editTgrLink()" 
                                style="flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; opacity:0.6; font-size:13px; font-family:monospace; cursor:pointer; transition:opacity 0.2s;" 
                                onmouseover="this.style.opacity='0.9'" 
                                onmouseout="this.style.opacity='0.6'"
                                title="Click to edit">${savedLink}</div>
                           <button class="tgr-saved-badge" onclick="Actions.editTgrLink()" style="flex-shrink:0; background:rgba(0,230,118,0.12); color:#00E676; border:1px solid rgba(0,230,118,0.3); border-radius:12px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; transition:all 0.2s; display:flex; align-items:center; gap:4px;" onmouseover="this.style.background='rgba(0,230,118,0.18)'" onmouseout="this.style.background='rgba(0,230,118,0.12)'">
                               <span style="font-size:12px;">✅</span>
                               <span>${t.saved || 'Збережено'}</span>
                           </button>
                       </div>
                       <div class="input-helper-text" style="cursor:pointer; text-align:center; padding:6px; opacity:0.45; font-size:12px; transition:opacity 0.2s;" 
                            onclick="Actions.editTgrLink()" 
                            onmouseover="this.style.opacity='0.7'" 
                            onmouseout="this.style.opacity='0.45'">${t.change_link || 'Змінити лінку?'}</div>
                   </div>`
                : `<div class="tgr-input-group" style="max-width:100%;">
                       <div class="tgr-input-icon">🔗</div>
                       <input type="url" 
                              inputmode="url" 
                              autocomplete="off" 
                              autocorrect="off" 
                              autocapitalize="off" 
                              spellcheck="false"
                              id="tgr-link-input" 
                              class="tgr-input" 
                              value="${savedLink || ''}"
                              placeholder="${t.paste_link_placeholder || 'Paste your 7% link here...'}"
                              oninput="Actions.validateTgrInput(this)"
                              onfocus="document.body.classList.add('keyboard-open'); setTimeout(() => this.scrollIntoView({behavior: 'smooth', block: 'center'}), 300)"
                              onblur="document.body.classList.remove('keyboard-open')">
                       <button id="tgr-save-btn" class="tgr-save-btn ${savedLink ? '' : 'disabled'}" ${savedLink ? '' : 'disabled'} onclick="Actions.saveTgrLink(); AppState.setIsEditingTgrLink(false);">
                           ${t.save || 'Save'}
                       </button>
                   </div>
                   <div id="tgr-input-helper" class="input-helper-status" style="display:none;"></div>`
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
