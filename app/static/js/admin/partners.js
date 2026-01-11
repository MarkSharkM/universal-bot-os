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
        const res = await fetch(url);

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
        const res = await fetch(`${API_BASE}/bots/${botId}/partners`, {
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
    document.getElementById('edit-partner-active').value = partner.active || 'Yes';
    document.getElementById('edit-partner-verified').value = partner.verified || 'Yes';
    document.getElementById('edit-partner-roi').value = partner.roi_score || 0;
    document.getElementById('edit-partner-duration').value = partner.duration ? String(partner.duration).replace(/\s/g, '') : '';

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
        <td>${partner.roi_score || 0}</td>
        <td>
            <button onclick="showEditPartnerForm('${partner.id}')" style="background: #059669; margin-right: 5px; font-size: 12px; padding: 6px 10px;">Edit</button>
            <button class="btn-danger" onclick="deletePartner('${document.getElementById('partners-bot-select').value}', '${partner.id}')" style="font-size: 12px; padding: 6px 10px;">Delete</button>
        </td>
    `;

    tbody.insertBefore(row, tbody.firstChild);
    if (window.partnersData) window.partnersData.unshift(partner);
    else window.partnersData = [partner];
}

async function deletePartner(botId, partnerId) {
    if (!confirm('Are you sure?')) return;
    try {
        const res = await fetch(`${API_BASE}/bots/${botId}/partners/${partnerId}`, { method: 'DELETE' });
        if (res.ok) {
            showMessage('partners-message', 'Deleted!', 'success');
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
