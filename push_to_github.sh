#!/bin/bash
# Скрипт для завантаження коду в GitHub

echo "🚀 Завантаження коду в GitHub..."
echo ""

# Перевірка чи є remote
if git remote | grep -q origin; then
    echo "⚠️  Remote 'origin' вже існує"
    echo "   Видалити? (y/n)"
    read -r answer
    if [ "$answer" = "y" ]; then
        git remote remove origin
    else
        echo "❌ Скасовано"
        exit 1
    fi
fi

echo "📋 Введи назву GitHub репозиторію:"
echo "   Формат: username/repo-name"
read -r REPO_NAME

if [ -z "$REPO_NAME" ]; then
    echo "❌ Назва репозиторію не вказана"
    exit 1
fi

# Додати remote (токен треба вказати вручну або через змінну оточення)
# GITHUB_TOKEN з змінної оточення або вкажи вручну
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  GITHUB_TOKEN не встановлено"
    echo "   Вкажи токен: export GITHUB_TOKEN=твій-токен"
    echo "   Або додай remote вручну: git remote add origin https://github.com/\${REPO_NAME}.git"
    exit 1
fi
git remote add origin "https://${GITHUB_TOKEN}@github.com/${REPO_NAME}.git"

echo ""
echo "📤 Завантаження коду..."
git branch -M main
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Код завантажено в GitHub!"
    echo "🔗 Репозиторій: https://github.com/${REPO_NAME}"
    echo ""
    echo "📋 Наступний крок:"
    echo "   1. Відкрий Railway: https://railway.app/project/46aa6dc7-1bb1-49b7-ac65-e9a8ac73636a"
    echo "   2. Сервіс 'api' → Settings → Source"
    echo "   3. Натисни 'Connect GitHub'"
    echo "   4. Виберіть репозиторій: ${REPO_NAME}"
    echo "   5. Railway автоматично задеплоїть"
else
    echo ""
    echo "❌ Помилка при завантаженні"
    echo "   Перевір:"
    echo "   - Чи репозиторій створено на GitHub"
    echo "   - Чи токен правильний"
    echo "   - Чи маєш права доступу"
fi

