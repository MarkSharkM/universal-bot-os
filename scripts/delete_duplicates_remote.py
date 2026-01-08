import urllib.request
import json
import ssl
import time

# Configuration
API_BASE = "https://api-production-57e8.up.railway.app/api/v1"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
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
    print(f"--- Bulk Deleting Duplicates for External ID {TARGET_EXTERNAL_ID} ---")
    
    # 1. Find ALL matching users
    print("1. Searching for all duplicate users...")
    # Since we can't filter by external_id directly in the list endpoint efficiently (it takes user_id UUID),
    # we will fetch the list and filter client-side. 
    # Or better: search via messages if list is too huge, but user list is safer for complete cleanup.
    
    # Try fetching users (filtered by user_id not possible, so fetch page 1 and hope they are there, 
    # otherwise we might miss them if there are thousands. 
    # But wait, looking at admin.py, listing users sorts by last_activity.
    # The screenshot showed them at the top, so they must be recent.
    
    url = f"{API_BASE}/admin/bots/{BOT_ID}/users?limit=100&sort_by=last_activity"
    users = make_request(url)
    
    if not users:
        print("Failed to fetch user list.")
        return

    targets = []
    for u in users:
        if str(u.get('external_id')) == TARGET_EXTERNAL_ID:
            targets.append(u)
            
    print(f"Found {len(targets)} matching user records.")
    
    if len(targets) == 0:
        print("No users found to delete.")
        return

    # 2. Delete EACH target
    for i, target in enumerate(targets):
        uuid = target['id']
        print(f"\n[{i+1}/{len(targets)}] Deleting User UUID: {uuid}...")
        
        delete_url = f"{API_BASE}/admin/bots/{BOT_ID}/users/{uuid}"
        result = make_request(delete_url, method="DELETE")
        
        if result and result.get("success"):
            print("   ✅ Deleted successfully.")
        else:
            print("   ❌ Failed to delete.")
            
    print("\n--- Done ---")
    print("All duplicates should be gone. Please verify in Admin Panel.")

if __name__ == "__main__":
    main()
