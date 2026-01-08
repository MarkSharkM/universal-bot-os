/**
 * API Client for Mini App
 * Handles all API calls to backend with caching and retry logic
 */

const API_BASE = window.location.origin;

/**
 * Get Mini App data from backend with caching and retry
 * @param {string} botId - Bot UUID
 * @param {string} userId - User external ID (optional, can be extracted from initData)
 * @param {string} initData - Telegram WebApp initData (optional, for validation)
 * @param {boolean} forceRefresh - Force refresh, bypass cache
 * @returns {Promise<Object>} Mini App data
 */
async function getMiniAppData(botId, userId = null, initData = null, forceRefresh = false) {
    // Check cache first (if utils.js is loaded)
    if (!forceRefresh && typeof ApiCache !== 'undefined' && ApiCache.isValid(60000)) {
        const cached = ApiCache.get(60000);
        if (cached) {
            return cached;
        }
    }

    // Check if online
    if (!navigator.onLine) {
        throw new Error(AppState.getAppData()?.translations?.offline || 'Немає інтернет-з\'єднання');
    }

    // Retry with exponential backoff
    const fetchData = async () => {
        const params = new URLSearchParams();
        if (userId) params.append('user_id', userId);
        if (initData) params.append('init_data', initData);

        const url = `${API_BASE}/api/v1/mini-apps/mini-app/${botId}/data?${params.toString()}`;

        // Add timeout (30 seconds)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);

        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                signal: controller.signal,
            });
            clearTimeout(timeoutId);

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();

            // Cache the data
            if (typeof ApiCache !== 'undefined') {
                ApiCache.set(data);
            }

            return data;
        } catch (fetchError) {
            clearTimeout(timeoutId);
            if (fetchError.name === 'AbortError') {
                throw new Error(AppState.getAppData()?.translations?.timeout || 'Час очікування вичерпано. Спробуйте ще раз.');
            }
            throw fetchError;
        }
    };

    try {
        // Use retry with backoff if available, otherwise just try once
        if (typeof Retry !== 'undefined') {
            return await Retry.withBackoff(fetchData, 3, 1000);
        } else {
            return await fetchData();
        }
    } catch (error) {
        console.error('Error fetching Mini App data:', error);
        throw error;
    }
}

/**
 * Save wallet address with retry logic
 * @param {string} botId - Bot UUID
 * @param {string} walletAddress - TON wallet address
 * @param {string} userId - User external ID (optional)
 * @param {string} initData - Telegram WebApp initData (optional, for validation)
 * @returns {Promise<Object>} Success response
 */
async function saveWallet(botId, walletAddress, userId = null, initData = null) {
    console.log('📤 saveWallet called:', {
        botId,
        walletAddress: walletAddress ? `${walletAddress.substring(0, 10)}...` : 'null',
        userId,
        hasInitData: !!initData
    });

    // Check if online
    if (!navigator.onLine) {
        throw new Error(AppState.getAppData()?.translations?.offline || 'Немає інтернет-з\'єднання');
    }

    const saveData = async () => {
        const params = new URLSearchParams();
        params.append('wallet_address', walletAddress);
        if (userId) params.append('user_id', userId);
        if (initData) params.append('init_data', initData);

        const url = `${API_BASE}/api/v1/mini-apps/mini-app/${botId}/wallet?${params.toString()}`;
        console.log('📡 POST request to:', url);

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        console.log('📥 Response status:', response.status, response.statusText);

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            console.error('❌ Error response:', error);
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('✅ Wallet saved successfully:', data);

        // Clear cache after wallet save
        if (typeof ApiCache !== 'undefined') {
            ApiCache.clear();
        }

        return data;
    };

    try {
        // Use retry with backoff if available
        if (typeof Retry !== 'undefined') {
            return await Retry.withBackoff(saveData, 2, 1000);
        } else {
            return await saveData();
        }
    } catch (error) {
        console.error('Error saving wallet:', error);
        throw error;
    }
}

/**
 * Create invoice link for Telegram Stars payment (buy TOP)
 * @param {string} botId - Bot UUID
 * @param {string} initData - Telegram WebApp initData (optional, for validation)
 * @param {string} userId - User external ID (optional, if initData not provided)
 * @returns {Promise<string>} Invoice link URL
 */
async function createInvoiceLink(botId, initData = null, userId = null) {
    try {
        const params = new URLSearchParams();
        if (initData) params.append('init_data', initData);
        if (userId) params.append('user_id', userId);

        const url = `${API_BASE}/api/v1/mini-apps/mini-app/${botId}/create-invoice?${params.toString()}`;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const result = await response.json();
        if (result.ok && result.invoice_link) {
            return result.invoice_link;
        } else {
            throw new Error('Failed to create invoice link');
        }
    } catch (error) {
        console.error('Error creating invoice link:', error);
        throw error;
    }
}

/**
 * Send callback to backend (partner clicks, etc.)
 * @param {string} botId - Bot UUID
 * @param {Object} data - Callback data
 * @param {string} initData - Telegram WebApp initData (optional, for validation)
 * @returns {Promise<Object>} Response
 */
async function sendCallback(botId, data, initData = null) {
    try {
        const params = new URLSearchParams();
        if (initData) params.append('init_data', initData);

        const url = `${API_BASE}/api/v1/mini-apps/mini-app/${botId}?${params.toString()}`;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error sending callback:', error);
        throw error;
    }
}

// Export via namespace pattern (for compatibility with render.js)
window.Api = {
    getMiniAppData,
    saveWallet,
    sendCallback,
    createInvoiceLink
};

// Also export for Node.js if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { getMiniAppData, saveWallet, sendCallback };
}

