#!/usr/bin/env python3
"""
Test wallet saving via API (simulating Telegram webhook)
Tests various wallet address formats and validation
"""
import requests
import json
import time
from datetime import datetime

API_BASE = "https://api-production-57e8.up.railway.app"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
TEST_USER_EXTERNAL_ID = "test_wallet_api_user"

# Test cases
TEST_CASES = [
    {
        "name": "Valid EQ wallet",
        "address": "EQCwz3GkW9hkGkB3Dxvkdsi8IzUxxxxxxxxxxxxxxxxxxxxxxx",
        "should_save": True,
    },
    {
        "name": "Valid UQ wallet (real user's)",
        "address": "UQCFzwaYyii9HdAqAsKsW7T2VSmTnGQWVgBAKn9vdIQhg2zC",
        "should_save": True,
    },
    {
        "name": "Valid kQ wallet",
        "address": "kQCwz3GkW9hkGkB3Dxvkdsi8IzUxxxxxxxxxxxxxxxxxxxxxxx",
        "should_save": True,
    },
    {
        "name": "Valid 0Q wallet",
        "address": "0QCwz3GkW9hkGkB3Dxvkdsi8IzUxxxxxxxxxxxxxxxxxxxxxxx",
        "should_save": True,
    },
    {
        "name": "Wallet with spaces",
        "address": "  UQCFzwaYyii9HdAqAsKsW7T2VSmTnGQWVgBAKn9vdIQhg2zC  ",
        "should_save": True,
    },
    {
        "name": "Invalid - too short",
        "address": "UQCFzwaYyii9HdAqAsKsW7T2VSmTnGQWVgBAKn9vdIQhg2z",
        "should_save": False,
    },
    {
        "name": "Invalid - too long",
        "address": "UQCFzwaYyii9HdAqAsKsW7T2VSmTnGQWVgBAKn9vdIQhg2zCC",
        "should_save": False,
    },
    {
        "name": "Invalid - wrong prefix",
        "address": "ABCwz3GkW9hkGkB3Dxvkdsi8IzUxxxxxxxxxxxxxxxxxxxxxxx",
        "should_save": False,
    },
    {
        "name": "Invalid - contains @",
        "address": "UQCFzwaYyii9HdAqAsKsW7T2VSmTnGQWVgBAKn9vdIQhg2z@",
        "should_save": False,
    },
]


def simulate_telegram_webhook(text: str, external_id: str = TEST_USER_EXTERNAL_ID):
    """Simulate Telegram webhook message"""
    webhook_url = f"{API_BASE}/api/v1/webhooks/telegram/{BOT_ID}"
    
    payload = {
        "message": {
            "message_id": int(time.time()),
            "from": {
                "id": int(external_id) if external_id.isdigit() else 123456789,
                "is_bot": False,
                "first_name": "Test",
                "username": "test_user"
            },
            "chat": {
                "id": int(external_id) if external_id.isdigit() else 123456789,
                "type": "private"
            },
            "date": int(time.time()),
            "text": text
        }
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code, response.text
    except Exception as e:
        return None, str(e)


def get_user_wallet(external_id: str):
    """Get user wallet from API"""
    url = f"{API_BASE}/api/v1/admin/bots/{BOT_ID}/users"
    params = {"external_id": external_id}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                user = data[0]
                wallet = user.get('wallet_address', '')
                custom_data = user.get('custom_data', {})
                wallet_from_custom = custom_data.get('wallet_address', '')
                return wallet or wallet_from_custom
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


def test_wallet_case(test_case: dict):
    """Test a single wallet case"""
    print(f"\n{'='*70}")
    print(f"🧪 Testing: {test_case['name']}")
    print(f"Address: {test_case['address']}")
    print(f"Expected: {'SAVE ✅' if test_case['should_save'] else 'REJECT ❌'}")
    
    # Send wallet address via webhook
    status_code, response_text = simulate_telegram_webhook(test_case['address'])
    
    if status_code is None:
        print(f"❌ Error sending webhook: {response_text}")
        return {'success': False, 'error': response_text}
    
    print(f"Webhook response: {status_code}")
    if status_code != 200:
        print(f"Response text: {response_text[:200]}")
    
    # Wait a bit for processing
    time.sleep(2)
    
    # Check if wallet was saved
    wallet_address_clean = test_case['address'].strip()
    saved_wallet = get_user_wallet(TEST_USER_EXTERNAL_ID)
    
    print(f"Wallet in DB: {saved_wallet}")
    print(f"Expected: {wallet_address_clean if test_case['should_save'] else '(none)'}")
    
    # Evaluate
    if test_case['should_save']:
        success = saved_wallet == wallet_address_clean
        status = "✅ PASS" if success else "❌ FAIL"
        if not success:
            print(f"  Expected wallet to be saved, but got: {saved_wallet}")
    else:
        success = saved_wallet != wallet_address_clean
        status = "✅ PASS" if success else "❌ FAIL"
        if not success:
            print(f"  Expected wallet to be rejected, but it was saved: {saved_wallet}")
    
    print(f"Result: {status}")
    
    return {
        'test_case': test_case['name'],
        'success': success,
        'saved_wallet': saved_wallet,
        'expected': wallet_address_clean if test_case['should_save'] else None
    }


def main():
    """Run all wallet tests"""
    print("🧪 Testing Wallet Saving via API")
    print(f"Bot ID: {BOT_ID}")
    print(f"Test User: {TEST_USER_EXTERNAL_ID}")
    print(f"API Base: {API_BASE}")
    
    results = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}]")
        try:
            result = test_wallet_case(test_case)
            results.append(result)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'test_case': test_case['name'],
                'success': False,
                'error': str(e)
            })
        
        # Small delay between tests
        if i < len(TEST_CASES):
            time.sleep(1)
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 TEST SUMMARY")
    print(f"{'='*70}")
    
    passed = sum(1 for r in results if r.get('success', False))
    total = len(results)
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    print(f"\n{'='*70}")
    print("Detailed Results:")
    for result in results:
        status = "✅" if result.get('success', False) else "❌"
        print(f"{status} {result['test_case']}")
        if not result.get('success', False):
            if result.get('error'):
                print(f"   Error: {result['error']}")
            else:
                print(f"   Saved: {result.get('saved_wallet')}")
                print(f"   Expected: {result.get('expected')}")
    
    # Exit with error code if any test failed
    if passed < total:
        print(f"\n❌ Some tests failed!")
        exit(1)
    else:
        print(f"\n✅ All tests passed!")
        exit(0)


if __name__ == "__main__":
    main()

