# 🚀 QUICKSTART для нового AI чату

## 📖 Що це?

**Universal Bot OS** - multi-tenant платформа для управління Telegram ботами.  
Зараз працюємо з системою управління **партнерами** (partner bots).

---

## ⚡ Швидкий старт (скопіюй це в новий чат)

```
Привіт! Продовжуємо роботу з Universal Bot OS.

Прочитай контекст:
@universal-bot-os/PARTNER_MANAGEMENT_GUIDE.md
@universal-bot-os/TODO_PARTNER_SYSTEM.md
@universal-bot-os/AGENT_ONBOARDING.md

Основна інфа:
- Bot ID: 4f3c45a5-39ac-4d6e-a0eb-263765d70b1a (@EarnAggregatorBot)
- Admin UI: https://api-production-57e8.up.railway.app/admin
- API: https://api-production-57e8.up.railway.app/api/v1/admin

Вже є:
✅ Soft delete партнерів (можна відновити видалених)
✅ Admin UI з повним редагуванням + реф лінки
✅ Партнери: RandGiftBot (NEW), EasyGiftDropbot (TOP), TheStarsBank (TOP)
✅ Історія видалень + кнопка Restore

Поточне завдання:
[Опиши що треба зробити]
```

---

## 🔑 Ключова інформація

### **Bot ID (завжди використовуй цей):**
```
4f3c45a5-39ac-4d6e-a0eb-263765d70b1a
```

### **URLs:**
- **Admin UI:** https://api-production-57e8.up.railway.app/admin
- **API Base:** https://api-production-57e8.up.railway.app/api/v1/admin
- **Health:** https://api-production-57e8.up.railway.app/health

### **Поточні партнери (активні):**
1. **RandGiftBot** - NEW, Active → показується в `/partners`
2. **EasyGiftDropbot** - TOP, Active → показується в `/top`
3. **TheStarsBank** - TOP, Active → показується в `/top`

---

## 📁 Важливі файли

### **Документація:**
- `PARTNER_MANAGEMENT_GUIDE.md` - повний гайд
- `TODO_PARTNER_SYSTEM.md` - що зроблено + майбутні плани
- `AGENT_ONBOARDING.md` - загальний онбординг

### **Код (якщо треба змінювати):**
- `app/api/v1/admin.py` - Admin API endpoints
- `app/static/admin.html` - Admin UI
- `app/services/partner_service.py` - Partner logic
- `app/models/business_data.py` - BusinessData model (з deleted_at)

---

## 🛠️ Корисні команди

### **Тест команди в боті:**
```bash
curl -k -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/test-command?command=/partners&user_lang=uk"
```

### **Список партнерів:**
```bash
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/partners"
```

### **Історія видалених:**
```bash
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/partners/deleted"
```

---

## 🎯 Типові завдання

### 1. **Додати нового партнера:**
→ Використати Admin UI (Partners tab → Add Partner) або POST `/partners` endpoint

### 2. **Змінити статус партнера (active/category):**
→ Admin UI: Partners → Edit → змінити поля → Save

### 3. **Відновити видаленого партнера:**
→ Admin UI: Partners → Show Deleted Partners → Restore

### 4. **Видалити дублікати:**
```bash
# Dry run спочатку
curl -k -X POST "...remove-duplicate-partners?dry_run=true"
```

### 5. **Імпорт правильних партнерів:**
```bash
curl -k -X POST "...import-correct-partners"
```

---

## 🔍 Як перевірити що все працює

### **1. API Health:**
```bash
curl -k "https://api-production-57e8.up.railway.app/health"
# Має повернути: {"status": "healthy"}
```

### **2. Список партнерів:**
```bash
curl -k "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/partners"
# Має показати RandGiftBot, EasyGiftDropbot, TheStarsBank
```

### **3. Команда `/partners` в боті:**
```bash
curl -k -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/test-command?command=/partners&user_lang=uk"
# Має показати RandGiftBot
```

### **4. Admin UI:**
- Відкрити: https://api-production-57e8.up.railway.app/admin
- Перейти на Partners tab
- Вибрати EarnHubAggregatorBot
- Має показати 3 партнери + реф лінки

---

## ⚠️ Якщо щось не працює

### **"Internal server error" в API:**
→ Можливо треба застосувати міграцію:
```bash
curl -k -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/run-migration-add-deleted-at"
```

### **Партнери не показуються в `/partners` або `/top`:**
→ Перевір через Admin UI:
- `active = 'Yes'` ✅
- `category` правильна (NEW або TOP)
- НЕ видалений (deleted_at = null)

### **Дублікати партнерів:**
→ Видали дублікати через API:
```bash
curl -k -X POST "...remove-duplicate-partners?dry_run=false"
```

---

## 📞 Deployment

**Railway (автодеплой з GitHub):**
- Push в `main` branch → автоматичний deploy
- URL: https://api-production-57e8.up.railway.app
- GitHub: MarkSharkM/universal-bot-os

**Як задеплоїти зміни:**
```bash
cd universal-bot-os
git add .
git commit -m "Your message"
git push
# Чекай 45-60 секунд для deployment
```

---

## ✅ Checklist для нового AI

Перед початком роботи, переконайся що розумієш:

- [ ] Bot ID: `4f3c45a5-39ac-4d6e-a0eb-263765d70b1a`
- [ ] Admin UI: https://api-production-57e8.up.railway.app/admin
- [ ] Партнери: RandGiftBot (NEW), EasyGiftDropbot (TOP), TheStarsBank (TOP)
- [ ] Soft delete: партнери НЕ видаляються назавжди, можна відновити
- [ ] Документація: `PARTNER_MANAGEMENT_GUIDE.md` - повний гайд

**Якщо все зрозуміло → можна починати працювати! 🚀**

---

**Дата створення:** 29 січня 2025  
**Версія:** 1.0

