/**
 * Header.js (v5.0)
 * Sticky header with Profile and Wallet.
 */

window.Components = window.Components || {};

window.Components.Header = function (user, isTop) {
    // Container
    const header = document.createElement('div');
    header.className = 'v5-header';

    // User Info
    const userName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'User';
    const userAvatarChar = userName.charAt(0).toUpperCase(); // Yellow/M style

    // Status Logic
    const statusLabel = isTop ? 'TOP' : 'STARTER';
    const statusColorClass = isTop ? 'text-gold' : 'text-purple';

    // Wallet Logic (Unlocked for all)
    const walletAddress = user?.wallet || AppState.getAppData()?.user?.wallet;
    const isConnected = walletAddress && walletAddress.length > 5;
    const t = AppState.getAppData()?.translations || {};
    // FIX: Show simple "Wallet" text with active indicator instead of raw address
    const walletText = isConnected
        ? (t.wallet_btn || 'Wallet')
        : (t.wallet_btn || 'Wallet');

    const walletClass = isConnected ? 'wallet-btn active' : 'wallet-btn';

    header.innerHTML = `
        <div class="header-profile">
            <div class="avatar-circle">${userAvatarChar}</div>
            <div class="user-text">
                <div class="name">${escapeHtml(userName)}</div>
                <div class="status">Status: <span class="${statusColorClass}">${statusLabel}</span></div>
            </div>
        </div>
        
        <button class="${walletClass}" onclick="document.dispatchEvent(new CustomEvent('open-wallet-modal'))">
            ${Icons.Wallet}
            <span>${walletText}</span>
        </button>
    `;

    return header;
};
