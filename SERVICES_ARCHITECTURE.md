# 🏗️ Services Architecture - Universal Bot OS

**Multi-tenant сервісний шар для 100+ ботів**

---

## 📦 Створені сервіси (6)

### 1. `TranslationService` - i18n підтримка
**Файл:** `app/services/translation_service.py`

**Функціонал:**
- Детекція мови з Telegram `language_code`
- Нормалізація мовних кодів (uk, en, ru, de, es)
- Отримання перекладів з БД з fallback логікою
- Підстановка змінних (`{{variable}}` та `[[variable]]`)
- Bulk завантаження перекладів

**Multi-tenant:** ✅ Працює з глобальними перекладами (не залежить від bot_id)

**Замінює:** Translator Code node (33K рядків)

---

### 2. `UserService` - Керування користувачами
**Файл:** `app/services/user_service.py`

**Функціонал:**
- `get_or_create_user()` - створення/отримання користувача
- `update_wallet()` - збереження TON wallet address
- `get_wallet()` - отримання wallet з business_data
- `update_top_status()` - оновлення TOP доступу
- `update_balance()` - оновлення балансу користувача

**Multi-tenant:** ✅ Всі операції scoped по `bot_id`

**Замінює:** 
- Google Sheets `user_wallets` таблиця
- `read_user_wallet`, `read_user_wallet_for_top` ноди
- `create_wallet_entry`, `Upsert_TOP_user` ноди

---

### 3. `ReferralService` - Реферальна система
**Файл:** `app/services/referral_service.py`

**Функціонал:**
- `generate_referral_tag()` - генерація `_tgr_{userId}`
- `generate_referral_link()` - створення реферального URL
- `parse_referral_parameter()` - валідація реферального параметра
- `log_referral_event()` - логування подій (замість bot_log)
- `count_referrals()` - підрахунок унікальних рефералів
- `update_total_invited()` - оновлення лічильника інвайтів
- `check_top_unlock_eligibility()` - перевірка умов unlock TOP

**Multi-tenant:** ✅ Всі операції scoped по `bot_id`

**Замінює:**
- Google Sheets `bot_log` таблиця
- `Check: Is Referral` Code node
- `Count Referrals` Code node
- `Update Total Invited` Google Sheets node

---

### 4. `PartnerService` - Каталог партнерів
**Файл:** `app/services/partner_service.py`

**Функціонал:**
- `get_top_partners()` - отримання TOP партнерів (з сортуванням по ROI)
- `get_partners()` - отримання звичайних партнерів
- `_get_localized_description()` - мультимовні описи
- `personalize_referral_link()` - персоналізація лінків з `_tgr_{userId}`
- `format_top_message()` - форматування повідомлення з TOP списком
- `create_partner()` - створення партнера (для адмінки)

**Multi-tenant:** ✅ Всі операції scoped по `bot_id`

**Замінює:**
- Google Sheets `Partners_Settings` таблиця
- `/top` Google Sheets node
- `/partners` Google Sheets node
- `Format_TopBots_Message` Code node (~10K рядків)
- `format_partners_list` Code node

---

### 5. `EarningsService` - Earnings Center
**Файл:** `app/services/earnings_service.py`

**Функціонал:**
- `build_earnings_message()` - побудова повного earnings повідомлення
- `_build_top_block()` - блок з прогрес-баром інвайтів
- `_build_7percent_block()` - інформація про 7% програму Telegram
- `_build_action_block()` - блок "Що зробити зараз"

**Multi-tenant:** ✅ Всі операції scoped по `bot_id`

**Замінює:**
- `Build_Earnings_Message` Code node
- `Read_Wallets_Sheet` Google Sheets node

---

### 6. `CommandService` - Роутинг команд
**Файл:** `app/services/command_service.py`

**Функціонал:**
- `parse_command()` - парсинг команди з тексту
- `extract_start_parameter()` - витяг параметра з `/start`
- `handle_command()` - роутинг до обробників
- `_handle_wallet()` - обробка `/wallet`
- `_handle_top()` - обробка `/top`
- `_handle_partners()` - обробка `/partners`
- `_handle_share()` - обробка `/share`
- `_handle_earnings()` - обробка `/earnings`
- `_handle_info()` - обробка `/info`
- `_handle_start()` - обробка `/start` (з реферальним трекінгом)

**Multi-tenant:** ✅ Всі операції scoped по `bot_id`

**Замінює:**
- `Switch_Commands` Switch node
- `Command?` IF node
- Всі окремі обробники команд

---

## 🔑 Ключові принципи

### 1. Multi-Tenancy
**Кожен сервіс приймає `bot_id` в конструкторі:**
```python
user_service = UserService(db, bot_id=bot_id)
```

**Всі запити автоматично фільтруються:**
```python
User.bot_id == self.bot_id
```

### 2. Service Layer Independence
- Сервіси не знають про платформу (Telegram/Web/WhatsApp)
- Всі операції через чистий Python
- Немає залежності від n8n або Google Sheets

### 3. AI-Friendly
- Чіткі назви методів
- Type hints скрізь
- Документація в docstrings
- Модульна структура

### 4. Заміна Google Sheets
- `user_wallets` → `User` + `BusinessData` (data_type='wallet')
- `bot_log` → `BusinessData` (data_type='log')
- `Partners_Settings` → `BusinessData` (data_type='partner')

---

## 📊 Порівняння з n8n

| n8n Workflow | Python Service | Статус |
|--------------|----------------|--------|
| Translator (33K) | `TranslationService` | ✅ |
| Format_TopBots_Message (10K) | `PartnerService.format_top_message()` | ✅ |
| Build_Earnings_Message | `EarningsService.build_earnings_message()` | ✅ |
| Check: Is Referral | `ReferralService.parse_referral_parameter()` | ✅ |
| Count Referrals | `ReferralService.count_referrals()` | ✅ |
| Switch_Commands | `CommandService.handle_command()` | ✅ |
| Google Sheets queries | SQL через SQLAlchemy | ✅ |

---

## 🚀 Використання

### Приклад: Обробка команди `/wallet`

```python
from app.services import (
    UserService, TranslationService, CommandService,
    PartnerService, ReferralService, EarningsService
)
from app.core.database import get_db

db = next(get_db())
bot_id = UUID("...")  # Отримати з БД або конфігу

# Ініціалізація сервісів
user_service = UserService(db, bot_id)
translation_service = TranslationService(db)
referral_service = ReferralService(db, bot_id)
partner_service = PartnerService(db, bot_id)
earnings_service = EarningsService(
    db, bot_id, user_service, referral_service, translation_service
)
command_service = CommandService(
    db, bot_id, user_service, translation_service,
    partner_service, referral_service, earnings_service
)

# Обробка команди
user = user_service.get_or_create_user(
    external_id="123456789",
    platform="telegram",
    language_code="uk"
)

response = command_service.handle_command(
    command="wallet",
    user_id=user.id,
    user_lang=user.language_code
)

# response = {
#     'message': '👛 Твій TON-гаманець:...',
#     'buttons': [...],
#     'parse_mode': 'HTML'
# }
```

---

## ✅ Переваги над n8n

1. **Швидкість** - SQL замість HTTP запитів до Google Sheets
2. **Транзакції** - ACID гарантії PostgreSQL
3. **Масштабованість** - готовність до 100+ ботів
4. **Multi-tenancy** - автоматична ізоляція даних
5. **Тестованість** - легко писати unit tests
6. **Версіонування** - Git control замість n8n UI
7. **AI-friendly** - модульний код для легкого розширення

---

**Статус:** ✅ Фаза 2 завершена - всі сервіси створені та готові до використання

