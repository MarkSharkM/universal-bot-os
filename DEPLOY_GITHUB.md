# 🚀 Деплой через GitHub - Universal Bot OS

## 📋 Кроки для деплою:

### 1. Створи GitHub репозиторій

1. Відкрий https://github.com/new
2. Назва: `universal-bot-os` (або будь-яка інша)
3. Натисни "Create repository"

### 2. Завантаж код в GitHub

```bash
cd universal-bot-os

# Додай remote (заміни <username> та <repo-name>)
git remote add origin https://github.com/<username>/<repo-name>.git

# Або з токеном (якщо потрібно):
git remote add origin https://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@github.com/<username>/<repo-name>.git

# Завантаж код
git branch -M main
git push -u origin main
```

### 3. Підключи GitHub до Railway

**Через Railway UI:**

1. Відкрий проект: https://railway.app/project/46aa6dc7-1bb1-49b7-ac65-e9a8ac73636a
2. Сервіс `api` → Settings → Source
3. Натисни "Connect GitHub"
4. Дозволь доступ до репозиторію
5. Виберіть репозиторій `universal-bot-os`
6. Виберіть branch `main`
7. Railway автоматично почне деплой

**Альтернатива - через Railway CLI:**

```bash
cd universal-bot-os
railway login
railway link  # вибери проект universal-bot-os
railway up
```

---

## ✅ Після деплою:

1. **Перевір логи:**
   - Railway UI → Logs
   - Має бути: "✅ Database tables created/verified"

2. **Перевір health check:**
   ```bash
   curl https://your-app.railway.app/health
   ```

3. **Перевір Admin UI:**
   - Відкрий: `https://your-app.railway.app/admin`

---

**Готово!** 🎉

