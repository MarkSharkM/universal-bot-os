/**
 * API Client for Mini App
 * Handles all API calls to backend
 */

const API_BASE = window.location.origin;

/**
 * Get Mini App data from backend
 * @param {string} botId - Bot UUID
 * @param {string} userId - User external ID (optional, can be extracted from initData)
 * @param {string} initData - Telegram WebApp initData (optional, for validation)
 * @returns {Promise<Object>} Mini App data
 */
async function getMiniAppData(botId, userId = null, initData = null) {
    try {
        const params = new URLSearchParams();
        if (userId) params.append('user_id', userId);
        if (initData) params.append('init_data', initData);
        
        const url = `${API_BASE}/api/v1/mini-apps/mini-app/${botId}/data?${params.toString()}`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching Mini App data:', error);
        throw error;
    }
}

/**
 * Save wallet address
 * @param {string} botId - Bot UUID
 * @param {string} walletAddress - TON wallet address
 * @param {string} userId - User external ID (optional)
 * @param {string} initData - Telegram WebApp initData (optional, for validation)
 * @returns {Promise<Object>} Success response
 */
async function saveWallet(botId, walletAddress, userId = null, initData = null) {
    try {
        const params = new URLSearchParams();
        params.append('wallet_address', walletAddress);
        if (userId) params.append('user_id', userId);
        if (initData) params.append('init_data', initData);
        
        const url = `${API_BASE}/api/v1/mini-apps/mini-app/${botId}/wallet?${params.toString()}`;
        
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
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error saving wallet:', error);
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

// Export functions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { getMiniAppData, saveWallet, sendCallback };
}

