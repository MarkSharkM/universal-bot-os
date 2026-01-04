/**
 * Main Mini App Logic
 * Initialization and data loading
 */

// Note: Uses AppState for global state
// Note: Other modules (Render, Navigation, Events, Actions) are loaded before this

// Retry counter for AppState loading
let appStateRetryCount = 0;
const MAX_APPSTATE_RETRIES = 50; // 5 seconds max (50 * 100ms)

async function initMiniApp() {
    try {
        // Wait for AppState to be loaded (with max retries)
        if (typeof AppState === 'undefined' || !AppState.setTg) {
            appStateRetryCount++;
            if (appStateRetryCount >= MAX_APPSTATE_RETRIES) {
                console.error('AppState module failed to load after', MAX_APPSTATE_RETRIES, 'attempts');
                if (typeof Render !== 'undefined' && Render.showError) {
                    Render.showError('Помилка завантаження модулів. Перезавантажте сторінку.');
                } else {
                    showError('Помилка завантаження модулів. Перезавантажте сторінку.');
                }
                return;
            }
            // Only log first few attempts to avoid spam
            if (appStateRetryCount <= 3) {
                console.warn('AppState module not loaded yet, retrying...', appStateRetryCount);
            }
            setTimeout(initMiniApp, 100);
            return;
        }
        
        // Reset retry counter on success
        appStateRetryCount = 0;
        
        // Get Telegram WebApp instance
        const tg = window.Telegram?.WebApp;
        AppState.setTg(tg);
        
        if (!tg) {
            console.error('Telegram WebApp SDK not loaded');
            if (typeof Render !== 'undefined' && Render.showError) {
                Render.showError('Telegram WebApp SDK не завантажено');
            } else {
                showError('Telegram WebApp SDK не завантажено');
            }
            return;
        }
        
        // Initialize Telegram WebApp
        tg.ready();
        // Expand to full height to prevent closing on scroll
        tg.expand();
        // Enable closing confirmation (optional, prevents accidental closes)
        tg.enableClosingConfirmation();
        
        // Get user data from initData
        const initDataUnsafe = tg.initDataUnsafe;
        const user = initDataUnsafe?.user;
        const userId = user?.id?.toString();
        AppState.setUserId(userId);
        
        // Warn if userId is missing (but continue - API can use initData)
        if (!userId) {
            console.warn('User ID not found in initData, will use initData for validation');
        }
        
        // Get bot_id from URL or initData (async)
        const botId = await getBotIdFromUrl();
        AppState.setBotId(botId);
        
        if (!botId) {
            console.error('Bot ID not found');
            if (typeof Render !== 'undefined' && Render.showError) {
                Render.showError('Bot ID не знайдено. Перевірте URL або налаштування бота.');
            } else {
                showError('Bot ID не знайдено. Перевірте URL або налаштування бота.');
            }
            return;
        }
        
        // Initialize TON Connect (after app data is loaded)
        // Will be initialized in loadAppData after data is fetched
        
        // Apply theme from Telegram
        applyTheme();
        
        // Setup event handlers
        if (typeof Events !== 'undefined' && Events.setupEventHandlers) {
            Events.setupEventHandlers();
        } else {
            setupEventHandlers();
        }
        
        // Setup offline detection
        if (typeof Events !== 'undefined' && Events.setupOfflineDetection) {
            Events.setupOfflineDetection();
        }
        
        // Load app data
        loadAppData();
        
    } catch (error) {
        console.error('Error initializing Mini App:', error);
        const errorType = error.type || 'general';
        if (typeof Render !== 'undefined' && Render.showError) {
            Render.showError('Помилка ініціалізації: ' + error.message, errorType);
        } else {
            showError('Помилка ініціалізації: ' + error.message, errorType);
        }
    }
}

async function getBotIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    let botId = params.get('bot_id');
    
    const tg = AppState.getTg();
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

function applyTheme() {
    const tg = AppState.getTg();
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
    const appData = AppState.getAppData();
    if (appData && appData.config) {
        applyBotConfig(appData.config);
    }
}

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
        if (features.home === false) {
            const homeTab = document.querySelector('[data-tab="home"]');
            if (homeTab) homeTab.style.display = 'none';
        }
        if (features.partners === false) {
            const partnersTab = document.querySelector('[data-tab="partners"]');
            if (partnersTab) partnersTab.style.display = 'none';
        }
        if (features.top === false) {
            const topTab = document.querySelector('[data-tab="top"]');
            if (topTab) topTab.style.display = 'none';
        }
    }
    
    // Update bot name from config
    const botNameEl = document.getElementById('bot-name');
    if (botNameEl && config.name) {
        botNameEl.textContent = config.name;
    }
}

async function loadAppData(showRefreshIndicator = false) {
    // Prevent concurrent requests
    if (AppState.getIsLoadingData() && !showRefreshIndicator) {
        console.log('Data already loading, skipping duplicate request');
        return Promise.resolve(); // Return resolved promise to prevent errors
    }
    
    // Debounce: cancel previous pending request if not a refresh
    const timeout = AppState.getLoadDataTimeout();
    if (!showRefreshIndicator && timeout) {
        clearTimeout(timeout);
        AppState.setLoadDataTimeout(null);
    }
    
    // If not a refresh, debounce the request by 100ms to batch rapid calls
    if (!showRefreshIndicator && !AppState.getIsLoadingData()) {
        return new Promise((resolve, reject) => {
            const newTimeout = setTimeout(async () => {
                AppState.setLoadDataTimeout(null);
                try {
                    await loadAppDataInternal(showRefreshIndicator);
                    resolve();
                } catch (error) {
                    reject(error);
                }
            }, 100);
            AppState.setLoadDataTimeout(newTimeout);
        });
    }
    
    // For refresh or if already loading, call directly
    return loadAppDataInternal(showRefreshIndicator);
}

async function loadAppDataInternal(showRefreshIndicator = false) {
    try {
        AppState.setIsLoadingData(true);
        
        // Don't show loading screen if we're just refreshing data (not initial load)
        // Only show loading on first load or when explicitly requested via showRefreshIndicator
        if (!showRefreshIndicator && AppState.getIsInitialLoad()) {
            if (typeof Render !== 'undefined' && Render.showLoading) {
                Render.showLoading(true);
            } else {
                showLoading(true);
            }
        } else if (!showRefreshIndicator && AppState.getAppData()) {
            // Show skeleton for current page while loading
            const currentPage = AppState.getCurrentPage();
            if (currentPage) {
                if (typeof Render !== 'undefined' && Render.showSkeleton) {
                    Render.showSkeleton(currentPage);
                } else {
                    showSkeleton(currentPage);
                }
            }
        }
        // showRefreshIndicator is handled by pull-to-refresh UI
        
        // Get initData for validation
        const tg = AppState.getTg();
        const botId = AppState.getBotId();
        const userId = AppState.getUserId();
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
            AppState.setAppData(data);
            
            // Initialize TON Connect after app data is loaded
            if (typeof TonConnect !== 'undefined' && TonConnect.initTonConnect) {
                // Wait a bit for SDK to fully load and app data to be set
                setTimeout(() => {
                    TonConnect.initTonConnect();
                }, 500);
            }
            
            // Show onboarding on first visit (check localStorage)
            const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
            const hasSeenOnboarding = AppState.getHasSeenOnboarding() || 
                                      storage.getItem('has_seen_onboarding') === 'true';
            if (!hasSeenOnboarding) {
                // Hide loading screen when showing onboarding
                if (typeof Render !== 'undefined' && Render.showLoading) {
                    Render.showLoading(false);
                } else {
                    showLoading(false);
                }
                
                if (typeof Render !== 'undefined' && Render.showOnboarding) {
                    Render.showOnboarding();
                } else if (typeof Render !== 'undefined' && Render.showWelcomeScreen) {
                    Render.showWelcomeScreen();
                } else {
                    if (typeof showOnboarding === 'function') {
                        showOnboarding();
                    } else {
                        showWelcomeScreen();
                    }
                }
            } else {
                // Only switch to HOME tab on initial load (when app is first shown)
                // Don't switch if this is just a data refresh (showRefreshIndicator or not isInitialLoad)
                const isFirstLoad = AppState.getIsInitialLoad() && !showRefreshIndicator;
                
                if (isFirstLoad) {
                    // Show HOME tab first (Action Engine)
                    if (typeof Render !== 'undefined' && Render.renderApp) {
                        Render.renderApp();
                    } else {
                        renderApp();
                    }
                    
                    // Only auto-switch to home if isInitialLoad is still true
                    // (user hasn't manually switched tabs yet)
                    // Check again right before switching to handle race conditions
                    if (AppState.getIsInitialLoad()) {
                        // Switch to HOME tab first (Action Engine)
                        // Note: switchTab will set isInitialLoad = false when called
                        if (typeof Navigation !== 'undefined' && Navigation.switchTab) {
                            Navigation.switchTab('home');
                        } else {
                            switchTab('home');
                        }
                    }
                    // If isInitialLoad is false, user already switched tabs manually, don't force switch
                } else {
                    // This is a data refresh, not initial load
                    // Just update the data and re-render current tab
                    if (typeof Render !== 'undefined' && Render.renderApp) {
                        Render.renderApp();
                    } else {
                        renderApp();
                    }
                    // Re-render current page with fresh data
                    const currentPage = AppState.getCurrentPage();
                    if (currentPage === 'home') {
                        if (typeof Render !== 'undefined' && Render.hideSkeleton && Render.renderHome) {
                            Render.hideSkeleton('home');
                            Render.renderHome();
                        } else {
                            hideSkeleton('home');
                            renderHome();
                        }
                    } else if (currentPage === 'top') {
                        if (typeof Render !== 'undefined' && Render.hideSkeleton && Render.renderTop) {
                            Render.hideSkeleton('top');
                            Render.renderTop();
                        } else {
                            hideSkeleton('top');
                            renderTop();
                        }
                    } else if (currentPage === 'partners') {
                        if (typeof Render !== 'undefined' && Render.hideSkeleton && Render.renderPartners) {
                            Render.hideSkeleton('partners');
                            Render.renderPartners();
                        } else {
                            hideSkeleton('partners');
                            renderPartners();
                        }
                        if (typeof Navigation !== 'undefined' && Navigation.setupSearchAndFilters) {
                            Navigation.setupSearchAndFilters();
                        } else {
                            setupSearchAndFilters();
                        }
                    }
                }
                if (typeof Render !== 'undefined' && Render.showLoading) {
                    Render.showLoading(false);
                } else {
                    showLoading(false);
                }
            }
            
            if (showRefreshIndicator) {
                if (typeof Events !== 'undefined' && Events.hidePullToRefresh) {
                    Events.hidePullToRefresh();
                } else {
                    hidePullToRefresh();
                }
            }
        } else {
            throw new Error(data.detail || 'Failed to load data');
        }
        } catch (error) {
            console.error('Error loading app data:', error);
            const errorType = error.type || (error.message.includes('інтернет') ? 'network' : 'api');
            if (typeof Render !== 'undefined' && Render.showError) {
                Render.showError('Помилка завантаження даних: ' + error.message, errorType);
            } else {
                showError('Помилка завантаження даних: ' + error.message, errorType);
            }
        if (typeof Render !== 'undefined' && Render.showLoading) {
            Render.showLoading(false);
        } else {
            showLoading(false);
        }
        if (showRefreshIndicator) {
            if (typeof Events !== 'undefined' && Events.hidePullToRefresh) {
                Events.hidePullToRefresh();
            } else {
                hidePullToRefresh();
            }
        }
    } finally {
        AppState.setIsLoadingData(false); // Always reset loading flag
    }
}


// Initialize when DOM is ready AND all scripts are loaded
(function() {
    let initAttempts = 0;
    const MAX_INIT_ATTEMPTS = 20; // 1 second max (20 * 50ms)
    
    function tryInit() {
        initAttempts++;
        
        // Check if all required modules are loaded
        if (typeof AppState === 'undefined' || typeof AppState.setTg !== 'function') {
            if (initAttempts >= MAX_INIT_ATTEMPTS) {
                console.error('Failed to load AppState after', MAX_INIT_ATTEMPTS, 'attempts');
                console.error('AppState type:', typeof AppState);
                console.error('AppState value:', AppState);
                
                const errorEl = document.getElementById('error-message');
                const errorText = document.getElementById('error-text');
                const loading = document.getElementById('loading');
                if (errorEl && errorText) {
                    errorText.textContent = 'Помилка завантаження модулів. Перезавантажте сторінку.';
                    errorEl.style.display = 'block';
                    if (loading) loading.style.display = 'none';
                }
                return;
            }
            
            // Only log first few attempts
            if (initAttempts <= 3) {
                console.warn('Waiting for AppState... attempt', initAttempts, 'of', MAX_INIT_ATTEMPTS);
            }
            
            // Wait a bit more for modules to load
            if (document.readyState === 'complete') {
                // If DOM is complete but AppState still not loaded, wait a bit more
                setTimeout(tryInit, 50);
            } else {
                // DOM still loading, wait for it
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', tryInit);
                } else {
                    setTimeout(tryInit, 50);
                }
            }
            return;
        }
        
        // All modules loaded, initialize
        console.log('✅ All modules loaded, initializing Mini App...');
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => initMiniApp());
        } else {
            initMiniApp();
        }
    }
    
    // Start trying to initialize after a small delay to ensure scripts are parsed
    // Use requestAnimationFrame for better timing
    if (typeof requestAnimationFrame !== 'undefined') {
        requestAnimationFrame(() => {
            setTimeout(tryInit, 10);
        });
    } else {
        setTimeout(tryInit, 10);
    }
})();
