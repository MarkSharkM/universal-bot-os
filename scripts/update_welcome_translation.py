#!/usr/bin/env python3
"""
Update welcome translation to replace hardcoded username with placeholder.
"""
import httpx

API_URL = "https://api-production-57e8.up.railway.app"
langs = ['uk', 'en', 'ru', 'de', 'es']

updates = {
    'HubAggregatorBot': '{{bot_username}}',
    '@HubAggregatorBot': '@{{bot_username}}',
    'EarnHubAggregatorBot': '{{bot_username}}',
    '@EarnHubAggregatorBot': '@{{bot_username}}',
}

for lang in langs:
    try:
        # Get current translation
        r = httpx.get(f"{API_URL}/api/v1/admin/translations?key=welcome&lang={lang}", timeout=30)
        if r.status_code != 200:
            print(f"⚠️  Could not fetch welcome ({lang})")
            continue
        
        data = r.json()
        if not data:
            print(f"⚠️  No translation found for welcome ({lang})")
            continue
        
        translation = data[0]
        original_text = translation.get('text', '')
        
        if 'HubAggregatorBot' not in original_text and 'EarnHubAggregatorBot' not in original_text:
            print(f"ℹ️  welcome ({lang}) already updated")
            continue
        
        # Replace hardcoded username
        new_text = original_text
        for old, new in updates.items():
            new_text = new_text.replace(old, new)
        
        if new_text == original_text:
            print(f"ℹ️  welcome ({lang}) no changes needed")
            continue
        
        # Update translation
        r = httpx.put(
            f"{API_URL}/api/v1/admin/translations/welcome/{lang}",
            params={'text': new_text},
            timeout=30
        )
        
        if r.status_code == 200:
            print(f"✅ Updated welcome ({lang})")
            print(f"   OLD: {original_text[:80]}...")
            print(f"   NEW: {new_text[:80]}...")
        else:
            print(f"❌ Failed to update welcome ({lang}): {r.status_code}")
    except Exception as e:
        print(f"❌ Error updating welcome ({lang}): {e}")
