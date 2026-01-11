// Database (Users + Messages) Logic

let messagesOffset = 0;
const MESSAGES_PER_PAGE = 50;

async function loadDatabaseData() {
    loadUsersForMessagesFilter();
    loadMessages(0, true);
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

            const commandPreview = msg.command_content ? (msg.command_content.length > 20 ? msg.command_content.substring(0, 20) + '...' : msg.command_content) : '-';
            const commandExpandId = `cmd-${msg.id}`;

            row.innerHTML = `
                <td style="font-size: 9px;">${new Date(msg.created_at).toLocaleString('uk-UA')}</td>
                <td style="font-size: 9px;">${msg.user_id.substring(0, 8)}...</td>
                <td style="font-size: 9px;">${msg.external_id || '-'}</td>
                <td style="font-size: 9px;">${msg.username || '-'}</td>
                <td style="font-size: 9px;">${msg.device || '-'}</td>
                <td style="font-size: 9px;">${msg.language || '-'}</td>
                <td class="cell-wallet" style="font-size: 9px;">${msg.wallet_address || '-'}</td>
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
                <td style="font-size: 9px; max-width: 150px;">
                     <div onclick="toggleExpand('${commandExpandId}')" style="cursor: pointer; display: flex; align-items: center; gap: 4px;">
                        <span style="font-size: 9px; color: #6b7280;">${commandPreview}</span>
                        ${msg.custom_data?.partner_id ? `<span style="background: #e0f2fe; color: #0284c7; padding: 1px 3px; border-radius: 3px; font-size: 8px;">P: ${msg.custom_data.partner_id.substring(0, 5)}...</span>` : ''}
                        <span style="font-size: 8px; color: #9ca3af;">▼</span>
                    </div>
                    <div id="${commandExpandId}" style="display: none; margin-top: 4px; padding: 6px; background: #f9fafb; border-radius: 4px; font-size: 9px; white-space: pre-wrap; word-wrap: break-word;">
                        <div>${msg.command_content || '-'}</div>
                        ${msg.custom_data?.partner_id ? `<div style="margin-top: 4px; color: #0284c7;"><strong>Partner ID:</strong> ${msg.custom_data.partner_id}</div>` : ''}
                        ${msg.custom_data ? `<div style="margin-top: 4px; border-top: 1px solid #eee; padding-top: 2px; color: #9ca3af;">${JSON.stringify(msg.custom_data, null, 2)}</div>` : ''}
                    </div>
                </td>
                <td style="font-size: 9px;">${msg.source || '-'}</td>
                <td style="font-size: 9px;">${msg.response_content ? (msg.response_content.substring(0, 15) + '...') : '-'}</td>
                <td style="font-size: 9px;">${msg.response_time_seconds || '-'}s</td>
                <td style="font-size: 9px;">
                    <button onclick="showEditUserForm('${msg.user_id}')" style="background: #059669; color: white; padding: 2px 6px; border: none; border-radius: 3px; cursor: pointer;">Edit</button>
                    <button onclick="deleteUser('${msg.user_id}', '${msg.external_id}')" style="background: #dc2626; color: white; padding: 2px 6px; border: none; border-radius: 3px; cursor: pointer;">Hard Del</button>
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
            alert('Simulation failed: ' + result.message);
        }
    } catch (e) {
        alert('Error');
    }
}
