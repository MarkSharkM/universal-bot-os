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
    else if (event && event.target) event.target.classList.add('active');

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
            loadMonitoring();
        }
    }
}

// Global Bot Selector Logic
async function loadGlobalBotSelector() {
    try {
        // Check cache first
        const cached = getCached('bots');
        if (cached) {
            updateBotSelectOptions(cached);
            return;
        }

        const res = await fetch(`${API_BASE}/bots?limit=50`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const bots = await res.json();
        setCache('bots', bots);
        updateBotSelectOptions(bots);

    } catch (error) {
        console.error('Error loading bots:', error);
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
    const messagesList = document.getElementById('database-messages-msgs'); // corrected ID assumption, check HTML later
    const messagesContainer = document.getElementById('database-messages-list');
    if (messagesContainer) messagesContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #6b7280;">Select a bot to view messages</div>';

    // Reload current tab if it needs bot data
    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab) {
        const tabId = activeTab.id;
        if (tabId === 'database') loadDatabaseData();
        if (tabId === 'partners' && currentBotId) loadPartners();
        if (tabId === 'ai' && currentBotId) loadAIConfig();
        if (tabId === 'stats' && currentBotId) loadStats();
        if (tabId === 'monitoring' && currentBotId) loadMonitoring();
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
});
