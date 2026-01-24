/**
 * Gamification Component
 * Handles user status, badges, and social proof.
 */

window.Components = window.Components || {};

window.Components.Gamification = {
    /**
     * Calculate user status based on actions
     * Statuses: Starter → Pro → Hub
     */
    calculateStatus() {
        const appData = AppState.getAppData();
        if (!appData) return 'starter';

        const didStart7Flow = AppState.getDidStart7Flow();
        const topLocked = AppState.getTopLocked();
        const referralCount = AppState.getReferralCount();
        const user = appData.user || {};

        // Count actions (non-financial)
        let actionScore = 0;

        // Started 7% flow = 1 point
        if (didStart7Flow) actionScore += 1;

        // TOP unlocked = 2 points
        if (!topLocked) actionScore += 2;

        // Referrals (1 point per 2 referrals, max 3 points)
        actionScore += Math.min(Math.floor(referralCount / 2), 3);

        // Wallet connected = 1 point
        if (user.wallet) actionScore += 1;

        // Determine status
        if (actionScore >= 5) return 'hub';
        if (actionScore >= 2) return 'pro';
        return 'starter';
    },

    /**
     * Get user badges based on actions
     */
    getBadges() {
        const badges = [];
        const appData = AppState.getAppData();
        if (!appData) return badges;

        const didStart7Flow = AppState.getDidStart7Flow();
        const topLocked = AppState.getTopLocked();
        const referralCount = AppState.getReferralCount();

        // 7% Path Started badge
        if (didStart7Flow) {
            badges.push({ name: AppState.getAppData()?.translations?.badge_7_path || '7% Path Started', icon: '🎯' });
        }

        // TOP Member badge
        if (!topLocked) {
            badges.push({ name: AppState.getAppData()?.translations?.badge_top_member || 'TOP Member', icon: '⭐' });
        }

        // Super Sharer badge (3+ referrals)
        if (referralCount >= 3) {
            badges.push({ name: AppState.getAppData()?.translations?.badge_super_sharer || 'Super Sharer', icon: '🚀' });
        }

        return badges;
    },

    /**
     * Render Social Proof (event-based, NOT financial)
     */
    renderSocialProof() {
        const container = document.getElementById('social-proof');
        if (!container) return;

        // TODO: Get from internal events API
        // For now, show placeholder
        container.innerHTML = `
            <div class="social-proof-item">👥 ${AppState.getAppData()?.translations?.started_path || '47 людей почали 7% шлях'}</div>
            <div class="social-proof-item">⭐ ${AppState.getAppData()?.translations?.top_opened_today || 'TOP відкривали 19 разів сьогодні'}</div>
            <div class="social-proof-item">🔥 ${AppState.getAppData()?.translations?.partners_clicked_most || 'Most clicked partners'}</div>
        `;
    },

    /**
     * Render Gamification (Status, Badges, Progress)
     */
    render() {
        const container = document.getElementById('gamification');
        if (!container) return;

        const appData = AppState.getAppData();
        const t = appData?.translations || {};
        const status = this.calculateStatus();
        const badges = this.getBadges();
        const referralCount = AppState.getReferralCount();
        const topLocked = AppState.getTopLocked();

        // Extract earnings if available
        const balance = appData?.user?.balance || appData?.earnings?.total_earned || 0;
        const currency = appData?.config?.currency || 'TON';

        // Status labels
        const statusLabels = {
            starter: { label: t.starter || 'Starter', icon: '🌱', color: '#4CAF50' },
            pro: { label: t.pro || 'Pro', icon: '⚡', color: '#2196F3' },
            hub: { label: t.hub || 'Hub', icon: '🔥', color: '#FF9800' }
        };

        const currentStatus = statusLabels[status] || statusLabels.starter;

        // Calculate progress to next status
        let progressPercent = 0;
        let progressLabel = '';

        if (status === 'starter') {
            progressPercent = Math.min(50, (referralCount * 25));
            progressLabel = t.to_pro || 'To Pro';
        } else if (status === 'pro') {
            progressPercent = Math.min(80, 50 + (referralCount * 10));
            progressLabel = t.to_hub || 'To Hub';
        } else {
            progressPercent = 100;
            progressLabel = t.max_level || 'Max Level';
        }

        // TOP progress
        const topProgress = topLocked ? (referralCount / 5) * 100 : 100;

        container.innerHTML = `
            <div class="gamification-content">
                <!-- Earnings Overview (Integrated /earnings) -->
                <div class="earnings-overview">
                    <div class="earnings-overview-title">${t.your_earnings || 'Your Earnings'}</div>
                    <div class="earnings-amount">${balance} ${currency}</div>
                    <div class="earnings-7percent-info">
                        ${AppState.getDidStart7Flow() ? (t.program_active || '✅ 7% Program Active') : (t.program_inactive || '❌ 7% Program Inactive')}
                    </div>
                </div>

                <!-- User Status -->
                <div class="user-status">
                    <div class="status-badge" style="background: ${currentStatus.color}20; border-color: ${currentStatus.color};">
                        <span class="status-icon">${currentStatus.icon}</span>
                        <span class="status-label">${currentStatus.label}</span>
                    </div>
                    
                    <!-- Status Progress -->
                    <div class="status-progress">
                        <div class="progress-header">
                            <span class="progress-label">${progressLabel}</span>
                            <span class="progress-percent">${Math.round(progressPercent)}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progressPercent}%; background: ${currentStatus.color};"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Badges -->
                ${badges.length > 0 ? `
                    <div class="user-badges">
                        <h3 class="badges-title">🏆 ${appData?.translations?.achievements || 'Achievements'}</h3>
                        <div class="badges-list">
                            ${badges.map(badge => `
                                <div class="badge-item">
                                    <span class="badge-icon">${badge.icon}</span>
                                    <span class="badge-name">${escapeHtml(badge.name)}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                
                <!-- TOP Progress (if locked) -->
                ${topLocked ? `
                    <div class="top-progress">
                        <div class="progress-header">
                            <span class="progress-label">${appData?.translations?.unlock_top || 'Unlock TOP'}</span>
                            <span class="progress-percent">${referralCount} / 5</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${topProgress}%;"></div>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }
};

// Export to global scope for backward compatibility
window.renderGamification = () => window.Components.Gamification.render();
window.calculateUserStatus = () => window.Components.Gamification.calculateStatus();
window.getUserBadges = () => window.Components.Gamification.getBadges();
window.renderSocialProof = () => window.Components.Gamification.renderSocialProof();
