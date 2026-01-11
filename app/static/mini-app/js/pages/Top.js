/**
 * TOP Page Component
 * Handles rendering of the Leaderboard (TOP) tab.
 */

window.Pages = window.Pages || {};

window.Pages.Top = {
    render() {
        console.log('[Pages.Top] rendering...');

        const appData = AppState.getAppData();
        if (!appData) {
            console.warn('[Pages.Top] appData not available');
            return;
        }

        // Ensure we're on the TOP page
        const topPage = document.getElementById('top-page');
        if (!topPage || !topPage.classList.contains('active')) {
            console.warn('[Pages.Top] top page not active');
            return;
        }

        // Track view_top event
        if (window.trackEvent) trackEvent('view_top');

        const topPartners = appData.top_partners || [];

        // Check locked state (unless already unlocked in state)
        // Logic: You see TOP list only if you are TOP Member or it's free
        // For now, allow viewing but maybe show blur if locked (future feature)
        // Current logic: Show list regardless, but prompts to "Buy TOP" elsewhere.

        const container = document.getElementById('top-list');
        if (container) {
            container.innerHTML = '';

            const topStatus = appData.user?.top_status || 'locked';
            const canUnlock = appData.earnings?.can_unlock_top || false;

            // Logic: Show TOP only if unlocked or eligible (5+ invites)
            const isUnlocked = topStatus !== 'locked' || canUnlock;

            if (!isUnlocked) {
                // Render Locked State
                const invitesNeeded = appData.earnings?.invites_needed || 5;
                const buyPrice = appData.earnings?.buy_top_price || 1;

                container.innerHTML = `
                    <div class="top-locked-state">
                        <div class="locked-icon">🔒</div>
                        <h3>${appData.translations?.top_locked_title || 'TOP Locked'}</h3>
                        <p>${appData.translations?.top_locked_subtitle || `Invite ${invitesNeeded} more friends to unlock TOP partners or buy access.`}</p>
                        
                        <div class="locked-actions">
                            <button class="top-buy-btn" onclick="Actions.buyTop()">
                                ${appData.translations?.btn_unlock_top || `Unlock for ${buyPrice} Stars`}
                            </button>
                            <button class="top-share-btn" onclick="Actions.share()">
                                ${appData.translations?.share_button || 'Invite Friends'}
                            </button>
                        </div>
                    </div>
                `;
                return;
            }

            if (topPartners.length === 0) {
                container.innerHTML = `<p class="empty-state">${AppState.getAppData()?.translations?.no_top_bots || 'TOP ботів поки немає'}</p>`;
                return;
            }

            // Render header
            const header = document.createElement('div');
            header.className = 'top-header';
            header.innerHTML = `
                <h2>🏆 ${AppState.getAppData()?.translations?.top_profits_title || 'Most Profitable'}</h2>
                <p class="top-subtitle">${AppState.getAppData()?.translations?.top_profits_subtitle || 'Найвигідніші пропозиції тижня'}</p>
            `;
            container.appendChild(header);

            // Render list
            this.renderList(topPartners);
        }
    },

    renderList(partners) {
        const container = document.getElementById('top-list');
        if (!container) return;

        const listContainer = document.createElement('div');
        listContainer.className = 'top-list-container';

        partners.forEach((partner, index) => {
            const partnerId = partner.id || `top-${index}`;
            const partnerIdStr = typeof partnerId === 'string' ? partnerId : String(partnerId);

            const item = document.createElement('div');
            // Add top-podium classes for 1st, 2nd, 3rd
            let podiumClass = '';
            if (index === 0) podiumClass = 'podium-gold';
            else if (index === 1) podiumClass = 'podium-silver';
            else if (index === 2) podiumClass = 'podium-bronze';

            item.className = `top-item-card ${podiumClass}`;
            item.setAttribute('data-rank', index + 1);

            // Add click handler
            item.addEventListener('click', (e) => {
                if (e.target.tagName === 'BUTTON') return;

                if (window.Haptic) Haptic.light();
                if (window.trackEvent) trackEvent('top_partner_click_direct', { partner_id: partnerIdStr, rank: index + 1 });

                const link = partner.referral_link || partner.link; // Fallback

                // Direct open logic
                if (window.Actions && window.Actions.openPartner) {
                    Actions.openPartner(link, partnerIdStr);
                } else {
                    if (link) window.open(link, '_blank');
                }
            });


            // Rank badge style
            let rankBadge = `<span class="rank-number">#${index + 1}</span>`;
            if (index === 0) rankBadge = `<span class="rank-icon">🥇</span>`;
            if (index === 1) rankBadge = `<span class="rank-icon">🥈</span>`;
            if (index === 2) rankBadge = `<span class="rank-icon">🥉</span>`;

            const partnerName = partner.name || 'Bot';
            const partnerImage = partner.image_url || '/static/mini-app/icon.png';
            const commission = partner.commission || 0;
            const score = partner.roi_score || 0;
            const scoreDisplay = score > 0 ? `🔥 ${score}/10` : `🔥 High`;

            // Extract username from link for fallback
            let tgFallbackUrl = null;
            const linkForFallback = partner.referral_link || partner.link;
            if (linkForFallback && linkForFallback.includes('t.me/')) {
                const parts = linkForFallback.split('t.me/');
                if (parts[1]) {
                    const username = parts[1].split(/[/?#]/)[0];
                    if (username) {
                        tgFallbackUrl = `https://t.me/i/userpic/320/${username}.jpg`;
                    }
                }
            }

            const link = partner.referral_link || partner.link;

            // Updated Layout: Grid for Podium/Card
            item.innerHTML = `
                <div class="top-row-left">
                    <div class="top-rank-wrapper">${rankBadge}</div>
                    <img src="${partnerImage}" alt="${escapeHtml(partnerName)}" class="top-icon-new" onerror="handleImageError(this, '${escapeHtml(partnerName)}', '${tgFallbackUrl || ''}')">
                </div>
                <div class="top-row-middle">
                    <div class="top-name-new">${escapeHtml(partnerName)}</div>
                    <div class="top-metrics">
                        <span class="metric-score">${scoreDisplay}</span>
                        ${commission > 0 ? `<span class="metric-separator">•</span><span class="metric-commission">${commission}% share</span>` : ''}
                    </div>
                </div>
                <div class="top-row-right">
                    <button class="top-open-btn-pill" onclick="event.stopPropagation(); window.Actions && window.Actions.openPartner ? Actions.openPartner('${link}', '${partnerIdStr}') : window.open('${link}', '_blank')">
                        OPEN
                    </button>
                </div>
            `;

            listContainer.appendChild(item);
        });

        container.appendChild(listContainer);
    }
};

// Export to global scope
window.renderTop = () => window.Pages.Top.render();
