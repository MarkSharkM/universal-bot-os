# 🤖 Налаштування Telegram Бота

## 📋 Інформація

- **Deployment URL:** `https://api-production-57e8.up.railway.app`
- **Admin Panel:** `https://api-production-57e8.up.railway.app/admin`

> ⚠️ **Токени:** Див. `../AI_DOCS/01_AI_AGENT_QUICK_START/HOW_TO_VIEW_LOGS.md`

---

## 🚀 Крок 1: Створити бота в системі

### Варіант A: Через Admin UI (рекомендовано)

1. Відкрий Admin Panel: `https://api-production-57e8.up.railway.app/admin`
2. Залогінься (credentials в Railway env vars)
3. Перейди на вкладку **"Bots"**
4. Натисни **"+ Create Bot"**
5. Заповни форму:
   - **Name:** назва бота
   - **Platform:** `telegram`
   - **Token:** токен від @BotFather
   - **Default Language:** `uk` (або інша мова)
6. Натисни **"Create"**

### Варіант B: Через API (curl)

```bash
curl -X POST https://api-production-57e8.up.railway.app/api/v1/admin/bots \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "YourBotName",
    "platform_type": "telegram",
    "token": "YOUR_BOT_TOKEN",
    "default_lang": "uk",
    "config": {}
  }'
```

**Відповідь містить `id` бота - збережи його для наступних кроків!**

---

## 🔗 Крок 2: Налаштувати Telegram Webhook

Після створення бота, налаштуй webhook, щоб Telegram надсилав оновлення на наш сервер.

### Через Telegram Bot API (curl)

```bash
# Замініть YOUR_BOT_TOKEN на реальний токен
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" \
  -d "url=https://api-production-57e8.up.railway.app/api/v1/webhooks/telegram/YOUR_BOT_TOKEN"
```

**Очікувана відповідь:**
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

---

## ✅ Крок 3: Перевірка

### 3.1 Перевір webhook

```bash
curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo"
```

### 3.2 Відправ тестове повідомлення

1. Відкрий бота в Telegram
2. Надішли `/start`
3. Перевір логи в Railway Dashboard → Deploy Logs

### 3.3 Перевір в Admin UI

1. Відкрий `https://api-production-57e8.up.railway.app/admin`
2. Перейди на вкладку **"Stats"**
3. Вибери бота зі списку
4. Має з'явитися статистика (користувачі, повідомлення тощо)

---

## 🔧 Крок 4: Налаштування AI (опціонально)

Якщо хочеш, щоб бот відповідав через AI:

1. Відкрий Admin UI → вкладка **"AI Config"**
2. Вибери бота зі списку
3. Заповни:
   - **Provider:** `anthropic` (або `openai`)
   - **Model:** `claude-3-5-sonnet-20241022` (або інша модель)
   - **API Key:** твій API ключ
   - **Temperature:** `0.7`
   - **System Prompt:** налаштуй під свій бот
4. Натисни **"Save"**

---

## 📝 Крок 5: Імпорт даних (опціонально)

Якщо потрібно імпортувати дані з Google Sheets:

1. Експортуй дані з Google Sheets в CSV
2. Використай скрипти з `scripts/`:
   ```bash
   # Імпорт перекладів
   railway run python scripts/import_translations.py
   
   # Імпорт партнерів
   railway run python scripts/import_partners_from_csv.py
   
   # Міграція з Google Sheets
   railway run python scripts/migrate_from_sheets.py
   ```

---

## 🐛 Troubleshooting

### Проблема: Webhook не працює

**Рішення:**
1. Перевір, чи бот створений в системі
2. Перевір, чи URL правильний (має містити token в кінці)
3. Перевір логи Railway на наявність помилок

### Проблема: Бот не відповідає

**Рішення:**
1. Перевір, чи AI налаштований (якщо використовуєш AI)
2. Перевір, чи є переклади для мови бота
3. Перевір логи Railway

### Проблема: 404 при відкритті `/admin`

**Рішення:**
1. Перевір, чи домен правильний: `https://api-production-57e8.up.railway.app`
2. Перевір, чи сервіс `api` онлайн в Railway

---

## 📚 Корисні посилання

- **Admin UI:** `https://api-production-57e8.up.railway.app/admin`
- **Health Check:** `https://api-production-57e8.up.railway.app/health`
- **API Docs:** `https://api-production-57e8.up.railway.app/docs` (якщо додано Swagger)

---

**Готово!** 🎉 Бот налаштований і готовий до використання.

