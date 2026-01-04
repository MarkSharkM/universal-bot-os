/**
 * TON Connect Integration Module
 * Handles TON wallet connections using TON Connect SDK
 */

let tonConnectUI = null;

/**
 * Initialize TON Connect UI
 */
function initTonConnect() {
    try {
        // Check if TON Connect SDK is loaded
        // SDK from CDN is available as TON_CONNECT_UI.TonConnectUI
        if (typeof TON_CONNECT_UI === 'undefined' || typeof TON_CONNECT_UI.TonConnectUI === 'undefined') {
            console.warn('TON Connect SDK not loaded, using fallback');
            console.warn('Expected: TON_CONNECT_UI.TonConnectUI, but got:', {
                TON_CONNECT_UI: typeof TON_CONNECT_UI,
                TonConnectUI: typeof TonConnectUI,
                windowKeys: Object.keys(window).filter(k => k.includes('TON') || k.includes('Ton'))
            });
            return false;
        }
        
        const tg = AppState.getTg();
        const manifestUrl = window.location.origin + '/api/v1/mini-apps/tonconnect-manifest.json';
        
        // Get return URL for Telegram Mini App (universal for any bot)
        let twaReturnUrl = 'https://t.me/EarnHubAggregatorBot';
        if (typeof getBotUrl === 'function') {
            twaReturnUrl = getBotUrl();
        } else {
            // Fallback: try to get from AppState
            const appData = AppState.getAppData();
            if (appData && appData.config) {
                // Try to get username from config (stored by sync-username endpoint)
                if (appData.config.username) {
                    twaReturnUrl = `https://t.me/${appData.config.username.replace('@', '')}`;
                } else if (appData.config.name) {
                    // Fallback: use bot name (assuming it matches username)
                    const botName = appData.config.name.toLowerCase().replace(/\s+/g, '').replace('@', '');
                    twaReturnUrl = `https://t.me/${botName}`;
                }
            }
        }
        
        // Use TON_CONNECT_UI.TonConnectUI from CDN
        tonConnectUI = new TON_CONNECT_UI.TonConnectUI({
            manifestUrl: manifestUrl,
            buttonRootId: 'wallet-connect-telegram',
            uiOptions: {
                twaReturnUrl: twaReturnUrl,
            }
        });
        
        // Listen for wallet connection status changes
        tonConnectUI.onStatusChange((walletInfo) => {
            if (walletInfo) {
                // Wallet connected
                const address = walletInfo.account.address;
                console.log('TON Wallet connected:', address);
                handleWalletConnected(address);
            } else {
                // Wallet disconnected
                console.log('TON Wallet disconnected');
                handleWalletDisconnected();
            }
        });
        
        console.log('✅ TON Connect initialized');
        return true;
    } catch (error) {
        console.error('Error initializing TON Connect:', error);
        return false;
    }
}

/**
 * Handle wallet connected
 */
async function handleWalletConnected(address) {
    try {
        if (typeof Render !== 'undefined' && Render.trackEvent) {
            Render.trackEvent('wallet_connected_ton', { method: 'ton_connect' });
        } else if (typeof trackEvent === 'function') {
            trackEvent('wallet_connected_ton', { method: 'ton_connect' });
        }
        
        const botId = AppState.getBotId();
        const initData = AppState.getTg()?.initData || null;
        
        if (botId && typeof Api !== 'undefined' && Api.saveWallet) {
            await Api.saveWallet(botId, address, AppState.getUserId(), initData);
            
            // Update app data
            const appData = AppState.getAppData();
            if (appData && appData.user) {
                appData.user.wallet = address;
                AppState.setAppData(appData);
            }
            
            // Hide modals
            const tonConnectModal = document.getElementById('wallet-modal');
            if (tonConnectModal) tonConnectModal.style.display = 'none';
            
            const manualModal = document.getElementById('wallet-manual-modal');
            if (manualModal) manualModal.style.display = 'none';
            
            // Update wallet banner
            if (typeof Render !== 'undefined' && Render.renderWalletBanner) {
                Render.renderWalletBanner();
            }
            
            if (typeof Toast !== 'undefined') {
                Toast.success('✅ Гаманець підключено успішно!');
            }
            if (typeof Haptic !== 'undefined') {
                Haptic.success();
            }
        }
    } catch (error) {
        console.error('Error saving connected wallet:', error);
        if (typeof Toast !== 'undefined') {
            Toast.error('❌ Помилка збереження: ' + (error.message || 'Невідома помилка'));
        }
    }
}

/**
 * Handle wallet disconnected
 */
function handleWalletDisconnected() {
    // Update UI to show wallet banner again
    if (typeof Render !== 'undefined' && Render.renderWalletBanner) {
        Render.renderWalletBanner();
    }
}

/**
 * Connect Telegram Wallet using TON Connect
 */
function connectTelegramWallet() {
    if (tonConnectUI) {
        try {
            if (typeof Render !== 'undefined' && Render.trackEvent) {
                Render.trackEvent('wallet_connect_telegram_clicked');
            } else if (typeof trackEvent === 'function') {
                trackEvent('wallet_connect_telegram_clicked');
            }
            tonConnectUI.openModal();
        } catch (error) {
            console.error('Error opening TON Connect modal:', error);
            // Fallback to manual input
            if (typeof Render !== 'undefined' && Render.showManualWalletInput) {
                Render.showManualWalletInput();
            } else if (typeof showManualWalletInput === 'function') {
                showManualWalletInput();
            }
        }
    } else {
        // Fallback to manual input
        if (typeof Render !== 'undefined' && Render.showManualWalletInput) {
            Render.showManualWalletInput();
        } else if (typeof showManualWalletInput === 'function') {
            showManualWalletInput();
        }
    }
}

/**
 * Connect External Wallet using TON Connect
 */
function connectExternalWallet(walletName) {
    if (tonConnectUI) {
        try {
            if (typeof Render !== 'undefined' && Render.trackEvent) {
                Render.trackEvent('wallet_connect_external', { wallet: walletName });
            } else if (typeof trackEvent === 'function') {
                trackEvent('wallet_connect_external', { wallet: walletName });
            }
            // TON Connect SDK handles external wallets automatically
            tonConnectUI.openModal();
        } catch (error) {
            console.error('Error opening TON Connect modal:', error);
            if (typeof Render !== 'undefined' && Render.showManualWalletInput) {
                Render.showManualWalletInput();
            } else if (typeof showManualWalletInput === 'function') {
                showManualWalletInput();
            }
        }
    } else {
        if (typeof Render !== 'undefined' && Render.showManualWalletInput) {
            Render.showManualWalletInput();
        } else if (typeof showManualWalletInput === 'function') {
            showManualWalletInput();
        }
    }
}

// Export functions
window.TonConnect = {
    initTonConnect,
    connectTelegramWallet,
    connectExternalWallet,
    handleWalletConnected,
    handleWalletDisconnected
};
