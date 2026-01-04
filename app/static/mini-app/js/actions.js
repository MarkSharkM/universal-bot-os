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
    
    // Use Telegram WebApp API: openLink for all links (best practice)
    // openLink opens in browser within Telegram context, doesn't close Mini App
    // openTelegramLink would redirect to Telegram app and close Mini App
    // For t.me links, use openLink (not openTelegramLink) to keep user in Mini App context
    const tg = AppState.getTg();
    if (tg?.openLink) {
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
    
    // Use openLink to open share dialog in browser, keep user in Mini App context
    const tg = AppState.getTg();
    if (tg?.openLink) {
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

function handleBuyTop(price) {
    if (!AppState.getAppData() || !AppState.getBotId()) return;
    
    // Show confirmation modal
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
}

function openTelegramBot() {
    // Get bot username from config or use default
    const botName = AppState.getAppData()?.config?.name || 'EarnHubAggregatorBot';
    // Remove @ if present and extract username if it's a full URL
    let cleanBotName = botName.replace('@', '').trim();
    // If it's a full URL, extract username
    if (cleanBotName.includes('t.me/')) {
        cleanBotName = cleanBotName.split('t.me/')[1].split('/')[0];
    }
    const botUrl = `https://t.me/${cleanBotName}`;
    
    // Use openLink (not openTelegramLink) to open in browser, keep user in Mini App context
    const tg = AppState.getTg();
    if (tg?.openLink) {
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
    
    // Get instructions from translations or use default
    const instructions = translations.block2_enable_steps || 
        `1️⃣ Відкрий @HubAggregatorBot
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
