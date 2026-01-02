#!/usr/bin/env python3
"""
Test all bot commands and measure response time.
Shows which commands are slow and need optimization.
"""
import requests
import time
import json
import sys

# Configuration
API_BASE = "https://api-production-57e8.up.railway.app"
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
TEST_USER_ID = f"perf_test_{int(time.time())}"

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

# Thresholds
SLOW_THRESHOLD = 2.0  # seconds - warn if slower
VERY_SLOW_THRESHOLD = 5.0  # seconds - error if slower

def test_command(command: str, description: str) -> dict:
    """Test a single command and measure response time"""
    url = f"{API_BASE}/api/v1/admin/bots/{BOT_ID}/test-command"
    params = {
        "command": command,
        "user_external_id": TEST_USER_ID,
        "user_lang": "uk"
    }
    
    start_time = time.time()
    try:
        response = requests.get(url, params=params, verify=False, timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            success = data.get("success", False)
            has_message = bool(data.get("response", {}).get("message"))
            message_length = len(data.get("response", {}).get("message", ""))
            buttons_count = len(data.get("response", {}).get("buttons", []))
            
            return {
                "command": command,
                "description": description,
                "success": success,
                "elapsed": elapsed,
                "status": "ok",
                "message_length": message_length,
                "buttons_count": buttons_count,
                "error": None
            }
        else:
            return {
                "command": command,
                "description": description,
                "success": False,
                "elapsed": elapsed,
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text[:100]}"
            }
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        return {
            "command": command,
            "description": description,
            "success": False,
            "elapsed": elapsed,
            "status": "timeout",
            "error": "Request timeout"
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "command": command,
            "description": description,
            "success": False,
            "elapsed": elapsed,
            "status": "error",
            "error": str(e)
        }

def main():
    print("🚀 Testing Bot Commands Performance")
    print("=" * 70)
    print(f"Bot ID: {BOT_ID}")
    print(f"Test User: {TEST_USER_ID}")
    print(f"API: {API_BASE}")
    print("=" * 70)
    print()
    
    results = []
    
    for command, description in COMMANDS:
        print(f"Testing {command} ({description})...", end=" ", flush=True)
        result = test_command(command, description)
        results.append(result)
        
        elapsed = result["elapsed"]
        status_icon = "✅" if result["success"] else "❌"
        
        if elapsed < SLOW_THRESHOLD:
            time_status = "🟢"
        elif elapsed < VERY_SLOW_THRESHOLD:
            time_status = "🟡"
        else:
            time_status = "🔴"
        
        print(f"{status_icon} {time_status} {elapsed:.2f}s", end="")
        
        if result.get("message_length"):
            print(f" (msg: {result['message_length']} chars, buttons: {result['buttons_count']})", end="")
        
        if result.get("error"):
            print(f" - ERROR: {result['error'][:50]}")
        else:
            print()
    
    print()
    print("=" * 70)
    print("📊 Performance Summary")
    print("=" * 70)
    
    # Sort by elapsed time
    results_sorted = sorted(results, key=lambda x: x["elapsed"], reverse=True)
    
    total_time = sum(r["elapsed"] for r in results)
    avg_time = total_time / len(results) if results else 0
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Average time: {avg_time:.2f}s")
    print()
    
    print("Commands sorted by response time:")
    print("-" * 70)
    
    slow_commands = []
    very_slow_commands = []
    
    for result in results_sorted:
        elapsed = result["elapsed"]
        status_icon = "✅" if result["success"] else "❌"
        
        if elapsed < SLOW_THRESHOLD:
            time_status = "🟢 FAST"
        elif elapsed < VERY_SLOW_THRESHOLD:
            time_status = "🟡 SLOW"
            slow_commands.append(result)
        else:
            time_status = "🔴 VERY SLOW"
            very_slow_commands.append(result)
        
        print(f"{status_icon} {time_status:12} {elapsed:6.2f}s - {result['command']:15} ({result['description']})")
        
        if result.get("message_length"):
            print(f"   └─ Message: {result['message_length']} chars, Buttons: {result['buttons_count']}")
        
        if result.get("error"):
            print(f"   └─ ERROR: {result['error'][:60]}")
    
    print()
    print("=" * 70)
    
    if very_slow_commands:
        print("🔴 VERY SLOW COMMANDS (>5s) - NEED OPTIMIZATION:")
        for cmd in very_slow_commands:
            print(f"   - {cmd['command']}: {cmd['elapsed']:.2f}s")
        print()
    
    if slow_commands:
        print("🟡 SLOW COMMANDS (2-5s) - CONSIDER OPTIMIZATION:")
        for cmd in slow_commands:
            print(f"   - {cmd['command']}: {cmd['elapsed']:.2f}s")
        print()
    
    if not slow_commands and not very_slow_commands:
        print("✅ All commands are fast (<2s)!")
        print()
    
    # Return exit code based on results
    if very_slow_commands:
        sys.exit(1)  # Error if any command is very slow
    elif slow_commands:
        sys.exit(0)  # Warning if any command is slow
    else:
        sys.exit(0)  # Success if all commands are fast

if __name__ == "__main__":
    main()

