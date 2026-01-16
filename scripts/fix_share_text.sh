#!/bin/bash
# Script to update share text translations via API

API_BASE="https://api-production-57e8.up.railway.app/api/v1/admin"

# Function to update translation
update_translation() {
    local key=$1
    local lang=$2
    local text=$3
    
    echo "Updating $key ($lang)..."
    curl -k -X PUT "${API_BASE}/translations/${key}/${lang}?text=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$text'''))")" | python3 -m json.tool
    echo ""
}

echo "🔄 Updating share text translations..."
echo ""

# Update share_text_pro
update_translation "share_text_pro" "uk" "🚀 Долучайся до EarnHubAggregatorBot — отримуй зірки за активність!"
update_translation "share_text_pro" "en" "🚀 Join EarnHubAggregatorBot — earn Stars for your activity!"
update_translation "share_text_pro" "ru" "🚀 Присоединяйся к EarnHubAggregatorBot — получай звёзды за активность!"
update_translation "share_text_pro" "de" "🚀 Tritt EarnHubAggregatorBot bei — sammle Stars für deine Aktivität!"
update_translation "share_text_pro" "es" "🚀 ¡Únete a EarnHubAggregatorBot — gana Stars por tu actividad!"

# Update share_text_starter (same as pro)
update_translation "share_text_starter" "uk" "🚀 Долучайся до EarnHubAggregatorBot — отримуй зірки за активність!"
update_translation "share_text_starter" "en" "🚀 Join EarnHubAggregatorBot — earn Stars for your activity!"
update_translation "share_text_starter" "ru" "🚀 Присоединяйся к EarnHubAggregatorBot — получай звёзды за активность!"
update_translation "share_text_starter" "de" "🚀 Tritt EarnHubAggregatorBot bei — sammle Stars für deine Aktivität!"
update_translation "share_text_starter" "es" "🚀 ¡Únete a EarnHubAggregatorBot — gana Stars por tu actividad!"

echo "✅ Done!"
