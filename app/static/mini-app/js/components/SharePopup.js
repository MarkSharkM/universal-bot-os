/**
 * Share Popup Component
 * Handles the "Share Link" popup logic and trigger conditions.
 */

window.Components = window.Components || {};

window.Components.SharePopup = {
    /**
     * Show Share Auto-popup
     * Triggers: after start_7_flow, top_unlocked, 24h idle, 3 partner_click
     */
    show(trigger = 'manual') {
        const popup = document.getElementById('share-popup');
        if (!popup) return;

        // Track popup shown
        if (window.trackEvent) trackEvent('share_popup_shown', { trigger: trigger });

        // Show popup
        popup.style.display = 'flex';

        // Haptic feedback
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
        }

        // Setup buttons
        const shareBtn = document.getElementById('share-popup-share-btn');
        const closeBtn = document.getElementById('share-popup-close-btn');

        // Remove old listeners to avoid duplicates
        const newShareBtn = shareBtn ? shareBtn.cloneNode(true) : null;
        if (shareBtn && newShareBtn) {
            shareBtn.parentNode.replaceChild(newShareBtn, shareBtn);
            newShareBtn.onclick = () => {
                if (window.trackEvent) trackEvent('share_sent', { source: 'popup', trigger: trigger });

                if (typeof Actions !== 'undefined' && Actions.shareReferralLink) {
                    Actions.shareReferralLink();
                }

                popup.style.display = 'none';
                if (window.Telegram?.WebApp?.HapticFeedback) {
                    window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
                }
            };
        }

        const newCloseBtn = closeBtn ? closeBtn.cloneNode(true) : null;
        if (closeBtn && newCloseBtn) {
            closeBtn.parentNode.replaceChild(newCloseBtn, closeBtn);
            newCloseBtn.onclick = () => {
                popup.style.display = 'none';
                if (window.Telegram?.WebApp?.HapticFeedback) {
                    window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
                }
            };
        }

        // Close on overlay click
        popup.onclick = (e) => {
            if (e.target === popup) {
                popup.style.display = 'none';
            }
        };
    },

    /**
     * Check and trigger Share Auto-popup based on conditions
     * Implements STRICT ONE-TIME logic for milestones
     */
    checkTriggers() {
        const appData = AppState.getAppData();
        if (!appData) return;

        const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
        const now = Date.now();

        // Rate limiting: check last popup time (global spam prevention)
        const lastPopupTime = parseInt(storage.getItem('last_share_popup_time') || '0');
        const hoursSinceLastPopup = (now - lastPopupTime) / (1000 * 60 * 60);

        // Basic spam protection: Max 1 popup per 6 hours (unless manual)
        if (hoursSinceLastPopup < 6) {
            return;
        }

        // State Check
        const topLocked = AppState.getTopLocked();
        const lastActivity = parseInt(storage.getItem('last_activity') || '0');
        const partnerClickCount = parseInt(storage.getItem('partner_click_count') || '0');

        // --- TRIGGER 1: TOP Unlocked (Strict One-Time) ---
        // If user is unlocked AND has NEVER seen this popup before
        const hasShownTopPopup = storage.getItem('has_shown_top_popup') === 'true';

        if (!topLocked && !hasShownTopPopup) {
            console.log('[SharePopup] Triggering TOP Unlocked (First Time)');
            this.show('top_unlocked');

            // Mark as shown forever
            storage.setItem('has_shown_top_popup', 'true');
            storage.setItem('last_share_popup', 'top_unlocked');
            storage.setItem('last_share_popup_time', String(now));
            return;
        }

        // --- TRIGGER 2: 24h Idle (Recurring allowed, but respected 6h cooldown) ---
        if (lastActivity > 0) {
            const hoursSinceActivity = (now - lastActivity) / (1000 * 60 * 60);
            const lastSharePopup = storage.getItem('last_share_popup');

            if (hoursSinceActivity >= 24 && lastSharePopup !== '24h_idle') {
                console.log('[SharePopup] Triggering 24h Idle');
                this.show('24h_idle');

                storage.setItem('last_share_popup', '24h_idle');
                storage.setItem('last_share_popup_time', String(now));
                return;
            }
        }

        // --- TRIGGER 3: 3 Partner Clicks (Recurring allowed) ---
        // We use a separate flag to avoid spamming every click > 3
        const lastClickPopupCount = parseInt(storage.getItem('last_click_popup_count') || '0');

        if (partnerClickCount >= 3 && partnerClickCount > lastClickPopupCount) {
            console.log('[SharePopup] Triggering 3 Partner Clicks');
            this.show('3_partner_click');

            storage.setItem('last_click_popup_count', String(partnerClickCount)); // Don't show again until more clicks
            storage.setItem('last_share_popup', '3_partner_click');
            storage.setItem('last_share_popup_time', String(now));
            return;
        }
    },

    /**
     * Track partner clicks for auto-popup trigger
     */
    trackPartnerClick() {
        const storage = typeof SafeStorage !== 'undefined' ? SafeStorage : localStorage;
        const count = parseInt(storage.getItem('partner_click_count') || '0');
        storage.setItem('partner_click_count', String(count + 1));

        // Check triggers immediately after action
        this.checkTriggers();
    }
};

// Export to global scope for backward compatibility during refactor
window.showSharePopup = (t) => window.Components.SharePopup.show(t);
window.checkSharePopupTriggers = () => window.Components.SharePopup.checkTriggers();
window.trackPartnerClickForPopup = () => window.Components.SharePopup.trackPartnerClick();
