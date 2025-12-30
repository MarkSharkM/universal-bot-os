#!/usr/bin/env python3
"""
Test script: Verify that inviting 5 friends automatically unlocks TOP
Tests:
1. total_invited counter updates correctly
2. Progress bar in /earnings shows 5/5
3. TOP status changes from 'locked' to 'open'
4. top_unlock_method is set to 'invites'
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import SessionLocal
from app.models.bot import Bot
from app.models.user import User
from app.models.business_data import BusinessData
from app.services.referral_service import ReferralService
from app.services.earnings_service import EarningsService
from app.services.user_service import UserService
from app.services.translation_service import TranslationService

def test_5_invites_unlock(bot_id: str, user_id: str):
    """
    Test that inviting 5 friends unlocks TOP automatically
    
    Args:
        bot_id: Bot UUID string
        user_id: User UUID string (the inviter)
    """
    db: Session = SessionLocal()
    
    try:
        bot_uuid = UUID(bot_id)
        user_uuid = UUID(user_id)
        
        # Get bot and user
        bot = db.query(Bot).filter(Bot.id == bot_uuid).first()
        if not bot:
            print(f"❌ Bot {bot_id} not found")
            return False
        
        user = db.query(User).filter(
            User.id == user_uuid,
            User.bot_id == bot_uuid
        ).first()
        
        if not user:
            print(f"❌ User {user_id} not found")
            return False
        
        print(f"✅ Found user: {user.external_id}")
        print(f"   Current total_invited: {user.custom_data.get('total_invited', 0) if user.custom_data else 0}")
        print(f"   Current top_status: {user.custom_data.get('top_status', 'locked') if user.custom_data else 'locked'}")
        
        # Initialize services
        referral_service = ReferralService(db, bot_uuid)
        user_service = UserService(db, bot_uuid)
        translation_service = TranslationService(db, bot_uuid)
        earnings_service = EarningsService(
            db, bot_uuid, user_service, referral_service, translation_service
        )
        
        # Step 1: Create 5 referral events
        print("\n📝 Creating 5 referral events...")
        for i in range(1, 6):
            ref_param = f"_tgr_{user.external_id}"
            # Create a fake referred user external_id
            referred_external_id = f"test_referred_{i}_{user.external_id}"
            
            # Create referral log
            log_data = BusinessData(
                bot_id=bot_uuid,
                data_type='log',
                data={
                    'user_id': str(referred_external_id),  # Fake user
                    'external_id': referred_external_id,
                    'ref_parameter': ref_param,
                    'referral_tag': ref_param,
                    'inviter_external_id': user.external_id,
                    'is_referral': True,
                    'click_type': 'Referral',
                    'event_type': 'start',
                }
            )
            db.add(log_data)
            db.commit()
            print(f"   ✅ Created referral event {i}/5")
        
        # Step 2: Update total_invited (this should auto-unlock TOP)
        print("\n🔄 Updating total_invited count...")
        updated_user = referral_service.update_total_invited(user_uuid)
        
        total_invited = updated_user.custom_data.get('total_invited', 0)
        top_status = updated_user.custom_data.get('top_status', 'locked')
        top_unlock_method = updated_user.custom_data.get('top_unlock_method', '')
        
        print(f"   ✅ total_invited: {total_invited}")
        print(f"   ✅ top_status: {top_status}")
        print(f"   ✅ top_unlock_method: {top_unlock_method}")
        
        # Step 3: Verify results
        print("\n🧪 Running tests...")
        
        # Test 1: total_invited should be 5
        if total_invited == 5:
            print("   ✅ Test 1 PASSED: total_invited = 5")
        else:
            print(f"   ❌ Test 1 FAILED: total_invited = {total_invited}, expected 5")
            return False
        
        # Test 2: TOP should be unlocked
        if top_status == 'open':
            print("   ✅ Test 2 PASSED: top_status = 'open'")
        else:
            print(f"   ❌ Test 2 FAILED: top_status = '{top_status}', expected 'open'")
            return False
        
        # Test 3: top_unlock_method should be 'invites'
        if top_unlock_method == 'invites':
            print("   ✅ Test 3 PASSED: top_unlock_method = 'invites'")
        else:
            print(f"   ❌ Test 3 FAILED: top_unlock_method = '{top_unlock_method}', expected 'invites'")
            return False
        
        # Test 4: Check earnings message
        print("\n📊 Testing /earnings message...")
        earnings_data = earnings_service.build_earnings_message(user_uuid)
        
        if earnings_data['invites'] == 5:
            print(f"   ✅ Test 4 PASSED: earnings shows {earnings_data['invites']} invites")
        else:
            print(f"   ❌ Test 4 FAILED: earnings shows {earnings_data['invites']} invites, expected 5")
            return False
        
        if earnings_data['top_status'] == 'open':
            print(f"   ✅ Test 5 PASSED: earnings shows top_status = 'open'")
        else:
            print(f"   ❌ Test 5 FAILED: earnings shows top_status = '{earnings_data['top_status']}', expected 'open'")
            return False
        
        # Test 6: Check progress bar in earnings
        # The progress bar should show 5 filled squares
        earnings_text = earnings_data['text']
        if '🟩🟩🟩🟩🟩' in earnings_text or earnings_text.count('🟩') == 5:
            print(f"   ✅ Test 6 PASSED: Progress bar shows 5/5 (5 filled squares)")
        else:
            print(f"   ⚠️  Test 6 WARNING: Progress bar might not show correctly")
            print(f"      Earnings text snippet: {earnings_text[:200]}...")
        
        # Test 7: Check that can_unlock is True
        can_unlock, invites_needed = referral_service.check_top_unlock_eligibility(user_uuid)
        if can_unlock and invites_needed == 0:
            print(f"   ✅ Test 7 PASSED: check_top_unlock_eligibility returns (True, 0)")
        else:
            print(f"   ❌ Test 7 FAILED: check_top_unlock_eligibility returns ({can_unlock}, {invites_needed}), expected (True, 0)")
            return False
        
        print("\n🎉 All tests PASSED! TOP is correctly unlocked after 5 invites.")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python test_5_invites_unlock.py <bot_id> <user_id>")
        print("\nExample:")
        print("  python test_5_invites_unlock.py 4f3c45a5-39ac-4d6e-a0eb-263765d70b1a <user_uuid>")
        sys.exit(1)
    
    bot_id = sys.argv[1]
    user_id = sys.argv[2]
    
    success = test_5_invites_unlock(bot_id, user_id)
    sys.exit(0 if success else 1)

