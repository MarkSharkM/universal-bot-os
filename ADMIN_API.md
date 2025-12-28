# 👨‍💼 Admin API - Universal Bot OS

**Multi-tenant Admin API для керування ботами**

---

## 📡 Endpoints

### Bots Management

#### `GET /api/v1/admin/bots`
**List all bots**

**Query Parameters:**
- `skip` (int, default: 0) - Pagination offset
- `limit` (int, default: 100) - Max records
- `platform` (str, optional) - Filter by platform
- `is_active` (bool, optional) - Filter by active status

**Response:**
```json
[
    {
        "id": "uuid",
        "name": "HubAggregator Bot",
        "platform_type": "telegram",
        "default_lang": "uk",
        "is_active": true,
        "created_at": "2024-12-28T10:00:00Z",
        "updated_at": "2024-12-28T10:00:00Z"
    }
]
```

---

#### `GET /api/v1/admin/bots/{bot_id}`
**Get bot by ID**

**Response:**
```json
{
    "id": "uuid",
    "name": "HubAggregator Bot",
    "platform_type": "telegram",
    "default_lang": "uk",
    "is_active": true
}
```

---

#### `POST /api/v1/admin/bots`
**Create new bot**

**Request:**
```json
{
    "name": "New Bot",
    "platform_type": "telegram",
    "token": "123456:ABC-DEF...",
    "default_lang": "uk",
    "config": {}
}
```

**Response:** Created bot object

---

#### `PATCH /api/v1/admin/bots/{bot_id}`
**Update bot**

**Request:**
```json
{
    "name": "Updated Name",
    "config": {"ai": {"provider": "openai"}},
    "is_active": true
}
```

**Response:** Updated bot object

---

#### `DELETE /api/v1/admin/bots/{bot_id}`
**Delete bot (soft delete)**

**Response:**
```json
{
    "message": "Bot deactivated successfully"
}
```

---

### Bot Statistics

#### `GET /api/v1/admin/bots/{bot_id}/stats`
**Get bot statistics**

**Response:**
```json
{
    "bot_id": "uuid",
    "bot_name": "HubAggregator Bot",
    "users": {
        "total": 1500,
        "active": 1200
    },
    "partners": {
        "total": 50,
        "active": 45
    },
    "total_balance": 1234.56
}
```

---

### Partners Management

#### `GET /api/v1/admin/bots/{bot_id}/partners`
**List partners for a bot**

**Query Parameters:**
- `category` (str, optional) - Filter by category (TOP, NEW)
- `active_only` (bool, default: true) - Show only active

**Response:**
```json
[
    {
        "id": "uuid",
        "bot_name": "Boinkers",
        "description": "Мем-батли за зірки 🔥💎",
        "referral_link": "https://t.me/boinker_bot?start={TGR}",
        "commission": 62.0,
        "category": "NEW",
        "active": "Yes",
        "verified": "Yes",
        "roi_score": 1.0
    }
]
```

---

#### `POST /api/v1/admin/bots/{bot_id}/partners`
**Create partner**

**Request:**
```json
{
    "bot_name": "New Partner Bot",
    "description": "Description",
    "description_en": "Description EN",
    "description_ru": "Description RU",
    "referral_link": "https://t.me/bot?start={TGR}",
    "commission": 50.0,
    "category": "NEW",
    "active": "Yes",
    "verified": "Yes",
    "roi_score": 1.5
}
```

**Response:** Created partner object

---

#### `PATCH /api/v1/admin/bots/{bot_id}/partners/{partner_id}`
**Update partner**

**Request:**
```json
{
    "active": "No",
    "commission": 60.0
}
```

**Response:** Updated partner object

---

#### `DELETE /api/v1/admin/bots/{bot_id}/partners/{partner_id}`
**Delete partner**

**Response:**
```json
{
    "message": "Partner deleted successfully"
}
```

---

### AI Configuration

#### `GET /api/v1/admin/bots/{bot_id}/ai-config`
**Get AI configuration**

**Response:**
```json
{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 2000,
    "has_api_key": true,
    "has_system_prompt": false,
    "system_prompt": ""
}
```

---

#### `PATCH /api/v1/admin/bots/{bot_id}/ai-config`
**Update AI configuration**

**Request:**
```json
{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_key": "sk-...",
    "temperature": 0.7,
    "max_tokens": 2000,
    "system_prompt": "Custom prompt..."
}
```

**Response:** Updated AI configuration (without sensitive data)

---

## 🔐 Безпека

**⚠️ Важливо:**
- Зараз Admin API відкритий (без автентифікації)
- В production додай автентифікацію (JWT, API keys)
- Додай middleware для перевірки прав доступу

**Рекомендації:**
```python
# Додай в main.py
from app.core.security import verify_token

@app.middleware("http")
async def admin_auth(request: Request, call_next):
    if request.url.path.startswith("/api/v1/admin"):
        # Перевірка токену
        token = request.headers.get("Authorization")
        if not verify_token(token):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    return await call_next(request)
```

---

## 📊 Приклади використання

### Створити бота
```bash
curl -X POST https://api.example.com/api/v1/admin/bots \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Bot",
    "platform_type": "telegram",
    "token": "123456:ABC-DEF...",
    "default_lang": "uk"
  }'
```

### Отримати статистику
```bash
curl https://api.example.com/api/v1/admin/bots/{bot_id}/stats
```

### Додати партнера
```bash
curl -X POST https://api.example.com/api/v1/admin/bots/{bot_id}/partners \
  -H "Content-Type: application/json" \
  -d '{
    "bot_name": "Partner Bot",
    "description": "Description",
    "referral_link": "https://t.me/bot?start={TGR}",
    "commission": 50.0,
    "category": "NEW",
    "active": "Yes"
  }'
```

---

## ✅ Статус

- ✅ CRUD для ботів
- ✅ CRUD для партнерів
- ✅ AI конфігурація
- ✅ Статистика ботів
- ⏳ Автентифікація (TODO)
- ⏳ Admin UI (TODO)

---

**API готовий до використання!** 🚀

