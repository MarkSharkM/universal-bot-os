/**
 * Actions Module
 * User actions: opening links, wallet, sharing, etc.
 */

function openPartner(referralLink, partnerId) {
    if (!referralLink || !referralLink.trim()) {
        console.warn('Referral link is empty');
        const msg = AppState.getAppData()?.translations?.link_missing || 'Реферальна лінка відсутня';
        if (typeof Toast !== 'undefined') {
            Toast.error(msg);
        } else if (AppState.getTg()?.showAlert) {
            AppState.getTg().showAlert(msg);
        }
        return;
    }

    // Log partner click (Analytics for Charts)
    if (typeof trackEvent === 'function') {
        trackEvent('partner_click_direct', { partner_id: partnerId || null });
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
        const msg = AppState.getAppData()?.translations?.enter_wallet_error || 'Введіть адресу гаманця';
        showWalletMessage(msg, 'error');
        return;
    }

    // Simplified wallet submit logic for now
    try {
        const botId = AppState.getBotId();
        // Placeholder for wallet submission logic
        console.log('Wallet address submitted:', walletAddress);

        if (typeof Toast !== 'undefined') {
            Toast.success('Wallet saved (Simulation)');
        }
        if (typeof trackEvent === 'function') {
            trackEvent('wallet_simulation_success', { address: walletAddress });
        }

        // Update local state
        const appData = AppState.getAppData();
        if (appData && appData.user) {
            appData.user.wallet = walletAddress;
            AppState.setAppData(appData);
        }
    } catch (e) {
        console.error(e);
    }
}

async function saveTgrLink() {
    const input = document.getElementById('tgr-link-input');
    if (!input) return;

    const link = input.value.trim();
    if (!link) {
        if (typeof Toast !== 'undefined') Toast.error('Введіть посилання');
        return;
    }

    // Strict validation for _tgr_
    if (!link.includes('_tgr_')) {
        const msg = AppState.getAppData()?.translations?.invalid_tgr_link || 'Це не схоже на партнерське посилання (шукаю код _tgr_)';
        if (typeof Toast !== 'undefined') Toast.error(msg);
        return;
    }

    const botId = AppState.getBotId();
    if (!botId) return;

    try {
        const translations = AppState.getAppData()?.translations || {};
        if (typeof Toast !== 'undefined') Toast.info(translations.saving || 'Збереження...');
        if (typeof trackEvent === 'function') trackEvent('tgr_link_save_attempt');

        const initData = AppState.getTg()?.initData || '';
        const response = await fetch(`${API_BASE}/api/v1/mini-apps/mini-app/${botId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'save_custom_data',
                custom_data: { tgr_link: link }
            })
        });

        const data = await response.json();

        if (data.ok) {
            const translations = AppState.getAppData()?.translations || {};
            if (typeof Toast !== 'undefined') Toast.success(translations.tgr_link_updated || '✅ Лінку оновлено! Тепер кнопки поширюють твою 7% лінку.');
            if (typeof trackEvent === 'function') trackEvent('tgr_link_save_success');
            // Update local state
            AppState.setTgrLink(link);

            // Re-render home to show active status
            if (typeof Render !== 'undefined' && Render.renderHome) {
                Render.renderHome();
            }
        } else {
            throw new Error(data.error || 'Failed to save');
        }

    } catch (e) {
        console.error(e);
        if (typeof Toast !== 'undefined') Toast.error('Помилка збереження');
    }
}

function openBotForLink() {
    // Open bot with specific param to help user get link
    const botUsername = AppState.getAppData()?.config?.username;
    if (botUsername) {
        const tg = AppState.getTg();
        const url = `https://t.me/${botUsername}?start=earnings`;
        if (typeof trackEvent === 'function') trackEvent('open_bot_for_link');
        if (tg && tg.openTelegramLink) tg.openTelegramLink(url);
        else window.open(url, '_blank');
    } else {
        const msg = AppState.getAppData()?.translations?.open_bot_manual || 'Відкрийте бота і натисніть /start';
        if (typeof Toast !== 'undefined') Toast.info(msg);
    }
}



/**
 * Save manual wallet input
 */
async function saveManualWallet() {
    const input = document.getElementById('wallet-modal-input');
    if (!input) return;
    const walletAddress = input.value.trim();

    // Validate format
    const walletPattern = /^(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_-]{46,48}$/;
    if (!walletPattern.test(walletAddress)) {
        showWalletMessage(AppState.getAppData()?.translations?.invalid_wallet || 'Невірний формат адреси гаманця', 'error');
        return;
    }

    // Validate AppState.getBotId() before making request
    if (!AppState.getBotId()) {
        showWalletMessage(AppState.getAppData()?.translations?.bot_id_missing || 'Помилка: Bot ID не знайдено', 'error');
        return;
    }

    try {
        const translations = AppState.getAppData()?.translations || {};
        showWalletMessage(translations.saving || 'Збереження...', 'info');
        if (typeof trackEvent === 'function') trackEvent('wallet_manual_save_attempt');

        const initData = AppState.getTg()?.initData || null;
        const result = await saveWallet(AppState.getBotId(), walletAddress, AppState.getUserId(), initData);

        if (result && result.ok !== false) {
            // Show toast notification
            const successMsg = AppState.getAppData()?.translations?.wallet_saved_success || '✅ Гаманець збережено успішно!';
            if (typeof trackEvent === 'function') trackEvent('wallet_manual_save_success');
            if (typeof Toast !== 'undefined') {
                Toast.success(successMsg);
            }
            if (typeof Haptic !== 'undefined') {
                Haptic.success();
            }

            showWalletMessage(successMsg, 'success');

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
        const fullErrorMsg = (AppState.getAppData()?.translations?.save_error || '❌ Помилка збереження: ') + errorMsg;
        if (typeof Toast !== 'undefined') {
            Toast.error(fullErrorMsg);
        }
        if (typeof Haptic !== 'undefined') {
            Haptic.error();
        }
        if (typeof Render !== 'undefined' && Render.showWalletMessage) {
            Render.showWalletMessage(fullErrorMsg, 'error');
        } else {
            showWalletMessage(fullErrorMsg, 'error');
        }
    }
}

function copyReferralLink() {
    if (!AppState.getAppData() || !AppState.getAppData().user || !AppState.getAppData().user.referral_link) {
        const msg = AppState.getAppData()?.translations?.link_missing || 'Реферальна лінка відсутня';
        if (typeof Toast !== 'undefined') {
            Toast.error(msg);
        } else if (AppState.getTg()?.showAlert) {
            AppState.getTg().showAlert(msg);
        }
        return;
    }

    const link = AppState.getAppData().user.referral_link;

    // Try modern clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(link).then(() => {
            if (typeof trackEvent === 'function') trackEvent('referral_link_copy');
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

async function shareReferralLink() {
    // HYBRID LINK SYSTEM
    // 1. Check if user is TOP and has saved TGR link
    const tgrLink = AppState.getTgrLink() || AppState.getAppData()?.user?.custom_data?.tgr_link;
    const isTop = AppState.getReferralCount() >= 5 || !AppState.getTopLocked();

    let linkToShare;

    if (isTop && tgrLink) {
        // Share TGR Link (Direct Revenue)
        // Extract simple link if user pasted full text
        const match = tgrLink.match(/(https:\/\/t\.me\/[a-zA-Z0-9_]+(?:\?start=|\?startapp=)[a-zA-Z0-9_]+)/);
        linkToShare = match ? match[1] : tgrLink;
    } else {
        // Share Internal Link (Quest Progress)
        const botUsername = AppState.getAppData()?.config?.username;
        const userId = AppState.getUserId();
        if (!botUsername || !userId) {
            const msg = 'Помилка: Не знайдено username бота або userID';
            if (typeof Toast !== 'undefined') Toast.error(msg);
            return;
        }
        linkToShare = `https://t.me/${botUsername}?start=${userId}`;
    }

    const translations = AppState.getAppData()?.translations || {};
    const textPro = translations.share_text_pro || "🔥 Join me & Earn 7% RevShare!";
    const textStarter = translations.share_text_starter || "Look! I'm earning on Telegram with this bot 🚀";
    const text = isTop ? textPro : textStarter;
    const url = `https://t.me/share/url?url=${encodeURIComponent(linkToShare)}&text=${encodeURIComponent(text)}`;

    if (typeof trackEvent === 'function') trackEvent('referral_link_share', { type: isTop ? 'pro' : 'starter' });

    const tg = AppState.getTg();
    if (tg && tg.openTelegramLink) {
        tg.openTelegramLink(url);
    } else {
        window.open(url, '_blank');
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
        const appData = AppState.getAppData() || {};
        const translations = appData.translations || {};
        const title = translations.buy_top_fallback_title || 'Розблокувати TOP';
        const needed = appData.earnings?.invites_needed || 0;
        let text = translations.buy_top_fallback_text || "Для розблокування TOP потрібно:\n• Запросити {{needed}} друзів\n• Або купити доступ за {{price}} ⭐\nДля покупки відкрийте бота та натисніть кнопку \"Розблокувати TOP\"";

        text = text.replace('{{needed}}', needed).replace('{{price}}', price);

        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>${title}</h2>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="instructions-text">
                        ${text.split('\n').map(line => `<p>${line}</p>`).join('')}
                    </div>
                    <div class="modal-actions">
                        <button class="action-btn primary" onclick="openTelegramBot(); this.closest('.modal-overlay').remove();">
                            ${translations.open_bot || 'Відкрити бота'}
                        </button>
                        <button class="action-btn secondary" onclick="this.closest('.modal-overlay').remove()">
                            ${translations.cancel || 'Закрити'}
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
        const translations = AppState.getAppData()?.translations || {};
        // Show loading state
        if (typeof Toast !== 'undefined') {
            Toast.info(translations.creating_invoice || 'Створюємо рахунок...');
        }
        if (typeof trackEvent === 'function') trackEvent('top_purchase_attempt', { price });
        if (typeof Haptic !== 'undefined') {
            Haptic.light();
        }

        // Create invoice link via backend
        const invoiceLink = await Api.createInvoiceLink(botId, initData, userId);

        // Open invoice in Mini App (stays in Mini App, no browser redirect)
        tg.openInvoice(invoiceLink, (status) => {
            console.log('Payment callback received, status:', status);
            if (status === 'paid') {
                const translations = AppState.getAppData()?.translations || {};
                // Payment successful
                console.log('✅ Payment successful, updating UI...');
                if (typeof Toast !== 'undefined') {
                    Toast.success(translations.top_unlocked || '✅ TOP розблоковано!');
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
                const translations = AppState.getAppData()?.translations || {};
                // Payment failed or cancelled
                if (typeof Toast !== 'undefined') {
                    Toast.warning(translations.payment_cancelled || 'Оплата скасована');
                }
                if (typeof Haptic !== 'undefined') {
                    Haptic.error();
                }

                // Track event
                trackEvent('top_purchase_cancelled');
            }
        });
    } catch (error) {
        const translations = AppState.getAppData()?.translations || {};
        console.error('Error creating invoice link:', error);

        // Show error and fallback to bot
        if (typeof Toast !== 'undefined') {
            Toast.error(translations.payment_error || 'Помилка створення рахунку. Спробуйте через бота.');
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
    const botUrl = typeof getBotUrl === 'function' ? getBotUrl() : null;

    if (!botUrl) {
        console.error('❌ Bot URL not found. Please sync username via API.');
        return;
    }

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



function validateTgrInput(input) {
    const btn = document.getElementById('tgr-save-btn');
    const helper = document.getElementById('tgr-input-helper');
    if (!btn) return;

    const val = input.value.trim();

    // Basic validation
    if (val.length > 5 && (val.includes('t.me') || val.includes('_tgr_'))) {
        btn.disabled = false;
        btn.classList.remove('disabled');
        if (helper) helper.style.display = 'none';
    } else {
        btn.disabled = true;
        btn.classList.add('disabled');
        // Optional: show helper only if typed something invalid
        if (val.length > 0 && helper) {
            helper.textContent = 'Link must contain t.me or _tgr_';
            helper.style.display = 'block';
            helper.style.color = '#ff4d4d'; // Red warning
        } else if (helper) {
            helper.style.display = 'none';
        }
    }
}

function editTgrLink() {
    // Clear local state only for UI purposes
    // We don't delete from backend immediately to avoid accidental loss
    // We just re-render Hero in "edit mode" (savedLink = null)

    const appData = AppState.getAppData();
    // Trick: we temporarily stash the real link but clear view
    // Ideally we would have a separate 'isEditing' state, 
    // but clearing the TGR link in AppState works for now:
    AppState.setTgrLink(null);

    if (typeof Render !== 'undefined' && Render.renderHome) {
        Render.renderHome();
        // Focus the input? NO, per strict rules: "User controls focus"
        // But we can show a toast
        if (typeof Toast !== 'undefined') Toast.info('Edit mode: Paste your new link');
    }
}

function showActivate7Instructions() {
    const appData = AppState.getAppData();
    const earnings = appData.earnings || {};
    const translations = appData.translations || {};
    const commissionPercent = Math.round((earnings.commission_rate || 0.07) * 100);
    const botUsername = typeof getBotUsername === 'function' ? getBotUsername() : null;

    if (!botUsername) {
        console.error('Bot username missing');
        return;
    }

    const title = translations.activate_7_title || `Як увімкнути ${commissionPercent}% (1 раз назавжди):`;
    let instructions = `${translations.activate_7_step_1 || '1️⃣ Відкрий @{{username}}'}\n${translations.activate_7_step_2 || '2️⃣ «Партнерська програма»'}\n${translations.activate_7_step_3 || '3️⃣ «Під\'єднатись»'}\n${translations.activate_7_footer || '→ {{percent}}% активуються назавжди'}`;

    instructions = instructions
        .replace('{{username}}', botUsername)
        .replace('{{percent}}', commissionPercent);

    // IMPORTANT NOTE per Senior QA rule:
    const note = translations.activate_7_note || '⚠️ Important: After connecting, tap "Open App" in chat to return here.';

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>${title}</h2>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
            </div>
            <div class="modal-body">
                <div class="instructions-text">
                    ${instructions.split('\n').map(line => `<p>${line}</p>`).join('')}
                    <div class="instruction-note" style="margin-top:12px; font-size:11px; color:#aaa; border-left: 2px solid #555; padding-left:8px;">
                        ${note}
                    </div>
                </div>
                <div class="modal-actions">
                    <button class="action-btn primary" onclick="Actions.activatePartnerAndReturn()">
                        ${translations.open_bot || 'Відкрити бота'}
                    </button>
                    <button class="action-btn secondary" onclick="this.closest('.modal-overlay').remove()">
                        ${translations.cancel || 'Скасувати'}
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

function showCopySuccess() {
    if (AppState.getTg()?.showAlert) {
        const msg = AppState.getAppData()?.translations?.link_copied || '✅ Лінк скопійовано!';
        if (typeof Toast !== 'undefined') {
            Toast.success(msg);
            if (typeof Haptic !== 'undefined') Haptic.success();
        } else if (AppState.getTg()?.showAlert) {
            AppState.getTg().showAlert(msg);
        }
    } else if (AppState.getTg()?.HapticFeedback?.impactOccurred) {
        // Haptic feedback if available
        AppState.getTg().HapticFeedback.impactOccurred('light');
    }

    // Visual feedback on button
    const copyBtn = document.querySelector('.copy-btn');
    if (copyBtn) {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = AppState.getAppData()?.translations?.copied || '✅ Скопійовано!';
        copyBtn.style.background = 'var(--success-color)';
        setTimeout(() => {
            copyBtn.textContent = originalText;
            copyBtn.style.background = '';
        }, 2000);
    }
}



async function activatePartnerAndReturn() {
    const botId = AppState.getBotId();
    const tg = AppState.getTg();
    const initData = tg?.initData || null;

    if (!botId) {
        console.error('❌ Bot ID not found');
        return;
    }

    try {
        // 1. Notify backend to send return message
        if (typeof Api !== 'undefined' && Api.notifyReturn) {
            await Api.notifyReturn(botId, initData);
        }

        // 2. Track event
        if (typeof trackEvent === 'function') {
            trackEvent('activate_partner_return_start');
        }

        // 3. Get bot username for profile link
        const botUsername = typeof getBotUsername === 'function' ? getBotUsername() : null;

        if (botUsername && tg?.openTelegramLink) {
            // 4. Open bot profile
            tg.openTelegramLink(`https://t.me/${botUsername}?profile`);

            // 5. Close Mini App
            if (tg.close) {
                // Slight delay to ensure openTelegramLink starts
                setTimeout(() => {
                    tg.close();
                }, 100);
            }
        } else {
            // Fallback: just close or show bot
            if (typeof openTelegramBot === 'function') {
                openTelegramBot();
            }
            if (tg?.close) tg.close();
        }
    } catch (error) {
        console.error('Error in activatePartnerAndReturn:', error);
        // Even if API fails, try to open bot and close
        if (typeof openTelegramBot === 'function') {
            openTelegramBot();
        }
        if (tg?.close) tg.close();
    }
}

window.Actions = {
    openPartner,
    handleWalletSubmit,
    saveManualWallet,
    copyReferralLink,
    shareReferralLink,
    handleBuyTop,
    openTelegramBot,
    saveTgrLink,
    openBotForLink,
    saveManualWallet,
    validateTgrInput,
    editTgrLink,
    showActivate7Instructions,
    activatePartnerAndReturn,
    fallbackCopyText,
    showCopySuccess,
    showCopySuccess

};
// Developer Tools
window.toggleDevMode = function (mode) {
    if (mode === 'top') {
        console.log('⚡️ Switching to TOP Mode');
        AppState.setReferralCount(10);
        AppState.setTopLocked(false);
    } else {
        console.log('🌱 Switching to Starter Mode');
        AppState.setReferralCount(2);
        AppState.setTopLocked(true);
        AppState.setTgrLink(null); // Clear link to test input
    }
    if (typeof Render !== 'undefined') Render.renderHome();
    return "Done";
};

