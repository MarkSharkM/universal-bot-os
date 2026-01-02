#!/usr/bin/env python3
"""
Test referral counting logic
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.referral_service import ReferralService
from app.models.user import User
from app.models.business_data import BusinessData
from uuid import UUID

BOT_ID = UUID("4f3c45a5-39ac-4d6e-a0eb-263765d70b1a")

def test_referral_counting():
    """Test referral counting logic"""
    db = SessionLocal()
    try:
        referral_service = ReferralService(db, BOT_ID)
        
        # Find test user
        test_user = db.query(User).filter(
            User.bot_id == BOT_ID,
            User.external_id == "8144081672"
        ).first()
        
        if not test_user:
            print("❌ Test user not found (external_id=8144081672)")
            return False
        
        print(f"✅ Found test user: {test_user.id}")
        
        # Get current count
        current_count = referral_service.get_total_invited(test_user.id)
        print(f"📊 Current total_invited: {current_count}")
        
        # Count manually from logs
        manual_count = referral_service.count_referrals(test_user.id)
        print(f"📊 Manual count_referrals: {manual_count}")
        
        # Check logs
        logs = db.query(BusinessData).filter(
            BusinessData.bot_id == BOT_ID,
            BusinessData.data_type == 'log',
            BusinessData.data['inviter_external_id'].astext == test_user.external_id
        ).all()
        
        print(f"📋 Total logs for inviter: {len(logs)}")
        
        # Count unique external_ids
        unique_external_ids = set()
        referral_logs = 0
        for log in logs:
            data = log.data or {}
            is_referral = data.get('is_referral')
            if is_referral == True or is_referral == 'true' or is_referral == 'True':
                referral_logs += 1
                external_id = data.get('external_id', '')
                if external_id:
                    unique_external_ids.add(external_id)
        
        print(f"📋 Referral logs: {referral_logs}")
        print(f"📋 Unique external_ids: {len(unique_external_ids)}")
        print(f"📋 Unique IDs: {sorted(list(unique_external_ids))[:10]}...")
        
        # Verify
        if manual_count == len(unique_external_ids):
            print(f"✅ Count matches! {manual_count} = {len(unique_external_ids)}")
            return True
        else:
            print(f"❌ Count mismatch! SQL={manual_count}, Python={len(unique_external_ids)}")
            return False
            
    finally:
        db.close()

if __name__ == "__main__":
    success = test_referral_counting()
    sys.exit(0 if success else 1)

