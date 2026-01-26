// Partners Management Logic

let partnersROISortDesc = true;

function sortPartnersByROI() {
    partnersROISortDesc = !partnersROISortDesc;
    const icon = document.getElementById('roi-sort-icon');
    if (icon) {
        icon.textContent = partnersROISortDesc ? '⬇' : '⬆';
    }
    loadPartners();
}

async function loadPartners() {
    const botId = document.getElementById('partners-bot-select').value;
    if (!botId) return;

    try {
        const showInactive = document.getElementById('show-inactive-partners')?.checked || false;
        const activeOnly = !showInactive;
        const url = `${API_BASE}/bots/${botId}/partners?active_only=${activeOnly}`;
        const res = await authFetch(url);

        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: 'Failed to load partners' }));
            showMessage('partners-message', 'Error loading partners: ' + (error.detail || 'Unknown error'), 'error');
            return;
        }

        const partners = await res.json();

        // Sort by ROI Score
        partners.sort((a, b) => {
            const roiA = parseFloat(a.roi_score || 0);
            const roiB = parseFloat(b.roi_score || 0);
            return partnersROISortDesc ? (roiB - roiA) : (roiA - roiB);
        });

        const tbody = document.getElementById('partners-tbody');
        tbody.innerHTML = partners.map(p => {
            const refLink = p.referral_link || '';
            const startDate = p.start_date ? new Date(p.start_date).toLocaleDateString() : '-';

            let daysLeft = parseInt(p.days_remaining);
            if (isNaN(daysLeft)) daysLeft = 9999;

            let daysStyle = '';
            let daysText = daysLeft > 9000 ? '∞' : daysLeft;

            if (daysLeft <= 3) {
                daysStyle = 'background: #ef4444; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;';
            } else if (daysLeft <= 7) {
                daysStyle = 'background: #f59e0b; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;';
            }

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
                <td>${startDate}</td>
                <td><span style="${daysStyle}">${daysText}</span></td>
                <td>${p.roi_score || 0}</td>
                <td>
                    <button onclick="showEditPartnerForm('${p.id}')" style="background: #059669; margin-right: 5px; font-size: 12px; padding: 6px 10px;">Edit</button>
                    <button onclick="deletePartner('${botId}', '${p.id}')" style="background: #f97316; font-size: 12px; padding: 6px 10px; border: none; border-radius: 4px; color: white; cursor: pointer;">Delete</button>
                    <button class="btn-danger" onclick="deletePartner('${botId}', '${p.id}', true)" style="font-size: 12px; padding: 6px 10px; margin-left: 2px;">Hard Delete</button>
                </td>
            </tr>
            `;
        }).join('');

        window.partnersData = partners;
    } catch (error) {
        showMessage('partners-message', 'Error loading partners: ' + error.message, 'error');
    }
}

function parsePastedData() {
    const pastedText = document.getElementById('partner-paste-data').value.trim();
    if (!pastedText) {
        alert('Please paste data from Google Sheets first');
        return;
    }

    const parts = pastedText.split('\t');
    if (parts.length < 9) {
        alert('Invalid format. Expected at least 9 columns separated by tabs.');
        return;
    }

    // Map columns from Google Sheets (based on known format)
    const botName = (parts[0] || '').trim();
    const descUk = (parts[1] || '').trim();
    const descEn = (parts[2] || '').trim();
    const descRu = (parts[3] || '').trim();
    const descDe = (parts[4] || '').trim();
    const descEs = (parts[5] || '').trim();
    const referralLink = (parts[6] || '').trim();
    const commission = parseFloat((parts[8] || '0').replace(/\s/g, '').replace(',', '.')) || 0;
    const category = (parts[9] || 'NEW').trim().toUpperCase();
    const active = (parts[10] || 'Yes').trim();
    const duration = (parts[11] || '').trim().replace(/\s/g, '') || '';
    const verified = (parts[12] || 'Yes').trim();

    // ROI Score logic
    let roiScore = parts[parts.length - 1] || '0';
    if (parts.length >= 2 && parts[parts.length - 1] === '1,0' && parts[parts.length - 2]) {
        roiScore = parts[parts.length - 2];
    }
    const roiScoreValue = parseFloat(roiScore.replace(/\s/g, '').replace(',', '.')) || 0;

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

    // Animation
    const pasteField = document.getElementById('partner-paste-data');
    pasteField.style.background = '#d1fae5';
    setTimeout(() => pasteField.style.background = '', 500);

    showPartnerPreview({
        botName, descUk, descEn, descRu, descDe, descEs,
        referralLink, commission, category, active, verified, roiScore: roiScoreValue, duration
    });
}

function showPartnerPreview(data) {
    const previewCard = document.getElementById('partner-preview-card');
    const previewContent = document.getElementById('partner-preview-content');
    const warningsList = document.getElementById('partner-preview-warnings-list');
    const warningsDiv = document.getElementById('partner-preview-warnings');

    if (!previewCard || !previewContent) return;

    previewContent.innerHTML = `
        <div><strong>Bot Name:</strong> ${data.botName || '⚠️ Missing'}</div>
        <div><strong>Category:</strong> ${data.category || 'NEW'}</div>
        <div><strong>Commission:</strong> ${data.commission || 0}%</div>
        <div><strong>ROI:</strong> ${data.roiScore || 0}</div>
        <div style="grid-column: 1 / -1;"><strong>Link:</strong> ${data.referralLink || '⚠️ Missing'}</div>
    `;

    const warnings = [];
    if (!data.botName) warnings.push('Bot Name missing');
    if (!data.referralLink) warnings.push('Link missing');
    if (data.commission === 0) warnings.push('Commission is 0%');

    if (warnings.length > 0 && warningsList) {
        warningsList.innerHTML = warnings.map(w => `<li>${w}</li>`).join('');
        warningsDiv.style.display = 'block';
    } else if (warningsDiv) {
        warningsDiv.style.display = 'none';
    }

    previewCard.style.display = 'block';
    previewCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
        const res = await authFetch(`${API_BASE}/bots/${botId}/partners`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            const result = await res.json();
            showMessage('partners-message', 'Partner added successfully!', 'success');
            hideCreatePartnerForm();
            addPartnerRowToTable(result);
        } else {
            showMessage('partners-message', 'Error creating partner', 'error');
        }
    } catch (error) {
        showMessage('partners-message', 'Error: ' + error.message, 'error');
    }
}

function showCreatePartnerForm() {
    document.getElementById('create-partner-form').style.display = 'block';
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
    document.getElementById('edit-partner-verified').value = partner.verified || 'Yes';
    document.getElementById('edit-partner-roi').value = partner.roi_score || 0;
    document.getElementById('edit-partner-duration').value = partner.duration ? String(partner.duration).replace(/\s/g, '') : '';

    // Format start_date for date input (YYYY-MM-DD)
    if (partner.start_date) {
        try {
            const date = new Date(partner.start_date);
            const dateString = date.toISOString().split('T')[0];
            document.getElementById('edit-partner-start-date').value = dateString;
        } catch (e) {
            console.error('Invalid date format:', partner.start_date);
            document.getElementById('edit-partner-start-date').value = '';
        }
    } else {
        document.getElementById('edit-partner-start-date').value = '';
    }

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
        start_date: document.getElementById('edit-partner-start-date').value || null, // Allow empty to reset
        duration: document.getElementById('edit-partner-duration').value || ''
    };

    try {
        const res = await authFetch(`${API_BASE}/bots/${botId}/partners/${partnerId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            const result = await res.json();
            showMessage('partners-message', 'Partner updated successfully!', 'success');
            hideEditPartnerForm();
            updatePartnerRowInTable(partnerId, result);
        } else {
            showMessage('partners-message', 'Error updating partner', 'error');
        }
    } catch (error) {
        showMessage('partners-message', 'Error: ' + error.message, 'error');
    }
}

async function updatePartnerRowInTable(partnerId, updatedPartner) {
    // Only update existing row to avoid full reload
    const tbody = document.getElementById('partners-tbody');
    const rows = tbody.querySelectorAll('tr');

    rows.forEach(row => {
        if (row.innerHTML.includes(`showEditPartnerForm('${partnerId}')`)) {
            // Rebuild row content
            const refLink = updatedPartner.referral_link || '';
            const startDate = updatedPartner.start_date ? new Date(updatedPartner.start_date).toLocaleDateString() : '-';

            let daysLeft = parseInt(updatedPartner.days_remaining);
            if (isNaN(daysLeft)) daysLeft = 9999;

            let daysStyle = '';
            let daysText = daysLeft > 9000 ? '∞' : daysLeft;

            if (daysLeft <= 3) {
                daysStyle = 'background: #ef4444; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;';
            } else if (daysLeft <= 7) {
                daysStyle = 'background: #f59e0b; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;';
            }

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
                <td>${startDate}</td>
                <td><span style="${daysStyle}">${daysText}</span></td>
                <td>${updatedPartner.roi_score || 0}</td>
                <td>
                    <button onclick="showEditPartnerForm('${updatedPartner.id}')" style="background: #059669; margin-right: 5px; font-size: 12px; padding: 6px 10px;">Edit</button>
                    <button onclick="deletePartner('${document.getElementById('partners-bot-select').value}', '${updatedPartner.id}')" style="background: #f97316; font-size: 12px; padding: 6px 10px; border: none; border-radius: 4px; color: white; cursor: pointer;">Delete</button>
                    <button class="btn-danger" onclick="deletePartner('${document.getElementById('partners-bot-select').value}', '${updatedPartner.id}', true)" style="font-size: 12px; padding: 6px 10px; margin-left: 2px;">Hard Delete</button>
                </td>
            `;
        }
    });

    if (window.partnersData) {
        const idx = window.partnersData.findIndex(p => p.id === partnerId);
        if (idx !== -1) window.partnersData[idx] = updatedPartner;
    }
}

async function addPartnerRowToTable(partner) {
    if (!partner || !partner.id) return loadPartners();

    const showInactive = document.getElementById('show-inactive-partners')?.checked || false;
    if (partner.active !== 'Yes' && !showInactive) return;

    const tbody = document.getElementById('partners-tbody');
    const row = document.createElement('tr');
    const refLink = partner.referral_link || '';
    const startDate = partner.start_date ? new Date(partner.start_date).toLocaleDateString() : 'Just now';

    // For new partners, days left is usually duration (unless start date was backdated manually, but here we assume new)
    let durationVal = parseInt(String(partner.duration || '9999').replace(/\s/g, ''));
    if (isNaN(durationVal)) durationVal = 9999;

    let daysLeft = durationVal;
    // If backend returns days_remaining, prefer it
    if (partner.days_remaining !== undefined) {
        daysLeft = parseInt(partner.days_remaining);
    }

    let daysStyle = '';
    let daysText = daysLeft > 9000 ? '∞' : daysLeft;

    if (daysLeft <= 3) {
        daysStyle = 'background: #ef4444; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;';
    } else if (daysLeft <= 7) {
        daysStyle = 'background: #f59e0b; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;';
    }

    row.innerHTML = `
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
        <td>${startDate}</td>
        <td><span style="${daysStyle}">${daysText}</span></td>
        <td>${partner.roi_score || 0}</td>
        <td>
            <button onclick="showEditPartnerForm('${partner.id}')" style="background: #059669; margin-right: 5px; font-size: 12px; padding: 6px 10px;">Edit</button>
            <button onclick="deletePartner('${document.getElementById('partners-bot-select').value}', '${partner.id}')" style="background: #f97316; font-size: 12px; padding: 6px 10px; border: none; border-radius: 4px; color: white; cursor: pointer;">Delete</button>
            <button class="btn-danger" onclick="deletePartner('${document.getElementById('partners-bot-select').value}', '${partner.id}', true)" style="font-size: 12px; padding: 6px 10px; margin-left: 2px;">Hard Delete</button>
        </td>
    `;

    tbody.insertBefore(row, tbody.firstChild);
    if (window.partnersData) window.partnersData.unshift(partner);
    else window.partnersData = [partner];
}

async function deletePartner(botId, partnerId, hardDelete = false) {
    const confirmMsg = hardDelete
        ? '⚠️ PERMANENT DELETE! This will remove the partner from history too. Are you sure?'
        : 'Soft delete this partner? It will be moved to history.';

    if (!confirm(confirmMsg)) return;

    try {
        const url = `${API_BASE}/bots/${botId}/partners/${partnerId}?hard_delete=${hardDelete}`;
        const res = await authFetch(url, { method: 'DELETE' });
        if (res.ok) {
            showMessage('partners-message', hardDelete ? 'Permanently deleted!' : 'Deleted!', 'success');
            removePartnerRowFromTable(partnerId);
        }
    } catch (e) {
        showMessage('partners-message', 'Error deleting', 'error');
    }
}

function removePartnerRowFromTable(partnerId) {
    const tbody = document.getElementById('partners-tbody');
    const rows = tbody.querySelectorAll('tr');
    rows.forEach(row => {
        if (row.innerHTML.includes(`showEditPartnerForm('${partnerId}')`)) {
            row.remove();
        }
    });
    if (window.partnersData) {
        window.partnersData = window.partnersData.filter(p => p.id !== partnerId);
    }
}

async function showDeletedPartners() {
    const botId = document.getElementById('partners-bot-select').value;
    if (!botId) {
        alert('Please select a bot first');
        return;
    }

    try {
        const res = await authFetch(`${API_BASE}/bots/${botId}/partners/deleted`);
        const deleted = await res.json();

        const tbody = document.getElementById('deleted-partners-tbody');
        if (deleted.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px;">No deleted partners found</td></tr>';
        } else {
            tbody.innerHTML = deleted.map(p => `
                <tr id="deleted-row-${p.id}">
                    <td>${p.bot_name}</td>
                    <td>${p.category}</td>
                    <td>${p.deleted_at ? new Date(p.deleted_at).toLocaleString('uk-UA') : '-'}</td>
                    <td>
                        <button onclick="restorePartner('${botId}', '${p.id}')" style="background: #10b981; font-size: 11px; padding: 4px 8px;">Restore</button>
                        <button onclick="deletePartner('${botId}', '${p.id}', true)" style="background: #dc2626; color: white; font-size: 11px; padding: 4px 8px; border: none; border-radius: 4px; margin-left: 4px; cursor: pointer;">Hard Delete</button>
                    </td>
                </tr>
            `).join('');
        }

        document.getElementById('deleted-partners-modal').style.display = 'block';
    } catch (e) {
        alert('Error loading deleted partners: ' + e.message);
    }
}

function hideDeletedPartners() {
    document.getElementById('deleted-partners-modal').style.display = 'none';
}

async function restorePartner(botId, partnerId) {
    try {
        const res = await authFetch(`${API_BASE}/bots/${botId}/partners/${partnerId}/restore`, { method: 'POST' });
        if (res.ok) {
            alert('Partner restored!');
            const row = document.getElementById(`deleted-row-${partnerId}`);
            if (row) row.remove();
            loadPartners(); // Reload active list
        } else {
            alert('Failed to restore partner');
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}
