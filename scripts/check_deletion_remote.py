import urllib.request
import json
import ssl

# Configuration
API_BASE = "https://api-production-57e8.up.railway.app/api/v1"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
TARGET_USER_UUID = "d420e0b9-5c33-4efc-a781-e13260b870c7"

def make_request(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        # 404 might be expected if checking a specific resource, but here we query a list
        print(f"HTTP Error {e.code}: {e.read().decode()}")
        return None
    except Exception as e:
        print(f"Error requesting {url}: {e}")
        return None

def main():
    print(f"--- Verifying Deletion of User {TARGET_USER_UUID} ---")
    
    # Check by querying users list with user_id filter
    url = f"{API_BASE}/admin/bots/{BOT_ID}/users?user_id={TARGET_USER_UUID}"
    print(f"Querying: {url}")
    
    users = make_request(url)
    
    if isinstance(users, list):
        if len(users) == 0:
            print("\n✅ VERIFIED: User NOT found in database.")
            print("The API returned an empty list for this User UUID.")
        else:
            print(f"\n❌ WARNING: User FOUND! ({len(users)} records)")
            print(json.dumps(users, indent=2, ensure_ascii=False))
    else:
        print("\n❌ Error checking user status.")

if __name__ == "__main__":
    main()
