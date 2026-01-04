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
        
        console.log('TON Connect SDK loaded successfully:', {
            TON_CONNECT_UI: typeof TON_CONNECT_UI,
            TonConnectUI: typeof TON_CONNECT_UI.TonConnectUI
        });
        
        const tg = AppState.getTg();
        const manifestUrl = window.location.origin + '/api/v1/mini-apps/tonconnect-manifest.json';
        console.log('📋 TON Connect manifest URL:', manifestUrl);
        
        // Get return URL for Telegram Mini App (universal for any bot)
        // This is CRITICAL - wallet must return to this URL after connection
        let twaReturnUrl = 'https://t.me/EarnHubAggregatorBot';
        
        // Try multiple methods to get correct bot URL
        if (typeof getBotUrl === 'function') {
            try {
                twaReturnUrl = getBotUrl();
                console.log('📋 Using getBotUrl():', twaReturnUrl);
            } catch (err) {
                console.warn('⚠️ Error calling getBotUrl():', err);
            }
        }
        
        // Fallback: try to get from AppState
        if (twaReturnUrl === 'https://t.me/EarnHubAggregatorBot') {
            const appData = AppState.getAppData();
            if (appData && appData.config) {
                // Try to get username from config (stored by sync-username endpoint)
                if (appData.config.username) {
                    twaReturnUrl = `https://t.me/${appData.config.username.replace('@', '').trim()}`;
                    console.log('📋 Using config.username:', twaReturnUrl);
                } else if (appData.config.name) {
                    // Fallback: use bot name (assuming it matches username)
                    const botName = appData.config.name.toLowerCase().replace(/\s+/g, '').replace('@', '').trim();
                    twaReturnUrl = `https://t.me/${botName}`;
                    console.log('📋 Using config.name:', twaReturnUrl);
                }
            }
        }
        
        // Validate twaReturnUrl format
        if (!twaReturnUrl.startsWith('https://t.me/')) {
            console.error('❌ Invalid twaReturnUrl format:', twaReturnUrl);
            console.error('Expected format: https://t.me/username');
            twaReturnUrl = 'https://t.me/EarnHubAggregatorBot'; // Fallback
        }
        
        console.log('📋 Final twaReturnUrl:', twaReturnUrl);
        console.log('⚠️ IMPORTANT: Wallet must return to this URL after connection!');
        
        // Use TON_CONNECT_UI.TonConnectUI from CDN
        // Don't use buttonRootId since we have custom button in HTML
        // We'll call openModal() manually when button is clicked
        console.log('🔧 Creating TON Connect UI instance with:', {
            manifestUrl,
            twaReturnUrl,
            hasTON_CONNECT_UI: typeof TON_CONNECT_UI !== 'undefined',
            hasTonConnectUI: typeof TON_CONNECT_UI?.TonConnectUI !== 'undefined'
        });
        
        tonConnectUI = new TON_CONNECT_UI.TonConnectUI({
            manifestUrl: manifestUrl,
            // buttonRootId: 'wallet-connect-telegram', // Removed - we use custom button
            uiOptions: {
                twaReturnUrl: twaReturnUrl,
            }
        });
        
        console.log('✅ TON Connect UI instance created');
        console.log('🔍 Instance properties:', {
            hasWallet: 'wallet' in tonConnectUI,
            hasWalletInfo: 'walletInfo' in tonConnectUI,
            hasOnStatusChange: typeof tonConnectUI.onStatusChange === 'function',
            hasOpenModal: typeof tonConnectUI.openModal === 'function'
        });
        
        // Listen for wallet connection status changes
        tonConnectUI.onStatusChange((walletInfo) => {
            console.log('🔔 TON Connect status changed callback fired!');
            console.log('walletInfo:', walletInfo);
            console.log('walletInfo type:', typeof walletInfo);
            console.log('walletInfo keys:', walletInfo ? Object.keys(walletInfo) : 'null');
            
            if (walletInfo) {
                // Wallet connected - handle different possible formats
                console.log('walletInfo.account:', walletInfo.account);
                console.log('walletInfo.address:', walletInfo.address);
                
                const address = walletInfo.account?.address || walletInfo.address;
                console.log('✅ TON Wallet connected, extracted address:', address);
                
                if (address) {
                    handleWalletConnected(address);
                } else {
                    console.warn('⚠️ Wallet connected but no address found:', walletInfo);
                    console.warn('Full walletInfo object:', JSON.stringify(walletInfo, null, 2));
                }
            } else {
                // Wallet disconnected
                console.log('⚠️ TON Wallet disconnected');
                handleWalletDisconnected();
            }
        });
        
        // Check current connection status (try multiple properties)
        try {
            console.log('Checking current wallet status...');
            console.log('tonConnectUI.wallet:', tonConnectUI.wallet);
            console.log('tonConnectUI.walletInfo:', tonConnectUI.walletInfo);
            
            // Try wallet property
            const currentWallet = tonConnectUI.wallet || tonConnectUI.walletInfo;
            if (currentWallet) {
                console.log('TON Connect: Already connected to wallet:', currentWallet);
                // If already connected, handle it
                const address = currentWallet.account?.address || currentWallet.address;
                if (address) {
                    console.log('Found existing wallet address:', address);
                    handleWalletConnected(address);
                } else {
                    console.warn('Wallet object exists but no address found:', currentWallet);
                }
            } else {
                console.log('TON Connect: No wallet connected yet');
            }
        } catch (err) {
            console.warn('Could not check current wallet status:', err);
        }
        
        console.log('TON Connect UI instance created:', tonConnectUI);
        console.log('Available methods:', Object.keys(tonConnectUI));
        console.log('openModal type:', typeof tonConnectUI.openModal);
        
        console.log('✅ TON Connect initialized successfully');
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
    console.log('🎉 handleWalletConnected called with address:', address);
    try {
        if (typeof Render !== 'undefined' && Render.trackEvent) {
            Render.trackEvent('wallet_connected_ton', { method: 'ton_connect' });
        } else if (typeof trackEvent === 'function') {
            trackEvent('wallet_connected_ton', { method: 'ton_connect' });
        }
        
        const botId = AppState.getBotId();
        const initData = AppState.getTg()?.initData || null;
        const userId = AppState.getUserId();
        
        console.log('💾 Saving wallet to backend:', {
            botId,
            address: address ? `${address.substring(0, 10)}...` : 'null',
            userId,
            hasApi: typeof Api !== 'undefined',
            hasSaveWallet: typeof Api !== 'undefined' && typeof Api.saveWallet === 'function'
        });
        
        if (botId && typeof Api !== 'undefined' && Api.saveWallet) {
            console.log('📤 Calling Api.saveWallet...');
            const saveResult = await Api.saveWallet(botId, address, userId, initData);
            console.log('✅ Wallet saved successfully:', saveResult);
            
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
        } else {
            console.error('❌ Cannot save wallet - missing requirements:', {
                botId: !!botId,
                hasApi: typeof Api !== 'undefined',
                hasSaveWallet: typeof Api !== 'undefined' && typeof Api.saveWallet === 'function'
            });
        }
    } catch (error) {
        console.error('❌ Error saving connected wallet:', error);
        console.error('Error stack:', error.stack);
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
    console.log('connectTelegramWallet called');
    console.log('tonConnectUI:', tonConnectUI);
    console.log('TON_CONNECT_UI available:', typeof TON_CONNECT_UI !== 'undefined');
    
    if (tonConnectUI) {
        try {
            if (typeof Render !== 'undefined' && Render.trackEvent) {
                Render.trackEvent('wallet_connect_telegram_clicked');
            } else if (typeof trackEvent === 'function') {
                trackEvent('wallet_connect_telegram_clicked');
            }
            
            console.log('Opening TON Connect modal...');
            console.log('tonConnectUI.openModal type:', typeof tonConnectUI.openModal);
            
            // Check if openModal exists
            if (typeof tonConnectUI.openModal === 'function') {
                console.log('Calling tonConnectUI.openModal()...');
                tonConnectUI.openModal();
                console.log('✅ TON Connect modal opened successfully');
                
                // After opening modal, set up polling to check connection status
                // This helps catch cases where onStatusChange doesn't fire immediately
                let pollCount = 0;
                const maxPolls = 30; // Check for 30 seconds
                const pollInterval = setInterval(() => {
                    pollCount++;
                    console.log(`[Poll ${pollCount}/${maxPolls}] Checking wallet status...`);
                    
                    try {
                        // Check both wallet and walletInfo properties
                        const wallet = tonConnectUI.wallet || tonConnectUI.walletInfo;
                        if (wallet) {
                            console.log('✅ Wallet found via polling!', wallet);
                            const address = wallet.account?.address || wallet.address;
                            if (address) {
                                clearInterval(pollInterval);
                                handleWalletConnected(address);
                            }
                        } else {
                            // Check if modal is still open (if we can detect it)
                            if (pollCount >= maxPolls) {
                                console.log('⚠️ Polling timeout - no wallet connection detected');
                                clearInterval(pollInterval);
                            }
                        }
                    } catch (err) {
                        console.warn('Error during wallet status poll:', err);
                        if (pollCount >= maxPolls) {
                            clearInterval(pollInterval);
                        }
                    }
                }, 1000); // Check every second
                
                // Clear polling if modal is closed (we'll detect this via onStatusChange or timeout)
                setTimeout(() => {
                    clearInterval(pollInterval);
                    console.log('Stopped polling for wallet status');
                }, maxPolls * 1000);
                
            } else {
                console.error('❌ tonConnectUI.openModal is not a function!');
                console.error('tonConnectUI object:', Object.keys(tonConnectUI));
                throw new Error('openModal is not a function');
            }
        } catch (error) {
            console.error('❌ Error opening TON Connect modal:', error);
            console.error('Error details:', error.message, error.stack);
            console.error('tonConnectUI object:', tonConnectUI);
            
            // Fallback to manual input
            if (typeof Render !== 'undefined' && Render.showManualWalletInput) {
                Render.showManualWalletInput();
            } else if (typeof showManualWalletInput === 'function') {
                showManualWalletInput();
            }
        }
    } else {
        console.warn('⚠️ TON Connect UI not initialized');
        console.warn('Attempting to re-initialize...');
        
        // Try to re-initialize
        if (typeof TonConnect !== 'undefined' && TonConnect.initTonConnect) {
            const initialized = TonConnect.initTonConnect();
            if (initialized && tonConnectUI) {
                console.log('✅ Re-initialized TON Connect, retrying...');
                connectTelegramWallet();
                return;
            }
        }
        
        console.warn('Using fallback to manual input');
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
