#!/usr/bin/env python3
"""
Test script to send a Telegram webhook update with referral parameter.
This simulates a real user clicking a referral link.
"""
import requests
import json
import sys
import time
from datetime import datetime

# Configuration
API_BASE = "https://api-production-57e8.up.railway.app"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
INVITER_EXTERNAL_ID = "8144081672"

# Generate a unique test user external_id
TEST_USER_EXTERNAL_ID = f"test_referral_{int(time.time())}"

def get_bot_token():
    """Get bot token from admin API"""
    try:
        response = requests.get(
            f"{API_BASE}/api/v1/admin/bots/{BOT_ID}",
            verify=False,
            timeout=10
        )
        if response.status_code == 200:
            bot_data = response.json()
            # Token might be hidden for security, try to get it
            if 'token' in bot_data:
                return bot_data['token']
            print("⚠️  Bot token not in response (hidden for security)")
            print("   Trying to use a placeholder - webhook will fail but we can check logs")
            return "PLACEHOLDER_TOKEN"
        else:
            print(f"❌ Failed to get bot: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting bot: {e}")
        return None

def create_webhook_update(inviter_external_id: str, test_user_id: str):
    """Create a Telegram webhook update object"""
    return {
        "update_id": int(time.time()),
        "message": {
            "message_id": int(time.time()),
            "from": {
                "id": int(test_user_id.split("_")[-1]) if "_" in test_user_id else 999999999,
                "is_bot": False,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "language_code": "uk"
            },
            "chat": {
                "id": int(test_user_id.split("_")[-1]) if "_" in test_user_id else 999999999,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "type": "private"
            },
            "date": int(time.time()),
            "text": f"/start {inviter_external_id}",
            "entities": [
                {
                    "offset": 0,
                    "length": 6,
                    "type": "bot_command"
                }
            ]
        }
    }

def send_webhook(bot_token: str, update: dict):
    """Send webhook to Telegram endpoint"""
    url = f"{API_BASE}/api/v1/webhooks/telegram/{bot_token}"
    
    print(f"\n📤 Sending webhook to: {url}")
    print(f"   Update: /start {INVITER_EXTERNAL_ID}")
    print(f"   Test user: {TEST_USER_EXTERNAL_ID}")
    
    try:
        response = requests.post(
            url,
            json=update,
            verify=False,
            timeout=30
        )
        
        print(f"\n📥 Response: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Webhook accepted: {response.json()}")
            return True
        else:
            print(f"   ❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def check_user_total_invited():
    """Check inviter's total_invited count"""
    url = f"{API_BASE}/api/v1/admin/bots/{BOT_ID}/users"
    params = {"external_id": INVITER_EXTERNAL_ID}
    
    try:
        response = requests.get(url, params=params, verify=False, timeout=10)
        if response.status_code == 200:
            users = response.json()
            if users and len(users) > 0:
                user = users[0]
                total_invited = user.get('custom_data', {}).get('total_invited', 'N/A')
                return total_invited
        return None
    except Exception as e:
        print(f"❌ Error checking user: {e}")
        return None

def main():
    print("🧪 Testing Telegram Webhook with Referral Parameter")
    print("=" * 60)
    
    # Step 1: Get current total_invited
    print("\n📊 Step 1: Checking current total_invited...")
    initial_count = check_user_total_invited()
    if initial_count is not None:
        print(f"   ✅ Current total_invited: {initial_count}")
    else:
        print("   ⚠️  Could not get current count")
        initial_count = 0
    
    # Step 2: Get bot token
    print("\n🔑 Step 2: Getting bot token...")
    bot_token = get_bot_token()
    if not bot_token:
        print("   ❌ Could not get bot token")
        return
    
    # Step 3: Create webhook update
    print("\n📝 Step 3: Creating webhook update...")
    update = create_webhook_update(INVITER_EXTERNAL_ID, TEST_USER_EXTERNAL_ID)
    print(f"   ✅ Update created: {json.dumps(update, indent=2)[:200]}...")
    
    # Step 4: Send webhook
    print("\n🚀 Step 4: Sending webhook...")
    success = send_webhook(bot_token, update)
    
    if success:
        print("\n⏳ Step 5: Waiting 10 seconds for background task to complete...")
        time.sleep(10)
        
        # Step 5: Check updated total_invited
        print("\n📊 Step 6: Checking updated total_invited...")
        final_count = check_user_total_invited()
        if final_count is not None:
            print(f"   ✅ Final total_invited: {final_count}")
            if final_count > initial_count:
                print(f"   🎉 SUCCESS! Counter increased from {initial_count} to {final_count}")
            else:
                print(f"   ⚠️  Counter did not increase (still {final_count})")
        else:
            print("   ⚠️  Could not get updated count")
    else:
        print("\n❌ Webhook failed, cannot test counter update")
    
    print("\n" + "=" * 60)
    print("✅ Test completed")

if __name__ == "__main__":
    main()

