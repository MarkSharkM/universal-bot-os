# 📊 Аналіз n8n Workflow - HubAggregator Bot

**Дата аналізу:** 2024-12-28  
**Workflow:** PROD hub+mcp  
**Всього нод:** 52  
**Критичні Code ноди:** 10 (Translator найбільша ~33K, Format_TopBots_Message ~10K)

---

## 🎯 Основна бізнес-логіка

### 1. Вхідний роутинг (Trigger → Switch)

```
Trigger (Telegram webhook)
  ↓
Switch (розділяє по типу події):
  ├─ Message (звичайні повідомлення)
  ├─ Callback (callback_query)
  ├─ System (my_chat_member)
  └─ Payment (pre_checkout_query / successful_payment)
```

**Бізнес-логіка:**
- Визначає тип події з Telegram update
- Роутить до відповідних обробників

---

### 2. Команди бота (Switch_Commands)

**Підтримувані команди:**
- `/wallet` - керування TON гаманцем
- `/top` - TOP партнери (потрібен unlock)
- `/partners` - список всіх партнерів
- `/share` - реферальне посилання
- `/earnings` - центр заробітку
- `/info` - інформація про бота
- `/start` - привітання

**Бізнес-логіка:**
- Перевірка чи це команда (починається з `/`)
- Regex matching для команд
- Роутинг до відповідних обробників

---

### 3. Ключові функції

#### 3.1. Wallet Management (`/wallet`)

**Потік:**
```
/wallet command
  ↓
read_user_wallet (Google Sheets)
  ↓
Switch_wallet_check (є гаманець?)
  ├─ Так → format_wallet_info → wallet_info (Telegram)
  └─ Ні → wallet_not_found → wallet_not_found1 (Telegram)
```

**Валідація гаманця:**
- Regex: `/^(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_-]{46,48}$/`
- Якщо валідний → збереження в Google Sheets
- Якщо невалідний → повідомлення про помилку

**Бізнес-логіка:**
- Збереження TON wallet address
- Відображення заробітку (Total Earned TON)
- Мультимовні повідомлення

---

#### 3.2. TOP Partners (`/top`)

**Потік:**
```
/top command
  ↓
read_user_wallet_for_top (Google Sheets)
  ↓
/top (Google Sheets - Partners_Settings, Category=TOP, Active=Yes, Verified=Yes)
  ↓
Format_TopBots_Message (Code node ~10K)
  ↓
IF — TOP Locked?
  ├─ locked → top locked (Telegram з кнопкою unlock)
  └─ open → top (Telegram зі списком)
```

**Умови доступу:**
- `TOP Status = "open"` в user_wallets АБО
- `Total Invited >= 5` АБО
- Оплата через `buy_top` (1⭐)

**Бізнес-логіка:**
- Фільтрація TOP ботів (Category=TOP, Active=Yes, Verified=Yes)
- Сортування по ROI Score (descending)
- Персоналізація реферальних лінків (`_tgr_{userId}`)
- Мультимовні описи (Description_{lang})
- Ліміт повідомлення (3900 символів)

---

#### 3.3. Partners List (`/partners`)

**Потік:**
```
/partners command
  ↓
/partners (Google Sheets - Partners_Settings, Active=Yes, Verified=Yes)
  ↓
format_partners_list (Code node)
  ↓
partners (Telegram)
```

**Бізнес-логіка:**
- Фільтрація партнерів (Active=Yes, Verified=Yes, не TOP)
- Мультимовні описи
- Список з нумерацією

---

#### 3.4. Earnings Center (`/earnings`)

**Потік:**
```
/earnings command (або callback)
  ↓
Extract_Share_Referral_Info
  ↓
Read_Wallets_Sheet (Google Sheets)
  ↓
Build_Earnings_Message (Code node)
  ↓
Send_Earnings_Message (Telegram)
```

**Бізнес-логіка:**
- Відображення прогрес-бару інвайтів (0-5)
- Статус TOP (locked/open)
- Інформація про 7% партнерську програму Telegram
- Реферальне посилання
- Мультимовні повідомлення

---

#### 3.5. Referral System (`/share`)

**Потік:**
```
/share command
  ↓
Extract_User_Info
  ↓
Check_If_User_Exists (Google Sheets)
  ↓
Filter_User_By_ID
  ├─ Новий → Upsert_TOP_user1 → Send_Referral
  └─ Існуючий → Send_Referral
```

**Бізнес-логіка:**
- Генерація реферального тегу: `_tgr_{userId}`
- Створення реферального лінка: `https://t.me/HubAggregatorBot?start=_tgr_{userId}`
- Перевірка чи користувач існує
- Автоматичне створення запису в user_wallets

---

#### 3.6. Referral Tracking

**Потік:**
```
Trigger (будь-яка подія)
  ↓
Extract message data
  ↓
Translator
  ↓
Format_Log_Entry
  ↓
Check: Is Referral
  ├─ Так → Log to bot_log → IF (isReferral = true) → Get bot_log → Count Referrals → Update Total Invited
  └─ Ні → Log to bot_log → Switch
```

**Бізнес-логіка:**
- Визначення реферального трафіку: `_tgr_{userId}` або `tgr_{userId}`
- Логування всіх подій в bot_log
- Підрахунок унікальних рефералів
- Оновлення Total Invited в user_wallets

**Валідація реферала:**
- Regex: `/^_?tgr_[a-z0-9-]+$/i`
- Виключення резервованих команд
- Спецвипадок: `_tgr_gptstore` → не вважається рефералом

---

#### 3.7. TOP Unlock (Payment)

**Потік:**
```
buy_top callback
  ↓
buy_top (HTTP Request - sendInvoice)
  ↓
Switch_PaymentType
  ├─ pre_checkout → answer_pre_checkout → Upsert_TOP_user (TOP Status = "open")
  └─ successful_payment → Upsert_TOP_user → send_top_unlocked
```

**Бізнес-логіка:**
- Створення invoice через Telegram Bot API
- Ціна: 1⭐ (з Translator.buy_top_price)
- Після оплати → TOP Status = "open" в user_wallets
- Підтвердження unlock

---

#### 3.8. Translator (i18n)

**Нода:** Translator (Code node ~33K рядків, винесена в CSV)

**Підтримувані мови:**
- uk, en, ru, de, es

**Бізнес-логіка:**
- Детекція мови з `Trigger.from.language_code`
- Нормалізація до 2-літерного коду
- Завантаження перекладів з CSV
- Підстановка плейсхолдерів (`{{variable}}`)
- Fallback на en → uk

**Ключові переклади:**
- welcome, info_main, wallet_*, earnings_*, partners_*, share_*, buy_top_*

---

## 🗄️ Google Sheets залежності

### Таблиця 1: `user_wallets`
**Використання:**
- Читання: `/wallet`, `/top`, `/earnings`, `/share`
- Запис: створення/оновлення користувача, wallet address, TOP Status, Total Invited

**Ключові поля:**
- User Chat ID (primary key)
- Wallet Address
- Total Earned TON
- Total Invited
- TOP Status (locked/open)
- Language

---

### Таблиця 2: `bot_log`
**Використання:**
- Запис: логування всіх подій
- Читання: підрахунок рефералів (Count Referrals)

**Ключові поля:**
- User Chat ID
- Message Text
- Ref Parameter
- Click Type (Organic/Referral)
- Referred By

---

### Таблиця 3: `Partners_Settings`
**Використання:**
- Читання: `/top`, `/partners`

**Ключові поля:**
- Bot Name
- Description_{lang} (uk/en/ru/de/es)
- Referral Link
- Commission (%)
- Category (TOP/NEW)
- Active (Yes/No)
- Verified (Yes/No)
- ROI Score

---

## 🔍 Виявлені проблеми та оптимізації

### 1. Зайві кроки
- **Множинні Switch ноди** - можна об'єднати в один router
- **Дублювання логіки** - Extract_User_Info та Extract_Share_Referral_Info майже ідентичні
- **Google Sheets запити** - багато окремих запитів, можна батчити

### 2. Google Sheets обмеження
- **Read-only поля** - API не працює для редагування (згадано в пам'яті)
- **Повільність** - кожен запит = HTTP request
- **Немає транзакцій** - ризик race conditions

### 3. Код ноди проблеми
- **Translator (33K)** - дуже велика, краще винести в окремий сервіс
- **Format_TopBots_Message (10K)** - складна логіка, треба розбити
- **Build_Earnings_Message** - багато шаблонів, краще винести в templates

### 4. Мультимовність
- **Hardcoded в Code нодах** - краще використовувати translations таблицю
- **CSV файл** - вже винесено, треба імпортувати в БД

---

## 📋 План міграції

### Етап 1: Заміна Google Sheets
1. Створити SQL моделі для:
   - `user_wallets` → `users` + `business_data` (data_type='wallet')
   - `bot_log` → `messages` + `business_data` (data_type='log')
   - `Partners_Settings` → `business_data` (data_type='partner')

2. Міграція даних:
   - Скрипт для експорту з Google Sheets
   - Імпорт в PostgreSQL

### Етап 2: Рефакторинг логіки
1. **Translator** → `app/services/translation_service.py`
2. **Format_TopBots_Message** → `app/services/partner_service.py`
3. **Build_Earnings_Message** → `app/services/earnings_service.py`
4. **Referral tracking** → `app/services/referral_service.py`

### Етап 3: API Endpoints
1. Telegram webhook → `app/api/v1/webhooks.py`
2. Command handlers → `app/services/command_service.py`
3. Callback handlers → `app/services/callback_service.py`

---

## 🎯 Наступні кроки

1. ✅ Аналіз завершено
2. ⏳ Створити детальну схему міграції
3. ⏳ Реалізувати сервіси
4. ⏳ Створити API endpoints

---

**Статус:** Аналіз завершено, готовий до реалізації 🚀

