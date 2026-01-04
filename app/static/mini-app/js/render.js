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
    }
    
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
    const appData = AppState.getAppData();
    if (!appData) {
        console.warn('[Render] renderPartners: appData not available');
        return;
    }
    
    // Track view_partners event
    trackEvent('view_partners');
    
    // Ensure we're on the partners page
    const partnersPage = document.getElementById('partners-page');
    if (!partnersPage || !partnersPage.classList.contains('active')) {
        console.warn('[Render] renderPartners: partners page is not active');
        return;
    }
    
    AppState.setFilteredPartners([]);
    const partners = appData.partners || [];
    
    if (partners.length === 0) {
        const container = document.getElementById('partners-list');
        if (container) {
            container.innerHTML = '<p class="empty-state">Партнерів поки немає</p>';
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
                <h2>🔮 Recommended for you</h2>
                <p class="recommended-subtitle">Партнери, які найчастіше запускають шлях</p>
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
            showMoreBtn.textContent = 'Показати всіх';
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
        emptyState.textContent = 'Партнерів не знайдено';
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
        
        // Determine labels based on partner data
        const labels = [];
        if (isTop) labels.push('⭐ TOP');
        if ((partner.commission || 0) >= 5) labels.push('🔥 часто купують');
        if ((partner.commission || 0) < 3) labels.push('🛡 для новачків');
        if (index < 2) labels.push('⚡ швидкий старт');
        
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
        
        // Create button
        const button = document.createElement('button');
        button.className = 'partner-btn';
        button.textContent = '▶️ Відкрити';
        button.setAttribute('aria-label', `Відкрити партнера ${partner.name || 'Unknown'}`);
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
            content.innerHTML = '<p class="empty-state">Партнер не знайдено</p>';
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
        badge.textContent = `${partner.commission || 0}% комісія`;
        
        header.appendChild(h2);
        header.appendChild(badge);
        
        // Create body
        const body = document.createElement('div');
        body.className = 'partner-detail-body';
        
        const description = document.createElement('p');
        description.className = 'partner-detail-description';
        description.textContent = partner.description || 'Опис відсутній';
        
        const actions = document.createElement('div');
        actions.className = 'partner-detail-actions';
        
        const button = document.createElement('button');
        button.className = 'partner-btn large';
        button.textContent = 'Перейти до партнера';
        button.setAttribute('aria-label', `Перейти до партнера ${partner.name || 'Unknown'}`);
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
    // Ensure we're on the top page
    const topPage = document.getElementById('top-page');
    if (!topPage || !topPage.classList.contains('active')) {
        console.warn('[Render] renderTop: top page is not active');
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
        container.innerHTML = '<div class="loading-state"><p>Завантаження даних...</p></div>';
        return;
    }
    
    // Clear container
    container.innerHTML = '';
    
    const topStatus = appData.user?.top_status || 'locked';
    const topPartners = appData.top_partners || [];
    const referralCount = AppState.getReferralCount();
    const invitesNeeded = appData.earnings?.invites_needed || 5;
    const buyTopPrice = appData.earnings?.buy_top_price || 1;
    
    // Determine state: LOCKED, ALMOST (X >= 3), or UNLOCKED
    let state = 'LOCKED';
    if (topStatus === 'open' || topStatus === 'unlocked') {
        state = 'UNLOCKED';
    } else if (referralCount >= 3 && referralCount < 5) {
        state = 'ALMOST';
    }
    
    if (state === 'LOCKED') {
        renderTopLocked(container, referralCount, invitesNeeded, buyTopPrice, topPartners);
    } else if (state === 'ALMOST') {
        renderTopAlmost(container, referralCount, invitesNeeded, buyTopPrice, topPartners);
    } else {
        renderTopUnlocked(container, topPartners);
    }
}

/**
 * Render TOP LOCKED state (FOMO + Paywall)
 */
function renderTopLocked(container, referralCount, invitesNeeded, buyTopPrice, topPartners) {
    container.className = 'top-locked';
    
    const progress = Math.min(referralCount, invitesNeeded);
    const progressPercent = (progress / invitesNeeded) * 100;
    
    const lockedDiv = document.createElement('div');
    lockedDiv.className = 'top-locked-content';
    
    lockedDiv.innerHTML = `
        <div class="top-locked-header">
            <h2>⭐ TOP = більше видимості твоєї лінки</h2>
            <p class="top-locked-copy">TOP відкривають ті, хто запускає дохід</p>
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
                <span>👥 ${referralCount} / ${invitesNeeded} друзів</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progressPercent}%"></div>
            </div>
        </div>
        
        <div class="top-locked-cta">
            <button class="primary-action-btn" id="invite-for-top-btn">
                ▶️ Запросити друга
            </button>
            <button class="secondary-action-btn" id="buy-top-btn">
                💎 Відкрити за ${buyTopPrice}⭐
            </button>
        </div>
        
        <div class="top-fomo">
            <p>23 людини відкрили TOP сьогодні</p>
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
function renderTopAlmost(container, referralCount, invitesNeeded, buyTopPrice, topPartners) {
    container.className = 'top-almost';
    
    const progress = Math.min(referralCount, invitesNeeded);
    const progressPercent = (progress / invitesNeeded) * 100;
    
    const almostDiv = document.createElement('div');
    almostDiv.className = 'top-almost-content';
    
    // Show 1 partner as preview
    const previewPartner = topPartners[0];
    
    almostDiv.innerHTML = `
        <div class="top-almost-header">
            <h2>Ти майже всередині</h2>
            <p class="top-almost-copy">Ще ${invitesNeeded - referralCount} запрошень до TOP</p>
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
                <span>👥 ${referralCount} / ${invitesNeeded} друзів</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progressPercent}%"></div>
            </div>
        </div>
        
        <div class="top-almost-cta">
            <button class="primary-action-btn" id="invite-almost-btn">
                ▶️ Запросити
            </button>
            <button class="secondary-action-btn" id="buy-almost-btn">
                💎 Відкрити за ${buyTopPrice}⭐
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
            <h2>⭐ TOP партнери</h2>
            <p class="top-unlocked-copy">Тут максимальна конверсія</p>
        </div>
    `;
    
    // Render TOP partners grid
    if (topPartners.length === 0) {
        const emptyState = document.createElement('p');
        emptyState.className = 'empty-state';
        emptyState.textContent = 'TOP партнерів поки немає';
        unlockedDiv.appendChild(emptyState);
    } else {
        const gridContainer = document.createElement('div');
        gridContainer.className = 'partners-grid';
        
        topPartners.forEach((partner, index) => {
            const card = document.createElement('div');
            card.className = 'partner-card top-partner';
            card.setAttribute('data-partner-id', String(partner.id));
            
            card.innerHTML = `
                <div class="partner-header">
                    <h3 class="partner-name">${escapeHtml(partner.name || 'Unknown')}</h3>
                    <span class="commission-badge top-badge">${partner.commission || 0}%</span>
                </div>
                <div class="partner-labels">
                    <span class="partner-label">⭐ TOP</span>
                    <span class="partner-label">🔥 часто купують</span>
                </div>
                <p class="partner-description">${escapeHtml((partner.description || '').substring(0, 100))}${partner.description && partner.description.length > 100 ? '...' : ''}</p>
                <button class="partner-btn highlight-cta">▶️ Перейти</button>
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
        container.innerHTML = '<div class="loading-state"><p>Завантаження даних...</p></div>';
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
                <h2>Заробітки</h2>
            </div>
            
            <!-- Balance Card -->
            <div class="earnings-section-card">
                <div class="section-header">
                    <h3 class="section-title">Твій баланс</h3>
                </div>
                <div class="balance-display">
                    <span class="balance-amount">${earnings.earned || 0} TON</span>
                    <span class="balance-label">Зароблено</span>
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
                    <h3 class="section-title">Реферальна лінка</h3>
                </div>
                ${user.referral_link ? `
                <div class="referral-section">
                    <div class="referral-link-box">
                        <code>${user.referral_link}</code>
                    </div>
                    <div class="referral-actions">
                        <button class="copy-btn" data-action="copy-referral">📋 Копіювати</button>
                        <button class="share-btn" data-action="share-referral">📤 Поділитися</button>
                    </div>
                </div>
                ` : `
                <p class="empty-state">Реферальна лінка генерується...</p>
                `}
            </div>
            
            <!-- 7% Program Card -->
            <div class="earnings-section-card">
                <div class="section-header">
                    <h3 class="section-title">${commissionPercent}% від Telegram</h3>
                </div>
                <details class="accordion">
                    <summary class="accordion-summary">Деталі та інструкції</summary>
                    <div class="accordion-body">
                        <div class="commission-info">
                            <p class="info-text">Офіційна партнерська програма Telegram. Коли люди переходять по твоїй лінці, запускають бота та купують зірки — Telegram ділиться з тобою доходом (~${commissionPercent}%).</p>
                            <div class="commission-example-box">
                                <p class="example-label">Скільки може приносити один юзер:</p>
                                <ul class="example-list">
                                    <li>1 юзер → ~0.35-0.70€</li>
                                    <li>10 юзерів → ~3.5-7€</li>
                                    <li>100 юзерів → ~35-70€</li>
                                </ul>
                            </div>
                        </div>
                        <div class="commission-activate">
                            <h4 class="activate-title">Як активувати ${commissionPercent}% (1 раз назавжди):</h4>
                            <div class="activate-steps">
                                <div class="activate-step">Відкрий @HubAggregatorBot</div>
                                <div class="activate-step">«Партнерська програма»</div>
                                <div class="activate-step">«Під'єднатись» → ${commissionPercent}% активуються назавжди</div>
                            </div>
                        </div>
                    </div>
                </details>
            </div>
            
            <!-- What to do next Card -->
            <div class="earnings-section-card">
                <div class="section-header">
                    <h3 class="section-title">Що зробити прямо зараз</h3>
                </div>
                <details class="accordion">
                    <summary class="accordion-summary">План дій</summary>
                    <div class="accordion-body">
                        <div class="action-steps-simple">
                            <div class="action-step-item">
                                <span class="action-step-text">Додай ще ${earnings.invites_needed || 0} друзів → TOP відкриється</span>
                            </div>
                            <div class="action-step-item">
                                <span class="action-step-text">Активуй свої ${commissionPercent}%</span>
                            </div>
                            <div class="action-step-item">
                                <span class="action-step-text">Кинь цю лінку в 1-2 "живі" чати або друзів — кожен юзер може приносити тобі €</span>
                            </div>
                            <div class="action-step-item">
                                <span class="action-step-text">Запускай TOP-партнерів</span>
                            </div>
                        </div>
                        <p class="auto-stats">Статистика оновлюється автоматично</p>
                    </div>
                </details>
            </div>
            
            <!-- Action Buttons -->
            <div class="earnings-actions">
                ${earnings.can_unlock_top ? `
                    <button class="action-btn unlock-btn" data-action="switch-top" aria-label="Відкрити TOP партнерів">
                        ${translations.btn_top_partners || 'Відкрити TOP'}
                    </button>
                ` : `
                    <button class="action-btn unlock-btn" data-action="buy-top" data-price="${earnings.buy_top_price || 1}" aria-label="Розблокувати TOP за ${earnings.buy_top_price || 1} зірок">
                        ${translations.btn_unlock_top || `Розблокувати TOP (${earnings.buy_top_price || 1} ⭐)`}
                    </button>
                `}
                <button class="action-btn activate-btn" data-action="activate-7" aria-label="Активувати програму 7% комісії">
                    ${translations.btn_activate_7 || 'Активувати 7%'}
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
            <h2>TON Гаманець</h2>
            ${hasWallet ? `
                <div class="current-wallet">
                    <p>Поточний гаманець:</p>
                    <code class="wallet-address">${wallet}</code>
                </div>
            ` : walletHelp ? `
                <div class="wallet-help">
                    <p>${escapeHtml(walletHelp).replace(/\n/g, '<br>')}</p>
                </div>
            ` : `
                <div class="wallet-help">
                    <p>⚠️ У вас ще немає збереженого TON гаманця.</p>
                    <p>Відкрийте будь-який TON гаманець, скопіюйте адресу та введіть її нижче.</p>
                </div>
            `}
            <form id="wallet-form">
                <label for="wallet-input">Введіть TON гаманець:</label>
                <input 
                    type="text" 
                    id="wallet-input" 
                    class="wallet-input" 
                    placeholder="EQ..."
                    value="${wallet}"
                    pattern="^(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_-]{46,48}$"
                    required
                />
                <button type="submit" class="save-btn">Зберегти</button>
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
                ${safeMessage || '<p>Інформація про бота</p>'}
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
            displayMessage = 'Проблеми з інтернет-з\'єднанням. Перевірте підключення та спробуйте ще раз.';
        } else if (errorType === 'api') {
            displayMessage = 'Помилка завантаження даних. Спробуйте пізніше.';
        } else if (errorType === 'validation') {
            displayMessage = 'Невірні дані. Перевірте введену інформацію.';
        }
        
        errorText.textContent = displayMessage;
        errorEl.style.display = 'block';
        
        // Add error type class for styling
        errorEl.className = `error-message error-${errorType}`;
    }
    
    // Retry button
    const retryBtn = document.getElementById('retry-btn');
    if (retryBtn) {
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
    if (didStart7Flow && lastSharePopup !== 'start_7_flow') {
        showSharePopup('start_7_flow');
        storage.setItem('last_share_popup', 'start_7_flow');
        storage.setItem('last_share_popup_time', String(Date.now()));
        return;
    }
    
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
function renderHome() {
    const appData = AppState.getAppData();
    if (!appData) return;
    
    // Track view_home event
    trackEvent('view_home');
    
    // Render Trust Header (static)
    renderTrustHeader();
    
    // Render Primary Action Card (with priority logic)
    renderPrimaryActionCard();
    
    // Render Share Strip (always visible)
    renderShareStrip();
    
    // Render Wallet Banner (contextual, if not connected)
    renderWalletBanner();
    
    // Render Social Proof (event-based)
    renderSocialProof();
    
    // Render Gamification (Status, Badges, Progress)
    renderGamification();
}

/**
 * Render Trust Header (static, only facts)
 */
function renderTrustHeader() {
    const container = document.getElementById('trust-header');
    if (!container) return;
    
    // Trust Header is already in HTML, just ensure it's visible
    container.style.display = 'block';
    
    // Update wallet status if available
    const appData = AppState.getAppData();
    if (appData && appData.wallet) {
        const walletItem = container.querySelector('.trust-item:last-child');
        if (walletItem) {
            walletItem.textContent = '🟢 Wallet: connected';
        }
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
            <h2>💸 Підʼєднай 7% від Telegram</h2>
        </div>
        <div class="action-card-body">
            <p class="action-card-copy">Telegram ділиться доходом, якщо твої реферали купують ⭐</p>
            <div class="action-card-badges">
                <span class="badge">🟢 Official</span>
                <span class="badge">♾️ One-time setup</span>
                <span class="badge">🛡 Safe</span>
            </div>
        </div>
        <div class="action-card-footer">
            <button class="primary-action-btn" id="start-7-flow-btn" aria-label="Почати 7% flow">
                ▶️ Почати
            </button>
            <p class="action-card-subtext">Чим раніше запустиш шлях — тим більше шансів отримувати %</p>
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
            
            // Open official Telegram partner screen
            const tg = AppState.getTg();
            if (tg && tg.openLink) {
                tg.openLink('https://t.me/HubAggregatorBot');
            }
            
            // Show instruction modal (1 time)
            show7FlowInstructionModal();
            
            // Check for share popup trigger
            setTimeout(() => {
                if (typeof checkSharePopupTriggers === 'function') {
                    checkSharePopupTriggers();
                }
            }, 1000);
            
            // Re-render to show next state
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
            <h2>⭐ TOP = більше покупок → більше %</h2>
        </div>
        <div class="action-card-body">
            <p class="action-card-copy">TOP бачать найвигідніші Mini Apps і частіше купують ⭐</p>
            <div class="top-progress">
                <div class="progress-info">
                    <span>👥 ${referralCount} / ${needed} друзів</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progressPercent}%"></div>
                </div>
            </div>
        </div>
        <div class="action-card-footer">
            <button class="primary-action-btn" id="invite-friend-btn" aria-label="Запросити друга">
                ▶️ Запросити
            </button>
            <button class="secondary-action-btn" id="buy-top-btn" aria-label="Купити TOP за 1 Star">
                💎 Відкрити за 1⭐
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
            // Handle TOP purchase
            if (typeof Actions !== 'undefined' && Actions.handleBuyTop) {
                Actions.handleBuyTop();
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
            <h2>🔥 Запусти партнерів</h2>
        </div>
        <div class="action-card-body">
            <p class="action-card-copy">Кожен клік → потенційна покупка → Telegram платить %</p>
        </div>
        <div class="action-card-footer">
            <button class="primary-action-btn" id="go-to-partners-btn" aria-label="Перейти до партнерів">
                ▶️ Перейти до партнерів
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
    
    modal.innerHTML = `
        <div class="modal-content" style="background: var(--tg-theme-bg-color); border-radius: var(--radius-lg); padding: var(--spacing-lg); max-width: 90%; max-height: 80vh; overflow-y: auto;">
            <h2 style="margin: 0 0 var(--spacing-md) 0; font-size: var(--font-size-xl);">💸 Як активувати 7%</h2>
            <div style="margin-bottom: var(--spacing-md);">
                <p style="margin: var(--spacing-sm) 0; line-height: 1.5;">1. Відкрий @HubAggregatorBot в Telegram</p>
                <p style="margin: var(--spacing-sm) 0; line-height: 1.5;">2. Надішли команду /earnings</p>
                <p style="margin: var(--spacing-sm) 0; line-height: 1.5;">3. Слідуй інструкціям для активації</p>
            </div>
            <button class="primary-action-btn" id="close-7-flow-modal" style="width: 100%;">
                Зрозуміло
            </button>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close modal handlers
    const closeBtn = modal.querySelector('#close-7-flow-modal');
    const closeModal = () => {
        document.body.removeChild(modal);
    };
    
    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
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
    
    // Show banner only if wallet is not connected
    if (!walletTrimmed || walletTrimmed.length < 20) {
        banner.style.display = 'block';
        
        // Setup button click
        const btn = document.getElementById('wallet-banner-btn');
        if (btn && !btn.hasAttribute('data-listener')) {
            btn.setAttribute('data-listener', 'true');
            btn.addEventListener('click', () => {
                trackEvent('wallet_banner_clicked');
                showWalletModal();
            });
        }
    } else {
        banner.style.display = 'none';
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
                tg.showAlert('TON Connect — це офіційний протокол для підключення TON гаманців у Telegram Mini Apps. Він дозволяє безпечно підключати гаманці без передачі приватних ключів.');
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
                    Toast.error('Введіть адресу гаманця');
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
        <div class="social-proof-item">👥 47 людей почали 7% шлях</div>
        <div class="social-proof-item">⭐ TOP відкривали 19 разів сьогодні</div>
        <div class="social-proof-item">🔥 Найчастіше клікають партнерів</div>
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
        badges.push({ name: '7% Path Started', icon: '🎯' });
    }
    
    // TOP Member badge
    if (!topLocked) {
        badges.push({ name: 'TOP Member', icon: '⭐' });
    }
    
    // Super Sharer badge (3+ referrals)
    if (referralCount >= 3) {
        badges.push({ name: 'Super Sharer', icon: '🚀' });
    }
    
    return badges;
}

/**
 * Render Gamification (Status, Badges, Progress)
 */
function renderGamification() {
    const container = document.getElementById('gamification');
    if (!container) return;
    
    const status = calculateUserStatus();
    const badges = getUserBadges();
    const referralCount = AppState.getReferralCount();
    const topLocked = AppState.getTopLocked();
    
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
        // Progress to Pro (need 2 action points)
        progressPercent = Math.min(50, (referralCount * 25)); // Simplified
        progressLabel = 'До Pro';
    } else if (status === 'pro') {
        // Progress to Hub (need 5 action points total)
        progressPercent = Math.min(80, 50 + (referralCount * 10)); // Simplified
        progressLabel = 'До Hub';
    } else {
        // Hub - max level
        progressPercent = 100;
        progressLabel = 'Максимальний рівень';
    }
    
    // TOP progress
    const topProgress = topLocked ? (referralCount / 5) * 100 : 100;
    
    container.innerHTML = `
        <div class="gamification-content">
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
                    <h3 class="badges-title">🏆 Досягнення</h3>
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
                        <span class="progress-label">Розблокувати TOP</span>
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
 * Track analytics event
 */
function trackEvent(eventName, data = {}) {
    console.log('Track event:', eventName, data);
    
    // Send to backend if API available
    const botId = AppState.getBotId();
    const initData = AppState.getTg()?.initData || null;
    
    if (botId && typeof Api !== 'undefined' && Api.sendCallback) {
        Api.sendCallback(botId, {
            type: 'analytics',
            event: eventName,
            data: data
        }, initData).catch(err => console.error('Error tracking event:', err));
    }
}

// Export via namespace pattern
window.Render = {
    renderApp,
    renderHome,
    renderPartners,
    renderPartnersList,
    renderPartnerDetail,
    renderTop,
    renderEarnings,
    renderWallet,
    renderInfo,
    renderTrustHeader,
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
