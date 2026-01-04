#!/usr/bin/env python3
"""
Check invites for a specific user in the database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.services.referral_service import ReferralService
from app.models.user import User
from app.models.business_data import BusinessData
from uuid import UUID

BOT_ID = UUID("4f3c45a5-39ac-4d6e-a0eb-263765d70b1a")
EXTERNAL_ID = "380927579"  # mark_mark_23

def check_user_invites():
    """Check invites for a specific user"""
    db = SessionLocal()
    try:
        # Find user
        user = db.query(User).filter(
            User.bot_id == BOT_ID,
            User.external_id == EXTERNAL_ID
        ).first()
        
        if not user:
            print(f"❌ User not found (external_id={EXTERNAL_ID})")
            return False
        
        print(f"✅ Found user:")
        print(f"   ID: {user.id}")
        print(f"   External ID: {user.external_id}")
        print(f"   Username: {user.custom_data.get('username', 'N/A') if user.custom_data else 'N/A'}")
        print(f"   Current total_invited: {user.custom_data.get('total_invited', 0) if user.custom_data else 0}")
        print()
        
        # Check referral service count
        referral_service = ReferralService(db, BOT_ID)
        sql_count = referral_service.count_referrals(user.id)
        print(f"📊 SQL count_referrals result: {sql_count}")
        print()
        
        # Check all business_data logs for this inviter
        print("🔍 Checking business_data logs...")
        
        # All logs (including deleted)
        all_logs = db.query(BusinessData).filter(
            BusinessData.bot_id == BOT_ID,
            BusinessData.data_type == 'log'
        ).all()
        
        # Filter logs for this inviter
        inviter_logs = []
        for log in all_logs:
            if log.data and log.data.get('inviter_external_id') == EXTERNAL_ID:
                inviter_logs.append(log)
        
        print(f"📋 Total logs with inviter_external_id={EXTERNAL_ID}: {len(inviter_logs)}")
        
        # Count by deleted_at status
        active_logs = [log for log in inviter_logs if log.deleted_at is None]
        deleted_logs = [log for log in inviter_logs if log.deleted_at is not None]
        
        print(f"   ✅ Active (deleted_at IS NULL): {len(active_logs)}")
        print(f"   ❌ Deleted (deleted_at IS NOT NULL): {len(deleted_logs)}")
        print()
        
        # Check referral logs (is_referral = true)
        referral_logs = []
        for log in active_logs:
            data = log.data or {}
            is_referral = data.get('is_referral')
            if is_referral == True or is_referral == 'true' or is_referral == 'True':
                referral_logs.append(log)
        
        print(f"📋 Referral logs (is_referral=true): {len(referral_logs)}")
        
        # Count unique external_ids
        unique_external_ids = set()
        for log in referral_logs:
            data = log.data or {}
            external_id = data.get('external_id', '')
            if external_id:
                unique_external_ids.add(external_id)
        
        print(f"📋 Unique external_ids: {len(unique_external_ids)}")
        print(f"📋 Unique IDs: {sorted(list(unique_external_ids))}")
        print()
        
        # Execute raw SQL query (same as in count_referrals)
        sql_query = text("""
            SELECT COUNT(DISTINCT data->>'external_id') as count
            FROM business_data
            WHERE bot_id = CAST(:bot_id AS uuid)
              AND data_type = 'log'
              AND deleted_at IS NULL
              AND (data->>'inviter_external_id') = :inviter_external_id
              AND (
                (data->>'is_referral') IN ('true', 'True')
                OR (data->>'is_referral')::boolean = true
              )
              AND (data->>'external_id') IS NOT NULL
              AND (data->>'external_id') != ''
        """)
        
        result = db.execute(
            sql_query,
            {
                'bot_id': str(BOT_ID),
                'inviter_external_id': EXTERNAL_ID
            }
        ).first()
        
        sql_count_raw = result.count if result and hasattr(result, 'count') else 0
        print(f"📊 Raw SQL query result: {sql_count_raw}")
        print()
        
        # Compare
        print("🔍 Comparison:")
        print(f"   User custom_data['total_invited']: {user.custom_data.get('total_invited', 0) if user.custom_data else 0}")
        print(f"   referral_service.count_referrals(): {sql_count}")
        print(f"   Raw SQL query: {sql_count_raw}")
        print(f"   Python count (unique external_ids): {len(unique_external_ids)}")
        print()
        
        # Check if they match
        if sql_count == len(unique_external_ids) == sql_count_raw:
            print("✅ All counts match!")
            if user.custom_data.get('total_invited', 0) != sql_count:
                print(f"⚠️  WARNING: user.custom_data['total_invited'] ({user.custom_data.get('total_invited', 0)}) doesn't match SQL count ({sql_count})")
                print("   This means total_invited needs to be updated!")
                return False
            return True
        else:
            print("❌ Count mismatch!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = check_user_invites()
    sys.exit(0 if success else 1)
