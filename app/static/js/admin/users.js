/**
 * Users Tab Logic
 * Handles unique user list, growth charts, and revenue stats.
 */

// Global chart instances
let userGrowthChart = null;
let revenueChart = null;

// Initialize Users Tab
function initUsersTab() {
    console.log('Initializing Users Tab');
    loadUsersAnalytics();
    loadUsersTable(); // Re-use or fetch users list
}

// Load Analytics (Charts & Top Cards)
async function loadUsersAnalytics() {
    const botId = getBotId();
    if (!botId) return;

    try {
        const response = await fetchWithAuth(`/api/v1/admin/bots/${botId}/users/analytics?days=30`);
        const data = await response.json();

        // Update Stats Cards
        updateUserStatsCards(data.stats);

        // Render Charts
        renderUserGrowthChart(data.chart_data);
        renderRevenueChart(data.chart_data);

    } catch (error) {
        console.error('Error loading user analytics:', error);
        showToast('Error loading analytics', 'error');
    }
}

// Update Top Cards
function updateUserStatsCards(stats) {
    // Total Users
    $('#users-total-count').text(stats.total_users.toLocaleString());

    // Total Buyers (Star Purchasers)
    $('#users-total-buyers').text(stats.total_buyers.toLocaleString());

    // Total Revenue
    $('#users-total-revenue').text(`${stats.total_revenue.toLocaleString()} ⭐️`);
}

// Render User Growth Chart
function renderUserGrowthChart(chartData) {
    const ctx = document.getElementById('userGrowthChart').getContext('2d');

    if (userGrowthChart) {
        userGrowthChart.destroy();
    }

    const labels = chartData.map(d => formatDateShort(d.date));
    const values = chartData.map(d => d.new_users);

    userGrowthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'New Users',
                data: values,
                borderColor: '#10b981', // Emerald 500
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { mode: 'index', intersect: false }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#374151' } },
                x: { grid: { display: false } }
            }
        }
    });
}

// Render Revenue Chart
function renderRevenueChart(chartData) {
    const ctx = document.getElementById('revenueChart').getContext('2d');

    if (revenueChart) {
        revenueChart.destroy();
    }

    const labels = chartData.map(d => formatDateShort(d.date));
    const values = chartData.map(d => d.revenue);

    revenueChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Revenue (Stars)',
                data: values,
                backgroundColor: '#f59e0b', // Amber 500
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#374151' } },
                x: { grid: { display: false } }
            }
        }
    });
}

// Load Unique Users Table
async function loadUsersTable() {
    const botId = getBotId();
    if (!botId) return;

    showLoader('#users-table-body');

    try {
        // Use existing endpoint but render differently
        const response = await fetchWithAuth(`/api/v1/admin/bots/${botId}/users?limit=100`);
        const users = await response.json();

        renderUsersTable(users);

    } catch (error) {
        console.error('Error loading users table:', error);
        $('#users-table-body').html('<tr><td colspan="7" class="text-center text-red-400 py-4">Error loading data</td></tr>');
    }
}

// Render Table Rows
function renderUsersTable(users) {
    const tbody = $('#users-table-body');
    tbody.empty();

    if (users.length === 0) {
        tbody.html('<tr><td colspan="7" class="text-center text-gray-500 py-4">No users found</td></tr>');
        return;
    }

    users.forEach(user => {
        const customData = user.custom_data || {};

        // Identify if bought stars
        const hasBought = customData.top_unlock_method === 'payment';
        const starsBadge = hasBought
            ? '<span class="px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded-full text-xs font-bold border border-yellow-500/30">⭐️ Bought</span>'
            : '<span class="text-gray-600">-</span>';

        // Status
        const topStatus = customData.top_status || 'locked';

        const row = `
            <tr class="border-b border-gray-700 hover:bg-gray-800/50 transition-colors">
                <td class="px-4 py-3 text-sm text-gray-300 font-mono">${formatDate(user.created_at)}</td>
                <td class="px-4 py-3">
                    <div class="flex items-center">
                        <div class="text-sm font-medium text-white">${escapeHtml(customData.first_name || '')} ${escapeHtml(customData.last_name || '')}</div>
                        ${customData.username ? `<div class="text-xs text-blue-400 ml-2">@${escapeHtml(customData.username)}</div>` : ''}
                    </div>
                    <div class="text-xs text-gray-500 font-mono">${user.external_id}</div>
                </td>
                <td class="px-4 py-3 text-center">
                    <span class="px-2 py-1 bg-gray-700 rounded text-xs text-gray-300 font-mono uppercase">${user.language_code || '??'}</span>
                </td>
                <td class="px-4 py-3 text-center">
                    ${starsBadge}
                </td>
                <td class="px-4 py-3 text-center">
                    <div class="text-sm text-gray-300">${customData.total_invited || 0} invites</div>
                </td>
                <td class="px-4 py-3 text-center">
                    <span class="px-2 py-1 rounded text-xs ${topStatus === 'open' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}">
                        ${topStatus.toUpperCase()}
                    </span>
                </td>
                <td class="px-4 py-3 text-right">
                    <button onclick="openUserModal('${user.id}')" class="text-blue-400 hover:text-blue-300 mr-2">
                        <i class="fas fa-edit"></i>
                    </button>
                </td>
            </tr>
        `;
        tbody.append(row);
    });
}

// Helper: Short Date Format (Jan 24)
function formatDateShort(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Make globally available
window.initUsersTab = initUsersTab;
