import urllib.request
import json
import ssl
import sys

# Configuration
API_BASE = "https://api-production-57e8.up.railway.app/api/v1"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
TARGET_EXTERNAL_ID = "380927579"

def make_request(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error requesting {url}: {e}")
        return None

def main():
    print(f"--- Remote Debugger for User {TARGET_EXTERNAL_ID} ---")
    
    # 1. Find User UUID via Messages
    print("1. Searching for User UUID in recent messages...")
    messages_url = f"{API_BASE}/admin/bots/{BOT_ID}/messages?limit=1000"
    messages = make_request(messages_url)
    
    if not messages:
        print("Failed to fetch messages.")
        return

    user_uuid = None
    for msg in messages:
        if str(msg.get('external_id')) == TARGET_EXTERNAL_ID:
            user_uuid = msg.get('user_id')
            print(f"   Found User UUID: {user_uuid}")
            print(f"   User Info: {msg.get('first_name')} {msg.get('last_name')} (@{msg.get('username')})")
            break
            
    if not user_uuid:
        print("   User NOT found in recent messages. Cannot proceed without UUID.")
        return

    # 2. Call Debug Endpoint
    print(f"\n2. Calling Debug Endpoint for UUID {user_uuid}...")
    debug_url = f"{API_BASE}/admin/bots/{BOT_ID}/users/{user_uuid}/debug-referrals"
    debug_data = make_request(debug_url)
    
    if debug_data:
        print("\n--- DEBUG RESULTS ---")
        print(json.dumps(debug_data, indent=2, ensure_ascii=False))
        
        counts = debug_data.get('counts', {})
        print("\n--- ANALYSIS ---")
        print(f"Stored Count (User.custom_data): {counts.get('stored_total_invited')}")
        print(f"Active Logs (DB):               {counts.get('raw_active_logs_count')}")
        print(f"Deleted Logs (DB):              {counts.get('raw_deleted_logs_count')}")
        
        if counts.get('stored_total_invited') != counts.get('raw_active_logs_count'):
            print("\n❌ DISCREPANCY DETECTED!")
            print("The stored count in User table does NOT match the actual number of active referral logs.")
            print("This confirms the counter is not updating correctly or was manually reset without clearing logs.")
        else:
            print("\n✅ Counts match. The counter reflects the database state.")
            
    else:
        print("Failed to fetch debug data.")

if __name__ == "__main__":
    main()
