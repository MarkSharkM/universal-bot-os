/**
 * Actions Module
 * User actions: opening links, wallet, sharing, etc.
 */

function openPartner(referralLink, partnerId) {
    if (!referralLink || !referralLink.trim()) {
        console.warn('Referral link is empty');
        if (typeof Toast !== 'undefined') {
            Toast.error('Реферальна лінка відсутня');
        } else if (AppState.getTg()?.showAlert) {
            AppState.getTg().showAlert('Реферальна лінка відсутня');
        }
        return;
    }

    // Log partner click
    if (AppState.getBotId()) {
        const initData = AppState.getTg()?.initData || null;
        sendCallback(AppState.getBotId(), {
            action: 'partner_click',
            partner_id: partnerId || null
        }, initData).catch(err => console.error('Error logging partner click:', err));
    }

    // Use correct Telegram WebApp API method based on link type
    // For t.me links: use openTelegramLink() to open in Telegram app
    // For external links: use openLink() to open in browser
    const tg = AppState.getTg();
    const isTelegramLink = referralLink && referralLink.startsWith('https://t.me/');

    if (isTelegramLink && tg?.openTelegramLink) {
        // Open Telegram link in Telegram app (not browser)
        tg.openTelegramLink(referralLink);
        // Explicitly close Mini App to prevent overlay issues on Web
        // Mobile usually handles this automatically, but Web might keep iframe open
        if (tg.close) tg.close();
    } else if (tg?.openLink) {
        // Open external link in browser
        tg.openLink(referralLink);
    } else {
        // Fallback: open in same window
        window.location.href = referralLink;
    }
}

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

    // Validate AppState.getBotId() before making request
    if (!AppState.getBotId()) {
        showWalletMessage('Помилка: Bot ID не знайдено', 'error');
        return;
    }

    try {
        showWalletMessage('Збереження...', 'info');

        const initData = AppState.getTg()?.initData || null;
        const result = await saveWallet(AppState.getBotId(), walletAddress, AppState.getUserId(), initData);

        if (result && result.ok !== false) {
            // Show toast notification
            if (typeof Toast !== 'undefined') {
                Toast.success('✅ Гаманець збережено успішно!');
            }
            if (typeof Haptic !== 'undefined') {
                Haptic.success();
            }

            showWalletMessage('✅ Гаманець збережено успішно!', 'success');

            // Update app data locally (no need to reload all data, just update wallet)
            const appData = AppState.getAppData();
            if (appData && appData.user) {
                appData.user.wallet = walletAddress;
                AppState.setAppData(appData);
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
        if (typeof Toast !== 'undefined') {
            Toast.error('❌ Помилка збереження: ' + errorMsg);
        }
        if (typeof Haptic !== 'undefined') {
            Haptic.error();
        }
        if (typeof Render !== 'undefined' && Render.showWalletMessage) {
            Render.showWalletMessage('❌ Помилка збереження: ' + errorMsg, 'error');
        } else {
            showWalletMessage('❌ Помилка збереження: ' + errorMsg, 'error');
        }
    }
}

function copyReferralLink() {
    if (!AppState.getAppData() || !AppState.getAppData().user || !AppState.getAppData().user.referral_link) {
        if (typeof Toast !== 'undefined') {
            Toast.error('Реферальна лінка відсутня');
        } else if (AppState.getTg()?.showAlert) {
            AppState.getTg().showAlert('Реферальна лінка відсутня');
        }
        return;
    }

    const link = AppState.getAppData().user.referral_link;

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

function shareReferralLink() {
    if (!AppState.getAppData() || !AppState.getAppData().user || !AppState.getAppData().user.referral_link) {
        if (typeof Toast !== 'undefined') {
            Toast.error('Реферальна лінка відсутня');
        } else if (AppState.getTg()?.showAlert) {
            AppState.getTg().showAlert('Реферальна лінка відсутня');
        }
        return;
    }

    const link = AppState.getAppData().user.referral_link;
    // Updated share text (Revenue Launcher approach - NO numbers, NO TON)
    const shareText = 'Я підʼєднався до партнерської програми Telegram. Це працює автоматично.';

    // Track share event
    if (AppState.getBotId()) {
        const initData = AppState.getTg()?.initData || null;
        if (typeof Api !== 'undefined' && Api.sendCallback) {
            Api.sendCallback(AppState.getBotId(), {
                type: 'analytics',
                event: 'share_sent',
                data: {}
            }, initData).catch(err => console.error('Error tracking share:', err));
        }
    }

    // Use Telegram share URL
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(shareText)}`;

    // Share URL is t.me/share/url - use openTelegramLink for Telegram links
    const tg = AppState.getTg();
    const isTelegramLink = shareUrl && shareUrl.startsWith('https://t.me/');

    if (isTelegramLink && tg?.openTelegramLink) {
        // Open Telegram share dialog in Telegram app
        tg.openTelegramLink(shareUrl);
    } else if (tg?.openLink) {
        // Fallback: open in browser
        tg.openLink(shareUrl);
    } else {
        // Fallback: open in same window
        window.location.href = shareUrl;
    }

    // Haptic feedback
    if (typeof Haptic !== 'undefined') {
        Haptic.medium();
    }
}

async function handleBuyTop(price) {
    if (!AppState.getAppData() || !AppState.getBotId()) return;

    const botId = AppState.getBotId();
    const tg = AppState.getTg();
    const initData = tg?.initData || null;
    const userId = AppState.getUserId();

    // Check if tg.openInvoice is available (Telegram WebApp API)
    if (!tg || !tg.openInvoice) {
        // Fallback: show modal with instructions
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
                        <p>• Запросити ${AppState.getAppData().earnings?.invites_needed || 0} друзів</p>
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
        return;
    }

    // Use Telegram Stars Payment API (openInvoice in Mini App)
    try {
        // Show loading state
        if (typeof Toast !== 'undefined') {
            Toast.info('Створюємо рахунок...');
        }
        if (typeof Haptic !== 'undefined') {
            Haptic.light();
        }

        // Create invoice link via backend
        const invoiceLink = await Api.createInvoiceLink(botId, initData, userId);

        // Open invoice in Mini App (stays in Mini App, no browser redirect)
        tg.openInvoice(invoiceLink, (status) => {
            console.log('Payment callback received, status:', status);
            if (status === 'paid') {
                // Payment successful
                console.log('✅ Payment successful, updating UI...');
                if (typeof Toast !== 'undefined') {
                    Toast.success('✅ TOP розблоковано!');
                }
                if (typeof Haptic !== 'undefined') {
                    Haptic.success();
                }

                // Track event
                trackEvent('top_purchase_success');

                // Reload app data to get updated TOP status
                if (typeof loadAppData === 'function') {
                    loadAppData(true).then(() => {
                        console.log('App data reloaded after payment, re-rendering...');
                        // Update AppState with new TOP status
                        const appData = AppState.getAppData();
                        if (appData && appData.user) {
                            const topStatus = appData.user.top_status || 'locked';
                            AppState.setTopLocked(topStatus === 'locked');
                            console.log('Updated TOP status in AppState:', topStatus);
                        }

                        // Re-render ALL components to show updated state
                        const currentPage = AppState.getCurrentPage() || 'home';
                        console.log('Current page:', currentPage);

                        // Always re-render home page (has Primary Action Card)
                        if (typeof Render !== 'undefined' && Render.renderHome) {
                            Render.renderHome();
                        } else if (typeof renderHome === 'function') {
                            renderHome();
                        }

                        // Re-render TOP page if we're on it
                        if (currentPage === 'top') {
                            if (typeof Render !== 'undefined' && Render.renderTop) {
                                Render.renderTop();
                            } else if (typeof renderTop === 'function') {
                                renderTop();
                            }
                        }

                        // Re-render Primary Action Card (shows on home page)
                        if (typeof Render !== 'undefined' && Render.renderPrimaryActionCard) {
                            Render.renderPrimaryActionCard();
                        }

                        console.log('✅ UI updated after payment');
                    }).catch(err => {
                        console.error('Error reloading app data after payment:', err);
                        // Force re-render even if loadAppData fails
                        if (typeof Render !== 'undefined' && Render.renderApp) {
                            Render.renderApp();
                        } else if (typeof renderApp === 'function') {
                            renderApp();
                        }
                    });
                } else {
                    console.warn('loadAppData function not available, forcing re-render');
                    // Fallback: force re-render
                    if (typeof Render !== 'undefined' && Render.renderApp) {
                        Render.renderApp();
                    } else if (typeof renderApp === 'function') {
                        renderApp();
                    }
                }
            } else if (status === 'failed' || status === 'cancelled') {
                // Payment failed or cancelled
                if (typeof Toast !== 'undefined') {
                    Toast.warning('Оплата скасована');
                }
                if (typeof Haptic !== 'undefined') {
                    Haptic.error();
                }

                // Track event
                trackEvent('top_purchase_cancelled');
            }
        });
    } catch (error) {
        console.error('Error creating invoice link:', error);

        // Show error and fallback to bot
        if (typeof Toast !== 'undefined') {
            Toast.error('Помилка створення рахунку. Спробуйте через бота.');
        }
        if (typeof Haptic !== 'undefined') {
            Haptic.error();
        }

        // Fallback: open bot
        openTelegramBot();
    }
}

function openTelegramBot() {
    // Get bot URL (universal for any bot)
    const botUrl = typeof getBotUrl === 'function' ? getBotUrl() : 'https://t.me/EarnHubAggregatorBot';

    // Use correct method: openTelegramLink for t.me links, openLink for external
    const tg = AppState.getTg();
    const isTelegramLink = botUrl && botUrl.startsWith('https://t.me/');

    if (isTelegramLink && tg?.openTelegramLink) {
        // Open bot URL in Telegram app
        tg.openTelegramLink(botUrl);
    } else if (tg?.openLink) {
        // Open external link in browser
        tg.openLink(botUrl);
    } else {
        // Fallback: open in same window
        window.location.href = botUrl;
    }
}

function showActivate7Instructions() {
    if (!AppState.getAppData() || !AppState.getAppData().earnings) return;

    const earnings = AppState.getAppData().earnings || {};
    const translations = earnings.translations || {};
    const commissionPercent = Math.round((earnings.commission_rate || 0.07) * 100);

    // Get bot username (universal for any bot)
    const botUsername = typeof getBotUsername === 'function' ? getBotUsername() : 'EarnHubAggregatorBot';

    // Get instructions from translations or use default
    const instructions = translations.block2_enable_steps ||
        `1️⃣ Відкрий @${botUsername}
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
        if (AppState.getTg()?.showAlert) {
            if (typeof Toast !== 'undefined') {
                Toast.error('Не вдалося скопіювати лінк');
            } else if (AppState.getTg()?.showAlert) {
                AppState.getTg().showAlert('Не вдалося скопіювати лінк');
            }
        }
    }

    document.body.removeChild(textArea);
}

function showCopySuccess() {
    if (AppState.getTg()?.showAlert) {
        if (typeof Toast !== 'undefined') {
            Toast.success('✅ Лінк скопійовано!');
            if (typeof Haptic !== 'undefined') Haptic.success();
        } else if (AppState.getTg()?.showAlert) {
            AppState.getTg().showAlert('✅ Лінк скопійовано!');
        }
    } else if (AppState.getTg()?.HapticFeedback?.impactOccurred) {
        // Haptic feedback if available
        AppState.getTg().HapticFeedback.impactOccurred('light');
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


window.Actions = {
    openPartner,
    handleWalletSubmit,
    copyReferralLink,
    shareReferralLink,
    handleBuyTop,
    openTelegramBot,
    showActivate7Instructions,
    fallbackCopyText,
    showCopySuccess
};
