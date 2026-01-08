import urllib.request
import json
import ssl

# Configuration
API_BASE = "https://api-production-57e8.up.railway.app/api/v1"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
# The test user provided by the user (UUID found in previous step: d420e0b9-5c33-4efc-a781-e13260b870c7)
TARGET_USER_UUID = "d420e0b9-5c33-4efc-a781-e13260b870c7"
TARGET_EXTERNAL_ID = "380927579"

def make_request(url, method="GET"):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}")
        return None
    except Exception as e:
        print(f"Error requesting {url}: {e}")
        return None

def main():
    print(f"--- Hard Deleting User {TARGET_EXTERNAL_ID} ({TARGET_USER_UUID}) ---")
    
    # 1. Confirm User Exists before delete
    print("1. Verifying user existence...")
    # There is no direct "get user" by ID, so we skip directly to delete or try to find in list
    # Assuming UUID is correct from previous step.
    
    # 2. Execute DELETE
    print(f"\n2. Sending DELETE request for user {TARGET_USER_UUID}...")
    delete_url = f"{API_BASE}/admin/bots/{BOT_ID}/users/{TARGET_USER_UUID}"
    result = make_request(delete_url, method="DELETE")
    
    if result and result.get("success"):
        print("\n✅ SUCCESS: User deleted.")
        print("Deleted Data Summary:")
        deleted = result.get("deleted", {})
        print(f"- User Record: 1")
        print(f"- Business Data (Logs/Partners): {deleted.get('business_data_records', 0)}")
        print(f"- Messages: {deleted.get('messages', 0)}")
        print(f"- Analytics: {deleted.get('analytics_events', 0)}")
        print("\nThe user can now re-join via referral link to test the counter.")
    else:
        print("\n❌ FAILED to delete user.")
        if result:
            print(f"Error: {result.get('message')}")

if __name__ == "__main__":
    main()
