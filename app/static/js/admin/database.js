// Database (Users + Messages) Logic

let messagesOffset = 0;
const MESSAGES_PER_PAGE = 50;

// Cache for partner names
let partnersCache = new Map();

async function loadDatabaseData() {
    await loadPartnersForCache(); // Load partners first
    loadUsersForMessagesFilter();
    loadMessages(0, true);
}

async function loadPartnersForCache() {
    if (!currentBotId) return;
    try {
        const res = await fetch(`${API_BASE}/bots/${currentBotId}/partners?active_only=false&limit=500`);
        const partners = await res.json();
        partnersCache.clear();
        partners.forEach(p => {
            partnersCache.set(p.id, p.data?.bot_name || 'Unknown Partner');
        });
        console.log(`[Database] Loaded ${partnersCache.size} partners into cache`);
    } catch (e) {
        console.error('[Database] Failed to load partners:', e);
    }
}

function parseAction(customData) {
    if (!customData) return null;

    // Partner click
    if (customData.partner_id) {
        const partnerName = partnersCache.get(customData.partner_id) || customData.partner_id.substring(0, 8);
        return `🔗 Partner: ${partnerName}`;
    }

    // Share event
    if (customData.share_type) {
        return `📤 Share: ${customData.share_type}`;
    }

    // Wallet saved
    if (customData.wallet_address) {
        return `💰 Wallet Saved`;
    }

    // Buy TOP
    if (customData.action === 'buy_top') {
        return `💎 Buy TOP`;
    }

    return null;
}

async function loadMessages(offset = 0, reset = false) {
    if (!currentBotId) return;

    const filterUser = document.getElementById('messages-user-filter').value;
    const filterCommand = document.getElementById('messages-command-filter').value;

    let url = `${API_BASE}/bots/${currentBotId}/messages?skip=${offset}&limit=${MESSAGES_PER_PAGE}`;
    if (filterUser) url += `&user_id=${filterUser}`;
    if (filterCommand) url += `&command=${filterCommand}`;

    try {
        const res = await fetch(url);
        const messages = await res.json();
        const tbody = document.getElementById('database-messages-tbody');

        if (reset) {
            tbody.innerHTML = '';
            messagesOffset = 0;
            // Use a Map for usersData to avoid duplicates
            window.usersDataMap = new Map();
        }

        if (messages.length === 0 && reset) {
            tbody.innerHTML = '<tr><td colspan="17" style="padding: 20px; text-align: center;">No messages found</td></tr>';
            document.getElementById('database-messages-more').style.display = 'none';
            return;
        }

        // Cache users from messages
        messages.forEach(msg => {
            if (!window.usersDataMap.has(msg.user_id)) {
                window.usersDataMap.set(msg.user_id, {
                    id: msg.user_id,
                    external_id: msg.external_id,
                    username: msg.username,
                    first_name: msg.first_name,
                    last_name: msg.last_name,
                    top_status: msg.top_status,
                    total_invited: msg.total_invited,
                    wallet_address: msg.wallet_address,
                    balance: msg.balance,
                    is_active: msg.is_active
                });
            }
        });
        // Maintain window.usersData for backward compatibility if needed, but derived from Map
        window.usersData = Array.from(window.usersDataMap.values());

        messages.forEach(msg => {
            const row = document.createElement('tr');
            row.id = `msg-row-${msg.id}`;
            row.setAttribute('data-user-id', msg.user_id);

            // --- UI POLISH START ---

            // 1. COMMAND BADGES
            const rawCommand = msg.command_content || '-';
            let commandStyle = 'color: #374151; font-weight: 500;'; // Default
            let commandBg = '#f3f4f6';

            if (rawCommand.includes('/partners')) { commandBg = '#dcfce7'; commandStyle = 'color: #166534; font-weight: 600;'; }
            else if (rawCommand.includes('/top')) { commandBg = '#dbeafe'; commandStyle = 'color: #1e40af; font-weight: 600;'; }
            else if (rawCommand.includes('/start')) { commandBg = '#fef9c3'; commandStyle = 'color: #854d0e; font-weight: 600;'; }
            else if (rawCommand.includes('mini_app')) { commandBg = '#f3e8ff'; commandStyle = 'color: #6b21a8; font-weight: 500;'; }

            const commandBadge = `<span style="background: ${commandBg}; ${commandStyle} padding: 2px 6px; border-radius: 4px; font-size: 8px;">${rawCommand.length > 25 ? rawCommand.substring(0, 25) + '...' : rawCommand}</span>`;

            const commandExpandId = `cmd-${msg.id}`;

            // 2. WALLET TRUNCATION
            let walletDisplay = '-';
            if (msg.wallet_address) {
                const w = msg.wallet_address;
                walletDisplay = w.length > 12
                    ? `<span title="${w}" style="font-family: monospace; color: #4b5563; cursor: help;">${w.substring(0, 4)}...${w.substring(w.length - 4)}</span>`
                    : w;
            }

            // 3. SOURCE BADGE (Mini App vs Telegram)
            let sourceBadge = '-';
            if (msg.source) {
                if (msg.source.includes('mini_app')) {
                    sourceBadge = '<span style="background: #f3e8ff; color: #6b21a8; padding: 2px 6px; border-radius: 4px; font-size: 8px; font-weight: 600;">📱 Mini App</span>';
                } else if (msg.source.includes('telegram')) {
                    sourceBadge = '<span style="background: #dbeafe; color: #1e40af; padding: 2px 6px; border-radius: 4px; font-size: 8px; font-weight: 600;">💬 Telegram</span>';
                } else {
                    sourceBadge = `<span style="color: #6b7280; font-size: 8px;">${msg.source}</span>`;
                }
            }

            // 4. RESPONSE STATUS BADGE (with expandable content)
            const isMiniAppEvent = (msg.source && msg.source.includes('mini_app')) || (rawCommand.startsWith('/'));
            const responseExpandId = `resp-${msg.id}`;
            let responseDisplay = '-';
            let hasError = false; // Track if this row has an error

            if (!msg.response_content && isMiniAppEvent) {
                // Event log (no response expected)
                responseDisplay = '<span style="background: #f3f4f6; color: #6b7280; padding: 2px 6px; border-radius: 4px; font-size: 8px; font-weight: 500;">📝 Event Log</span>';
            } else if (msg.response_content) {
                // Check for error indicators in response
                hasError = msg.response_content.toLowerCase().includes('error') ||
                    msg.response_content.toLowerCase().includes('failed') ||
                    msg.response_content.toLowerCase().includes('exception');

                if (hasError) {
                    responseDisplay = `<div onclick="toggleExpand('${responseExpandId}')" style="cursor: pointer; display: flex; align-items: center; gap: 4px;">
                        <span style="background: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 4px; font-size: 8px; font-weight: 600;">❌ Error</span>
                        <span style="font-size: 8px; color: #9ca3af;">▼</span>
                    </div>`;
                } else {
                    responseDisplay = `<div onclick="toggleExpand('${responseExpandId}')" style="cursor: pointer; display: flex; align-items: center; gap: 4px;">
                        <span style="background: #d1fae5; color: #065f46; padding: 2px 6px; border-radius: 4px; font-size: 8px; font-weight: 600;">✅ Success</span>
                        <span style="font-size: 8px; color: #9ca3af;">▼</span>
                    </div>`;
                }
            } else {
                // No response yet
                responseDisplay = '<span style="background: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 4px; font-size: 8px; font-weight: 500;">⏳ Pending</span>';
            }

            // 5. RESPONSE TIME COLOR CODING
            // For Mini App events, response_time is meaningless (they're not request-response pairs)
            const isMiniAppSource = msg.source && msg.source.includes('mini_app');
            let timeDisplay = '-';

            if (isMiniAppSource) {
                // Mini App events: no response time calculation makes sense
                timeDisplay = '<span style="color: #9ca3af; font-size: 8px;">—</span>';
            } else if (msg.response_time_seconds) {
                const time = msg.response_time_seconds;
                let timeStyle = '';

                if (time < 2) {
                    // Fast (< 2s) - Green
                    timeStyle = 'background: #d1fae5; color: #065f46;';
                } else if (time < 5) {
                    // Medium (2-5s) - Yellow
                    timeStyle = 'background: #fef3c7; color: #92400e;';
                } else {
                    // Slow (> 5s) - Red
                    timeStyle = 'background: #fee2e2; color: #991b1b;';
                }

                timeDisplay = `<span style="${timeStyle} padding: 2px 6px; border-radius: 4px; font-size: 8px; font-weight: 600;">${time}s</span>`;
            } else if (!msg.response_content && isMiniAppEvent) {
                timeDisplay = '<span style="color: #9ca3af; font-size: 8px;">-</span>';
            }

            // 6. ERROR ROW HIGHLIGHTING
            if (hasError) {
                row.style.backgroundColor = '#fef2f2'; // Light red background for error rows
                row.style.borderLeft = '3px solid #ef4444'; // Red left border
            }

            // 7. DEVICE/PLATFORM DISPLAY (from custom_data.platform for Mini App events)
            let deviceDisplay = msg.device || '-';
            const msgCustomData = msg.custom_data || {};
            if (msgCustomData.platform || msg.device) {
                const platform = (msgCustomData.platform || msg.device || '').toLowerCase();
                let platformBadge = '';
                if (platform === 'ios') {
                    platformBadge = '<span style="background: #000; color: white; padding: 1px 4px; border-radius: 3px; font-size: 7px; font-weight: 600;">iOS</span>';
                } else if (platform === 'android') {
                    platformBadge = '<span style="background: #3ddc84; color: white; padding: 1px 4px; border-radius: 3px; font-size: 7px; font-weight: 600;">Android</span>';
                } else if (platform === 'web' || platform === 'weba' || platform === 'webk') {
                    platformBadge = '<span style="background: #6366f1; color: white; padding: 1px 4px; border-radius: 3px; font-size: 7px; font-weight: 600;">Web</span>';
                } else if (platform === 'tdesktop' || platform === 'macos') {
                    platformBadge = '<span style="background: #475569; color: white; padding: 1px 4px; border-radius: 3px; font-size: 7px; font-weight: 600;">Desktop</span>';
                } else if (platform.includes('telegram') || platform.includes('miniapp')) {
                    platformBadge = '<span style="background: #0088cc; color: white; padding: 1px 4px; border-radius: 3px; font-size: 7px; font-weight: 600;">TG Mini</span>';
                } else if (platform) {
                    // Truncate long platform names
                    const shortPlatform = platform.length > 8 ? platform.substring(0, 8) + '..' : platform;
                    platformBadge = `<span style="background: #9ca3af; color: white; padding: 1px 4px; border-radius: 3px; font-size: 7px;">${shortPlatform}</span>`;
                }
                deviceDisplay = platformBadge || '-';
            }

            // --- UI POLISH END ---

            row.innerHTML = `
                <td style="font-size: 8px; line-height: 1.3;">
                    ${new Date(msg.created_at).toLocaleDateString('uk-UA')}<br>
                    <span style="color: #6b7280;">${new Date(msg.created_at).toLocaleTimeString('uk-UA')}</span>
                </td>
                <td style="font-size: 9px;">${msg.user_id.substring(0, 6)}...</td>
                <td style="font-size: 9px;">${msg.external_id || '-'}</td>
                <td style="font-size: 9px;">${msg.username || '-'}</td>
                <td style="font-size: 9px;">${deviceDisplay}</td>
                <td style="font-size: 9px;">${msg.language || '-'}</td>
                <td class="cell-wallet" style="font-size: 9px;">${walletDisplay}</td>
                <td class="cell-invited" style="font-size: 9px; text-align: center;">${msg.total_invited || 0}</td>
                <td class="cell-top" style="font-size: 9px; text-align: center;">
                    ${msg.top_status === 'open'
                    ? '<span style="background: #10b981; color: white; padding: 2px 6px; border-radius: 4px;">OPEN</span>'
                    : '<span style="background: #ef4444; color: white; padding: 2px 6px; border-radius: 4px;">LOCKED</span>'}
                </td>
                <td class="cell-balance" style="font-size: 9px;">${msg.balance || 0}</td>
                <td style="font-size: 9px;">${msg.is_active ? '✅' : '❌'}</td>
                <td style="font-size: 9px;">${new Date(msg.created_at).toLocaleDateString()}</td>
                <td style="font-size: 9px;">${msg.last_activity ? new Date(msg.last_activity).toLocaleDateString() : '-'}</td>
                <td style="font-size: 9px; max-width: 180px;">
                     <div onclick="toggleExpand('${commandExpandId}')" style="cursor: pointer; display: flex; align-items: center; gap: 6px;">
                        ${commandBadge}
                        ${msg.custom_data?.partner_id ? (() => {
                    const partnerName = partnersCache.get(msg.custom_data.partner_id);
                    if (partnerName) {
                        return `<span style="background: #e0f2fe; color: #0284c7; padding: 1px 3px; border-radius: 3px; font-size: 8px;">🤖 ${partnerName.substring(0, 15)}${partnerName.length > 15 ? '...' : ''}</span>`;
                    }
                    return `<span style="background: #e0f2fe; color: #0284c7; padding: 1px 3px; border-radius: 3px; font-size: 8px;">P: ${msg.custom_data.partner_id.substring(0, 5)}...</span>`;
                })() : ''}
                        <span style="font-size: 8px; color: #9ca3af;">▼</span>
                    </div>
                    <div id="${commandExpandId}" style="display: none; margin-top: 4px; padding: 6px; background: #f9fafb; border-radius: 4px; font-size: 9px; white-space: pre-wrap; word-wrap: break-word; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                        <div style="font-weight:bold; margin-bottom:2px;">Full Command:</div>
                        <div style="color:#4b5563;">${msg.command_content || '-'}</div>
                        ${msg.custom_data?.partner_id ? (() => {
                    const partnerName = partnersCache.get(msg.custom_data.partner_id);
                    return `<div style="margin-top: 4px; color: #0284c7;"><strong>Partner:</strong> ${partnerName || msg.custom_data.partner_id}</div>`;
                })() : ''}
                        ${msg.custom_data ? `<div style="margin-top: 4px; border-top: 1px solid #eee; padding-top: 2px; color: #9ca3af;">${JSON.stringify(msg.custom_data, null, 2)}</div>` : ''}
                    </div>
                </td>
                <td style="font-size: 9px;">${sourceBadge}</td>
                <td style="font-size: 9px; max-width: 120px;">
                    ${responseDisplay}
                    ${msg.response_content ? `<div id="${responseExpandId}" style="display: none; margin-top: 4px; padding: 6px; background: #f9fafb; border-radius: 4px; font-size: 9px; white-space: pre-wrap; word-wrap: break-word; box-shadow: 0 1px 2px rgba(0,0,0,0.05); max-height: 200px; overflow-y: auto;">
                        <div style="font-weight:bold; margin-bottom:2px;">Full Response:</div>
                        <div style="color:#4b5563;">${msg.response_content}</div>
                    </div>` : ''}
                </td>
                <td style="font-size: 9px;">${timeDisplay}</td>
                <td style="font-size: 9px; white-space: nowrap;">
                    <button onclick="showEditUserForm('${msg.user_id}')" style="background: #059669; color: white; padding: 1px 4px; border: none; border-radius: 2px; cursor: pointer; font-size: 7px;">Edit</button>
                    <button onclick="deleteUser('${msg.user_id}', '${msg.external_id}')" style="background: #dc2626; color: white; padding: 1px 4px; border: none; border-radius: 2px; cursor: pointer; font-size: 7px;">Del</button>
                </td>
            `;
            tbody.appendChild(row);
        });

        messagesOffset += messages.length;
        document.getElementById('database-messages-more').style.display = messages.length === MESSAGES_PER_PAGE ? 'block' : 'none';

    } catch (e) {
        console.error(e);
    }
}

function loadMoreMessages() {
    loadMessages(messagesOffset, false);
}

function toggleExpand(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function loadUsersForMessagesFilter() {
    if (!currentBotId) return;
    try {
        const res = await fetch(`${API_BASE}/bots/${currentBotId}/users?skip=0&limit=100`);
        const users = await res.json();
        const select = document.getElementById('messages-user-filter');
        let options = '<option value="">All users</option>';
        users.forEach(u => {
            options += `<option value="${u.id}">${u.username || u.external_id}</option>`;
        });
        select.innerHTML = options;
    } catch (e) {
        console.error(e);
    }
}

// User Actions
function showEditUserForm(userId) {
    const user = window.usersData.find(u => u.id === userId);
    if (!user) return;

    document.getElementById('edit-user-id').value = user.id;
    document.getElementById('edit-user-total-invited').value = user.total_invited || 0;
    document.getElementById('edit-user-top-status').value = user.top_status || 'locked';
    document.getElementById('edit-user-top-unlock-method').value = user.top_unlock_method || '';
    document.getElementById('edit-user-wallet-address').value = user.wallet_address || '';
    document.getElementById('edit-user-balance').value = user.balance || 0;

    document.getElementById('edit-user-form').style.display = 'block';
    document.getElementById('edit-user-form').scrollIntoView({ behavior: 'smooth' });
}

function hideEditUserForm() {
    document.getElementById('edit-user-form').style.display = 'none';
}

async function updateUser() {
    const userId = document.getElementById('edit-user-id').value;
    const topStatus = document.getElementById('edit-user-top-status').value;
    const topUnlockMethod = document.getElementById('edit-user-top-unlock-method').value;
    const totalInvited = document.getElementById('edit-user-total-invited').value;
    const walletAddress = document.getElementById('edit-user-wallet-address').value;
    const balance = document.getElementById('edit-user-balance').value;

    const params = new URLSearchParams({
        top_status: topStatus,
        top_unlock_method: topUnlockMethod,
        total_invited: totalInvited,
        wallet_address: walletAddress,
        balance: balance
    });

    try {
        const res = await fetch(`${API_BASE}/bots/${currentBotId}/users/${userId}?${params}`, { method: 'PATCH' });
        if (res.ok) {
            showMessage('database-message', 'User updated successfully!');
            hideEditUserForm();

            // OPTIMIZED: Update only the rows for this user instead of full reload
            updateUserRowsInTable(userId, {
                top_status: topStatus,
                total_invited: totalInvited,
                wallet_address: walletAddress,
                balance: balance
            });
        } else {
            alert('Failed to update user');
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

function updateUserRowsInTable(userId, newData) {
    // 1. Update the cache
    if (window.usersDataMap && window.usersDataMap.has(userId)) {
        const user = window.usersDataMap.get(userId);
        Object.assign(user, newData);
        window.usersData = Array.from(window.usersDataMap.values());
    }

    // 2. Update the DOM rows
    const rows = document.querySelectorAll(`tr[data-user-id="${userId}"]`);
    rows.forEach(row => {
        if (newData.top_status !== undefined) {
            const topCell = row.querySelector('.cell-top');
            if (topCell) {
                topCell.innerHTML = newData.top_status === 'open'
                    ? '<span style="background: #10b981; color: white; padding: 2px 6px; border-radius: 4px;">OPEN</span>'
                    : '<span style="background: #ef4444; color: white; padding: 2px 6px; border-radius: 4px;">LOCKED</span>';
            }
        }
        if (newData.total_invited !== undefined) {
            const invitedCell = row.querySelector('.cell-invited');
            if (invitedCell) invitedCell.textContent = newData.total_invited;
        }
        if (newData.wallet_address !== undefined) {
            const walletCell = row.querySelector('.cell-wallet');
            if (walletCell) walletCell.textContent = newData.wallet_address || '-';
        }
        if (newData.balance !== undefined) {
            const balanceCell = row.querySelector('.cell-balance');
            if (balanceCell) balanceCell.textContent = newData.balance || 0;
        }
    });

    console.log(`Updated ${rows.length} rows for user ${userId}`);
}

async function deleteUser(userId, externalId) {
    if (!confirm(`⚠️ PERMANENTLY DELETE user ${externalId} and ALL related messages/analytics? This cannot be undone!`)) return;
    try {
        const res = await fetch(`${API_BASE}/bots/${currentBotId}/users/${userId}`, { method: 'DELETE' });
        if (res.ok) {
            alert('Deleted!');
            loadMessages(0, true);
        }
    } catch (e) {
        alert('Error deleting');
    }
}

async function resetInvites() {
    const userId = document.getElementById('edit-user-id').value;
    if (!confirm('Reset invites to 0?')) return;

    try {
        const res = await fetch(`${API_BASE}/bots/${currentBotId}/users/${userId}/reset-invites`, { method: 'POST' });
        if (res.ok) {
            showMessage('database-message', 'Invites reset successfully!');
            hideEditUserForm();

            // OPTIMIZED: Update only rows for this user
            updateUserRowsInTable(userId, {
                total_invited: 0,
                top_status: 'locked'
            });
        }
    } catch (e) {
        alert('Error');
    }
}

async function test5Invites() {
    const userId = document.getElementById('edit-user-id').value;
    if (!confirm('Simulate 5 invites?')) return;

    try {
        const res = await fetch(`${API_BASE}/bots/${currentBotId}/users/${userId}/test-5-invites`, { method: 'POST' });
        const result = await res.json();

        if (result.success) {
            showMessage('database-message', 'Test 5 Invites: SUCCESS! TOP unlocked.');
            hideEditUserForm();

            // OPTIMIZED: Update rows with fresh data
            updateUserRowsInTable(userId, {
                total_invited: result.final_state.total_invited,
                top_status: result.final_state.top_status
            });
        } else {
            showMessage('database-message', 'Test failed: ' + result.message);
        }
    } catch (e) {
        showMessage('database-message', 'Error: ' + e.message);
    }
}

// CSV Export Function
function exportMessagesToCSV() {
    const tbody = document.getElementById('database-messages-tbody');
    const rows = tbody.querySelectorAll('tr');

    if (rows.length === 0) {
        alert('No messages to export');
        return;
    }

    // CSV Headers
    const headers = [
        'Timestamp', 'User ID', 'External ID', 'Username', 'Device', 'Language',
        'Wallet', 'Invited', 'TOP Status', 'Balance', 'Active', 'Created', 'Last Activity',
        'Command', 'Source', 'Response Status', 'Response Time', 'Partner'
    ];

    let csvContent = headers.join(',') + '\n';

    // Extract data from visible rows
    rows.forEach(row => {
        if (row.cells.length < 17) return; // Skip invalid rows

        const cells = Array.from(row.cells).map((cell, idx) => {
            let text = cell.textContent.trim();

            // Clean up badges and special characters
            text = text.replace(/[📱💬✅❌⏳📝🟢🟡🔴🤖]/g, ''); // Remove emojis
            text = text.replace(/▼/g, ''); // Remove expand arrows
            text = text.replace(/Mini App|Telegram|Success|Error|Pending|Event Log/g, (match) => match);

            // Escape quotes and commas
            if (text.includes(',') || text.includes('"') || text.includes('\n')) {
                text = '"' + text.replace(/"/g, '""') + '"';
            }

            return text;
        });

        csvContent += cells.slice(0, 17).join(',') + '\n';
    });

    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', `messages_export_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showMessage('database-message', `Exported ${rows.length} messages to CSV`, 'success');
}
