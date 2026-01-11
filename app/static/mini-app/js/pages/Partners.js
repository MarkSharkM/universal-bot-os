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

            const labels = [];
            if (isTop) labels.push(`⭐ ${AppState.getAppData()?.translations?.label_top || 'TOP'}`);
            if ((partner.commission || 0) >= 5) labels.push(`🔥 ${AppState.getAppData()?.translations?.label_hot || 'часто купують'}`);
            if ((partner.commission || 0) < 3) labels.push(`🛡 ${AppState.getAppData()?.translations?.label_safe || 'для новачків'}`);
            if (index < 2) labels.push(`⚡ ${AppState.getAppData()?.translations?.label_fast || 'швидкий старт'}`);

            // Create card element
            const card = document.createElement('div');
            card.className = `partner-card ${isTop ? 'top-partner' : ''}`;
            card.setAttribute('data-partner-id', partnerIdStr);

            // Add click handler for card
            card.addEventListener('click', () => {
                if (window.Haptic) Haptic.light();
                if (window.trackEvent) trackEvent('partner_open', { partner_id: partnerIdStr });

                if (typeof Navigation !== 'undefined' && Navigation.showPartnerDetail) {
                    Navigation.showPartnerDetail(partnerIdStr);
                } else if (typeof showPartnerDetail === 'function') {
                    showPartnerDetail(partnerIdStr);
                } else {
                    // Inside Pages.Partners, we might need a reference or global
                    if (window.Render && window.Render.renderPartnerDetail) {
                        // Navigation usually handles showPartnerDetail which calls renderPartnerDetail
                        // but for now let's assume global or Navigation is present
                    }
                }
            });

            const partnerName = partner.name || 'Partner';
            const partnerImage = partner.image_url || '/static/mini-app/icon.png';
            const commission = partner.commission || 0;

            // Extract username from link for fallback
            let tgFallbackUrl = null;
            if (partner.link && partner.link.includes('t.me/')) {
                const parts = partner.link.split('t.me/');
                if (parts[1]) {
                    const username = parts[1].split(/[/?#]/)[0]; // Remove ?start=... or /
                    if (username) {
                        tgFallbackUrl = `https://t.me/i/userpic/320/${username}.jpg`;
                    }
                }
            }

            card.innerHTML = `
                <div class="partner-header">
                    <img src="${partnerImage}" alt="${escapeHtml(partnerName)}" class="partner-icon" onerror="handleImageError(this, '${escapeHtml(partnerName)}', '${tgFallbackUrl || ''}')">
                    <div class="partner-info">
                        <div class="partner-name-row">
                            <h3 class="partner-name">${escapeHtml(partnerName)}</h3>
                            ${isTop ? '<span class="verified-badge">✓</span>' : ''}
                        </div>
                        <div class="commission-badge">
                            <span class="commission-value">${commission}%</span>
                            <span class="commission-label">share</span>
                        </div>
                    </div>
                </div>
                
                ${labels.length > 0 ? `
                <div class="partner-labels">
                    ${labels.slice(0, 3).map(label => `<span class="partner-label">${label}</span>`).join('')}
                </div>
                ` : ''}

                <div class="partner-description">
                    ${escapeHtml(partner.short_description || partner.description || 'Офіційний партнер Telegram')}
                </div>

                <div class="partner-rating">
                    ${'★'.repeat(Math.min(5, Math.ceil(commission / 2)))}${'☆'.repeat(5 - Math.min(5, Math.ceil(commission / 2)))}
                    <span class="rating-value">(${commission}/10)</span>
                </div>

                <button class="partner-btn">
                    ${AppState.getAppData()?.translations?.open || 'Відкрити'}
                </button>
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
