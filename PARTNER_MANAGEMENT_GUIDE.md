# 📋 Partner Management Guide - Universal Bot OS

## 🎯 Огляд

Система управління партнерами з **soft delete**, **історією видалень**, **відновленням** та **повним редагуванням** через Admin UI.

---

## ✅ Що вже зроблено

### 1. **Soft Delete для партнерів** ✅
- Додано поле `deleted_at` в таблицю `business_data`
- Партнери НЕ видаляються назавжди, тільки помічаються як видалені
- Можна відновити будь-якого видаленого партнера

**Файли:**
- `app/models/business_data.py` - додано `deleted_at` поле
- `app/services/partner_service.py` - фільтрація `deleted_at.is_(None)`
- `alembic/versions/add_soft_delete_to_business_data.py` - міграція

### 2. **Admin UI покращення** ✅
- Таблиця партнерів показує **реф лінки** (скорочені з tooltip)
- Кнопка **"Edit"** - редагування всіх полів:
  - Bot Name
  - Descriptions (UK, EN, RU, DE, ES)
  - Referral Link
  - Commission (%)
  - Category (NEW/TOP)
  - Active (Yes/No)
  - Verified (Yes/No)
  - ROI Score
- Кнопка **"Delete"** - soft delete (можна відновити)
- Кнопка **"🗑️ Show Deleted Partners"** - історія видалень
- Модальне вікно з видаленими партнерами та кнопкою **"♻️ Restore"**

**Файл:**
- `app/static/admin.html` - оновлено UI та JS функції

### 3. **API Endpoints** ✅

#### **Partners CRUD:**
- `GET /api/v1/admin/bots/{bot_id}/partners` - список активних партнерів
- `POST /api/v1/admin/bots/{bot_id}/partners` - створити партнера
- `PATCH /api/v1/admin/bots/{bot_id}/partners/{partner_id}` - оновити партнера
- `DELETE /api/v1/admin/bots/{bot_id}/partners/{partner_id}?hard_delete=false` - soft delete (default) або hard delete

#### **Soft Delete Management:**
- `GET /api/v1/admin/bots/{bot_id}/partners/deleted` - список видалених партнерів (історія)
- `POST /api/v1/admin/bots/{bot_id}/partners/{partner_id}/restore` - відновити видаленого партнера

#### **Utilities:**
- `POST /api/v1/admin/bots/{bot_id}/import-correct-partners` - імпорт правильних партнерів (EasyGiftDropbot, RandGiftBot, TheStarsBank)
- `POST /api/v1/admin/bots/{bot_id}/remove-duplicate-partners?dry_run=true` - знайти/видалити дублікати
- `POST /api/v1/admin/run-migration-add-deleted-at` - застосувати міграцію для `deleted_at`

**Файл:**
- `app/api/v1/admin.py` - всі endpoints

### 4. **Правильні партнери імпортовані** ✅

**3 партнери з правильними налаштуваннями:**

| Bot Name | Category | Active | Ref Link | Description |
|----------|----------|--------|----------|-------------|
| **RandGiftBot** | NEW | ✅ Yes | `https://t.me/randgift_bot?start=_tgr_dkf6mDQ3Y2M6` | 🎁 Випадкові подарунки |
| **EasyGiftDropbot** | TOP | ✅ Yes | `https://t.me/EasyGiftDropbot?start=_tgr_WhrUYB40ZWFi` | 🎁 Подарунки за активність |
| **TheStarsBank** | TOP | ✅ Yes | `https://t.me/m5bank_bot?start=_tgr_JUV1QD8zMDUy` | 🏦 Заробіток на транзакціях |

**Логіка показу:**
- **`/partners`** → показує партнерів з `category != 'TOP'` AND `active = 'Yes'` (RandGiftBot)
- **`/top`** → показує партнерів з `category = 'TOP'` AND `active = 'Yes'` (EasyGiftDropbot, TheStarsBank)

**Файл:**
- `scripts/partners_data.py` - дані партнерів для імпорту

---

## 🚀 Як використовувати Admin UI

### 1. **Відкрити Admin Panel:**
```
https://api-production-57e8.up.railway.app/admin
```

### 2. **Перейти на вкладку "Partners"**

### 3. **Вибрати бота** (EarnHubAggregatorBot)

### 4. **Операції з партнерами:**

#### **Редагувати партнера:**
1. Натиснути **"Edit"** на потрібному партнері
2. Змінити потрібні поля (category, active, descriptions, реф лінка)
3. Натиснути **"Save Changes"**

#### **Видалити партнера (soft delete):**
1. Натиснути **"Delete"**
2. Підтвердити (партнер не видалиться назавжди)
3. Партнер зникне з таблиці, але залишиться в історії

#### **Переглянути історію видалених:**
1. Натиснути **"🗑️ Show Deleted Partners"**
2. Побачити всіх видалених партнерів з датою видалення

#### **Відновити видаленого партнера:**
1. У модальному вікні з видаленими натиснути **"♻️ Restore"**
2. Підтвердити
3. Партнер з'явиться знову в основній таблиці

---

## 🔧 API Приклади (curl)

### **Список партнерів:**
```bash
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/partners"
```

### **Редагувати партнера (наприклад, активувати TheStarsBank):**
```bash
curl -k -X PATCH "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/partners/{partner_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "active": "Yes",
    "category": "TOP"
  }'
```

### **Soft delete партнера:**
```bash
curl -k -X DELETE "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/partners/{partner_id}?hard_delete=false"
```

### **Список видалених партнерів:**
```bash
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/partners/deleted"
```

### **Відновити партнера:**
```bash
curl -k -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/partners/{partner_id}/restore"
```

### **Імпорт правильних партнерів:**
```bash
curl -k -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/import-correct-partners"
```

### **Видалити дублікати (dry run спочатку):**
```bash
# Dry run (подивитись що буде видалено)
curl -k -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/remove-duplicate-partners?dry_run=true"

# Реальне видалення
curl -k -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/remove-duplicate-partners?dry_run=false"
```

---

## 🔑 Важливі ID

### **Bot ID:**
```
4f3c45a5-39ac-4d6e-a0eb-263765d70b1a
```
(EarnHubAggregatorBot / @EarnAggregatorBot)

### **Partner IDs (після імпорту):**
Отримати через:
```bash
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/partners"
```

---

## 📁 Структура файлів

```
universal-bot-os/
├── app/
│   ├── api/v1/
│   │   └── admin.py                 # ✅ Admin API endpoints (CRUD, soft delete, restore)
│   ├── models/
│   │   └── business_data.py         # ✅ BusinessData model (додано deleted_at)
│   ├── services/
│   │   └── partner_service.py       # ✅ Partner service (фільтрація deleted_at)
│   └── static/
│       └── admin.html               # ✅ Admin UI (редагування, історія, restore)
├── alembic/versions/
│   └── add_soft_delete_to_business_data.py  # ✅ Міграція для deleted_at
└── scripts/
    ├── partners_data.py             # ✅ Правильні дані партнерів
    ├── remove_duplicate_partners.py # Скрипт видалення дублікатів
    └── add_deleted_at.sql           # SQL міграція
```

---

## 🐛 Troubleshooting

### **Проблема: API повертає "Internal server error"**
**Рішення:** Застосувати міграцію для `deleted_at`:
```bash
curl -k -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/run-migration-add-deleted-at"
```

### **Проблема: Партнери не показуються в `/partners` або `/top`**
**Перевірити:**
1. `active = 'Yes'`
2. `category` правильна (NEW для `/partners`, TOP для `/top`)
3. `deleted_at IS NULL`

**Виправити через Admin UI або API**

### **Проблема: Дублікати партнерів**
**Рішення:**
```bash
# 1. Подивитись що буде видалено
curl -k -X POST "...remove-duplicate-partners?dry_run=true"

# 2. Видалити дублікати
curl -k -X POST "...remove-duplicate-partners?dry_run=false"
```

---

## 🎯 TODO для нового чату

### **Швидкий старт (що сказати AI):**

```
Привіт! Працюємо з Universal Bot OS.

Контекст:
- Проект: @universal-bot-os/PARTNER_MANAGEMENT_GUIDE.md
- Bot ID: 4f3c45a5-39ac-4d6e-a0eb-263765d70b1a
- Admin UI: https://api-production-57e8.up.railway.app/admin
- API Base: https://api-production-57e8.up.railway.app/api/v1/admin

Вже є:
✅ Soft delete для партнерів (deleted_at)
✅ Admin UI з редагуванням, історією видалень, restore
✅ Партнери: RandGiftBot (NEW), EasyGiftDropbot (TOP), TheStarsBank (TOP)

Треба зробити:
[Опишіть що треба]
```

### **Приклади завдань:**

1. **Додати нового партнера:**
```
Додай нового партнера через Admin UI або API:
- Bot Name: NewBot
- Category: NEW
- Active: Yes
- Ref Link: https://t.me/newbot?start=...
```

2. **Змінити category партнера:**
```
Зміни RandGiftBot з NEW → TOP через Admin UI
```

3. **Відновити видаленого:**
```
Віднови TheStarsBank з історії видалень
```

---

## 📞 Корисні посилання

- **Admin UI:** https://api-production-57e8.up.railway.app/admin
- **Health Check:** https://api-production-57e8.up.railway.app/health
- **API Docs:** (FastAPI auto-docs) `/docs` або `/redoc`
- **GitHub:** MarkSharkM/universal-bot-os
- **Railway:** https://railway.app

---

## 🧪 Тестування

### **Тест команди `/partners` (має показати RandGiftBot):**
```bash
curl -k -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/test-command?command=/partners&user_lang=uk"
```

### **Тест команди `/top` (має показати EasyGiftDropbot + TheStarsBank або locked якщо немає рефералів):**
```bash
curl -k -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/test-command?command=/top&user_lang=uk"
```

---

**Готово! 🚀 Тепер можна легко продовжити роботу в новому чаті.**

