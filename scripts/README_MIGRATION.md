# 📥 Migration Scripts - Google Sheets to PostgreSQL

**Скрипти для міграції даних з Google Sheets (CSV/JSON) до PostgreSQL**

---

## 🎯 Підхід

Оскільки трафіку мало, міграція виконується через файли:
1. Експортуй дані з Google Sheets в CSV
2. Запусти скрипти для імпорту
3. Після міграції - керування через адмінку (Фаза 6)

---

## 📋 Доступні скрипти

### 1. `migrate_from_sheets.py` - Повна міграція

**Використання:**
```bash
python scripts/migrate_from_sheets.py \
  --bot-id <BOT_UUID> \
  --user-wallets path/to/user_wallets.csv \
  --bot-log path/to/bot_log.csv \
  --partners path/to/Partners_Settings.csv
```

**Що мігрує:**
- `user_wallets` → `User` + `BusinessData` (data_type='wallet')
- `bot_log` → `BusinessData` (data_type='log')
- `Partners_Settings` → `BusinessData` (data_type='partner')

---

### 2. `import_partners_from_csv.py` - Швидкий імпорт партнерів

**Використання:**
```bash
python scripts/import_partners_from_csv.py \
  --bot-id <BOT_UUID> \
  --csv path/to/Partners_Settings.csv \
  --update  # Якщо треба оновити існуючі
```

**Призначення:**
- Швидкий імпорт/оновлення партнерів
- Можна використовувати для оновлення списку партнерів

---

### 3. `import_translations.py` - Імпорт перекладів

**Використання:**
```bash
python scripts/import_translations.py
```

**Призначення:**
- Імпортує переклади з `translations_for prod tg.csv`
- Створює записи в таблиці `translations`

---

## 📊 Формат CSV файлів

### user_wallets.csv
**Колонки:**
- User Chat ID (обов'язково)
- Username
- Wallet Address
- Total Earned TON
- Total Invited
- TOP Status (locked/open)
- Language
- Status (active/ban)
- Referred By
- ... (інші поля зберігаються в metadata)

### bot_log.csv
**Колонки:**
- User Chat ID (обов'язково)
- Timestamp
- Message Text
- Ref Parameter
- Click Type (Organic/Referral)
- Referred By
- Earned TON
- ... (інші поля зберігаються в data JSONB)

### Partners_Settings.csv
**Колонки:**
- Bot Name (обов'язково)
- Description
- Description_en, Description_ru, Description_de, Description_es
- Referral Link
- Commission (%)
- Category (TOP/NEW)
- Active (Yes/No)
- Verified (Yes/No)
- ROI Score
- ... (інші поля зберігаються в data JSONB)

---

## 🔄 Workflow міграції

### Крок 1: Експорт з Google Sheets
1. Відкрий Google Sheets
2. File → Download → CSV
3. Збережи файли в `scripts/data/` або будь-де

### Крок 2: Створи бота (якщо ще немає)
```python
from app.core.database import SessionLocal
from app.models.bot import Bot

db = SessionLocal()
bot = Bot(
    name="HubAggregator Bot",
    platform_type="telegram",
    token="YOUR_BOT_TOKEN",
    default_lang="uk"
)
db.add(bot)
db.commit()
bot_id = bot.id
```

### Крок 3: Запусти міграцію
```bash
# Повна міграція
python scripts/migrate_from_sheets.py \
  --bot-id <BOT_UUID> \
  --user-wallets scripts/data/user_wallets.csv \
  --bot-log scripts/data/bot_log.csv \
  --partners scripts/data/Partners_Settings.csv

# Тільки партнери
python scripts/import_partners_from_csv.py \
  --bot-id <BOT_UUID> \
  --csv scripts/data/Partners_Settings.csv
```

### Крок 4: Перевірка
```python
from app.core.database import SessionLocal
from app.models import User, BusinessData

db = SessionLocal()
users_count = db.query(User).filter(User.bot_id == bot_id).count()
partners_count = db.query(BusinessData).filter(
    BusinessData.bot_id == bot_id,
    BusinessData.data_type == 'partner'
).count()

print(f"Users: {users_count}, Partners: {partners_count}")
```

---

## ⚠️ Важливо

1. **Backup:** Зроби backup БД перед міграцією
2. **Bot ID:** Потрібен валідний `bot_id` (UUID)
3. **Duplicates:** Скрипти перевіряють на дублікати
4. **Partners:** Після міграції партнери можна керувати через адмінку (Фаза 6)

---

## 🎯 Після міграції

**Partners_Settings:**
- Зараз: імпорт через CSV
- Після Фази 6: керування через адмінку (CRUD через веб-інтерфейс)

**user_wallets та bot_log:**
- Автоматично оновлюються через API
- Міграція потрібна тільки для історичних даних

---

**Готово до використання!** 🚀

