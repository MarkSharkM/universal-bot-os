# 🔧 Environment Variables для Universal Bot OS

## ✅ Що вже є в `.env`:
- `ANTHROPIC_API_KEY` - ✅ Готово!

---

## ❌ Що потрібно додати:

### 🔴 Обов'язкові (без них не запуститься):

1. **`DATABASE_URL`** - URL для PostgreSQL
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/universal_bot_os
   ```
   - Для локального тесту: `postgresql://postgres:password@localhost:5432/universal_bot_os`
   - На Railway: Railway автоматично надасть `DATABASE_URL` при додаванні PostgreSQL сервісу

2. **`SECRET_KEY`** - Секретний ключ для JWT/безпеки
   ```env
   SECRET_KEY=your-super-secret-key-min-32-chars-long
   ```
   - Згенеруй: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

---

### 🟡 Опціональні (мають default значення):

3. **`REDIS_URL`** - URL для Redis (опціонально)
   ```env
   REDIS_URL=redis://localhost:6379
   ```
   - Default: `redis://localhost:6379`
   - На Railway: Railway автоматично надасть при додаванні Redis

4. **`OPENAI_API_KEY`** - OpenAI API ключ (якщо використовуєш OpenAI)
   ```env
   OPENAI_API_KEY=sk-...
   ```
   - Опціонально, якщо використовуєш тільки Anthropic

5. **`PORT`** - Порт для сервера
   ```env
   PORT=8000
   ```
   - Default: `8000`
   - На Railway: Railway автоматично встановить

---

## 📝 Приклад повного `.env` для локального тесту:

```env
# Universal Bot OS - Required
DATABASE_URL=postgresql://postgres:password@localhost:5432/universal_bot_os
SECRET_KEY=your-super-secret-key-min-32-chars-long-generate-with-secrets-token-urlsafe

# Universal Bot OS - Optional
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...  # Якщо потрібен OpenAI
PORT=8000

# AI Providers (вже є)
ANTHROPIC_API_KEY=sk-ant-api03-...  # ✅ Вже є в твоєму .env

# Railway (вже є)
RAILWAY_TOKEN=3eafda3e-4ce7-4834-b359-99a59a17e884  # ✅ Вже є
RAILWAY_PROJECT_TOKEN=159c843c-4489-4d07-beec-87e1107d2cb3  # ✅ Вже є

# N8N (старе, можна залишити)
N8N_BASE_URL=https://app.hubaggregator.com
N8N_MCP_KEY=...
N8N_API_KEY=...
GITHUB_PAT=...
```

---

## 🚀 Швидка команда для генерації SECRET_KEY:

```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

---

## ✅ Підсумок:

**Мінімум для запуску:**
1. `DATABASE_URL` - обов'язково
2. `SECRET_KEY` - обов'язково

**Вже є:**
- `ANTHROPIC_API_KEY` ✅

**Опціонально:**
- `REDIS_URL` (має default)
- `OPENAI_API_KEY` (якщо потрібен)
- `PORT` (має default)

---

**Додай ці 2 змінні і можна запускати!** 🎉

