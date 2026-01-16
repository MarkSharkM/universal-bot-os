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

            // Get navigation element for positioning
            const topPage = document.getElementById('top-page');
            const tabs = document.querySelector('.tabs');

            if (!isUnlocked) {
                // Add locked state class to page
                if (topPage) topPage.classList.add('locked-state');

                // Move tabs to top
                if (tabs) tabs.classList.add('position-top');

                // Render Locked State with new card-based UI
                const invitesNeeded = appData.earnings?.invites_needed || 5;
                const currentInvites = appData.earnings?.total_invited || 0;
                const buyPrice = appData.earnings?.buy_top_price || 1;
                const t = appData.translations || {};

                // Create progress segments
                const goal = appData.earnings?.required_invites || 5;
                const current = Math.min(currentInvites, goal);
                const progressSegments = Array.from({ length: goal }).map((_, i) => {
                    const isActive = i < current;
                    return `<div class="seg ${isActive ? 'filled' : ''}"></div>`;
                }).join('');

                const invitedLabel = (t.invited_count || '{{count}} запрошено').replace('{{count}}', current);
                const goalLabel = (t.goal_text || 'Ціль: {{goal}}').replace('{{goal}}', goal);
                const subtitle = (t.top_locked_subtitle || 'Запроси ще {{count}} друзів, щоб відкрити доступ до ексклюзивних пропозицій').replace('{{count}}', invitesNeeded);
                const btnBuyLabel = (t.btn_unlock_top || '💎 Купити ({{price}}⭐)').replace('{{price}}', buyPrice).replace('{{buy_top_price}}', buyPrice);
                const btnInviteLabel = t.invite_and_earn || '🚀 Запросити';

                container.innerHTML = `
                    <div class="top-locked-container">
                        <!-- Single Unified Card -->
                        <div class="top-status-card">
                            <!-- Lock Icon inside card -->
                            <div class="lock-icon-wrapper">🔒</div>
                            
                            <h3>${t.top_locked_title || 'TOP заблоковано'}</h3>
                            <p>${subtitle}</p>
                            
                            <!-- Progress Section -->
                            <div class="top-progress-section">
                                <div class="progress-label">${t.my_progress || 'Мій прогрес'}: ${current}/${goal}</div>
                                <div class="progress-segments">
                                    ${progressSegments}
                                </div>
                                <div class="progress-stats">
                                    <span>${invitedLabel}</span>
                                    <span class="text-gold">${goalLabel}</span>
                                </div>
                            </div>
                            
                            <!-- Action Buttons -->
                            <div class="top-locked-actions">
                                <button class="top-buy-btn-new" onclick="Actions.buyTop()">
                                    ${btnBuyLabel}
                                </button>
                                <button class="top-invite-btn-new" onclick="Actions.share()">
                                    ${btnInviteLabel}
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                return;
            }

            // Remove locked state class when unlocked
            if (topPage) topPage.classList.remove('locked-state');

            // Return tabs to bottom when unlocked
            if (tabs) tabs.classList.remove('position-top');

            if (topPartners.length === 0) {
                container.innerHTML = `<p class="empty-state">${AppState.getAppData()?.translations?.no_top_bots || 'TOP ботів поки немає'}</p>`;
                return;
            }

            // Render header
            const header = document.createElement('div');
            header.className = 'top-header';
            const t = appData.translations || {};
            header.innerHTML = `
                <h2>🏆 ${t.top_profits_title || 'ТОП партнери'}</h2>
                <p class="top-subtitle">${t.top_profits_subtitle || 'Найвигідніші пропозиції тижня'}</p>
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

            const partnerName = partner.name || 'Bot';
            // Fix: Check partner.icon / partner.image specifically as backend provides those keys
            const partnerImage = partner.icon || partner.image || partner.image_url || tgFallbackUrl || '/static/mini-app/icon.png';

            const commission = partner.commission || 0;
            const score = partner.roi_score || 0;
            const scoreDisplay = score > 0 ? `🔥 ${score}/10` : `🔥 High`;

            const link = partner.referral_link || partner.link;

            const t = AppState.getAppData()?.translations || {};
            const commissionLabel = (t.estimated_share || '{{percent}}% share').replace('{{percent}}', commission);

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
                        ${commission > 0 ? `<span class="metric-separator">•</span><span class="metric-commission">${commissionLabel}</span>` : ''}
                    </div>
                </div>
                <div class="top-row-right">
                    <button class="top-open-btn-pill" onclick="event.stopPropagation(); window.Actions && window.Actions.openPartner ? Actions.openPartner('${link}', '${partnerIdStr}') : window.open('${link}', '_blank')">
                        ${t.open_btn || 'Відкрити ↗'}
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
