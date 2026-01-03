#!/usr/bin/env python3
"""
Test script for Mini App commands
Tests all commands and compares with Telegram bot logic
"""
import requests
import json
import sys
from typing import Dict, Any, Optional

# Configuration
BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
USER_ID = "380927579"  # Test user
BASE_URL = "https://api-production-57e8.up.railway.app"
# BASE_URL = "http://localhost:8000"  # For local testing

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text: str):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


def print_success(text: str):
    print(f"{GREEN}✅ {text}{RESET}")


def print_error(text: str):
    print(f"{RED}❌ {text}{RESET}")


def print_warning(text: str):
    print(f"{YELLOW}⚠️  {text}{RESET}")


def print_info(text: str):
    print(f"ℹ️  {text}")


def test_mini_app_data() -> Optional[Dict[str, Any]]:
    """Test GET /mini-app/{bot_id}/data endpoint"""
    print_header("TEST 1: Mini App Data Endpoint")
    
    url = f"{BASE_URL}/api/v1/mini-apps/mini-app/{BOT_ID}/data"
    params = {"user_id": USER_ID}
    
    try:
        response = requests.get(url, params=params, verify=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("ok") is True:
            print_success("Data endpoint works")
            
            # Check required fields
            required_fields = ["user", "earnings", "partners", "top_partners", "config"]
            for field in required_fields:
                if field in data:
                    print_success(f"  ✓ {field} field present")
                else:
                    print_error(f"  ✗ {field} field missing")
            
            # Print summary
            user = data.get("user", {})
            earnings = data.get("earnings", {})
            partners = data.get("partners", [])
            top_partners = data.get("top_partners", [])
            
            print_info(f"  User balance: {user.get('balance', 0)}")
            print_info(f"  User wallet: {user.get('wallet', 'Not set')[:20]}...")
            print_info(f"  Top status: {user.get('top_status', 'unknown')}")
            print_info(f"  Total invited: {user.get('total_invited', 0)}")
            print_info(f"  Partners count: {len(partners)}")
            print_info(f"  TOP partners count: {len(top_partners)}")
            print_info(f"  Can unlock TOP: {earnings.get('can_unlock_top', False)}")
            print_info(f"  Invites needed: {earnings.get('invites_needed', 0)}")
            
            return data
        else:
            print_error(f"Data endpoint returned ok=False: {data}")
            return None
            
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON response: {e}")
        return None


def test_wallet_save() -> bool:
    """Test POST /mini-app/{bot_id}/wallet endpoint"""
    print_header("TEST 2: Wallet Save Endpoint")
    
    url = f"{BASE_URL}/api/v1/mini-apps/mini-app/{BOT_ID}/wallet"
    
    # Test with valid wallet
    test_wallet = "EQD__________________________________________0vo"  # Valid format
    params = {
        "wallet_address": test_wallet,
        "user_id": USER_ID
    }
    
    try:
        response = requests.post(url, params=params, verify=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("ok") is True:
            print_success("Wallet save endpoint works")
            print_info(f"  Message: {data.get('message', 'No message')}")
            return True
        else:
            print_error(f"Wallet save returned ok=False: {data}")
            return False
            
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON response: {e}")
        return False


def test_wallet_validation() -> bool:
    """Test wallet validation (invalid format)"""
    print_header("TEST 3: Wallet Validation")
    
    url = f"{BASE_URL}/api/v1/mini-apps/mini-app/{BOT_ID}/wallet"
    
    # Test with invalid wallet
    invalid_wallet = "invalid_wallet_address"
    params = {
        "wallet_address": invalid_wallet,
        "user_id": USER_ID
    }
    
    try:
        response = requests.post(url, params=params, verify=False, timeout=10)
        
        # Should return 400 Bad Request
        if response.status_code == 400:
            print_success("Wallet validation works (rejects invalid format)")
            print_info(f"  Error: {response.json().get('detail', 'No detail')}")
            return True
        else:
            print_error(f"Expected 400, got {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return False


def test_bot_command(command: str, description: str) -> Optional[Dict[str, Any]]:
    """Test bot command via test-command endpoint"""
    print_header(f"TEST: Bot Command /{command}")
    print_info(f"Description: {description}")
    
    url = f"{BASE_URL}/api/v1/admin/bots/{BOT_ID}/test-command"
    params = {
        "command": f"/{command}",
        "user_lang": "uk"
    }
    
    try:
        response = requests.post(url, params=params, verify=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("has_error") is False:
            print_success(f"Command /{command} works")
            
            message = data.get("message", {})
            if message:
                text = message.get("text", "")
                buttons = message.get("buttons", [])
                print_info(f"  Message length: {len(text)} chars")
                print_info(f"  Buttons count: {len(buttons)}")
                if text:
                    print_info(f"  Preview: {text[:100]}...")
            
            return data
        else:
            print_error(f"Command /{command} returned has_error=True")
            print_error(f"  Error: {data.get('error', 'No error message')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON response: {e}")
        return None


def compare_mini_app_vs_bot(mini_app_data: Dict[str, Any], bot_data: Dict[str, Any], command: str):
    """Compare Mini App data with bot command response"""
    print_header(f"COMPARE: Mini App vs Bot for /{command}")
    
    if command == "earnings":
        # Compare earnings data
        mini_earnings = mini_app_data.get("earnings", {})
        bot_message = bot_data.get("message", {}).get("text", "")
        
        mini_balance = mini_app_data.get("user", {}).get("balance", 0)
        mini_top_status = mini_app_data.get("user", {}).get("top_status", "unknown")
        mini_invites = mini_app_data.get("user", {}).get("total_invited", 0)
        
        print_info(f"Mini App - Balance: {mini_balance}")
        print_info(f"Mini App - Top status: {mini_top_status}")
        print_info(f"Mini App - Total invited: {mini_invites}")
        print_info(f"Bot message contains balance: {'balance' in bot_message.lower() or str(mini_balance) in bot_message}")
        print_info(f"Bot message contains top status: {mini_top_status in bot_message.lower()}")
        
    elif command == "partners":
        # Compare partners
        mini_partners = mini_app_data.get("partners", [])
        bot_message = bot_data.get("message", {}).get("text", "")
        
        print_info(f"Mini App - Partners count: {len(mini_partners)}")
        print_info(f"Bot message length: {len(bot_message)}")
        
        # Check if partner names are in bot message
        if mini_partners:
            first_partner_name = mini_partners[0].get("name", "")
            if first_partner_name:
                in_message = first_partner_name in bot_message
                print_info(f"First partner '{first_partner_name}' in bot message: {in_message}")
    
    elif command == "top":
        # Compare TOP data
        mini_top_status = mini_app_data.get("user", {}).get("top_status", "unknown")
        mini_top_partners = mini_app_data.get("top_partners", [])
        bot_message = bot_data.get("message", {}).get("text", "")
        
        print_info(f"Mini App - Top status: {mini_top_status}")
        print_info(f"Mini App - TOP partners count: {len(mini_top_partners)}")
        print_info(f"Bot message contains 'locked': {'locked' in bot_message.lower() or 'закрито' in bot_message.lower()}")
        
        if mini_top_status == "unlocked" and mini_top_partners:
            first_top_name = mini_top_partners[0].get("name", "")
            if first_top_name:
                in_message = first_top_name in bot_message
                print_info(f"First TOP partner '{first_top_name}' in bot message: {in_message}")


def main():
    """Run all tests"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Mini App Commands Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = {
        "mini_app_data": False,
        "wallet_save": False,
        "wallet_validation": False,
        "bot_commands": {},
        "comparisons": {}
    }
    
    # Test 1: Mini App Data
    mini_app_data = test_mini_app_data()
    if mini_app_data:
        results["mini_app_data"] = True
        
        # Test 2: Wallet Save
        results["wallet_save"] = test_wallet_save()
        
        # Test 3: Wallet Validation
        results["wallet_validation"] = test_wallet_validation()
        
        # Test 4-8: Bot Commands
        commands = [
            ("start", "Welcome message"),
            ("wallet", "Wallet management"),
            ("partners", "Partners list"),
            ("top", "TOP partners"),
            ("share", "Referral link"),
            ("earnings", "Earnings center"),
            ("info", "Bot information"),
        ]
        
        bot_responses = {}
        for cmd, desc in commands:
            bot_data = test_bot_command(cmd, desc)
            if bot_data:
                bot_responses[cmd] = bot_data
                results["bot_commands"][cmd] = True
                
                # Compare with Mini App data
                if cmd in ["earnings", "partners", "top"]:
                    compare_mini_app_vs_bot(mini_app_data, bot_data, cmd)
            else:
                results["bot_commands"][cmd] = False
    
    # Summary
    print_header("TEST SUMMARY")
    
    total_tests = 1 + 2 + len(commands)  # mini_app_data + wallet tests + commands
    passed_tests = sum([
        results["mini_app_data"],
        results["wallet_save"],
        results["wallet_validation"],
        sum(results["bot_commands"].values())
    ])
    
    print_info(f"Total tests: {total_tests}")
    print_info(f"Passed: {passed_tests}")
    print_info(f"Failed: {total_tests - passed_tests}")
    
    if results["mini_app_data"]:
        print_success("Mini App data endpoint: PASSED")
    else:
        print_error("Mini App data endpoint: FAILED")
    
    if results["wallet_save"]:
        print_success("Wallet save: PASSED")
    else:
        print_error("Wallet save: FAILED")
    
    if results["wallet_validation"]:
        print_success("Wallet validation: PASSED")
    else:
        print_error("Wallet validation: FAILED")
    
    for cmd, passed in results["bot_commands"].items():
        if passed:
            print_success(f"Bot command /{cmd}: PASSED")
        else:
            print_error(f"Bot command /{cmd}: FAILED")
    
    print(f"\n{BLUE}{'='*60}{RESET}\n")
    
    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())

