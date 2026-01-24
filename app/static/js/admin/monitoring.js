/**
 * Product Monitoring - separate JS module
 * TG Bot vs Mini App analytics
 */

const MONITORING_API = window.location.origin + '/api/v1/admin/monitoring';

// Chart instances
let dailyComparisonChart = null;
let platformChart = null;

/**
 * Load product monitoring data
 */
async function loadProductMonitoring() {
    if (!currentBotId) {
        console.log('No bot selected for monitoring');
        return;
    }

    try {
        const start = document.getElementById('monitoring-date-start').value;
        const end = document.getElementById('monitoring-date-end').value;

        let query = `?days=30`;
        if (start && end) {
            query = `?start_date=${start}&end_date=${end}`;
        }

        const res = await authFetch(`${MONITORING_API}/product/${currentBotId}${query}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        renderProductMonitoring(data);

    } catch (error) {
        console.error('Error loading product monitoring:', error);
        document.getElementById('monitoring-content').innerHTML = `
            <div style="padding: 20px; color: #ef4444;">
                Error loading monitoring data: ${error.message}
            </div>
        `;
    }
}

/**
 * Render monitoring dashboard
 */
function renderProductMonitoring(data) {
    const container = document.getElementById('monitoring-content');
    if (!container) return;

    const tg = data.telegram_bot;
    const ma = data.mini_app;

    container.innerHTML = `
        <!-- Overview Cards -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;">
            <!-- TG Bot Card -->
            <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: white; padding: 20px; border-radius: 12px;">
                <h3 style="margin: 0 0 15px 0; font-size: 16px;">🤖 Telegram Bot</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div>
                        <div style="font-size: 28px; font-weight: bold;">${tg.total_users}</div>
                        <div style="font-size: 12px; opacity: 0.8;">Total Users</div>
                    </div>
                    <div>
                        <div style="font-size: 28px; font-weight: bold;">${tg.commands_today}</div>
                        <div style="font-size: 12px; opacity: 0.8;">Commands Today</div>
                    </div>
                    <div>
                        <div style="font-size: 28px; font-weight: bold;">${tg.dau_7d}</div>
                        <div style="font-size: 12px; opacity: 0.8;">DAU (7d)</div>
                    </div>
                    <div>
                        <div style="font-size: 28px; font-weight: bold;">${tg.avg_response_time_seconds}s</div>
                        <div style="font-size: 12px; opacity: 0.8;">Avg Response</div>
                    </div>
                </div>
            </div>
            
            <!-- Mini App Card -->
            <div style="background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 20px; border-radius: 12px;">
                <h3 style="margin: 0 0 15px 0; font-size: 16px;">📱 Mini App</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div>
                        <div style="font-size: 28px; font-weight: bold;">${ma.sessions}</div>
                        <div style="font-size: 12px; opacity: 0.8;">Sessions (30d)</div>
                    </div>
                    <div>
                        <div style="font-size: 28px; font-weight: bold;">${ma.clicks_today}</div>
                        <div style="font-size: 12px; opacity: 0.8;">Clicks Today</div>
                    </div>
                    <div>
                        <div style="font-size: 28px; font-weight: bold;">${ma.dau_7d}</div>
                        <div style="font-size: 12px; opacity: 0.8;">DAU (7d)</div>
                    </div>
                    <div>
                        <div style="font-size: 28px; font-weight: bold;">${Object.values(ma.platform_breakdown).reduce((a, b) => a + b, 0)}</div>
                        <div style="font-size: 12px; opacity: 0.8;">Total Events</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Charts Row -->
        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 30px;">
            <!-- Daily Activity Chart -->
            <div style="background: white; padding: 20px; border-radius: 12px; border: 1px solid #e5e7eb;">
                <h3 style="margin: 0 0 15px 0; font-size: 14px;">📊 Daily Activity: Bot vs Mini App</h3>
                <div style="height: 250px; position: relative;">
                    <canvas id="dailyComparisonChart"></canvas>
                </div>
            </div>
            
            <!-- Platform Breakdown -->
            <div style="background: white; padding: 20px; border-radius: 12px; border: 1px solid #e5e7eb;">
                <h3 style="margin: 0 0 15px 0; font-size: 14px;">📱 Platform Breakdown</h3>
                <div style="height: 250px; position: relative;">
                    <canvas id="platformChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Details Row -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <!-- Command Usage -->
            <div style="background: white; padding: 20px; border-radius: 12px; border: 1px solid #e5e7eb;">
                <h3 style="margin: 0 0 15px 0; font-size: 14px;">⌨️ Top Commands</h3>
                ${renderCommandUsage(tg.command_usage)}
            </div>
            
            <!-- Language Distribution -->
            <div style="background: white; padding: 20px; border-radius: 12px; border: 1px solid #e5e7eb;">
                <h3 style="margin: 0 0 15px 0; font-size: 14px;">🌍 Languages</h3>
                ${renderLanguageDistribution(tg.language_distribution)}
            </div>
        </div>
    `;

    // Render charts after DOM is ready
    setTimeout(() => {
        renderDailyComparisonChart(data.daily_comparison);
        renderPlatformChart(ma.platform_breakdown);
    }, 100);
}

/**
 * Render command usage list
 */
function renderCommandUsage(usage) {
    if (!usage || Object.keys(usage).length === 0) {
        return '<div style="color: #9ca3af;">No commands recorded</div>';
    }
    return Object.entries(usage).map(([cmd, count]) => `
        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f3f4f6;">
            <span style="font-family: monospace; font-size: 12px;">${cmd}</span>
            <span style="font-weight: 600; color: #3b82f6;">${count}</span>
        </div>
    `).join('');
}

/**
 * Render language distribution
 */
function renderLanguageDistribution(dist) {
    if (!dist || Object.keys(dist).length === 0) {
        return '<div style="color: #9ca3af;">No language data</div>';
    }
    const colors = { uk: '#fbbf24', en: '#3b82f6', ru: '#ef4444', de: '#10b981', es: '#f97316' };
    return Object.entries(dist).map(([lang, count]) => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #f3f4f6;">
            <span>
                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: ${colors[lang] || '#9ca3af'}; margin-right: 8px;"></span>
                ${lang.toUpperCase()}
            </span>
            <span style="font-weight: 600;">${count}</span>
        </div>
    `).join('');
}

/**
 * Render daily comparison chart
 */
function renderDailyComparisonChart(dailyData) {
    const ctx = document.getElementById('dailyComparisonChart');
    if (!ctx) return;

    if (dailyComparisonChart) {
        dailyComparisonChart.destroy();
    }

    dailyComparisonChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dailyData.map(d => d.date.slice(5)), // MM-DD
            datasets: [
                {
                    label: 'Bot Commands',
                    data: dailyData.map(d => d.bot),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Mini App Events',
                    data: dailyData.map(d => d.mini_app),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

/**
 * Render platform pie chart
 */
function renderPlatformChart(breakdown) {
    const ctx = document.getElementById('platformChart');
    if (!ctx) return;

    if (platformChart) {
        platformChart.destroy();
    }

    const labels = ['iOS', 'Android', 'Web', 'Desktop', 'Other'];
    const data = [breakdown.ios, breakdown.android, breakdown.web, breakdown.desktop, breakdown.other];
    const colors = ['#000000', '#3ddc84', '#6366f1', '#475569', '#9ca3af'];

    platformChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });
}
