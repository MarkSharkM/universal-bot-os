# 🚀 Quick Start - Universal Bot OS

## ⚡ Швидкий запуск

### 1️⃣ Локально (для тестування)

```bash
# 1. Встанови залежності
cd universal-bot-os
pip install -r requirements.txt

# 2. Створи .env файл
cp .env.example .env  # або створи вручну

# 3. Налаштуй БД (PostgreSQL)
# В .env вкажи DATABASE_URL

# 4. Створи таблиці
python -c "from app.core.database import engine; from app.models import Base; Base.metadata.create_all(engine)"

# 5. Запусти сервер
uvicorn app.main:app --reload
```

**API буде доступний:** `http://localhost:8000`

---

### 2️⃣ На Railway (production)

**Варіант A: Через Railway CLI**
```bash
# 1. Встанови Railway CLI
npm i -g @railway/cli

# 2. Логін
railway login

# 3. Створи проект
railway init

# 4. Додай PostgreSQL та Redis
railway add postgresql
railway add redis

# 5. Деплой
railway up
```

**Варіант B: Через GitHub (рекомендовано)**
1. Завантаж код в GitHub
2. На Railway: New Project → Deploy from GitHub
3. Додай PostgreSQL та Redis сервіси
4. Налаштуй змінні оточення (Environment Variables)
5. Railway автоматично задеплоїть

---

## 📋 Що потрібно налаштувати

### Обов'язкові змінні оточення:
```env
DATABASE_URL=postgresql://...  # Railway надасть автоматично
REDIS_URL=redis://...          # Railway надасть автоматично
SECRET_KEY=your-secret-key      # Згенеруй сам
```

### Опціонально (для AI):
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 🤖 Підключення Telegram бота

### 1. Створи бота через BotFather
- Отримай токен: `123456:ABC-DEF...`

### 2. Додай бота в систему (через Admin UI або API)

**Через Admin UI:**
- Відкрий `/admin`
- Вкладка "Bots" → "Create Bot"
- Введи токен та налаштування

**Через API:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/bots \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Bot",
    "platform_type": "telegram",
    "token": "123456:ABC-DEF...",
    "default_lang": "uk"
  }'
```

### 3. Налаштуй webhook на Telegram
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://your-railway-url.railway.app/api/v1/webhooks/telegram/<TOKEN>"
```

**АБО** використай Railway URL:
```
https://your-app.railway.app/api/v1/webhooks/telegram/<BOT_TOKEN>
```

---

## 📊 Міграція даних з Google Sheets

```bash
# 1. Експортуй дані з Google Sheets в CSV
# 2. Запусти скрипт міграції
python scripts/migrate_from_sheets.py user_wallets.csv bot_log.csv Partners_Settings.csv
```

Детальніше: `scripts/README_MIGRATION.md`

---

## ✅ Перевірка роботи

1. **Health check:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Admin UI:**
   - Відкрий `http://localhost:8000/admin`

3. **API docs:**
   - Відкрий `http://localhost:8000/docs`

---

## 🔄 n8n більше НЕ потрібен!

**Вся логіка тепер в Python:**
- ✅ Команди → `CommandService`
- ✅ Переклади → `TranslationService`
- ✅ Партнери → `PartnerService`
- ✅ Реферали → `ReferralService`
- ✅ Заробітки → `EarningsService`
- ✅ Гаманці → `WalletService`
- ✅ AI → `AIService`

**n8n можна вимкнути!** 🎉

---

## 🆘 Проблеми?

1. **БД не підключається:**
   - Перевір `DATABASE_URL` в `.env`
   - Переконайся, що PostgreSQL запущений

2. **Бот не відповідає:**
   - Перевір webhook URL
   - Перевір логи: `railway logs`

3. **404 на `/admin`:**
   - Перевір, що файл `app/static/admin.html` існує

---

## 📚 Документація

- `DEPLOYMENT.md` - детальний гайд по деплою
- `API_ENDPOINTS.md` - всі API endpoints
- `ADMIN_API.md` - Admin API документація
- `MONITORING.md` - моніторинг та логи

---

**Готово до запуску!** 🚀

