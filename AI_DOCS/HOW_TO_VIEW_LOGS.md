# 📊 Як дивитись логи GitHub та Railway

Повна інструкція для AI та розробників.

---

## 🔑 Токени для доступу

**GitHub:**
```
GITHUB_PAT_NEW=<your_github_token>
```
Токен зберігається в `.env` файлі або в AI_DOCS/DOCS_FOR_NEW_AI.md

**Railway:**
```
RAILWAY_PROJECT_TOKEN_N8N_MCP=<your_railway_token>
```
Токен зберігається в `.env` файлі або в AI_DOCS/DOCS_FOR_NEW_AI.md

⚠️ **Увага:** Railway Project Token не працює з GraphQL API, потрібен Account Token для повного доступу.
⚠️ **Безпека:** Ніколи не комітьте токени в git! Використовуйте `.env` файли або змінні середовища.

---

## 📝 GitHub - Перегляд логів

### 1. Через GitHub API (для AI)

#### Отримати останні коміти:
```bash
curl -H "Authorization: token $GITHUB_PAT_NEW" \
  "https://api.github.com/repos/MarkSharkM/universal-bot-os/commits?per_page=10"
```

#### Отримати конкретний коміт:
```bash
curl -H "Authorization: token $GITHUB_PAT_NEW" \
  "https://api.github.com/repos/MarkSharkM/universal-bot-os/commits/4acff8f"
```

#### Отримати зміни в коміті:
```bash
curl -H "Authorization: token $GITHUB_PAT_NEW" \
  "https://api.github.com/repos/MarkSharkM/universal-bot-os/commits/4acff8f" | \
  python3 -m json.tool | grep -A 20 '"files"'
```

#### Отримати GitHub Actions runs (якщо налаштовано):
```bash
curl -H "Authorization: token $GITHUB_PAT_NEW" \
  "https://api.github.com/repos/MarkSharkM/universal-bot-os/actions/runs?per_page=5"
```

#### Отримати логи конкретного workflow run:
```bash
# Спочатку отримати run_id з попереднього запиту
curl -H "Authorization: token $GITHUB_PAT_NEW" \
  "https://api.github.com/repos/MarkSharkM/universal-bot-os/actions/runs/{run_id}/logs"
```

### 2. Через Git CLI (локально)

#### Останні коміти:
```bash
cd /Users/anastasiiamalynovska/Desktop/mark/railway-mcp-project/universal-bot-os
git log --oneline -10
```

#### Детальна інформація про коміт:
```bash
git show 4acff8f
```

#### Зміни між комітами:
```bash
git diff HEAD~5..HEAD
```

#### Логи з датами:
```bash
git log --format="%h %s %ad" --date=short -10
```

### 3. Через GitHub Web UI

1. Відкрий: https://github.com/MarkSharkM/universal-bot-os
2. Вкладка **"Commits"** - всі коміти
3. Клікни на коміт - деталі та зміни
4. Вкладка **"Actions"** - GitHub Actions логи (якщо налаштовано)

---

## 🚂 Railway - Перегляд логів

### 1. Через Railway Web UI (найпростіше)

1. Відкрий: https://railway.app
2. Увійди в акаунт
3. Відкрий проект: **universal-bot-os**
4. Вкладка **"Deployments"** → вибери останній deployment → **"View Logs"**
5. Або вкладка **"Metrics"** → **"Logs"**

### 2. Через Railway CLI

#### Авторизація:
```bash
railway login
# Або через токен:
export RAILWAY_TOKEN=your_account_token
```

#### Перегляд логів:
```bash
# Зв'язати проект
railway link

# Переглянути логи
railway logs

# Логи конкретного сервісу
railway logs --service universal-bot-os

# Логи з фільтром
railway logs | grep ERROR
```

### 3. Через Railway API (обмежено)

⚠️ **Project Token не працює з GraphQL API!**

#### Спробувати через REST API:
```bash
curl -H "Authorization: Bearer $RAILWAY_PROJECT_TOKEN_N8N_MCP" \
  "https://api.railway.app/v1/projects"
```

#### Через GraphQL (потрібен Account Token):
```bash
curl -X POST "https://backboard.railway.app/graphql/v2" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCOUNT_TOKEN" \
  -d '{
    "query": "query { projects { edges { node { id name } } } }"
  }'
```

### 4. Через Application API Endpoint (новий)

#### Перегляд логів через API:
```bash
# Останні 50 логів
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/logs"

# Тільки помилки
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/logs?level=ERROR"

# Пошук по тексту
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/logs?search=wallet"

# Комбінація фільтрів
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/logs?level=ERROR&search=TON&limit=20"
```

**Параметри:**
- `limit` (1-500, за замовчуванням 50) - кількість рядків логів
- `level` (DEBUG, INFO, WARNING, ERROR) - фільтр за рівнем
- `search` - пошук тексту в логах

⚠️ **Примітка:** На Railway логи зберігаються в stdout/stderr і доступні через Railway dashboard. Цей endpoint читає з файлів логів (якщо вони доступні локально).

### 5. Через Application Health Endpoints

#### Health check:
```bash
curl -k "https://api-production-57e8.up.railway.app/health"
```

#### Тест команди (для перевірки логів в коді):
```bash
curl -k -X POST \
  "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/test-command?command=/top&user_lang=uk"
```

---

## 🤖 Для AI - Автоматичний перегляд логів

### Python скрипт для перегляду GitHub комітів:

```python
import requests
import json

GITHUB_TOKEN = os.getenv("GITHUB_PAT_NEW")  # З .env або змінних середовища
REPO = "MarkSharkM/universal-bot-os"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Отримати останні коміти
response = requests.get(
    f"https://api.github.com/repos/{REPO}/commits?per_page=10",
    headers=headers
)

commits = response.json()
for commit in commits:
    print(f"{commit['sha'][:7]} - {commit['commit']['message']} - {commit['commit']['author']['date']}")
```

### Python скрипт для перевірки Railway health:

```python
import requests

# Health check
response = requests.get("https://api-production-57e8.up.railway.app/health", verify=False)
print(json.dumps(response.json(), indent=2))

# Test command
response = requests.post(
    "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/test-command",
    params={"command": "/top", "user_lang": "uk"},
    verify=False
)
print(json.dumps(response.json(), indent=2))
```

---

## 🔍 Що шукати в логах

### GitHub:
- **Коміти** - хто і коли зробив зміни
- **Зміни в файлах** - що саме було змінено
- **GitHub Actions** - логи деплоїв (якщо налаштовано)

### Railway:
- **Application logs** - логи FastAPI додатку
- **ERROR** - помилки в коді
- **WARNING** - попередження
- **INFO** - загальна інформація про виконання команд
- **Database queries** - запити до бази даних (якщо увімкнено SQLAlchemy logging)

### Ключові слова для пошуку:
- `ERROR` - всі помилки
- `handle_command` - обробка команд
- `_handle_top` / `_handle_earnings` / `_handle_partners` - конкретні команди
- `Timeout` - зависання
- `Database` - проблеми з БД
- `Telegram API` - проблеми з відправкою повідомлень

---

## 📋 Швидкі команди для AI

### Перевірити останні коміти:
```bash
curl -H "Authorization: token $GITHUB_PAT_NEW" \
  "https://api.github.com/repos/MarkSharkM/universal-bot-os/commits?per_page=5" | \
  python3 -m json.tool | grep -E '"sha"|"message"'
```

### Перевірити health:
```bash
curl -k "https://api-production-57e8.up.railway.app/health" | python3 -m json.tool
```

### Переглянути логи через API:
```bash
# Останні помилки
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/logs?level=ERROR&limit=20" | \
  python3 -m json.tool

# Пошук по тексту
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/logs?search=wallet" | \
  python3 -m json.tool
```

### Тест команди:
```bash
curl -k -X POST \
  "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/test-command?command=/top&user_lang=uk" | \
  python3 -m json.tool
```

---

## 🎯 Типові сценарії

### Сценарій 1: Команда зависає
1. Перевір Railway логи через Web UI
2. Шукай `ERROR` або `Timeout`
3. Перевір останній коміт через GitHub
4. Тестуй через `/test-command` endpoint

### Сценарій 2: Помилка після деплою
1. Перевір GitHub коміти - що було змінено
2. Перевір Railway логи - де саме помилка
3. Перевір health endpoint - чи працює додаток

### Сценарій 3: Проблема з базою даних
1. Шукай в Railway логах: `Database`, `SQLAlchemy`, `timeout`
2. Перевір health endpoint - чи підключена БД
3. Перевір останні зміни в `database.py`

---

## 📚 Додаткові ресурси

- **GitHub API Docs:** https://docs.github.com/en/rest
- **Railway Dashboard:** https://railway.app
- **Railway API Docs:** https://docs.railway.app/reference/api
- **Railway CLI Docs:** https://docs.railway.app/develop/cli

---

---

## 📝 Додаткова інформація

### Структура логів в додатку

Логи зберігаються в:
- `logs/app.log` - всі логи (ротація 10MB, 5 файлів)
- `logs/error.log` - тільки помилки (ротація 10MB, 5 файлів)

**Формат логів:**
```
2024-12-28 10:30:45 - app.api.v1.webhooks - INFO - POST /api/v1/webhooks/telegram/... - Status: 200 - Time: 0.123s
```

**Рівні логування:**
- `DEBUG` - детальна інформація (тільки в development)
- `INFO` - загальна інформація
- `WARNING` - попередження
- `ERROR` - помилки

### Railway логування

На Railway:
- Логи автоматично виводяться в stdout/stderr
- Доступні в реальному часі через Railway dashboard
- Зберігаються протягом обмеженого часу (залежить від плану Railway)
- Для довготривалого зберігання використовуйте зовнішні сервіси (Datadog, Logtail, тощо)

---

**Останнє оновлення:** 31 грудня 2025

