// AI Config Logic
async function loadAIConfig() {
    const botId = currentBotId;
    if (!botId) return;

    try {
        const res = await authFetch(`${API_BASE}/bots/${botId}`);
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
    const botId = currentBotId;
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
        const res = await authFetch(`${API_BASE}/bots/${botId}`, {
            method: 'PATCH',
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
    const botId = currentBotId;
    if (!botId) return;

    try {
        const res = await authFetch(`${API_BASE}/bots/${botId}/stats`);
        const stats = await res.json();

        document.getElementById('stats-users-total').textContent = stats.users.total;
        document.getElementById('stats-users-active').textContent = stats.users.active;
        document.getElementById('stats-partners-total').textContent = stats.partners.total;
        document.getElementById('stats-partners-active').textContent = stats.partners.active;

        // Also load Mini App analytics
        loadMiniAppAnalytics();
    } catch (e) {
        console.error('Error loading stats', e);
    }
}

// Mini App Analytics Logic
async function loadMiniAppAnalytics() {
    const botId = currentBotId;
    if (!botId) return;

    try {
        const start = document.getElementById('stats-date-start').value;
        const end = document.getElementById('stats-date-end').value;

        let query = `?days=30`; // fallback
        if (start && end) {
            query = `?start_date=${start}&end_date=${end}`;
            // Update title
            const headers = Array.from(document.querySelectorAll('h2'));
            const header = headers.find(h => h.textContent.includes('Mini App Analytics'));
            if (header) {
                // Optional: Update title to reflect range if needed, e.g.
                // header.textContent = `📱 Mini App Analytics (${start} to ${end})`;
            }
        }

        const res = await authFetch(`${API_BASE}/bots/${botId}/mini-app-analytics${query}`);
        const data = await res.json();

        // Update counters
        document.getElementById('stats-ma-events').textContent = data.total_events || 0;
        document.getElementById('stats-ma-sessions').textContent = data.total_sessions || 0;
        document.getElementById('stats-ma-wallets').textContent = data.wallet_connections || 0;
        document.getElementById('stats-ma-shares').textContent = data.share_events || 0;

        // Update funnel
        if (data.funnel) {
            document.getElementById('funnel-home').textContent = data.funnel.home_views || 0;
            document.getElementById('funnel-partners').textContent = data.funnel.partners_views || 0;
            document.getElementById('funnel-clicks').textContent = data.funnel.partner_clicks || 0;
            document.getElementById('funnel-rate1').textContent = `${data.funnel.home_to_partners_rate || 0}%`;
            document.getElementById('funnel-rate2').textContent = `${data.funnel.partners_to_click_rate || 0}%`;
        }

        // Update top partners
        const topPartnersEl = document.getElementById('stats-top-partners');
        if (topPartnersEl && data.top_partners) {
            if (data.top_partners.length === 0) {
                topPartnersEl.innerHTML = '<div style="color: #6b7280; font-style: italic;">No partner clicks yet</div>';
            } else {
                topPartnersEl.innerHTML = data.top_partners.map((p, i) => `
                    <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee;">
                        <span>${i + 1}. ${p.name}</span>
                        <span style="font-weight: 600; color: #8b5cf6;">${p.clicks} clicks</span>
                    </div>
                `).join('');
            }
        }

    } catch (e) {
        console.error('Error loading mini app analytics', e);
        // Set default values on error
        document.getElementById('stats-ma-events').textContent = '-';
        document.getElementById('stats-ma-sessions').textContent = '-';
        document.getElementById('stats-ma-wallets').textContent = '-';
        document.getElementById('stats-ma-shares').textContent = '-';
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
        const res = await authFetch(`${API_BASE}/bots/${currentBotId}/stats/analytics?days=30`);
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
