/**
 * Utility Functions for Mini App
 * Toast notifications, caching, haptic feedback, etc.
 */

/**
 * Toast Notification System
 */
const Toast = {
    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type: 'success', 'error', 'info', 'warning'
     * @param {number} duration - Duration in milliseconds (default: 3000)
     */
    show(message, type = 'info', duration = 3000) {
        // Remove existing toast if any
        const existingToast = document.getElementById('toast');
        if (existingToast) {
            existingToast.remove();
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        
        const icon = this.getIcon(type);
        toast.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <span class="toast-message">${this.escapeHtml(message)}</span>
        `;

        document.body.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('toast-show');
        });

        // Auto remove
        setTimeout(() => {
            toast.classList.remove('toast-show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    /**
     * Get icon for toast type
     * @param {string} type - Toast type
     * @returns {string} Icon emoji
     */
    getIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
    },

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    success(message, duration) {
        this.show(message, 'success', duration);
    },

    error(message, duration) {
        this.show(message, 'error', duration);
    },

    warning(message, duration) {
        this.show(message, 'warning', duration);
    },

    info(message, duration) {
        this.show(message, 'info', duration);
    }
};

/**
 * API Cache with TTL
 */
const ApiCache = {
    cache: {
        data: null,
        timestamp: 0,
        ttl: 60000 // 1 minute default
    },

    /**
     * Get cached data if still valid
     * @param {number} ttl - Time to live in milliseconds
     * @returns {Object|null} Cached data or null
     */
    get(ttl = 60000) {
        const now = Date.now();
        if (this.cache.data && (now - this.cache.timestamp) < ttl) {
            return this.cache.data;
        }
        return null;
    },

    /**
     * Set cache data
     * @param {Object} data - Data to cache
     */
    set(data) {
        this.cache.data = data;
        this.cache.timestamp = Date.now();
    },

    /**
     * Clear cache
     */
    clear() {
        this.cache.data = null;
        this.cache.timestamp = 0;
    },

    /**
     * Check if cache is valid
     * @param {number} ttl - Time to live in milliseconds
     * @returns {boolean} True if cache is valid
     */
    isValid(ttl = 60000) {
        const now = Date.now();
        return this.cache.data && (now - this.cache.timestamp) < ttl;
    }
};

/**
 * Haptic Feedback Wrapper
 */
const Haptic = {
    /**
     * Trigger haptic feedback
     * @param {string} type - Type: 'impact', 'notification', 'selection'
     * @param {string} style - Style: 'light', 'medium', 'heavy', 'rigid', 'soft' (for impact)
     */
    feedback(type = 'impact', style = 'medium') {
        if (window.tg?.HapticFeedback) {
            try {
                if (type === 'impact') {
                    window.tg.HapticFeedback.impactOccurred(style);
                } else if (type === 'notification') {
                    window.tg.HapticFeedback.notificationOccurred(style);
                } else if (type === 'selection') {
                    window.tg.HapticFeedback.selectionChanged();
                }
            } catch (error) {
                console.warn('Haptic feedback error:', error);
            }
        }
    },

    /**
     * Light impact feedback
     */
    light() {
        this.feedback('impact', 'light');
    },

    /**
     * Medium impact feedback
     */
    medium() {
        this.feedback('impact', 'medium');
    },

    /**
     * Heavy impact feedback
     */
    heavy() {
        this.feedback('impact', 'heavy');
    },

    /**
     * Success notification
     */
    success() {
        this.feedback('notification', 'success');
    },

    /**
     * Error notification
     */
    error() {
        this.feedback('notification', 'error');
    },

    /**
     * Warning notification
     */
    warning() {
        this.feedback('notification', 'warning');
    }
};

/**
 * Retry utility with exponential backoff
 */
const Retry = {
    /**
     * Retry a function with exponential backoff
     * @param {Function} fn - Async function to retry
     * @param {number} maxRetries - Maximum number of retries
     * @param {number} initialDelay - Initial delay in milliseconds
     * @returns {Promise} Promise that resolves with function result
     */
    async withBackoff(fn, maxRetries = 3, initialDelay = 1000) {
        let lastError;
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return await fn();
            } catch (error) {
                lastError = error;
                if (attempt < maxRetries) {
                    const delay = initialDelay * Math.pow(2, attempt);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }
        throw lastError;
    }
};

/**
 * Check if device is online
 * @returns {boolean} True if online
 */
function isOnline() {
    return navigator.onLine !== false;
}

/**
 * Safe localStorage wrapper with fallback to memory storage
 */
const memoryStorage = {};

const SafeStorage = {
    get(key) {
        try {
            return localStorage.getItem(key);
        } catch (e) {
            console.warn('localStorage not available, using memory storage');
            return memoryStorage[key] || null;
        }
    },
    
    set(key, value) {
        try {
            localStorage.setItem(key, value);
        } catch (e) {
            console.warn('localStorage not available, using memory storage');
            memoryStorage[key] = value;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            delete memoryStorage[key];
        }
    },
    
    clear() {
        try {
            localStorage.clear();
        } catch (e) {
            Object.keys(memoryStorage).forEach(key => delete memoryStorage[key]);
        }
    },
    
    // Alias methods for localStorage compatibility
    getItem(key) {
        return this.get(key);
    },
    
    setItem(key, value) {
        return this.set(key, value);
    },
    
    removeItem(key) {
        return this.remove(key);
    }
};

// Export SafeStorage
window.SafeStorage = SafeStorage;

// Export utility functions
window.getBotUsername = getBotUsername;
window.getBotUrl = getBotUrl;

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    if (typeof text !== 'string') {
        text = String(text);
    }
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get bot username from app config (universal for any bot)
 * @returns {string} Bot username (without @)
 */
function getBotUsername() {
    // Try to get from AppState if available
    if (typeof AppState !== 'undefined') {
        const appData = AppState.getAppData();
        if (appData?.config?.username) {
            // Remove @ if present
            return appData.config.username.replace('@', '').trim();
        }
        if (appData?.config?.name) {
            // Extract username from name if it's a URL or contains @
            let name = appData.config.name;
            // Remove @ if present
            name = name.replace('@', '').trim();
            // If it's a full URL, extract username
            if (name.includes('t.me/')) {
                name = name.split('t.me/')[1].split('/')[0];
            }
            return name;
        }
    }
    
    // Fallback: try to get from Telegram WebApp
    if (typeof window !== 'undefined' && window.Telegram?.WebApp) {
        const tg = window.Telegram.WebApp;
        // Try to extract from initData or other sources
        // This is a last resort fallback
    }
    
    // Final fallback (should not happen in production)
    return 'EarnHubAggregatorBot';
}

/**
 * Get bot URL (t.me link)
 * @returns {string} Bot URL
 */
function getBotUrl() {
    const username = getBotUsername();
    return `https://t.me/${username}`;
}
