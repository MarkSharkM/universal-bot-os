/**
 * Render Module
 * Main entry point for UI rendering and orchestration.
 * Delegates specific logic to Components and Pages modules.
 */

window.Render = {
    // Core App Rendering
    renderApp() {
        console.log('[Render] renderApp: starting');
        const appData = AppState.getAppData();
        if (!appData) return;

        // Apply global config customization
        if (appData.config && typeof applyBotConfig === 'function') {
            applyBotConfig(appData.config);
        }

        // Update bot name in header
        const botNameEl = document.getElementById('bot-name');
        if (botNameEl) {
            botNameEl.textContent = appData.config?.name || 'Mini App';
            this.setupDevMode(botNameEl);
        }

        // Translate static UI elements
        this.translateStaticElements();

        // Initialize Global State Logic (Gamification, Onboarding)
        this.initializeState(appData);

        // NOTE: Initial tab switch is handled in app.js after loadAppData
    },

    // Initialize State Logic (moved from monolithic renderApp)
    initializeState(appData) {
        // Extract gamification state
        if (appData.user) {
            AppState.setReferralCount(appData.user.total_invited || 0);
            AppState.setTopLocked(appData.user.top_status !== 'unlocked');
        } else if (appData.earnings) {
            AppState.setReferralCount(appData.earnings.total_invited || 0);
            AppState.setTopLocked(appData.earnings.top_status !== 'unlocked');
        }

        // Check 7% flow status
        const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
        const didStart7Flow = storage.getItem('did_start_7_flow') === 'true' ||
            (appData.user?.custom_data?.did_start_7_flow);
        AppState.setDidStart7Flow(didStart7Flow);

        // Check onboarding
        const hasSeenOnboarding = storage.getItem('has_seen_onboarding') === 'true' ||
            (appData.user?.custom_data?.has_seen_onboarding);
        AppState.setHasSeenOnboarding(hasSeenOnboarding);
    },

    // Developer Mode Trigger (5 taps)
    setupDevMode(element) {
        let tapCount = 0;
        let lastTapTime = 0;

        // Clone to remove old listeners
        const newEl = element.cloneNode(true);
        element.parentNode.replaceChild(newEl, element);

        newEl.addEventListener('click', () => {
            const now = Date.now();
            if (now - lastTapTime > 1000) tapCount = 0;
            tapCount++;
            lastTapTime = now;

            if (tapCount >= 5) {
                tapCount = 0;
                if (typeof handleHardReset === 'function') {
                    handleHardReset();
                } else {
                    const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
                    storage.clear();
                    if (typeof Toast !== 'undefined') Toast.info('♻️ Factory Reset Initiated...');
                    setTimeout(() => window.location.reload(), 1000);
                }
            }
        });
    },

    // Delegate to Components/Pages
    renderHome: () => window.Pages.Home.render(), // Assumes existing Home.js or refactored separately
    renderPartners: () => window.Pages.Partners.render(),
    renderPartnersList: (p, e) => window.Pages.Partners.renderList(p, e),
    renderTop: () => window.Pages.Top.render(),

    // Delegate to Components
    renderGamification: () => window.Components.Gamification.render(),
    calculateUserStatus: () => window.Components.Gamification.calculateStatus(),
    getUserBadges: () => window.Components.Gamification.getBadges(),
    renderSocialProof: () => window.Components.Gamification.renderSocialProof(),

    showSharePopup: (t) => window.Components.SharePopup.show(t),
    checkSharePopupTriggers: () => window.Components.SharePopup.checkTriggers(),
    trackPartnerClickForPopup: () => window.Components.SharePopup.trackPartnerClick(),

    showWalletModal: () => window.Components.Wallet.showModal(),
    renderWalletBanner: () => window.Components.Wallet.renderBanner(),
    showManualWalletInput: () => window.Components.Wallet.showManualInput(),

    // UI Helpers (Keep core implementation here or move to Utils)
    showLoading(show = true) {
        const loading = document.getElementById('loading');
        if (loading) loading.style.display = show ? 'flex' : 'none';
    },

    showError(message, type = 'error') {
        const errorEl = document.getElementById('error-message');
        const errorText = document.getElementById('error-text');
        const loading = document.getElementById('loading');

        if (loading) loading.style.display = 'none';

        if (errorEl && errorText) {
            errorText.textContent = message;
            errorEl.style.display = 'block';

            // Add retry button if network error
            if (type === 'network') {
                const retryBtn = document.createElement('button');
                retryBtn.className = 'primary-btn';
                retryBtn.style.marginTop = '20px';
                retryBtn.textContent = 'Спробувати ще раз';
                retryBtn.onclick = () => window.location.reload();

                if (!errorEl.querySelector('button')) {
                    errorEl.appendChild(retryBtn);
                }
            }
        }
    },

    showSkeleton(type) {
        // Simple implementation or delegate if complex
        const ids = {
            'home': 'skeleton-home',
            'partners': 'skeleton-partners',
            'top': 'skeleton-top'
        };
        const id = ids[type];
        if (id) {
            const el = document.getElementById(id);
            if (el) el.style.display = 'block';
        }
    },

    hideSkeleton(type) {
        const ids = {
            'home': 'skeleton-home',
            'partners': 'skeleton-partners',
            'top': 'skeleton-top'
        };
        const id = ids[type];
        if (id) {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        }
    },

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    },

    trackEvent(eventName, data = {}) {
        console.log('Track event:', eventName, data);

        const botId = AppState.getBotId();
        const initData = AppState.getTg()?.initData || null;
        const tg = AppState.getTg();

        // Extract limited user data primarily for debugging/analytics
        const userData = {};
        if (tg?.initDataUnsafe?.user) {
            const user = tg.initDataUnsafe.user;
            if (user.username) userData.username = user.username;
            if (user.language_code) userData.language_code = user.language_code;
        }

        const enrichedData = {
            ...userData,
            ...data,
            source: 'mini_app_v5'
        };

        if (botId && typeof Api !== 'undefined' && Api.sendCallback) {
            Api.sendCallback(botId, {
                type: 'analytics',
                event: eventName,
                data: enrichedData
            }, initData).catch(err => console.error('Error tracking event:', err));
        }
    },

    // Static Translation (Keep here as it manipulates DOM directly based on config)
    translateStaticElements() {
        const translations = AppState.getAppData()?.translations || {};

        // Helper to safe update
        const setText = (id, text) => {
            const el = document.getElementById(id);
            if (el && text) el.textContent = text;
        };

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

        setText('loading-text', translations.loading || 'Завантаження...');
        setText('share-popup-title', translations.share_popup_title || 'Поділися лінкою');
        // ... (Other static translations can remain or be moved to a util if too large)
        // For now, keeping core UI translations here is fine for render loop.
    }
};

// Aliases for global access (backward compatibility)
window.renderApp = () => window.Render.renderApp();
window.trackEvent = (e, d) => window.Render.trackEvent(e, d);
window.escapeHtml = (s) => window.Render.escapeHtml(s);
// Other aliases provided by Components themselves
