// Bots Management logic

async function loadBots() {
    try {
        const res = await fetch(`${API_BASE}/bots?is_active=true`);
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
                        <button onclick="showStatsTab('${bot.id}')" style="margin-right: 5px;">Stats</button>
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
        const res = await fetch(`${API_BASE}/bots`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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

async function deleteBot(botId) {
    if (!confirm('Are you sure you want to delete this bot?')) return;

    try {
        const res = await fetch(`${API_BASE}/bots/${botId}`, { method: 'DELETE' });
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
        const res = await fetch(`${API_BASE}/bots`);
        const bots = await res.json();
        const select = document.getElementById(selectId);
        select.innerHTML = '<option value="">Select Bot</option>' +
            bots.map(bot => `<option value="${bot.id}">${bot.name}</option>`).join('');
        if (callback) callback();
    } catch (error) {
        console.error('Error loading bots:', error);
    }
}
