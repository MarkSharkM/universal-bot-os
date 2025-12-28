# 📊 Monitoring & Health Checks - Universal Bot OS

**Система моніторингу та health checks для production**

---

## 🏥 Health Checks

### Endpoints

#### 1. `GET /health`
**Повний health check всіх компонентів**

**Response:**
```json
{
    "status": "healthy",
    "version": "0.1.0",
    "environment": "production",
    "components": {
        "database": {
            "status": "healthy",
            "message": "Database connection successful"
        },
        "redis": {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    }
}
```

---

#### 2. `GET /health/ready`
**Readiness probe для Kubernetes/Railway**

**Returns:**
- `200 OK` - готовий приймати трафік
- `503 Service Unavailable` - не готовий

**Використання:**
- Railway автоматично перевіряє цей endpoint
- Kubernetes readiness probe

---

#### 3. `GET /health/live`
**Liveness probe для Kubernetes/Railway**

**Returns:**
- `200 OK` - застосунок живий

**Використання:**
- Railway автоматично перевіряє цей endpoint
- Kubernetes liveness probe

---

## 📝 Логування

### Структура логів

**Файли:**
- `logs/app.log` - всі логи (ротація 10MB, 5 файлів)
- `logs/error.log` - тільки помилки (ротація 10MB, 5 файлів)

**Формат:**
```
2024-12-28 10:30:45 - app.api.v1.webhooks - INFO - POST /api/v1/webhooks/telegram/... - Status: 200 - Time: 0.123s
```

**Рівні:**
- `DEBUG` - детальна інформація (тільки в development)
- `INFO` - загальна інформація
- `WARNING` - попередження
- `ERROR` - помилки

---

### Request Logging

**Автоматичне логування всіх запитів:**
- Метод та URL
- IP адреса клієнта
- Статус код відповіді
- Час виконання

**Приклад:**
```
2024-12-28 10:30:45 - app.main - INFO - POST /api/v1/webhooks/telegram/... - 192.168.1.1
2024-12-28 10:30:45 - app.main - INFO - POST /api/v1/webhooks/telegram/... - Status: 200 - Time: 0.123s
```

---

## 🐛 Error Tracking

### Автоматичне відстеження помилок

**Глобальний exception handler:**
- Логує всі необроблені винятки
- Повертає структуровані помилки
- В production приховує деталі

**Приклад:**
```python
from app.core.monitoring import track_error

try:
    # код
except Exception as e:
    track_error(
        "wallet_validation_error",
        bot_id=str(bot_id),
        user_id=str(user_id),
        metadata={"wallet": wallet_address}
    )
    raise
```

---

## 📈 Performance Monitoring

### Decorator для моніторингу

**Використання:**
```python
from app.core.monitoring import monitor_performance

@monitor_performance
async def my_function():
    # код
    pass
```

**Що відстежується:**
- Час виконання функції
- Статус (success/error)
- Автоматичне логування метрик

---

## 🔧 Налаштування

### Environment Variables

```env
# Logging
DEBUG=false
ENVIRONMENT=production

# Health checks
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

---

## 🚀 Railway Integration

**Railway автоматично:**
- Перевіряє `/health/ready` для readiness
- Перевіряє `/health/live` для liveness
- Перезапускає контейнер при невдачі liveness

**Налаштування в railway.json:**
```json
{
    "healthcheckPath": "/health/ready",
    "healthcheckTimeout": 100
}
```

---

## 📊 Метрики

### Відстежувані метрики

**Автоматично:**
- Request duration
- Error rate
- Function performance

**Вручну:**
```python
from app.core.monitoring import track_metric

track_metric(
    "user_registrations",
    value=1,
    bot_id=str(bot_id),
    tags={"platform": "telegram"}
)
```

---

## ✅ Статус

- ✅ Health checks готові
- ✅ Логування з ротацією
- ✅ Error tracking
- ✅ Performance monitoring
- ✅ Railway integration
- ⏳ External monitoring (Sentry, DataDog) - опціонально

---

**Готово до production!** 🚀

