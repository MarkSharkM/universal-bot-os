/**
 * TON Connect Integration Module
 * Handles TON wallet connections using TON Connect SDK
 */

const TON_CONNECT_VERSION = "1.0.2";
console.log(`[TON Connect Extension] Loading Version: ${TON_CONNECT_VERSION}`);

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

        // Dynamic Manifest URL construction
        // Try to get bot_id from URL params (standard for our mini app routing)
        const urlParams = new URLSearchParams(window.location.search);
        // Sometimes bot_id is in the path, sometimes passed as query param. 
        // For Mini Apps started via /mini-app/{bot_id}/index.html, we can try to extract it from location or initData

        // Default base
        let manifestBase = '/api/v1/mini-apps/tonconnect-manifest.json';

        // Try to find bot_id in URL path (e.g., /api/v1/mini-apps/{bot_id}/index.html is not common, usually served via static)
        // Better: Check if we have appData with bot_id
        const appData = AppState.getAppData();
        if (appData && appData.botId) {
            console.log('✅ Found botId in AppState:', appData.botId);
            manifestBase = `/api/v1/mini-apps/${appData.botId}/tonconnect-manifest.json`;
        } else {
            console.warn('⚠️ No botId found in AppState, using default manifest endpoint');
        }

        const manifestUrl = window.location.origin + manifestBase + '?v=' + new Date().getTime();
        // This is CRITICAL - wallet must return to this URL after connection
        // Format: https://t.me/{bot_username}/mini-app (REQUIRED for Mini Apps!)
        let twaReturnUrl = null;

        // DEBUG: Log AppState data to see what we have
        // Reuse appData from above
        console.log('🔍 DEBUG AppState config:', {
            hasAppData: !!appData,
            hasConfig: !!(appData && appData.config),
            configUsername: appData?.config?.username,
            configName: appData?.config?.name,
            fullConfig: appData?.config
        });

        // Priority 1: Use config.username from API (most reliable)
        if (appData && appData.config && appData.config.username) {
            const apiUsername = appData.config.username.replace('@', '').trim();
            twaReturnUrl = `https://t.me/${apiUsername}/mini-app`;
            console.log('📋 Using config.username (from API):', twaReturnUrl);
        }
        // Priority 2: Try getBotUrl() function
        else if (typeof getBotUrl === 'function') {
            try {
                const botUrl = getBotUrl();
                console.log('📋 getBotUrl() returned:', botUrl);
                if (botUrl) {
                    // Add /mini-app suffix if not present (REQUIRED for TON Connect in Mini Apps)
                    twaReturnUrl = botUrl.endsWith('/mini-app') ? botUrl : `${botUrl}/mini-app`;
                    console.log('📋 Using getBotUrl() (with /mini-app):', twaReturnUrl);
                }
            } catch (err) {
                console.warn('⚠️ Error calling getBotUrl():', err);
            }
        }
        // Priority 3: Fallback to config.name
        if (!twaReturnUrl && appData && appData.config && appData.config.name) {
            // Extract username from name (remove spaces, keep only alphanumeric and underscores)
            const botName = appData.config.name.replace(/[^a-zA-Z0-9_]/g, '').trim().toLowerCase();
            if (botName) {
                twaReturnUrl = `https://t.me/${botName}/mini-app`;
                console.log('📋 Using config.name (fallback):', twaReturnUrl);
            }
        }

        // Validate twaReturnUrl format (must include /mini-app for Mini Apps)
        if (!twaReturnUrl || !twaReturnUrl.startsWith('https://t.me/')) {
            console.error('❌ Invalid twaReturnUrl format:', twaReturnUrl);
            console.error('Expected format: https://t.me/username/mini-app');
            console.error('Bot username not found in config. Please sync username via /api/v1/admin/bots/{bot_id}/sync-username');
            throw new Error('Bot username not found. Please sync username via API.');
        } else if (!twaReturnUrl.endsWith('/mini-app')) {
            // Ensure /mini-app suffix is present (REQUIRED for TON Connect)
            twaReturnUrl = `${twaReturnUrl}/mini-app`;
            console.log('⚠️ Added /mini-app suffix to twaReturnUrl:', twaReturnUrl);
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
                    console.log('✅ TON Wallet connected, extracted address:', address);
                    console.log('🔗 Full Address Object:', JSON.stringify(walletInfo.account || walletInfo, null, 2));
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
let lastSavedAddress = null;

/**
 * Handle wallet connected
 */
async function handleWalletConnected(address) {
    console.log('🎉 handleWalletConnected called with address:', address);

    // Prevent duplicate saves for same session/address
    if (lastSavedAddress === address) {
        console.log('⚠️ Wallet already processed in this session, skipping API call.');
        return;
    }
    lastSavedAddress = address; // Mark as processing immediately

    console.log('📏 Address length:', address.length);
    console.log('🆔 Address start:', address.substring(0, 5));
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
            const knownWallet = appData?.user?.wallet;

            // LOGIC: If the wallet we just connected is ALREADY the one in our database (loaded on startup),
            // implies this is just a session restore/page reload. Don't spam the user with "Connected!" toast.
            const isSilent = (knownWallet && knownWallet === address);

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

            // Only show success notification if it's a NEW connection (not silent restore)
            if (!isSilent) {
                if (typeof Toast !== 'undefined') {
                    Toast.success(AppState.getAppData()?.translations?.wallet_connected || '✅ Гаманець підключено успішно!');
                }
                if (typeof Haptic !== 'undefined') {
                    Haptic.success();
                }
            } else {
                console.log('🤫 Silent connection restore (wallet unchanged), skipping toast.');
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
            const errorMsg = error.message || 'Невідома помилка при збереженні гаманця';
            Toast.error(errorMsg);
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
async function connectTelegramWallet() {
    console.log('connectTelegramWallet called');
    if (!tonConnectUI) {
        console.error('TON Connect UI not initialized');
        return;
    }

    try {
        if (typeof Render !== 'undefined' && Render.trackEvent) {
            Render.trackEvent('wallet_connect_telegram_clicked');
        }

        // Hide our custom modal immediately to show wallet UI
        const modal = document.getElementById('wallet-modal');
        if (modal) modal.style.display = 'none';

        // Get available wallets to find Telegram Wallet
        const wallets = await tonConnectUI.getWallets();
        console.log('[TON Connect] All available wallets:', JSON.stringify(wallets, null, 2));

        // Let's log specifically what we are looking for
        wallets.forEach(w => {
            console.log(`[Wallet Check] Name: "${w.name}", appName: "${w.appName}", jsBridgeKey: "${w.jsBridgeKey}"`);
        });

        // Find Telegram Wallet (usually named "Wallet" or has "telegram-wallet" jsBridgeKey)
        const tgWallet = wallets.find(w =>
            w.appName === 'telegram-wallet' ||
            w.appName === 'wallet' ||
            w.name.toLowerCase().includes('wallet') ||
            w.jsBridgeKey === 'telegram-wallet'
        );

        if (tgWallet) {
            console.log('🚀 Connecting to Telegram Wallet directly...', tgWallet);
            await tonConnectUI.connectWallet(tgWallet);
        } else {
            console.warn('⚠️ Telegram Wallet not found in list, falling back to modal');
            await tonConnectUI.openModal();
        }
    } catch (error) {
        console.error('❌ Error connecting Telegram Wallet:', error);
        if (typeof Toast !== 'undefined') {
            Toast.error('Помилка підключення до Wallet');
        }
    }
}

/**
 * Connect External Wallet using TON Connect
 */
async function connectExternalWallet(walletName) {
    if (!tonConnectUI) return;

    try {
        if (typeof Render !== 'undefined' && Render.trackEvent) {
            Render.trackEvent('wallet_connect_external', { wallet: walletName });
        }

        // Hide our custom modal
        const modal = document.getElementById('wallet-modal');
        if (modal) modal.style.display = 'none';

        if (walletName === 'all') {
            await tonConnectUI.openModal();
            return;
        }

        const wallets = await tonConnectUI.getWallets();
        const selectedWallet = wallets.find(w =>
            w.appName === walletName ||
            w.name.toLowerCase().includes(walletName.toLowerCase())
        );

        if (selectedWallet) {
            console.log(`🚀 Connecting to ${walletName} directly...`, selectedWallet);
            await tonConnectUI.connectWallet(selectedWallet);
        } else {
            console.warn(`⚠️ Wallet ${walletName} not found, opening modal`);
            await tonConnectUI.openModal();
        }
    } catch (error) {
        console.error(`❌ Error connecting to ${walletName}:`, error);
        if (typeof Toast !== 'undefined') {
            Toast.error(`Помилка підключення до ${walletName}`);
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
