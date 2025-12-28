# 🚂 Railway Setup Status - universal-bot-os

## ✅ Що зроблено:

1. **Проект створено:**
   - ID: `46aa6dc7-1bb1-49b7-ac65-e9a8ac73636a`
   - URL: https://railway.app/project/46aa6dc7-1bb1-49b7-ac65-e9a8ac73636a

2. **Сервіс 'api' створено:**
   - ID: `a9598ef7-0499-439f-bf3c-c6de5f3cd022`

3. **Токени налаштовано:**
   - `RAILWAY_TOKEN` - Account Token (для API)
   - `RAILWAY_PROJECT_TOKEN_UNIVERSAL_BOT_OS` - Project Token

---

## ⚠️ Обмеження Railway API:

**GraphQL API не дозволяє:**
- ❌ Встановлювати змінні оточення через `variableUpsert` (400 Bad Request)
- ❌ Отримувати змінні через `service.variables` (400 Bad Request)
- ❌ Створювати плагіни (PostgreSQL/Redis) через API

**Рішення:**
- Використовуй Railway UI або Railway CLI для встановлення змінних

---

## 📋 Що потрібно зробити вручну:

### 1. Додати PostgreSQL та Redis:

**Через Railway UI:**
1. Відкрий: https://railway.app/project/46aa6dc7-1bb1-49b7-ac65-e9a8ac73636a
2. Натисни **"New"** → **"Database"** → **"PostgreSQL"**
3. Натисни **"New"** → **"Database"** → **"Redis"**
4. Railway автоматично створить `DATABASE_URL` та `REDIS_URL` для сервісу `api`

### 2. Встановити змінні оточення:

**Через Railway UI:**
1. Відкрий сервіс `api`
2. Перейди в **"Variables"**
3. Додай змінні:

```env
SECRET_KEY=oixjJs7E8Y9v1ziK1Mk90lRnnPMV_eUmK_tvWgrkf-Q
ANTHROPIC_API_KEY=sk-ant-api03-... (з твого .env)
```

**Через Railway CLI:**
```bash
cd universal-bot-os
railway link 46aa6dc7-1bb1-49b7-ac65-e9a8ac73636a
railway variables set SECRET_KEY=oixjJs7E8Y9v1ziK1Mk90lRnnPMV_eUmK_tvWgrkf-Q
railway variables set ANTHROPIC_API_KEY=sk-ant-api03-...
```

---

## 🔑 Згенерований SECRET_KEY:

```
SECRET_KEY=oixjJs7E8Y9v1ziK1Mk90lRnnPMV_eUmK_tvWgrkf-Q
```

**⚠️ Збережи цей ключ!** Він потрібен для безпеки додатку.

---

## 📊 Поточний статус:

| Змінна | Статус | Дії |
|--------|--------|-----|
| `DATABASE_URL` | ❌ | Додай PostgreSQL через UI |
| `REDIS_URL` | ❌ | Додай Redis через UI |
| `SECRET_KEY` | ⏳ | Встанови через UI/CLI |
| `ANTHROPIC_API_KEY` | ⏳ | Встанови через UI/CLI |

---

## 🚀 Наступні кроки:

1. ✅ Додай PostgreSQL та Redis через Railway UI
2. ✅ Встанови змінні оточення
3. ✅ Підключи GitHub репозиторій для автоматичного деплою
4. ✅ Або задеплой вручну: `railway up`

---

**💡 Порада:** Railway автоматично створить `DATABASE_URL` та `REDIS_URL` коли додаси бази даних. Потім просто додай `SECRET_KEY` та `ANTHROPIC_API_KEY` вручну.

