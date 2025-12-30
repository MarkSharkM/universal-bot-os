#!/bin/bash
# Backup bot data via API before deletion

BOT_ID="4ba166f8-01b2-416d-892e-cabf0b8a8514"
API_BASE="https://api-production-57e8.up.railway.app/api/v1/admin"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="backup_bot_${BOT_ID:0:8}_${TIMESTAMP}.json"

echo "📦 Створюю backup дубліката бота перед видаленням..."
echo ""

# Get bot info
echo "1. Отримую інформацію про бота..."
BOT_INFO=$(curl -s -k "${API_BASE}/bots/${BOT_ID}")

# Get stats
echo "2. Отримую статистику..."
STATS=$(curl -s -k "${API_BASE}/bots/${BOT_ID}/stats")

# Get partners
echo "3. Отримую партнерів..."
PARTNERS=$(curl -s -k "${API_BASE}/bots/${BOT_ID}/partners")

# Get users
echo "4. Отримую users..."
USERS=$(curl -s -k "${API_BASE}/bots/${BOT_ID}/users?limit=1000")

# Combine into backup
python3 << EOF
import json
import sys
from datetime import datetime

bot_info = json.loads('''$BOT_INFO''')
stats = json.loads('''$STATS''')
partners = json.loads('''$PARTNERS''')
users = json.loads('''$USERS''')

backup = {
    "backup_timestamp": datetime.now().isoformat(),
    "bot_id": "${BOT_ID}",
    "bot": bot_info,
    "stats": stats,
    "partners": partners,
    "users": users,
    "note": "Backup created before hard delete. Use restore script to restore if needed."
}

with open("${BACKUP_FILE}", "w", encoding="utf-8") as f:
    json.dump(backup, f, indent=2, ensure_ascii=False)

print(f"✅ Backup saved to: ${BACKUP_FILE}")
print(f"   - Bot: 1")
print(f"   - Users: {len(users)}")
print(f"   - Partners: {len(partners)}")
print(f"   - Stats: {stats}")
EOF

echo ""
echo "💾 Backup file: $(pwd)/${BACKUP_FILE}"
echo "   Можна використати для відновлення якщо потрібно."

