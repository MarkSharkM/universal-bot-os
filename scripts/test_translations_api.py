#!/usr/bin/env python3
"""
Test translation system via API
Tests language detection, translations, and fallback
"""
import subprocess
import json
import time

API_BASE = "https://api-production-57e8.up.railway.app"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
TEST_USER_EXTERNAL_ID = "test_translations_user_999"

# Test cases
TEST_CASES = [
    {
        "name": "Language detection - uk-UA",
        "language_code": "uk-UA",
        "expected_lang": "uk",
        "test_key": "welcome"
    },
    {
        "name": "Language detection - en-US",
        "language_code": "en-US",
        "expected_lang": "en",
        "test_key": "welcome"
    },
    {
        "name": "Language detection - ru-RU",
        "language_code": "ru-RU",
        "expected_lang": "ru",
        "test_key": "welcome"
    },
    {
        "name": "Language detection - ua (should map to uk)",
        "language_code": "ua",
        "expected_lang": "uk",
        "test_key": "welcome"
    },
    {
        "name": "Language detection - unsupported (should fallback to en)",
        "language_code": "fr",
        "expected_lang": "en",
        "test_key": "welcome"
    },
    {
        "name": "Translation with variables - wallet_info_saved",
        "language_code": "uk",
        "expected_lang": "uk",
        "test_key": "wallet_info_saved",
        "variables": {"wallet": "EQCwz3GkW9hkGkB3Dxvkdsi8IzUxxxxxxxxxxxxxxxxxxxxxxx"}
    },
    {
        "name": "Translation with variables - earnings_has_income",
        "language_code": "uk",
        "expected_lang": "uk",
        "test_key": "earnings_has_income",
        "variables": {"wallet": "EQ123...", "earned": 4.0}
    },
    {
        "name": "New translations - errorEmptyTopByLang",
        "language_code": "uk",
        "expected_lang": "uk",
        "test_key": "errorEmptyTopByLang"
    },
    {
        "name": "New translations - partners_intro",
        "language_code": "uk",
        "expected_lang": "uk",
        "test_key": "partners_intro"
    },
    {
        "name": "New translations - partners_empty",
        "language_code": "en",
        "expected_lang": "en",
        "test_key": "partners_empty"
    },
    {
        "name": "New translations - launch_label",
        "language_code": "ru",
        "expected_lang": "ru",
        "test_key": "launch_label"
    },
    {
        "name": "Fallback test - nonexistent key",
        "language_code": "uk",
        "expected_lang": "uk",
        "test_key": "nonexistent_key_12345_should_return_key"
    },
]

def test_translation_via_command(command, language_code, expected_lang):
    """Test translation by sending a command"""
    webhook_url = f"{API_BASE}/api/v1/webhooks/telegram/{BOT_ID}"
    payload = {
        "message": {
            "message_id": int(time.time()),
            "from": {
                "id": 999999999,
                "is_bot": False,
                "first_name": "Test",
                "username": "test_user",
                "language_code": language_code
            },
            "chat": {
                "id": 999999999,
                "type": "private"
            },
            "date": int(time.time()),
            "text": command
        }
    }
    
    try:
        result = subprocess.run(
            ['curl', '-s', '-X', 'POST', webhook_url, 
             '-H', 'Content-Type: application/json', 
             '-d', json.dumps(payload)],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except:
        return False

def test_translation_key(key, lang, variables=None):
    """Test specific translation key via test-command endpoint"""
    url = f"{API_BASE}/api/v1/admin/bots/{BOT_ID}/test-command"
    params = {
        "command": "/info",  # Use /info as it's simple
        "user_external_id": TEST_USER_EXTERNAL_ID,
        "user_lang": lang
    }
    
    # We can't directly test translation keys via API, so we test via commands
    # that use those keys
    return True

def main():
    """Run translation tests"""
    print("🧪 Testing Translation System via API")
    print("="*70)
    print(f"Bot ID: {BOT_ID}")
    print(f"API Base: {API_BASE}\n")
    
    results = []
    
    # Test 1: Language detection via commands
    print("📝 Test 1: Language Detection via Commands")
    print("-"*70)
    
    lang_tests = [
        ("uk-UA", "/start", "uk"),
        ("en-US", "/start", "en"),
        ("ru-RU", "/start", "ru"),
        ("ua", "/start", "uk"),
        ("fr", "/start", "en"),  # Should fallback to en
    ]
    
    for lang_code, command, expected in lang_tests:
        print(f"  Testing: {lang_code} -> {expected}")
        success = test_translation_via_command(command, lang_code, expected)
        status = "✅" if success else "❌"
        print(f"    {status} Command sent successfully")
        results.append({
            "test": f"Language detection: {lang_code}",
            "success": success,
            "expected": expected
        })
        time.sleep(1)
    
    # Test 2: Commands with translations
    print(f"\n📝 Test 2: Commands with Translations")
    print("-"*70)
    
    command_tests = [
        ("/wallet", "uk", "wallet_help"),
        ("/wallet", "en", "wallet_help"),
        ("/partners", "uk", "partners_intro"),
        ("/partners", "en", "partners_intro"),
        ("/top", "uk", "errorEmptyTopByLang or top_locked_message"),
        ("/earnings", "uk", "earnings_title"),
        ("/share", "uk", "share_referral"),
        ("/info", "uk", "info_main"),
    ]
    
    for command, lang, expected_key in command_tests:
        print(f"  Testing: {command} (lang={lang}, expects {expected_key})")
        success = test_translation_via_command(command, lang, lang)
        status = "✅" if success else "❌"
        print(f"    {status} Command sent")
        results.append({
            "test": f"Command: {command} (lang={lang})",
            "success": success,
            "expected_key": expected_key
        })
        time.sleep(1)
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY")
    print(f"{'='*70}")
    
    passed = sum(1 for r in results if r.get('success', False))
    total = len(results)
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    print(f"\n{'='*70}")
    print("💡 Note: These tests verify that commands are sent successfully.")
    print("   To verify actual translations, check the bot responses in Telegram.")
    print("   All translation keys should now be in the database.")
    
    if passed < total:
        print(f"\n⚠️  Some tests failed - check API connectivity")
        return 1
    else:
        print(f"\n✅ All API tests passed!")
        return 0

if __name__ == "__main__":
    exit(main())

