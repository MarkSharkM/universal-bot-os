# ⚡ Швидкий імпорт даних

## 🚀 Одна команда для всього

```bash
railway run python scripts/import_all_data.py --bot-name EarnHubAggregatorBot
```

**Це імпортує:**
- ✅ Переклади (uk, en, ru, de, es)
- ✅ Користувачі з гаманцями
- ✅ Партнери (TOP та NEW)
- ✅ Логи бота

---

## 📋 Перед запуском

1. **Переконайся, що бот створений:**
   - Відкрий `https://api-production-57e8.up.railway.app/admin`
   - Перевір, чи є бот `EarnHubAggregatorBot`

2. **Переконайся, що Railway CLI підключений:**
   ```bash
   railway link
   ```

3. **Файли вже в репозиторії:**
   - ✅ `old-prod-hub-bot/translations_for prod tg.csv`
   - ✅ `old-prod-hub-bot/Earnbot_Referrals - user_wallets.csv`
   - ✅ `old-prod-hub-bot/Earnbot_Referrals - Partners_Settings.csv`
   - ✅ `old-prod-hub-bot/Earnbot_Referrals - bot_log.csv`

---

## ▶️ Запуск

```bash
cd universal-bot-os
railway run python scripts/import_all_data.py --bot-name EarnHubAggregatorBot
```

**Очікуваний вивід:**
```
🤖 Importing data for bot: EarnHubAggregatorBot (xxx-xxx-xxx)
============================================================

📥 [1/4] Importing translations from translations_for prod tg.csv...
✅ Translations imported successfully

📥 [2/4] Importing users from Earnbot_Referrals - user_wallets.csv...
✅ Imported 5 users

📥 [3/4] Importing partners from Earnbot_Referrals - Partners_Settings.csv...
✅ Imported 7 partners

📥 [4/4] Importing logs from Earnbot_Referrals - bot_log.csv...
✅ Imported 340 log entries

============================================================
🎉 Import completed! Total records: 352
```

---

## ✅ Перевірка

**1. Через Admin UI:**
- Відкрий `/admin` → вкладка "Stats"
- Вибери бота
- Має показати: 5 користувачів, 7 партнерів

**2. Через Telegram:**
- Надішли `/start` - має показати привітання
- Надішли `/partners` - мають з'явитися партнери
- Надішли `/top` - мають з'явитися TOP партнери

---

## 🐛 Якщо щось не так

**Помилка: "Bot not found"**
```bash
# Перевір список ботів
railway run python -c "
from app.core.database import SessionLocal
from app.models.bot import Bot
db = SessionLocal()
bots = db.query(Bot).all()
for b in bots:
    print(f'{b.name}: {b.id}')
db.close()
"
```

**Помилка: "File not found"**
- Перевір, чи файли в `old-prod-hub-bot/`
- Використай абсолютні шляхи: `--translations /full/path/to/file.csv`

---

**Детальніше:** `IMPORT_DATA.md`

