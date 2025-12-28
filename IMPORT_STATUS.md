# Статус імпорту даних

## Що зроблено:

1. ✅ Створено API endpoint: `/api/v1/admin/bots/{bot_id}/import-data`
2. ✅ Додано CSV файли в git:
   - `translations_for prod tg.csv`
   - `Earnbot_Referrals - user_wallets.csv`
   - `Earnbot_Referrals - Partners_Settings.csv`
   - `Earnbot_Referrals - bot_log.csv`
3. ✅ Виправлено помилку з Decimal → float для JSON serialization

## Після завершення деплоїв:

Запусти імпорт через API:

```bash
curl -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/import-data?import_type=all" \
  -H "Content-Type: application/json"
```

Або через Admin UI - після імпорту дані з'являться в таблицях.

## Примітка:

Надалі буду об'єднувати зміни в один коміт, щоб уникнути множинних деплоїв.

