// AI Config Logic
async function loadAIConfig() {
    const botId = document.getElementById('ai-bot-select').value;
    if (!botId) return;

    try {
        const res = await fetch(`${API_BASE}/bots/${botId}`);
        const bot = await res.json();
        const config = bot.config || {};

        document.getElementById('ai-provider').value = config.ai_provider || 'openai';
        document.getElementById('ai-model').value = config.ai_model || 'gpt-4o';
        document.getElementById('ai-prompt').value = config.system_prompt || '';
        document.getElementById('ai-temperature').value = config.temperature || 0.7;
    } catch (e) {
        showMessage('ai-message', 'Error loading config', 'error');
    }
}

async function saveAIConfig() {
    const botId = document.getElementById('ai-bot-select').value;
    if (!botId) return;

    const data = {
        config: {
            ai_provider: document.getElementById('ai-provider').value,
            ai_model: document.getElementById('ai-model').value,
            system_prompt: document.getElementById('ai-prompt').value,
            temperature: parseFloat(document.getElementById('ai-temperature').value)
        }
    };

    try {
        const res = await fetch(`${API_BASE}/bots/${botId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            showMessage('ai-message', 'Config saved!', 'success');
        } else {
            showMessage('ai-message', 'Error saving', 'error');
        }
    } catch (e) {
        showMessage('ai-message', 'Error: ' + e.message, 'error');
    }
}

// Stats Logic
async function loadStats() {
    const botId = document.getElementById('stats-bot-select')?.value || currentBotId;
    if (!botId) return;

    try {
        const res = await fetch(`${API_BASE}/bots/${botId}/stats`);
        const stats = await res.json();

        document.getElementById('stats-users-total').textContent = stats.users.total;
        document.getElementById('stats-users-active').textContent = stats.users.active;
        document.getElementById('stats-partners-total').textContent = stats.partners.total;
        document.getElementById('stats-partners-active').textContent = stats.partners.active;
    } catch (e) {
        console.error('Error loading stats', e);
    }
}

// Monitoring (Analytics) Logic
async function loadMonitoring() {
    if (!currentBotId) return;

    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js not loaded');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/bots/${currentBotId}/stats/analytics?days=30`);
        const data = await res.json();

        // 1. Render Line Chart
        renderClicksChart(data.daily_clicks);

        // 2. Render Partners Table
        renderTopPartners(data.top_partners);

        // 3. Update summary
        document.getElementById('monitoring-total-clicks').textContent = data.total_clicks || 0;

    } catch (e) {
        console.error('Error loading monitoring', e);
    }
}

let clicksChart = null;

function renderClicksChart(dailyData) {
    const ctx = document.getElementById('clicksChart');
    if (!ctx) return;

    if (clicksChart) {
        clicksChart.destroy();
    }

    const labels = dailyData.map(d => d.date);
    const dataPoints = dailyData.map(d => d.count);

    clicksChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Partner Clicks',
                data: dataPoints,
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function renderTopPartners(partners) {
    const list = document.getElementById('top-partners-list');
    if (!list) return;

    list.innerHTML = partners.map((p, i) => `
        <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee;">
            <span>${i + 1}. ${p.name}</span>
            <span style="font-weight: 600; color: #4f46e5;">${p.count} clicks</span>
        </div>
    `).join('');
}
