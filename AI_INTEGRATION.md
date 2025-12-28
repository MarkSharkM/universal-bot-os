# 🤖 AI Integration - Universal Bot OS

**Multi-tenant AI service з підтримкою мови користувача**

---

## 📦 Створено

### 1. `AIService` - AI сервіс
**Файл:** `app/services/ai_service.py`

**Функціонал:**
- Підтримка OpenAI та Anthropic
- Автоматична детекція мови користувача
- Контекст з історії повідомлень
- Налаштування через bot.config
- Збереження історії в БД

**Multi-tenant:** ✅ Всі операції scoped по `bot_id`

---

## 🔧 Налаштування

### Через Bot Config (JSONB)

```python
bot.config = {
    "ai": {
        "provider": "openai",  # або "anthropic"
        "model": "gpt-4o-mini",
        "api_key": "sk-...",
        "temperature": 0.7,
        "max_tokens": 2000,
        "system_prompt": "Ти корисний асистент..."  # опціонально
    }
}
```

### Через API (після Фази 6 - адмінка)

```bash
PUT /api/v1/admin/bots/{bot_id}/ai-config
{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_key": "sk-...",
    "temperature": 0.7,
    "system_prompt": "Custom prompt..."
}
```

---

## 🌍 Підтримка мов

**Автоматична детекція мови:**
- Українська (uk)
- Англійська (en)
- Російська (ru)
- Німецька (de)
- Іспанська (es)

**System prompts по мовах:**
- Автоматично генерується на основі мови користувача
- Можна перевизначити через `system_prompt` в конфігу

---

## 📡 API Endpoints

### POST `/api/v1/ai/chat`

**Request:**
```json
{
    "user_id": "123456789",
    "message": "Привіт!",
    "user_lang": "uk"
}
```

**Response:**
```json
{
    "response": "Привіт! Чим можу допомогти?",
    "language": "uk"
}
```

**Headers:**
- `X-Bot-ID: <bot_uuid>` (multi-tenant routing)

---

### GET `/api/v1/ai/config`

**Response:**
```json
{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 2000,
    "has_api_key": true,
    "has_system_prompt": false
}
```

---

## 💾 Історія повідомлень

**Автоматичне збереження:**
- Всі повідомлення зберігаються в таблиці `messages`
- Використовується для контексту AI
- Останні 10 повідомлень використовуються як контекст

**Формат:**
```python
Message(
    user_id=user_id,
    bot_id=bot_id,
    role="user" | "assistant" | "system",
    content="..."
)
```

---

## 🔄 Інтеграція з Telegram

**Приклад використання в webhook:**

```python
from app.services import AIService, TranslationService

# В webhook handler
if not command:  # Якщо не команда
    ai_service = AIService(db, bot_id, translation_service)
    response = await ai_service.generate_response(
        user.id,
        text,
        user.language_code
    )
    
    await adapter.send_message(
        bot_id,
        user.external_id,
        response
    )
```

---

## 📚 Залежності

**Додано в requirements.txt:**
- `openai==1.12.0` - OpenAI API
- `anthropic==0.18.1` - Anthropic API

**Встановлення:**
```bash
pip install -r requirements.txt
```

---

## ⚙️ Конфігурація через змінні оточення

**Опціонально (для глобальних налаштувань):**

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_AI_PROVIDER=openai
DEFAULT_AI_MODEL=gpt-4o-mini
```

**Пріоритет:**
1. Bot config (найвищий)
2. Environment variables
3. Defaults

---

## 🎯 Multi-Tenant

**Кожен бот має свою AI конфігурацію:**
- Окремі API ключі
- Окремі моделі
- Окремі system prompts
- Окремі історії повідомлень

**Приклад:**
```python
# Bot 1 - OpenAI
bot1.config['ai'] = {
    'provider': 'openai',
    'model': 'gpt-4o-mini',
    'api_key': 'sk-...'
}

# Bot 2 - Anthropic
bot2.config['ai'] = {
    'provider': 'anthropic',
    'model': 'claude-3-haiku-20240307',
    'api_key': 'sk-ant-...'
}
```

---

## ✅ Статус

- ✅ AIService створено
- ✅ Підтримка OpenAI
- ✅ Підтримка Anthropic
- ✅ Автоматична детекція мови
- ✅ Збереження історії
- ✅ API endpoints готові
- ⏳ Інтеграція в Telegram webhook (опціонально)

---

**Готово до використання!** 🚀

