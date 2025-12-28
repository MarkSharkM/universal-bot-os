# Google Sheets Schema - HubAggregator

**Spreadsheet:** Earnbot_Referrals  
**Date mapped:** 20 грудня 2025  
**Total tables:** 4+ (user_wallets, bot_log, Partners_Settings, Definitions, to do, IDEA, earnbot back up, seo, backup)

---

## 📊 Table 1: user_wallets

**Tab name:** `user_wallets`  
**Purpose:** Зберігає інформацію про користувачів, їх гаманці, earnings, TOP статус, реферали

### Columns (16 total):

| # | Column Name | Data Type | Example Value | Required | Description |
|---|-------------|-----------|---------------|----------|-------------|
| A | User Chat ID | number | 9426363 | ✅ | Telegram user ID (primary key) |
| B | Username | text | @userone | ✅ | Telegram username |
| C | Wallet Address | text | EQabd1234/walletuserone | ❌ | TON wallet address (може бути порожнім) |
| D | Last Updated | datetime | 2025-07-10 3.50 | ✅ | Timestamp останнього оновлення |
| E | Total Earned TON | number | 3.50, 1.75, 0.00 | ✅ | Загальний заробіток в TON |
| F | Status | text | active, ban | ✅ | Статус користувача (active/ban) |
| G | Comment | text | spam, --- | ❌ | Коментар (причина бану або нотатки) |
| H | Level | number | 0, 1, 2 | ✅ | Рівень користувача |
| I | Total Invited | number | 0, 1, 3 | ✅ | Кількість запрошених рефералів |
| J | Last Bonus Date | date | 2025-06-30, 2025-07-11 | ❌ | Дата останнього бонусу |
| K | Referred By | number | 123456789, 987654321 | ❌ | User Chat ID реферера |
| L | First Join Date | date | uk, en | ❌ | Дата першого приєднання (⚠️ або мова?) |
| M | Language | text | iOS, Android | ❌ | Мова користувача (⚠️ або Device?) |
| N | Device | text | UA, PL | ❌ | Пристрій (⚠️ або Geo?) |
| O | Geo | text | locked, open | ❌ | Гео-локація користувача (⚠️ або TOP Status?) |
| P | TOP Status | text | locked, open | ✅ | Статус доступу до TOP Partners |

### ⚠️ ВАЖЛИВО - Невідповідності header vs data:

Бачу що **headers (L, M, N, O)** НЕ збігаються з **реальними даними**:
- Column L header: "First Join Date" → data: "uk", "en" (схоже на Language!)
- Column M header: "Language" → data: "iOS", "Android" (схоже на Device!)
- Column N header: "Device" → data: "UA", "PL" (схоже на Geo!)
- Column O header: "Geo" → data порожнє

**Реальна структура (based on data):**
- L = Language (uk, en)
- M = Device (iOS, Android)
- N = Geo (UA, PL)
- O = ??? (порожнє)
- P = TOP Status (locked, open)

### Data Examples:

**Row 2:**
```
User Chat ID: 9426363
Username: @userone
Wallet: EQabd1234/walletuserone
Last Updated: 2025-07-10 3.50
Total Earned TON: 3.50
Status: active
Comment: ---
Level: 1
Total Invited: 1
Last Bonus Date: 2025-06-30
Referred By: ---
Language: uk
Device: iOS
Geo: UA
TOP Status: locked
```

**Row 3:**
```
User Chat ID: 987654321
Username: @usertwo
Wallet: EQefgh5678/walletusertwo
Last Updated: 2025-07-09 1.75
Total Earned TON: 1.75
Status: active
Comment: ---
Level: 2
Total Invited: 1
Last Bonus Date: 2025-07-01
Referred By: 123456789
Language: en
Device: Android
Geo: PL
TOP Status: open
```

**Row 4:**
```
User Chat ID: 123456789
Username: @userthree
Wallet: EQzcxv9090/walletthree
Last Updated: 2025-07-11 0.00
Total Earned TON: 0.00
Status: ban
Comment: spam
Level: 0
Total Invited: 0
Last Bonus Date: 2025-07-11
Referred By: 987654321
Language: uk
Device: iOS
Geo: UA
TOP Status: locked
```

### Relationships:
- **Referred By** (column K) → references **User Chat ID** (column A)
- Self-referencing relationship для реферальної системи

### Business Rules:
1. **TOP Status unlock:**
   - `locked` → потрібно 5 інвайтів АБО оплата 500⭐
   - `open` → доступ до TOP Partners

2. **Status values:**
   - `active` - звичайний користувач
   - `ban` - забанений (spam або інше)

3. **Total Invited:**
   - Рахується з таблиці `bot_log` (унікальні `Ref Parameter`)

---

## 📋 Table 2: bot_log

**Tab name:** `bot_log`  
**Purpose:** Логування всіх подій користувачів - команди, кліки, реферальний трафік

### Columns (24+ total):

| # | Column Name | Data Type | Example Value | Required | Description |
|---|-------------|-----------|---------------|----------|-------------|
| A | Timestamp | datetime | 2025-08-01 20:19, 2025-10-04 19:58:59 | ✅ | Час події |
| B | User Chat ID | number | 987654321, 380927579 | ✅ | Telegram user ID |
| C | Username | text | @johndoe, k_23, mark_mar | ✅ | Telegram username |
| D | First Name | text | John, mark | ❌ | Ім'я користувача |
| E | Last Name | text | Doe, mark | ❌ | Прізвище користувача |
| F | Message ID | number | 1122, 712, 1757, 3143 | ✅ | ID повідомлення в Telegram |
| G | Message Text | text | /start, /partners, /start earnings, activate_7 | ✅ | Текст команди або callback |
| H | Original Link | url | https://t.me/ThePostArchitectBot?start=... | ❌ | Оригінальний лінк (якщо є) |
| I | Short Link | url | https://bit.ly/... | ❌ | Короткий лінк |
| J | Ref Parameter | text | tgr_XYZ7, NO_REF, tgr_3809 | ✅ | Реферальний параметр (_tgr_userId або NO_REF) |
| K | Clicks | number | 89, 1 | ❌ | Кількість кліків |
| L | Partner Bot | text | @ThePostArchitectBot | ❌ | Назва партнерського бота |
| M | Commission (%) | number | 25 | ❌ | Відсоток комісії |
| N | Earned TON | number | 0.10, 0 | ✅ | Зарахований TON |
| O | Payout Status | text | Pending, Unpaid | ✅ | Статус виплати |
| P | Payout Date | date | (empty) | ❌ | Дата виплати |
| Q | Referred By | text | @ref_user, NO_REF, tgr_3809 | ✅ | Хто зареферив (username або tgr) |
| R | Referral Level | number | 1, 0 | ✅ | Рівень реферала (0 = direct) |
| S | Smart Link | url | https://earnbot.link/g... | ❌ | Smart tracking лінк |
| T | Click Type | text | start, Organic, Referral | ✅ | Тип кліку (start/Organic/Referral) |
| U | Language | text | uk, en | ✅ | Мова користувача |
| V | Device | text | Android, iOS | ❌ | Тип пристрою |
| W | Geo | text | UA | ❌ | Гео-локація |
| X | Month | text | Aug, October, November | ❌ | Місяць події |
| Y | Status | text | OK, Logged | ✅ | Статус запису (OK/Logged) |

### Data Examples:

**Row 2 (реферальний клік з payment):**
```
Timestamp: 2025-08-01 20:19
User Chat ID: 987654321
Username: @johndoe
First Name: John
Last Name: Doe
Message ID: 1122
Message Text: /start
Original Link: https://t.me/ThePostArchitectBot?start=tgr_XYZ789
Short Link: https://bit.ly/vwz789
Ref Parameter: tgr_XYZ7
Clicks: 89
Partner Bot: @ThePostArchitectBot
Commission (%): 25
Earned TON: 0.10
Payout Status: Pending
Referred By: @ref_user
Referral Level: 1
Smart Link: https://earnbot.link/g...
Click Type: start
Language: uk
Device: Android
Geo: UA
Month: Aug
Status: OK
```

**Row 3 (органічний трафік, /partners):**
```
Timestamp: 2025-10-04 19:58:59
User Chat ID: 380927579
Username: k_23
First Name: mark
Last Name: mark
Message ID: 712
Message Text: /partners
Ref Parameter: NO_REF
Clicks: 1
Earned TON: 0
Payout Status: Unpaid
Referred By: NO_REF
Referral Level: 0
Click Type: Organic
Language: uk
Month: October
Status: Logged
```

**Row 4 (реферальний, /start з tgr):**
```
Timestamp: 2025-11-08 15:48:00
User Chat ID: 380927579
Username: k_23
First Name: mark
Last Name: mark_mar
Message ID: 1757
Message Text: /start tgr_38092 7579
Original Link: https://t.me/EarnHubAggregatorBot?start=tgr_3 80927579
Ref Parameter: tgr_3809 27579
Clicks: 1
Earned TON: 0
Payout Status: Unpaid
Referred By: tgr_3809 27579
Referral Level: 1
Click Type: Referral
Language: en
Month: November
Status: Logged
```

**Rows 5-12 (різні команди без рефералів):**
- `/start partners` - NO_REF, Organic, uk
- `/start earnings` - NO_REF, Organic, uk
- `/earnings` - NO_REF, Organic, uk
- `activate_7` (callback) - NO_REF, Organic, uk (×5 записів)

### Ref Parameter Values:
1. **`tgr_<userId>`** - валідний реферальний параметр (наприклад: tgr_XYZ7, tgr_3809)
2. **`NO_REF`** - органічний трафік (без реферала)
3. **Format:** `_tgr_{userId}` або legacy `tgr_{userId}`

### Click Type Values:
1. **`start`** - перший запуск через /start з лінком
2. **`Organic`** - прямий трафік без реферала
3. **`Referral`** - трафік з реферального лінка

### Business Logic:
1. **Count Referrals:** Підрахунок унікальних `Ref Parameter` (not NO_REF) для кожного користувача
2. **Referral Level:**
   - `0` = direct (without referrer)
   - `1` = first level referral
3. **Payout Status:**
   - `Pending` - очікує виплату
   - `Unpaid` - не оплачено
4. **Status:**
   - `OK` - успішно оброблено
   - `Logged` - тільки залогувано

### ⚠️ Observations:
- **Message Text** може бути командою (`/start`, `/partners`, `/earnings`) або callback (`activate_7`)
- **Ref Parameter** зберігається навіть якщо це NO_REF (для фільтрації organic vs referral)
- **Smart Link** використовується для tracking (earnbot.link)
- Є багато записів з однаковим користувачем (380927579 / k_23 / mark) - тестування?

---

## 📋 Table 3: Partners_Settings

**Tab name:** `Partners_Settings`  
**Purpose:** Каталог всіх ботів (TOP та Partners) з описами на 5 мовах, комісіями, ROI

### Columns (21 total):

| # | Column Name | Data Type | Example Value | Required | Description |
|---|-------------|-----------|---------------|----------|-------------|
| A | Bot Name | text | Boinkers, EasyGiftDropbot, CashBackBot | ✅ | Назва бота |
| B | Description | text (emoji) | Мем-батли за зірки 🔥💎 | ✅ | Опис українською (базовий) |
| C | Description_en | text (emoji) | Meme battles for Stars 🔥💎 | ✅ | Опис англійською |
| D | Description_ru | text (emoji) | Мем-батлы за звёзды 🔥💎 | ✅ | Опис російською |
| E | Description_de | text (emoji) | Meme-Schlachten für Sterne 🔥💎 | ✅ | Опис німецькою |
| F | Description_es | text (emoji) | Batallas de memes por Estrellas 🔥💎 | ✅ | Опис іспанською |
| G | Referral Link | url | https://t.me/boinker_bot?start=tgr_qEfhJpQxZGQy | ✅ | Реферальний лінк з placeholder `{TGR}` або `tgr_` |
| H | Bitly Link | url | (порожньо) або shortened link | ❌ | Короткий лінк |
| I | RefParam | text | _tgr_qEfhJpQxZGQy, _tgr_WhuYB40ZWFI | ✅ | Реферальний параметр (_tgr_ format) |
| J | Commission (%) | number | 62, 20, 30, 1, 2 | ✅ | Відсоток комісії |
| K | Category | text | NEW, TOP | ✅ | Категорія бота (NEW/TOP) |
| L | Active | text | Yes, No | ✅ | Чи активний бот |
| M | Duration | number | 9999, 30, 90, 365 | ❌ | Тривалість (днів?) |
| N | Verified | text | Yes | ✅ | Чи верифікований |
| O | Clicks | number | 0 | ✅ | Кількість кліків |
| P | GPT | text (emoji) | Мем-батли 🔥, Рандом 🎁, Калібрі 📊, Фінанси 💰, Бот Автопокупки 🤖, Банк 🏦 | ❌ | Категорія для GPT (з emoji) |
| Q | Short Link | text | Boinkers, Подарунки, Gifts, Банк | ❌ | Коротка назва/категорія |
| R | Added | date | 2025-07-18 | ✅ | Дата додавання |
| S | Owner | text | @HubAggregatorBot | ✅ | Власник/джерело |
| T | Середній дохід | number | 1,60, 9,40, 1,50, 4,40, 23,90, 31,60, 23,9 | ❌ | Середній дохід (для розрахунків?) |
| U | ROI Score | number | 1,0, 1,9, 0,5, 0,8, 7,2, 0,6 | ✅ | ROI Score для сортування TOP ботів! |

### Data Examples:

**Row 2 (Boinkers - NEW категорія):**
```
Bot Name: Boinkers
Description: Мем-батли за зірки 🔥💎
Description_en: Meme battles for Stars 🔥💎
Description_ru: Мем-батлы за звёзды 🔥💎
Description_de: Meme-Schlachten für Sterne 🔥💎
Description_es: Batallas de memes por Estrellas 🔥💎
Referral Link: https://t.me/boinker_bot?start=tgr_qEfhJpQxZGQy
RefParam: _tgr_qEfhJpQxZGQy
Commission (%): 62
Category: NEW
Active: No (червоний)
Duration: 9999
Verified: Yes
Clicks: 0
GPT: Мем-батли 🔥
Short Link: Boinkers
Added: 2025-07-18
Owner: @HubAggregatorBot
Середній дохід: 1,60
ROI Score: 1,0
```

**Row 3 (EasyGiftDropbot - TOP):**
```
Bot Name: EasyGiftDropbot
Description: 🎁 Подарунки за активність
Description_en: 🎁 Gifts for activity
Description_ru: 🎁 Подарки за активность
Description_de: 🎁 Geschenke für Aktivität
Description_es: 🎁 Regalos por actividad
Referral Link: https://t.me/EasyGiftDropbot?start=tgr_WhuYB40ZWFI
Bitly Link: (порожньо)
RefParam: _tgr_WhuYB40ZWFI
Commission (%): 20
Category: TOP
Active: Yes
Duration: 30
Verified: Yes
Clicks: 0
GPT: Рандом 🎁
Short Link: Подарунки
Added: 2025-07-18
Owner: @HubAggregatorBot
Середній дохід: 9,40
ROI Score: 1,9
```

**Row 4 (CashBackBot - TOP):**
```
Bot Name: CashBackBot
RefParam: _tgr_JhtU6nIj4O0Oji
Commission (%): 30
Category: TOP
Active: Yes
Duration: 90
ROI Score: 0,5
```

**Row 5 (RandGiftBot - NEW):**
```
Bot Name: RandGiftBot
RefParam: _tgr_dKf6mDQ3Y2M6
Commission (%): 1
Category: NEW
Active: Yes
Duration: 9999
ROI Score: 0,8
```

**Row 6 (TheStarsBank - TOP):**
```
Bot Name: TheStarsBank
Description: 💰 Заробіток на транзакціях 💰
Description_en: 💰 Earnings from transactions 💰
Description_ru: 💰 Заработок на транзакциях 💰
Description_de: 💰 Einnahmen aus Transaktionen 💰
Description_es: 💰 Ganancias por transacciones 💰
RefParam: _tgr_JUV1QDBzMDUy
Commission (%): 30
Category: TOP
Active: No (червоний)
Duration: 365
GPT: Фінанси 💰
Short Link: Банк
ROI Score: 7,2
```

**Row 7 (AutoGiftsBot - NEW):**
```
Bot Name: AutoGiftsBot
Description: 🎁 Автопокупка подарунків
Description_en: 🎁 Auto purchase of gifts
Description_ru: 🎁 Автопокупка подарков
Description_de: 🎁 Automatischer Kauf von Geschenken
Description_es: 🎁 Compra automática de regalos
RefParam: _tgr_nWMmrkI3MDMy
Commission (%): 2
Category: NEW
Active: No
Duration: 9999
GPT: Бот Автопокупки 🤖
Short Link: Gifts
ROI Score: 0,6
```

**Row 8 (TheStarsBank duplicate - TOP):**
```
Same as Row 6 but ROI Score: 7,2
```

### Category Values:
1. **`TOP`** - Преміум боти (потрібно unlock через 5 invites або 500⭐)
2. **`NEW`** - Безкоштовні партнерські боти

### Active Values:
1. **`Yes`** - Активний (зелений)
2. **`No`** - Неактивний (червоний)

### Business Logic:

1. **TOP Bots фільтр:**
   ```
   Category = "TOP" AND Active = "Yes"
   ```

2. **Partners фільтр:**
   ```
   Category = "Partners" (або не TOP?) AND Active = "Yes" AND Verified = "Yes"
   ```

3. **ROI Score sorting:**
   - Використовується для сортування TOP ботів
   - Вищий ROI = вище в списку
   - Formula: можливо `Середній дохід / Commission` або інша

4. **Multilang descriptions:**
   - Format: `Description_{lang}` де lang = uk/en/ru/de/es
   - Fallback: якщо `Description_{lang}` порожнє → використовується базовий `Description`

5. **Referral Link personalization:**
   - Template: `{TGR}` або `tgr_` в лінку
   - Заміняється на `_tgr_{userId}` при генерації для конкретного юзера

### ⚠️ Issues:
1. **Duplicate TheStarsBank** (rows 6 та 8) - обидва з `Active = No`
2. **RefParam format inconsistency:**
   - Деякі з `_tgr_` (underscore спочатку)
   - Можливо legacy format `tgr_` (без underscore)
3. **Duration values:**
   - `9999` = "назавжди"?
   - `30/90/365` = днів активності?

### 🎯 Usage in Code Nodes:

**Format_TopBots_Message (381 lines):**
- Читає цю таблицю
- Фільтрує `Category = "TOP" AND Active != "false"`
- Сортує по `ROI Score` (descending)
- Персоналізує `Referral Link` з `_tgr_{userId}`
- Використовує `Description_{lang}` для multilang

**format_partners_list (87 lines):**
- Читає цю таблицю
- Фільтрує партнерів (не TOP)
- Використовує `Description_{lang}` для multilang

---

## 📋 Table 4: Other tabs

Бачу ще таби:
- `Definitions`
- `to do`
- `IDEA`
- `earnbot back up`
- `seo`
- `backup`

**Waiting for screenshots щоб зрозуміти структуру** 📸

---

## 🔍 Next Steps:

1. ⏳ Waiting for `bot_log` screenshot
2. ⏳ Waiting for `Partners_Settings` screenshot
3. ⏳ Check if `Earnbot AGE` tab is used (бачу внизу)
4. ⏳ Verify column headers (L, M, N, O мають невідповідності)
