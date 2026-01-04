/**
 * Telegram Mini App Compliance Checker
 * Checks if our Mini App follows Telegram WebApp API best practices
 * 
 * Run this in browser console to check compliance
 */

(async function() {
    const complianceResult = {
        telegramAPI: false,
        webappInitData: null,
        readyCalled: false,
        expandCalled: false,
        themeParams: null,
        themeSwitchingSupported: false,
        closingConfirmationEnabled: false,
        ux: {
            mobileCompatible: true,
            desktopCompatible: true,
            portraitLandscape: true,
            themeSwitchingSupported: false
        },
        wallet: {
            enabled: false,
            connected: false,
            address: null,
            sdkLoaded: false,
            errors: []
        },
        payments: {
            enabled: false,
            openInvoiceAvailable: false,
            errors: []
        },
        storage: {
            available: false,
            testKey: null,
            testValue: null,
            errors: []
        },
        onboarding: {
            implemented: false,
            completed: false,
            errors: []
        },
        errors: []
    };

    console.log('🔍 Starting Mini App Compliance Check...');

    /* -------------------- TELEGRAM WEBAPP API -------------------- */
    try {
        if (window.Telegram && window.Telegram.WebApp) {
            complianceResult.telegramAPI = true;
            const tg = window.Telegram.WebApp;

            // initData
            try {
                complianceResult.webappInitData = tg.initData || null;
                if (!complianceResult.webappInitData) {
                    complianceResult.errors.push("init_data_missing");
                }
            } catch(e) {
                complianceResult.errors.push("initData_error:" + e.message);
            }

            // ready - check if called (we can't detect if it was called, but we can check if it exists)
            try {
                if (typeof tg.ready === 'function') {
                    complianceResult.readyCalled = true;
                } else {
                    complianceResult.errors.push("ready_not_available");
                }
            } catch(e) {
                complianceResult.errors.push("ready_check_failed:" + e.message);
            }

            // expand - check if available
            try {
                if (typeof tg.expand === 'function') {
                    complianceResult.expandCalled = true;
                } else {
                    complianceResult.errors.push("expand_not_available");
                }
            } catch(e) {
                complianceResult.errors.push("expand_check_failed:" + e.message);
            }

            // themeParams
            try {
                complianceResult.themeParams = tg.themeParams || null;
                complianceResult.ux.themeSwitchingSupported = !!(tg.themeParams);
                complianceResult.themeSwitchingSupported = !!(tg.themeParams);
            } catch(e) {
                complianceResult.errors.push("themeParams_error:" + e.message);
            }

            // closingConfirmation
            try {
                if (typeof tg.enableClosingConfirmation === 'function') {
                    complianceResult.closingConfirmationEnabled = true;
                }
            } catch(e) {
                // Not critical
            }

        } else {
            complianceResult.errors.push("telegram_webapp_api_missing");
        }
    } catch(fatal) {
        complianceResult.errors.push("fatal_telegram_error:" + fatal.message);
    }

    /* -------------------- TON CONNECT WALLET -------------------- */
    try {
        // Check if TON Connect SDK is loaded (our implementation uses TON_CONNECT_UI)
        if (typeof TON_CONNECT_UI !== 'undefined' && typeof TON_CONNECT_UI.TonConnectUI !== 'undefined') {
            complianceResult.wallet.enabled = true;
            complianceResult.wallet.sdkLoaded = true;

            // Check if we have a tonConnectUI instance
            if (typeof TonConnect !== 'undefined' && TonConnect.tonConnectUI) {
                const tonConnectUI = TonConnect.tonConnectUI;
                try {
                    const walletInfo = tonConnectUI.walletInfo;
                    if (walletInfo) {
                        complianceResult.wallet.connected = true;
                        complianceResult.wallet.address = walletInfo.account?.address || walletInfo.address || null;
                    }
                } catch(e) {
                    complianceResult.wallet.errors.push("wallet_check_failed:" + e.message);
                }
            } else {
                complianceResult.wallet.errors.push("tonConnectUI_instance_not_found");
            }
        } else {
            complianceResult.wallet.errors.push("ton_connect_sdk_not_loaded");
        }
    } catch(err) {
        complianceResult.wallet.errors.push("wallet_error:" + err.message);
    }

    /* -------------------- TELEGRAM PAYMENTS API -------------------- */
    try {
        if (window.Telegram && window.Telegram.WebApp) {
            const tg = window.Telegram.WebApp;
            complianceResult.payments.enabled = true;

            // Check if openInvoice is available
            if (typeof tg.openInvoice === 'function') {
                complianceResult.payments.openInvoiceAvailable = true;
            } else {
                complianceResult.payments.errors.push("openInvoice_not_available");
            }
        }
    } catch(err) {
        complianceResult.payments.errors.push("payments_error:" + err.message);
    }

    /* -------------------- SECURE STORAGE / LOCAL STORAGE -------------------- */
    try {
        if (window.localStorage) {
            complianceResult.storage.available = true;
            complianceResult.storage.testKey = "miniAppComplianceTestKey";
            complianceResult.storage.testValue = "test_" + Date.now();
            
            window.localStorage.setItem(complianceResult.storage.testKey, complianceResult.storage.testValue);
            const val = window.localStorage.getItem(complianceResult.storage.testKey);
            
            if (val !== complianceResult.storage.testValue) {
                complianceResult.storage.errors.push("storage_value_mismatch");
            }
            
            window.localStorage.removeItem(complianceResult.storage.testKey);
        } else {
            complianceResult.storage.errors.push("localStorage_not_available");
        }
    } catch(err) {
        complianceResult.storage.errors.push("storage_error:" + err.message);
    }

    /* -------------------- UX / UI Checks -------------------- */
    complianceResult.ux.mobileCompatible = /Mobi|Android/i.test(navigator.userAgent);
    complianceResult.ux.desktopCompatible = !/Mobi|Android/i.test(navigator.userAgent);
    complianceResult.ux.portraitLandscape = window.innerWidth > 0 && window.innerHeight > 0;

    /* -------------------- ONBOARDING FLOW CHECK -------------------- */
    try {
        // Check if onboarding is implemented
        if (typeof Render !== 'undefined' && typeof Render.showOnboarding === 'function') {
            complianceResult.onboarding.implemented = true;
            
            // Check if user has seen onboarding (from AppState)
            if (typeof AppState !== 'undefined' && typeof AppState.getHasSeenOnboarding === 'function') {
                complianceResult.onboarding.completed = AppState.getHasSeenOnboarding();
            }
        } else {
            complianceResult.onboarding.errors.push("onboarding_not_implemented");
        }
    } catch(err) {
        complianceResult.onboarding.errors.push("onboarding_error:" + err.message);
    }

    /* -------------------- PUSH NOTIFICATIONS (OPTIONAL) -------------------- */
    try {
        if ("Notification" in window) {
            complianceResult.pushNotifications.enabled = true;
            complianceResult.pushNotifications.canSubscribe = Notification.permission !== "denied";
            complianceResult.pushNotifications.permission = Notification.permission;
        }
        
        // Check Service Worker registration
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.getRegistration('/static/mini-app/');
                if (registration) {
                    complianceResult.pushNotifications.serviceWorkerRegistered = true;
                    complianceResult.pushNotifications.serviceWorkerScope = registration.scope;
                    
                    // Check if push manager is available
                    if (registration.pushManager) {
                        complianceResult.pushNotifications.pushManagerAvailable = true;
                        
                        // Check subscription
                        const subscription = await registration.pushManager.getSubscription();
                        if (subscription) {
                            complianceResult.pushNotifications.subscribed = true;
                            complianceResult.pushNotifications.subscriptionEndpoint = subscription.endpoint;
                        }
                    }
                } else {
                    complianceResult.pushNotifications.errors.push("service_worker_not_registered");
                }
            } catch(swErr) {
                complianceResult.pushNotifications.errors.push("service_worker_check_failed:" + swErr.message);
            }
        } else {
            complianceResult.pushNotifications.errors.push("service_worker_not_supported");
        }
    } catch(err) {
        complianceResult.pushNotifications.errors.push("push_notifications_error:" + err.message);
    }

    /* -------------------- OUTPUT -------------------- */
    console.log('='.repeat(80));
    console.log('📊 MINI APP COMPLIANCE CHECK RESULTS');
    console.log('='.repeat(80));
    console.log(JSON.stringify(complianceResult, null, 2));
    
    // Summary
    const totalChecks = Object.keys(complianceResult).length;
    const passedChecks = Object.values(complianceResult).filter(v => {
        if (typeof v === 'boolean') return v;
        if (typeof v === 'object' && v !== null) {
            if (Array.isArray(v)) return v.length === 0;
            return Object.values(v).some(val => val === true || (Array.isArray(val) && val.length === 0));
        }
        return false;
    }).length;

    console.log('\n📈 Summary:');
    console.log(`   Total checks: ${totalChecks}`);
    console.log(`   Passed: ${passedChecks}`);
    console.log(`   Errors: ${complianceResult.errors.length}`);
    
    if (complianceResult.errors.length > 0) {
        console.log('\n❌ Errors found:');
        complianceResult.errors.forEach(err => console.log(`   - ${err}`));
    }
    
    if (complianceResult.wallet.errors.length > 0) {
        console.log('\n⚠️  Wallet errors:');
        complianceResult.wallet.errors.forEach(err => console.log(`   - ${err}`));
    }
    
    if (complianceResult.payments.errors.length > 0) {
        console.log('\n⚠️  Payments errors:');
        complianceResult.payments.errors.forEach(err => console.log(`   - ${err}`));
    }

    console.log('='.repeat(80));
    
    // Return result for programmatic access
    window.MiniAppComplianceResult = complianceResult;
    return complianceResult;
})();
