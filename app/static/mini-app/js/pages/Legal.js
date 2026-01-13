// Localized Content Dictionary
const LEGAL_CONTENT = {
    en: {
        terms_title: 'Terms of Use',
        terms_body: `**Terms of Use**

By using this Mini App, you agree to the conditions below.

**Service**
We provide a gamified digital rewards and referral service within Telegram. All rewards are accrued automatically after completing relevant actions, according to the Telegram Partner Program rules. Verification and crediting may take several days until Telegram confirms the activity.

**Fair Use & Anti-Fraud**
We may limit or cancel rewards in cases of abuse, creating multiple accounts, or prohibited activity.

**Data & Privacy**
We store only the minimal amount of data necessary for the application to work. See Privacy Policy for details.

**Contact**
Support: t.me/{{username}}`,
        privacy_title: 'Privacy Policy',
        privacy_body: `**Privacy Policy**

{{botname}} ("we") processes only minimal data necessary for the operation of rewards and referral programs in Telegram.

1. Telegram user ID, nickname, and interface language;
2. Referral connections and reward activity logs;
3. Anti-fraud data and basic analytics.

**We do not collect payment information.** Data is stored only while the account is active or until a support request for deletion.
Data processing is carried out in accordance with Telegram Terms of Service.`
    },
    uk: {
        terms_title: 'Умови використання',
        terms_body: `**Умови використання**

Використовуючи цей Mini App, ви погоджуєтесь з умовами нижче.

**Сервіс**
Ми надаємо гейміфікований сервіс цифрових винагород та реферальних програм у Telegram. Всі винагороди нараховуються автоматично після виконання дій, згідно з правилами Партнерської програми Telegram. Перевірка та нарахування можуть зайняти кілька днів, поки Telegram підтвердить активність.

**Чесне використання**
Ми можемо обмежити або скасувати винагороди у випадках зловживання, створення мультиаккаунтів або забороненої активності.

**Дані та Конфіденційність**
Ми зберігаємо тільки мінімальний обсяг даних, необхідний для роботи програми. Детальніше див. Політику конфіденційності.

**Контакт**
Підтримка: t.me/{{username}}`,
        privacy_title: 'Політика конфіденційності',
        privacy_body: `**Политика конфіденційності**

{{botname}} («ми») обробляє лише мінімальні дані, необхідні для роботи винагород та реферальних програм у Telegram.

1. Telegram ID користувача, нікнейм та мова інтерфейсу;
2. Реферальні зв'язки та журнали активності винагород;
3. Дані анти-фрод та базова аналітика.

**Ми не збираємо платіжну інформацію.** Дані зберігаються лише поки обліковий запис активний або до запиту в підтримку про видалення.
Обробка даних здійснюється відповідно до Умов надання послуг Telegram.`
    },
    ru: {
        terms_title: 'Условия использования',
        terms_body: `**Условия использования**

Используя этот Mini App, вы соглашаетесь с условиями ниже.

**Сервис**
Мы предоставляем геймифицированный сервис цифровых вознаграждений и реферальных программ в Telegram. Все вознаграждения начисляются автоматически после выполнения действий, согласно правилам Партнерской программы Telegram.

**Честное использование**
Мы можем ограничить или отменить вознаграждения в случаях злоупотребления или запрещенной активности.

**Конфиденциальность**
Мы храним только минимальный объем данных. Подробнее см. Политику конфиденциальности.

**Контакт**
Поддержка: t.me/{{username}}`,
        privacy_title: 'Политика конфиденциальности',
        privacy_body: `**Политика конфиденциальности**

{{botname}} обрабатывает только минимальные данные, необходимые для работы: ID пользователя, никнейм, язык и реферальные связи.

**Мы не собираем платежную информацию.**
Обработка данных осуществляется в соответствии с Правилами Telegram.`
    },
    es: {
        terms_title: 'Términos de Uso',
        terms_body: `**Términos de Uso**

Al usar esta Mini App, aceptas las condiciones a continuación.

**Servicio**
Proporcionamos un servicio gamificado de recompensas digitales. Todas las recompensas se acumulan automáticamente según las reglas del Programa de Socios de Telegram.

**Uso Justo**
Podemos limitar las recompensas en casos de abuso o actividad prohibida.

**Privacidad**
Almacenamos solo los datos mínimos necesarios. Ver Política de Privacidad.

**Contacto**
Soporte: t.me/{{username}}`,
        privacy_title: 'Política de Privacidad',
        privacy_body: `**Política de Privacidad**

{{botname}} procesa solo datos mínimos: ID de usuario, apodo, idioma y conexiones de referencia.

**No recopilamos información de pago.**
El procesamiento de datos cumple con los Términos de Servicio de Telegram.`
    },
    de: {
        terms_title: 'Nutzungsbedingungen',
        terms_body: `**Nutzungsbedingungen**

Durch die Nutzung dieser Mini-App stimmen Sie den folgenden Bedingungen zu.

**Service**
Wir bieten einen gamifizierten digitalen Belohnungs- und Empfehlungsdienst innerhalb von Telegram an. Alle Belohnungen werden automatisch nach Abschluss der entsprechenden Aktionen gutgeschrieben, gemäß den Regeln des Telegram-Partnerprogramms.

**Faire Nutzung**
Wir können Belohnungen bei Missbrauch oder verbotenen Aktivitäten einschränken oder stornieren.

**Datenschutz**
Wir speichern nur die minimal notwendigen Daten. Siehe Datenschutzrichtlinie.

**Kontakt**
Support: t.me/{{username}}`,
        privacy_title: 'Datenschutzrichtlinie',
        privacy_body: `**Datenschutzrichtlinie**

{{botname}} verarbeitet nur minimale Daten: Benutzer-ID, Spitzname, Sprache und Empfehlungsverbindungen.

**Wir sammeln keine Zahlungsinformationen.**
Die Datenverarbeitung erfolgt in Übereinstimmung mit den Telegram-Nutzungsbedingungen.`
    }
};

window.Render.renderLegalPage = function (title, content) {
    let overlay = document.getElementById('legal-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'legal-overlay';
        document.body.appendChild(overlay);
    }

    // Dynamic Footer Name
    const config = AppState.getAppData()?.config || {};
    const footerName = config.name || 'Bot App';

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
                © ${new Date().getFullYear()} ${footerName} · This Mini App is not affiliated with Telegram
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
    const appData = AppState.getAppData() || {};
    const config = appData.config || {};
    const userLang = (appData.user?.language_code || 'en').substring(0, 2).toLowerCase();

    // Select language content (fallback to 'en')
    const texts = LEGAL_CONTENT[userLang] || LEGAL_CONTENT['en'];

    const botName = config.name || 'EarnHub';
    const botUsername = config.username || 'HubAggregatorBot';
    const cleanUsername = botUsername.replace('@', '');

    const content = texts.terms_body
        .replace('{{username}}', cleanUsername)
        .replace('{{botname}}', botName);

    const htmlContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#fff;">$1</strong>')
        .replace(/\n\n/g, '<br><br>');

    window.Render.renderLegalPage(texts.terms_title, htmlContent);
};

window.Render.renderPrivacy = function () {
    const appData = AppState.getAppData() || {};
    const config = appData.config || {};
    const userLang = (appData.user?.language_code || 'en').substring(0, 2).toLowerCase();

    // Select language content (fallback to 'en')
    const texts = LEGAL_CONTENT[userLang] || LEGAL_CONTENT['en'];

    const botName = config.name || 'EarnHub';

    const content = texts.privacy_body.replace('{{botname}}', botName);

    const htmlContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#fff;">$1</strong>')
        .replace(/\n\n/g, '<br><br>');

    window.Render.renderLegalPage(texts.privacy_title, htmlContent);
};
