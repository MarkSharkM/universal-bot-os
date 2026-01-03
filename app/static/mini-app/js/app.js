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
    // Normalize config shape for backward compatibility:
    // - New backend: config.ui.{theme,colors,features,force_dark}
    // - Old backend: config.{theme,colors,features,name}
    if (config && !config.ui) {
        config.ui = {
            theme: config.theme,
            colors: config.colors,
            features: config.features,
            force_dark: config.force_dark,
        };
    }

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

    // Optional: force Hub-like dark UI regardless of Telegram theme
    // Usage in bot.config:
    // {
    //   "ui": { "force_dark": true, "theme": "dark" }
    // }
    const forceDark = Boolean(config?.ui?.force_dark);
    if (forceDark) {
        document.body.setAttribute('data-theme', 'dark');
        // Force Hub-like palette so it matches the HubAggregator look, not Telegram default dark.
        document.documentElement.style.setProperty('--tg-theme-bg-color', '#0b1220');
        document.documentElement.style.setProperty('--tg-theme-text-color', '#eaf1ff');
        document.documentElement.style.setProperty('--tg-theme-hint-color', '#8a94a7');
        document.documentElement.style.setProperty('--tg-theme-link-color', '#2f80ed');
        document.documentElement.style.setProperty('--tg-theme-button-color', config?.ui?.colors?.primary || '#2f80ed');
        document.documentElement.style.setProperty('--tg-theme-button-text-color', '#ffffff');
        document.documentElement.style.setProperty('--primary-color', config?.ui?.colors?.primary || '#2f80ed');
        document.documentElement.style.setProperty('--secondary-color', config?.ui?.colors?.secondary || '#6c5ce7');
    }
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    document.body.classList.toggle('hub-dark', isDark || forceDark);
    
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
let isInitialLoad = true; // Track if this is the first load
let isLoadingData = false; // Track if data is currently loading (prevent concurrent requests)
let loadDataTimeout = null; // Debounce timer for loadAppData calls

/**
 * Switch between tabs/pages
 */
function switchTab(tabName) {
    // If user manually switches tabs, mark that initial load is done
    // This prevents loadAppData from auto-switching to earnings
    if (isInitialLoad) {
        isInitialLoad = false;
    }
    
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        const isActive = tab.getAttribute('data-tab') === tabName;
        tab.classList.toggle('active', isActive);
        // Update aria-current for accessibility
        if (isActive) {
            tab.setAttribute('aria-current', 'page');
        } else {
            tab.removeAttribute('aria-current');
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
        
        // Render content immediately with existing data (if available)
        // This ensures user sees content right away, not a blank screen
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
        
        // Reload data when switching to tabs that need fresh data
        // This ensures counters and stats are up-to-date
        // BUT: Don't reload on initial load (isInitialLoad = true) to prevent infinite loop
        // AND: Only reload if we have existing data (to avoid double load on first visit)
        if ((tabName === 'earnings' || tabName === 'top') && appData && !isInitialLoad) {
            // Reload app data to get fresh counters (only if appData already exists and not initial load)
            // Use debounced version to prevent multiple rapid calls
            // Note: loadAppData will update the current tab, not switch to earnings
            loadAppData(false).catch(err => {
                console.error('Error reloading data:', err);
                // Data already rendered above, so user sees content even if reload fails
            });
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
    // Prevent concurrent requests
    if (isLoadingData && !showRefreshIndicator) {
        console.log('Data already loading, skipping duplicate request');
        return Promise.resolve(); // Return resolved promise to prevent errors
    }
    
    // Debounce: cancel previous pending request if not a refresh
    if (!showRefreshIndicator && loadDataTimeout) {
        clearTimeout(loadDataTimeout);
        loadDataTimeout = null;
    }
    
    // If not a refresh, debounce the request by 100ms to batch rapid calls
    if (!showRefreshIndicator && !isLoadingData) {
        return new Promise((resolve, reject) => {
            loadDataTimeout = setTimeout(async () => {
                try {
                    await loadAppDataInternal(showRefreshIndicator);
                    resolve();
                } catch (error) {
                    reject(error);
                }
            }, 100);
        });
    }
    
    // For refresh or if already loading, call directly
    return loadAppDataInternal(showRefreshIndicator);
}

/**
 * Internal function to actually load data (called after debounce)
 */
async function loadAppDataInternal(showRefreshIndicator = false) {
    try {
        isLoadingData = true;
        
        // Don't show loading screen if we're just refreshing data (not initial load)
        // Only show loading on first load or when explicitly requested via showRefreshIndicator
        if (!showRefreshIndicator && isInitialLoad) {
            showLoading(true);
        }
        // showRefreshIndicator is handled by pull-to-refresh UI
        
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
            if (!hasSeenWelcome) {
                showWelcomeScreen();
            } else {
                // Only switch to Earnings tab on initial load (when app is first shown)
                // Don't switch if this is just a data refresh (showRefreshIndicator or not isInitialLoad)
                const isFirstLoad = isInitialLoad && !showRefreshIndicator;
                
                if (isFirstLoad) {
                    // Show Earnings tab first (it has instructions on what to do)
                    // This helps users understand what the bot does
                    isInitialLoad = true; // Mark as initial load to prevent reload loop
                    renderApp();
                    
                    // Only auto-switch to earnings if isInitialLoad is still true
                    // (user hasn't manually switched tabs yet)
                    // Check again right before switching to handle race conditions
                    if (isInitialLoad) {
                        // Switch to Earnings tab first (instead of Partners)
                        // Note: switchTab will set isInitialLoad = false when called
                        switchTab('earnings');
                    }
                    // If isInitialLoad is false, user already switched tabs manually, don't force switch
                } else {
                    // This is a data refresh, not initial load
                    // Just update the data and re-render current tab
                    renderApp();
                    // Re-render current page with fresh data
                    if (currentPage === 'earnings') {
                        renderEarnings();
                    } else if (currentPage === 'top') {
                        renderTop();
                    } else if (currentPage === 'partners') {
                        renderPartners();
                        setupSearchAndFilters();
                    } else if (currentPage === 'wallet') {
                        renderWallet();
                    } else if (currentPage === 'info') {
                        renderInfo();
                    }
                }
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
    } finally {
        isLoadingData = false; // Always reset loading flag
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
    
    // Render initial tab (earnings - has instructions on what to do)
    // This helps users understand what the bot does
    // Note: switchTab is called from loadAppData, not here, to avoid double call
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
                <button class="partner-btn" onclick="event.stopPropagation(); openPartner('${escapeHtml(referralLink)}', '${escapeHtml(partnerIdStr)}')" aria-label="Перейти до партнера ${escapeHtml(partner.name || 'Unknown')}">
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
                        <button class="partner-btn large" onclick="openPartner('${escapeHtml(partner.referral_link || '')}', '${escapeHtml(String(partnerId))}')" aria-label="Перейти до партнера ${escapeHtml(partner.name || 'Unknown')}">
                            Перейти до партнера
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
    if (!container) {
        console.warn('TOP container not found');
        return;
    }
    
    if (!appData) {
        console.warn('appData not loaded yet, showing loading state');
        container.innerHTML = '<div class="loading-state"><p>Завантаження даних...</p></div>';
        return;
    }
    
    const topStatus = appData.user?.top_status || 'locked';
    const topPartners = appData.top_partners || [];
    const wasLocked = container.querySelector('.locked-state') !== null;
    
    if (topStatus === 'locked') {
        const invitesNeeded = appData.earnings?.invites_needed || 0;
        const buyTopPrice = appData.earnings?.buy_top_price || 1;
        const canUnlockTop = appData.earnings?.can_unlock_top || false;
        
        container.innerHTML = `
            <div class="locked-state">
                <h2>TOP закрито</h2>
                <p>Запроси ${invitesNeeded} друзів щоб розблокувати TOP</p>
                <p>Або купи доступ за ${buyTopPrice} ⭐</p>
                ${canUnlockTop ? `
                    <button class="action-btn unlock-btn" onclick="switchTab('earnings')" aria-label="Розблокувати TOP через заробітки">
                        Розблокувати TOP
                    </button>
                ` : `
                    <button class="action-btn unlock-btn" onclick="handleBuyTop(${buyTopPrice})" aria-label="Купити доступ до TOP за ${buyTopPrice} зірок">
                        Купити доступ за ${buyTopPrice} ⭐
                    </button>
                `}
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
                    <button class="partner-btn" onclick="openPartner('${escapeHtml(referralLink)}', '${escapeHtml(partnerIdStr)}')" aria-label="Перейти до партнера ${escapeHtml(partner.name || 'Unknown')}">
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
    if (!container) {
        console.warn('Earnings container not found');
        return;
    }
    
    if (!appData) {
        console.warn('appData not loaded yet, showing loading state');
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
                        <button class="copy-btn" onclick="copyReferralLink()">📋 Копіювати</button>
                        <button class="share-btn" onclick="shareReferralLink()">📤 Поділитися</button>
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
                    <button class="action-btn unlock-btn" onclick="switchTab('top')" aria-label="Відкрити TOP партнерів">
                        ${translations.btn_top_partners || 'Відкрити TOP'}
                    </button>
                ` : `
                    <button class="action-btn unlock-btn" onclick="handleBuyTop(${earnings.buy_top_price || 1})" aria-label="Розблокувати TOP за ${earnings.buy_top_price || 1} зірок">
                        ${translations.btn_unlock_top || `Розблокувати TOP (${earnings.buy_top_price || 1} ⭐)`}
                    </button>
                `}
                <button class="action-btn activate-btn" onclick="showActivate7Instructions()" aria-label="Активувати програму 7% комісії">
                    ${translations.btn_activate_7 || 'Активувати 7%'}
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
    
    // Use Telegram WebApp API: openLink for all links (best practice)
    // openLink opens in browser within Telegram context, doesn't close Mini App
    // openTelegramLink would redirect to Telegram app and close Mini App
    // For t.me links, use openLink (not openTelegramLink) to keep user in Mini App context
    if (tg?.openLink) {
        tg.openLink(referralLink);
    } else {
        // Fallback: open in same window
        window.location.href = referralLink;
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
            
            // Update app data locally (no need to reload all data, just update wallet)
            if (appData && appData.user) {
                appData.user.wallet = walletAddress;
            }
            
            // Update input after successful save
            if (input) {
                input.value = walletAddress;
            }
            
            // Re-render wallet section to show updated data
            // Don't call loadAppData here to avoid tab switching issues
            renderWallet();
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
 * Show welcome screen with clear instructions
 */
function showWelcomeScreen() {
    const welcomeScreen = document.getElementById('welcome-screen');
    const welcomeMessage = document.getElementById('welcome-message');
    const welcomeCloseBtn = document.getElementById('welcome-close-btn');
    
    if (!welcomeScreen || !appData) return;
    
    // Create clear onboarding message
    const botName = appData.config?.name || 'Mini App';
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
    
    // Close welcome screen
    if (welcomeCloseBtn) {
        welcomeCloseBtn.onclick = () => {
            welcomeScreen.style.display = 'none';
            localStorage.setItem('mini_app_welcome_seen', 'true');
            // appData should already be loaded at this point
            if (appData) {
                renderApp(); // This will show Earnings tab first
            } else {
                // If appData not loaded, load it first
                loadAppData(false).then(() => {
                    renderApp();
                });
            }
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
    
    // Use openLink to open share dialog in browser, keep user in Mini App context
    if (tg?.openLink) {
        tg.openLink(shareUrl);
    } else {
        // Fallback: open in same window
        window.location.href = shareUrl;
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
    
    // Disable pull-to-refresh - it's too sensitive and causes accidental reloads
    // Users can refresh by closing and reopening Mini App if needed
    return;
    
    // Old code below (disabled)
    /*
    let touchStartY = 0;
    let touchCurrentY = 0;
    let isPulling = false;
    let pullDistance = 0;
    let touchStartTime = 0;
    const pullThreshold = 200; // Very high threshold - requires intentional pull
    const minPullDistance = 100; // Minimum distance before showing indicator
    const maxScrollTop = 2; // Very strict - must be exactly at top
    
    content.addEventListener('touchstart', (e) => {
        // Only trigger if at top of scroll (with small tolerance)
        if (content.scrollTop <= maxScrollTop) {
            touchStartY = e.touches[0].clientY;
            touchStartTime = Date.now();
            isPulling = true;
        } else {
            isPulling = false;
        }
    }, { passive: true });
    
    content.addEventListener('touchmove', (e) => {
        if (!isPulling) return;
        
        // Check if still at top
        if (content.scrollTop > maxScrollTop) {
            isPulling = false;
            hidePullToRefresh();
            return;
        }
        
        touchCurrentY = e.touches[0].clientY;
        pullDistance = touchCurrentY - touchStartY;
        
        // Only show indicator if pulled down significantly
        if (pullDistance > minPullDistance && content.scrollTop <= maxScrollTop) {
            e.preventDefault();
            updatePullToRefresh(pullDistance);
        } else if (pullDistance <= 0) {
            // User is scrolling up, cancel pull-to-refresh
            isPulling = false;
            hidePullToRefresh();
        }
    }, { passive: false });
    
    content.addEventListener('touchend', () => {
        if (!isPulling) {
            hidePullToRefresh();
            return;
        }
        
        // Only trigger if pulled down enough AND user held for a moment (not accidental scroll)
        const touchDuration = Date.now() - touchStartTime;
        const minDuration = 300; // At least 300ms to distinguish from quick scroll
        
        if (pullDistance >= pullThreshold && touchDuration >= minDuration) {
            // Trigger refresh
            showPullToRefresh();
            loadAppData(true);
        } else {
            hidePullToRefresh();
        }
        
        isPulling = false;
        pullDistance = 0;
        touchStartTime = 0;
    }, { passive: true });
    
    // Also handle scroll events to cancel pull-to-refresh if user scrolls
    content.addEventListener('scroll', () => {
        if (isPulling && content.scrollTop > maxScrollTop) {
            isPulling = false;
            hidePullToRefresh();
        }
    }, { passive: true });
    */
}

/**
 * Update pull-to-refresh indicator
 */
function updatePullToRefresh(distance) {
    const indicator = document.getElementById('pull-to-refresh');
    if (!indicator) return;
    
    const threshold = 120; // Match pullThreshold
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
    // Disabled - do nothing
    return;
    /*
    const indicator = document.getElementById('pull-to-refresh');
    if (indicator) {
        indicator.classList.add('active');
        indicator.querySelector('.pull-to-refresh-icon').textContent = '🔄';
        indicator.querySelector('.pull-to-refresh-text').textContent = 'Оновлення...';
    }
    */
}

/**
 * Hide pull-to-refresh indicator
 */
function hidePullToRefresh() {
    // Disabled - do nothing
    return;
    /*
    const indicator = document.getElementById('pull-to-refresh');
    if (indicator) {
        indicator.classList.remove('active', 'ready');
        indicator.style.opacity = '0';
        indicator.style.transform = 'translateX(-50%) translateY(-100%)';
        indicator.querySelector('.pull-to-refresh-icon').textContent = '⬇️';
        indicator.querySelector('.pull-to-refresh-text').textContent = 'Потягніть для оновлення';
    }
    */
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
    
    // Use openLink (not openTelegramLink) to open in browser, keep user in Mini App context
    if (tg?.openLink) {
        tg.openLink(botUrl);
    } else {
        // Fallback: open in same window
        window.location.href = botUrl;
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

