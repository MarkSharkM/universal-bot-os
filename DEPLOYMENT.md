# 🚀 Deployment Guide - Railway

**Інструкції для деплою Universal Bot OS на Railway**

---

## 📋 Передумови

1. **Railway account** - зареєструйся на [railway.app](https://railway.app)
2. **GitHub repository** - завантаж код в GitHub
3. **PostgreSQL** - Railway автоматично надасть
4. **Redis** - Railway автоматично надасть

---

## 🔧 Крок 1: Підготовка проекту

### 1.1 Перевір файли

**Обов'язкові файли:**
- ✅ `Dockerfile` - вже створено
- ✅ `railway.json` - вже створено
- ✅ `requirements.txt` - вже створено
- ✅ `.env.example` - створи приклад

### 1.2 Створи `.env.example`

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here

# AI Providers (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Environment
ENVIRONMENT=production
DEBUG=false
PORT=8000
```

---

## 🚂 Крок 2: Створення проекту на Railway

### 2.1 Новий проект

1. Зайди в [Railway Dashboard](https://railway.app/dashboard)
2. Натисни **"New Project"**
3. Обери **"Deploy from GitHub repo"**
4. Вибери свій репозиторій

### 2.2 Додай сервіси

**PostgreSQL:**
1. Натисни **"+ New"**
2. Обери **"Database"** → **"PostgreSQL"**
3. Railway автоматично створить БД

**Redis:**
1. Натисни **"+ New"**
2. Обери **"Database"** → **"Redis"**
3. Railway автоматично створить Redis

**FastAPI Service:**
1. Натисни **"+ New"**
2. Обери **"GitHub Repo"**
3. Вибери репозиторій з кодом

---

## ⚙️ Крок 3: Налаштування змінних оточення

### 3.1 Environment Variables

В налаштуваннях FastAPI сервісу додай:

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=<generate-random-string>
ENVIRONMENT=production
DEBUG=false
PORT=8000
```

**Як отримати DATABASE_URL:**
1. Відкрий PostgreSQL service
2. Скопіюй `DATABASE_URL` з вкладки "Variables"
3. Використай `${{Postgres.DATABASE_URL}}` для автоматичного підключення

**Як згенерувати SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3.2 AI Keys (опціонально)

Якщо використовуєш AI:
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 🗄️ Крок 4: Міграція бази даних

### 4.1 Створи таблиці

**Варіант 1: Через Railway CLI**
```bash
# Встанови Railway CLI
npm i -g @railway/cli

# Логін
railway login

# Підключись до проекту
railway link

# Запусти міграцію
railway run python -c "from app.core.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine)"
```

**Варіант 2: Через Railway Console**
1. Відкрий PostgreSQL service
2. Натисни **"Query"**
3. Виконай SQL для створення таблиць (або використай Alembic)

**Варіант 3: Через Python скрипт**
```bash
railway run python scripts/create_tables.py
```

---

## 🔄 Крок 5: Деплой

### 5.1 Автоматичний деплой

Railway автоматично:
1. Визначить Dockerfile
2. Збудує образ
3. Запустить контейнер
4. Перевірить health checks

### 5.2 Перевірка

**Health check:**
```bash
curl https://your-app.railway.app/health
```

**Очікувана відповідь:**
```json
{
    "status": "healthy",
    "version": "0.1.0",
    "environment": "production",
    "components": {
        "database": {"status": "healthy"},
        "redis": {"status": "healthy"}
    }
}
```

---

## 🌐 Крок 6: Налаштування домену

### 6.1 Railway Domain

1. Відкрий FastAPI service
2. Перейди в **"Settings"** → **"Networking"**
3. Натисни **"Generate Domain"**
4. Скопіюй URL (наприклад: `universal-bot-os-production.up.railway.app`)

### 6.2 Custom Domain (опціонально)

1. В **"Settings"** → **"Networking"**
2. Додай свій домен
3. Налаштуй DNS записи

---

## 📡 Крок 7: Налаштування Telegram Webhook

### 7.1 Отримай URL

```bash
# Railway domain
WEBHOOK_URL=https://your-app.railway.app/api/v1/webhooks/telegram/{bot_token}
```

### 7.2 Встанови webhook

**Через Telegram Bot API:**
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://your-app.railway.app/api/v1/webhooks/telegram/<BOT_TOKEN>"
```

**Або через код:**
```python
from app.adapters.telegram import TelegramAdapter

adapter = TelegramAdapter()
await adapter.set_webhook(
    bot_id=bot_id,
    url=f"https://your-app.railway.app/api/v1/webhooks/telegram/{bot_token}"
)
```

---

## 🔍 Крок 8: Моніторинг

### 8.1 Railway Metrics

**В Railway Dashboard:**
- CPU використання
- Memory використання
- Network traffic
- Logs

### 8.2 Application Logs

**Перегляд логів:**
1. Відкрий FastAPI service
2. Перейди в **"Deployments"**
3. Натисни на deployment
4. Переглянь **"Logs"**

**Health checks:**
- `/health` - повний статус
- `/health/ready` - readiness probe
- `/health/live` - liveness probe

---

## 🛠️ Крок 9: Оновлення

### 9.1 Автоматичний деплой

Railway автоматично деплоїть при push в `main` branch.

### 9.2 Ручний деплой

1. В Railway Dashboard
2. Натисни **"Redeploy"**

---

## 🔐 Крок 10: Безпека

### 10.1 Environment Variables

**Ніколи не коміть:**
- `.env` файли
- API keys
- Database passwords

**Використовуй Railway Variables:**
- Всі секрети в Railway Dashboard
- Не в коді!

### 10.2 HTTPS

Railway автоматично надає HTTPS для всіх доменів.

---

## 📊 Крок 11: Масштабування

### 11.1 Horizontal Scaling

**В Railway:**
1. Відкрий service settings
2. Збільш **"Instances"**
3. Railway автоматично розподілить навантаження

### 11.2 Resource Limits

**Налаштуй:**
- CPU limits
- Memory limits
- Network limits

---

## ✅ Чеклист деплою

- [ ] Проект створено на Railway
- [ ] PostgreSQL додано
- [ ] Redis додано
- [ ] Environment variables налаштовано
- [ ] Таблиці створено в БД
- [ ] Health checks працюють
- [ ] Telegram webhook налаштовано
- [ ] Логи перевірено
- [ ] Домен налаштовано

---

## 🐛 Troubleshooting

### Проблема: Health check fails

**Рішення:**
1. Перевір `DATABASE_URL` та `REDIS_URL`
2. Перевір логи: `railway logs`
3. Перевір чи таблиці створено

### Проблема: Webhook не працює

**Рішення:**
1. Перевір URL webhook
2. Перевір чи бот активний
3. Перевір логи на помилки

### Проблема: Database connection error

**Рішення:**
1. Перевір `DATABASE_URL` format
2. Перевір чи PostgreSQL service запущено
3. Перевір network connectivity

---

## 📚 Додаткові ресурси

- [Railway Documentation](https://docs.railway.app)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL on Railway](https://docs.railway.app/databases/postgresql)

---

**Готово до деплою!** 🚀

