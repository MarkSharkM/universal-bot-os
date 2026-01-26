// Bots Management logic

async function loadBots() {
    try {
        const res = await authFetch(`${API_BASE}/bots?is_active=true`);
        const bots = await res.json();
        const tbody = document.getElementById('bots-tbody');
        if (bots.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px;">No active bots</td></tr>';
        } else {
            tbody.innerHTML = bots.map(bot => `
                <tr>
                    <td>${bot.name}</td>
                    <td>${bot.platform_type}</td>
                    <td>${bot.is_active ? '✅ Active' : '❌ Inactive'}</td>
                    <td>
                        <button onclick="editBotSettings('${bot.id}')" style="margin-right: 5px; background: #22c55e;">⚙️ Settings</button>
                        <button onclick="showStatsTab('${bot.id}')" style="margin-right: 5px;">Stats</button>
                        <button onclick="editBotToken('${bot.id}')" style="margin-right: 5px; background: #f59e0b;">Edit Token</button>
                        <button class="btn-danger" onclick="deleteBot('${bot.id}')">Delete</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        showMessage('bots-message', 'Error loading bots: ' + error.message, 'error');
    }
}

function showCreateBotForm() {
    document.getElementById('create-bot-form').style.display = 'block';
    document.getElementById('edit-bot-settings-form').style.display = 'none';
}

function hideCreateBotForm() {
    document.getElementById('create-bot-form').style.display = 'none';
}

async function createBot() {
    const data = {
        name: document.getElementById('bot-name').value,
        platform_type: document.getElementById('bot-platform').value,
        token: document.getElementById('bot-token').value,
        default_lang: document.getElementById('bot-lang').value,
        config: {}
    };

    try {
        const res = await authFetch(`${API_BASE}/bots`, {
            method: 'POST',
            body: JSON.stringify(data)
        });

        if (res.ok) {
            showMessage('bots-message', 'Bot created successfully!', 'success');
            hideCreateBotForm();
            loadBots();
        } else {
            showMessage('bots-message', 'Error creating bot', 'error');
        }
    } catch (error) {
        showMessage('bots-message', 'Error: ' + error.message, 'error');
    }
}

// Settings Logic
async function editBotSettings(botId) {
    try {
        // Fetch fresh bot data to ensuring we have latest config
        const res = await authFetch(`${API_BASE}/bots/${botId}`);
        if (!res.ok) throw new Error("Failed to load bot details");

        const bot = await res.json();
        const config = bot.config || {};
        const earnings = config.earnings || {};

        // Populate form
        document.getElementById('setting-bot-id').value = bot.id;
        document.getElementById('setting-buy-top-price').value = earnings.buy_top_price || 1;

        // Show form
        hideCreateBotForm();
        document.getElementById('edit-bot-settings-form').style.display = 'block';
        window.currentBotConfig = config; // Store full config for merging
    } catch (e) {
        showMessage('bots-message', 'Error loading settings: ' + e.message, 'error');
    }
}

function hideBotSettingsForm() {
    document.getElementById('edit-bot-settings-form').style.display = 'none';
}

async function saveBotSettings() {
    const botId = document.getElementById('setting-bot-id').value;
    const buyTopPrice = parseInt(document.getElementById('setting-buy-top-price').value) || 1;

    // Merge with existing config to preserve other settings
    const config = window.currentBotConfig || {};
    config.earnings = config.earnings || {};
    config.earnings.buy_top_price = buyTopPrice;

    try {
        const res = await authFetch(`${API_BASE}/bots/${botId}`, {
            method: 'PATCH',
            body: JSON.stringify({ config: config })
        });

        if (res.ok) {
            showMessage('bots-message', 'Settings saved successfully!', 'success');
            hideBotSettingsForm();
            loadBots();
        } else {
            const err = await res.json();
            showMessage('bots-message', 'Error saving settings: ' + (err.detail || 'Unknown error'), 'error');
        }
    } catch (e) {
        showMessage('bots-message', 'Error: ' + e.message, 'error');
    }
}

async function editBotToken(botId) {
    const newToken = prompt("Enter new Telegram Bot Token (plain text):");
    if (!newToken) return;

    try {
        const res = await authFetch(`${API_BASE}/bots/${botId}`, {
            method: 'PATCH',
            body: JSON.stringify({ token: newToken })
        });

        if (res.ok) {
            showMessage('bots-message', 'Token updated successfully!', 'success');
            loadBots();
        } else {
            showMessage('bots-message', 'Error updating token', 'error');
        }
    } catch (e) {
        showMessage('bots-message', 'Error: ' + e.message, 'error');
    }
}

async function deleteBot(botId) {
    if (!confirm('Are you sure you want to delete this bot?')) return;

    try {
        const res = await authFetch(`${API_BASE}/bots/${botId}`, { method: 'DELETE' });
        if (res.ok) {
            showMessage('bots-message', 'Bot deleted successfully', 'success');
            setTimeout(() => loadBots(), 500);
        } else {
            const errorData = await res.json().catch(() => ({ detail: 'Unknown error' }));
            showMessage('bots-message', 'Error: ' + (errorData.detail || 'Failed to delete bot'), 'error');
        }
    } catch (error) {
        showMessage('bots-message', 'Error: ' + error.message, 'error');
    }
}

// Utils needed for other modules
async function loadBotsForSelect(selectId, callback) {
    try {
        const res = await authFetch(`${API_BASE}/bots`);
        const bots = await res.json();
        const select = document.getElementById(selectId);
        select.innerHTML = '<option value="">Select Bot</option>' +
            bots.map(bot => `<option value="${bot.id}">${bot.name}</option>`).join('');
        if (callback) callback();
    } catch (error) {
        console.error('Error loading bots:', error);
    }
}
