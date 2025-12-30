#!/bin/bash
# Check bots and their partners via API

API_BASE="https://api-production-57e8.up.railway.app/api/v1/admin"

echo "🔍 Перевірка ботів та партнерів..."
echo ""

# Get all bots
echo "📋 Список ботів:"
curl -s -k "${API_BASE}/bots" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Всього ботів: {len(data)}')
for bot in data:
    print(f'  - {bot[\"name\"]} (ID: {bot[\"id\"]}, Active: {bot[\"is_active\"]})')
"

echo ""
echo "📋 Перевірка партнерів для кожного бота:"

# Get bot IDs
BOT_IDS=$(curl -s -k "${API_BASE}/bots" | python3 -c "
import sys, json
data = json.load(sys.stdin)
ids = [bot['id'] for bot in data]
print(' '.join(ids))
")

for BOT_ID in $BOT_IDS; do
    BOT_NAME=$(curl -s -k "${API_BASE}/bots/${BOT_ID}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data['name'])
" 2>/dev/null || echo "Unknown")
    
    echo ""
    echo "Bot: ${BOT_NAME} (${BOT_ID})"
    
    # Get partners
    PARTNERS=$(curl -s -k "${API_BASE}/bots/${BOT_ID}/partners")
    COUNT=$(echo "$PARTNERS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data))
except:
    print(0)
")
    
    echo "  Партнерів: $COUNT"
    
    if [ "$COUNT" -gt 0 ]; then
        echo "$PARTNERS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for p in data:
    print(f'    - {p[\"bot_name\"]} ({p[\"category\"]}, Active: {p[\"active\"]})')
"
    fi
done

