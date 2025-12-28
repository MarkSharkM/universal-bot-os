# 🤖 Universal Bot OS - Multi-Tenant Architecture

**Масштабована AI-френдлі платформа для керування 100+ ботами**

## 📋 TODO План (17 задач)

### ✅ Фаза 1: Фундамент (3 задачі)
- [x] Структура проекту - модульна FastAPI архітектура
- [ ] SQL схема - моделі SQLAlchemy
- [ ] Конфігурація - core/config.py, database.py, security.py

### 🔄 Фаза 2: Міграція з n8n (3 задачі)
- [ ] Аналіз n8n - проаналізувати JSON експорт (60 нод)
- [ ] Витяг логіки - визначити бізнес-логіку та залежності
- [ ] Сервіси - реалізувати чисту логіку в app/services/

### 🚀 Фаза 3: Core функціонал (3 задачі)
- [ ] Адаптери - Telegram adapter + omnichannel інтерфейс
- [ ] API endpoints - вебхуки, Mini Apps, SEO
- [ ] i18n - система перекладів (5+ мов)

### 🧠 Фаза 4: AI та дані (2 задачі)
- [ ] AI інтеграція - OpenAI/Anthropic з підтримкою мови
- [ ] Міграція даних - скрипти з Google Sheets до PostgreSQL

### 🐳 Фаза 5: Деплой (3 задачі)
- [ ] Docker & Railway - Dockerfile, docker-compose.yml, railway.json
- [ ] Деплой - налаштування Railway з PostgreSQL + Redis
- [ ] Моніторинг - health checks, логування, error tracking

### 👨‍💼 Фаза 6: Адмінка (3 задачі)
- [ ] Адмінка API - CRUD для ботів, промптів, конфігурацій
- [ ] Адмінка UI - веб-інтерфейс для керування
- [ ] Адмінка статистика - дашборд з метриками

---

## 🏗️ Архітектура

### Структура проекту
```
universal-bot-os/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   │
│   ├── api/                    # API endpoints
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── webhooks.py     # Telegram webhooks
│   │   │   ├── mini_apps.py    # Mini Apps endpoints
│   │   │   ├── seo.py          # SEO endpoints
│   │   │   └── admin.py        # Admin API
│   │
│   ├── core/                   # Core infrastructure
│   │   ├── __init__.py
│   │   ├── config.py           # Settings (Pydantic)
│   │   ├── database.py         # DB connection
│   │   ├── security.py         # Auth, JWT
│   │   └── dependencies.py     # FastAPI dependencies
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── bot.py              # Bot model
│   │   ├── user.py             # User model
│   │   ├── message.py          # Message model
│   │   ├── translation.py     # Translation model
│   │   └── business_data.py   # Business data models
│   │
│   ├── schemas/                # Pydantic schemas (API)
│   │   ├── __init__.py
│   │   ├── bot.py
│   │   ├── user.py
│   │   └── message.py
│   │
│   ├── services/               # Business logic (чиста логіка)
│   │   ├── __init__.py
│   │   ├── bot_service.py      # Bot management
│   │   ├── user_service.py     # User management
│   │   ├── message_service.py  # Message handling
│   │   ├── ai_service.py       # AI integration
│   │   └── translation_service.py  # i18n
│   │
│   ├── adapters/               # Platform adapters
│   │   ├── __init__.py
│   │   ├── base.py             # Base adapter interface
│   │   ├── telegram.py         # Telegram adapter
│   │   └── web.py              # Web chat adapter (майбутнє)
│   │
│   └── utils/                  # Utilities
│       ├── __init__.py
│       └── helpers.py
│
├── migrations/                 # Alembic migrations
├── scripts/                    # Utility scripts
│   └── migrate_from_sheets.py  # Google Sheets migration
│
├── tests/                      # Tests
│   ├── __init__.py
│   ├── test_api/
│   ├── test_services/
│   └── test_adapters/
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── railway.json
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Технологічний стек
- **Backend:** Python 3.11+, FastAPI
- **Database:** PostgreSQL (SQLAlchemy/SQLModel)
- **Cache:** Redis
- **Infrastructure:** Railway
- **AI:** OpenAI/Anthropic
- **Frontend (майбутнє):** Next.js для адмінки

---

## 🗄️ SQL Схема

### Основні таблиці

#### `bots`
```sql
- id: UUID (PK)
- platform_type: VARCHAR (tg/web/whatsapp)
- token: VARCHAR (encrypted)
- name: VARCHAR
- config: JSONB (AI prompts, colors, keys, settings)
- default_lang: VARCHAR (uk/en/ru/pl/de)
- is_active: BOOLEAN
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

#### `users`
```sql
- id: UUID (PK)
- external_id: VARCHAR (telegram_id, etc.)
- platform: VARCHAR (telegram/web)
- bot_id: UUID (FK -> bots.id)
- language_code: VARCHAR (uk/en/ru/pl/de)
- balance: DECIMAL (10,2)
- metadata: JSONB (custom fields)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
- UNIQUE(bot_id, external_id, platform)
```

#### `messages`
```sql
- id: UUID (PK)
- user_id: UUID (FK -> users.id)
- bot_id: UUID (FK -> bots.id)
- role: VARCHAR (user/assistant/system)
- content: TEXT
- metadata: JSONB (message_id, reply_to, etc.)
- timestamp: TIMESTAMP
- INDEX(user_id, timestamp) для контексту AI
```

#### `translations`
```sql
- id: UUID (PK)
- key: VARCHAR (message.welcome, button.start, etc.)
- lang: VARCHAR (uk/en/ru/pl/de)
- text: TEXT
- UNIQUE(key, lang)
```

#### `business_data` (залежить від ніші)
```sql
- id: UUID (PK)
- bot_id: UUID (FK -> bots.id)
- data_type: VARCHAR (wallet, partner, log, etc.)
- data: JSONB (flexible structure)
- created_at: TIMESTAMP
- INDEX(bot_id, data_type)
```

---

## 🔑 Ключові принципи

### 1. Omnichannel Architecture
- **Base Adapter Interface:** Всі адаптери реалізують спільний інтерфейс
- **Service Layer:** Бізнес-логіка незалежна від платформи
- **Додавання нової платформи:** Тільки новий adapter, без змін у services/

### 2. Multi-Tenancy
- Кожен запит має `bot_id`
- Ізоляція даних на рівні БД (WHERE bot_id = ?)
- Shared infrastructure, isolated data

### 3. i18n
- Всі системні рядки в таблиці `translations`
- Мова користувача зберігається в `users.language_code`
- AI промпти враховують мову користувача

### 4. AI-Friendly Code
- Модульна структура
- Документація в коді
- Чіткі назви функцій/класів
- Type hints скрізь

---

## 📝 Наступні кроки

1. ✅ Створено TODO план (17 задач)
2. ⏳ Створюю базову структуру проекту
3. ⏳ Створюю SQL моделі
4. ⏳ Очікую JSON експорт n8n для аналізу

**Готовий до роботи!** 🚀

