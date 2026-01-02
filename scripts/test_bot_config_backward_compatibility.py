#!/usr/bin/env python3
"""
Test Bot Config Backward Compatibility
Перевіряє що всі команди працюють як раніше з порожнім bot.config
"""
import requests
import time
import json
import sys

# Configuration
API_BASE = "https://api-production-57e8.up.railway.app"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
TEST_USER_ID = f"backward_test_{int(time.time())}"

# Commands to test
COMMANDS = [
    ("/start", "Start command"),
    ("/wallet", "Wallet command"),
    ("/partners", "Partners command"),
    ("/top", "Top partners command"),
    ("/share", "Share referral link"),
    ("/earnings", "Earnings command"),
    ("/info", "Info command"),
]

def test_command(command: str, description: str) -> dict:
    """Test a single command and check if it works"""
    url = f"{API_BASE}/api/v1/admin/bots/{BOT_ID}/test-command"
    params = {
        "command": command,
        "user_external_id": TEST_USER_ID,
        "user_lang": "uk"
    }
    
    start_time = time.time()
    try:
        response = requests.post(url, params=params, timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "command": command,
                "description": description,
                "elapsed": elapsed,
                "has_message": bool(data.get("message")),
                "has_buttons": bool(data.get("buttons")),
                "has_error": bool(data.get("error")),
                "message_preview": (data.get("message") or data.get("error", ""))[:100] if data.get("message") or data.get("error") else "No message",
                "buttons_count": len(data.get("buttons", [])),
            }
        else:
            return {
                "success": False,
                "command": command,
                "description": description,
                "elapsed": elapsed,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "command": command,
            "description": description,
            "elapsed": elapsed,
            "error": str(e),
        }

def main():
    """Test all commands for backward compatibility"""
    print("=" * 70)
    print("🔍 ТЕСТ BACKWARD COMPATIBILITY - Bot Config")
    print("=" * 70)
    print(f"Bot ID: {BOT_ID}")
    print(f"Test User: {TEST_USER_ID}")
    print(f"API: {API_BASE}")
    print("")
    print("Перевірка: Чи працюють команди з порожнім bot.config?")
    print("")
    
    results = []
    for command, description in COMMANDS:
        print(f"Testing {command:15} ({description})...", end=" ", flush=True)
        result = test_command(command, description)
        results.append(result)
        
        if result["success"]:
            status = "✅ OK"
            if result.get("has_error"):
                status = "⚠️  ERROR"
            elif not result.get("has_message"):
                status = "⚠️  NO MESSAGE"
            print(status)
        else:
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
    
    print("")
    print("=" * 70)
    print("📊 РЕЗУЛЬТАТИ")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r["success"] and not r.get("has_error") and r.get("has_message"))
    total_count = len(results)
    
    print(f"Успішних: {success_count}/{total_count}")
    print("")
    
    # Detailed results
    for result in results:
        status = "✅" if result["success"] and not result.get("has_error") and result.get("has_message") else "❌"
        print(f"{status} {result['command']:15} - {result['description']}")
        if result["success"]:
            print(f"   ⏱️  {result['elapsed']:.2f}s | 📝 Message: {result.get('has_message', False)} | 🔘 Buttons: {result.get('buttons_count', 0)}")
            if result.get("has_error"):
                print(f"   ⚠️  Error in response: {result.get('message_preview', '')}")
        else:
            print(f"   ❌ {result.get('error', 'Unknown error')}")
        print("")
    
    print("=" * 70)
    print("📝 ДЕ ДИВИТИСЬ ЛОГИ:")
    print("=" * 70)
    print("1. Railway Logs:")
    print(f"   https://railway.app/project/{BOT_ID}/logs")
    print("")
    print("2. GitHub Actions (якщо деплой через GitHub):")
    print("   https://github.com/your-repo/actions")
    print("")
    print("3. Локальні логи (якщо запущено локально):")
    print("   docker logs <container_name>")
    print("")
    print("4. Тестовий endpoint (детальні логи):")
    print(f"   POST {API_BASE}/api/v1/admin/bots/{BOT_ID}/test-command")
    print("")
    print("=" * 70)
    
    # Exit code
    if success_count == total_count:
        print("✅ ВСІ ТЕСТИ ПРОЙШЛИ!")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} ТЕСТІВ НЕ ПРОЙШЛИ")
        return 1

if __name__ == "__main__":
    sys.exit(main())

