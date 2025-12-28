# Виправлення емодзі в /start

## Проблема:
- Прод версія: ✨ (іскра) та 💰 (мішок грошей)
- Поточна версія: ⭐ (зірка) та 💸 (гроші з крилами)

## Виправлення:
✅ Оновлено CSV файл `translations_for prod tg.csv`:
- ⭐ → ✨
- 💸 → 💰

✅ Зміни задеплоєні в git

## Наступні кроки:
1. Зачекати deployment (30-60 сек)
2. Імпортувати переклади через API:
   ```bash
   curl -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/import-data?import_type=translations"
   ```
3. Перевірити через тестовий endpoint:
   ```bash
   curl -X POST "https://api-production-57e8.up.railway.app/api/v1/admin/bots/4f3c45a5-39ac-4d6e-a0eb-263765d70b1a/test-command?command=/start&user_lang=uk"
   ```

