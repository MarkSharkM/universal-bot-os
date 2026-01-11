/**
 * Partners Page Component
 * Handles rendering of the Partners tab and list.
 */

window.Pages = window.Pages || {};

window.Pages.Partners = {
    render() {
        console.log('[Pages.Partners] rendering...');

        const appData = AppState.getAppData();
        if (!appData) {
            console.warn('[Pages.Partners] appData not available');
            return;
        }

        // Ensure we're on the partners page
        const partnersPage = document.getElementById('partners-page');
        if (!partnersPage || !partnersPage.classList.contains('active')) {
            console.warn('[Pages.Partners] partners page not active');
            return;
        }

        // Track view_partners event
        if (window.trackEvent) trackEvent('view_partners');

        AppState.setFilteredPartners([]);
        const partners = appData.partners || [];

        if (partners.length === 0) {
            const container = document.getElementById('partners-list');
            if (container) {
                container.innerHTML = `<p class="empty-state">${AppState.getAppData()?.translations?.no_partners || 'Партнерів поки немає'}</p>`;
            }
            return;
        }

        // Check if expanded view
        const isExpanded = AppState.getPartnersExpanded();

        // Sort partners: Conversion (commission) first, then popularity
        const sortedPartners = [...partners].sort((a, b) => {
            // Primary: commission (conversion)
            const commissionDiff = (b.commission || 0) - (a.commission || 0);
            if (Math.abs(commissionDiff) > 0.1) {
                return commissionDiff;
            }
            return 0;
        });

        // Show 5 partners by default, all if expanded
        const partnersToShow = isExpanded ? sortedPartners : sortedPartners.slice(0, 5);

        // Render recommended header if not expanded
        const container = document.getElementById('partners-list');
        if (container) {
            container.innerHTML = '';

            if (!isExpanded) {
                const header = document.createElement('div');
                header.className = 'partners-recommended-header';
                header.innerHTML = `
                    <h2>🔮 ${AppState.getAppData()?.translations?.recommended_title || 'Recommended for you'}</h2>
                    <p class="recommended-subtitle">${AppState.getAppData()?.translations?.recommended_subtitle || 'Партнери, які найчастіше запускають шлях'}</p>
                `;
                container.appendChild(header);
            } else {
                // Show search & filters when expanded
                const pageHeader = document.getElementById('partners-page-header');
                if (pageHeader) {
                    pageHeader.style.display = 'block';
                    // Setup search and filters
                    if (typeof Navigation !== 'undefined' && Navigation.setupSearchAndFilters) {
                        Navigation.setupSearchAndFilters();
                    }
                }
            }

            // Render partners list
            this.renderList(partnersToShow, isExpanded);

            // Add "Show more" button if not expanded and there are more partners
            if (!isExpanded && sortedPartners.length > 5) {
                const showMoreBtn = document.createElement('button');
                showMoreBtn.className = 'show-more-btn';
                showMoreBtn.textContent = AppState.getAppData()?.translations?.show_all || 'Показати всіх';
                showMoreBtn.addEventListener('click', () => {
                    if (window.trackEvent) trackEvent('partners_expanded');
                    AppState.setPartnersExpanded(true);
                    this.render(); // Re-render with expanded view
                });
                container.appendChild(showMoreBtn);
            }
        }
    },

    renderList(partners, isExpanded = false) {
        const container = document.getElementById('partners-list');
        if (!container) return;

        const appData = AppState.getAppData();

        if (partners.length === 0) {
            const emptyState = document.createElement('p');
            emptyState.className = 'empty-state';
            emptyState.textContent = AppState.getAppData()?.translations?.no_partners_found || 'Партнерів не знайдено';
            container.appendChild(emptyState);
            return;
        }

        // Create partners grid container if not exists
        let gridContainer = container.querySelector('.partners-grid');
        if (!gridContainer) {
            gridContainer = document.createElement('div');
            gridContainer.className = 'partners-grid';
            container.appendChild(gridContainer);
        } else {
            gridContainer.innerHTML = ''; // Clear existing
        }

        partners.forEach((partner, index) => {
            const partnerId = partner.id || `temp-${index}`;
            const partnerIdStr = typeof partnerId === 'string' ? partnerId : String(partnerId);
            const isTop = (appData.top_partners || []).some(p => String(p.id) === String(partner.id));

            // Labels removed to match bot logic
            const labels = [];

            // Create card element
            const card = document.createElement('div');
            card.className = `partner-compact-row ${isTop ? 'top-partner-highlight' : ''}`;
            card.setAttribute('data-partner-id', partnerIdStr);

            // Add click handler for card
            card.addEventListener('click', (e) => {
                // Prevent trigger if clicking button directly (handled by button's own listener if needed, but here simple click is fine)
                if (e.target.tagName === 'BUTTON') return;

                if (window.Haptic) Haptic.light();
                if (window.trackEvent) trackEvent('partner_click_direct', { partner_id: partnerIdStr });

                const link = partner.referral_link || partner.link;
                if (window.Actions && window.Actions.openPartner) {
                    Actions.openPartner(link, partnerIdStr);
                } else {
                    if (link) window.open(link, '_blank');
                }
            });

            const partnerName = partner.name || 'Partner';
            const partnerImage = partner.image_url || '/static/mini-app/icon.png';

            // Defines the "Profit Badge" text
            // Use localized description from backend (handles 5 languages)
            // Allow up to 60 chars (approx 2 lines)
            const description = partner.description || partner.short_description || 'Telegram App';
            const badgeText = description.length > 60 ? description.substring(0, 60) + '...' : description;

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

            // Compact Row Layout: Logo | Info | Button
            // Using inline onclick for button to handle the specific action and stop propagation if needed
            const link = partner.referral_link || partner.link;

            card.innerHTML = `
                <div class="partner-row-left">
                    <img src="${partnerImage}" alt="${escapeHtml(partnerName)}" class="partner-logo-compact" onerror="handleImageError(this, '${escapeHtml(partnerName)}', '${tgFallbackUrl || ''}')">
                </div>
                <div class="partner-row-middle">
                    <h3 class="partner-title-compact">${escapeHtml(partnerName)}</h3>
                    <div class="partner-badge-compact">${escapeHtml(badgeText)}</div>
                </div>
                <div class="partner-row-right">
                    <button class="partner-open-btn-pill" onclick="event.stopPropagation(); window.Actions && window.Actions.openPartner ? Actions.openPartner('${link}', '${partnerIdStr}') : window.open('${link}', '_blank')">
                        OPEN
                    </button>
                </div>
            `;

            gridContainer.appendChild(card);
        });
    },

    renderPartnerDetail(partnerId) {
        console.log('[Pages.Partners] renderDetail:', partnerId);
        const appData = AppState.getAppData();
        if (!appData) return;

        const partners = [...(appData.partners || []), ...(appData.top_partners || [])];
        const partner = partners.find(p => String(p.id) === String(partnerId));

        if (!partner) {
            console.error('Partner not found:', partnerId);
            return;
        }

        const container = document.getElementById('partner-detail-content');
        const nameEl = document.getElementById('partner-detail-name');

        if (nameEl) nameEl.textContent = partner.name || 'Partner Detail';
        if (!container) return;

        const partnerImage = partner.image_url || '/static/mini-app/icon.png';
        const commission = partner.commission || 0;

        // Extract username for fallback (same logic)
        let tgFallbackUrl = null;
        if (partner.link && partner.link.includes('t.me/')) {
            const parts = partner.link.split('t.me/');
            if (parts[1]) {
                const username = parts[1].split(/[/?#]/)[0];
                if (username) tgFallbackUrl = `https://t.me/i/userpic/320/${username}.jpg`;
            }
        }

        container.innerHTML = `
            <div class="detail-hero">
                <img src="${partnerImage}" class="detail-icon" alt="${escapeHtml(partner.name)}" onerror="handleImageError(this, '${escapeHtml(partner.name)}', '${tgFallbackUrl || ''}')">
                <div class="detail-badges">
                    <span class="detail-badge success">${commission}% Share</span>
                    <span class="detail-badge info">${partner.category || 'App'}</span>
                </div>
            </div>

            <div class="detail-section">
                <h3>📜 Description</h3>
                <p>${escapeHtml(partner.description || partner.short_description || 'No description available.')}</p>
            </div>

            <div class="detail-section">
                 <h3>🔗 Link</h3>
                 <div class="detail-link-box">
                    <span>${partner.link || 'No link'}</span>
                    <button class="copy-btn" onclick="Utils.copyToClipboard('${partner.link}')">Copy</button>
                 </div>
            </div>

            <button class="cta-btn main-action-btn" onclick="window.Telegram.WebApp.openTelegramLink('${partner.link}')">
                🚀 Launch ${escapeHtml(partner.name)}
            </button>
        `;
    }
};

// Export to global scope
window.renderPartners = () => window.Pages.Partners.render();
window.renderPartnersList = (p, e) => window.Pages.Partners.renderList(p, e);
window.renderPartnerDetail = (id) => window.Pages.Partners.renderPartnerDetail(id);
