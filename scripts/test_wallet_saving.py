#!/usr/bin/env python3
"""
Test wallet saving functionality
Tests various wallet address formats and validation
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from uuid import UUID
import asyncio

from app.core.database import SessionLocal
from app.models.bot import Bot
from app.models.user import User
from app.models.business_data import BusinessData
from app.services.user_service import UserService
from app.services.wallet_service import WalletService
from app.adapters.telegram import TelegramAdapter

# Test cases
TEST_CASES = [
    {
        "name": "Valid EQ wallet",
        "address": "EQCwz3GkW9hkGkB3Dxvkdsi8IzUxxxxxxxxxxxxxxxxxxxxxxx",
        "should_save": True,
        "description": "Standard EQ format wallet (48 chars)"
    },
    {
        "name": "Valid UQ wallet",
        "address": "UQCFzwaYyii9HdAqAsKsW7T2VSmTnGQWVgBAKn9vdIQhg2zC",
        "should_save": True,
        "description": "UQ format wallet (48 chars) - real user's wallet"
    },
    {
        "name": "Valid kQ wallet",
        "address": "kQCwz3GkW9hkGkB3Dxvkdsi8IzUxxxxxxxxxxxxxxxxxxxxxxx",
        "should_save": True,
        "description": "kQ format wallet"
    },
    {
        "name": "Valid 0Q wallet",
        "address": "0QCwz3GkW9hkGkB3Dxvkdsi8IzUxxxxxxxxxxxxxxxxxxxxxxx",
        "should_save": True,
        "description": "0Q format wallet"
    },
    {
        "name": "Wallet with spaces (should strip)",
        "address": "  UQCFzwaYyii9HdAqAsKsW7T2VSmTnGQWVgBAKn9vdIQhg2zC  ",
        "should_save": True,
        "description": "Wallet with leading/trailing spaces"
    },
    {
        "name": "Invalid - too short",
        "address": "UQCFzwaYyii9HdAqAsKsW7T2VSmTnGQWVgBAKn9vdIQhg2z",
        "should_save": False,
        "description": "Wallet too short (47 chars, needs 46-48)"
    },
    {
        "name": "Invalid - too long",
        "address": "UQCFzwaYyii9HdAqAsKsW7T2VSmTnGQWVgBAKn9vdIQhg2zCC",
        "should_save": False,
        "description": "Wallet too long (49 chars, needs 46-48)"
    },
    {
        "name": "Invalid - wrong prefix",
        "address": "ABCwz3GkW9hkGkB3Dxvkdsi8IzUxxxxxxxxxxxxxxxxxxxxxxx",
        "should_save": False,
        "description": "Wallet with wrong prefix (not EQ/UQ/kQ/0Q)"
    },
    {
        "name": "Invalid - contains invalid chars",
        "address": "UQCFzwaYyii9HdAqAsKsW7T2VSmTnGQWVgBAKn9vdIQhg2z@",
        "should_save": False,
        "description": "Wallet with invalid character (@)"
    },
    {
        "name": "Invalid - empty string",
        "address": "",
        "should_save": False,
        "description": "Empty string"
    },
    {
        "name": "Invalid - just spaces",
        "address": "   ",
        "should_save": False,
        "description": "Only spaces"
    },
]

BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
TEST_USER_EXTERNAL_ID = "test_wallet_user_12345"


class MockAdapter:
    """Mock adapter for testing"""
    def __init__(self):
        self.sent_messages = []
    
    async def send_message(self, bot_id, external_id, message, **kwargs):
        self.sent_messages.append({
            'bot_id': str(bot_id),
            'external_id': external_id,
            'message': message,
            'kwargs': kwargs
        })
        return {'ok': True, 'result': {'message_id': 999}}


def check_wallet_in_db(db: Session, bot_id: UUID, user_id: UUID, wallet_address: str) -> bool:
    """Check if wallet is saved in database"""
    # Check custom_data
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.custom_data:
        if user.custom_data.get('wallet_address') == wallet_address:
            return True
    
    # Check business_data
    wallet_data = db.query(BusinessData).filter(
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'wallet',
        BusinessData.data['user_id'].astext == str(user_id)
    ).order_by(BusinessData.created_at.desc()).first()
    
    if wallet_data and wallet_data.data:
        if wallet_data.data.get('wallet_address') == wallet_address:
            return True
    
    return False


async def test_wallet_case(db: Session, bot_id: UUID, test_case: dict, adapter: MockAdapter) -> dict:
    """Test a single wallet case"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_case['name']}")
    print(f"Address: {test_case['address']}")
    print(f"Expected: {'SAVE' if test_case['should_save'] else 'REJECT'}")
    print(f"Description: {test_case['description']}")
    
    # Get or create test user
    user_service = UserService(db, bot_id)
    user = user_service.get_or_create_user(
        external_id=TEST_USER_EXTERNAL_ID,
        platform="telegram",
        language_code="uk",
        username="test_wallet_user",
        first_name="Test",
        last_name="Wallet"
    )
    
    # Clear existing wallet for this test
    if user.custom_data:
        user.custom_data.pop('wallet_address', None)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, 'custom_data')
    db.commit()
    
    # Delete existing wallet records
    db.query(BusinessData).filter(
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'wallet',
        BusinessData.data['user_id'].astext == str(user.id)
    ).delete()
    db.commit()
    
    # Test wallet service
    wallet_service = WalletService(db, bot_id, user_service)
    
    # Validate format first
    is_valid = wallet_service.validate_wallet_format(test_case['address'])
    print(f"Format validation: {'✅ VALID' if is_valid else '❌ INVALID'}")
    
    # Try to save
    try:
        result = await wallet_service.save_wallet(user.id, test_case['address'], adapter)
        print(f"Save result: {result}")
    except Exception as e:
        print(f"❌ Exception during save: {e}")
        result = False
    
    # Check if saved in DB
    wallet_address_clean = test_case['address'].strip()
    saved_in_db = check_wallet_in_db(db, bot_id, user.id, wallet_address_clean)
    
    # Check messages sent
    messages_sent = len(adapter.sent_messages)
    last_message = adapter.sent_messages[-1]['message'] if adapter.sent_messages else None
    
    # Evaluate result
    if test_case['should_save']:
        success = result and saved_in_db
        status = "✅ PASS" if success else "❌ FAIL"
        if not success:
            print(f"  Expected: Should save, but result={result}, saved_in_db={saved_in_db}")
    else:
        success = not result and not saved_in_db
        status = "✅ PASS" if success else "❌ FAIL"
        if not success:
            print(f"  Expected: Should reject, but result={result}, saved_in_db={saved_in_db}")
    
    print(f"Status: {status}")
    if last_message:
        print(f"Message sent: {last_message[:100]}...")
    
    return {
        'test_case': test_case['name'],
        'success': success,
        'result': result,
        'saved_in_db': saved_in_db,
        'message_sent': messages_sent > 0,
        'last_message': last_message
    }


async def main():
    """Run all wallet tests"""
    db = SessionLocal()
    bot_id = UUID(BOT_ID)
    adapter = MockAdapter()
    
    print("🧪 Testing Wallet Saving Functionality")
    print(f"Bot ID: {bot_id}")
    print(f"Test User: {TEST_USER_EXTERNAL_ID}")
    
    results = []
    
    for test_case in TEST_CASES:
        try:
            result = await test_wallet_case(db, bot_id, test_case, adapter)
            results.append(result)
            adapter.sent_messages.clear()  # Clear for next test
        except Exception as e:
            print(f"❌ Error testing {test_case['name']}: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'test_case': test_case['name'],
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r.get('success', False))
    total = len(results)
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    print(f"\n{'='*60}")
    print("Detailed Results:")
    for result in results:
        status = "✅" if result.get('success', False) else "❌"
        print(f"{status} {result['test_case']}")
        if not result.get('success', False):
            print(f"   Result: {result.get('result')}")
            print(f"   Saved in DB: {result.get('saved_in_db')}")
            if result.get('error'):
                print(f"   Error: {result['error']}")
    
    db.close()
    
    # Exit with error code if any test failed
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

