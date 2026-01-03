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
    
    // Render initial tab (earnings - has instructions on what to do)
    // This helps users understand what the bot does
    // Note: switchTab is called from loadAppData, not here, to avoid double call
}

function renderPartners() {
    const appData = AppState.getAppData();
    if (!appData) return;
    
    AppState.setFilteredPartners([]);
    const partners = appData.partners || [];
    
    if (partners.length === 0) {
        const container = document.getElementById('partners-list');
        if (container) {
            container.innerHTML = '<p class="empty-state">Партнерів поки немає</p>';
        }
        return;
    }
    
    if (typeof Navigation !== 'undefined' && Navigation.applyFilters) {
        Navigation.applyFilters();
    } else {
        applyFilters();
    }
}

function renderPartnersList(partners) {
    const container = document.getElementById('partners-list');
    if (!container) return;
    
    const appData = AppState.getAppData();
    
    // Clear container
    container.innerHTML = '';
    
    if (partners.length === 0) {
        const emptyState = document.createElement('p');
        emptyState.className = 'empty-state';
        emptyState.textContent = 'Партнерів не знайдено';
        container.appendChild(emptyState);
        return;
    }
    
    // Use DocumentFragment for batch DOM operations
    const fragment = document.createDocumentFragment();
    
    partners.forEach((partner, index) => {
        const partnerId = partner.id || `temp-${index}`;
        const partnerIdStr = typeof partnerId === 'string' ? partnerId : String(partnerId);
        const isTop = (appData.top_partners || []).some(p => String(p.id) === String(partner.id));
        const referralLink = partner.referral_link || '';
        
        // Create card element
        const card = document.createElement('div');
        card.className = `partner-card ${isTop ? 'top-partner' : ''}`;
        card.setAttribute('data-partner-id', partnerIdStr);
        
        // Add click handler for card
        card.addEventListener('click', () => {
            if (typeof Haptic !== 'undefined') Haptic.light();
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
        
        // Create description
        const description = document.createElement('p');
        description.className = 'partner-description';
        const descText = (partner.description || '').substring(0, 100);
        description.textContent = descText + (partner.description && partner.description.length > 100 ? '...' : '');
        
        // Create button
        const button = document.createElement('button');
        button.className = 'partner-btn';
        button.textContent = 'Перейти →';
        button.setAttribute('aria-label', `Перейти до партнера ${partner.name || 'Unknown'}`);
        button.addEventListener('click', (e) => {
            e.stopPropagation();
            if (typeof Haptic !== 'undefined') Haptic.medium();
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
    
    container.appendChild(fragment);
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
    const container = document.getElementById('top-content');
    if (!container) {
        console.warn('TOP container not found');
        return;
    }
    
    // Hide skeleton
    const appData = AppState.getAppData();
    if (typeof Render !== 'undefined' && Render.hideSkeleton) {
        Render.hideSkeleton('top');
    } else {
        hideSkeleton('top');
    }
    
    if (!appData) {
        console.warn('appData not loaded yet, showing loading state');
        container.innerHTML = '<div class="loading-state"><p>Завантаження даних...</p></div>';
        return;
    }
    
    // Clear container
    container.innerHTML = '';
    
    const topStatus = appData.user?.top_status || 'locked';
    const topPartners = appData.top_partners || [];
    const wasLocked = container.classList.contains('locked');
    
    if (topStatus === 'locked') {
        const invitesNeeded = appData.earnings?.invites_needed || 0;
        const buyTopPrice = appData.earnings?.buy_top_price || 1;
        const canUnlockTop = appData.earnings?.can_unlock_top || false;
        
        const lockedDiv = document.createElement('div');
        lockedDiv.className = 'locked-state';
        
        const h2 = document.createElement('h2');
        h2.textContent = 'TOP закрито';
        
        const p1 = document.createElement('p');
        p1.textContent = `Запроси ${invitesNeeded} друзів щоб розблокувати TOP`;
        
        const p2 = document.createElement('p');
        p2.textContent = `Або купи доступ за ${buyTopPrice} ⭐`;
        
        const button = document.createElement('button');
        button.className = 'action-btn unlock-btn';
        
        if (canUnlockTop) {
            button.textContent = 'Розблокувати TOP';
            button.setAttribute('aria-label', 'Розблокувати TOP через заробітки');
            button.addEventListener('click', () => {
                if (typeof Haptic !== 'undefined') Haptic.medium();
                if (typeof Navigation !== 'undefined' && Navigation.switchTab) {
                    Navigation.switchTab('earnings');
                } else {
                    switchTab('earnings');
                }
            });
        } else {
            button.textContent = `Купити доступ за ${buyTopPrice} ⭐`;
            button.setAttribute('aria-label', `Купити доступ до TOP за ${buyTopPrice} зірок`);
            button.addEventListener('click', () => {
                if (typeof Haptic !== 'undefined') Haptic.medium();
                if (typeof Actions !== 'undefined' && Actions.handleBuyTop) {
                    Actions.handleBuyTop(buyTopPrice);
                } else {
                    handleBuyTop(buyTopPrice);
                }
            });
        }
        
        lockedDiv.appendChild(h2);
        lockedDiv.appendChild(p1);
        lockedDiv.appendChild(p2);
        lockedDiv.appendChild(button);
        container.appendChild(lockedDiv);
    } else {
        // Check if was just unlocked
        if (wasLocked) {
            container.classList.add('unlocked');
            setTimeout(() => {
                container.classList.remove('unlocked');
            }, 1000);
        }
        
        if (topPartners.length === 0) {
            const emptyState = document.createElement('p');
            emptyState.className = 'empty-state';
            emptyState.textContent = 'TOP партнерів поки немає';
            container.appendChild(emptyState);
        } else {
            // Use DocumentFragment for batch DOM operations
            const fragment = document.createDocumentFragment();
            
            topPartners.forEach((partner, index) => {
                const partnerId = partner.id || `temp-top-${index}`;
                const partnerIdStr = typeof partnerId === 'string' ? partnerId : String(partnerId);
                const referralLink = partner.referral_link || '';
                
                // Create card element
                const card = document.createElement('div');
                card.className = 'partner-card top-partner';
                card.setAttribute('data-partner-id', partnerIdStr);
                
                // Add click handler for card
                card.addEventListener('click', () => {
                    if (typeof Haptic !== 'undefined') Haptic.light();
                    showPartnerDetail(partnerIdStr);
                });
                
                // Create header
                const header = document.createElement('div');
                header.className = 'partner-header';
                
                const name = document.createElement('h3');
                name.className = 'partner-name';
                name.textContent = partner.name || 'Unknown';
                
                const badge = document.createElement('span');
                badge.className = 'commission-badge top-badge';
                badge.textContent = `${partner.commission || 0}%`;
                
                header.appendChild(name);
                header.appendChild(badge);
                
                // Create description
                const description = document.createElement('p');
                description.className = 'partner-description';
                description.textContent = partner.description || '';
                
                // Create button
                const button = document.createElement('button');
                button.className = 'partner-btn';
                button.textContent = 'Перейти →';
                button.setAttribute('aria-label', `Перейти до партнера ${partner.name || 'Unknown'}`);
                button.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (typeof Haptic !== 'undefined') Haptic.medium();
                    openPartner(referralLink, partnerIdStr);
                });
                
                // Assemble card
                card.appendChild(header);
                card.appendChild(description);
                card.appendChild(button);
                
                fragment.appendChild(card);
            });
            
            container.appendChild(fragment);
        }
    }
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

function showError(message) {
    const errorEl = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    const app = document.getElementById('app');
    
    // Show app container so user can still see navigation and retry
    if (app) {
        app.style.display = 'block';
    }
    
    if (errorEl && errorText) {
        errorText.textContent = message;
        errorEl.style.display = 'block';
    }
    
    // Retry button
    const retryBtn = document.getElementById('retry-btn');
    if (retryBtn) {
        retryBtn.onclick = () => {
            if (errorEl) errorEl.style.display = 'none';
            if (typeof loadAppData === 'function') {
                loadAppData();
            }
        };
    }
}

function showSkeleton(pageName) {
    const skeletonId = `${pageName}-skeleton`;
    const skeleton = document.getElementById(skeletonId);
    const contentId = pageName === 'partners' ? 'partners-list' : 
                     pageName === 'top' ? 'top-content' :
                     pageName === 'earnings' ? 'earnings-dashboard' :
                     pageName === 'wallet' ? 'wallet-section' :
                     pageName === 'info' ? 'info-section' : null;
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
    const contentId = pageName === 'partners' ? 'partners-list' : 
                     pageName === 'top' ? 'top-content' :
                     pageName === 'earnings' ? 'earnings-dashboard' :
                     pageName === 'wallet' ? 'wallet-section' :
                     pageName === 'info' ? 'info-section' : null;
    const content = contentId ? document.getElementById(contentId) : null;
    
    if (skeleton) {
        skeleton.style.display = 'none';
    }
    if (content) {
        content.style.display = 'block';
    }
}

function showWelcomeScreen() {
    const welcomeScreen = document.getElementById('welcome-screen');
    const welcomeMessage = document.getElementById('welcome-message');
    const welcomeCloseBtn = document.getElementById('welcome-close-btn');
    
    if (!welcomeScreen || !AppState.getAppData()) return;
    
    // Create clear onboarding message
    const botName = AppState.getAppData().config?.name || 'Mini App';
    const welcomeHTML = `
        <div class="welcome-steps">
            <div class="welcome-step">
                <div class="step-icon">🤝</div>
                <div class="step-content">
                    <h3>Партнери</h3>
                    <p>Обери партнерського бота та отримуй зірки</p>
                </div>
            </div>
            <div class="welcome-step">
                <div class="step-icon">⭐</div>
                <div class="step-content">
                    <h3>TOP партнери</h3>
                    <p>Найкращі пропозиції з високою комісією</p>
                </div>
            </div>
            <div class="welcome-step">
                <div class="step-icon">💰</div>
                <div class="step-content">
                    <h3>Заробітки</h3>
                    <p>Переглянь свій баланс та прогрес</p>
                </div>
            </div>
            <div class="welcome-step">
                <div class="step-icon">👛</div>
                <div class="step-content">
                    <h3>Гаманець</h3>
                    <p>Додай TON гаманець для виведення</p>
                </div>
            </div>
        </div>
        <p class="welcome-hint">👆 Оберіть розділ внизу екрана</p>
    `;
    
    if (welcomeMessage) {
        welcomeMessage.innerHTML = welcomeHTML;
    }
    
    welcomeScreen.style.display = 'flex';
    
    // Hide loading screen when showing welcome screen
    showLoading(false);
    
    // Close welcome screen
    if (welcomeCloseBtn) {
        welcomeCloseBtn.onclick = () => {
            welcomeScreen.style.display = 'none';
            localStorage.setItem('mini_app_welcome_seen', 'true');
            // AppState.getAppData() should already be loaded at this point
            if (AppState.getAppData()) {
                renderApp(); // This will show Earnings tab first
            } else {
                // If AppState.getAppData() not loaded, load it first
                loadAppData(false).then(() => {
                    renderApp();
                });
            }
            showLoading(false);
        };
    }
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
    if (typeof window.escapeHtml === 'function') {
        return window.escapeHtml(text);
    }
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// Export via namespace pattern
window.Render = {
    renderApp,
    renderPartners,
    renderPartnersList,
    renderPartnerDetail,
    renderTop,
    renderEarnings,
    renderWallet,
    renderInfo,
    showLoading,
    showError,
    showSkeleton,
    hideSkeleton,
    showWelcomeScreen,
    showWalletMessage,
    escapeHtml
};
