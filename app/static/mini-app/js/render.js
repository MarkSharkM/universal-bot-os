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

        // Ensure App Container is visible
        const appContainer = document.getElementById('app');
        if (appContainer) appContainer.style.display = 'block';

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

    handleImageError(img, name, secondaryUrl) {
        if (!img || !img.parentNode) return;

        // Try secondary URL (e.g. Telegram CDN) if not already tried
        if (secondaryUrl && !img.dataset.triedSecondary) {
            img.dataset.triedSecondary = 'true';
            img.src = secondaryUrl;
            return;
        }

        // Generate nice color from name
        const colors = ['#F44336', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#009688', '#4CAF50', '#FFC107', '#FF5722'];
        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }
        const color = colors[Math.abs(hash) % colors.length];

        const initials = (name || 'B').substring(0, 2).toUpperCase();

        // Create fallback element
        const div = document.createElement('div');
        div.className = 'icon-fallback';
        div.style.backgroundColor = color;
        div.textContent = initials;

        // Preserve classes from original img
        div.className += ' ' + img.className;

        // Replace img with div
        img.parentNode.replaceChild(div, img);
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

        const setPlaceholder = (id, text) => {
            const el = document.getElementById(id);
            if (el && text) el.placeholder = text;
        };

        // Navigation
        const tabs = document.querySelectorAll('.tab');
        tabs.forEach(tab => {
            const tabName = tab.getAttribute('data-tab');
            const label = tab.querySelector('.tab-label');
            if (label) {
                if (tabName === 'home') label.textContent = translations.nav_home || 'Home';
                if (tabName === 'partners') label.textContent = translations.nav_partners || 'Partners';
                if (tabName === 'top') label.textContent = translations.nav_top || 'TOP';
            }
        });

        // Common
        setText('loading-text', translations.loading || 'Loading...');
        setText('retry-btn', translations.retry_btn || 'Try again');

        // Home Page Static Elements
        setText('trust-item-1', translations.trust_item_1 || '🟢 Official Telegram Partner Program');
        setText('trust-item-2', translations.trust_item_2 || '🟢 Revenue share model (up to 7%)');
        setText('trust-item-3', translations.trust_item_3 || '🟢 Wallet: optional');

        setText('share-copy-1', translations.share_copy_1 || 'Your link works 24/7');
        setText('share-copy-2', translations.share_copy_2 || 'Every new user can launch this path further');

        setText('wallet-banner-text', translations.wallet_banner_text || 'Connect wallet → enable withdrawals');
        setText('wallet-banner-btn', translations.wallet_banner_btn || 'Connect');

        setText('info-title-text', translations.info_title || 'Bot Info');

        // Share Popup
        setText('share-popup-title', translations.share_popup_title || 'Share Link');
        setText('share-popup-text', translations.share_popup_text || 'I joined the Telegram partner program. It works automatically.');
        setText('share-popup-share-text', translations.share_button || '🧡 Share Link');
        setText('share-popup-close-text', translations.close_btn || 'Close');

        // Wallet manual modal
        setText('wallet-manual-title', translations.connect || 'Connect TON Wallet');
        setText('wallet-modal-copy', translations.wallet_modal_copy || 'Only needed for future payouts\nWe never withdraw funds');
        setText('wallet-instructions-title', translations.how_to_find_address || 'How to find wallet address:');
        setText('wallet-instruction-1', translations.instruction_step_1 || 'Open your TON wallet (Tonkeeper, MyTonWallet, Tonhub)');
        setText('wallet-instruction-2', translations.instruction_step_2 || 'Find "Receive" section');
        setText('wallet-instruction-3', translations.instruction_step_3 || 'Copy address (starts with EQ, UQ, kQ or 0Q)');
        setText('wallet-modal-input-label', translations.wallet_input_label || 'TON Wallet Address:');
        setText('wallet-manual-save-btn', translations.save || 'Save');
        setText('wallet-manual-close', translations.cancel || 'Cancel');
        setPlaceholder('wallet-modal-input', 'EQD0X...');

        // Wallet Connect Modal (TON Connect style)
        setText('wallet-connect-title', translations.wallet_connect_title || 'Connect your TON wallet');
        setText('wallet-connect-subtitle', translations.wallet_connect_subtitle || 'Use Wallet in Telegram or choose other application');
        setText('wallet-connect-telegram-text', translations.connect_telegram_wallet || 'Connect Wallet in Telegram');
        setText('wallet-connect-choose-text', translations.choose_other_wallet || 'Choose other application');
        setText('wallet-connect-view-all-text', translations.view_all_wallets || 'View all wallets');

        // Onboarding
        setText('onboarding-title-1', translations.onboarding_title_1 || 'Earn from actions in Telegram');
        setText('onboarding-step-1-text', translations.onboarding_step_1 || 'Activate 7%');
        setText('onboarding-step-2-text', translations.onboarding_step_2 || 'Share your link');
        setText('onboarding-step-3-text', translations.onboarding_step_3 || 'People buy → you get %');
        setText('onboarding-next-text', translations.next_btn || 'Next');
        setText('onboarding-start-text', translations.start_btn || 'Start');
    }
};

// Aliases for global access (backward compatibility)
window.renderApp = () => window.Render.renderApp();
window.trackEvent = (e, d) => window.Render.trackEvent(e, d);
window.escapeHtml = (s) => window.Render.escapeHtml(s);

// UI Helper Aliases (Restore missing globals)
window.showLoading = (s) => window.Render.showLoading(s);
window.showError = (m, t) => window.Render.showError(m, t);
window.showSkeleton = (t) => window.Render.showSkeleton(t);
window.hideSkeleton = (t) => window.Render.hideSkeleton(t);
window.handleImageError = (i, n, s) => window.Render.handleImageError(i, n, s);


