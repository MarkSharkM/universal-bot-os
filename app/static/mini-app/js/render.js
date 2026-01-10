/**
 * Render Module
 * All rendering functions and UI helpers
 */

// Note: Uses AppState for global state access
// Note: Functions reference other modules (Navigation, Actions) which will be loaded

function renderApp() {
    const appData = AppState.getAppData();
    if (!appData) return;

    // Apply bot.config customizations
    if (appData.config) {
        // applyBotConfig will be in app.js
        if (typeof applyBotConfig === 'function') {
            applyBotConfig(appData.config);
        }
    }

    // Update bot name
    const botNameEl = document.getElementById('bot-name');
    if (botNameEl) {
        botNameEl.textContent = appData.config?.name || 'Mini App';

        // Developer Mode: Hard Reset (5 taps)
        let tapCount = 0;
        let lastTapTime = 0;

        // Remove old listener to avoid duplicates if re-rendered (though usually renderApp called once)
        const newEl = botNameEl.cloneNode(true);
        botNameEl.parentNode.replaceChild(newEl, botNameEl);

        newEl.addEventListener('click', () => {
            const now = Date.now();
            if (now - lastTapTime > 1000) {
                tapCount = 0; // Reset if too slow
            }

            tapCount++;
            lastTapTime = now;

            if (tapCount >= 5) {
                // Trigger Hard Reset
                tapCount = 0;
                if (typeof handleHardReset === 'function') {
                    handleHardReset();
                } else {
                    // Inline fallback if function not defined globaly
                    const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
                    storage.clear();
                    if (typeof Toast !== 'undefined') Toast.info('♻️ Factory Reset Initiated...');
                    setTimeout(() => window.location.reload(), 1000);
                }
            }
        });
    }

    // Translate static elements in index.html
    translateStaticElements();

    // Extract state from appData for Revenue Launcher
    if (appData.user) {
        // Extract referral count and TOP status from user data
        const referralCount = appData.user.total_invited || 0;
        const topStatus = appData.user.top_status || 'locked';

        AppState.setReferralCount(referralCount);
        AppState.setTopLocked(topStatus === 'locked');
    } else if (appData.earnings) {
        // Fallback: extract from earnings data if user data not available
        const referralCount = appData.earnings.total_invited || 0;
        const topStatus = appData.earnings.top_status || 'locked';

        AppState.setReferralCount(referralCount);
        AppState.setTopLocked(topStatus === 'locked');
    }

    // Check if user started 7% flow (from localStorage or custom_data)
    const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
    const didStart7Flow = storage.getItem('did_start_7_flow') === 'true' ||
        (appData.user && appData.user.custom_data && appData.user.custom_data.did_start_7_flow);
    AppState.setDidStart7Flow(didStart7Flow);

    // Check onboarding status
    const hasSeenOnboarding = storage.getItem('has_seen_onboarding') === 'true' ||
        (appData.user && appData.user.custom_data && appData.user.custom_data.has_seen_onboarding);
    AppState.setHasSeenOnboarding(hasSeenOnboarding);

    // Render initial tab (HOME - Action Engine)
    // Note: switchTab is called from loadAppData, not here, to avoid double call
}

function renderPartners() {
    console.log('[Render] renderPartners: starting');

    const appData = AppState.getAppData();
    if (!appData) {
        console.warn('[Render] renderPartners: appData not available');
        return;
    }

    // Ensure we're on the partners page
    const partnersPage = document.getElementById('partners-page');
    const topPage = document.getElementById('top-page');
    const homePage = document.getElementById('home-page');

    console.log('[Render] renderPartners: partners-page active?', partnersPage?.classList.contains('active'));
    console.log('[Render] renderPartners: top-page active?', topPage?.classList.contains('active'));
    console.log('[Render] renderPartners: home-page active?', homePage?.classList.contains('active'));

    if (!partnersPage) {
        console.error('[Render] renderPartners: partners-page element not found');
        return;
    }

    if (!partnersPage.classList.contains('active')) {
        console.warn('[Render] renderPartners: partners page is not active, skipping render');
        return;
    }

    // Track view_partners event
    trackEvent('view_partners');

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
        // Secondary: popularity (if available in data)
        // For now, just use commission
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
        renderPartnersList(partnersToShow, isExpanded);

        // Add "Show more" button if not expanded and there are more partners
        if (!isExpanded && sortedPartners.length > 5) {
            const showMoreBtn = document.createElement('button');
            showMoreBtn.className = 'show-more-btn';
            showMoreBtn.textContent = AppState.getAppData()?.translations?.show_all || 'Показати всіх';
            showMoreBtn.addEventListener('click', () => {
                trackEvent('partners_expanded');
                AppState.setPartnersExpanded(true);
                renderPartners(); // Re-render with expanded view
            });
            container.appendChild(showMoreBtn);
        }
    }
}

function renderPartnersList(partners, isExpanded = false) {
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

    // Use DocumentFragment for batch DOM operations
    const fragment = document.createDocumentFragment();

    partners.forEach((partner, index) => {
        const partnerId = partner.id || `temp-${index}`;
        const partnerIdStr = typeof partnerId === 'string' ? partnerId : String(partnerId);
        const isTop = (appData.top_partners || []).some(p => String(p.id) === String(partner.id));
        const referralLink = partner.referral_link || '';

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
            if (typeof Haptic !== 'undefined') Haptic.light();
            trackEvent('partner_open', { partner_id: partnerIdStr });
            if (typeof Navigation !== 'undefined' && Navigation.showPartnerDetail) {
                Navigation.showPartnerDetail(partnerIdStr);
            } else {
                showPartnerDetail(partnerIdStr);
            }
        });

        // Create header
        const header = document.createElement('div');
        header.className = 'partner-header';

        // Add partner icon if available
        const iconUrl = partner.icon || partner.image || '';
        if (iconUrl) {
            const icon = document.createElement('img');
            icon.className = 'partner-icon';
            icon.src = iconUrl;
            icon.alt = partner.name || 'Partner';
            icon.onerror = function () {
                // Hide icon if image fails to load
                this.style.display = 'none';
            };
            header.appendChild(icon);
        }

        const name = document.createElement('h3');
        name.className = 'partner-name';
        name.textContent = partner.name || 'Unknown';

        const badge = document.createElement('span');
        badge.className = `commission-badge ${isTop ? 'top-badge' : ''}`;
        badge.textContent = `${partner.commission || 0}%`;

        header.appendChild(name);
        header.appendChild(badge);

        // Create labels
        if (labels.length > 0) {
            const labelsContainer = document.createElement('div');
            labelsContainer.className = 'partner-labels';
            labels.forEach(label => {
                const labelEl = document.createElement('span');
                labelEl.className = 'partner-label';
                labelEl.textContent = label;
                labelsContainer.appendChild(labelEl);
            });
            card.appendChild(labelsContainer);
        }

        // Create description
        const description = document.createElement('p');
        description.className = 'partner-description';
        const descText = (partner.description || '').substring(0, 100);
        description.textContent = descText + (partner.description && partner.description.length > 100 ? '...' : '');

        const button = document.createElement('button');
        button.className = 'partner-btn';
        button.textContent = `▶️ ${AppState.getAppData()?.translations?.open || 'Відкрити'}`;
        button.setAttribute('aria-label', `${AppState.getAppData()?.translations?.open || 'Відкрити'} ${partner.name || 'Unknown'}`);
        button.addEventListener('click', (e) => {
            e.stopPropagation();
            if (typeof Haptic !== 'undefined') Haptic.medium();
            trackEvent('partner_click', { partner_id: partnerIdStr });
            if (typeof trackPartnerClickForPopup === 'function') {
                trackPartnerClickForPopup(); // Track for auto-popup trigger
            }
            if (typeof Actions !== 'undefined' && Actions.openPartner) {
                Actions.openPartner(referralLink, partnerIdStr);
            } else {
                openPartner(referralLink, partnerIdStr);
            }
        });

        // Assemble card
        card.appendChild(header);
        card.appendChild(description);
        card.appendChild(button);

        fragment.appendChild(card);
    });

    gridContainer.appendChild(fragment);
}

function renderPartnerDetail(partnerId) {
    const appData = AppState.getAppData();
    if (!appData || !partnerId) return;

    const allPartners = [...(appData.partners || []), ...(appData.top_partners || [])];
    // Compare as strings to handle UUIDs correctly
    const partner = allPartners.find(p => String(p.id) === String(partnerId));

    if (!partner) {
        const content = document.getElementById('partner-detail-content');
        if (content) {
            content.innerHTML = `<p class="empty-state">${AppState.getAppData()?.translations?.partner_not_found || 'Партнер не знайдено'}</p>`;
        }
        return;
    }

    const nameEl = document.getElementById('partner-detail-name');
    if (nameEl) {
        nameEl.textContent = partner.name || 'Unknown';
    }

    const content = document.getElementById('partner-detail-content');
    if (content) {
        const appData = AppState.getAppData();
        const isTop = (appData.top_partners || []).some(p => p.id === partner.id);

        // Clear content
        content.innerHTML = '';

        // Create card using DOM API
        const card = document.createElement('div');
        card.className = 'partner-detail-card';

        // Create header
        const header = document.createElement('div');
        header.className = 'partner-detail-header';

        const h2 = document.createElement('h2');
        h2.textContent = partner.name || 'Unknown';

        const badge = document.createElement('span');
        badge.className = `commission-badge large ${isTop ? 'top-badge' : ''}`;
        badge.textContent = `${partner.commission || 0}% ${AppState.getAppData()?.translations?.commission || 'комісія'}`;

        header.appendChild(h2);
        header.appendChild(badge);

        // Create body
        const body = document.createElement('div');
        body.className = 'partner-detail-body';

        const description = document.createElement('p');
        description.className = 'partner-detail-description';
        description.textContent = partner.description || AppState.getAppData()?.translations?.no_description || 'Опис відсутній';

        const actions = document.createElement('div');
        actions.className = 'partner-detail-actions';

        const button = document.createElement('button');
        button.className = 'partner-btn large';
        button.textContent = AppState.getAppData()?.translations?.go_to_partner || 'Перейти до партнера';
        button.setAttribute('aria-label', `${AppState.getAppData()?.translations?.go_to_partner || 'Перейти до партнера'} ${partner.name || 'Unknown'}`);
        button.addEventListener('click', () => {
            if (typeof Haptic !== 'undefined') Haptic.medium();
            if (typeof Actions !== 'undefined' && Actions.openPartner) {
                Actions.openPartner(partner.referral_link || '', String(partnerId));
            } else {
                openPartner(partner.referral_link || '', String(partnerId));
            }
        });

        actions.appendChild(button);
        body.appendChild(description);
        body.appendChild(actions);

        card.appendChild(header);
        card.appendChild(body);
        content.appendChild(card);
    }
}

function renderTop() {
    console.log('[Render] renderTop: starting');

    // Ensure we're on the top page
    const topPage = document.getElementById('top-page');
    const partnersPage = document.getElementById('partners-page');
    const homePage = document.getElementById('home-page');

    console.log('[Render] renderTop: top-page active?', topPage?.classList.contains('active'));
    console.log('[Render] renderTop: partners-page active?', partnersPage?.classList.contains('active'));
    console.log('[Render] renderTop: home-page active?', homePage?.classList.contains('active'));

    if (!topPage) {
        console.error('[Render] renderTop: top-page element not found');
        return;
    }

    if (!topPage.classList.contains('active')) {
        console.warn('[Render] renderTop: top page is not active, skipping render');
        return;
    }

    const container = document.getElementById('top-content');
    if (!container) {
        console.warn('[Render] TOP container not found');
        return;
    }

    // Track view_top event
    trackEvent('view_top');

    // Hide skeleton
    const appData = AppState.getAppData();
    if (typeof Render !== 'undefined' && Render.hideSkeleton) {
        Render.hideSkeleton('top');
    } else {
        hideSkeleton('top');
    }

    if (!appData) {
        console.warn('[Render] appData not loaded yet, showing loading state');
        container.innerHTML = `<div class="loading-state"><p>${AppState.getAppData()?.translations?.loading_data || 'Завантаження даних...'}</p></div>`;
        return;
    }

    // Clear container
    container.innerHTML = '';

    const topStatus = appData.user?.top_status || 'locked';
    const topPartners = appData.top_partners || [];
    const referralCount = AppState.getReferralCount();
    const requiredInvites = appData.earnings?.required_invites || 5; // Total needed (like in bot)
    const invitesNeeded = appData.earnings?.invites_needed || 0; // How many more needed
    const buyTopPrice = appData.earnings?.buy_top_price || 1;

    // Determine state: LOCKED, ALMOST (X >= 3), or UNLOCKED
    let state = 'LOCKED';
    if (topStatus === 'open' || topStatus === 'unlocked') {
        state = 'UNLOCKED';
    } else if (referralCount >= 3 && referralCount < requiredInvites) {
        state = 'ALMOST';
    }

    if (state === 'LOCKED') {
        renderTopLocked(container, referralCount, requiredInvites, invitesNeeded, buyTopPrice, topPartners);
    } else if (state === 'ALMOST') {
        renderTopAlmost(container, referralCount, requiredInvites, invitesNeeded, buyTopPrice, topPartners);
    } else {
        renderTopUnlocked(container, topPartners);
    }
}

/**
 * Render TOP LOCKED state (FOMO + Paywall)
 */
function renderTopLocked(container, referralCount, requiredInvites, invitesNeeded, buyTopPrice, topPartners) {
    container.className = 'top-locked';

    // Use requiredInvites for progress calculation (like in bot: total_invited / required_invites)
    const progress = Math.min(referralCount, requiredInvites);
    const progressPercent = requiredInvites > 0 ? (progress / requiredInvites) * 100 : 0;

    const lockedDiv = document.createElement('div');
    lockedDiv.className = 'top-locked-content';

    lockedDiv.innerHTML = `
        <div class="top-locked-header">
            <h2>⭐ ${AppState.getAppData()?.translations?.top_header || 'TOP = більше видимості твоєї лінки'}</h2>
            <p class="top-locked-copy">${AppState.getAppData()?.translations?.top_copy || 'TOP відкривають ті, хто запускає дохід'}</p>
        </div>
        
        <div class="top-locked-partners">
            ${topPartners.slice(0, 3).map((partner, index) => `
                <div class="top-partner-blur" style="animation-delay: ${index * 0.1}s">
                    <div class="blur-overlay"></div>
                    <div class="blur-content">
                        <h3>${escapeHtml(partner.name || 'Partner')}</h3>
                        <p>${escapeHtml((partner.description || '').substring(0, 50))}...</p>
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div class="top-locked-progress">
            <div class="progress-info">
                <span>👥 ${referralCount} / ${requiredInvites} ${AppState.getAppData()?.translations?.friends || 'друзів'}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progressPercent}%"></div>
            </div>
        </div>
        
        <div class="top-locked-cta">
            <button class="primary-action-btn" id="invite-for-top-btn">
                ▶️ ${AppState.getAppData()?.translations?.invite_friend || 'Запросити друга'}
            </button>
            <button class="secondary-action-btn" id="buy-top-btn">
                💎 ${AppState.getAppData()?.translations?.open_for || 'Відкрити за'} ${buyTopPrice}⭐
            </button>
        </div>
        
        <div class="top-fomo">
            <p>${AppState.getAppData()?.translations?.top_fomo || '23 людини відкрили TOP сьогодні'}</p>
        </div>
    `;

    container.appendChild(lockedDiv);

    // Add click handlers
    const inviteBtn = container.querySelector('#invite-for-top-btn');
    if (inviteBtn) {
        inviteBtn.addEventListener('click', () => {
            trackEvent('invite_sent', { source: 'top' });
            if (typeof Actions !== 'undefined' && Actions.shareReferralLink) {
                Actions.shareReferralLink();
            }
        });
    }

    const buyBtn = container.querySelector('#buy-top-btn');
    if (buyBtn) {
        buyBtn.addEventListener('click', () => {
            trackEvent('top_purchase', { source: 'top_page' });
            if (typeof Actions !== 'undefined' && Actions.handleBuyTop) {
                Actions.handleBuyTop(buyTopPrice);
            }
        });
    }
}

/**
 * Render TOP ALMOST state (X >= 3)
 */
function renderTopAlmost(container, referralCount, requiredInvites, invitesNeeded, buyTopPrice, topPartners) {
    container.className = 'top-almost';

    // Use requiredInvites for progress calculation (like in bot: total_invited / required_invites)
    const progress = Math.min(referralCount, requiredInvites);
    const progressPercent = requiredInvites > 0 ? (progress / requiredInvites) * 100 : 0;

    const almostDiv = document.createElement('div');
    almostDiv.className = 'top-almost-content';

    // Show 1 partner as preview
    const previewPartner = topPartners[0];

    almostDiv.innerHTML = `
        <div class="top-almost-header">
            <h2>${AppState.getAppData()?.translations?.almost_there || 'Ти майже всередині'}</h2>
            <p class="top-almost-copy">${AppState.getAppData()?.translations?.invites_needed_text || 'Ще'} ${invitesNeeded - referralCount} ${AppState.getAppData()?.translations?.invites_to_top || 'запрошень до TOP'}</p>
        </div>
        
        <div class="top-almost-preview">
            <div class="preview-partner-card">
                <h3>${escapeHtml(previewPartner?.name || 'Partner')}</h3>
                <p>${escapeHtml((previewPartner?.description || '').substring(0, 80))}...</p>
                <span class="preview-badge">⭐ TOP</span>
            </div>
        </div>
        
        <div class="top-almost-progress">
            <div class="progress-info">
                <span>👥 ${referralCount} / ${requiredInvites} ${AppState.getAppData()?.translations?.friends || 'друзів'}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progressPercent}%"></div>
            </div>
        </div>
        
        <div class="top-almost-cta">
            <button class="primary-action-btn" id="invite-almost-btn">
                ▶️ ${AppState.getAppData()?.translations?.invite || 'Запросити'}
            </button>
            <button class="secondary-action-btn" id="buy-almost-btn">
                💎 ${AppState.getAppData()?.translations?.open_for || 'Відкрити за'} ${buyTopPrice}⭐
            </button>
        </div>
    `;

    container.appendChild(almostDiv);

    // Add click handlers
    const inviteBtn = container.querySelector('#invite-almost-btn');
    if (inviteBtn) {
        inviteBtn.addEventListener('click', () => {
            trackEvent('invite_sent', { source: 'top_almost' });
            if (typeof Actions !== 'undefined' && Actions.shareReferralLink) {
                Actions.shareReferralLink();
            }
        });
    }

    const buyBtn = container.querySelector('#buy-almost-btn');
    if (buyBtn) {
        buyBtn.addEventListener('click', () => {
            trackEvent('top_purchase', { source: 'top_almost' });
            if (typeof Actions !== 'undefined' && Actions.handleBuyTop) {
                Actions.handleBuyTop(buyTopPrice);
            }
        });
    }
}

/**
 * Render TOP UNLOCKED state
 */
function renderTopUnlocked(container, topPartners) {
    container.className = 'top-unlocked';

    const unlockedDiv = document.createElement('div');
    unlockedDiv.className = 'top-unlocked-content';

    unlockedDiv.innerHTML = `
        <div class="top-unlocked-header">
            <h2>⭐ ${AppState.getAppData()?.translations?.top_partners_title || 'TOP партнери'}</h2>
            <p class="top-unlocked-copy">${AppState.getAppData()?.translations?.top_unlocked_copy || 'Тут максимальна конверсія'}</p>
        </div>
    `;

    // Render TOP partners grid
    if (topPartners.length === 0) {
        const emptyState = document.createElement('p');
        emptyState.className = 'empty-state';
        emptyState.textContent = AppState.getAppData()?.translations?.no_top_partners || 'TOP партнерів поки немає';
        unlockedDiv.appendChild(emptyState);
    } else {
        const gridContainer = document.createElement('div');
        gridContainer.className = 'partners-grid';

        topPartners.forEach((partner, index) => {
            const card = document.createElement('div');
            card.className = 'partner-card top-partner';
            card.setAttribute('data-partner-id', String(partner.id));

            const iconUrl = partner.icon || partner.image || '';
            const iconHtml = iconUrl ? `<img class="partner-icon" src="${escapeHtml(iconUrl)}" alt="${escapeHtml(partner.name || 'Partner')}" onerror="this.style.display='none'">` : '';

            card.innerHTML = `
                <div class="partner-header">
                    ${iconHtml}
                    <h3 class="partner-name">${escapeHtml(partner.name || 'Unknown')}</h3>
                    <span class="commission-badge top-badge">${partner.commission || 0}%</span>
                </div>
                <div class="partner-labels">
                    <span class="partner-label">⭐ ${AppState.getAppData()?.translations?.label_top || 'TOP'}</span>
                    <span class="partner-label">🔥 ${AppState.getAppData()?.translations?.label_hot || 'часто купують'}</span>
                </div>
                <p class="partner-description">${escapeHtml((partner.description || '').substring(0, 100))}${partner.description && partner.description.length > 100 ? '...' : ''}</p>
                <button class="partner-btn highlight-cta">▶️ ${AppState.getAppData()?.translations?.go_to || 'Перейти'}</button>
            `;

            // Add click handlers
            const btn = card.querySelector('.partner-btn');
            if (btn) {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (typeof Haptic !== 'undefined') Haptic.medium();
                    trackEvent('partner_click', { partner_id: String(partner.id), source: 'top' });
                    if (typeof Actions !== 'undefined' && Actions.openPartner) {
                        Actions.openPartner(partner.referral_link || '', String(partner.id));
                    }
                });
            }

            card.addEventListener('click', () => {
                if (typeof Haptic !== 'undefined') Haptic.light();
                trackEvent('partner_open', { partner_id: String(partner.id), source: 'top' });
                if (typeof Navigation !== 'undefined' && Navigation.showPartnerDetail) {
                    Navigation.showPartnerDetail(String(partner.id));
                }
            });

            gridContainer.appendChild(card);
        });

        unlockedDiv.appendChild(gridContainer);
    }

    container.appendChild(unlockedDiv);
}

function renderEarnings() {
    const container = document.getElementById('earnings-dashboard');
    if (!container) {
        console.warn('Earnings container not found');
        return;
    }

    // Hide skeleton
    const appData = AppState.getAppData();
    if (typeof Render !== 'undefined' && Render.hideSkeleton) {
        Render.hideSkeleton('earnings');
    } else {
        hideSkeleton('earnings');
    }

    if (!appData) {
        console.warn('AppState.getAppData() not loaded yet, showing loading state');
        container.innerHTML = `<div class="loading-state"><p>${AppState.getAppData()?.translations?.loading_data || 'Завантаження даних...'}</p></div>`;
        return;
    }

    const earnings = appData.earnings || {};
    const user = appData.user || {};
    const translations = earnings.translations || {};
    const commissionPercent = Math.round((earnings.commission_rate || 0.07) * 100);

    const totalInvited = user.total_invited || 0;
    const requiredInvites = earnings.required_invites || 5;
    const progress = requiredInvites > 0 ? Math.min((totalInvited / requiredInvites) * 100, 100) : 0;

    container.innerHTML = `
        <div class="earnings-container">
            <!-- Header -->
            <div class="earnings-header">
                <h2>${AppState.getAppData()?.translations?.earnings_title || 'Заробітки'}</h2>
            </div>
            
            <!-- Balance Card -->
            <div class="earnings-section-card">
                <div class="section-header">
                    <h3 class="section-title">${AppState.getAppData()?.translations?.your_balance || 'Твій баланс'}</h3>
                </div>
                <div class="balance-display">
                    <span class="balance-amount">${earnings.earned || 0} TON</span>
                    <span class="balance-label">${AppState.getAppData()?.translations?.earned || 'Зароблено'}</span>
                </div>
            </div>
            
            <!-- Progress Card -->
            <div class="earnings-section-card">
                <div class="section-header">
                    <h3 class="section-title">Прогрес до TOP</h3>
                </div>
                <div class="progress-section">
                    <p class="progress-label">Інвайтів: <strong>${totalInvited} / ${requiredInvites}</strong></p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    ${earnings.can_unlock_top ?
            '<p class="progress-hint success">✅ Можна розблокувати TOP!</p>' :
            `<p class="progress-hint">Потрібно ще <strong>${earnings.invites_needed || 0}</strong> інвайтів</p>`
        }
                </div>
            </div>
            
            <!-- Referral Link Card -->
            <div class="earnings-section-card">
                <div class="section-header">
                    <h3 class="section-title">${AppState.getAppData()?.translations?.referral_link_title || 'Реферальна лінка'}</h3>
                </div>
                ${user.referral_link ? `
                <div class="referral-section">
                    <div class="referral-link-box">
                        <code>${user.referral_link}</code>
                    </div>
                    <div class="referral-actions">
                        <button class="copy-btn" data-action="copy-referral">📋 ${AppState.getAppData()?.translations?.copy || 'Копіювати'}</button>
                        <button class="share-btn" data-action="share-referral">📤 ${AppState.getAppData()?.translations?.share || 'Поділитися'}</button>
                    </div>
                </div>
                ` : `
                <p class="empty-state">${AppState.getAppData()?.translations?.generating_link || 'Реферальна лінка генерується...'}</p>
                `}
            </div>
            
            <!-- 7% Program Card -->
            <div class="earnings-section-card">
                <div class="section-header">
                    <h3 class="section-title">${commissionPercent}% ${AppState.getAppData()?.translations?.from_telegram || 'від Telegram'}</h3>
                </div>
                <details class="accordion">
                    <summary class="accordion-summary">${AppState.getAppData()?.translations?.details_and_instructions || 'Деталі та інструкції'}</summary>
                    <div class="accordion-body">
                        <div class="commission-info">
                            <p class="info-text">${AppState.getAppData()?.translations?.commission_info_text || `Офіційна партнерська програма Telegram. Коли люди переходять по твоїй лінці, запускають бота та купують зірки — Telegram ділиться з тобою доходом (~${commissionPercent}%).`}</p>
                            <div class="commission-example-box">
                                <p class="example-label">${AppState.getAppData()?.translations?.example_label || 'Скільки може приносити один юзер:'}</p>
                                <ul class="example-list">
                                    <li>1 ${AppState.getAppData()?.translations?.user || 'юзер'} → ~0.35-0.70€</li>
                                    <li>10 ${AppState.getAppData()?.translations?.users || 'юзерів'} → ~3.5-7€</li>
                                    <li>100 ${AppState.getAppData()?.translations?.users || 'юзерів'} → ~35-70€</li>
                                </ul>
                            </div>
                        </div>
                        <div class="commission-activate">
                            <h4 class="activate-title">${AppState.getAppData()?.translations?.how_to_activate || `Як активувати ${commissionPercent}% (1 раз назавжди):`}</h4>
                            <div class="activate-steps">
                                <div class="activate-step">${AppState.getAppData()?.translations?.step_open_bot || 'Відкрий'} @${typeof getBotUsername === 'function' ? (getBotUsername() || 'bot') : 'bot'}</div>
                                <div class="activate-step">«${AppState.getAppData()?.translations?.partner_program || 'Партнерська програма'}»</div>
                                <div class="activate-step">«${AppState.getAppData()?.translations?.connect || 'Під\'єднатись'}» → ${commissionPercent}% ${AppState.getAppData()?.translations?.activated_forever || 'активуються назавжди'}</div>
                            </div>
                        </div>
                    </div>
                </details>
            </div>
            
            <!-- What to do next Card -->
            <div class="earnings-section-card">
                <div class="section-header">
                    <h3 class="section-title">${AppState.getAppData()?.translations?.what_to_do_now || 'Що зробити прямо зараз'}</h3>
                </div>
                <details class="accordion">
                    <summary class="accordion-summary">${AppState.getAppData()?.translations?.action_plan || 'План дій'}</summary>
                    <div class="accordion-body">
                        <div class="action-steps-simple">
                            <div class="action-step-item">
                                <span class="action-step-text">${AppState.getAppData()?.translations?.step_add_friends || 'Додай ще'} ${earnings.invites_needed || 0} ${AppState.getAppData()?.translations?.friends_plural || 'друзів'} → ${AppState.getAppData()?.translations?.top_will_open || 'TOP відкриється'}</span>
                            </div>
                            <div class="action-step-item">
                                <span class="action-step-text">${AppState.getAppData()?.translations?.step_activate_percent || 'Активуй свої'} ${commissionPercent}%</span>
                            </div>
                            <div class="action-step-item">
                                <span class="action-step-text">${AppState.getAppData()?.translations?.step_share_link || 'Кинь цю лінку в 1-2 "живі" чати або друзів — кожен юзер може приносити тобі €'}</span>
                            </div>
                            <div class="action-step-item">
                                <span class="action-step-text">${AppState.getAppData()?.translations?.step_launch_partners || 'Запускай TOP-партнерів'}</span>
                            </div>
                        </div>
                        <p class="auto-stats">${AppState.getAppData()?.translations?.auto_stats || 'Статистика оновлюється автоматично'}</p>
                    </div>
                </details>
            </div>
            
            <!-- Action Buttons -->
            <div class="earnings-actions">
                ${earnings.can_unlock_top ? `
                    <button class="action-btn unlock-btn" data-action="switch-top" aria-label="${AppState.getAppData()?.translations?.btn_top_partners || 'Відкрити TOP партнерів'}">
                        ${translations.btn_top_partners || AppState.getAppData()?.translations?.open_top || 'Відкрити TOP'}
                    </button>
                ` : `
                    <button class="action-btn unlock-btn" data-action="buy-top" data-price="${earnings.buy_top_price || 1}" aria-label="${AppState.getAppData()?.translations?.btn_unlock_top || `Розблокувати TOP за ${earnings.buy_top_price || 1} зірок`}">
                        ${translations.btn_unlock_top || `${AppState.getAppData()?.translations?.unlock_top || 'Розблокувати TOP'} (${earnings.buy_top_price || 1} ⭐)`}
                    </button>
                `}
                <button class="action-btn activate-btn" data-action="activate-7" aria-label="${AppState.getAppData()?.translations?.btn_activate_7 || 'Активувати програму 7% комісії'}">
                    ${translations.btn_activate_7 || AppState.getAppData()?.translations?.activate_7_percent || 'Активувати 7%'}
                </button>
            </div>
        </div>
    `;
}

function renderWallet() {
    const container = document.getElementById('wallet-section');
    const appData = AppState.getAppData();
    if (!container || !appData) return;

    // Hide skeleton
    if (typeof Render !== 'undefined' && Render.hideSkeleton) {
        Render.hideSkeleton('wallet');
    } else {
        hideSkeleton('wallet');
    }

    const wallet = appData.user?.wallet || '';
    const walletHelp = appData.wallet?.help || '';
    // Check if wallet is valid (not empty, not just underscores/placeholders)
    // "EQD____ _0vo" looks like a placeholder, not a real wallet
    // Valid TON wallet should be at least 48 chars and not contain multiple underscores in a row
    const walletTrimmed = wallet ? wallet.trim() : '';
    const hasWallet = walletTrimmed &&
        walletTrimmed.length >= 48 &&
        !walletTrimmed.match(/_{3,}/) && // Not multiple underscores in a row
        walletTrimmed.match(/^EQ[A-Za-z0-9_-]+$/); // Valid TON wallet format

    container.innerHTML = `
        <div class="wallet-card">
            <h2>${AppState.getAppData()?.translations?.wallet_title || 'TON Гаманець'}</h2>
            ${hasWallet ? `
                <div class="current-wallet">
                    <p>${AppState.getAppData()?.translations?.current_wallet || 'Поточний гаманець'}:</p>
                    <code class="wallet-address">${wallet}</code>
                </div>
            ` : walletHelp ? `
                <div class="wallet-help">
                    <p>${escapeHtml(walletHelp).replace(/\n/g, '<br>')}</p>
                </div>
            ` : `
                <div class="wallet-help">
                    <p>⚠️ ${AppState.getAppData()?.translations?.no_wallet_warning || 'У вас ще немає збереженого TON гаманця.'}</p>
                    <p>${AppState.getAppData()?.translations?.wallet_how_to || 'Відкрийте будь-який TON гаманець, скопіюйте адресу та введіть її нижче.'}</p>
                </div>
            `}
            <form id="wallet-form">
                <label for="wallet-input">${AppState.getAppData()?.translations?.enter_wallet_label || 'Введіть TON гаманець'}:</label>
                <input 
                    type="text" 
                    id="wallet-input" 
                    class="wallet-input" 
                    placeholder="EQ..."
                    value="${wallet}"
                    pattern="^(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_-]{46,48}$"
                    required
                />
                <button type="submit" class="save-btn">${AppState.getAppData()?.translations?.save || 'Зберегти'}</button>
            </form>
            <div id="wallet-message" class="wallet-message"></div>
        </div>
    `;
}

function renderInfo() {
    const container = document.getElementById('info-section');
    const appData = AppState.getAppData();
    if (!container || !appData) return;

    // Hide skeleton
    if (typeof Render !== 'undefined' && Render.hideSkeleton) {
        Render.hideSkeleton('info');
    } else {
        hideSkeleton('info');
    }

    const infoMessage = appData.info?.message || '';

    // Fix cases where backend sends literal "\n" sequences instead of newlines
    // Escape HTML first to prevent XSS, then convert newlines to <br>
    const safeMessage = escapeHtml(String(infoMessage || ''))
        .replace(/\\n/g, '\n')
        .replace(/\n/g, '<br>');

    // Use escaped content for safety
    container.innerHTML = `
        <div class="info-card">
            <div class="info-content">
                ${safeMessage || `<p>${AppState.getAppData()?.translations?.bot_info || 'Інформація про бота'}</p>`}
            </div>
        </div>
    `;
}

function showLoading(show) {
    const loading = document.getElementById('loading');
    const app = document.getElementById('app');

    if (loading) loading.style.display = show ? 'flex' : 'none';
    if (app) app.style.display = show ? 'none' : 'block';
}

function showError(message, errorType = 'general') {
    const errorEl = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    const app = document.getElementById('app');

    // Track error
    trackEvent('error_shown', { type: errorType, message: message });

    // Show app container so user can still see navigation and retry
    if (app) {
        app.style.display = 'block';
    }

    if (errorEl && errorText) {
        // Enhanced error messages based on type
        let displayMessage = message;

        if (errorType === 'network') {
            displayMessage = AppState.getAppData()?.translations?.error_network || 'Проблеми з інтернет-з\'єднанням. Перевірте підключення та спробуйте ще раз.';
        } else if (errorType === 'api') {
            displayMessage = AppState.getAppData()?.translations?.error_api || 'Помилка завантаження даних. Спробуйте пізніше.';
        } else if (errorType === 'validation') {
            displayMessage = AppState.getAppData()?.translations?.error_validation || 'Невірні дані. Перевірте введену інформацію.';
        }

        errorText.textContent = displayMessage;
        errorEl.style.display = 'block';

        // Add error type class for styling
        errorEl.className = `error-message error-${errorType}`;
    }

    // Retry button
    const retryBtn = document.getElementById('retry-btn');
    if (retryBtn) {
        retryBtn.textContent = AppState.getAppData()?.translations?.retry || 'Спробувати ще раз';
        retryBtn.onclick = () => {
            if (errorEl) errorEl.style.display = 'none';
            trackEvent('error_retry', { type: errorType });
            if (typeof loadAppData === 'function') {
                loadAppData(true); // Force refresh
            }
        };
    }

    // Haptic feedback
    if (typeof Haptic !== 'undefined') {
        Haptic.error();
    }
}

function showSkeleton(pageName) {
    const skeletonId = `${pageName}-skeleton`;
    const skeleton = document.getElementById(skeletonId);
    const contentId = pageName === 'home' ? 'home-page' :
        pageName === 'partners' ? 'partners-list' :
            pageName === 'top' ? 'top-content' : null;
    const content = contentId ? document.getElementById(contentId) : null;

    if (skeleton) {
        skeleton.style.display = 'grid';
    }
    if (content) {
        content.style.display = 'none';
    }
}

function hideSkeleton(pageName) {
    const skeletonId = `${pageName}-skeleton`;
    const skeleton = document.getElementById(skeletonId);
    const contentId = pageName === 'home' ? 'home-page' :
        pageName === 'partners' ? 'partners-list' :
            pageName === 'top' ? 'top-content' : null;
    const content = contentId ? document.getElementById(contentId) : null;

    if (skeleton) {
        skeleton.style.display = 'none';
    }
    if (content) {
        content.style.display = 'block';
    }
}

function showOnboarding() {
    const onboardingScreen = document.getElementById('onboarding-screen');
    if (!onboardingScreen) return;

    // Check if user already saw onboarding
    const hasSeenOnboarding = AppState.getHasSeenOnboarding();
    if (hasSeenOnboarding) {
        onboardingScreen.style.display = 'none';
        return;
    }

    // Show onboarding
    onboardingScreen.style.display = 'flex';

    // Show screen 1
    const screen1 = document.getElementById('onboarding-screen-1');
    const screen2 = document.getElementById('onboarding-screen-2');
    const nextBtn = document.getElementById('onboarding-next-btn');
    const startBtn = document.getElementById('onboarding-start-btn');

    if (screen1) screen1.classList.add('active');
    if (screen2) screen2.classList.remove('active');

    // Handle next button (screen 1 -> screen 2)
    if (nextBtn) {
        nextBtn.onclick = () => {
            if (screen1) screen1.classList.remove('active');
            if (screen2) screen2.classList.add('active');
            if (typeof Haptic !== 'undefined') Haptic.light();
        };
    }

    // Handle start button (screen 2 -> close onboarding)
    if (startBtn) {
        startBtn.onclick = () => {
            // Mark onboarding as seen
            AppState.setHasSeenOnboarding(true);
            const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
            storage.setItem('has_seen_onboarding', 'true');

            // Track onboarding completion
            trackEvent('onboarding_completed');

            // Hide onboarding
            onboardingScreen.style.display = 'none';

            // Handle start_param (referral parameter)
            const tg = AppState.getTg();
            if (tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) {
                // Referral parameter is already handled by backend
                trackEvent('referral_clicked', { start_param: tg.initDataUnsafe.start_param });
            }

            // Show app
            const app = document.getElementById('app');
            if (app) app.style.display = 'block';

            // Load and render app data
            if (typeof loadAppData === 'function') {
                loadAppData(false).then(() => {
                    if (typeof Navigation !== 'undefined' && Navigation.switchTab) {
                        Navigation.switchTab('home');
                    }
                });
            }

            if (typeof Haptic !== 'undefined') Haptic.success();
        };
    }
}

// Legacy function for backward compatibility
function showWelcomeScreen() {
    showOnboarding();
}

/**
 * Show Share Auto-popup
 * Triggers: after start_7_flow, top_unlocked, 24h idle, 3 partner_click
 */
function showSharePopup(trigger = 'manual') {
    const popup = document.getElementById('share-popup');
    if (!popup) return;

    // Track popup shown
    trackEvent('share_popup_shown', { trigger: trigger });

    // Show popup
    popup.style.display = 'flex';

    // Haptic feedback
    if (typeof Haptic !== 'undefined') {
        Haptic.light();
    }

    // Setup buttons
    const shareBtn = document.getElementById('share-popup-share-btn');
    const closeBtn = document.getElementById('share-popup-close-btn');

    if (shareBtn) {
        shareBtn.onclick = () => {
            trackEvent('share_sent', { source: 'popup', trigger: trigger });
            if (typeof Actions !== 'undefined' && Actions.shareReferralLink) {
                Actions.shareReferralLink();
            }
            popup.style.display = 'none';
            if (typeof Haptic !== 'undefined') Haptic.success();
        };
    }

    if (closeBtn) {
        closeBtn.onclick = () => {
            popup.style.display = 'none';
            if (typeof Haptic !== 'undefined') Haptic.light();
        };
    }

    // Close on overlay click
    popup.onclick = (e) => {
        if (e.target === popup) {
            popup.style.display = 'none';
        }
    };
}

/**
 * Check and trigger Share Auto-popup based on conditions
 * With rate limiting (max 1 popup per 6 hours)
 */
function checkSharePopupTriggers() {
    const appData = AppState.getAppData();
    if (!appData) return;

    // Rate limiting: check last popup time
    const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
    const lastPopupTime = storage.getItem('last_share_popup_time');
    if (lastPopupTime) {
        const lastTime = parseInt(lastPopupTime);
        const now = Date.now();
        const hoursSinceLastPopup = (now - lastTime) / (1000 * 60 * 60);
        // Max 1 popup per 6 hours
        if (hoursSinceLastPopup < 6) {
            return;
        }
    }

    // Check trigger conditions
    const didStart7Flow = AppState.getDidStart7Flow();
    const topLocked = AppState.getTopLocked();
    const lastSharePopup = storage.getItem('last_share_popup');
    const lastActivity = storage.getItem('last_activity');
    const partnerClickCount = parseInt(storage.getItem('partner_click_count') || '0');

    // Trigger 1: After start_7_flow
    // DISABLED: Don't show share popup immediately after clicking "Start 7% flow"
    // User should see instructions first, then decide when to share
    // Share popup will be shown later (after user closes instruction modal or other triggers)
    // if (didStart7Flow && lastSharePopup !== 'start_7_flow') {
    //     showSharePopup('start_7_flow');
    //     storage.setItem('last_share_popup', 'start_7_flow');
    //     storage.setItem('last_share_popup_time', String(Date.now()));
    //     return;
    // }

    // Trigger 2: After top_unlocked
    if (!topLocked && lastSharePopup !== 'top_unlocked') {
        showSharePopup('top_unlocked');
        storage.setItem('last_share_popup', 'top_unlocked');
        storage.setItem('last_share_popup_time', String(Date.now()));
        return;
    }

    // Trigger 3: After 24h idle
    if (lastActivity) {
        const lastActivityTime = parseInt(lastActivity);
        const now = Date.now();
        const hoursSinceActivity = (now - lastActivityTime) / (1000 * 60 * 60);
        if (hoursSinceActivity >= 24 && lastSharePopup !== '24h_idle') {
            showSharePopup('24h_idle');
            storage.setItem('last_share_popup', '24h_idle');
            storage.setItem('last_share_popup_time', String(Date.now()));
            return;
        }
    }

    // Trigger 4: After 3 partner_click
    if (partnerClickCount >= 3 && lastSharePopup !== '3_partner_click') {
        showSharePopup('3_partner_click');
        storage.setItem('last_share_popup', '3_partner_click');
        localStorage.setItem('last_share_popup_time', String(Date.now()));
        return;
    }
}

// Track partner clicks for auto-popup trigger
function trackPartnerClickForPopup() {
    const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
    const count = parseInt(storage.getItem('partner_click_count') || '0');
    storage.setItem('partner_click_count', String(count + 1));
    storage.setItem('last_activity', String(Date.now()));

    // Check if should show popup
    if (count + 1 >= 3) {
        checkSharePopupTriggers();
    }
}

// Track activity for 24h idle trigger
function trackActivity() {
    const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
    storage.setItem('last_activity', String(Date.now()));
}

// Initialize activity tracking
if (typeof window !== 'undefined') {
    window.addEventListener('click', trackActivity);
    window.addEventListener('touchstart', trackActivity);
}

// Check triggers on app load
if (typeof window !== 'undefined') {
    window.addEventListener('load', () => {
        setTimeout(checkSharePopupTriggers, 2000); // Check after 2 seconds
    });
}

function showWalletMessage(message, type = 'info') {
    const messageEl = document.getElementById('wallet-message');
    if (messageEl) {
        messageEl.textContent = message;
        messageEl.className = `wallet-message ${type}`;
        messageEl.style.display = 'block';

        if (type === 'success') {
            setTimeout(() => {
                messageEl.style.display = 'none';
            }, 3000);
        }
    }
}

function escapeHtml(text) {
    // Always use local implementation to avoid recursion
    // Don't check window.escapeHtml as it might point back to this function
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

/**
 * Render HOME page (Action Engine)
 */
/**
 * Render HOME page (Action Engine)
 */
/**
 * Render HOME page (Action Engine)
 */
function renderHome() {
    const appData = AppState.getAppData();
    if (!appData) return;

    // Track view_home event
    trackEvent('view_home');

    // CLEANUP: Hide the secondary Share Strip (blue button)
    const shareStrip = document.getElementById('share-strip');
    if (shareStrip) shareStrip.style.display = 'none';

    // Determine State: Starter vs TOP
    const referralCount = AppState.getReferralCount();
    const isTop = (referralCount >= 5) || (!AppState.getTopLocked());

    // 1. Render Persistent Header (Avatar + Wallet)
    renderPersistentHeaderV2(appData.user, isTop);

    // 2. Render Hero Section (Quest vs Dashboard)
    renderHeroSection(isTop, referralCount);

    // 3. Render Primary Action Card
    renderActionCard(isTop, referralCount);

    // 3.5 Render Partners Teaser (Boost)
    renderPartnersTeaser();

    // 4. Render Money Math Card (Benefits)
    renderMoneyMathCardV2(isTop);

    // 5. Render Info Section (Footer)
    renderInfoSection(true); // true = as footer link
}

/**
 * Render Persistent Header (Avatar + Wallet)
 */
function renderPersistentHeader(user, isTop) {
    // We insert this BEFORE the trust-header (Hero)
    const hero = document.getElementById('trust-header');
    if (!hero) return;

    // Check if header already exists, if not create logic
    let header = document.getElementById('persistent-header-container');
    if (!header) {
        header = document.createElement('div');
        header.id = 'persistent-header-container';
        hero.parentNode.insertBefore(header, hero);
    }

    const userName = user?.first_name || 'User';
    const userAvatarChar = userName.charAt(0).toUpperCase();

    // Badge Logic
    const badgeText = isTop ? '🏆 TOP Partner' : '🌱 Starter';
    const badgeClass = isTop ? 'badge-top' : 'badge-starter';

    // Wallet Logic
    const walletAddress = user?.wallet || AppState.getAppData()?.user?.wallet;
    const shortWallet = walletAddress ? `${walletAddress.slice(0, 4)}...${walletAddress.slice(-4)}` : 'Connect Wallet (Soon)';
    const walletClass = isTop ? '' : 'locked';
    // If wallet is connected, show address. If not, and isTop, show "Connect Wallet". If STARTER, show "Connect Wallet (Soon)" (locked) or just "Wallet"

    // Wallet Click Handler
    window.handleHeaderWalletClick = () => {
        if (!isTop) {
            if (typeof Toast !== 'undefined') Toast.error('🔒 Спочатку розблокуй TOP статус!');
            return;
        }
        // Open wallet modal (existing function)
        const event = new CustomEvent('open-wallet-modal');
        document.dispatchEvent(event);
    };

    header.innerHTML = `
        <div class="persistent-header">
            <div class="user-profile">
                <div class="user-avatar">${userAvatarChar}</div>
                <div class="user-info-text">
                    <span class="user-name">${escapeHtml(userName)}</span>
                    <span class="user-badge ${badgeClass}">${badgeText}</span>
                </div>
            </div>
            <button class="wallet-pill-btn ${walletClass}" onclick="handleHeaderWalletClick()">
                <span>💎</span>
                <span>${shortWallet}</span>
            </button>
        </div>
    `;
}

/**
 * Render Money Math Card (Benefits)
 */
function renderMoneyMathCard(isTop) {
    // Insert AFTER action card
    const actionCard = document.getElementById('primary-action-card');
    if (!actionCard) return;

    let benefits = document.getElementById('benefits-card-container');
    if (!benefits) {
        benefits = document.createElement('div');
        benefits.id = 'benefits-card-container';
        actionCard.parentNode.insertBefore(benefits, actionCard.nextSibling);
    }

    benefits.innerHTML = `
        <div class="benefits-card">
            <!-- Replacing weak list with Money Math -->
            <div class="benefits-title">💰 Money Math (Твій потенціал)</div>
            <div class="benefit-item">
                <span>👤</span>
                <span>1 user → ~0.35–0.70€</span>
            </div>
            <div class="benefit-item">
                <span>👥</span>
                <span>10 users → ~3.5–7.0€</span>
            </div>
            <div class="benefit-item">
                <span>🚀</span>
                <span>100 users → ~35–70€</span>
            </div>
            <div style="margin-top: 12px; font-size: 11px; color: #666; text-align: center; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;">
                Telegram платить 7% від кожної покупки зірок.
            </div>
        </div>
    `;
}

/**
 * Render Hero Section (Quest vs Dashboard)
 */
function renderHeroSection(isTop, referralCount) {
    const container = document.getElementById('trust-header');
    if (!container) return;

    container.style.display = 'block';

    // Add specific class for styling hook
    container.className = isTop ? 'hero-section hero-top' : 'hero-section hero-starter';

    if (isTop) {
        // --- TOP STATE (Dashboard) ---
        const savedLink = AppState.getTgrLink() || AppState.getAppData()?.user?.custom_data?.tgr_link;

        container.innerHTML = `
            <div class="dashboard-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px;">
                <div class="dash-card" style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 16px; text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #fff;">👥 ${referralCount}</div>
                    <div style="font-size: 12px; color: #aaa; margin-top: 4px;">Друзів</div>
                </div>
                <div class="dash-card active" style="background: rgba(0, 122, 255, 0.15); padding: 15px; border-radius: 16px; text-align: center; border: 1px solid rgba(0, 122, 255, 0.3);">
                    <div style="font-size: 24px;">⭐️</div>
                    <div style="font-size: 12px; color: #007aff; margin-top: 4px;">Program Active</div>
                </div>
            </div>
            
            ${renderTgrLinkInput(savedLink)}
        `;
    } else {
        // --- STARTER STATE (Quest) ---
        const needed = 5;
        const current = Math.min(referralCount, 5);
        const progressPercent = (current / needed) * 100;

        container.innerHTML = `
            <div class="quest-card">           
                <div style="font-size: 16px; font-weight: bold; color: #fff; margin-bottom: 5px; text-align: center;">
                    Відкрий TOP — x3–x7 більше зірок
                </div>
                
                <div class="progress-container">
                    <div style="width: ${progressPercent}%; height: 100%; background: #007aff; box-shadow: 0 0 10px #007aff; transition: width 0.5s ease;"></div>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
                    ${Array.from({ length: 5 }).map((_, i) => `
                        <div style="font-size: 16px; opacity: ${i < current ? '1' : '0.3'};">
                            ${i < current ? '✅' : (i === current ? '🎁' : '🔒')}
                        </div>
                    `).join('')}
                </div>
                
                <div style="text-align: center;">
                    <button class="text-link-btn" onclick="Actions.handleBuyTop(1)" style="background: none; border: none; color: #007aff; font-size: 13px; text-decoration: underline; cursor: pointer;">
                        Відкрити TOP за 1⭐
                    </button>
                </div>
            </div>
        `;
    }
}

/**
 * Helper: Smart Input for TGR Link
 */
function renderTgrLinkInput(savedLink) {
    if (savedLink) {
        return `
            <div class="tgr-status" style="background: rgba(40, 167, 69, 0.1); border: 1px solid rgba(40, 167, 69, 0.3); padding: 15px; border-radius: 12px; display: flex; align-items: center; gap: 10px;">
                <div style="font-size: 24px;">✅</div>
                <div>
                    <div style="font-weight: 600; color: #28a745;">Виплати активовано</div>
                    <div style="font-size: 12px; color: #aaa; word-break: break-all;">${savedLink.slice(0, 25)}...</div>
                </div>
            </div>
        `;
    }
    return `
        <div class="smart-input" style="background: rgba(255, 193, 7, 0.1); border: 1px solid rgba(255, 193, 7, 0.3); padding: 15px; border-radius: 12px;">
            <div style="margin-bottom: 10px; font-weight: 600; color: #ffc107;">⚠️ Активуй свої 7% виплат!</div>
            <div style="display: flex; gap: 8px;">
                <input type="text" id="tgr-link-input" placeholder="Встав лінку (t.me/...)" 
                       style="flex: 1; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: #fff; padding: 10px; border-radius: 8px;" />
                <button onclick="Actions.saveTgrLink()" style="background: #ffc107; color: #000; border: none; padding: 0 15px; border-radius: 8px; font-weight: 600;">OK</button>
            </div>
            <div style="margin-top: 8px; font-size: 12px; text-align: right;">
                <a href="#" onclick="Actions.openBotForLink()" style="color: #aaa; text-decoration: underline;">👉 Де взяти лінку?</a>
            </div>
        </div>
    `;
}

/**
 * Render Action Card (Main Button)
 */
function renderActionCard(isTop, referralCount) {
    const container = document.getElementById('primary-action-card');
    if (!container) return;

    const savedLink = AppState.getTgrLink() || AppState.getAppData()?.user?.custom_data?.tgr_link;

    if (isTop) {
        container.innerHTML = `
            <div class="action-card-content" style="text-align: center; margin-top: 20px;">
                <button class="primary-action-btn pulse glow-effect" onclick="${savedLink ? 'Actions.shareReferralLink()' : 'document.getElementById(\'tgr-link-input\').focus()'}" 
                        style="width: 100%; padding: 18px; border-radius: 16px; background: linear-gradient(90deg, #007aff, #00d4ff); font-size: 18px; font-weight: 700; border: none; color: #fff; box-shadow: 0 4px 20px rgba(0,122,255,0.4);">
                    💸 ${savedLink ? 'Активувати 7% та Заробити' : 'Активувати Виплати'}
                </button>
            </div>
         `;
    } else {
        container.innerHTML = `
            <div class="action-card-content" style="text-align: center; margin-top: 20px;">
                <button class="primary-action-btn glow-effect" onclick="Actions.shareReferralLink()"
                        style="width: 100%; padding: 18px; border-radius: 16px; background: linear-gradient(90deg, #28a745, #34d058); font-size: 18px; font-weight: 700; border: none; color: #fff; box-shadow: 0 4px 20px rgba(40,167,69,0.4);">
                    🚀 Запросити (Відкрити TOP)
                </button>
            </div>
         `;
    }
}

/**
 * Render Trust Header (static, only facts)
 */
/**
 * Render Progress Roadmap (Steps to Success)
 * Replaces static Trust Header
 */
function renderProgressRoadmap() {
    const container = document.getElementById('trust-header');
    if (!container) return;

    // Ensure visible
    container.style.display = 'block';

    // Add class for styling logic if needed (or reuse existing)
    container.className = 'trust-header progress-roadmap-container';

    // Get state
    const appData = AppState.getAppData();
    const didStart7Flow = AppState.getDidStart7Flow();
    const wallet = appData?.user?.wallet || '';
    const isWalletConnected = wallet && wallet.trim().length >= 20;
    const topStatus = appData?.user?.top_status || 'locked';
    const isTopUnlocked = topStatus === 'open' || topStatus === 'unlocked';

    // Step 1: Start 7%
    // Considered done if user has started the flow
    const step1Done = didStart7Flow;
    const step1Active = !step1Done;

    // Step 2: Wallet
    // Active if Step 1 done but Wallet not connected
    const step2Done = isWalletConnected;
    const step2Active = step1Done && !step2Done;

    // Step 3: TOP (Scale)
    // Active if Step 2 done but TOP locked
    const step3Done = isTopUnlocked;
    const step3Active = step2Done && !step3Done;

    // Render HTML
    container.innerHTML = `
        <div class="roadmap-title">Твій шлях до прибутку</div>
        <div class="roadmap-steps">
            <!-- Step 1: Start -->
            <div class="roadmap-step ${step1Done ? 'done' : (step1Active ? 'active' : '')}" onclick="if(${step1Active}) { document.getElementById('primary-action-card').scrollIntoView({behavior: 'smooth'}); }">
                <div class="step-icon">${step1Done ? '✅' : '🚀'}</div>
                <div class="step-label">Старт 7%</div>
                ${step1Active ? '<div class="step-indicator">👈 Ти тут</div>' : ''}
            </div>
            
            <!-- Connector 1-2 -->
            <div class="step-connector ${step1Done ? 'done' : ''}"></div>

            <!-- Step 2: Wallet -->
            <div class="roadmap-step ${step2Done ? 'done' : (step2Active ? 'active' : '')}" onclick="if(${step2Active}) { showWalletModal(); }">
                <div class="step-icon">${step2Done ? '✅' : '🏦'}</div>
                <div class="step-label">Гаманець</div>
                ${step2Active ? '<div class="step-indicator">👈 Ти тут</div>' : ''}
            </div>

            <!-- Connector 2-3 -->
            <div class="step-connector ${step2Done ? 'done' : ''}"></div>

            <!-- Step 3: Scale/TOP -->
            <div class="roadmap-step ${step3Done ? 'done' : (step3Active ? 'active' : '')}" onclick="if(${step3Active}) { Navigation.switchTab('top'); }">
                <div class="step-icon">${step3Done ? '✅' : '⭐'}</div>
                <div class="step-label">Масштаб</div>
                ${step3Active ? '<div class="step-indicator">👈 Ти тут</div>' : ''}
            </div>
        </div>
        ${step2Active ? '<div class="roadmap-hint">Підключи гаманець для майбутніх виплат (Coming Soon)</div>' : ''}
    `;

    // Inject styles explicitly if not present (simple inline style for this component)
    if (!document.getElementById('roadmap-styles')) {
        const style = document.createElement('style');
        style.id = 'roadmap-styles';
        style.textContent = `
            .progress-roadmap-container {
                background: linear-gradient(135deg, rgba(36, 129, 204, 0.1) 0%, rgba(36, 129, 204, 0.05) 100%);
                border-radius: 16px;
                padding: 16px;
                margin-bottom: 24px;
                border: 1px solid rgba(36, 129, 204, 0.2);
            }
            .roadmap-title {
                font-size: 14px;
                font-weight: 600;
                color: var(--tg-theme-hint-color, #8a94a7);
                margin-bottom: 12px;
                text-align: center;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .roadmap-steps {
                display: flex;
                align-items: flex-start; /* Align top so labels don't jump */
                justify-content: space-between;
                position: relative;
            }
            .roadmap-step {
                display: flex;
                flex-direction: column;
                align-items: center;
                position: relative;
                z-index: 2;
                width: 33%;
                cursor: pointer;
            }
            .step-icon {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: var(--tg-theme-bg-color, #fff);
                border: 2px solid var(--tg-theme-hint-color, #ccc);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                margin-bottom: 8px;
                transition: all 0.3s ease;
            }
            .roadmap-step.active .step-icon {
                border-color: var(--primary-color, #2481cc);
                box-shadow: 0 0 0 4px rgba(36, 129, 204, 0.2);
                transform: scale(1.1);
            }
            .roadmap-step.done .step-icon {
                background: rgba(46, 204, 113, 0.1);
                border-color: #2ecc71;
                color: #2ecc71;
            }
            .step-label {
                font-size: 12px;
                font-weight: 500;
                color: var(--tg-theme-hint-color, #8a94a7);
                text-align: center;
            }
            .roadmap-step.active .step-label {
                color: var(--tg-theme-text-color, #000);
                font-weight: 700;
            }
            .step-indicator {
                position: absolute;
                top: 50px; /* Below label */
                background: var(--primary-color, #2481cc);
                color: #fff;
                font-size: 10px;
                padding: 2px 8px;
                border-radius: 10px;
                white-space: nowrap;
                animation: bounce 1s infinite;
            }
            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-3px); }
            }
            .step-connector {
                flex-grow: 1;
                height: 2px;
                background: var(--tg-theme-hint-color, #ccc);
                margin-top: 20px; /* Half of icon height */
                position: absolute;
                top: 0;
                z-index: 1;
            }
            /* Connector positioning */
            .roadmap-steps > .step-connector:nth-child(2) { left: 16%; width: 34%; }
            .roadmap-steps > .step-connector:nth-child(4) { left: 50%; width: 34%; }

            .step-connector.done {
                background: #2ecc71;
            }
            .roadmap-hint {
                margin-top: 16px;
                font-size: 12px;
                color: var(--tg-theme-hint-color, #8a94a7);
                text-align: center;
                background: rgba(0,0,0,0.05);
                padding: 8px;
                border-radius: 8px;
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * Render Primary Action Card (1 card only, with priority logic)
 * Priority:
 * 1. if !did_start_7_flow → START 7% FLOW (STATE A)
 * 2. else if top_locked → UNLOCK TOP (STATE B)
 * 3. else → CLICK PARTNERS (STATE C)
 */
function renderPrimaryActionCard() {
    const container = document.getElementById('primary-action-card');
    if (!container) return;

    const didStart7Flow = AppState.getDidStart7Flow();
    const topLocked = AppState.getTopLocked();
    const referralCount = AppState.getReferralCount();

    // Clear container
    container.innerHTML = '';

    // Priority logic
    if (!didStart7Flow) {
        // STATE A: START 7% FLOW
        renderPrimaryActionCardStateA(container);
    } else if (topLocked) {
        // STATE B: UNLOCK TOP
        renderPrimaryActionCardStateB(container, referralCount);
    } else {
        // STATE C: CLICK PARTNERS
        renderPrimaryActionCardStateC(container);
    }
}

/**
 * STATE A: START 7% FLOW
 */
function renderPrimaryActionCardStateA(container) {
    const card = document.createElement('div');
    card.className = 'primary-action-card-content';

    card.innerHTML = `
        <div class="action-card-header">
            <h2>💸 ${AppState.getAppData()?.translations?.connect_7_percent || 'Підʼєднай 7% від Telegram'}</h2>
        </div>
        <div class="action-card-body">
            <p class="action-card-copy">${AppState.getAppData()?.translations?.connect_7_copy || 'Telegram ділиться доходом, якщо твої реферали купують ⭐'}</p>
            <div class="action-card-badges">
                <span class="badge">🟢 Official</span>
                <span class="badge">♾️ One-time setup</span>
                <span class="badge">🛡 Safe</span>
            </div>
        </div>
        <div class="action-card-footer">
            <button class="primary-action-btn" id="start-7-flow-btn" aria-label="${AppState.getAppData()?.translations?.aria_start_7 || 'Почати 7% flow'}">
                ▶️ ${AppState.getAppData()?.translations?.start || 'Почати'}
            </button>
            <p class="action-card-subtext">${AppState.getAppData()?.translations?.start_7_hint || 'Чим раніше запустиш шлях — тим більше шансів отримувати %'}</p>
        </div>
    `;

    container.appendChild(card);

    // Add click handler
    const btn = container.querySelector('#start-7-flow-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            // Track event
            trackEvent('start_7_flow_clicked');

            // Mark as started
            AppState.setDidStart7Flow(true);
            const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
            storage.setItem('did_start_7_flow', 'true');

            // Show instruction modal (1 time) - NO automatic redirect to browser
            // User stays in Mini App and can decide when to open bot if needed
            show7FlowInstructionModal();

            // DO NOT automatically show share popup after clicking "Start 7% flow"
            // User should see instructions first, then decide when to share
            // Share popup will be shown later (after other triggers or user actions)

            // Re-render to show next state (will show STATE B or STATE C)
            renderPrimaryActionCard();
        });
    }
}

/**
 * STATE B: UNLOCK TOP
 */
function renderPrimaryActionCardStateB(container, referralCount) {
    const needed = 5;
    const progress = Math.min(referralCount, needed);
    const progressPercent = (progress / needed) * 100;

    const card = document.createElement('div');
    card.className = 'primary-action-card-content';

    card.innerHTML = `
        <div class="action-card-header">
            <h2>⭐ ${AppState.getAppData()?.translations?.top_visibility_header || 'TOP = більше покупок → більше %'}</h2>
        </div>
        <div class="action-card-body">
            <p class="action-card-copy">${AppState.getAppData()?.translations?.top_visibility_copy || 'TOP бачать найвигідніші Mini Apps і частіше купують ⭐'}</p>
            <div class="top-progress">
                <div class="progress-info">
                    <span>👥 ${referralCount} / ${needed} ${AppState.getAppData()?.translations?.friends || 'друзів'}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progressPercent}%"></div>
                </div>
            </div>
        </div>
        <div class="action-card-footer">
            <button class="primary-action-btn" id="invite-friend-btn" aria-label="${AppState.getAppData()?.translations?.invite_friend || 'Запросити друга'}">
                ▶️ ${AppState.getAppData()?.translations?.invite || 'Запросити'}
            </button>
            <button class="secondary-action-btn" id="buy-top-btn" aria-label="${AppState.getAppData()?.translations?.unlock_top_for || 'Купити TOP за 1 Star'}">
                💎 ${AppState.getAppData()?.translations?.open_for || 'Відкрити за'} 1⭐
            </button>
        </div>
    `;

    container.appendChild(card);

    // Add click handlers
    const inviteBtn = container.querySelector('#invite-friend-btn');
    if (inviteBtn) {
        inviteBtn.addEventListener('click', () => {
            trackEvent('invite_sent');
            // Open share popup
            if (typeof Actions !== 'undefined' && Actions.shareReferralLink) {
                Actions.shareReferralLink();
            }
        });
    }

    const buyBtn = container.querySelector('#buy-top-btn');
    if (buyBtn) {
        buyBtn.addEventListener('click', () => {
            trackEvent('top_purchase');
            // Get price from appData
            const appData = AppState.getAppData();
            const price = appData?.earnings?.buy_top_price || 1;
            // Handle TOP purchase (using Telegram Stars Payment API)
            if (typeof Actions !== 'undefined' && Actions.handleBuyTop) {
                Actions.handleBuyTop(price);
            } else if (typeof handleBuyTop === 'function') {
                handleBuyTop(price);
            }
        });
    }
}

/**
 * STATE C: CLICK PARTNERS
 */
function renderPrimaryActionCardStateC(container) {
    const card = document.createElement('div');
    card.className = 'primary-action-card-content';

    card.innerHTML = `
        <div class="action-card-header">
            <h2>🔥 ${AppState.getAppData()?.translations?.launch_partners_header || 'Запусти партнерів'}</h2>
        </div>
        <div class="action-card-body">
            <p class="action-card-copy">${AppState.getAppData()?.translations?.launch_partners_copy || 'Кожен клік → потенційна покупка → Telegram платить %'}</p>
        </div>
        <div class="action-card-footer">
            <button class="primary-action-btn" id="go-to-partners-btn" aria-label="${AppState.getAppData()?.translations?.go_to_partners || 'Перейти до партнерів'}">
                ▶️ ${AppState.getAppData()?.translations?.go_to_partners || 'Перейти до партнерів'}
            </button>
        </div>
    `;

    container.appendChild(card);

    // Add click handler
    const btn = container.querySelector('#go-to-partners-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            trackEvent('partner_click_from_home');
            // Switch to partners tab
            if (typeof Navigation !== 'undefined' && Navigation.switchTab) {
                Navigation.switchTab('partners');
            }
        });
    }
}

/**
 * Show 7% Flow instruction modal (1 time)
 */
function show7FlowInstructionModal() {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;';

    // Get bot username from config (universal for any bot)
    const botUsername = typeof getBotUsername === 'function' ? getBotUsername() : null;

    if (!botUsername) {
        console.error('❌ Bot username not found. Please sync username via API.');
        return;
    }

    modal.innerHTML = `
        <div class="modal-content" style="background: var(--tg-theme-bg-color); border-radius: var(--radius-lg); padding: var(--spacing-lg); max-width: 90%; max-height: 80vh; overflow-y: auto;">
            <h2 style="margin: 0 0 var(--spacing-md) 0; font-size: var(--font-size-xl);">💸 ${AppState.getAppData()?.translations?.how_to_activate_7_title || 'Як активувати 7%'}</h2>
            <div style="margin-bottom: var(--spacing-lg);">
                <p style="margin: var(--spacing-sm) 0; line-height: 1.6; font-size: var(--font-size-md);">
                    ${AppState.getAppData()?.translations?.telegram_revenue_share_info || 'Telegram ділиться доходом, якщо твої реферали купують ⭐'}
                </p>
                <div style="margin: var(--spacing-md) 0; padding: var(--spacing-md); background: var(--tg-theme-secondary-bg-color, rgba(0,0,0,0.1)); border-radius: var(--radius-md);">
                    <p style="margin: var(--spacing-xs) 0; line-height: 1.6;">1️⃣ ${AppState.getAppData()?.translations?.step_open_bot_text || 'Відкрий'} <strong>@${botUsername}</strong> ${AppState.getAppData()?.translations?.in_telegram || 'в Telegram'}</p>
                    <p style="margin: var(--spacing-xs) 0; line-height: 1.6;">2️⃣ ${AppState.getAppData()?.translations?.step_send_earnings || 'Надішли команду'} <code style="background: var(--tg-theme-bg-color); padding: 2px 6px; border-radius: 4px;">/earnings</code></p>
                    <p style="margin: var(--spacing-xs) 0; line-height: 1.6;">3️⃣ ${AppState.getAppData()?.translations?.step_follow_instructions || 'Слідуй інструкціям для активації'}</p>
                </div>
                <p style="margin: var(--spacing-sm) 0; line-height: 1.6; font-size: var(--font-size-sm); color: var(--tg-theme-hint-color, #999);">
                    ♾️ ${AppState.getAppData()?.translations?.one_time_setup || 'Одноразове налаштування назавжди'}
                </p>
            </div>
            <div style="display: flex; gap: var(--spacing-sm); flex-direction: column;">
                <button class="secondary-action-btn" id="open-bot-btn" style="width: 100%;">
                    📱 ${AppState.getAppData()?.translations?.open_bot_optional || 'Відкрити бота (опціонально)'}
                </button>
                <button class="primary-action-btn" id="close-7-flow-modal" style="width: 100%;">
                    ✅ ${AppState.getAppData()?.translations?.understood || 'Зрозуміло'}
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Close modal handlers
    const closeBtn = modal.querySelector('#close-7-flow-modal');
    const openBotBtn = modal.querySelector('#open-bot-btn');

    const closeModal = () => {
        if (document.body.contains(modal)) {
            document.body.removeChild(modal);
        }
        // Re-render primary action card to show updated state (STATE B or STATE C)
        // Since user has started 7% flow, next state will be shown
        if (typeof renderPrimaryActionCard === 'function') {
            renderPrimaryActionCard();
        }
    };

    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    // Optional: Open bot button (user decides)
    if (openBotBtn) {
        openBotBtn.addEventListener('click', () => {
            // Use activatePartnerAndReturn to notify backend and close app
            if (typeof Actions !== 'undefined' && Actions.activatePartnerAndReturn) {
                Actions.activatePartnerAndReturn();
            } else {
                // Fallback if Actions not available
                const botUrl = typeof getBotUrl === 'function' ? getBotUrl() : null;
                const tg = AppState.getTg();
                if (botUrl && tg?.openTelegramLink) {
                    tg.openTelegramLink(botUrl);
                    if (tg.close) tg.close();
                }
            }

            // Close modal
            closeModal();
        });
    }

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Haptic feedback
    if (typeof Haptic !== 'undefined') {
        Haptic.light();
    }
}

/**
 * Render Share Strip (always visible)
 */
function renderShareStrip() {
    const container = document.getElementById('share-strip');
    if (!container) return;

    // Share Strip is already in HTML, just ensure button works
    const shareBtn = document.getElementById('share-btn');
    if (shareBtn && !shareBtn.hasAttribute('data-listener')) {
        shareBtn.setAttribute('data-listener', 'true');
        shareBtn.addEventListener('click', () => {
            trackEvent('share_opened');
            if (typeof Actions !== 'undefined' && Actions.shareReferralLink) {
                Actions.shareReferralLink();
            }
        });
    }
}

/**
 * Render Wallet Banner (contextual layer, shown if wallet not connected)
 */
function renderWalletBanner() {
    const banner = document.getElementById('wallet-banner');
    if (!banner) return;

    const appData = AppState.getAppData();
    const wallet = appData?.user?.wallet || '';
    const walletTrimmed = wallet ? wallet.trim() : '';

    // Debug logging
    console.log('[Render] renderWalletBanner:', {
        hasAppData: !!appData,
        hasUser: !!appData?.user,
        walletRaw: wallet,
        walletTrimmed: walletTrimmed,
        walletLength: walletTrimmed.length,
        decisionSafe: (!walletTrimmed || walletTrimmed.length < 20) ? 'SHOW_BANNER' : 'HIDE_BANNER'
    });

    // Show banner only if wallet is not connected
    if (!walletTrimmed || walletTrimmed.length < 20) {
        banner.style.display = 'block';

        // Setup button click
        const btn = document.getElementById('wallet-banner-btn');
        if (btn && !btn.hasAttribute('data-listener')) {
            btn.textContent = AppState.getAppData()?.translations?.connect || 'Підключити';
            btn.setAttribute('data-listener', 'true');
            btn.addEventListener('click', () => {
                trackEvent('wallet_banner_clicked');
                showWalletModal();
            });
        }
    } else {
        banner.style.display = 'none';
    }

    // Update banner text if needed
    const bannerText = banner.querySelector('p');
    if (bannerText) {
        bannerText.textContent = AppState.getAppData()?.translations?.wallet_banner_text || 'Підключи гаманець → зможеш виводити';
    }
}

/**
 * Show Wallet Modal (TON Connect Style)
 */
function showWalletModal() {
    const modal = document.getElementById('wallet-modal');
    if (!modal) return;

    trackEvent('wallet_modal_opened');
    modal.style.display = 'flex';

    // Haptic feedback
    if (typeof Haptic !== 'undefined') {
        Haptic.light();
    }

    // Setup close button
    const closeBtn = document.getElementById('wallet-modal-close');
    if (closeBtn) {
        closeBtn.onclick = () => {
            modal.style.display = 'none';
            if (typeof Haptic !== 'undefined') {
                Haptic.light();
            }
        };
    }

    // Setup Telegram Wallet button (primary)
    const telegramBtn = document.getElementById('wallet-connect-telegram');
    if (telegramBtn) {
        telegramBtn.onclick = () => {
            connectTelegramWallet();
        };
    }

    // Setup wallet options
    const walletOptions = modal.querySelectorAll('.wallet-option');
    walletOptions.forEach(option => {
        option.onclick = () => {
            const wallet = option.getAttribute('data-wallet');
            if (wallet === 'view-all') {
                // Show all wallets (fallback to manual input for now)
                showManualWalletInput();
            } else {
                connectExternalWallet(wallet);
            }
        };
    });

    // Setup help button
    const helpBtn = modal.querySelector('.wallet-help-btn');
    if (helpBtn) {
        helpBtn.onclick = () => {
            const tg = AppState.getTg();
            if (tg && tg.showAlert) {
                tg.showAlert(AppState.getAppData()?.translations?.ton_connect_help || 'TON Connect — це офіційний протокол для підключення TON гаманців у Telegram Mini Apps. Він дозволяє безпечно підключати гаманці без передачі приватних ключів.');
            }
        };
    }

    // Close on overlay click
    modal.onclick = (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    };
}

/**
 * Connect Telegram Wallet (native integration via TON Connect)
 */
async function connectTelegramWallet() {
    // Use TON Connect SDK if available
    if (typeof TonConnect !== 'undefined' && TonConnect.connectTelegramWallet) {
        TonConnect.connectTelegramWallet();
    } else {
        // Fallback to manual input
        showManualWalletInput();
    }
}

/**
 * Connect External Wallet (Tonkeeper, MyTonWallet, Tonhub via TON Connect)
 */
function connectExternalWallet(walletName) {
    // Use TON Connect SDK if available
    if (typeof TonConnect !== 'undefined' && TonConnect.connectExternalWallet) {
        TonConnect.connectExternalWallet(walletName);
    } else {
        // Fallback to manual input
        showManualWalletInput();
    }
}

/**
 * Show Manual Wallet Input (fallback)
 */
function showManualWalletInput() {
    const tonConnectModal = document.getElementById('wallet-modal');
    const manualModal = document.getElementById('wallet-manual-modal');

    if (tonConnectModal) tonConnectModal.style.display = 'none';
    if (!manualModal) return;

    manualModal.style.display = 'flex';

    // Setup form submit
    const form = document.getElementById('wallet-modal-form');
    const input = document.getElementById('wallet-modal-input');
    const closeBtn = document.getElementById('wallet-manual-close');

    if (form) {
        form.onsubmit = async (e) => {
            e.preventDefault();
            const walletAddress = input.value.trim();

            if (!walletAddress) {
                if (typeof Toast !== 'undefined') {
                    Toast.error(AppState.getAppData()?.translations?.enter_wallet || 'Введіть адресу гаманця');
                }
                return;
            }

            // Validate format
            const walletPattern = /^(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_-]{46,48}$/;
            if (!walletPattern.test(walletAddress)) {
                if (typeof Toast !== 'undefined') {
                    Toast.error('Невірний формат адреси гаманця');
                }
                return;
            }

            try {
                if (typeof Render !== 'undefined' && Render.trackEvent) {
                    Render.trackEvent('wallet_added', { method: 'manual' });
                } else if (typeof trackEvent === 'function') {
                    trackEvent('wallet_added', { method: 'manual' });
                }
                const botId = AppState.getBotId();
                const initData = AppState.getTg()?.initData || null;

                if (botId && typeof Api !== 'undefined' && Api.saveWallet) {
                    await Api.saveWallet(botId, walletAddress, AppState.getUserId(), initData);

                    // Update app data
                    const appData = AppState.getAppData();
                    if (appData && appData.user) {
                        appData.user.wallet = walletAddress;
                        AppState.setAppData(appData);
                    }

                    // Hide modal and banner
                    manualModal.style.display = 'none';
                    if (typeof Render !== 'undefined' && Render.renderWalletBanner) {
                        Render.renderWalletBanner();
                    } else {
                        renderWalletBanner();
                    }

                    if (typeof Toast !== 'undefined') {
                        Toast.success('✅ Гаманець збережено успішно!');
                    }
                    if (typeof Haptic !== 'undefined') {
                        Haptic.success();
                    }
                }
            } catch (error) {
                console.error('Error saving wallet:', error);
                if (typeof Toast !== 'undefined') {
                    Toast.error('❌ Помилка збереження: ' + (error.message || 'Невідома помилка'));
                }
                if (typeof Haptic !== 'undefined') {
                    Haptic.error();
                }
            }
        };
    }

    if (closeBtn) {
        closeBtn.onclick = () => {
            manualModal.style.display = 'none';
            if (typeof Haptic !== 'undefined') {
                Haptic.light();
            }
        };
    }

    // Close on overlay click
    manualModal.onclick = (e) => {
        if (e.target === manualModal) {
            manualModal.style.display = 'none';
        }
    };
}

/**
 * Render Social Proof (event-based, NOT financial)
 */
function renderSocialProof() {
    const container = document.getElementById('social-proof');
    if (!container) return;

    // TODO: Get from internal events API
    // For now, show placeholder
    container.innerHTML = `
        <div class="social-proof-item">👥 ${AppState.getAppData()?.translations?.started_path || '47 людей почали 7% шлях'}</div>
        <div class="social-proof-item">⭐ ${AppState.getAppData()?.translations?.top_opened_today || 'TOP відкривали 19 разів сьогодні'}</div>
        <div class="social-proof-item">🔥 ${AppState.getAppData()?.translations?.partners_clicked_most || 'Найчастіше клікають партнерів'}</div>
    `;
}

/**
 * Calculate user status based on actions
 * Statuses: Starter → Pro → Hub
 */
function calculateUserStatus() {
    const appData = AppState.getAppData();
    if (!appData) return 'starter';

    const didStart7Flow = AppState.getDidStart7Flow();
    const topLocked = AppState.getTopLocked();
    const referralCount = AppState.getReferralCount();
    const user = appData.user || {};

    // Count actions (non-financial)
    let actionScore = 0;

    // Started 7% flow = 1 point
    if (didStart7Flow) actionScore += 1;

    // TOP unlocked = 2 points
    if (!topLocked) actionScore += 2;

    // Referrals (1 point per 2 referrals, max 3 points)
    actionScore += Math.min(Math.floor(referralCount / 2), 3);

    // Wallet connected = 1 point
    if (user.wallet) actionScore += 1;

    // Determine status
    if (actionScore >= 5) return 'hub';
    if (actionScore >= 2) return 'pro';
    return 'starter';
}

/**
 * Get user badges based on actions
 */
function getUserBadges() {
    const badges = [];
    const appData = AppState.getAppData();
    if (!appData) return badges;

    const didStart7Flow = AppState.getDidStart7Flow();
    const topLocked = AppState.getTopLocked();
    const referralCount = AppState.getReferralCount();
    const user = appData.user || {};

    // 7% Path Started badge
    if (didStart7Flow) {
        badges.push({ name: AppState.getAppData()?.translations?.badge_7_path || '7% Path Started', icon: '🎯' });
    }

    // TOP Member badge
    if (!topLocked) {
        badges.push({ name: AppState.getAppData()?.translations?.badge_top_member || 'TOP Member', icon: '⭐' });
    }

    // Super Sharer badge (3+ referrals)
    if (referralCount >= 3) {
        badges.push({ name: AppState.getAppData()?.translations?.badge_super_sharer || 'Super Sharer', icon: '🚀' });
    }

    return badges;
}

/**
 * Render Gamification (Status, Badges, Progress)
 */
function renderGamification() {
    const container = document.getElementById('gamification');
    if (!container) return;

    const appData = AppState.getAppData();
    const status = calculateUserStatus();
    const badges = getUserBadges();
    const referralCount = AppState.getReferralCount();
    const topLocked = AppState.getTopLocked();

    // Extract earnings if available
    const balance = appData?.user?.balance || appData?.earnings?.total_earned || 0;
    const currency = appData?.config?.currency || 'TON';

    // Status labels
    const statusLabels = {
        starter: { label: 'Starter', icon: '🌱', color: '#4CAF50' },
        pro: { label: 'Pro', icon: '⚡', color: '#2196F3' },
        hub: { label: 'Hub', icon: '🔥', color: '#FF9800' }
    };

    const currentStatus = statusLabels[status] || statusLabels.starter;

    // Calculate progress to next status
    let progressPercent = 0;
    let progressLabel = '';

    if (status === 'starter') {
        progressPercent = Math.min(50, (referralCount * 25));
        progressLabel = 'До Pro';
    } else if (status === 'pro') {
        progressPercent = Math.min(80, 50 + (referralCount * 10));
        progressLabel = 'До Hub';
    } else {
        progressPercent = 100;
        progressLabel = 'Максимальний рівень';
    }

    // TOP progress
    const topProgress = topLocked ? (referralCount / 5) * 100 : 100;

    container.innerHTML = `
        <div class="gamification-content">
            <!-- Earnings Overview (Integrated /earnings) -->
            <div class="earnings-overview">
                <div class="earnings-overview-title">${appData?.translations?.your_earnings || 'Ваш заробіток'}</div>
                <div class="earnings-amount">${balance} ${currency}</div>
                <div class="earnings-7percent-info">
                    ${AppState.getDidStart7Flow() ? '✅ 7% Program Active' : '❌ 7% Program Inactive'}
                </div>
            </div>

            <!-- User Status -->
            <div class="user-status">
                <div class="status-badge" style="background: ${currentStatus.color}20; border-color: ${currentStatus.color};">
                    <span class="status-icon">${currentStatus.icon}</span>
                    <span class="status-label">${currentStatus.label}</span>
                </div>
                
                <!-- Status Progress -->
                <div class="status-progress">
                    <div class="progress-header">
                        <span class="progress-label">${progressLabel}</span>
                        <span class="progress-percent">${Math.round(progressPercent)}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progressPercent}%; background: ${currentStatus.color};"></div>
                    </div>
                </div>
            </div>
            
            <!-- Badges -->
            ${badges.length > 0 ? `
                <div class="user-badges">
                    <h3 class="badges-title">🏆 ${appData?.translations?.achievements || 'Досягнення'}</h3>
                    <div class="badges-list">
                        ${badges.map(badge => `
                            <div class="badge-item">
                                <span class="badge-icon">${badge.icon}</span>
                                <span class="badge-name">${escapeHtml(badge.name)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            <!-- TOP Progress (if locked) -->
            ${topLocked ? `
                <div class="top-progress">
                    <div class="progress-header">
                        <span class="progress-label">${appData?.translations?.unlock_top || 'Розблокувати TOP'}</span>
                        <span class="progress-percent">${referralCount} / 5</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${topProgress}%;"></div>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

/**
 * Render Info Section (Integrated /info command)
 */
/**
 * Render Info Section (Integrated /info command)
 */
function renderInfoSection(isFooter = false) {
    const container = document.getElementById('info-content');
    const sectionContainer = document.getElementById('info-section');
    const btn = document.getElementById('info-collapse-btn');

    if (!container || !btn) return;

    // Footer Mode Styling
    if (isFooter && sectionContainer) {
        sectionContainer.style.marginTop = '40px';
        sectionContainer.style.marginBottom = '20px';
        sectionContainer.style.textAlign = 'center';

        // Change button to look like a discreet link
        btn.style.background = 'transparent';
        btn.style.border = 'none';
        btn.style.color = 'var(--tg-theme-hint-color)';
        btn.style.fontSize = '12px';
        btn.style.width = 'auto';
        btn.style.display = 'inline-flex';
        btn.style.opacity = '0.7';

        // Update button content for footer look
        btn.innerHTML = '<span>ℹ️ Інформація про бот</span>';
    }

    const appData = AppState.getAppData();

    // Populate content from translations if available
    const infoContent = appData?.translations?.bot_info_content || `
        <p>Цей Mini App дозволяє вам заробляти на партнерській програмі Telegram безпосередньо в метерджері.</p>
        <h3>Як це працює:</h3>
        <p>1. <b>Виберіть партнера</b> в розділі "Партнери".</p>
        <p>2. <b>Активуйте потік</b> (якщо потрібно) та отримайте персональне посилання.</p>
        <p>3. <b>Діліться посиланням</b> з друзями або в групах.</p>
        <p>4. <b>Отримуйте комісію</b> до 7% від кожної успішної дії за вашим посиланням.</p>
        <h3>Вивід коштів:</h3>
        <p>Виплати здійснюються на TON гаманець. Ви можете підключити його у верхній частині головного екрану.</p>
    `;

    container.innerHTML = infoContent;

    // Handle toggle
    btn.onclick = () => {
        const isHidden = container.style.display === 'none';
        container.style.display = isHidden ? 'block' : 'none';

        // Update styling when opened
        if (isFooter && isHidden) {
            container.style.textAlign = 'left';
            container.style.background = 'rgba(255,255,255,0.05)';
            container.style.padding = '15px';
            container.style.borderRadius = '12px';
            container.style.marginTop = '10px';
        }

        if (!isFooter) btn.classList.toggle('active', !isHidden);

        // Haptic feedback
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.selectionChanged();
        }

        trackEvent('info_section_toggle', { opened: !isHidden });
    };
}

/**
 * Track analytics event
 */
function trackEvent(eventName, data = {}) {
    console.log('Track event:', eventName, data);

    // Send to backend if API available
    const botId = AppState.getBotId();
    const initData = AppState.getTg()?.initData || null;
    const tg = AppState.getTg();

    // Extract user data from initDataUnsafe for tracking
    const userData = {};
    if (tg?.initDataUnsafe?.user) {
        const user = tg.initDataUnsafe.user;
        if (user.username) userData.username = user.username;
        if (user.first_name) userData.first_name = user.first_name;
        if (user.last_name) userData.last_name = user.last_name;
        if (user.language_code) userData.language_code = user.language_code;
    }

    // Extract device/platform info from Telegram WebApp
    if (tg?.version) userData.telegram_version = tg.version;
    if (tg?.platform) userData.platform = tg.platform;

    // Get device info from appData if available
    const appData = AppState.getAppData();
    if (appData?.user) {
        if (appData.user.device && !userData.device) userData.device = appData.user.device;
        if (appData.user.device_version && !userData.device_version) userData.device_version = appData.user.device_version;
    }

    // Merge user data with event-specific data
    const enrichedData = {
        ...userData,
        ...data,
        source: 'mini_app',
        mini_app_v2: true
    };

    if (botId && typeof Api !== 'undefined' && Api.sendCallback) {
        Api.sendCallback(botId, {
            type: 'analytics',
            event: eventName,
            data: enrichedData
        }, initData).catch(err => console.error('Error tracking event:', err));
    }
}

/**
 * Translate static elements in index.html
 */
function translateStaticElements() {
    const translations = AppState.getAppData()?.translations || {};

    // Header
    const botNameEl = document.getElementById('bot-name');
    if (botNameEl) botNameEl.textContent = AppState.getAppData()?.config?.name || 'Mini App';

    // Loading
    const loadingText = document.getElementById('loading-text');
    if (loadingText) loadingText.textContent = translations.loading || 'Завантаження...';

    // Navigation
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        const tabName = tab.getAttribute('data-tab');
        const label = tab.querySelector('.tab-label');
        if (label) {
            if (tabName === 'home') label.textContent = translations.nav_home || 'Головна';
            if (tabName === 'partners') label.textContent = translations.nav_partners || 'Партнери';
            if (tabName === 'top') label.textContent = translations.nav_top || 'TOP';
        }
    });

    // Onboarding
    const onboardingTitle1 = document.getElementById('onboarding-title-1');
    if (onboardingTitle1) onboardingTitle1.textContent = translations.onboarding_title_1 || 'Тут заробляють на дії у Telegram';

    const onboardingNextText = document.getElementById('onboarding-next-text');
    if (onboardingNextText) onboardingNextText.textContent = translations.next || 'Далі';

    const onboardingStep1Text = document.getElementById('onboarding-step-1-text');
    if (onboardingStep1Text) onboardingStep1Text.textContent = translations.onboarding_step_1 || 'Активуй 7%';

    const onboardingStep2Text = document.getElementById('onboarding-step-2-text');
    if (onboardingStep2Text) onboardingStep2Text.textContent = translations.onboarding_step_2 || 'Поділись лінкою';

    const onboardingStep3Text = document.getElementById('onboarding-step-3-text');
    if (onboardingStep3Text) onboardingStep3Text.textContent = translations.onboarding_step_3 || 'Люди купують → ти отримуєш %';

    const onboardingStartText = document.getElementById('onboarding-start-text');
    if (onboardingStartText) onboardingStartText.textContent = translations.start || 'Поти';

    // Share Popup
    const sharePopupTitle = document.getElementById('share-popup-title');
    if (sharePopupTitle) sharePopupTitle.textContent = translations.share_popup_title || 'Поділися лінкою';

    const sharePopupTextText = document.getElementById('share-popup-text');
    if (sharePopupTextText) sharePopupTextText.textContent = translations.share_popup_text || 'Я підʼєднався до партнерської програми Telegram. Це працює автоматично.';

    const sharePopupShareText = document.getElementById('share-popup-share-text');
    if (sharePopupShareText) sharePopupShareText.textContent = translations.share || 'Поділитися';

    const sharePopupCloseText = document.getElementById('share-popup-close-text');
    if (sharePopupCloseText) sharePopupCloseText.textContent = translations.close || 'Закрити';

    // Trust Header
    const trustItem1 = document.getElementById('trust-item-1');
    if (trustItem1) trustItem1.textContent = translations.trust_item_1 || '🟢 Official Telegram Partner Program';

    const trustItem2 = document.getElementById('trust-item-2');
    if (trustItem2) trustItem2.textContent = translations.trust_item_2 || '🟢 Revenue share model (до 7%)';

    const trustItem3 = document.getElementById('trust-item-3');
    if (trustItem3) trustItem3.textContent = translations.trust_item_3 || '🟢 Wallet: optional';

    // Share Strip
    const shareBtnText = document.getElementById('share-btn-text');
    if (shareBtnText) shareBtnText.textContent = translations.share || 'Поділитися';

    const shareCopy1 = document.getElementById('share-copy-1');
    if (shareCopy1) shareCopy1.textContent = translations.share_copy_1 || 'Твоя лінка працює 24/7';

    const shareCopy2 = document.getElementById('share-copy-2');
    if (shareCopy2) shareCopy2.textContent = translations.share_copy_2 || 'Кожен новий юзер може запускати цей шлях далі';

    // Offline indicator
    const offlineText = document.querySelector('.offline-text');
    if (offlineText) offlineText.textContent = translations.offline || 'Немає інтернет-з\'єднання';

    // Partner Search
    const searchInput = document.getElementById('partner-search');
    if (searchInput) searchInput.placeholder = translations.search_placeholder || '🔍 Пошук партнерів...';

    // Wallet Manual Input Modal
    const walletManualTitle = document.getElementById('wallet-manual-title');
    if (walletManualTitle) walletManualTitle.textContent = translations.wallet_title || 'Підключити TON гаманець';

    const walletModalCopy = document.getElementById('wallet-modal-copy');
    if (walletModalCopy) walletModalCopy.innerHTML = translations.wallet_modal_copy || 'Потрібно лише для майбутніх виплат<br>Ніколи не списуємо кошти';

    const walletInstructionsTitle = document.getElementById('wallet-instructions-title');
    if (walletInstructionsTitle) walletInstructionsTitle.textContent = translations.wallet_instructions_title || 'Як знайти адресу гаманця:';

    const walletInstruction1 = document.getElementById('wallet-instruction-1');
    if (walletInstruction1) walletInstruction1.textContent = translations.wallet_instruction_1 || 'Відкрий свій TON гаманець (Tonkeeper, MyTonWallet, Tonhub)';

    const walletInstruction2 = document.getElementById('wallet-instruction-2');
    if (walletInstruction2) walletInstruction2.textContent = translations.wallet_instruction_2 || 'Знайди розділ "Receive" або "Отримати"';

    const walletInstruction3 = document.getElementById('wallet-instruction-3');
    if (walletInstruction3) walletInstruction3.textContent = translations.wallet_instruction_3 || 'Скопіюй адресу (починається з EQ, UQ, kQ або 0Q)';

    const walletModalInputLabel = document.getElementById('wallet-modal-input-label');
    if (walletModalInputLabel) walletModalInputLabel.textContent = translations.enter_wallet_label || 'Адреса TON гаманця:';

    const walletModalSaveBtn = document.getElementById('wallet-modal-save-btn');
    if (walletModalSaveBtn) walletModalSaveBtn.textContent = translations.save || 'Зберегти';

    const walletManualSaveBtn = document.getElementById('wallet-manual-save-btn');
    if (walletManualSaveBtn) walletManualSaveBtn.textContent = translations.save || 'Зберегти';

    const walletManualClose = document.getElementById('wallet-manual-close');
    if (walletManualClose) walletManualClose.textContent = translations.cancel || 'Скасувати';

    // Wallet Banner
    const walletBannerText = document.getElementById('wallet-banner-text');
    if (walletBannerText) walletBannerText.textContent = translations.wallet_banner_text || 'Підключи гаманець → зможеш виводити';

    const walletBannerBtn = document.getElementById('wallet-banner-btn');
    if (walletBannerBtn) walletBannerBtn.textContent = translations.connect || 'Підключити';

    // Filters
    const sortLabel = document.getElementById('sort-label');
    if (sortLabel) sortLabel.textContent = translations.sort_label || 'Сортування:';

    const sortName = document.getElementById('sort-name');
    if (sortName) sortName.textContent = translations.sort_name || 'За назвою';

    const sortCommission = document.getElementById('sort-commission');
    if (sortCommission) sortCommission.textContent = translations.sort_commission || 'За комісією';

    const sortNew = document.getElementById('sort-new');
    if (sortNew) sortNew.textContent = translations.sort_new || 'Спочатку нові';

    const categoryLabel = document.getElementById('category-label');
    if (categoryLabel) categoryLabel.textContent = translations.category_label || 'Категорія:';

    const filterAll = document.getElementById('filter-all');
    if (filterAll) filterAll.textContent = translations.filter_all || 'Всі';

    const filterNew = document.getElementById('filter-new');
    if (filterNew) filterNew.textContent = translations.filter_new || 'NEW';

    const filterTop = document.getElementById('filter-top');
    if (filterTop) filterTop.textContent = translations.filter_top || 'TOP';

    // Back Button
    const backBtn = document.getElementById('back-btn');
    if (backBtn) backBtn.textContent = translations.back_button || '← Назад';

    // Pull to Refresh
    const pullToRefreshText = document.getElementById('pull-to-refresh-text');
    if (pullToRefreshText) pullToRefreshText.textContent = translations.pull_to_refresh || 'Потягніть для оновлення';
}

// Export via namespace pattern
window.Render = {
    renderApp,
    renderHome,
    renderPartners,
    renderPartnersList,
    renderPartnerDetail,
    renderTop,
    renderTrustHeader,
    renderInfoSection,
    renderPrimaryActionCard,
    renderShareStrip,
    renderWalletBanner,
    showWalletModal,
    renderSocialProof,
    showLoading,
    showError,
    showSkeleton,
    hideSkeleton,
    showWelcomeScreen,
    showOnboarding,
    showSharePopup,
    checkSharePopupTriggers,
    trackPartnerClickForPopup,
    showManualWalletInput,
    showWalletMessage,
    escapeHtml,
    trackEvent,
    renderGamification,
    calculateUserStatus,
    getUserBadges
};

/** 
 * V2 FUNCTIONS FOR HOME REBUILD (FINAL POLISH)
 */

function renderPersistentHeaderV2(user, isTop) {
    const hero = document.getElementById('trust-header');
    if (!hero) return;

    let header = document.getElementById('persistent-header-container');
    if (!header) {
        header = document.createElement('div');
        header.id = 'persistent-header-container';
        hero.parentNode.insertBefore(header, hero);
    }

    // REAL DATA FETCH
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    const realName = tgUser?.first_name || user?.first_name || 'Partner';
    const userAvatarChar = realName.charAt(0).toUpperCase();

    // Badge Logic
    const badgeText = isTop ? '🏆 TOP Partner' : '🌱 Starter';
    const badgeClass = isTop ? 'badge-top' : 'badge-starter';

    // Wallet Logic
    const walletAddress = user?.wallet || AppState.getAppData()?.user?.wallet;
    // Check if wallet connects
    const isWalletConnected = walletAddress && walletAddress.length > 5;

    const walletText = isWalletConnected
        ? `${walletAddress.slice(0, 4)}...${walletAddress.slice(-4)}`
        : '👛 Wallet';

    // active class will color it
    const walletClass = isWalletConnected ? 'wallet-active' : '';

    // Wallet Click Handler - OPEN FOR ALL
    window.handleHeaderWalletClick = () => {
        const event = new CustomEvent('open-wallet-modal');
        document.dispatchEvent(event);
    };

    header.innerHTML = `
        <div class="persistent-header">
            <div class="user-profile">
                <div class="user-avatar">${userAvatarChar}</div>
                <div class="user-info-text">
                    <span class="user-name">${escapeHtml(realName)}</span>
                    <span class="user-badge ${badgeClass}">${badgeText}</span>
                </div>
            </div>
            <button class="wallet-pill-btn ${walletClass}" onclick="handleHeaderWalletClick()">
                ${walletText}
            </button>
        </div>
    `;
}

function renderMoneyMathCardV2(isTop) {
    const teaser = document.getElementById('partners-teaser-container');
    const actionCard = document.getElementById('primary-action-card');
    const refNode = teaser || actionCard;

    if (!refNode) return;

    let benefits = document.getElementById('benefits-card-container');
    if (!benefits) {
        benefits = document.createElement('div');
        benefits.id = 'benefits-card-container';
        if (refNode.nextSibling) {
            refNode.parentNode.insertBefore(benefits, refNode.nextSibling);
        } else {
            refNode.parentNode.appendChild(benefits);
        }
    } else {
        // Re-insert to ensure correct order if it moved
        if (refNode.nextSibling) {
            refNode.parentNode.insertBefore(benefits, refNode.nextSibling);
        } else {
            refNode.parentNode.appendChild(benefits);
        }
    }

    benefits.innerHTML = `
        <div class="benefits-card">
            <div class="benefits-title">💰 Money Math (Твій потенціал)</div>
            <div class="benefit-item">
                <span>👤</span>
                <span>1 user → ~0.35–0.70€</span>
            </div>
            <div class="benefit-item">
                <span>👥</span>
                <span>10 users → ~3.5–7.0€</span>
            </div>
            <div class="benefit-item">
                <span>🚀</span>
                <span>100 users → ~35–70€</span>
            </div>
            <div style="margin-top: 12px; font-size: 11px; color: #8a94a7; text-align: center; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;">
                Заробляй ці суми, запрошуючи друзів та клікаючи партнерів.
                <br>Telegram платить 7% від кожної покупки зірок.
            </div>
        </div>
    `;
}

function renderPartnersTeaser() {
    const actionCard = document.getElementById('primary-action-card');
    if (!actionCard) return;

    let teaser = document.getElementById('partners-teaser-container');
    if (!teaser) {
        teaser = document.createElement('div');
        teaser.id = 'partners-teaser-container';
        if (actionCard.nextSibling) {
            actionCard.parentNode.insertBefore(teaser, actionCard.nextSibling);
        } else {
            actionCard.parentNode.appendChild(teaser);
        }
    }

    teaser.innerHTML = `
        <div class="partners-teaser" onclick="if(typeof Navigation !== 'undefined') { Navigation.switchTab('partners'); } else { console.log('Nav missing'); }">
            <div class="teaser-content">
                <div class="teaser-icon">⚡️</div>
                <div class="teaser-text">
                    <h4>Збільшити дохід</h4>
                    <p>Запускай перевірених партнерів</p>
                </div>
            </div>
            <div class="teaser-action">Go 👉</div>
        </div>
    `;
}
