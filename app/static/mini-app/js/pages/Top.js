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
                // FIRST: Render TOP partners list in background (with reduced opacity)
                if (topPartners.length > 0) {
                    // Render header
                    const header = document.createElement('div');
                    header.className = 'top-header';
                    const t = appData.translations || {};
                    header.innerHTML = `
                        <h2>🏆 ${t.top_profits_title || 'ТОП партнери'}</h2>
                        <p class="top-subtitle">${t.top_profits_subtitle || 'Найвигідніші пропозиції тижня'}</p>
                    `;
                    header.style.opacity = '0.3'; // Dim the header
                    container.appendChild(header);

                    // Render partners list with reduced opacity
                    const listContainer = document.createElement('div');
                    listContainer.className = 'top-list-container';
                    listContainer.style.opacity = '0.3'; // Dim the list
                    listContainer.style.filter = 'blur(2px)'; // Slight blur

                    topPartners.forEach((partner, index) => {
                        const partnerId = partner.id || `top-${index}`;
                        const partnerIdStr = typeof partnerId === 'string' ? partnerId : String(partnerId);

                        const item = document.createElement('div');
                        let podiumClass = '';
                        if (index === 0) podiumClass = 'podium-gold';
                        else if (index === 1) podiumClass = 'podium-silver';
                        else if (index === 2) podiumClass = 'podium-bronze';

                        item.className = `top-item-card ${podiumClass}`;
                        item.setAttribute('data-rank', index + 1);

                        let rankBadge = `<span class="rank-number">#${index + 1}</span>`;
                        if (index === 0) rankBadge = `<span class="rank-icon">🥇</span>`;
                        if (index === 1) rankBadge = `<span class="rank-icon">🥈</span>`;
                        if (index === 2) rankBadge = `<span class="rank-icon">🥉</span>`;

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
                        const partnerImage = partner.icon || partner.image || partner.image_url || tgFallbackUrl || '/static/mini-app/icon.png';
                        const commission = partner.commission || 0;
                        const score = partner.roi_score || 0;
                        const scoreDisplay = score > 0 ? `🔥 ${score}/10` : `🔥 High`;
                        const link = partner.referral_link || partner.link;
                        const commissionLabel = (t.estimated_share || '{{percent}}% share').replace('{{percent}}', commission);

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
                                <button class="top-open-btn-pill" disabled style="opacity: 0.5;">
                                    ${t.open_btn || 'Відкрити ↗'}
                                </button>
                            </div>
                        `;

                        listContainer.appendChild(item);
                    });

                    container.appendChild(listContainer);
                }

                // SECOND: Render locked overlay on top
                const invitesNeeded = appData.earnings?.invites_needed || 5;
                const currentInvites = appData.user?.total_invited || 0;  // FIXED: Read from user object
                const buyPrice = appData.earnings?.buy_top_price || 1;
                const t = appData.translations || {};

                const goal = appData.earnings?.required_invites || 5;
                const current = Math.min(currentInvites, goal);
                const subtitle = (t.top_locked_subtitle || 'Запроси ще {{count}} друзів, щоб відкрити доступ до ексклюзивних пропозицій').replace('{{count}}', invitesNeeded);
                const progressWidth = Math.round((current / goal) * 100);

                // Create overlay element
                const overlay = document.createElement('div');
                overlay.style.cssText = 'position: fixed; top: 60px; left: 0; right: 0; bottom: 80px; display: flex; align-items: center; justify-content: center; padding: 20px 16px; z-index: 50; pointer-events: none;';
                overlay.innerHTML = `
                    <div style="background: #16181D; backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 24px; padding: 32px 28px; width: 100%; max-width: 380px; text-align: center; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); pointer-events: auto;">
                        <!-- Lock Icon in Rounded Box -->
                        <div style="width: 72px; height: 72px; margin: 0 auto 20px; background: rgba(255, 200, 50, 0.15); border: 2px solid rgba(255, 200, 50, 0.3); border-radius: 18px; display: flex; align-items: center; justify-content: center;">
                            <span style="font-size: 36px; filter: drop-shadow(0 2px 8px rgba(255, 200, 50, 0.4));">🔒</span>
                        </div>
                        
                        <h2 style="font-size: 20px; font-weight: 700; color: #fff; margin: 0 0 10px; line-height: 1.3;">${t.top_locked_title || '🔒 Розблокуй TOP Статус'}</h2>
                        <p style="font-size: 14px; color: rgba(255, 255, 255, 0.6); margin: 0 0 24px; line-height: 1.5;">${subtitle}</p>
                        
                        <!-- Progress Section -->
                        <div style="margin-bottom: 24px; text-align: left;">
                            <div style="display: flex; justify-content: space-between; font-size: 13px; color: rgba(255, 255, 255, 0.7); margin-bottom: 8px; font-weight: 600;">
                                <span>${t.my_progress || 'Мій прогрес'}:</span>
                                <span style="color: #fff; font-weight: 700;">${current} / ${goal}</span>
                            </div>
                            <div style="height: 8px; background: rgba(255, 255, 255, 0.1); border-radius: 4px; overflow: hidden;">
                                <div style="height: 100%; width: ${progressWidth}%; background: linear-gradient(90deg, #00c853, #69f0ae); border-radius: 4px; transition: width 0.3s ease;"></div>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 11px; color: rgba(255, 255, 255, 0.5); margin-top: 8px;">
                                <span>${t.invited_label || 'Запрошено'}: ${current}</span>
                                <span>• ${t.goal_label || 'Ціль'}: ${goal}</span>
                            </div>
                        </div>
                        
                        <!-- Action Buttons -->
                        <div style="display: flex; gap: 12px;">
                            <button onclick="Actions.handleBuyTop(${buyPrice})" style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; padding: 16px 20px; border-radius: 14px; font-weight: 700; font-size: 15px; cursor: pointer; border: 1px solid rgba(100, 150, 200, 0.3); background: linear-gradient(135deg, #1e3a5f, #2d4a6f); color: #fff; min-width: 140px;">
                                <span style="font-size: 20px;">💎</span>
                                <span>${t.buy_top_btn || 'Купити'}</span>
                                <span style="font-size: 11px; opacity: 0.7;">(${buyPrice} ⭐)</span>
                            </button>
                            <button onclick="Actions.shareReferralLink()" style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 8px; padding: 16px 20px; border-radius: 14px; font-weight: 700; font-size: 15px; cursor: pointer; border: none; background: linear-gradient(135deg, #00c853, #00e676); color: #000; box-shadow: 0 4px 16px rgba(0, 200, 83, 0.35); min-width: 140px;">
                                <span style="font-size: 20px;">🚀</span>
                                <span>${t.share_btn || 'Запросити'}</span>
                            </button>
                        </div>
                    </div>
                `;

                container.appendChild(overlay);
                return;
            }

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
                if (window.trackEvent) trackEvent('top_partner_click_direct', { partner_id: partnerIdStr, partner_name: partnerName, rank: index + 1 });

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
