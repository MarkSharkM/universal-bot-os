# 🌐 API Endpoints - Universal Bot OS

**Multi-tenant API для 100+ ботів**

---

## 📍 Endpoints

### 1. Telegram Webhook
**POST** `/api/v1/webhooks/telegram/{bot_token}`

**Опис:** Основний endpoint для обробки Telegram webhook updates.

**Multi-tenant:** ✅ Ідентифікація бота через `bot_token` (в production через `bot_id`)

**Обробляє:**
- Messages (команди, текст, wallet addresses)
- Callback queries (кнопки)
- Payment events (pre_checkout_query, successful_payment)

**Приклад:**
```json
POST /api/v1/webhooks/telegram/123456:ABC-DEF...
{
  "message": {
    "from": {"id": 123456789, "language_code": "uk"},
    "text": "/wallet"
  }
}
```

**Відповідь:**
```json
{"ok": true}
```

---

### 2. Mini Apps
**POST** `/api/v1/mini-apps/mini-app/{bot_id}`

**Опис:** Webhook для Telegram Mini Apps.

**Multi-tenant:** ✅ `bot_id` в URL

**GET** `/api/v1/mini-apps/mini-app/{bot_id}/data?user_id={user_id}`

**Опис:** Отримання даних користувача для Mini App.

---

### 3. SEO Pages
**GET** `/api/v1/seo/bot/{bot_id}`

**Опис:** SEO-оптимізована сторінка для бота.

**Multi-tenant:** ✅ Кожен бот має свою SEO сторінку

**Відповідь:** HTML з мета-тегами, описом бота

---

## 🔑 Multi-Tenant Routing

### Поточний підхід:
- **Telegram webhook:** `bot_token` в URL (тимчасово)
- **Mini Apps:** `bot_id` в URL
- **SEO:** `bot_id` в URL

### Production підхід (рекомендовано):
- Використовувати `X-Bot-ID` header
- Або subdomain routing: `{bot_id}.api.domain.com`
- Або path prefix: `/api/v1/bots/{bot_id}/...`

---

## 🔄 Flow Diagram

```
Telegram Update
    ↓
POST /api/v1/webhooks/telegram/{bot_token}
    ↓
Get Bot by token → bot_id
    ↓
Initialize Services (with bot_id)
    ↓
TelegramAdapter.handle_webhook()
    ↓
Route by event_type:
    ├─ message → CommandService
    ├─ callback_query → CommandService
    └─ payment → Payment handler
    ↓
Send response via TelegramAdapter
```

---

## ✅ Статус

- ✅ Telegram webhook endpoint готовий
- ✅ Mini Apps endpoints готові (базова структура)
- ✅ SEO endpoints готові (базова структура)
- ⏳ Admin API (Фаза 6)

---

**Готово до тестування!** 🚀

