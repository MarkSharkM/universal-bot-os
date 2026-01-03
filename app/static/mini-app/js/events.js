/**
 * Events Module
 * Event handlers setup
 */

function setupEventHandlers() {
    // Close button
    const closeBtn = document.getElementById('close-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            const tg = AppState.getTg();
            if (tg) {
                tg.close();
            }
        });
    }
    
    // Tab navigation
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.getAttribute('data-tab');
            if (typeof Navigation !== 'undefined' && Navigation.switchTab) {
                Navigation.switchTab(tabName);
            } else {
                switchTab(tabName);
            }
        });
    });
    
    // Back button (if needed)
    const tg = AppState.getTg();
    if (tg?.BackButton) {
        tg.BackButton.onClick(() => {
            // Handle back button
            const activeTab = document.querySelector('.tab.active');
            if (activeTab) {
                // Go to first tab or close
                if (typeof Navigation !== 'undefined' && Navigation.switchTab) {
                    Navigation.switchTab('partners');
                } else {
                    switchTab('partners');
                }
            }
        });
    }
    
    // Swipe gestures for mobile navigation
    setupSwipeGestures();
    
    // Pull-to-refresh
    setupPullToRefresh();
    
    // Ripple effects for buttons
    setupRippleEffects();
    
    // Event delegation for dynamic buttons with data-action
    document.addEventListener('click', (e) => {
        const action = e.target.getAttribute('data-action');
        if (!action) return;
        
        if (typeof Haptic !== 'undefined') Haptic.light();
        
        if (action === 'switch-top') {
            if (typeof Navigation !== 'undefined' && Navigation.switchTab) {
                Navigation.switchTab('top');
            } else {
                switchTab('top');
            }
        } else if (action === 'buy-top') {
            const price = parseInt(e.target.getAttribute('data-price') || '1');
            if (typeof Actions !== 'undefined' && Actions.handleBuyTop) {
                Actions.handleBuyTop(price);
            } else {
                handleBuyTop(price);
            }
        } else if (action === 'activate-7') {
            if (typeof Actions !== 'undefined' && Actions.showActivate7Instructions) {
                Actions.showActivate7Instructions();
            } else {
                showActivate7Instructions();
            }
        } else if (action === 'copy-referral') {
            if (typeof Actions !== 'undefined' && Actions.copyReferralLink) {
                Actions.copyReferralLink();
            } else {
                copyReferralLink();
            }
        } else if (action === 'share-referral') {
            if (typeof Actions !== 'undefined' && Actions.shareReferralLink) {
                Actions.shareReferralLink();
            } else {
                shareReferralLink();
            }
        }
    });
    
    // Wallet form submit handler
    document.addEventListener('submit', (e) => {
        if (e.target.id === 'wallet-form') {
            e.preventDefault();
            if (typeof Actions !== 'undefined' && Actions.handleWalletSubmit) {
                Actions.handleWalletSubmit(e);
            } else {
                handleWalletSubmit(e);
            }
        }
    });
}

function setupSwipeGestures() {
    let touchStartX = 0;
    let touchEndX = 0;
    const content = document.querySelector('.content');
    
    if (!content) return;
    
    content.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
    
    content.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });
    
    function handleSwipe() {
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;
        
        if (Math.abs(diff) < swipeThreshold) return;
        
        const tabs = ['partners', 'top', 'earnings', 'wallet'];
        const currentTab = document.querySelector('.tab.active')?.getAttribute('data-tab');
        const currentIndex = tabs.indexOf(currentTab);
        
        if (diff > 0 && currentIndex < tabs.length - 1) {
            // Swipe left - next tab
            if (typeof Navigation !== 'undefined' && Navigation.switchTab) {
                Navigation.switchTab(tabs[currentIndex + 1]);
            } else {
                switchTab(tabs[currentIndex + 1]);
            }
        } else if (diff < 0 && currentIndex > 0) {
            // Swipe right - previous tab
            if (typeof Navigation !== 'undefined' && Navigation.switchTab) {
                Navigation.switchTab(tabs[currentIndex - 1]);
            } else {
                switchTab(tabs[currentIndex - 1]);
            }
        }
    }
}

function setupPullToRefresh() {
    const content = document.querySelector('.content');
    if (!content) return;
    
    // Disable pull-to-refresh - it's too sensitive and causes accidental reloads
    // Users can refresh by closing and reopening Mini App if needed
    return;
    
    // Old code below (disabled)
    /*
    let touchStartY = 0;
    let touchCurrentY = 0;
    let isPulling = false;
    let pullDistance = 0;
    let touchStartTime = 0;
    const pullThreshold = 200; // Very high threshold - requires intentional pull
    const minPullDistance = 100; // Minimum distance before showing indicator
    const maxScrollTop = 2; // Very strict - must be exactly at top
    
    content.addEventListener('touchstart', (e) => {
        // Only trigger if at top of scroll (with small tolerance)
        if (content.scrollTop <= maxScrollTop) {
            touchStartY = e.touches[0].clientY;
            touchStartTime = Date.now();
            isPulling = true;
        } else {
            isPulling = false;
        }
    }, { passive: true });
    
    content.addEventListener('touchmove', (e) => {
        if (!isPulling) return;
        
        // Check if still at top
        if (content.scrollTop > maxScrollTop) {
            isPulling = false;
            hidePullToRefresh();
            return;
        }
        
        touchCurrentY = e.touches[0].clientY;
        pullDistance = touchCurrentY - touchStartY;
        
        // Only show indicator if pulled down significantly
        if (pullDistance > minPullDistance && content.scrollTop <= maxScrollTop) {
            e.preventDefault();
            updatePullToRefresh(pullDistance);
        } else if (pullDistance <= 0) {
            // User is scrolling up, cancel pull-to-refresh
            isPulling = false;
            hidePullToRefresh();
        }
    }, { passive: false });
    
    content.addEventListener('touchend', () => {
        if (!isPulling) {
            hidePullToRefresh();
            return;
        }
        
        // Only trigger if pulled down enough AND user held for a moment (not accidental scroll)
        const touchDuration = Date.now() - touchStartTime;
        const minDuration = 300; // At least 300ms to distinguish from quick scroll
        
        if (pullDistance >= pullThreshold && touchDuration >= minDuration) {
            // Trigger refresh
            showPullToRefresh();
            loadAppData(true);
        } else {
            hidePullToRefresh();
        }
        
        isPulling = false;
        pullDistance = 0;
        touchStartTime = 0;
    }, { passive: true });
    
    // Also handle scroll events to cancel pull-to-refresh if user scrolls
    content.addEventListener('scroll', () => {
        if (isPulling && content.scrollTop > maxScrollTop) {
            isPulling = false;
            hidePullToRefresh();
        }
    }, { passive: true });
    */
}

function setupRippleEffects() {
    // Add ripple to all buttons
    document.addEventListener('click', (e) => {
        const button = e.target.closest('button, .partner-btn, .partner-card, .tab');
        if (!button) return;
        
        // Skip if already has ripple
        if (button.querySelector('.ripple')) return;
        
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');
        
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        
        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        button.appendChild(ripple);
        
        // Remove ripple after animation
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
}

function updatePullToRefresh(distance) {
    const indicator = document.getElementById('pull-to-refresh');
    if (!indicator) return;
    
    const threshold = 120; // Match pullThreshold
    const progress = Math.min(distance / threshold, 1);
    
    indicator.style.opacity = progress;
    indicator.style.transform = `translateX(-50%) translateY(${Math.min(distance, threshold) - 100}px)`;
    
    if (distance >= threshold) {
        indicator.classList.add('ready');
    } else {
        indicator.classList.remove('ready');
    }
}

function showPullToRefresh() {
    // Disabled - do nothing
    return;
    /*
    const indicator = document.getElementById('pull-to-refresh');
    if (indicator) {
        indicator.classList.add('active');
        indicator.querySelector('.pull-to-refresh-icon').textContent = '🔄';
        indicator.querySelector('.pull-to-refresh-text').textContent = 'Оновлення...';
    }
    */
}

function hidePullToRefresh() {
    // Disabled - do nothing
    return;
    /*
    const indicator = document.getElementById('pull-to-refresh');
    if (indicator) {
        indicator.classList.remove('active', 'ready');
        indicator.style.opacity = '0';
        indicator.style.transform = 'translateX(-50%) translateY(-100%)';
        indicator.querySelector('.pull-to-refresh-icon').textContent = '⬇️';
        indicator.querySelector('.pull-to-refresh-text').textContent = 'Потягніть для оновлення';
    }
    */
}


window.Events = {
    setupEventHandlers,
    setupSwipeGestures,
    setupPullToRefresh,
    setupRippleEffects,
    updatePullToRefresh,
    showPullToRefresh,
    hidePullToRefresh
};
