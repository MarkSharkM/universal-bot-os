# 📱 Push Notifications в Telegram Mini App

## 📋 Огляд

Push notifications дозволяють надсилати повідомлення користувачам навіть коли міні апп закрито. В Telegram Mini App є два способи:

1. **Telegram Bot API** (основний) - надсилання повідомлень через бота
2. **Web Push API** (опціонально) - через Service Workers для веб-повідомлень

## 🔧 Поточна реалізація

### ✅ Telegram Bot API (активно використовується)

Ми вже маємо систему надсилання повідомлень через Telegram Bot API:

```python
# app/adapters/telegram.py
adapter.send_message(bot_id, user_external_id, text)
```

**Переваги:**
- Працює всередині Telegram
- Високий open rate
- Не потребує додаткових дозволів
- Повідомлення приходять у чат бота

**Використання:**
- Нагадування про нових партнерів
- Оновлення балансу
- Сповіщення про розблокування TOP
- Інші важливі події

### 🔄 Web Push API (зареєстровано, не використовується)

Додано Service Worker для майбутнього використання:

**Файли:**
- `/static/mini-app/sw.js` - Service Worker
- Реєстрація в `app.js` → `registerServiceWorker()`

**Можливості:**
- Push notifications навіть коли міні апп закрито
- Offline caching
- Background sync

**Статус:** Зареєстровано, але не активно використовується. Може бути увімкнено в майбутньому.

## 📝 Як використовувати

### Telegram Bot API (рекомендовано)

```python
from app.adapters.telegram import TelegramAdapter

adapter = TelegramAdapter()
await adapter.send_message(
    bot_id=bot_id,
    user_external_id="380927579",
    text="🎉 Новий партнер додано! Перевірте в міні апп.",
    reply_markup={
        "inline_keyboard": [[
            {"text": "Відкрити міні апп", "web_app": {"url": mini_app_url}}
        ]]
    }
)
```

### Web Push API (майбутнє)

Для активації потрібно:

1. **Отримати subscription:**
```javascript
const registration = await navigator.serviceWorker.ready;
const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: VAPID_PUBLIC_KEY
});
```

2. **Надіслати subscription на backend:**
```javascript
await Api.savePushSubscription(botId, subscription);
```

3. **Надсилати push з backend:**
```python
# Використовувати webpush library
import webpush
webpush.send_notification(
    subscription_info,
    data=json.dumps({"title": "Нове повідомлення", "body": "..."})
)
```

## 🎯 Коли використовувати

### Telegram Bot API (завжди)
- ✅ Нагадування про важливі події
- ✅ Оновлення балансу
- ✅ Нові партнери
- ✅ Розблокування TOP

### Web Push API (опціонально)
- ⚠️ Тільки якщо потрібні повідомлення поза Telegram
- ⚠️ Для веб-версії міні апп (якщо буде)
- ⚠️ Для cross-platform підтримки

## 🔍 Compliance Checker

Compliance checker автоматично перевіряє:
- ✅ Service Worker registration
- ✅ Notification permission
- ✅ Push Manager availability
- ✅ Subscription status

Запустити перевірку:
```javascript
// В консолі браузера
window.MiniAppComplianceResult.pushNotifications
```

## 📚 Документація

- **Telegram Bot API:** https://core.telegram.org/bots/api#sendmessage
- **Web Push API:** https://developer.mozilla.org/en-US/docs/Web/API/Push_API
- **Service Workers:** https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API

## ⚠️ Важливо

1. **Telegram Bot API** - основний спосіб для Telegram Mini App
2. **Web Push API** - опціонально, для майбутнього використання
3. **Service Worker** вже зареєстровано, але не активний
4. Для активації Web Push потрібно додати VAPID keys та backend endpoint

---

**Останнє оновлення:** 4 січня 2026
