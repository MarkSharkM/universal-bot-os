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

async function loadGlobalBotSelector() {
    try {
        // Check cache first
        const cached = getCached('bots');
        if (cached) {
            const select = document.getElementById('global-bot-select');
            if (select) {
                select.innerHTML = '<option value="">Select Bot</option>' +
                    cached.map(bot => `<option value="${bot.id}">${bot.name}</option>`).join('');
                if (cached.length > 0) {
                    select.value = cached[0].id;
                    onGlobalBotChange();
                }
            }
            return;
        }

        const res = await fetch(`${API_BASE}/bots?limit=50`);
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        const bots = await res.json();
        setCache('bots', bots); // Cache for 5 minutes

        const select = document.getElementById('global-bot-select');
        if (!select) return;

        select.innerHTML = '<option value="">Select Bot</option>' +
            bots.map(bot => `<option value="${bot.id}">${bot.name}</option>`).join('');

        // Auto-select first bot if exists
        if (bots.length > 0) {
            select.value = bots[0].id;
            onGlobalBotChange();
        } else {
            select.innerHTML = '<option value="">No bots found</option>';
        }
    } catch (error) {
        console.error('Error loading bots:', error);
        const select = document.getElementById('global-bot-select');
        if (select) {
            select.innerHTML = '<option value="">Error loading bots</option>';
        }
    }
}

function onGlobalBotChange() {
    const select = document.getElementById('global-bot-select');
    currentBotId = select.value;
    const selectedOption = select.options[select.selectedIndex];
    currentBotName = selectedOption ? selectedOption.text : '-';
    document.getElementById('database-bot-name').textContent = currentBotName;

    // Update all bot selects in other tabs
    ['partners-bot-select', 'ai-bot-select', 'stats-bot-select'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = currentBotId;
    });

    // Clear messages when bot changes
    const messagesList = document.getElementById('database-messages-list');
    if (messagesList) messagesList.innerHTML = '<div style="padding: 20px; text-align: center; color: #6b7280;">Select a bot to view messages</div>';

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

// Tab switching
function showTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
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
        loadBotsForSelect('ai-bot-select', () => {
            if (currentBotId) {
                document.getElementById('ai-bot-select').value = currentBotId;
                loadAIConfig();
            }
        });
    }
    if (tabName === 'stats') {
        loadBotsForSelect('stats-bot-select', () => {
            if (currentBotId) {
                document.getElementById('stats-bot-select').value = currentBotId;
                loadStats();
            }
        });
    }
    if (tabName === 'monitoring') {
        if (currentBotId) {
            loadMonitoring();
        }
    }
}


// Database sub-tabs switching (removed - no tabs needed)
function showDatabaseTab(tabName) {
    // No tabs anymore - always show users+messages combined
    if (currentBotId) {
        loadUsersForMessagesFilter();
        loadMessages(0, true);
        loadUsersForMessagesFilter();
    }
}

// Show stats tab for specific bot
function showStatsTab(botId) {
    // Switch to stats tab
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.getElementById('stats').classList.add('active');
    // Find and activate stats tab button
    const statsTab = document.querySelector('.tab[onclick*="stats"]');
    if (statsTab) statsTab.classList.add('active');

    // Load bots for select and set the bot
    loadBotsForSelect('stats-bot-select', () => {
        document.getElementById('stats-bot-select').value = botId;
        loadStats();
    });
}

// Bots
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
            // Reload bots list after a short delay
            setTimeout(() => loadBots(), 500);
        } else {
            const errorData = await res.json().catch(() => ({ detail: 'Unknown error' }));
            showMessage('bots-message', 'Error: ' + (errorData.detail || 'Failed to delete bot'), 'error');
        }
    } catch (error) {
        showMessage('bots-message', 'Error: ' + error.message, 'error');
    }
}

// Partners
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

function parsePastedData() {
    const pastedText = document.getElementById('partner-paste-data').value.trim();
    if (!pastedText) {
        alert('Please paste data from Google Sheets first');
        return;
    }

    // Split by tab (Google Sheets uses tabs when copying)
    const parts = pastedText.split('\t');

    if (parts.length < 9) {
        alert('Invalid format. Expected at least 9 columns separated by tabs.');
        return;
    }

    // Map columns from Google Sheets:
    // 0: Bot Name
    // 1: Description (UK)
    // 2: Description (EN)
    // 3: Description (RU)
    // 4: Description (DE)
    // 5: Description (ES)
    // 6: Referral Link
    // 7: RefParam (skip)
    // 8: Commission
    // 9: Category
    // 10: Active
    // 11: Duration
    // 12: Verified
    // ... (skip clicks, added, owner, доход)
    // Last: ROI Score

    // Clean and parse data
    const botName = (parts[0] || '').trim();
    const descUk = (parts[1] || '').trim();
    const descEn = (parts[2] || '').trim();
    const descRu = (parts[3] || '').trim();
    const descDe = (parts[4] || '').trim();
    const descEs = (parts[5] || '').trim();
    const referralLink = (parts[6] || '').trim();
    // Skip parts[7] - RefParam
    const commission = parseFloat((parts[8] || '0').replace(/\s/g, '').replace(',', '.')) || 0;
    const category = (parts[9] || 'NEW').trim().toUpperCase();
    const active = (parts[10] || 'Yes').trim();
    // Parse Duration (parts[11])
    const duration = (parts[11] || '').trim().replace(/\s/g, '') || '';
    const verified = (parts[12] || 'Yes').trim();

    // ROI Score is usually the last column (or second to last)
    let roiScore = parts[parts.length - 1] || '0';
    // If last is 1,0 and second to last is 1,60, use second to last
    if (parts.length >= 2 && parts[parts.length - 1] === '1,0' && parts[parts.length - 2]) {
        roiScore = parts[parts.length - 2];
    }
    // Handle comma as decimal separator (1,60 -> 1.60) and remove spaces
    const roiScoreValue = parseFloat(roiScore.replace(/\s/g, '').replace(',', '.')) || 0;

    // Fill form (with null checks)
    const setValue = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.value = value;
    };

    setValue('partner-name', botName);
    setValue('partner-description', descUk);
    setValue('partner-description-en', descEn);
    setValue('partner-description-ru', descRu);
    setValue('partner-description-de', descDe);
    setValue('partner-description-es', descEs);
    setValue('partner-link', referralLink);
    setValue('partner-commission', commission);
    setValue('partner-category', category);
    setValue('partner-active', active);
    setValue('partner-verified', verified);
    setValue('partner-roi', roiScoreValue);
    setValue('partner-duration', duration);

    // Enhanced highlight animation
    const pasteField = document.getElementById('partner-paste-data');
    pasteField.style.background = '#d1fae5';
    pasteField.style.borderColor = '#22c55e';
    pasteField.style.borderWidth = '2px';
    pasteField.style.transition = 'all 0.3s ease';

    // Animate border pulse
    let pulseCount = 0;
    const pulseInterval = setInterval(() => {
        pulseCount++;
        if (pulseCount % 2 === 0) {
            pasteField.style.borderColor = '#22c55e';
        } else {
            pasteField.style.borderColor = '#16a34a';
        }
        if (pulseCount >= 6) {
            clearInterval(pulseInterval);
            setTimeout(() => {
                pasteField.style.background = '';
                pasteField.style.borderColor = '#0284c7';
                pasteField.style.borderWidth = '1px';
            }, 500);
        }
    }, 200);

    // Show preview card
    showPartnerPreview({
        botName, descUk, descEn, descRu, descDe, descEs,
        referralLink, commission, category, active, verified, roiScore: roiScoreValue, duration
    });

    console.log('Form filled from Google Sheets data:', {
        botName, commission, category, active, verified, roiScore: roiScoreValue
    });
}

async function loadPartners() {
    const botId = document.getElementById('partners-bot-select').value;
    if (!botId) return;

    try {
        // Check if we should show inactive partners
        const showInactive = document.getElementById('show-inactive-partners')?.checked || false;
        const activeOnly = !showInactive;
        const url = `${API_BASE}/bots/${botId}/partners?active_only=${activeOnly}`;
        console.log('Loading partners from:', url);
        const res = await fetch(url);

        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: 'Failed to load partners' }));
            showMessage('partners-message', 'Error loading partners: ' + (error.detail || 'Unknown error'), 'error');
            return;
        }

        const partners = await res.json();
        console.log('Loaded partners:', partners.length);

        // Sort by ROI Score
        partners.sort((a, b) => {
            const roiA = parseFloat(a.roi_score || 0);
            const roiB = parseFloat(b.roi_score || 0);
            return partnersROISortDesc ? (roiB - roiA) : (roiA - roiB);
        });

        const tbody = document.getElementById('partners-tbody');
        tbody.innerHTML = partners.map(p => {
            const refLink = p.referral_link || '';
            return `
            <tr>
                <td><strong>${p.bot_name}</strong></td>
                <td><span style="background: ${p.category === 'TOP' ? '#fbbf24' : '#60a5fa'}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">${p.category}</span></td>
                <td style="word-break: break-all; max-width: 300px; padding: 10px;">
                    <a href="${refLink}" target="_blank" style="font-size: 11px; color: #2563eb; text-decoration: none; line-height: 1.4; display: block;">
                        ${refLink || '-'}
                    </a>
                </td>
                <td>${p.commission}%</td>
                <td>${p.active === 'Yes' ? '✅' : '❌'}</td>
                <td>${p.verified === 'Yes' ? '✅' : '❌'}</td>
                <td>${p.duration ? String(p.duration).replace(/\s/g, '') : '-'}</td>
                <td>${p.roi_score || 0}</td>
                <td>
                    <button onclick="showEditPartnerForm('${p.id}')" style="background: #059669; margin-right: 5px; font-size: 12px; padding: 6px 10px;">Edit</button>
                    <button class="btn-danger" onclick="deletePartner('${botId}', '${p.id}')" style="font-size: 12px; padding: 6px 10px;">Delete</button>
                </td>
            </tr>
            `;
        }).join('');

        // Store partners data for editing
        window.partnersData = partners;
    } catch (error) {
        showMessage('partners-message', 'Error loading partners: ' + error.message, 'error');
    }
}

let partnersROISortDesc = true;

function sortPartnersByROI() {
    partnersROISortDesc = !partnersROISortDesc;
    const icon = document.getElementById('roi-sort-icon');
    if (icon) {
        icon.textContent = partnersROISortDesc ? '⬇' : '⬆';
    }
    loadPartners();
}

async function updatePartnerRowInTable(partnerId, updatedPartner) {
    // Update only row for specific partner_id instead of reloading entire table
    if (!updatedPartner) {
        // Fallback to full reload if partner data not provided
        await loadPartners();
        return;
    }

    try {
        const tbody = document.getElementById('partners-tbody');
        const rows = tbody.querySelectorAll('tr');
        let updated = false;

        rows.forEach(row => {
            const editButton = row.querySelector('button[onclick*="showEditPartnerForm"]');
            if (editButton) {
                const onclickAttr = editButton.getAttribute('onclick');
                const match = onclickAttr.match(/showEditPartnerForm\('([^']+)'\)/);
                if (match && match[1] === partnerId) {
                    // Found the row - update it
                    const refLink = updatedPartner.referral_link || '';
                    row.innerHTML = `
                        <td><strong>${updatedPartner.bot_name}</strong></td>
                        <td><span style="background: ${updatedPartner.category === 'TOP' ? '#fbbf24' : '#60a5fa'}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">${updatedPartner.category}</span></td>
                        <td style="word-break: break-all; max-width: 300px; padding: 10px;">
                            <a href="${refLink}" target="_blank" style="font-size: 11px; color: #2563eb; text-decoration: none; line-height: 1.4; display: block;">
                                ${refLink || '-'}
                            </a>
                        </td>
                        <td>${updatedPartner.commission}%</td>
                        <td>${updatedPartner.active === 'Yes' ? '✅' : '❌'}</td>
                        <td>${updatedPartner.verified === 'Yes' ? '✅' : '❌'}</td>
                        <td>${updatedPartner.duration ? String(updatedPartner.duration).replace(/\s/g, '') : '-'}</td>
                        <td>${updatedPartner.roi_score || 0}</td>
                        <td>
                            <button onclick="showEditPartnerForm('${updatedPartner.id}')" style="background: #059669; margin-right: 5px; font-size: 12px; padding: 6px 10px;">Edit</button>
                            <button class="btn-danger" onclick="deletePartner('${document.getElementById('partners-bot-select').value}', '${updatedPartner.id}')" style="font-size: 12px; padding: 6px 10px;">Delete</button>
                        </td>
                    `;
                    updated = true;
                }
            }
        });

        // Update cache
        if (window.partnersData) {
            const index = window.partnersData.findIndex(p => p.id === partnerId);
            if (index !== -1) {
                window.partnersData[index] = updatedPartner;
            }
        }

        // Check if partner visibility changed (active/inactive filter)
        const showInactive = document.getElementById('show-inactive-partners')?.checked || false;
        const shouldBeVisible = showInactive || updatedPartner.active === 'Yes';

        if (!updated && shouldBeVisible) {
            // Partner not found in table but should be visible - might need to add it
            // For now, fallback to reload (could be optimized further)
            console.log('Partner not found in table, reloading...');
            await loadPartners();
        } else if (updated && !shouldBeVisible) {
            // Partner was updated but should not be visible - remove it
            rows.forEach(row => {
                const editButton = row.querySelector('button[onclick*="showEditPartnerForm"]');
                if (editButton) {
                    const onclickAttr = editButton.getAttribute('onclick');
                    const match = onclickAttr.match(/showEditPartnerForm\('([^']+)'\)/);
                    if (match && match[1] === partnerId) {
                        row.remove();
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error updating partner row:', error);
        // Fallback to full reload if update fails
        await loadPartners();
    }
}

async function addPartnerRowToTable(partnerResponse) {
    // Add new partner row instead of reloading entire table
    try {
        let partner;
        if (partnerResponse instanceof Response) {
            partner = await partnerResponse.json();
        } else {
            partner = partnerResponse;
        }

        if (!partner || !partner.id) {
            // Fallback to full reload if partner data not provided
            await loadPartners();
            return;
        }

        const showInactive = document.getElementById('show-inactive-partners')?.checked || false;
        const shouldBeVisible = showInactive || partner.active === 'Yes';

        if (!shouldBeVisible) {
            // Partner is inactive and filter hides inactive - no need to add
            return;
        }

        const tbody = document.getElementById('partners-tbody');
        const refLink = partner.referral_link || '';
        const newRow = document.createElement('tr');
        newRow.innerHTML = `
            <td><strong>${partner.bot_name}</strong></td>
            <td><span style="background: ${partner.category === 'TOP' ? '#fbbf24' : '#60a5fa'}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">${partner.category}</span></td>
            <td style="word-break: break-all; max-width: 300px; padding: 10px;">
                <a href="${refLink}" target="_blank" style="font-size: 11px; color: #2563eb; text-decoration: none; line-height: 1.4; display: block;">
                    ${refLink || '-'}
                </a>
            </td>
            <td>${partner.commission}%</td>
            <td>${partner.active === 'Yes' ? '✅' : '❌'}</td>
            <td>${partner.verified === 'Yes' ? '✅' : '❌'}</td>
            <td>${partner.duration ? String(partner.duration).replace(/\s/g, '') : '-'}</td>
            <td>${partner.roi_score || 0}</td>
            <td>
                <button onclick="showEditPartnerForm('${partner.id}')" style="background: #059669; margin-right: 5px; font-size: 12px; padding: 6px 10px;">Edit</button>
                <button class="btn-danger" onclick="deletePartner('${document.getElementById('partners-bot-select').value}', '${partner.id}')" style="font-size: 12px; padding: 6px 10px;">Delete</button>
            </td>
        `;

        // Insert at the beginning (newest first) or maintain sort order
        tbody.insertBefore(newRow, tbody.firstChild);

        // Update cache
        if (window.partnersData) {
            window.partnersData.unshift(partner);
        } else {
            window.partnersData = [partner];
        }
    } catch (error) {
        console.error('Error adding partner row:', error);
        // Fallback to full reload if add fails
        await loadPartners();
    }
}

async function removePartnerRowFromTable(partnerId) {
    // Remove partner row instead of reloading entire table
    try {
        const tbody = document.getElementById('partners-tbody');
        const rows = tbody.querySelectorAll('tr');
        let removed = false;

        rows.forEach(row => {
            const editButton = row.querySelector('button[onclick*="showEditPartnerForm"]');
            if (editButton) {
                const onclickAttr = editButton.getAttribute('onclick');
                const match = onclickAttr.match(/showEditPartnerForm\('([^']+)'\)/);
                if (match && match[1] === partnerId) {
                    row.remove();
                    removed = true;
                }
            }
        });

        // Update cache
        if (window.partnersData) {
            window.partnersData = window.partnersData.filter(p => p.id !== partnerId);
        }

        if (!removed) {
            console.log('Partner row not found, might already be removed');
        }
    } catch (error) {
        console.error('Error removing partner row:', error);
        // Fallback to full reload if remove fails
        await loadPartners();
    }
}

function showPartnerPreview(data) {
    const previewCard = document.getElementById('partner-preview-card');
    const previewContent = document.getElementById('partner-preview-content');
    const warningsDiv = document.getElementById('partner-preview-warnings');
    const warningsList = document.getElementById('partner-preview-warnings-list');

    if (!previewCard || !previewContent) return;

    // Build preview content
    previewContent.innerHTML = `
        <div><strong>Bot Name:</strong> ${data.botName || '<span style="color: #ef4444;">⚠️ Missing</span>'}</div>
        <div><strong>Category:</strong> <span style="background: ${data.category === 'TOP' ? '#fbbf24' : '#60a5fa'}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">${data.category || 'NEW'}</span></div>
        <div><strong>Commission:</strong> ${data.commission || 0}%</div>
        <div><strong>ROI Score:</strong> <span style="font-weight: 600; color: ${data.roiScore >= 5 ? '#22c55e' : data.roiScore >= 2 ? '#f59e0b' : '#ef4444'};">${data.roiScore || 0}</span></div>
        <div><strong>Active:</strong> ${data.active === 'Yes' ? '✅' : '❌'}</div>
        <div><strong>Verified:</strong> ${data.verified === 'Yes' ? '✅' : '❌'}</div>
        <div><strong>Duration:</strong> ${data.duration || '<span style="color: #ef4444;">⚠️ Missing</span>'}</div>
        <div style="grid-column: 1 / -1;"><strong>Referral Link:</strong><br><a href="${data.referralLink}" target="_blank" style="color: #2563eb; word-break: break-all; font-size: 11px;">${data.referralLink || '<span style="color: #ef4444;">⚠️ Missing</span>'}</a></div>
        <div style="grid-column: 1 / -1;"><strong>Description (UK):</strong> ${data.descUk || '<span style="color: #ef4444;">⚠️ Missing</span>'}</div>
        <div style="grid-column: 1 / -1;"><strong>Description (EN):</strong> ${data.descEn || '<span style="color: #ef4444;">⚠️ Missing</span>'}</div>
    `;

    // Check for warnings
    const warnings = [];
    if (!data.botName || data.botName.trim() === '') warnings.push('Bot Name is missing');
    if (!data.referralLink || data.referralLink.trim() === '') warnings.push('Referral Link is missing');
    if (!data.descUk || data.descUk.trim() === '') warnings.push('Description (UK) is missing');
    if (!data.descEn || data.descEn.trim() === '') warnings.push('Description (EN) is missing');
    if (data.commission === 0) warnings.push('Commission is 0% - is this correct?');
    if (data.roiScore === 0) warnings.push('ROI Score is 0 - is this correct?');
    if (data.active === 'No') warnings.push('Partner is set to "No" (inactive)');

    if (warnings.length > 0 && warningsList) {
        warningsList.innerHTML = warnings.map(w => `<li>${w}</li>`).join('');
        warningsDiv.style.display = 'block';
    } else if (warningsDiv) {
        warningsDiv.style.display = 'none';
    }

    // Show preview with animation
    previewCard.style.display = 'block';
    previewCard.style.opacity = '0';
    previewCard.style.transform = 'translateY(-10px)';
    setTimeout(() => {
        previewCard.style.transition = 'all 0.3s ease';
        previewCard.style.opacity = '1';
        previewCard.style.transform = 'translateY(0)';
    }, 10);

    // Scroll to preview
    previewCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showCreatePartnerForm() {
    document.getElementById('create-partner-form').style.display = 'block';
    // Clear paste field and hide preview when showing form
    const pasteField = document.getElementById('partner-paste-data');
    if (pasteField) pasteField.value = '';
    const previewCard = document.getElementById('partner-preview-card');
    if (previewCard) previewCard.style.display = 'none';
}

function hideCreatePartnerForm() {
    document.getElementById('create-partner-form').style.display = 'none';
}

function showEditPartnerForm(partnerId) {
    const partner = window.partnersData.find(p => p.id === partnerId);
    if (!partner) return;

    document.getElementById('edit-partner-id').value = partner.id;
    document.getElementById('edit-partner-name').value = partner.bot_name;
    document.getElementById('edit-partner-description').value = partner.description || '';
    document.getElementById('edit-partner-description-en').value = partner.description_en || '';
    document.getElementById('edit-partner-description-ru').value = partner.description_ru || '';
    document.getElementById('edit-partner-description-de').value = partner.description_de || '';
    document.getElementById('edit-partner-description-es').value = partner.description_es || '';
    document.getElementById('edit-partner-link').value = partner.referral_link || '';
    document.getElementById('edit-partner-commission').value = partner.commission || 0;
    document.getElementById('edit-partner-category').value = partner.category || 'NEW';
    document.getElementById('edit-partner-active').value = partner.active || 'Yes';
    document.getElementById('edit-partner-verified').value = partner.verified || 'Yes';
    document.getElementById('edit-partner-roi').value = partner.roi_score || 0;
    // Clean duration (remove spaces like "9 999" -> "9999")
    const duration = partner.duration ? String(partner.duration).replace(/\s/g, '') : '';
    document.getElementById('edit-partner-duration').value = duration;

    document.getElementById('edit-partner-form').style.display = 'block';
    document.getElementById('edit-partner-form').scrollIntoView({ behavior: 'smooth' });
}

function hideEditPartnerForm() {
    document.getElementById('edit-partner-form').style.display = 'none';
}

async function updatePartner() {
    const botId = document.getElementById('partners-bot-select').value;
    const partnerId = document.getElementById('edit-partner-id').value;

    const data = {
        bot_name: document.getElementById('edit-partner-name').value,
        description: document.getElementById('edit-partner-description').value,
        description_en: document.getElementById('edit-partner-description-en').value,
        description_ru: document.getElementById('edit-partner-description-ru').value,
        description_de: document.getElementById('edit-partner-description-de').value,
        description_es: document.getElementById('edit-partner-description-es').value,
        referral_link: document.getElementById('edit-partner-link').value,
        commission: parseFloat(document.getElementById('edit-partner-commission').value),
        category: document.getElementById('edit-partner-category').value,
        active: document.getElementById('edit-partner-active').value,
        verified: document.getElementById('edit-partner-verified').value,
        roi_score: parseFloat(document.getElementById('edit-partner-roi').value) || 0,
        duration: document.getElementById('edit-partner-duration').value || ''
    };

    try {
        const res = await fetch(`${API_BASE}/bots/${botId}/partners/${partnerId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            const result = await res.json();
            showMessage('partners-message', 'Partner updated successfully!', 'success');
            hideEditPartnerForm();
            // Update only affected row instead of reloading entire table
            await updatePartnerRowInTable(partnerId, result);
        } else {
            const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
            showMessage('partners-message', 'Error: ' + (error.detail || 'Unknown error'), 'error');
            console.error('Update error:', error);
        }
    } catch (error) {
        showMessage('partners-message', 'Error updating partner: ' + error.message, 'error');
    }
}

async function createPartner() {
    const botId = document.getElementById('partners-bot-select').value;
    if (!botId) {
        showMessage('partners-message', 'Please select a bot first', 'error');
        return;
    }

    const data = {
        bot_name: document.getElementById('partner-name').value,
        description: document.getElementById('partner-description').value,
        description_en: document.getElementById('partner-description-en').value,
        description_ru: document.getElementById('partner-description-ru').value,
        description_de: document.getElementById('partner-description-de').value,
        description_es: document.getElementById('partner-description-es').value,
        referral_link: document.getElementById('partner-link').value,
        commission: parseFloat(document.getElementById('partner-commission').value) || 0,
        category: document.getElementById('partner-category').value,
        active: document.getElementById('partner-active').value || 'Yes',
        verified: document.getElementById('partner-verified').value || 'Yes',
        roi_score: parseFloat(document.getElementById('partner-roi').value) || 0,
        duration: document.getElementById('partner-duration').value || ''
    };

    try {
        const res = await fetch(`${API_BASE}/bots/${botId}/partners`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            const result = await res.json();
            const active = document.getElementById('partner-active').value || 'Yes';
            let message = 'Partner added successfully!';
            if (active === 'No') {
                message += ' (Note: Partner is inactive - enable "Show inactive partners" to see it)';
            }
            showMessage('partners-message', message, 'success');
            // Hide preview after successful creation
            const previewCard = document.getElementById('partner-preview-card');
            if (previewCard) previewCard.style.display = 'none';
            hideCreatePartnerForm();
            // Add new row instead of reloading entire table
            await addPartnerRowToTable(result);
        } else {
            const error = await res.json();
            showMessage('partners-message', 'Error adding partner: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showMessage('partners-message', 'Error: ' + error.message, 'error');
    }
}

async function deletePartner(botId, partnerId) {
    if (!confirm('⚠️ Delete partner? (Can be restored from deletion history)')) return;

    try {
        // Soft delete by default
        const res = await fetch(`${API_BASE}/bots/${botId}/partners/${partnerId}?hard_delete=false`, {
            method: 'DELETE'
        });

        if (res.ok) {
            showMessage('partners-message', 'Partner deleted (can be restored)', 'success');
            // Remove row from table instead of reloading entire table
            await removePartnerRowFromTable(partnerId);
        } else {
            const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
            showMessage('partners-message', 'Error deleting partner: ' + (error.detail || 'Unknown error'), 'error');
            console.error('Delete error:', error);
        }
    } catch (error) {
        showMessage('partners-message', 'Error: ' + error.message, 'error');
        console.error('Delete exception:', error);
    }
}

async function showDeletedPartners() {
    const botId = document.getElementById('partners-bot-select').value;
    if (!botId) return;

    try {
        const res = await fetch(`${API_BASE}/bots/${botId}/partners/deleted`);
        const deleted = await res.json();
        const tbody = document.getElementById('deleted-partners-tbody');

        if (deleted.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px;">No deleted partners</td></tr>';
        } else {
            tbody.innerHTML = deleted.map(p => `
                <tr>
                    <td><strong>${p.bot_name}</strong></td>
                    <td><span style="background: ${p.category === 'TOP' ? '#fbbf24' : '#60a5fa'}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">${p.category}</span></td>
                    <td>${new Date(p.deleted_at).toLocaleString()}</td>
                    <td>
                        <button onclick="restorePartner('${botId}', '${p.id}')" style="background: #059669;">♻️ Restore</button>
                    </td>
                </tr>
            `).join('');
        }

        document.getElementById('deleted-partners-modal').style.display = 'block';
    } catch (error) {
        showMessage('partners-message', 'Error loading deleted partners: ' + error.message, 'error');
    }
}

function hideDeletedPartners() {
    document.getElementById('deleted-partners-modal').style.display = 'none';
}

async function restorePartner(botId, partnerId) {
    if (!confirm('Restore this partner?')) return;

    try {
        const res = await fetch(`${API_BASE}/bots/${botId}/partners/${partnerId}/restore`, { method: 'POST' });
        if (res.ok) {
            const result = await res.json();
            showMessage('partners-message', 'Partner restored successfully!', 'success');
            hideDeletedPartners();
            // Add restored row instead of reloading entire table
            await addPartnerRowToTable(result);
        } else {
            const error = await res.json();
            showMessage('partners-message', 'Error: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showMessage('partners-message', 'Error restoring partner: ' + error.message, 'error');
    }
}

// AI Config
async function loadAIConfig() {
    const botId = document.getElementById('ai-bot-select').value;
    if (!botId) return;

    try {
        const res = await fetch(`${API_BASE}/bots/${botId}/ai-config`);
        const config = await res.json();

        document.getElementById('ai-provider').value = config.provider || 'openai';
        document.getElementById('ai-model').value = config.model || 'gpt-4o-mini';
        document.getElementById('ai-temperature').value = config.temperature || 0.7;
        document.getElementById('ai-prompt').value = config.system_prompt || '';
    } catch (error) {
        showMessage('ai-message', 'Error loading config: ' + error.message, 'error');
    }
}

async function saveAIConfig() {
    const botId = document.getElementById('ai-bot-select').value;
    if (!botId) {
        showMessage('ai-message', 'Please select a bot first', 'error');
        return;
    }

    const data = {
        provider: document.getElementById('ai-provider').value,
        model: document.getElementById('ai-model').value,
        api_key: document.getElementById('ai-api-key').value,
        temperature: parseFloat(document.getElementById('ai-temperature').value),
        system_prompt: document.getElementById('ai-prompt').value
    };

    try {
        const res = await fetch(`${API_BASE}/bots/${botId}/ai-config`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            showMessage('ai-message', 'AI config saved!', 'success');
        } else {
            showMessage('ai-message', 'Error saving config', 'error');
        }
    } catch (error) {
        showMessage('ai-message', 'Error: ' + error.message, 'error');
    }
}

// Statistics
async function loadStats() {
    const botId = document.getElementById('stats-bot-select').value;
    if (!botId) {
        document.getElementById('stats-content').innerHTML = '<p>Please select a bot</p>';
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/bots/${botId}/stats`);

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
            throw new Error(errorData.detail || 'Failed to load stats');
        }

        const stats = await res.json();

        // Validate stats structure
        if (!stats || !stats.users || !stats.partners) {
            throw new Error('Invalid stats data format');
        }

        document.getElementById('stats-content').innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">${stats.users.total || 0}</div>
                    <div class="stat-label">Total Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.users.active || 0}</div>
                    <div class="stat-label">Active Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.partners.total || 0}</div>
                    <div class="stat-label">Total Partners</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.partners.active || 0}</div>
                    <div class="stat-label">Active Partners</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${(stats.total_balance || 0).toFixed(2)}</div>
                    <div class="stat-label">Total Balance</div>
                </div>
            </div>
        `;
    } catch (error) {
        showMessage('stats-message', 'Error loading stats: ' + error.message, 'error');
    }
}

function showMessage(elementId, message, type) {
    const el = document.getElementById(elementId);
    el.innerHTML = `<div class="${type}">${message}</div>`;
    setTimeout(() => el.innerHTML = '', 5000);
}

// Database Viewer Functions
let usersOffset = 0;
let partnersOffset = 0;
let translationsOffset = 0;
let messagesOffset = 0;
const ROWS_PER_PAGE = 10;
const MESSAGES_PER_PAGE = 20;

async function loadDatabaseData() {
    if (!currentBotId) {
        document.getElementById('database-users-tbody').innerHTML = '<tr><td colspan="15" style="padding: 20px; text-align: center; color: #6b7280;">Please select a bot from header</td></tr>';
        return;
    }

    usersOffset = 0;
    partnersOffset = 0;
    translationsOffset = 0;
    messagesOffset = 0;

    // Always load messages table
    await loadUsersForMessagesFilter();
    await loadMessages(0, true);
}

async function loadUsersForMessages() {
    if (!currentBotId) return;

    try {
        // Load only first 100 users for dropdown (lazy load more if needed)
        const res = await fetch(`${API_BASE}/bots/${currentBotId}/users?limit=100`);
        const users = await res.json();
        const select = document.getElementById('messages-user-select');
        select.innerHTML = '<option value="">-- Select user to view messages --</option>';

        users.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = `${user.external_id} (${user.platform})`;
            select.appendChild(option);
        });

        // Show note if there are more users
        if (users.length === 100) {
            const option = document.createElement('option');
            option.disabled = true;
            option.textContent = `... (showing first 100 users, use search for more)`;
            select.appendChild(option);
        }
    } catch (error) {
        console.error('Error loading users for messages:', error);
    }
}

// Helper function to format Telegram message (preserve HTML, handle newlines)
function formatTelegramMessage(text) {
    if (!text) return '';

    // Decode escaped newlines (\\n -> actual newline)
    text = text.replace(/\\n/g, '\n');

    // Create a temporary div to sanitize HTML while preserving Telegram tags
    const tempDiv = document.createElement('div');

    // Telegram uses: <b>, <i>, <u>, <s>, <code>, <pre>, <a href="...">
    // We'll use DOMParser to safely parse and preserve only allowed tags
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, 'text/html');

    // Sanitize: remove dangerous tags, keep only Telegram HTML tags
    const allowedTags = ['b', 'i', 'u', 's', 'code', 'pre', 'a'];
    const allowedAttrs = ['href'];

    function sanitizeNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            // Convert newlines to <br> in text nodes
            return node.textContent.replace(/\n/g, '<br>');
        }

        if (node.nodeType === Node.ELEMENT_NODE) {
            const tagName = node.tagName.toLowerCase();

            if (allowedTags.includes(tagName)) {
                // Preserve allowed tag
                let html = `<${tagName}`;

                // Add allowed attributes
                if (tagName === 'a') {
                    const href = node.getAttribute('href');
                    if (href) {
                        html += ` href="${href.replace(/"/g, '&quot;')}"`;
                    }
                }

                html += '>';

                // Process children
                for (let child of node.childNodes) {
                    html += sanitizeNode(child);
                }

                html += `</${tagName}>`;
                return html;
            } else {
                // Remove disallowed tag, keep content
                let html = '';
                for (let child of node.childNodes) {
                    html += sanitizeNode(child);
                }
                return html;
            }
        }

        return '';
    }

    // Process body content
    let result = '';
    for (let child of doc.body.childNodes) {
        result += sanitizeNode(child);
    }

    // If no HTML tags were found, just convert newlines
    if (!text.includes('<') || result === '') {
        return text.replace(/\n/g, '<br>');
    }

    return result;
}

// messagesOffset and MESSAGES_PER_PAGE declared above

async function loadMessages(offset = 0, reset = false) {
    if (!currentBotId) return;

    try {
        const sortBy = document.getElementById('messages-sort-by')?.value || 'timestamp';
        const command = document.getElementById('messages-command-filter')?.value || '';
        const userId = document.getElementById('messages-user-filter')?.value || '';
        let url = `${API_BASE}/bots/${currentBotId}/messages?skip=${offset}&limit=${MESSAGES_PER_PAGE}&sort_by=${sortBy}`;
        if (command) url += `&command=${encodeURIComponent(command)}`;
        if (userId) {
            // userId is already UUID from select option value
            url += `&user_id=${encodeURIComponent(userId)}`;
        }
        console.log('Loading messages with URL:', url);

        const res = await fetch(url);
        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(error.detail || `HTTP ${res.status}`);
        }
        const messages = await res.json();
        const tbody = document.getElementById('database-messages-tbody');

        if (reset) {
            tbody.innerHTML = '';
            messagesOffset = 0;
        }

        if (messages.length === 0 && reset) {
            tbody.innerHTML = '<tr><td colspan="17" style="padding: 20px; text-align: center; color: #6b7280;">No messages found. Make sure there are user messages (commands) in the database.</td></tr>';
            document.getElementById('database-messages-more').style.display = 'none';
            return;
        }

        console.log('Loaded messages:', messages.length, messages);

        // Store user data for editing (from messages)
        if (reset) {
            window.usersData = [];
        }
        // Extract unique users from messages
        const userMap = new Map();
        messages.forEach(msg => {
            if (!userMap.has(msg.user_id)) {
                userMap.set(msg.user_id, {
                    id: msg.user_id,
                    external_id: msg.external_id,
                    username: msg.username,
                    first_name: msg.first_name,
                    last_name: msg.last_name,
                    top_status: msg.top_status,
                    top_unlock_method: msg.top_status === 'open' ? (msg.total_invited >= 5 ? 'invites' : 'payment') : '',
                    total_invited: msg.total_invited,
                    wallet_address: msg.wallet_address,
                    balance: msg.balance,
                    is_active: msg.is_active
                });
            }
        });
        window.usersData.push(...Array.from(userMap.values()));

        messages.forEach(msg => {
            const username = msg.username || '-';
            const firstName = msg.first_name || '';
            const lastName = msg.last_name || '';
            const fullName = `${firstName} ${lastName}`.trim() || '-';
            const wallet = msg.wallet_address || '-';
            const totalInvited = msg.total_invited || 0;
            const topStatus = msg.top_status || 'locked';
            let topBadge;
            if (topStatus === 'open') {
                topBadge = '<span style="background: #10b981; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 600;">OPEN</span>';
            } else {
                topBadge = '<span style="background: #ef4444; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 600;">LOCKED</span>';
            }

            // Format dates (combined date/time)
            const commandDate = msg.command_timestamp ? new Date(msg.command_timestamp) : null;
            const dateTimeStr = commandDate ? commandDate.toLocaleString('uk-UA', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }) : '-';
            const createdDate = msg.created_at ? new Date(msg.created_at).toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit' }) : '-';
            const lastActivityDate = msg.last_activity ? new Date(msg.last_activity).toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit' }) : '-';

            // Response time formatting with color coding
            let responseTimeCell = '-';
            if (msg.response_time_seconds !== null && msg.response_time_seconds !== undefined) {
                const rt = msg.response_time_seconds;
                let color, icon;
                if (rt < 1) {
                    color = '#10b981'; // green
                    icon = '✅';
                } else if (rt <= 3) {
                    color = '#f59e0b'; // yellow
                    icon = '⚠️';
                } else {
                    color = '#ef4444'; // red
                    icon = '❌';
                }
                responseTimeCell = `<span style="background: ${color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 600;">${rt.toFixed(1)}s ${icon}</span>`;
            } else {
                responseTimeCell = '<span style="background: #9ca3af; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px;">-</span>';
            }

            // Command and response previews (expandable)
            const commandPreview = msg.command_content ? (msg.command_content.length > 20 ? msg.command_content.substring(0, 20) + '...' : msg.command_content) : '-';
            const responsePreview = msg.response_content ? (msg.response_content.length > 30 ? msg.response_content.substring(0, 30) + '...' : msg.response_content) : '-';
            const commandExpandId = `cmd-expand-${msg.id}`;
            const responseExpandId = `resp-expand-${msg.id}`;

            const row = document.createElement('tr');
            row.innerHTML = `
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px;">${dateTimeStr}</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px;">${msg.user_id.substring(0, 8)}...</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px;">${msg.external_id || '-'}</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px;">${username}</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px; text-align: center;">
                    ${msg.device ? `<span style="background: #e5e7eb; color: #374151; padding: 1px 4px; border-radius: 3px; font-size: 9px;">${msg.device}</span>` : '-'}
                </td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px;">
                    ${msg.language ? `<span style="background: #dbeafe; color: #1e40af; padding: 1px 4px; border-radius: 3px; font-size: 9px; font-weight: 500;">${msg.language.toUpperCase()}</span>` : '-'}
                </td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px; word-break: break-all; max-width: 100px;">${wallet}</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px; text-align: center;">${totalInvited}</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px; text-align: center;">${topBadge}</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px;">${msg.balance || 0}</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px; text-align: center;">${msg.is_active ? '✅' : '❌'}</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px;">${createdDate}</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px;">${lastActivityDate}</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px; max-width: 150px;">
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
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px; text-align: center;">
                    ${msg.source ? `<span style="background: #8b5cf6; color: white; padding: 1px 4px; border-radius: 3px; font-size: 8px;">${msg.source}</span>` : '-'}
                </td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px; max-width: 200px;">
                    <div onclick="toggleExpand('${responseExpandId}')" style="cursor: pointer; display: flex; align-items: center; gap: 4px;">
                        <span style="font-size: 9px; color: #6b7280;">
                            ${responsePreview}
                        </span>
                        <span style="font-size: 8px; color: #9ca3af;">▼</span>
                    </div>
                    <div id="${responseExpandId}" style="display: none; margin-top: 4px; padding: 6px; background: #f9fafb; border-radius: 4px; font-size: 9px; white-space: pre-wrap; word-wrap: break-word;">${msg.response_content || '-'}</div>
                </td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px; text-align: center;">${responseTimeCell}</td>
                <td style="padding: 2px 4px; border-bottom: 1px solid #e5e7eb; font-size: 9px; position: sticky; right: 0; background: white; z-index: 5; white-space: nowrap;">
                    <button onclick="showEditUserForm('${msg.user_id}')" style="background: #059669; color: white; padding: 2px 6px; border: none; border-radius: 3px; cursor: pointer; font-size: 9px; font-weight: 600; margin-right: 4px;">Edit</button>
                    <button onclick="deleteUser('${msg.user_id}', '${msg.external_id || msg.user_id}')" style="background: #dc2626; color: white; padding: 2px 6px; border: none; border-radius: 3px; cursor: pointer; font-size: 9px; font-weight: 600;">Del</button>
                </td>
            `;
            tbody.appendChild(row);
        });

        messagesOffset += messages.length;
        document.getElementById('database-messages-more').style.display = messages.length === MESSAGES_PER_PAGE ? 'block' : 'none';
    } catch (error) {
        console.error('Error loading messages:', error);
        document.getElementById('database-messages-tbody').innerHTML = '<tr><td colspan="17" style="padding: 20px; text-align: center; color: #ef4444;">Error loading messages: ' + error.message + '</td></tr>';
    }
}

function loadMoreMessages() {
    loadMessages(messagesOffset, false);
}

async function loadUsersForMessagesFilter() {
    if (!currentBotId) return;

    try {
        // Check cache first (same as users filter)
        const cacheKey = `usersForFilter_${currentBotId}`;
        const cached = getCached(cacheKey);
        if (cached) {
            const select = document.getElementById('messages-user-filter');
            if (select) {
                select.innerHTML = '<option value="">All users</option>' + cached;
            }
            return;
        }

        // Load only first 100 users for filter (to save resources)
        const res = await fetch(`${API_BASE}/bots/${currentBotId}/users?skip=0&limit=100`);
        const users = await res.json();
        const select = document.getElementById('messages-user-filter');

        // Keep "All users" option
        let optionsHtml = '<option value="">All users</option>';

        // Add users (username + external_id)
        users.forEach(u => {
            const displayName = u.username ? `@${u.username} (${u.external_id})` : `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.external_id;
            optionsHtml += `<option value="${u.id}">${displayName}</option>`;
        });

        if (users.length === 100) {
            optionsHtml += '<option disabled>... (showing first 100)</option>';
        }

        select.innerHTML = optionsHtml;

        // Cache for 2 minutes
        cache[cacheKey] = { data: optionsHtml, timestamp: Date.now(), ttl: 2 * 60 * 1000 };
    } catch (error) {
        console.error('Error loading users for filter:', error);
    }
}

// Store users data for editing
if (!window.usersData) {
    window.usersData = [];
}

function showEditUserForm(userId) {
    const user = window.usersData.find(u => u.id === userId);
    if (!user) {
        alert('User data not found. Please reload the users list.');
        return;
    }

    document.getElementById('edit-user-id').value = user.id;
    document.getElementById('edit-user-top-status').value = user.top_status || 'locked';
    document.getElementById('edit-user-top-unlock-method').value = user.top_unlock_method || '';
    document.getElementById('edit-user-total-invited').value = user.total_invited || 0;
    document.getElementById('edit-user-wallet-address').value = user.wallet_address || '';
    document.getElementById('edit-user-balance').value = user.balance || 0;

    document.getElementById('edit-user-form').style.display = 'block';
    document.getElementById('edit-user-form').scrollIntoView({ behavior: 'smooth' });
}

function hideEditUserForm() {
    document.getElementById('edit-user-form').style.display = 'none';
}

async function resetUserInvites() {
    if (!currentBotId) {
        alert('Please select a bot first');
        return;
    }

    const userId = document.getElementById('edit-user-id').value;
    if (!userId) {
        alert('Please select a user first');
        return;
    }

    if (!confirm('⚠️ Reset invites to 0 for this user?\n\nThis will:\n- Set total_invited to 0\n- Lock TOP status\n\nContinue?')) {
        return;
    }

    try {
        const url = `${API_BASE}/bots/${currentBotId}/users/${userId}/reset-invites`;
        const res = await fetch(url, { method: 'POST' });

        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(error.detail || `HTTP ${res.status}`);
        }

        const result = await res.json();
        alert(`✅ Invites reset successfully!\n\nOld count: ${result.old_total_invited}\nNew count: ${result.new_total_invited}\nActual DB count: ${result.actual_count_from_db}\n\nNote: If actual_count_from_db > 0, there are still referral logs in the database.`);

        // Reload messages to show updated data
        // Update only affected rows instead of reloading entire table
        await updateUserRowsInTable(userId);
    } catch (error) {
        alert('Error resetting invites: ' + error.message);
        console.error('Error resetting invites:', error);
    }
}

async function test5Invites() {
    if (!currentBotId) {
        alert('Please select a bot first');
        return;
    }

    const userId = document.getElementById('edit-user-id').value;
    if (!userId) {
        alert('Please select a user first');
        return;
    }

    if (!confirm('🧪 Create 5 test invites for this user?\n\nThis will:\n- Create 5 referral log entries\n- Update total_invited count\n- Auto-unlock TOP if >= 5 invites\n\nContinue?')) {
        return;
    }

    try {
        const url = `${API_BASE}/bots/${currentBotId}/users/${userId}/test-5-invites`;
        const res = await fetch(url, { method: 'POST' });

        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(error.detail || `HTTP ${res.status}`);
        }

        const result = await res.json();
        let message = `✅ Test completed!\n\n`;
        message += `Initial: ${result.initial_state.total_invited} invites, TOP: ${result.initial_state.top_status}\n`;
        message += `Final: ${result.final_state.total_invited} invites, TOP: ${result.final_state.top_status}\n\n`;
        message += `Tests passed: ${result.tests_passed}/${result.tests_total}\n`;
        if (result.tests_passed < result.tests_total) {
            message += `\n⚠️ Some tests failed. Check details in console.`;
        }
        alert(message);
        console.log('Test results:', result);

        // Reload messages to show updated data
        // Update only affected rows instead of reloading entire table
        await updateUserRowsInTable(userId);
    } catch (error) {
        alert('Error testing invites: ' + error.message);
        console.error('Error testing invites:', error);
    }
}

async function updateUser() {
    if (!currentBotId) {
        alert('Please select a bot first');
        return;
    }

    const userId = document.getElementById('edit-user-id').value;
    if (!userId) {
        alert('User ID is required');
        return;
    }

    const topStatus = document.getElementById('edit-user-top-status').value;
    const topUnlockMethod = document.getElementById('edit-user-top-unlock-method').value;
    const totalInvited = parseInt(document.getElementById('edit-user-total-invited').value) || 0;
    const walletAddress = document.getElementById('edit-user-wallet-address').value.trim();
    const balance = parseFloat(document.getElementById('edit-user-balance').value) || 0;

    // Build query params
    const params = new URLSearchParams();
    if (topStatus) params.append('top_status', topStatus);
    if (topUnlockMethod) params.append('top_unlock_method', topUnlockMethod);
    if (!isNaN(totalInvited)) params.append('total_invited', totalInvited);
    if (walletAddress) params.append('wallet_address', walletAddress);
    if (!isNaN(balance)) params.append('balance', balance);

    try {
        const url = `${API_BASE}/bots/${currentBotId}/users/${userId}?${params.toString()}`;
        const res = await fetch(url, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!res.ok) {
            let errorText = 'Failed to update user';
            try {
                const error = await res.json();
                errorText = error.detail || error.message || JSON.stringify(error);
            } catch (e) {
                errorText = `HTTP ${res.status}: ${res.statusText}`;
            }
            throw new Error(errorText);
        }

        const result = await res.json();
        alert('User updated successfully!');
        hideEditUserForm();
        // Update only affected rows instead of reloading entire table
        await updateUserRowsInTable(userId);
        loadUsersForMessagesFilter();
    } catch (error) {
        let errorMessage = 'Failed to update user';
        if (error && error.message) {
            errorMessage = error.message;
        } else if (typeof error === 'string') {
            errorMessage = error;
        } else if (error && error.toString && error.toString() !== '[object Object]') {
            errorMessage = error.toString();
        }
        alert('Error updating user: ' + errorMessage);
        console.error('Error updating user:', error);
    }
}

async function deleteUser(userId, userExternalId) {
    if (!currentBotId) {
        alert('Please select a bot first');
        return;
    }

    // Confirm deletion
    const confirmMessage = `Are you sure you want to delete user ${userExternalId}?\n\nThis will permanently delete:\n- User record\n- All referral logs\n- All analytics events\n- All messages\n\nThis action cannot be undone!`;
    if (!confirm(confirmMessage)) {
        return;
    }

    // Double confirmation for safety
    if (!confirm('⚠️ FINAL CONFIRMATION: Delete this user and ALL related data?\n\nThis action is IRREVERSIBLE!')) {
        return;
    }

    try {
        const url = `${API_BASE}/bots/${currentBotId}/users/${userId}`;
        const res = await fetch(url, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!res.ok) {
            let errorText = 'Failed to delete user';
            try {
                const error = await res.json();
                errorText = error.detail || error.message || JSON.stringify(error);
            } catch (e) {
                errorText = `HTTP ${res.status}: ${res.statusText}`;
            }
            throw new Error(errorText);
        }

        const result = await res.json();
        const deleted = result.deleted || {};
        alert(`User deleted successfully!\n\nDeleted:\n- User record\n- ${deleted.business_data_records || 0} business data records\n- ${deleted.analytics_events || 0} analytics events\n- ${deleted.messages || 0} messages\n\nTotal: ${deleted.total_records || 0} records`);

        // Reload users list
        loadMessages(0, true);
        loadUsersForMessagesFilter();
    } catch (error) {
        let errorMessage = 'Failed to delete user';
        if (error && error.message) {
            errorMessage = error.message;
        } else if (typeof error === 'string') {
            errorMessage = error;
        } else if (error && error.toString && error.toString() !== '[object Object]') {
            errorMessage = error.toString();
        }
        alert('Error deleting user: ' + errorMessage);
        console.error('Error deleting user:', error);
    }
}

async function updateUserRowsInTable(userId) {
    // Update only rows for specific user_id instead of reloading entire table
    if (!currentBotId || !userId) return;

    try {
        // Fetch latest user data by external_id from cache
        const cachedUser = window.usersData.find(u => u.id === userId);
        if (!cachedUser || !cachedUser.external_id) {
            console.warn('User not found in cache, falling back to full reload');
            loadMessages(0, true);
            return;
        }

        const userRes = await fetch(`${API_BASE}/bots/${currentBotId}/users?external_id=${cachedUser.external_id}`);
        if (!userRes.ok) {
            console.warn('Could not fetch updated user data, falling back to full reload');
            loadMessages(0, true);
            return;
        }

        const users = await userRes.json();
        const userList = Array.isArray(users) ? users : users.users || [];
        const updatedUser = userList.find(u => u.id === userId) || userList[0];

        if (!updatedUser) {
            console.warn('User not found in response, falling back to full reload');
            loadMessages(0, true);
            return;
        }

        const totalInvited = updatedUser.total_invited || updatedUser.custom_data?.total_invited || 0;
        const topStatus = updatedUser.top_status || updatedUser.custom_data?.top_status || 'locked';

        // Update only rows with matching user_id
        const tbody = document.getElementById('database-messages-tbody');
        const rows = tbody.querySelectorAll('tr');
        let updatedCount = 0;

        rows.forEach(row => {
            const rowUserIdCell = row.querySelector('td:nth-child(2)');
            if (!rowUserIdCell) return;

            const rowUserIdText = rowUserIdCell.textContent?.trim() || '';
            // Check if row belongs to this user (user_id starts with first 8 chars)
            if (rowUserIdText && userId && rowUserIdText.startsWith(userId.substring(0, 8))) {
                // Update INVITED column (8th column)
                const invitedCell = row.querySelector('td:nth-child(8)');
                if (invitedCell && invitedCell.textContent !== String(totalInvited)) {
                    invitedCell.textContent = totalInvited;
                    updatedCount++;
                }

                // Update TOP column (9th column)
                const topCell = row.querySelector('td:nth-child(9)');
                if (topCell) {
                    const currentTopStatus = topCell.querySelector('span')?.textContent?.trim();
                    const newTopStatus = topStatus === 'open' ? 'OPEN' : 'LOCKED';

                    if (currentTopStatus !== newTopStatus) {
                        if (topStatus === 'open') {
                            topCell.innerHTML = '<span style="background: #10b981; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 600;">OPEN</span>';
                        } else {
                            topCell.innerHTML = '<span style="background: #ef4444; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 600;">LOCKED</span>';
                        }
                        updatedCount++;
                    }
                }
            }
        });

        // Update window.usersData cache
        if (cachedUser) {
            cachedUser.total_invited = totalInvited;
            cachedUser.top_status = topStatus;
        }

        if (updatedCount > 0) {
            console.log(`Updated ${updatedCount} row(s) for user ${userId.substring(0, 8)}...`);
        }
    } catch (error) {
        console.error('Error updating user rows:', error);
        // Fallback to full reload if update fails
        loadMessages(0, true);
    }
}

function toggleExpand(expandId) {
    const expandDiv = document.getElementById(expandId);
    if (expandDiv) {
        expandDiv.style.display = expandDiv.style.display === 'none' ? 'block' : 'none';
        // Update arrow icon
        const arrow = expandDiv.previousElementSibling?.querySelector('span:last-child');
        if (arrow) {
            arrow.textContent = expandDiv.style.display === 'none' ? '▼' : '▲';
        }
    }
}

function loadAllMessages() {
    // Load all messages (with reasonable limit)
    loadMessages(0, true);
    // Then load more until no more
    const checkMore = setInterval(() => {
        if (document.getElementById('database-messages-more').style.display === 'none') {
            clearInterval(checkMore);
        } else {
            loadMoreMessages();
        }
    }, 500);
}

// ==========================================
// Monitoring / Analytics
// ==========================================

let clicksChart = null;
let partnersChart = null;

async function loadMonitoring() {
    if (!currentBotId) return;

    try {
        const statsContainer = document.querySelector('#monitoring .stats-grid');
        const clickCountEl = document.getElementById('total-clicks');

        const response = await fetch(`${API_BASE}/bots/${currentBotId}/stats/analytics?days=30`);
        if (!response.ok) throw new Error('Failed to load analytics');

        const data = await response.json();

        // Update Stats
        if (clickCountEl) clickCountEl.textContent = data.total_clicks.toLocaleString();

        // Render Clicks Chart (Line)
        const ctxClicks = document.getElementById('clicksChart').getContext('2d');

        if (clicksChart) clicksChart.destroy();

        clicksChart = new Chart(ctxClicks, {
            type: 'line',
            data: {
                labels: data.daily_clicks.map(d => d.date),
                datasets: [{
                    label: 'Direct Clicks',
                    data: data.daily_clicks.map(d => d.count),
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });

        // Render Top Partners Chart (Bar)
        const ctxPartners = document.getElementById('partnersChart').getContext('2d');

        if (partnersChart) partnersChart.destroy();

        partnersChart = new Chart(ctxPartners, {
            type: 'bar',
            data: {
                labels: data.top_partners.map(p => p.name.substring(0, 15) + (p.name.length > 15 ? '...' : '')),
                datasets: [{
                    label: 'Clicks',
                    data: data.top_partners.map(p => p.count),
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(255, 206, 86, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(153, 102, 255, 0.7)',
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y', // Horizontal bar chart
                plugins: {
                    legend: {
                        display: false,
                    }
                }
            }
        });

    } catch (error) {
        console.error('Error loading monitoring data:', error);
    }
}

// Load on page load
loadGlobalBotSelector();
loadBots();



