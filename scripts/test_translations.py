#!/usr/bin/env python3
"""
Test translation system - check if all translations work correctly
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.services.translation_service import TranslationService

# Test cases
TEST_CASES = [
    {
        "key": "welcome",
        "langs": ["uk", "en", "ru", "de", "es"],
        "variables": None
    },
    {
        "key": "wallet_help",
        "langs": ["uk", "en", "ru"],
        "variables": None
    },
    {
        "key": "wallet_info_saved",
        "langs": ["uk", "en"],
        "variables": {"wallet": "EQCwz3GkW9hkGkB3Dxvkdsi8IzUxxxxxxxxxxxxxxxxxxxxxxx"}
    },
    {
        "key": "earnings_has_income",
        "langs": ["uk", "en"],
        "variables": {"wallet": "EQ123...", "earned": 4.0}
    },
    {
        "key": "share_referral",
        "langs": ["uk", "en"],
        "variables": {"referralLink": "https://t.me/HubAggregatorBot?start=123"}
    },
    {
        "key": "partners_intro",  # Може бути відсутній
        "langs": ["uk", "en"],
        "variables": None
    },
    {
        "key": "top_locked_message",  # Може бути відсутній
        "langs": ["uk", "en"],
        "variables": {"needed": 2}
    },
    {
        "key": "nonexistent_key_12345",  # Не існує
        "langs": ["uk", "en"],
        "variables": None
    },
]

def test_translation_system():
    """Test translation system"""
    db = SessionLocal()
    translation_service = TranslationService(db)
    
    print("🧪 Testing Translation System")
    print("="*70)
    
    results = []
    
    for test_case in TEST_CASES:
        key = test_case["key"]
        print(f"\n📝 Testing key: {key}")
        
        for lang in test_case["langs"]:
            variables = test_case.get("variables")
            
            # Test language detection
            detected = translation_service.detect_language(lang)
            print(f"  Language detection: {lang} -> {detected}")
            
            # Get translation
            translation = translation_service.get_translation(key, detected, variables)
            
            # Check result
            if translation == key:
                status = "❌ NOT FOUND (returned key)"
            elif translation.startswith("{{") or translation.startswith("[["):
                status = "⚠️  VARIABLE NOT SUBSTITUTED"
            else:
                status = "✅ OK"
            
            print(f"    {lang:2} -> {status}")
            if status == "✅ OK":
                print(f"      Preview: {translation[:60]}...")
            elif status == "⚠️  VARIABLE NOT SUBSTITUTED":
                print(f"      Text: {translation[:60]}...")
            
            results.append({
                "key": key,
                "lang": lang,
                "status": status,
                "translation": translation
            })
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY")
    print(f"{'='*70}")
    
    ok = sum(1 for r in results if r["status"] == "✅ OK")
    not_found = sum(1 for r in results if r["status"] == "❌ NOT FOUND (returned key)")
    not_substituted = sum(1 for r in results if r["status"] == "⚠️  VARIABLE NOT SUBSTITUTED")
    total = len(results)
    
    print(f"Total tests: {total}")
    print(f"✅ OK: {ok}")
    print(f"❌ Not found: {not_found}")
    print(f"⚠️  Variable not substituted: {not_substituted}")
    print(f"Success rate: {ok/total*100:.1f}%")
    
    # Check fallback
    print(f"\n{'='*70}")
    print("🔄 Testing Fallback Chain")
    print(f"{'='*70}")
    
    # Test with non-existent key
    test_key = "nonexistent_key_test_12345"
    for lang in ["fr", "zh", "ja"]:  # Unsupported languages
        detected = translation_service.detect_language(lang)
        translation = translation_service.get_translation(test_key, detected)
        print(f"  {lang} -> {detected} -> translation: '{translation}'")
        if translation == test_key:
            print(f"    ✅ Correctly returned key (no translation found)")
        else:
            print(f"    ⚠️  Unexpected: got translation instead of key")
    
    db.close()
    
    if not_found > 0 or not_substituted > 0:
        print(f"\n⚠️  Some issues found!")
        return 1
    else:
        print(f"\n✅ All tests passed!")
        return 0

if __name__ == "__main__":
    exit(test_translation_system())

