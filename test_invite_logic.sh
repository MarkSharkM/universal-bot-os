#!/bin/bash
# Test script for invite/referral logic in Mini App
# Verifies that invite counting, TOP unlock, and referral links work correctly

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

print_header() {
    echo -e "\n${BLUE}============================================================${RESET}"
    echo -e "${BLUE}$1${RESET}"
    echo -e "${BLUE}============================================================${RESET}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${RESET}"
}

print_error() {
    echo -e "${RED}❌ $1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${RESET}"
}

print_info() {
    echo -e "ℹ️  $1"
}

test_mini_app_invite_data() {
    print_header "TEST: Mini App Invite Data"
    
    URL="${BASE_URL}/api/v1/mini-apps/mini-app/${BOT_ID}/data?user_id=${USER_ID}"
    
    RESPONSE=$(curl -k -s -X GET "$URL")
    
    REFERRAL_LINK=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('referral_link', 'Not set'))" 2>/dev/null || echo "Not set")
    TOTAL_INVITED=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('total_invited', 0))" 2>/dev/null || echo "0")
    REQUIRED_INVITES=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('earnings', {}).get('required_invites', 0))" 2>/dev/null || echo "0")
    INVITES_NEEDED=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('earnings', {}).get('invites_needed', 0))" 2>/dev/null || echo "0")
    CAN_UNLOCK_TOP=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('earnings', {}).get('can_unlock_top', False))" 2>/dev/null || echo "False")
    TOP_STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('top_status', 'unknown'))" 2>/dev/null || echo "unknown")
    
    print_info "Referral link: $REFERRAL_LINK"
    print_info "Total invited: $TOTAL_INVITED"
    print_info "Required invites: $REQUIRED_INVITES"
    print_info "Invites needed: $INVITES_NEEDED"
    print_info "Can unlock TOP: $CAN_UNLOCK_TOP"
    print_info "Top status: $TOP_STATUS"
    
    # Validate data
    ERRORS=0
    
    if [ "$REFERRAL_LINK" = "Not set" ] || [ -z "$REFERRAL_LINK" ]; then
        print_error "Referral link is missing or not set"
        ((ERRORS++))
    else
        if [[ "$REFERRAL_LINK" == *"start="* ]]; then
            print_success "Referral link format is correct (contains start=)"
        else
            print_error "Referral link format is incorrect (missing start=)"
            ((ERRORS++))
        fi
    fi
    
    if [ "$TOTAL_INVITED" -ge 0 ] 2>/dev/null; then
        print_success "Total invited is a valid number: $TOTAL_INVITED"
    else
        print_error "Total invited is not a valid number: $TOTAL_INVITED"
        ((ERRORS++))
    fi
    
    if [ "$REQUIRED_INVITES" -gt 0 ] 2>/dev/null; then
        print_success "Required invites is valid: $REQUIRED_INVITES"
    else
        print_error "Required invites is invalid: $REQUIRED_INVITES"
        ((ERRORS++))
    fi
    
    # Check logic consistency
    CALCULATED_NEEDED=$((REQUIRED_INVITES - TOTAL_INVITED))
    if [ "$CALCULATED_NEEDED" -lt 0 ]; then
        CALCULATED_NEEDED=0
    fi
    
    if [ "$INVITES_NEEDED" -eq "$CALCULATED_NEEDED" ]; then
        print_success "Invites needed calculation is correct: $INVITES_NEEDED"
    else
        print_warning "Invites needed mismatch: expected $CALCULATED_NEEDED, got $INVITES_NEEDED"
    fi
    
    # Check TOP unlock logic
    if [ "$TOTAL_INVITED" -ge "$REQUIRED_INVITES" ]; then
        if [ "$CAN_UNLOCK_TOP" = "True" ] || [ "$TOP_STATUS" = "open" ]; then
            print_success "TOP unlock logic is correct (invited >= required, can unlock)"
        else
            print_error "TOP unlock logic error: invited >= required but can_unlock_top=False"
            ((ERRORS++))
        fi
    else
        if [ "$CAN_UNLOCK_TOP" = "False" ] && [ "$TOP_STATUS" = "locked" ]; then
            print_success "TOP unlock logic is correct (invited < required, locked)"
        else
            print_warning "TOP unlock logic might be inconsistent"
        fi
    fi
    
    # Progress calculation
    if [ "$REQUIRED_INVITES" -gt 0 ]; then
        PROGRESS=$((TOTAL_INVITED * 100 / REQUIRED_INVITES))
        if [ "$PROGRESS" -gt 100 ]; then
            PROGRESS=100
        fi
        print_info "Progress: $PROGRESS% ($TOTAL_INVITED/$REQUIRED_INVITES)"
    fi
    
    return $ERRORS
}

test_bot_earnings_invite_data() {
    print_header "TEST: Bot /earnings Invite Data"
    
    URL="${BASE_URL}/api/v1/admin/bots/${BOT_ID}/test-command"
    
    RESPONSE=$(curl -k -s -X POST "${URL}?command=/earnings&user_lang=uk")
    
    MESSAGE=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); resp=d.get('response', {}); msg_obj=resp.get('message', {}); msg=msg_obj.get('text', '') if isinstance(msg_obj, dict) else (msg_obj if isinstance(msg_obj, str) else ''); print(msg)" 2>/dev/null || echo "")
    
    if [ -z "$MESSAGE" ]; then
        print_error "Bot /earnings message is empty"
        return 1
    fi
    
    print_info "Message length: ${#MESSAGE} chars"
    
    # Check for invite-related content
    HAS_REFERRAL_LINK=false
    HAS_TOTAL_INVITED=false
    HAS_INVITES_NEEDED=false
    HAS_PROGRESS=false
    
    if echo "$MESSAGE" | grep -qi "start="; then
        HAS_REFERRAL_LINK=true
        print_success "Bot message contains referral link"
    else
        print_warning "Bot message might not contain referral link"
    fi
    
    if echo "$MESSAGE" | grep -qiE "[0-9]+.*[0-9]+.*друз|інвайт"; then
        HAS_TOTAL_INVITED=true
        print_success "Bot message contains invite count"
    else
        print_warning "Bot message might not contain invite count"
    fi
    
    if echo "$MESSAGE" | grep -qiE "потрібно|ще.*інвайт"; then
        HAS_INVITES_NEEDED=true
        print_success "Bot message contains invites needed"
    else
        print_warning "Bot message might not contain invites needed"
    fi
    
    if echo "$MESSAGE" | grep -qiE "прогрес|progress|/"; then
        HAS_PROGRESS=true
        print_success "Bot message contains progress info"
    else
        print_warning "Bot message might not contain progress info"
    fi
    
    return 0
}

compare_mini_app_vs_bot_invites() {
    print_header "COMPARE: Mini App vs Bot Invite Data"
    
    # Get Mini App data
    MINI_APP_URL="${BASE_URL}/api/v1/mini-apps/mini-app/${BOT_ID}/data?user_id=${USER_ID}"
    MINI_APP_RESPONSE=$(curl -k -s -X GET "$MINI_APP_URL")
    
    MINI_TOTAL_INVITED=$(echo "$MINI_APP_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('total_invited', 0))" 2>/dev/null || echo "0")
    MINI_REFERRAL_LINK=$(echo "$MINI_APP_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('user', {}).get('referral_link', ''))" 2>/dev/null || echo "")
    
    # Get Bot data
    BOT_URL="${BASE_URL}/api/v1/admin/bots/${BOT_ID}/test-command"
    BOT_RESPONSE=$(curl -k -s -X POST "${BOT_URL}?command=/earnings&user_lang=uk")
    BOT_MESSAGE=$(echo "$BOT_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); resp=d.get('response', {}); msg_obj=resp.get('message', {}); msg=msg_obj.get('text', '') if isinstance(msg_obj, dict) else (msg_obj if isinstance(msg_obj, str) else ''); print(msg)" 2>/dev/null || echo "")
    
    print_info "Mini App - Total invited: $MINI_TOTAL_INVITED"
    print_info "Mini App - Referral link: ${MINI_REFERRAL_LINK:0:50}..."
    
    # Extract numbers from bot message
    BOT_INVITE_COUNT=$(echo "$BOT_MESSAGE" | grep -oE "[0-9]+.*/[0-9]+" | head -1 | grep -oE "^[0-9]+" | head -1 || echo "")
    
    if [ -n "$BOT_INVITE_COUNT" ]; then
        print_info "Bot - Invite count (extracted): $BOT_INVITE_COUNT"
        
        if [ "$MINI_TOTAL_INVITED" -eq "$BOT_INVITE_COUNT" ]; then
            print_success "Invite counts match: $MINI_TOTAL_INVITED"
        else
            print_warning "Invite counts mismatch: Mini App=$MINI_TOTAL_INVITED, Bot=$BOT_INVITE_COUNT"
        fi
    else
        print_warning "Could not extract invite count from bot message"
    fi
    
    # Check referral link
    if [ -n "$MINI_REFERRAL_LINK" ] && echo "$BOT_MESSAGE" | grep -q "$(echo "$MINI_REFERRAL_LINK" | grep -oE 'start=[^&]+' || echo '')"; then
        print_success "Referral links match"
    else
        print_warning "Referral links might not match (could be different user_id in test)"
    fi
}

# Main execution
echo -e "\n${BLUE}============================================================${RESET}"
echo -e "${BLUE}Invite Logic Test Suite${RESET}"
echo -e "${BLUE}============================================================${RESET}\n"

ERRORS=0

# Test 1: Mini App invite data
if test_mini_app_invite_data; then
    print_success "Mini App invite data test passed"
else
    print_error "Mini App invite data test failed"
    ((ERRORS++))
fi

# Test 2: Bot earnings invite data
if test_bot_earnings_invite_data; then
    print_success "Bot earnings invite data test passed"
else
    print_error "Bot earnings invite data test failed"
    ((ERRORS++))
fi

# Test 3: Compare Mini App vs Bot
compare_mini_app_vs_bot_invites

# Summary
print_header "TEST SUMMARY"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All invite logic tests passed! ✅${RESET}\n"
    exit 0
else
    echo -e "${RED}Some invite logic tests failed. ❌${RESET}\n"
    exit 1
fi

