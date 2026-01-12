/**
 * Legal.js (v5.0)
 * Terms and Privacy pages (Overlay Mode).
 */

window.Render = window.Render || {};

window.Render.renderLegalPage = function (title, content) {
    let overlay = document.getElementById('legal-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'legal-overlay';
        document.body.appendChild(overlay);
    }

    // Full screen overlay styles
    overlay.style.cssText = `
        position: fixed; 
        top: 0; 
        left: 0; 
        width: 100%; 
        height: 100%; 
        background: var(--bg-color); 
        z-index: 9999; 
        overflow-y: auto; 
        padding-bottom: 40px;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;

    // Content
    overlay.innerHTML = `
        <div class="legal-page" style="padding: 20px;">
            <div class="legal-header" style="display:flex; align-items:center; gap:16px; margin-bottom:24px; position:sticky; top:20px; z-index:100;">
                <button onclick="window.Render.closeLegalPage()" style="background:rgba(255,255,255,0.1); border:none; border-radius:50%; width:32px; height:32px; display:flex; align-items:center; justify-content:center; color:#fff; cursor:pointer;">
                    ${Icons.Back || '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5"/><path d="M12 19L5 12L12 5"/></svg>'}
                </button>
                <div style="font-size:18px; font-weight:700; color:#fff;">${title}</div>
            </div>
            
            <div class="legal-content" style="color:var(--text-secondary); font-size:14px; line-height:1.6; white-space: pre-wrap;">
                ${content}
            </div>
            
            <div style="margin-top:40px; text-align:center; font-size:11px; color:var(--text-tertiary);">
                © ${new Date().getFullYear()} Hub Aggregator · This Mini App is not affiliated with Telegram
            </div>
        </div>
    `;

    // Animation
    requestAnimationFrame(() => {
        overlay.style.opacity = '1';
    });
};

window.Render.closeLegalPage = function () {
    const overlay = document.getElementById('legal-overlay');
    if (overlay) {
        overlay.style.opacity = '0';
        setTimeout(() => {
            overlay.remove();
        }, 300);
    }
};

window.Render.renderTerms = function () {
    const config = AppState.getAppData()?.config || {};
    const botName = config.name || 'EarnHub';
    const botUsername = config.username || 'HubAggregatorBot';
    const cleanUsername = botUsername.replace('@', '');

    const content = `**Умови користування**

Використовуючи цей Mini App, ви погоджуєтесь із наведеними нижче умовами.

**Сервіс**
Ми надаємо гейміфікований сервіс цифрових винагород і реферальних програм у межах Telegram. Усі винагороди нараховуються автоматично після виконання відповідних дій, згідно з правилами Партнерської програми Telegram. Перевірка й зарахування можуть тривати кілька днів, доки Telegram підтвердить активність.

**Справедливе використання та антифрод**
Ми можемо обмежити або скасувати винагороди у випадках зловживання, створення кількох акаунтів чи забороненої активності.

**Дані та конфіденційність**
Ми зберігаємо лише мінімальний обсяг даних, необхідний для роботи застосунку. Детальніше див. Політику конфіденційності.

**Контакт**
Підтримка: t.me/${cleanUsername}`;

    const htmlContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#fff;">$1</strong>')
        .replace(/\n\n/g, '<br><br>');

    window.Render.renderLegalPage('Terms of Use', htmlContent);
};

window.Render.renderPrivacy = function () {
    const config = AppState.getAppData()?.config || {};
    const botName = config.name || 'EarnHub';

    const content = `**Політика конфіденційності**

${botName} («ми») обробляє лише мінімальні дані, необхідні для роботи винагород і реферальних програм у Telegram.

1. Ідентифікатор користувача Telegram, нікнейм та мова інтерфейсу;
2. Зв’язки рефералів і журнали активності винагород;
3. Дані антифроду та базової аналітики.

**Ми не збираємо платіжну інформацію.** Дані зберігаються лише поки акаунт активний або до звернення в підтримку щодо видалення.
Обробка даних здійснюється відповідно до Правил користування Telegram.`;

    const htmlContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#fff;">$1</strong>')
        .replace(/\n\n/g, '<br><br>');

    window.Render.renderLegalPage('Privacy Policy', htmlContent);
};
