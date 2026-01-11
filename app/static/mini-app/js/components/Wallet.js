/**
 * Wallet Component
 * Handles wallet connection (TON Connect + Manual fallback) and UI.
 */

window.Components = window.Components || {};

window.Components.Wallet = {
    /**
     * Show Wallet Modal (TON Connect Style)
     */
    showModal() {
        const modal = document.getElementById('wallet-modal');
        if (!modal) return;

        if (window.trackEvent) trackEvent('wallet_modal_opened');
        modal.style.display = 'flex';

        // Haptic feedback
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
        }

        // Setup close button
        const closeBtn = document.getElementById('wallet-modal-close');
        if (closeBtn) {
            // Remove old listener
            const newCloseBtn = closeBtn.cloneNode(true);
            closeBtn.parentNode.replaceChild(newCloseBtn, closeBtn);
            newCloseBtn.onclick = () => {
                modal.style.display = 'none';
                if (window.Telegram?.WebApp?.HapticFeedback) {
                    window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
                }
            };
        }

        // Setup Telegram Wallet button (primary)
        const telegramBtn = document.getElementById('wallet-connect-telegram');
        if (telegramBtn) {
            telegramBtn.onclick = () => {
                this.connectTelegramWallet();
            };
        }

        // Setup wallet options (Tonkeeper, etc)
        const walletOptions = modal.querySelectorAll('.wallet-option');
        walletOptions.forEach(option => {
            option.onclick = () => {
                const wallet = option.getAttribute('data-wallet');
                if (wallet === 'view-all') {
                    // Show all wallets (fallback to manual input for now)
                    this.showManualInput();
                } else {
                    this.connectExternalWallet(wallet);
                }
            };
        });

        if (helpBtn) {
            helpBtn.onclick = () => {
                const tg = AppState.getTg();
                if (tg && tg.showAlert) {
                    const t = AppState.getAppData()?.translations || {};
                    tg.showAlert(t.ton_connect_help || 'TON Connect — це офіційний протокол для підключення TON гаманців у Telegram Mini Apps. Він дозволяє безпечно підключати гаманці без передачі приватних ключів.');
                }
            };
        }

        // Close on overlay click
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        };
    },

    /**
     * Connect Telegram Wallet (native integration via TON Connect)
     */
    async connectTelegramWallet() {
        // Use TON Connect SDK if available
        if (typeof TonConnect !== 'undefined' && TonConnect.connectTelegramWallet) {
            TonConnect.connectTelegramWallet();
        } else {
            // Fallback to manual input
            this.showManualInput();
        }
    },

    /**
     * Connect External Wallet (Tonkeeper, MyTonWallet, Tonhub via TON Connect)
     */
    connectExternalWallet(walletName) {
        // Use TON Connect SDK if available
        if (typeof TonConnect !== 'undefined' && TonConnect.connectExternalWallet) {
            TonConnect.connectExternalWallet(walletName);
        } else {
            // Fallback to manual input
            this.showManualInput();
        }
    },

    /**
     * Show Manual Wallet Input (fallback)
     */
    showManualInput() {
        const tonConnectModal = document.getElementById('wallet-modal');
        const manualModal = document.getElementById('wallet-manual-modal');

        if (tonConnectModal) tonConnectModal.style.display = 'none';
        if (!manualModal) return;

        manualModal.style.display = 'flex';

        // Setup form submit
        const form = document.getElementById('wallet-modal-form');
        const input = document.getElementById('wallet-modal-input');
        const closeBtn = document.getElementById('wallet-manual-close');

        if (form) {
            form.onsubmit = async (e) => {
                e.preventDefault();
                const walletAddress = input.value.trim();

                if (!walletAddress) {
                    const t = AppState.getAppData()?.translations || {};
                    if (typeof Toast !== 'undefined') {
                        Toast.error(t.enter_wallet_error || 'Введіть адресу гаманця');
                    }
                    return;
                }

                // Validate format
                const walletPattern = /^(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_-]{46,48}$/;
                if (!walletPattern.test(walletAddress)) {
                    const t = AppState.getAppData()?.translations || {};
                    if (typeof Toast !== 'undefined') {
                        Toast.error(t.invalid_wallet_format || 'Невірний формат адреси гаманця');
                    }
                    return;
                }

                try {
                    if (window.trackEvent) trackEvent('wallet_added', { method: 'manual' });

                    const botId = AppState.getBotId();
                    const initData = AppState.getTg()?.initData || null;

                    if (botId && typeof Api !== 'undefined' && Api.saveWallet) {
                        await Api.saveWallet(botId, walletAddress, AppState.getUserId(), initData);

                        // Update app data
                        const appData = AppState.getAppData();
                        if (appData && appData.user) {
                            appData.user.wallet = walletAddress;
                            AppState.setAppData(appData);
                        }

                        // Hide modal and banner
                        manualModal.style.display = 'none';
                        this.renderBanner(); // Re-render logic

                        const t = AppState.getAppData()?.translations || {};
                        if (typeof Toast !== 'undefined') {
                            Toast.success(t.wallet_saved_success || '✅ Гаманець збережено успішно!');
                        }
                        if (window.Telegram?.WebApp?.HapticFeedback) {
                            window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
                        }

                        // Force header re-render to show updated wallet
                        if (window.Components.Header && typeof window.Components.Header.render === 'function') {
                            // This might be tricky if Header isn't re-rendering the whole thing
                            // simpler: reload OR trigger an event that the header listens to.
                            // For now assuming app re-renders or next nav.
                        }
                    }
                } catch (error) {
                    console.error('Error saving wallet:', error);
                    const t = AppState.getAppData()?.translations || {};
                    if (typeof Toast !== 'undefined') {
                        Toast.error((t.wallet_save_error || '❌ Помилка збереження: ') + (error.message || 'Невідома помилка'));
                    }
                    if (window.Telegram?.WebApp?.HapticFeedback) {
                        window.Telegram.WebApp.HapticFeedback.notificationOccurred('error');
                    }
                }
            };
        }

        if (closeBtn) {
            // Remove old listener
            const newCloseBtn = closeBtn.cloneNode(true);
            closeBtn.parentNode.replaceChild(newCloseBtn, closeBtn);
            newCloseBtn.onclick = () => {
                manualModal.style.display = 'none';
                if (window.Telegram?.WebApp?.HapticFeedback) {
                    window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
                }
            };
        }

        // Close on overlay click
        manualModal.onclick = (e) => {
            if (e.target === manualModal) {
                manualModal.style.display = 'none';
            }
        };
    },

    /**
     * Render Wallet Banner (contextual layer, shown if wallet not connected)
     */
    renderBanner() {
        const banner = document.getElementById('wallet-banner');
        if (!banner) return;

        const appData = AppState.getAppData();
        const wallet = appData?.user?.wallet || '';
        const walletTrimmed = wallet ? wallet.trim() : '';

        // Show banner only if wallet is not connected
        if (!walletTrimmed || walletTrimmed.length < 20) {
            banner.style.display = 'block';

            // Setup button click
            const btn = document.getElementById('wallet-banner-btn');
            if (btn && !btn.hasAttribute('data-listener')) {
                const t = AppState.getAppData()?.translations || {};
                btn.textContent = t.connect || 'Підключити';
                btn.setAttribute('data-listener', 'true');
                btn.addEventListener('click', () => {
                    if (window.trackEvent) trackEvent('wallet_banner_clicked');
                    this.showModal();
                });
            }
        } else {
            banner.style.display = 'none';
        }

        // Update banner text if needed
        const bannerText = banner.querySelector('p');
        const t = AppState.getAppData()?.translations || {};
        if (bannerText) {
            bannerText.textContent = t.wallet_banner_text || 'Підключи гаманець → зможеш виводити';
        }
    }
};

// Export to global scope for backward compatibility during refactor
window.showWalletModal = () => window.Components.Wallet.showModal();
window.connectTelegramWallet = () => window.Components.Wallet.connectTelegramWallet();
window.connectExternalWallet = (n) => window.Components.Wallet.connectExternalWallet(n);
window.showManualWalletInput = () => window.Components.Wallet.showManualInput();
window.renderWalletBanner = () => window.Components.Wallet.renderBanner();
