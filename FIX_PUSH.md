# 🔧 Виправлення git push

## Проблема:
```
remote: Invalid username or token. Password authentication is not supported for Git operations.
```

## Рішення:

### Варіант 1: Використати GitHub CLI (gh)

```bash
# Встанови GitHub CLI (якщо немає)
brew install gh

# Авторизуйся
gh auth login

# Push
git push
```

### Варіант 2: Оновити токен в Git credential helper

```bash
cd ~/Desktop/mark/railway-mcp-project/universal-bot-os

# Видали старий credential
git credential-osxkeychain erase
host=github.com
protocol=https

# Push з новим токеном
git push
# Username: MarkSharkM
# Password: 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
```

### Варіант 3: Використати SSH (найнадійніше)

```bash
# 1. Створи SSH ключ (якщо немає)
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. Додай ключ в GitHub
cat ~/.ssh/id_ed25519.pub
# Скопіюй і додай в GitHub → Settings → SSH keys

# 3. Зміни remote на SSH
git remote set-url origin git@github.com:MarkSharkM/universal-bot-os.git

# 4. Push
git push
```

### Варіант 4: Через GitHub Desktop

1. Встанови GitHub Desktop
2. Відкрий репозиторій
3. Натисни "Push origin"

---

## ⚡ Швидке рішення:

Спробуй через GitHub CLI:

```bash
brew install gh
gh auth login
cd ~/Desktop/mark/railway-mcp-project/universal-bot-os
git push
```

---

**Альтернатива:** Railway може автоматично підхопити зміни, якщо GitHub webhook налаштовано. Просто зачекай кілька хвилин.

