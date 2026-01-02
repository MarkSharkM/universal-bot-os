/**
 * Main Mini App Logic
 * Telegram WebApp Integration
 */

// API_BASE is defined in api.js (loaded before this file)

// Telegram WebApp instance
let tg = null;
let botId = null;
let userId = null;
let appData = null;

/**
 * Initialize Mini App
 */
async function initMiniApp() {
    try {
        // Get Telegram WebApp instance
        tg = window.Telegram?.WebApp;
        
        if (!tg) {
            console.error('Telegram WebApp SDK not loaded');
            showError('Telegram WebApp SDK не завантажено');
            return;
        }
        
        // Initialize Telegram WebApp
        tg.ready();
        tg.expand();
        
        // Get user data from initData
        const initDataUnsafe = tg.initDataUnsafe;
        const user = initDataUnsafe?.user;
        userId = user?.id?.toString();
        
        // Warn if userId is missing (but continue - API can use initData)
        if (!userId) {
            console.warn('User ID not found in initData, will use initData for validation');
        }
        
        // Get bot_id from URL or initData (async)
        botId = await getBotIdFromUrl();
        
        if (!botId) {
            console.error('Bot ID not found');
            showError('Bot ID не знайдено. Перевірте URL або налаштування бота.');
            return;
        }
        
        // Apply theme from Telegram
        applyTheme();
        
        // Setup event handlers
        setupEventHandlers();
        
        // Load app data
        loadAppData();
        
    } catch (error) {
        console.error('Error initializing Mini App:', error);
        showError('Помилка ініціалізації: ' + error.message);
    }
}

/**
 * Get bot_id from URL or initData
 * Priority: URL query param > initData API call
 */
async function getBotIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    let botId = params.get('bot_id');
    
    // If not in URL, try to get from initData via API
    if (!botId && tg?.initData) {
        try {
            const initData = tg.initData;
            const response = await fetch(`${API_BASE}/api/v1/mini-apps/mini-app/bot-id?init_data=${encodeURIComponent(initData)}`);
            if (response.ok) {
                const data = await response.json();
                botId = data.bot_id;
                console.log('Got bot_id from initData:', botId);
            }
        } catch (error) {
            console.error('Error getting bot_id from initData:', error);
        }
    }
    
    return botId;
}

/**
 * Apply theme from Telegram and bot.config
 */
function applyTheme() {
    if (!tg) return;
    
    const colorScheme = tg.colorScheme; // 'light' or 'dark'
    const themeColor = tg.themeParams?.bg_color || '#ffffff';
    
    // Apply theme to body
    document.body.setAttribute('data-theme', colorScheme);
    document.documentElement.style.setProperty('--tg-theme-bg-color', themeColor);
    
    // Apply other Telegram theme colors
    if (tg.themeParams) {
        const params = tg.themeParams;
        if (params.text_color) {
            document.documentElement.style.setProperty('--tg-theme-text-color', params.text_color);
        }
        if (params.hint_color) {
            document.documentElement.style.setProperty('--tg-theme-hint-color', params.hint_color);
        }
        if (params.link_color) {
            document.documentElement.style.setProperty('--tg-theme-link-color', params.link_color);
        }
        if (params.button_color) {
            document.documentElement.style.setProperty('--tg-theme-button-color', params.button_color);
        }
        if (params.button_text_color) {
            document.documentElement.style.setProperty('--tg-theme-button-text-color', params.button_text_color);
        }
    }
    
    // Apply bot.config customizations (after app data is loaded)
    if (appData && appData.config) {
        applyBotConfig(appData.config);
    }
}

/**
 * Apply bot.config customizations
 */
function applyBotConfig(config) {
    // Apply custom colors from bot.config.ui.colors
    if (config.ui && config.ui.colors) {
        const colors = config.ui.colors;
        if (colors.primary) {
            document.documentElement.style.setProperty('--primary-color', colors.primary);
            document.documentElement.style.setProperty('--tg-theme-button-color', colors.primary);
        }
        if (colors.secondary) {
            document.documentElement.style.setProperty('--secondary-color', colors.secondary);
        }
        if (colors.success) {
            document.documentElement.style.setProperty('--success-color', colors.success);
        }
        if (colors.error) {
            document.documentElement.style.setProperty('--error-color', colors.error);
        }
    }
    
    // Apply custom theme from bot.config.ui.theme
    if (config.ui && config.ui.theme) {
        const theme = config.ui.theme;
        if (theme === 'dark' || theme === 'light') {
            document.body.setAttribute('data-theme', theme);
        }
    }
    
    // Show/hide features based on bot.config.ui.features
    if (config.ui && config.ui.features) {
        const features = config.ui.features;
        
        // Hide tabs if features are disabled
        if (features.partners === false) {
            const partnersTab = document.querySelector('[data-tab="partners"]');
            if (partnersTab) partnersTab.style.display = 'none';
        }
        if (features.top === false) {
            const topTab = document.querySelector('[data-tab="top"]');
            if (topTab) topTab.style.display = 'none';
        }
        if (features.earnings === false) {
            const earningsTab = document.querySelector('[data-tab="earnings"]');
            if (earningsTab) earningsTab.style.display = 'none';
        }
        if (features.wallet === false) {
            const walletTab = document.querySelector('[data-tab="wallet"]');
            if (walletTab) walletTab.style.display = 'none';
        }
    }
    
    // Update bot name from config
    const botNameEl = document.getElementById('bot-name');
    if (botNameEl && config.name) {
        botNameEl.textContent = config.name;
    }
}

/**
 * Setup event handlers
 */
function setupEventHandlers() {
    // Close button
    const closeBtn = document.getElementById('close-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            if (tg) {
                tg.close();
            }
        });
    }
    
    // Tab navigation
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
    
    // Back button (if needed)
    if (tg?.BackButton) {
        tg.BackButton.onClick(() => {
            // Handle back button
            const activeTab = document.querySelector('.tab.active');
            if (activeTab) {
                // Go to first tab or close
                switchTab('partners');
            }
        });
    }
    
    // Swipe gestures for mobile navigation
    setupSwipeGestures();
    
    // Pull-to-refresh
    setupPullToRefresh();
    
    // Ripple effects for buttons
    setupRippleEffects();
}

/**
 * Setup swipe gestures for tab navigation (mobile)
 */
function setupSwipeGestures() {
    let touchStartX = 0;
    let touchEndX = 0;
    const content = document.querySelector('.content');
    
    if (!content) return;
    
    content.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
    
    content.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });
    
    function handleSwipe() {
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;
        
        if (Math.abs(diff) < swipeThreshold) return;
        
        const tabs = ['partners', 'top', 'earnings', 'wallet'];
        const currentTab = document.querySelector('.tab.active')?.getAttribute('data-tab');
        const currentIndex = tabs.indexOf(currentTab);
        
        if (diff > 0 && currentIndex < tabs.length - 1) {
            // Swipe left - next tab
            switchTab(tabs[currentIndex + 1]);
        } else if (diff < 0 && currentIndex > 0) {
            // Swipe right - previous tab
            switchTab(tabs[currentIndex - 1]);
        }
    }
}

// Navigation state
let currentPage = 'partners';
let navigationHistory = [];

/**
 * Switch between tabs/pages
 */
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.getAttribute('data-tab') === tabName) {
            tab.classList.add('active');
        }
    });
    
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show target page
    const targetPage = document.getElementById(`${tabName}-page`);
    if (targetPage) {
        targetPage.classList.add('active');
        currentPage = tabName;
        
        // Load content if not loaded yet
        if (tabName === 'partners') {
            renderPartners();
            setupSearchAndFilters();
        } else if (tabName === 'top') {
            renderTop();
        } else if (tabName === 'earnings') {
            renderEarnings();
        } else if (tabName === 'wallet') {
            renderWallet();
        } else if (tabName === 'info') {
            renderInfo();
        }
    }
}

/**
 * Navigate to partner detail page
 */
function showPartnerDetail(partnerId) {
    if (!partnerId) {
        console.error('Partner ID is required');
        return;
    }
    
    navigationHistory.push(currentPage);
    
    // Hide current page
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show detail page
    const detailPage = document.getElementById('partner-detail-page');
    if (detailPage) {
        detailPage.classList.add('active');
        currentPage = 'partner-detail';
        renderPartnerDetail(String(partnerId));
    }
}

/**
 * Go back in navigation
 */
function goBack() {
    if (navigationHistory.length > 0) {
        const previousPage = navigationHistory.pop();
        switchTab(previousPage);
    } else {
        switchTab('partners');
    }
}

/**
 * Load app data from backend
 */
async function loadAppData(showRefreshIndicator = false) {
    try {
        if (!showRefreshIndicator) {
            showLoading(true);
        }
        
        // Get initData for validation
        const initData = tg?.initData || null;
        
        // Validate we have botId before making request
        if (!botId) {
            throw new Error('Bot ID is required');
        }
        
        // Fetch data (userId can be null if initData is provided)
        const data = await getMiniAppData(botId, userId, initData);
        
        // Check if data is valid
        if (!data) {
            throw new Error('No data received from server');
        }
        
        // API returns {ok: true, ...} or throws error
        if (data.ok === true || data.ok === undefined) {
            // If ok is undefined, assume success (backward compatibility)
            appData = data;
            
            // Show welcome screen on first visit (check localStorage)
            const hasSeenWelcome = localStorage.getItem('mini_app_welcome_seen');
            if (!hasSeenWelcome && appData.welcome?.message) {
                showWelcomeScreen();
            } else {
                renderApp();
                showLoading(false);
            }
            
            if (showRefreshIndicator) {
                hidePullToRefresh();
            }
        } else {
            throw new Error(data.detail || 'Failed to load data');
        }
    } catch (error) {
        console.error('Error loading app data:', error);
        showError('Помилка завантаження даних: ' + error.message);
        showLoading(false);
        if (showRefreshIndicator) {
            hidePullToRefresh();
        }
    }
}

/**
 * Render main app content
 */
function renderApp() {
    if (!appData) return;
    
    // Apply bot.config customizations
    if (appData.config) {
        applyBotConfig(appData.config);
    }
    
    // Update bot name
    const botNameEl = document.getElementById('bot-name');
    if (botNameEl) {
        botNameEl.textContent = appData.config?.name || 'Mini App';
    }
    
    // Render initial tab (partners)
    switchTab('partners');
}

// Filtered partners cache
let filteredPartners = [];
let currentSort = 'name';
let currentFilter = 'all';

/**
 * Setup search and filters
 */
function setupSearchAndFilters() {
    // Search input
    const searchInput = document.getElementById('partner-search');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                filterPartners(e.target.value);
            }, 300); // Debounce
        });
    }
    
    // Filter button
    const filterBtn = document.getElementById('filter-btn');
    const filterPanel = document.getElementById('filter-panel');
    if (filterBtn && filterPanel) {
        filterBtn.addEventListener('click', () => {
            filterPanel.style.display = filterPanel.style.display === 'none' ? 'block' : 'none';
        });
    }
    
    // Sort select
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            currentSort = e.target.value;
            applyFilters();
        });
    }
    
    // Filter chips
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', (e) => {
            document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            e.target.classList.add('active');
            currentFilter = e.target.getAttribute('data-filter');
            applyFilters();
        });
    });
}

/**
 * Filter partners by search query
 */
function filterPartners(query) {
    if (!appData) return;
    
    const partners = appData.partners || [];
    const searchQuery = query.toLowerCase().trim();
    
    if (searchQuery === '') {
        filteredPartners = [...partners];
    } else {
        filteredPartners = partners.filter(partner => {
            const name = (partner.name || '').toLowerCase();
            const description = (partner.description || '').toLowerCase();
            return name.includes(searchQuery) || description.includes(searchQuery);
        });
    }
    
    applyFilters();
}

/**
 * Apply filters and sorting
 */
function applyFilters() {
    let partners = filteredPartners.length > 0 ? filteredPartners : (appData.partners || []);
    
    // Apply category filter
    if (currentFilter !== 'all') {
        // TODO: Add category filtering when backend supports it
        // For now, filter by TOP status
        if (currentFilter === 'top') {
            const topPartnerIds = (appData.top_partners || []).map(p => p.id);
            partners = partners.filter(p => topPartnerIds.includes(p.id));
        }
    }
    
    // Apply sorting
    partners.sort((a, b) => {
        switch (currentSort) {
            case 'commission':
                return (b.commission || 0) - (a.commission || 0);
            case 'name':
                return (a.name || '').localeCompare(b.name || '');
            case 'new':
                // TODO: Add date field when backend supports it
                return 0;
            default:
                return 0;
        }
    });
    
    renderPartnersList(partners);
}

/**
 * Render partners list
 */
function renderPartners() {
    if (!appData) return;
    
    filteredPartners = [];
    const partners = appData.partners || [];
    
    if (partners.length === 0) {
        const container = document.getElementById('partners-list');
        if (container) {
            container.innerHTML = '<p class="empty-state">Партнерів поки немає</p>';
        }
        return;
    }
    
    applyFilters();
}

/**
 * Render partners list (internal)
 */
function renderPartnersList(partners) {
    const container = document.getElementById('partners-list');
    if (!container) return;
    
    if (partners.length === 0) {
        container.innerHTML = '<p class="empty-state">Партнерів не знайдено</p>';
        return;
    }
    
    container.innerHTML = partners.map((partner, index) => {
        const partnerId = partner.id || `temp-${index}`;
        const partnerIdStr = typeof partnerId === 'string' ? partnerId : String(partnerId);
        const isTop = (appData.top_partners || []).some(p => String(p.id) === String(partner.id));
        const referralLink = partner.referral_link || '';
        
        return `
            <div class="partner-card ${isTop ? 'top-partner' : ''}" 
                 data-partner-id="${escapeHtml(partnerIdStr)}"
                 onclick="showPartnerDetail('${escapeHtml(partnerIdStr)}')">
                <div class="partner-header">
                    <h3 class="partner-name">${escapeHtml(partner.name || 'Unknown')}</h3>
                    <span class="commission-badge ${isTop ? 'top-badge' : ''}">${partner.commission || 0}%</span>
                </div>
                <p class="partner-description">${escapeHtml((partner.description || '').substring(0, 100))}${partner.description && partner.description.length > 100 ? '...' : ''}</p>
                <button class="partner-btn" onclick="event.stopPropagation(); openPartner('${escapeHtml(referralLink)}', '${escapeHtml(partnerIdStr)}')">
                    Перейти →
                </button>
            </div>
        `;
    }).join('');
}

/**
 * Render partner detail page
 */
function renderPartnerDetail(partnerId) {
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
        const isTop = (appData.top_partners || []).some(p => p.id === partner.id);
        
        content.innerHTML = `
            <div class="partner-detail-card">
                <div class="partner-detail-header">
                    <h2>${escapeHtml(partner.name || 'Unknown')}</h2>
                    <span class="commission-badge large ${isTop ? 'top-badge' : ''}">${partner.commission || 0}% комісія</span>
                </div>
                <div class="partner-detail-body">
                    <p class="partner-detail-description">${escapeHtml(partner.description || 'Опис відсутній')}</p>
                    <div class="partner-detail-actions">
                        <button class="partner-btn large" onclick="openPartner('${partner.referral_link || ''}', ${partnerId})">
                            🚀 Перейти до партнера
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
}

/**
 * Render TOP partners
 */
function renderTop() {
    const container = document.getElementById('top-content');
    if (!container || !appData) return;
    
    const topStatus = appData.user?.top_status || 'locked';
    const topPartners = appData.top_partners || [];
    const wasLocked = container.querySelector('.locked-state') !== null;
    
    if (topStatus === 'locked') {
        container.innerHTML = `
            <div class="locked-state">
                <div class="locked-icon">🔒</div>
                <h2>TOP закрито</h2>
                <p>Запроси ${appData.earnings?.invites_needed || 0} друзів щоб розблокувати TOP</p>
                <p>Або купи доступ за ${appData.earnings?.buy_top_price || 1} ⭐</p>
            </div>
        `;
    } else {
        // Check if was just unlocked
        if (wasLocked) {
            container.classList.add('unlocked');
            setTimeout(() => {
                container.classList.remove('unlocked');
            }, 1000);
        }
        
        if (topPartners.length === 0) {
            container.innerHTML = '<p class="empty-state">TOP партнерів поки немає</p>';
        } else {
            container.innerHTML = topPartners.map((partner, index) => {
                const partnerId = partner.id || `temp-top-${index}`;
                const partnerIdStr = typeof partnerId === 'string' ? partnerId : String(partnerId);
                const referralLink = partner.referral_link || '';
                
                return `
                <div class="partner-card top-partner" data-partner-id="${escapeHtml(partnerIdStr)}">
                    <div class="partner-header">
                        <h3 class="partner-name">${escapeHtml(partner.name || 'Unknown')}</h3>
                        <span class="commission-badge top-badge">${partner.commission || 0}%</span>
                    </div>
                    <p class="partner-description">${escapeHtml(partner.description || '')}</p>
                    <button class="partner-btn" onclick="openPartner('${escapeHtml(referralLink)}', '${escapeHtml(partnerIdStr)}')">
                        Перейти →
                    </button>
                </div>
            `;
            }).join('');
        }
    }
}

/**
 * Render earnings dashboard
 */
function renderEarnings() {
    const container = document.getElementById('earnings-dashboard');
    if (!container || !appData) return;
    
    const earnings = appData.earnings || {};
    const user = appData.user || {};
    const translations = earnings.translations || {};
    const commissionPercent = Math.round((earnings.commission_rate || 0.07) * 100);
    
    container.innerHTML = `
        <div class="earnings-card">
            <h2>💰 ${translations.block3_title || 'Заробітки'}</h2>
            
            <!-- Balance -->
            <div class="balance-display">
                <span class="balance-label">Зароблено:</span>
                <span class="balance-amount">${earnings.earned || 0} TON</span>
            </div>
            
            <!-- Progress Section -->
            <div class="progress-section">
                ${(() => {
                    const totalInvited = user.total_invited || 0;
                    const requiredInvites = earnings.required_invites || 5;
                    const progress = requiredInvites > 0 ? Math.min((totalInvited / requiredInvites) * 100, 100) : 0;
                    return `
                    <p class="progress-label">Інвайтів: ${totalInvited} / ${requiredInvites}</p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    ${earnings.can_unlock_top ? '<p class="progress-hint">✅ Можна розблокувати TOP!</p>' : `<p class="progress-hint">Потрібно ще ${earnings.invites_needed || 0} інвайтів</p>`}
                    `;
                })()}
            </div>
            
            <!-- Referral Link -->
            ${user.referral_link ? `
            <div class="referral-section">
                <p class="section-label">Реферальна лінка:</p>
                <div class="referral-link-box">
                    <code>${user.referral_link}</code>
                    <div class="referral-actions">
                        <button class="copy-btn" onclick="copyReferralLink()">📋 Копіювати</button>
                        <button class="share-btn" onclick="shareReferralLink()">📤 Поділитися</button>
                    </div>
                </div>
            </div>
            ` : `
            <div class="referral-section">
                <p class="section-label">Реферальна лінка:</p>
                <p class="empty-state">Реферальна лінка генерується...</p>
            </div>
            `}
            
            <!-- 7% Program Block -->
            <div class="commission-section">
                <h3 class="section-title">${translations.block2_title || `${commissionPercent}% Програма`}</h3>
                <div class="commission-info">
                    <p>${translations.block2_how_it_works || `Отримуй ${commissionPercent}% комісії з кожного заробітку твоїх рефералів`}</p>
                    <p class="commission-examples">${translations.block2_examples || 'Приклад: якщо реферал заробив 100 TON, ти отримаєш 7 TON'}</p>
                </div>
                <div class="commission-activate">
                    <h4>${translations.block2_enable_title || 'Як активувати:'}</h4>
                    <p>${translations.block2_enable_steps || '1. Запроси друзів\n2. Вони повинні заробити\n3. Ти отримаєш комісію автоматично'}</p>
                </div>
            </div>
            
            <!-- Action Steps -->
            <div class="action-steps">
                <h3 class="section-title">${translations.block3_title || 'Що робити далі:'}</h3>
                <ol class="steps-list">
                    <li>${translations.step1 || 'Запроси друзів'}</li>
                    <li>${translations.step2 || 'Вони реєструються'}</li>
                    <li>${translations.step3 || 'Вони заробляють'}</li>
                    <li>${translations.step4 || 'Ти отримуєш комісію'}</li>
                </ol>
                <p class="auto-stats">${translations.auto_stats || 'Статистика оновлюється автоматично'}</p>
            </div>
            
            <!-- Action Buttons -->
            <div class="earnings-actions">
                ${earnings.can_unlock_top ? `
                    <button class="action-btn unlock-btn" onclick="switchTab('top')">
                        🔓 ${translations.btn_top_partners || 'Відкрити TOP'}
                    </button>
                ` : `
                    <button class="action-btn unlock-btn" onclick="handleBuyTop(${earnings.buy_top_price || 1})">
                        🔒 ${translations.btn_unlock_top || `Розблокувати TOP (${earnings.buy_top_price || 1} ⭐)`}
                    </button>
                `}
                <button class="action-btn activate-btn" onclick="showActivate7Instructions()">
                    ⚡ ${translations.btn_activate_7 || 'Активувати 7%'}
                </button>
            </div>
        </div>
    `;
}

/**
 * Render wallet section
 */
function renderWallet() {
    const container = document.getElementById('wallet-section');
    if (!container || !appData) return;
    
    const wallet = appData.user?.wallet || '';
    
    container.innerHTML = `
        <div class="wallet-card">
            <h2>👛 TON Гаманець</h2>
            ${wallet ? `
                <div class="current-wallet">
                    <p>Поточний гаманець:</p>
                    <code class="wallet-address">${wallet}</code>
                </div>
            ` : ''}
            <form id="wallet-form" onsubmit="handleWalletSubmit(event)">
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

/**
 * Open partner link
 */
function openPartner(referralLink, partnerId) {
    if (!referralLink || !referralLink.trim()) {
        console.warn('Referral link is empty');
        if (tg?.showAlert) {
            tg.showAlert('Реферальна лінка відсутня');
        }
        return;
    }
    
    // Log partner click
    if (botId) {
        const initData = tg?.initData || null;
        sendCallback(botId, {
            action: 'partner_click',
            partner_id: partnerId || null
        }, initData).catch(err => console.error('Error logging partner click:', err));
    }
    
    // Open link
    if (tg?.openLink) {
        tg.openLink(referralLink);
    } else {
        window.open(referralLink, '_blank');
    }
}

/**
 * Handle wallet form submit
 */
async function handleWalletSubmit(event) {
    event.preventDefault();
    
    const input = document.getElementById('wallet-input');
    const walletAddress = input.value.trim();
    const messageEl = document.getElementById('wallet-message');
    
    if (!walletAddress) {
        showWalletMessage('Введіть адресу гаманця', 'error');
        return;
    }
    
    // Validate format
    const walletPattern = /^(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_-]{46,48}$/;
    if (!walletPattern.test(walletAddress)) {
        showWalletMessage('Невірний формат адреси гаманця', 'error');
        return;
    }
    
    // Validate botId before making request
    if (!botId) {
        showWalletMessage('Помилка: Bot ID не знайдено', 'error');
        return;
    }
    
    try {
        showWalletMessage('Збереження...', 'info');
        
        const initData = tg?.initData || null;
        const result = await saveWallet(botId, walletAddress, userId, initData);
        
        if (result && result.ok !== false) {
            showWalletMessage('✅ Гаманець збережено успішно!', 'success');
            // Update app data
            if (appData && appData.user) {
                appData.user.wallet = walletAddress;
            }
            // Clear input after successful save
            if (input) {
                input.value = walletAddress;
            }
        } else {
            throw new Error(result?.detail || 'Failed to save wallet');
        }
    } catch (error) {
        console.error('Error saving wallet:', error);
        const errorMsg = error.message || 'Невідома помилка';
        showWalletMessage('❌ Помилка збереження: ' + errorMsg, 'error');
    }
}

/**
 * Show wallet message
 */
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

/**
 * Show welcome screen
 */
function showWelcomeScreen() {
    const welcomeScreen = document.getElementById('welcome-screen');
    const welcomeMessage = document.getElementById('welcome-message');
    const welcomeCloseBtn = document.getElementById('welcome-close-btn');
    
    if (!welcomeScreen || !appData) return;
    
    // Parse welcome message (HTML from translations)
    const welcomeText = appData.welcome?.message || 'Ласкаво просимо до Mini App!';
    
    if (welcomeMessage) {
        welcomeMessage.innerHTML = welcomeText;
    }
    
    welcomeScreen.style.display = 'flex';
    
    // Close welcome screen
    if (welcomeCloseBtn) {
        welcomeCloseBtn.onclick = () => {
            welcomeScreen.style.display = 'none';
            localStorage.setItem('mini_app_welcome_seen', 'true');
            renderApp();
            showLoading(false);
        };
    }
}

/**
 * Render Info page
 */
function renderInfo() {
    const container = document.getElementById('info-section');
    if (!container || !appData) return;
    
    const infoMessage = appData.info?.message || '';
    
    // Parse HTML from info message (it comes as HTML from translations)
    container.innerHTML = `
        <div class="info-card">
            <div class="info-content">
                ${infoMessage || '<p>Інформація про бота</p>'}
            </div>
        </div>
    `;
}

/**
 * Copy referral link
 */
function copyReferralLink() {
    if (!appData || !appData.user || !appData.user.referral_link) {
        if (tg?.showAlert) {
            tg.showAlert('Реферальна лінка відсутня');
        }
        return;
    }
    
    const link = appData.user.referral_link;
    
    // Try modern clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(link).then(() => {
            showCopySuccess();
        }).catch(err => {
            console.error('Error copying link:', err);
            // Fallback to old method
            fallbackCopyText(link);
        });
    } else {
        // Fallback for older browsers
        fallbackCopyText(link);
    }
}

/**
 * Share referral link via Telegram
 */
function shareReferralLink() {
    if (!appData || !appData.user || !appData.user.referral_link) {
        if (tg?.showAlert) {
            tg.showAlert('Реферальна лінка відсутня');
        }
        return;
    }
    
    const link = appData.user.referral_link;
    const shareText = '🚀 Долучайся до HubAggregatorBot — отримуй зірки за активність!\nОсь твоє реферальне посилання:';
    
    // Use Telegram share URL
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(shareText)}`;
    
    // Try Telegram WebApp API first
    if (tg?.openTelegramLink) {
        tg.openTelegramLink(shareUrl);
    } else if (tg?.openLink) {
        tg.openLink(shareUrl);
    } else {
        // Fallback: open in new window
        window.open(shareUrl, '_blank');
    }
}

/**
 * Fallback copy method for older browsers
 */
function fallbackCopyText(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showCopySuccess();
    } catch (err) {
        console.error('Fallback copy failed:', err);
        if (tg?.showAlert) {
            tg.showAlert('Не вдалося скопіювати лінк');
        }
    }
    
    document.body.removeChild(textArea);
}

/**
 * Show copy success message
 */
function showCopySuccess() {
    if (tg?.showAlert) {
        tg.showAlert('✅ Лінк скопійовано!');
    } else if (tg?.HapticFeedback?.impactOccurred) {
        // Haptic feedback if available
        tg.HapticFeedback.impactOccurred('light');
    }
    
    // Visual feedback on button
    const copyBtn = document.querySelector('.copy-btn');
    if (copyBtn) {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = '✅ Скопійовано!';
        copyBtn.style.background = 'var(--success-color)';
        setTimeout(() => {
            copyBtn.textContent = originalText;
            copyBtn.style.background = '';
        }, 2000);
    }
}

/**
 * Show loading screen
 */
function showLoading(show) {
    const loading = document.getElementById('loading');
    const app = document.getElementById('app');
    
    if (loading) loading.style.display = show ? 'flex' : 'none';
    if (app) app.style.display = show ? 'none' : 'block';
}

/**
 * Show error message
 */
function showError(message) {
    const errorEl = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    
    if (errorEl && errorText) {
        errorText.textContent = message;
        errorEl.style.display = 'block';
    }
    
    // Retry button
    const retryBtn = document.getElementById('retry-btn');
    if (retryBtn) {
        retryBtn.onclick = () => {
            errorEl.style.display = 'none';
            loadAppData();
        };
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Setup pull-to-refresh functionality
 */
function setupPullToRefresh() {
    const content = document.querySelector('.content');
    if (!content) return;
    
    let touchStartY = 0;
    let touchCurrentY = 0;
    let isPulling = false;
    let pullDistance = 0;
    const pullThreshold = 80;
    
    content.addEventListener('touchstart', (e) => {
        // Only trigger if at top of scroll
        if (content.scrollTop === 0) {
            touchStartY = e.touches[0].clientY;
            isPulling = true;
        }
    }, { passive: true });
    
    content.addEventListener('touchmove', (e) => {
        if (!isPulling) return;
        
        touchCurrentY = e.touches[0].clientY;
        pullDistance = touchCurrentY - touchStartY;
        
        if (pullDistance > 0 && content.scrollTop === 0) {
            e.preventDefault();
            updatePullToRefresh(pullDistance);
        }
    }, { passive: false });
    
    content.addEventListener('touchend', () => {
        if (!isPulling) return;
        
        if (pullDistance >= pullThreshold) {
            // Trigger refresh
            showPullToRefresh();
            loadAppData(true);
        } else {
            hidePullToRefresh();
        }
        
        isPulling = false;
        pullDistance = 0;
    }, { passive: true });
}

/**
 * Update pull-to-refresh indicator
 */
function updatePullToRefresh(distance) {
    const indicator = document.getElementById('pull-to-refresh');
    if (!indicator) return;
    
    const threshold = 80;
    const progress = Math.min(distance / threshold, 1);
    
    indicator.style.opacity = progress;
    indicator.style.transform = `translateX(-50%) translateY(${Math.min(distance, threshold) - 100}px)`;
    
    if (distance >= threshold) {
        indicator.classList.add('ready');
    } else {
        indicator.classList.remove('ready');
    }
}

/**
 * Show pull-to-refresh indicator
 */
function showPullToRefresh() {
    const indicator = document.getElementById('pull-to-refresh');
    if (indicator) {
        indicator.classList.add('active');
        indicator.querySelector('.pull-to-refresh-icon').textContent = '🔄';
        indicator.querySelector('.pull-to-refresh-text').textContent = 'Оновлення...';
    }
}

/**
 * Hide pull-to-refresh indicator
 */
function hidePullToRefresh() {
    const indicator = document.getElementById('pull-to-refresh');
    if (indicator) {
        indicator.classList.remove('active', 'ready');
        indicator.style.opacity = '0';
        indicator.style.transform = 'translateX(-50%) translateY(-100%)';
        indicator.querySelector('.pull-to-refresh-icon').textContent = '⬇️';
        indicator.querySelector('.pull-to-refresh-text').textContent = 'Потягніть для оновлення';
    }
}

/**
 * Setup ripple effects for buttons
 */
function setupRippleEffects() {
    // Add ripple to all buttons
    document.addEventListener('click', (e) => {
        const button = e.target.closest('button, .partner-btn, .partner-card, .tab');
        if (!button) return;
        
        // Skip if already has ripple
        if (button.querySelector('.ripple')) return;
        
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');
        
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        
        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        button.appendChild(ripple);
        
        // Remove ripple after animation
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
}

/**
 * Show activate 7% instructions
 */
function showActivate7Instructions() {
    if (!appData || !appData.earnings) return;
    
    const earnings = appData.earnings || {};
    const translations = earnings.translations || {};
    const commissionPercent = Math.round((earnings.commission_rate || 0.07) * 100);
    
    // Get instructions from translations or use default
    const instructions = translations.block2_enable_steps || 
        `1️⃣ Відкрий @HubAggregatorBot
2️⃣ «Партнерська програма»
3️⃣ «Під'єднатись»
→ ${commissionPercent}% активуються назавжди`;
    
    // Show modal with instructions
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>${translations.block2_enable_title || `Як увімкнути ${commissionPercent}% (1 раз назавжди):`}</h2>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
            </div>
            <div class="modal-body">
                <div class="instructions-text">
                    ${instructions.split('\n').map(line => `<p>${line}</p>`).join('')}
                </div>
                <div class="modal-actions">
                    <button class="action-btn primary" onclick="openTelegramBot()">
                        Відкрити бота
                    </button>
                    <button class="action-btn secondary" onclick="this.closest('.modal-overlay').remove()">
                        Закрити
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close on overlay click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

/**
 * Open Telegram bot
 */
function openTelegramBot() {
    // Get bot username from config or use default
    const botName = appData?.config?.name || 'EarnHubAggregatorBot';
    // Remove @ if present and extract username if it's a full URL
    let cleanBotName = botName.replace('@', '').trim();
    // If it's a full URL, extract username
    if (cleanBotName.includes('t.me/')) {
        cleanBotName = cleanBotName.split('t.me/')[1].split('/')[0];
    }
    const botUrl = `https://t.me/${cleanBotName}`;
    
    if (tg && tg.openTelegramLink) {
        tg.openTelegramLink(botUrl);
    } else if (tg && tg.openLink) {
        tg.openLink(botUrl);
    } else {
        // Fallback: open in new window
        window.open(botUrl, '_blank');
    }
}

/**
 * Handle buy TOP - open bot to purchase
 */
function handleBuyTop(price) {
    if (!appData || !botId) return;
    
    // Show confirmation modal
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>Розблокувати TOP</h2>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
            </div>
            <div class="modal-body">
                <div class="instructions-text">
                    <p>Для розблокування TOP потрібно:</p>
                    <p>• Запросити ${appData.earnings?.invites_needed || 0} друзів</p>
                    <p>• Або купити доступ за ${price} ⭐</p>
                    <p>Для покупки відкрийте бота та натисніть кнопку "Розблокувати TOP"</p>
                </div>
                <div class="modal-actions">
                    <button class="action-btn primary" onclick="openTelegramBot(); this.closest('.modal-overlay').remove();">
                        Відкрити бота
                    </button>
                    <button class="action-btn secondary" onclick="this.closest('.modal-overlay').remove()">
                        Закрити
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close on overlay click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// Initialize when DOM is ready
(async () => {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => initMiniApp());
    } else {
        await initMiniApp();
    }
})();

