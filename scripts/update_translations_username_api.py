#!/usr/bin/env python3
"""
Script to update translations via API: replace hardcoded username with {{bot_username}} placeholder.

Usage:
    python scripts/update_translations_username_api.py [API_URL]
    
Example:
    python scripts/update_translations_username_api.py https://api-production-57e8.up.railway.app
"""
import sys
import httpx
import json
from urllib.parse import quote

# Default API URL
DEFAULT_API_URL = "https://api-production-57e8.up.railway.app"

def update_translations(api_url: str = DEFAULT_API_URL):
    """Update translations via API to replace hardcoded username with placeholder"""
    
    # Get all translations
    print(f"📥 Fetching translations from {api_url}...")
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{api_url}/api/v1/admin/translations")
            response.raise_for_status()
            translations = response.json()
        print(f"✅ Found {len(translations)} translations")
    except Exception as e:
        print(f"❌ Error fetching translations: {e}")
        return False
    
    # Find translations with hardcoded username
    updates = {
        'HubAggregatorBot': '{{bot_username}}',
        '@HubAggregatorBot': '@{{bot_username}}',
        'EarnHubAggregatorBot': '{{bot_username}}',
        '@EarnHubAggregatorBot': '@{{bot_username}}',
    }
    
    translations_to_update = []
    for translation in translations:
        text = translation.get('text', '')
        if 'HubAggregatorBot' in text or 'EarnHubAggregatorBot' in text:
            translations_to_update.append(translation)
    
    print(f"\n📋 Found {len(translations_to_update)} translations with hardcoded username:")
    for t in translations_to_update:
        print(f"  - {t['key']} ({t['lang']})")
    
    if not translations_to_update:
        print("ℹ️  No translations need updating")
        return True
    
    # Update each translation
    updated_count = 0
    failed_count = 0
    
    print(f"\n🔄 Updating translations...")
    for translation in translations_to_update:
        key = translation['key']
        lang = translation['lang']
        original_text = translation['text']
        new_text = original_text
        
        # Replace all occurrences
        for old, new in updates.items():
            new_text = new_text.replace(old, new)
        
        if new_text != original_text:
            try:
                # Update via API
                url = f"{api_url}/api/v1/admin/translations/{key}/{lang}"
                # URL encode the text parameter
                params = {'text': new_text}
                with httpx.Client(timeout=30.0) as client:
                    response = client.put(url, params=params)
                    response.raise_for_status()
                
                updated_count += 1
                print(f"  ✅ Updated {key} ({lang})")
                print(f"     OLD: {original_text[:80]}...")
                print(f"     NEW: {new_text[:80]}...")
            except Exception as e:
                failed_count += 1
                print(f"  ❌ Failed to update {key} ({lang}): {e}")
    
    print(f"\n📊 Summary:")
    print(f"  ✅ Successfully updated: {updated_count}")
    if failed_count > 0:
        print(f"  ❌ Failed: {failed_count}")
    
    return failed_count == 0


if __name__ == '__main__':
    api_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_API_URL
    print(f"🚀 Updating translations via API: {api_url}\n")
    success = update_translations(api_url)
    sys.exit(0 if success else 1)
