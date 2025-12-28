# 🤖 Налаштування Telegram Бота

## 📋 Інформація про тестовий бот

- **Bot Username:** `EarnHubAggregatorBot`
- **Bot Token:** `8067111045:AAFTM3kZEFrQvFnRnVI76WziDu2IHnix3ww`
- **Deployment URL:** `https://api-production-57e8.up.railway.app`

---

## 🚀 Крок 1: Створити бота в системі

### Варіант A: Через Admin UI (рекомендовано)

1. Відкрий Admin Panel: `https://api-production-57e8.up.railway.app/admin`
2. Перейди на вкладку **"Bots"**
3. Натисни **"+ Create Bot"**
4. Заповни форму:
   - **Name:** `EarnHubAggregatorBot` (або будь-яка назва)
   - **Platform:** `telegram`
   - **Token:** `8067111045:AAFTM3kZEFrQvFnRnVI76WziDu2IHnix3ww`
   - **Default Language:** `uk` (або інша мова)
5. Натисни **"Create"**

### Варіант B: Через API (curl)

```bash
curl -X POST https://api-production-57e8.up.railway.app/api/v1/admin/bots \
  -H "Content-Type: application/json" \
  -d '{
    "name": "EarnHubAggregatorBot",
    "platform_type": "telegram",
    "token": "8067111045:AAFTM3kZEFrQvFnRnVI76WziDu2IHnix3ww",
    "default_lang": "uk",
    "config": {}
  }'
```

**Відповідь містить `id` бота - збережи його для наступних кроків!**

---

## 🔗 Крок 2: Налаштувати Telegram Webhook

Після створення бота, налаштуй webhook, щоб Telegram надсилав оновлення на наш сервер.

### Варіант A: Через Telegram Bot API (curl)

```bash
curl -X POST "https://api.telegram.org/bot8067111045:AAFTM3kZEFrQvFnRnVI76WziDu2IHnix3ww/setWebhook" \
  -d "url=https://api-production-57e8.up.railway.app/api/v1/webhooks/telegram/8067111045:AAFTM3kZEFrQvFnRnVI76WziDu2IHnix3ww"
```

### Варіант B: Через браузер

Відкрий в браузері:
```
https://api.telegram.org/bot8067111045:AAFTM3kZEFrQvFnRnVI76WziDu2IHnix3ww/setWebhook?url=https://api-production-57e8.up.railway.app/api/v1/webhooks/telegram/8067111045:AAFTM3kZEFrQvFnRnVI76WziDu2IHnix3ww
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
curl "https://api.telegram.org/bot8067111045:AAFTM3kZEFrQvFnRnVI76WziDu2IHnix3ww/getWebhookInfo"
```

**Очікувана відповідь:**
```json
{
  "ok": true,
  "result": {
    "url": "https://api-production-57e8.up.railway.app/api/v1/webhooks/telegram/8067111045:AAFTM3kZEFrQvFnRnVI76WziDu2IHnix3ww",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

### 3.2 Відправ тестове повідомлення

1. Відкрий бота в Telegram: `@EarnHubAggregatorBot`
2. Надішли будь-яке повідомлення (наприклад, `/start`)
3. Перевір логи в Railway:
   - Відкрий Railway Dashboard
   - Перейди в сервіс `api` → `Deploy Logs`
   - Мають з'явитися записи про обробку повідомлення

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

