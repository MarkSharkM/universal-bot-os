const API_BASE = window.location.origin + '/api/v1/admin';

// Global bot selector
let currentBotId = null;
let currentBotName = null;

// Simple cache for API responses (to reduce server load)
const cache = {
    bots: { data: null, timestamp: 0, ttl: 5 * 60 * 1000 }, // 5 minutes
    usersForFilter: { data: null, timestamp: 0, ttl: 2 * 60 * 1000 }, // 2 minutes
    partners: { data: null, timestamp: 0, ttl: 1 * 60 * 1000 }, // 1 minute
};

function getCached(key) {
    const cached = cache[key];
    if (cached && cached.data && (Date.now() - cached.timestamp) < cached.ttl) {
        return cached.data;
    }
    return null;
}

function setCache(key, data) {
    cache[key] = { data, timestamp: Date.now(), ttl: cache[key]?.ttl || 60000 };
}

// Authentication Logic
const AUTH = {
    token: localStorage.getItem('admin_token'),

    setToken(token) {
        this.token = token;
        localStorage.setItem('admin_token', token);
    },

    logout() {
        this.token = null;
        localStorage.removeItem('admin_token');
        showLoginModal();
    },

    isAuthenticated() {
        return !!this.token;
    },

    getHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        return headers;
    }
};

async function authFetch(url, options = {}) {
    // Default headers
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (AUTH.token) {
        headers['Authorization'] = `Bearer ${AUTH.token}`;
    }

    const response = await fetch(url, {
        ...options,
        headers
    });

    if (response.status === 401 || response.status === 403) {
        showMessage('global-message', 'Session expired. Please login.', 'error');
        AUTH.logout();
        throw new Error('Unauthorized');
    }

    return response;
}

// Login UI Handlers
function showLoginModal() {
    const modal = document.getElementById('login-modal');
    if (modal) modal.style.display = 'flex';
}

function hideLoginModal() {
    const modal = document.getElementById('login-modal');
    if (modal) modal.style.display = 'none';
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');

    errorEl.style.display = 'none';

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (res.ok) {
            const data = await res.json();
            AUTH.setToken(data.access_token);
            hideLoginModal();
            showMessage('global-message', 'Logged in successfully', 'success');
            setTimeout(() => location.reload(), 500); // Reload to refresh state
        } else {
            const err = await res.json();
            errorEl.textContent = err.detail || 'Login failed';
            errorEl.style.display = 'block';
        }
    } catch (err) {
        console.error(err);
        errorEl.textContent = 'Connection error';
        errorEl.style.display = 'block';
    }
}

// Global Message Handler
function showMessage(elementId, message, type = 'success') {
    const el = document.getElementById(elementId);
    if (!el) return;

    el.textContent = message;
    el.className = 'message ' + type;
    el.style.display = 'block';

    setTimeout(() => {
        el.style.display = 'none';
    }, 5000);
}

// Tab Switching
function showTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

    // Activate tab button
    const tabBtn = document.querySelector(`.tab[onclick="showTab('${tabName}')"]`);
    if (tabBtn) tabBtn.classList.add('active');

    // Activate tab content
    document.getElementById(tabName).classList.add('active');

    if (tabName === 'bots') loadBots();
    if (tabName === 'partners') {
        loadBotsForSelect('partners-bot-select', () => {
            if (currentBotId) {
                document.getElementById('partners-bot-select').value = currentBotId;
                loadPartners();
            }
        });
    }
    if (tabName === 'database') {
        loadDatabaseData();
    }
    if (tabName === 'ai') {
        if (currentBotId) loadAIConfig();
    }
    if (tabName === 'stats') {
        if (currentBotId) loadStats();
    }
    if (tabName === 'monitoring') {
        if (currentBotId) {
            loadProductMonitoring();
        }
    }
    if (tabName === 'users') {
        if (currentBotId && window.initUsersTab) {
            initUsersTab();
        }
    }
}

// Global Bot Selector Logic
async function loadGlobalBotSelector() {
    // Check if user is authenticated first
    if (!AUTH.isAuthenticated()) {
        showLoginModal();
        return;
    }
    
    try {
        // Check cache first
        const cached = getCached('bots');
        if (cached) {
            updateBotSelectOptions(cached);
            return;
        }

        const res = await authFetch(`${API_BASE}/bots?limit=50`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const bots = await res.json();
        setCache('bots', bots);
        updateBotSelectOptions(bots);

    } catch (error) {
        console.error('Error loading bots:', error);
        // If unauthorized, show login modal
        if (error.message === 'Unauthorized') {
            return; // authFetch already shows login modal
        }
        const select = document.getElementById('global-bot-select');
        if (select) select.innerHTML = '<option value="">Error loading bots</option>';
    }
}

function updateBotSelectOptions(bots) {
    const select = document.getElementById('global-bot-select');
    if (!select) return;

    select.innerHTML = '<option value="">Select Bot</option>' +
        bots.map(bot => `<option value="${bot.id}">${bot.name}</option>`).join('');

    // Auto-select first bot
    if (bots.length > 0 && !currentBotId) {
        select.value = bots[0].id;
        onGlobalBotChange();
    } else if (bots.length === 0) {
        select.innerHTML = '<option value="">No bots found</option>';
    }
}

function onGlobalBotChange() {
    const select = document.getElementById('global-bot-select');
    currentBotId = select.value;
    const selectedOption = select.options[select.selectedIndex];
    currentBotName = selectedOption ? selectedOption.text : '-';

    const dbBotName = document.getElementById('database-bot-name');
    if (dbBotName) dbBotName.textContent = currentBotName;

    // Update all bot selects in other tabs
    ['partners-bot-select', 'ai-bot-select', 'stats-bot-select'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = currentBotId;
    });

    // Clear messages when bot changes
    const messagesTbody = document.getElementById('database-messages-tbody');
    if (messagesTbody) messagesTbody.innerHTML = '<tr><td colspan="17" style="padding: 20px; text-align: center; color: #6b7280;">Select a bot to view messages</td></tr>';

    // Reload current tab if it needs bot data
    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab) {
        const tabId = activeTab.id;
        if (tabId === 'database') loadDatabaseData();
        if (tabId === 'partners' && currentBotId) loadPartners();
        if (tabId === 'ai' && currentBotId) loadAIConfig();
        if (tabId === 'stats' && currentBotId) loadStats();
        if (tabId === 'users' && currentBotId && window.initUsersTab) initUsersTab();
        if (tabId === 'monitoring' && currentBotId) loadProductMonitoring();
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadGlobalBotSelector();

    // Set default tab
    showTab('bots');

    // Add global event listener for bot selector
    const globalSelect = document.getElementById('global-bot-select');
    if (globalSelect) {
        globalSelect.addEventListener('change', onGlobalBotChange);
    }

    // Initialize date inputs with default 30 days
    const today = new Date().toISOString().split('T')[0];
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    ['stats', 'monitoring'].forEach(tab => {
        const start = document.getElementById(`${tab}-date-start`);
        const end = document.getElementById(`${tab}-date-end`);
        if (start && end) {
            start.value = thirtyDaysAgo;
            end.value = today;
        }
    });
});

// Date Range Logic
function setDateRange(tabName, days, btnElement) {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - days);

    const startStr = start.toISOString().split('T')[0];
    const endStr = end.toISOString().split('T')[0];

    document.getElementById(`${tabName}-date-start`).value = startStr;
    document.getElementById(`${tabName}-date-end`).value = endStr;

    // Reset styles for all buttons in this tab's stats container
    const container = document.querySelector(`#${tabName} .date-filter-container`);
    if (container) {
        const buttons = container.querySelectorAll('button');
        buttons.forEach(btn => {
            if (btn.textContent.includes('Days')) { // Filter only preset buttons
                btn.className = 'date-btn'; // Reset class
                // Reset inline styles if used
                btn.style.background = '#f3f4f6';
                btn.style.color = '#374151';
                btn.style.border = '1px solid #d1d5db';
                btn.style.fontWeight = 'normal';
            }
        });
    }

    // specific button highlight
    if (btnElement) {
        btnElement.style.background = '#e0f2fe';
        btnElement.style.color = '#0284c7';
        btnElement.style.border = '1px solid #bae6fd';
        btnElement.style.fontWeight = '500';
    }

    applyCustomDateRange(tabName);
}

function applyCustomDateRange(tabName) {
    if (!currentBotId) return;

    if (tabName === 'stats') {
        loadStats(); // Logic inside loadStats needs update
    } else if (tabName === 'monitoring') {
        loadProductMonitoring(); // Logic inside loadProductMonitoring needs update
    }
}
