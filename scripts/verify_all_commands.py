import urllib.request
import json
import ssl
import time

# Configuration from HOW_TO_VIEW_LOGS.md
API_BASE = "https://api-production-57e8.up.railway.app"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
USER_EXTERNAL_ID = "test_user_v2"
TEST_ENDPOINT_TEMPLATE = "https://api-production-57e8.up.railway.app/api/v1/admin/bots/{bot_id}/test-command?command={command}&user_lang=uk&user_external_id={user_id}"

COMMANDS = [
    "/start",
    "/wallet",
    "/partners",
    "/top",
    "/share",
    "/earnings",
    "/info"
]

def make_request(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    print(f"Testing URL: {url}")
    req = urllib.request.Request(url, method="POST")
    # Add dummy headers to simulate browser/app
    req.add_header('User-Agent', 'MiniAppVerifyScript/1.0')
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            status = response.getcode()
            body = json.loads(response.read().decode())
            return status, body
    except Exception as e:
        return 500, str(e)

def main():
    print("🚀 Starting Comprehensive Command Verification...")
    results = {}
    
    for cmd in COMMANDS:
        # Use quote to handle / and other characters in command
        import urllib.parse
        encoded_cmd = urllib.parse.quote(cmd)
        url = TEST_ENDPOINT_TEMPLATE.format(bot_id=BOT_ID, command=encoded_cmd, user_id=USER_EXTERNAL_ID)
        status, response = make_request(url)
        results[cmd] = {
            "status": status,
            "success": status == 200,
            "response_preview": str(response)[:100] + "..." if isinstance(response, str) else response
        }
        print(f"   [{cmd}] Status: {status}")
        time.sleep(1) # Small delay to separate logs
        
    print("\n📊 VERIFICATION SUMMARY:")
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
