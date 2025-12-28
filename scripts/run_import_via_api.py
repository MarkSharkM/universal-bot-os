#!/usr/bin/env python3
"""
Script to trigger data import via API endpoint
"""
import sys
import httpx
import time
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

API_URL = "https://api-production-57e8.up.railway.app"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"  # Active EarnHubAggregatorBot


def trigger_import(import_type: str = "all"):
    """Trigger import via API"""
    url = f"{API_URL}/api/v1/admin/bots/{BOT_ID}/import-data"
    
    print(f"🚀 Triggering import: {import_type}")
    print(f"📡 URL: {url}")
    print()
    
    try:
        response = httpx.post(
            url,
            params={"import_type": import_type},
            timeout=300.0  # 5 minutes timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Import successful!")
            print(f"Bot: {result.get('bot_name')}")
            print(f"Type: {result.get('import_type')}")
            print("\nResults:")
            for key, value in result.get('results', {}).items():
                print(f"  {key}: {value}")
            return True
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except httpx.TimeoutException:
        print("⏱️  Request timeout - import might still be running")
        print("💡 Check Railway logs for progress")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    import_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    print("=" * 60)
    print("📥 Data Import via API")
    print("=" * 60)
    print()
    
    # Wait a bit for deployment
    print("⏳ Waiting for deployment to complete...")
    time.sleep(10)
    
    # Try import
    success = trigger_import(import_type)
    
    if not success:
        print("\n💡 If endpoint not found, wait a bit more for deployment")
        print("   Or run manually: railway run python scripts/import_all_data.py --bot-name EarnHubAggregatorBot")

