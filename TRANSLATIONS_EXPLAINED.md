# Як працюють переклади

## Два типи перекладів:

### 1. Переклади партнерів (в `business_data.data`)
- Зберігаються разом з кожним партнером
- Поля: `description`, `description_en`, `description_ru`, `description_de`, `description_es`
- Використовуються через `PartnerService._get_localized_description()`
- **Не змішуються з основним транслятором** ✅

### 2. Переклади кнопок/логіки (в таблиці `translations`)
- Зберігаються в окремій таблиці `translations`
- Використовуються через `TranslationService.get_translation()`
- Імпортовані з `translations_for prod tg.csv`
- **Працюють для всіх кнопок, повідомлень, логіки** ✅

## Переваги:

✅ Партнери можна додавати/видаляти без впливу на переклади кнопок
✅ Переклади партнерів зберігаються разом з партнером
✅ Переклади кнопок централізовані в одній таблиці

## Приклад:

```python
# Партнер (з business_data.data)
{
    "bot_name": "EarnBot",
    "description": "Опис українською",
    "description_en": "Description in English",
    "description_ru": "Описание на русском"
}

# Кнопка (з translations)
Translation(key="share_button", lang="uk", text="Поділитися")
Translation(key="share_button", lang="en", text="Share")
```

