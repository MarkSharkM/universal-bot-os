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
                <h2>🏆 ${AppState.getAppData()?.translations?.top_bots_title || 'TOP Telegram Bots'}</h2>
                <p class="top-subtitle">${AppState.getAppData()?.translations?.top_bots_subtitle || 'Найпопулярніші боти цього тижня'}</p>
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
            item.className = 'top-item';
            item.setAttribute('data-rank', index + 1);

            // Add click handler
            item.addEventListener('click', () => {
                if (window.Haptic) Haptic.light();
                if (window.trackEvent) trackEvent('top_partner_click_direct', { partner_id: partnerIdStr, rank: index + 1 });

                // Direct open logic (Skip Detail View)
                if (window.Actions && window.Actions.openPartner) {
                    Actions.openPartner(partner.link, partnerIdStr);
                } else {
                    // Fallback
                    const link = partner.link;
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
            // Users count removed to match bot logic

            // Extract username from link for fallback
            let tgFallbackUrl = null;
            if (partner.link && partner.link.includes('t.me/')) {
                const parts = partner.link.split('t.me/');
                if (parts[1]) {
                    const username = parts[1].split(/[/?#]/)[0];
                    if (username) {
                        tgFallbackUrl = `https://t.me/i/userpic/320/${username}.jpg`;
                    }
                }
            }

            item.innerHTML = `
                <div class="top-rank">${rankBadge}</div>
                <img src="${partnerImage}" alt="${escapeHtml(partnerName)}" class="top-icon" onerror="handleImageError(this, '${escapeHtml(partnerName)}', '${tgFallbackUrl || ''}')">
                <div class="top-info">
                    <div class="top-name">${escapeHtml(partnerName)}</div>
                    <div class="top-meta">
                        <span class="top-category">${partner.category || 'App'}</span>
                    </div>
                </div>
                <div class="top-action">
                    <button class="top-btn">Open</button>
                </div>
            `;

            listContainer.appendChild(item);
        });

        container.appendChild(listContainer);
    }
};

// Export to global scope
window.renderTop = () => window.Pages.Top.render();
