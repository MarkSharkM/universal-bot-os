#!/bin/bash
# Test script for Mini App commands
# Tests all commands and compares with Telegram bot logic

set -e

# Configuration
BOT_ID="4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
USER_ID="380927579"
BASE_URL="https://api-production-57e8.up.railway.app"

# Colors
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
BLUE='\033[94m'
RESET='\033[0m'

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

print_header() {
    echo -e "\n${BLUE}============================================================${RESET}"
    echo -e "${BLUE}$1${RESET}"
    echo -e "${BLUE}============================================================${RESET}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${RESET}"
    ((PASSED_TESTS++))
}

print_error() {
    echo -e "${RED}❌ $1${RESET}"
    ((FAILED_TESTS++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${RESET}"
}

print_info() {
    echo -e "ℹ️  $1"
}

test_mini_app_data() {
    print_header "TEST 1: Mini App Data Endpoint"
    ((TOTAL_TESTS++))
    
    URL="${BASE_URL}/api/v1/mini-apps/mini-app/${BOT_ID}/data?user_id=${USER_ID}"
    
    RESPONSE=$(curl -k -s -X GET "$URL" -w "\n%{http_code}")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" -eq 200 ]; then
        OK=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('ok', False))" 2>/dev/null || echo "false")
        
        if [ "$OK" = "True" ]; then
            print_success "Data endpoint works (HTTP 200)"
            
            # Extract and display key fields
            BALANCE=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('balance', 0))" 2>/dev/null || echo "0")
            WALLET=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('wallet', 'Not set')[:20])" 2>/dev/null || echo "Not set")
            TOP_STATUS=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('top_status', 'unknown'))" 2>/dev/null || echo "unknown")
            TOTAL_INVITED=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('total_invited', 0))" 2>/dev/null || echo "0")
            PARTNERS_COUNT=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('partners', [])))" 2>/dev/null || echo "0")
            TOP_PARTNERS_COUNT=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('top_partners', [])))" 2>/dev/null || echo "0")
            CAN_UNLOCK=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('earnings', {}).get('can_unlock_top', False))" 2>/dev/null || echo "False")
            INVITES_NEEDED=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('earnings', {}).get('invites_needed', 0))" 2>/dev/null || echo "0")
            
            print_info "  User balance: $BALANCE"
            print_info "  User wallet: ${WALLET}..."
            print_info "  Top status: $TOP_STATUS"
            print_info "  Total invited: $TOTAL_INVITED"
            print_info "  Partners count: $PARTNERS_COUNT"
            print_info "  TOP partners count: $TOP_PARTNERS_COUNT"
            print_info "  Can unlock TOP: $CAN_UNLOCK"
            print_info "  Invites needed: $INVITES_NEEDED"
            
            echo "$BODY" > /tmp/mini_app_data.json
            return 0
        else
            print_error "Data endpoint returned ok=False"
            return 1
        fi
    else
        print_error "Data endpoint failed (HTTP $HTTP_CODE)"
        return 1
    fi
}

test_wallet_save() {
    print_header "TEST 2: Wallet Save Endpoint"
    ((TOTAL_TESTS++))
    
    URL="${BASE_URL}/api/v1/mini-apps/mini-app/${BOT_ID}/wallet"
    TEST_WALLET="EQD__________________________________________0vo"
    
    RESPONSE=$(curl -k -s -X POST "${URL}?wallet_address=${TEST_WALLET}&user_id=${USER_ID}" -w "\n%{http_code}")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" -eq 200 ]; then
        OK=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('ok', False))" 2>/dev/null || echo "false")
        
        if [ "$OK" = "True" ]; then
            print_success "Wallet save works (HTTP 200)"
            MESSAGE=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('message', 'No message'))" 2>/dev/null || echo "No message")
            print_info "  Message: $MESSAGE"
            return 0
        else
            print_error "Wallet save returned ok=False"
            return 1
        fi
    else
        print_error "Wallet save failed (HTTP $HTTP_CODE)"
        return 1
    fi
}

test_wallet_validation() {
    print_header "TEST 3: Wallet Validation (Invalid Format)"
    ((TOTAL_TESTS++))
    
    URL="${BASE_URL}/api/v1/mini-apps/mini-app/${BOT_ID}/wallet"
    INVALID_WALLET="invalid_wallet_address"
    
    RESPONSE=$(curl -k -s -X POST "${URL}?wallet_address=${INVALID_WALLET}&user_id=${USER_ID}" -w "\n%{http_code}")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" -eq 400 ]; then
        print_success "Wallet validation works (rejects invalid format, HTTP 400)"
        DETAIL=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('detail', 'No detail'))" 2>/dev/null || echo "No detail")
        print_info "  Error: $DETAIL"
        return 0
    else
        print_error "Expected HTTP 400, got $HTTP_CODE"
        return 1
    fi
}

test_bot_command() {
    local CMD=$1
    local DESC=$2
    ((TOTAL_TESTS++))
    
    print_header "TEST: Bot Command /${CMD}"
    print_info "Description: $DESC"
    
    URL="${BASE_URL}/api/v1/admin/bots/${BOT_ID}/test-command"
    
    RESPONSE=$(curl -k -s -X POST "${URL}?command=/${CMD}&user_lang=uk" -w "\n%{http_code}")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" -eq 200 ]; then
        # Check both formats: has_error: false OR success: true
        HAS_ERROR=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('has_error', not d.get('success', False)))" 2>/dev/null || echo "True")
        SUCCESS=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('success', False))" 2>/dev/null || echo "False")
        
        if [ "$HAS_ERROR" = "False" ] || [ "$SUCCESS" = "True" ]; then
            print_success "Command /${CMD} works"
            
            # Check both formats: response.message (can be string or dict) OR message
            MESSAGE_TEXT=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); resp=d.get('response', {}); msg_obj=resp.get('message', {}); msg=msg_obj.get('text', '') if isinstance(msg_obj, dict) else (msg_obj if isinstance(msg_obj, str) else ''); alt_msg=d.get('message', {}); msg=msg or (alt_msg.get('text', '') if isinstance(alt_msg, dict) else (alt_msg if isinstance(alt_msg, str) else '')); print(len(msg))" 2>/dev/null || echo "0")
            BUTTONS_COUNT=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); resp=d.get('response', {}); msg_obj=resp.get('message', {}); buttons=msg_obj.get('buttons', []) if isinstance(msg_obj, dict) else resp.get('buttons', []); alt_buttons=d.get('message', {}).get('buttons', []) if isinstance(d.get('message'), dict) else []; buttons=buttons or alt_buttons; print(len(buttons))" 2>/dev/null || echo "0")
            PREVIEW=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); resp=d.get('response', {}); msg_obj=resp.get('message', {}); msg=msg_obj.get('text', '') if isinstance(msg_obj, dict) else (msg_obj if isinstance(msg_obj, str) else ''); alt_msg=d.get('message', {}); msg=msg or (alt_msg.get('text', '') if isinstance(alt_msg, dict) else (alt_msg if isinstance(alt_msg, str) else '')); print(msg[:100])" 2>/dev/null || echo "")
            
            print_info "  Message length: ${MESSAGE_TEXT} chars"
            print_info "  Buttons count: ${BUTTONS_COUNT}"
            if [ -n "$PREVIEW" ]; then
                print_info "  Preview: ${PREVIEW}..."
            fi
            
            echo "$BODY" > "/tmp/bot_command_${CMD}.json"
            return 0
        else
            ERROR_MSG=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('error', 'No error message'))" 2>/dev/null || echo "No error message")
            print_error "Command /${CMD} returned has_error=True"
            print_error "  Error: $ERROR_MSG"
            return 1
        fi
    else
        print_error "Command /${CMD} failed (HTTP $HTTP_CODE)"
        return 1
    fi
}

compare_mini_app_vs_bot() {
    local CMD=$1
    print_header "COMPARE: Mini App vs Bot for /${CMD}"
    
    if [ ! -f /tmp/mini_app_data.json ] || [ ! -f "/tmp/bot_command_${CMD}.json" ]; then
        print_warning "Cannot compare: missing data files"
        return
    fi
    
    if [ "$CMD" = "earnings" ]; then
        MINI_BALANCE=$(cat /tmp/mini_app_data.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('balance', 0))" 2>/dev/null || echo "0")
        MINI_TOP_STATUS=$(cat /tmp/mini_app_data.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('top_status', 'unknown'))" 2>/dev/null || echo "unknown")
        MINI_INVITES=$(cat /tmp/mini_app_data.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('total_invited', 0))" 2>/dev/null || echo "0")
        BOT_MESSAGE=$(cat "/tmp/bot_command_${CMD}.json" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('response', {}).get('message', {}).get('text', '') or d.get('message', {}).get('text', ''))" 2>/dev/null || echo "")
        
        print_info "Mini App - Balance: $MINI_BALANCE"
        print_info "Mini App - Top status: $MINI_TOP_STATUS"
        print_info "Mini App - Total invited: $MINI_INVITES"
        
        if echo "$BOT_MESSAGE" | grep -qi "balance\|баланс\|$MINI_BALANCE"; then
            print_success "Bot message contains balance info"
        else
            print_warning "Bot message might not contain balance info"
        fi
        
        if echo "$BOT_MESSAGE" | grep -qi "$MINI_TOP_STATUS\|закрито\|розблоковано"; then
            print_success "Bot message contains top status"
        else
            print_warning "Bot message might not contain top status"
        fi
        
    elif [ "$CMD" = "partners" ]; then
        MINI_PARTNERS_COUNT=$(cat /tmp/mini_app_data.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('partners', [])))" 2>/dev/null || echo "0")
        BOT_MESSAGE=$(cat "/tmp/bot_command_${CMD}.json" | python3 -c "import sys, json; d=json.load(sys.stdin); resp=d.get('response', {}); msg_obj=resp.get('message', {}); msg=msg_obj.get('text', '') if isinstance(msg_obj, dict) else (msg_obj if isinstance(msg_obj, str) else ''); alt_msg=d.get('message', {}); msg=msg or (alt_msg.get('text', '') if isinstance(alt_msg, dict) else (alt_msg if isinstance(alt_msg, str) else '')); print(msg)" 2>/dev/null || echo "")
        
        print_info "Mini App - Partners count: $MINI_PARTNERS_COUNT"
        print_info "Bot message length: ${#BOT_MESSAGE} chars"
        
        if [ "$MINI_PARTNERS_COUNT" -gt 0 ]; then
            FIRST_PARTNER=$(cat /tmp/mini_app_data.json | python3 -c "import sys, json; d=json.load(sys.stdin); partners=d.get('partners', []); print(partners[0].get('name', '') if partners else '')" 2>/dev/null || echo "")
            if [ -n "$FIRST_PARTNER" ] && echo "$BOT_MESSAGE" | grep -qi "$FIRST_PARTNER"; then
                print_success "First partner name found in bot message"
            else
                print_warning "First partner name might not be in bot message"
            fi
        fi
        
    elif [ "$CMD" = "top" ]; then
        MINI_TOP_STATUS=$(cat /tmp/mini_app_data.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('top_status', 'unknown'))" 2>/dev/null || echo "unknown")
        MINI_TOP_PARTNERS_COUNT=$(cat /tmp/mini_app_data.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('top_partners', [])))" 2>/dev/null || echo "0")
        BOT_MESSAGE=$(cat "/tmp/bot_command_${CMD}.json" | python3 -c "import sys, json; d=json.load(sys.stdin); resp=d.get('response', {}); msg_obj=resp.get('message', {}); msg=msg_obj.get('text', '') if isinstance(msg_obj, dict) else (msg_obj if isinstance(msg_obj, str) else ''); alt_msg=d.get('message', {}); msg=msg or (alt_msg.get('text', '') if isinstance(alt_msg, dict) else (alt_msg if isinstance(alt_msg, str) else '')); print(msg)" 2>/dev/null || echo "")
        
        print_info "Mini App - Top status: $MINI_TOP_STATUS"
        print_info "Mini App - TOP partners count: $MINI_TOP_PARTNERS_COUNT"
        
        if echo "$BOT_MESSAGE" | grep -qi "locked\|закрито"; then
            print_success "Bot message indicates locked status"
        elif echo "$BOT_MESSAGE" | grep -qi "unlocked\|розблоковано"; then
            print_success "Bot message indicates unlocked status"
        else
            print_warning "Bot message status unclear"
        fi
    fi
}

# Main execution
echo -e "\n${BLUE}============================================================${RESET}"
echo -e "${BLUE}Mini App Commands Test Suite${RESET}"
echo -e "${BLUE}============================================================${RESET}\n"

# Test 1: Mini App Data
if test_mini_app_data; then
    # Test 2: Wallet Save
    test_wallet_save
    
    # Test 3: Wallet Validation
    test_wallet_validation
    
    # Test 4-10: Bot Commands
    test_bot_command "start" "Welcome message"
    test_bot_command "wallet" "Wallet management"
    test_bot_command "partners" "Partners list"
    test_bot_command "top" "TOP partners"
    test_bot_command "share" "Referral link"
    test_bot_command "earnings" "Earnings center"
    test_bot_command "info" "Bot information"
    
    # Compare Mini App vs Bot
    compare_mini_app_vs_bot "earnings"
    compare_mini_app_vs_bot "partners"
    compare_mini_app_vs_bot "top"
fi

# Summary
print_header "TEST SUMMARY"

echo -e "Total tests: ${TOTAL_TESTS}"
echo -e "Passed: ${PASSED_TESTS}"
echo -e "Failed: ${FAILED_TESTS}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed! ✅${RESET}\n"
    exit 0
else
    echo -e "\n${RED}Some tests failed. ❌${RESET}\n"
    exit 1
fi

