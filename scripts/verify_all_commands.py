import urllib.request
import json
import ssl
import time
import urllib.parse

# Configuration
API_BASE = "https://api-production-57e8.up.railway.app"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
USER_EXTERNAL_ID = "test_user_v2"
SOURCE = "mini_app_verification"
TEST_ENDPOINT_TEMPLATE = "{api_base}/api/v1/admin/bots/{bot_id}/test-command?command={command}&user_lang={lang}&user_external_id={user_id}&source={source}"

COMMANDS = [
    "/start",
    "/wallet",
    "/partners",
    "/top",
    "/share",
    "/earnings",
    "/info"
]

LANGUAGES = ["uk", "en"]

def make_request(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    print(f"Testing URL: {url}")
    req = urllib.request.Request(url, method="POST")
    req.add_header('User-Agent', 'MiniAppVerifyScript/2.0')
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            status = response.getcode()
            body = json.loads(response.read().decode())
            return status, body
    except Exception as e:
        return 500, str(e)

def main():
    print("🚀 Starting Extended Command Verification...")
    results = {}
    
    # 1. Multi-language Command Test
    for lang in LANGUAGES:
        print(f"\n🌍 Testing Language: {lang.upper()}")
        for cmd in COMMANDS:
            encoded_cmd = urllib.parse.quote(cmd)
            url = TEST_ENDPOINT_TEMPLATE.format(
                api_base=API_BASE,
                bot_id=BOT_ID, 
                command=encoded_cmd, 
                user_id=USER_EXTERNAL_ID,
                lang=lang,
                source=SOURCE
            )
            status, response = make_request(url)
            
            # Extract messsage safely
            msg = "No response"
            if isinstance(response, dict):
                 msg = response.get('response', {}).get('message', '') or ''
            
            key = f"{cmd}_{lang}"
            results[key] = {
                "status": status,
                "lang": lang,
                "response_preview": str(msg)[:50] + "..."
            }
            print(f"   [{cmd}] Status: {status}")
            time.sleep(0.5)

    # 2. Referral Logic Test
    print("\n🔗 Testing Referral Logic (/start 123)...")
    cmd = "/start 123"
    encoded_cmd = urllib.parse.quote(cmd)
    url = TEST_ENDPOINT_TEMPLATE.format(
        api_base=API_BASE,
        bot_id=BOT_ID, 
        command=encoded_cmd, 
        user_id=USER_EXTERNAL_ID,
        lang="uk",
        source=SOURCE
    )
    status, response = make_request(url)
    
    msg = "No response"
    if isinstance(response, dict):
            msg = response.get('response', {}).get('message', '') or ''
            
    results["referral_test"] = {
        "status": status,
        "input": cmd,
        "response_preview": str(msg)[:50] + "..."
    }
    print(f"   [{cmd}] Status: {status}")

    print("\n📊 VERIFICATION SUMMARY:")
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
