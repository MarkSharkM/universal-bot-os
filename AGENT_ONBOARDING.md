# 🤖 Онбординг для AI Агента

**Мета:** Швидко зрозуміти проект, API, інструменти та як працювати з системою.

---

## 📋 Основні документи

- **`TODO.md`** - План розробки та прогрес
- **`QUICK_START.md`** - Швидкий старт для розробки та деплою
- **`.env`** - Змінні оточення (токени, ключі API)

---

## 🎯 Що це за проект?

**Universal Bot OS** - масштабована, AI-friendly, multi-tenant платформа для управління 100+ ботами.

### Ключові особливості:
- ✅ Multi-tenant архітектура (ізоляція даних по `bot_id`)
- ✅ FastAPI + PostgreSQL + Redis
- ✅ Міграція з n8n workflow → Python сервіси
- ✅ i18n підтримка (uk, en, ru, de, es)
- ✅ AI інтеграція (OpenAI/Anthropic)
- ✅ Telegram адаптер
- ✅ Admin UI + API

---

## 🛠️ Що я вмію (інструменти для роботи)

### 1. **Швидке оновлення перекладів (БЕЗ DEPLOYMENT)**
```bash
# Оновити переклад миттєво через API
PUT /api/v1/admin/translations/{key}/{lang}?text=новий_текст

# Приклад:
curl -X PUT "https://api-production-57e8.up.railway.app/api/v1/admin/translations/welcome/uk?text=..." 
```

**Переваги:**
- ⚡ Миттєве оновлення (без чекання deployment)
- 🔄 Не потрібно редагувати CSV
- ✅ Всі мови можна оновити одразу

### 2. **Тестування команд (БЕЗ TELEGRAM)**
```bash
# Протестувати будь-яку команду через API
POST /api/v1/admin/bots/{bot_id}/test-command?command=/start&user_lang=uk

# Приклад:
curl -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/test-command?command=/start&user_lang=uk"
```

**Переваги:**
- 🚀 Швидше, ніж через Telegram
- 📊 Бачиш повний JSON (повідомлення, кнопки)
- 🔍 Можна порівняти з прод версією

### 3. **Візуальне порівняння перекладів**
```bash
# Побачити всі пробіли та переноси
GET /api/v1/admin/translations/{key}/{lang}/visual

# Показує пробіли як ·, порожні рядки як [EMPTY]
```

### 4. **Імпорт даних**
```bash
# Імпортувати всі дані (translations, users, partners, logs)
POST /api/v1/admin/bots/{bot_id}/import-data?import_type=all
```

---

## 🔑 API Endpoints

### Admin API (`/api/v1/admin/`)

**Боти:**
- `GET /bots` - Список ботів
- `POST /bots` - Створити бота
- `GET /bots/{bot_id}` - Отримати бота
- `PATCH /bots/{bot_id}` - Оновити бота
- `DELETE /bots/{bot_id}` - Видалити бота (soft delete)
- `GET /bots/{bot_id}/stats` - Статистика бота

**Партнери:**
- `GET /bots/{bot_id}/partners` - Список партнерів
- `POST /bots/{bot_id}/partners` - Створити партнера
- `PATCH /bots/{bot_id}/partners/{partner_id}` - Оновити партнера
- `DELETE /bots/{bot_id}/partners/{partner_id}` - Видалити партнера

**Переклади:**
- `PUT /translations/{key}/{lang}?text=...` - Швидке оновлення (БЕЗ DEPLOYMENT)
- `GET /translations/{key}/{lang}/visual` - Візуальне порівняння

**Тестування:**
- `POST /bots/{bot_id}/test-command?command=/start&user_lang=uk` - Тест команди

**Імпорт:**
- `POST /bots/{bot_id}/import-data?import_type=all` - Імпорт даних

### Webhooks (`/api/v1/webhooks/`)
- `POST /telegram/{bot_token}` - Telegram webhook

### AI (`/api/v1/ai/`)
- `POST /chat` - AI чат
- `GET /config` - AI конфігурація

---

## 📁 Структура проекту

```
universal-bot-os/
├── app/
│   ├── api/v1/          # API endpoints
│   │   ├── admin.py     # Admin API (CRUD, тестування, імпорт)
│   │   ├── webhooks.py  # Telegram webhooks
│   │   └── ai.py        # AI endpoints
│   ├── services/        # Бізнес-логіка (multi-tenant)
│   │   ├── command_service.py
│   │   ├── translation_service.py
│   │   ├── partner_service.py
│   │   └── ...
│   ├── models/          # SQLAlchemy моделі
│   ├── adapters/        # Адаптери (Telegram, тощо)
│   └── static/          # Admin UI (admin.html)
├── scripts/             # Скрипти (міграція, імпорт)
├── old-prod-hub-bot/    # Старі дані з n8n
└── .env                 # Змінні оточення
```

---

## 🔐 Змінні оточення (.env)

**Railway:**
- `RAILWAY_TOKEN` - Account token для Railway API
- `RAILWAY_PROJECT_TOKEN_UNIVERSAL_BOT_OS` - Project token

**GitHub:**
- `GITHUB_PAT_NEW` - Personal Access Token для git push

**База даних:**
- `DATABASE_URL` - PostgreSQL connection string (автоматично з Railway)

**AI:**
- `OPENAI_API_KEY` - OpenAI API key (опціонально)
- `ANTHROPIC_API_KEY` - Anthropic API key (опціонально)

**Telegram:**
- Бот токени зберігаються в базі даних (`Bot.token`)

---

## 🚀 Deployment

**Railway:**
- URL: `https://api-production-57e8.up.railway.app`
- Автоматичний deployment з GitHub
- PostgreSQL + Redis підключені

**GitHub:**
- Репозиторій: `MarkSharkM/universal-bot-os`
- Main branch → автоматичний deploy

---

## 🎯 Процес виправлення команд

### Швидкий метод (рекомендовано):

1. **Користувач показує скрін** з прод версії (що має бути)
2. **Я тестую через API** → бачу поточний результат
3. **Я виправляю код**
4. **Я тестую знову через API** → перевіряю виправлення
5. **Користувач перевіряє в Telegram** (скрін) → фінальна перевірка

### Інструменти:

**Тестування:**
```bash
POST /api/v1/admin/bots/{bot_id}/test-command?command=/start&user_lang=uk
```

**Оновлення перекладів:**
```bash
PUT /api/v1/admin/translations/welcome/uk?text=точний_текст
```

**Візуальне порівняння:**
```bash
GET /api/v1/admin/translations/welcome/uk/visual
```

---

## 📊 Поточний стан

**Деплой:**
- ✅ Railway: `https://api-production-57e8.up.railway.app`
- ✅ Admin UI: `/admin`
- ✅ Health check: `/health`

**Дані:**
- ✅ Translations: імпортовано
- ✅ Users: 5 користувачів
- ✅ Partners: 7 партнерів
- ✅ Logs: 114 записів

**Боти:**
- ✅ EarnHubAggregatorBot (ID: `4f3c45a5-39ac-4d6e-a0eb-263765d70b1a`)

---

## 🔧 Швидкі команди

```bash
# Тест команди
curl -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/test-command?command=/start&user_lang=uk"

# Оновити переклад
curl -X PUT "https://api-production-57e8.up.railway.app/api/v1/admin/translations/welcome/uk?text=..."

# Візуальне порівняння
curl "https://api-production-57e8.up.railway.app/api/v1/admin/translations/welcome/uk/visual"

# Статистика бота
curl "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/stats"
```

---

## 💡 Важливо знати

1. **Multi-tenancy:** Всі запити мають `bot_id` для ізоляції даних
2. **Переклади:** Два типи:
   - Партнери: в `business_data.data` (окремо)
   - Кнопки/логіка: в таблиці `translations` (централізовано)
3. **Швидкі виправлення:** Використовуй API endpoints, не чекай deployment
4. **Тестування:** Завжди тестуй через API перед фінальною перевіркою в Telegram

---

**Готовий працювати! 🚀**

