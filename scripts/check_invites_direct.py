#!/usr/bin/env python3
"""
Direct database check for user invites
Uses SQLAlchemy to connect and query PostgreSQL
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.user import User
from app.models.business_data import BusinessData
from uuid import UUID

BOT_ID = UUID("4f3c45a5-39ac-4d6e-a0eb-263765d70b1a")
EXTERNAL_ID = "380927579"

def check_invites_direct():
    """Direct database check"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("🔍 CHECKING INVITES FOR USER (external_id = 380927579)")
        print("=" * 80)
        print()
        
        # 1. Find user
        print("1️⃣ Finding user...")
        user = db.query(User).filter(
            User.bot_id == BOT_ID,
            User.external_id == EXTERNAL_ID
        ).first()
        
        if not user:
            print(f"❌ User not found (external_id={EXTERNAL_ID})")
            return False
        
        print(f"✅ User found:")
        print(f"   ID: {user.id}")
        print(f"   External ID: {user.external_id}")
        print(f"   Username: {user.custom_data.get('username', 'N/A') if user.custom_data else 'N/A'}")
        print(f"   Current total_invited: {user.custom_data.get('total_invited', 0) if user.custom_data else 0}")
        print()
        
        # 2. Count all logs (including deleted)
        print("2️⃣ Counting all business_data logs...")
        all_logs_query = text("""
            SELECT 
                COUNT(*) as total_logs,
                COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as active_logs,
                COUNT(CASE WHEN deleted_at IS NOT NULL THEN 1 END) as deleted_logs
            FROM business_data
            WHERE bot_id = CAST(:bot_id AS uuid)
              AND data_type = 'log'
              AND (data->>'inviter_external_id') = :inviter_external_id
        """)
        
        result = db.execute(all_logs_query, {
            'bot_id': str(BOT_ID),
            'inviter_external_id': EXTERNAL_ID
        }).first()
        
        print(f"   Total logs: {result.total_logs}")
        print(f"   Active logs: {result.active_logs}")
        print(f"   Deleted logs: {result.deleted_logs}")
        print()
        
        # 3. Count referral logs (SQL query - same as in count_referrals)
        print("3️⃣ Counting referral logs (SQL query from count_referrals)...")
        referral_count_query = text("""
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
        
        result = db.execute(referral_count_query, {
            'bot_id': str(BOT_ID),
            'inviter_external_id': EXTERNAL_ID
        }).first()
        
        sql_count = result.count if result and hasattr(result, 'count') else 0
        print(f"   SQL count (unique referrals): {sql_count}")
        print()
        
        # 4. Show all referral logs with details
        print("4️⃣ All referral logs (active only):")
        referral_logs_query = text("""
            SELECT 
                id,
                data->>'external_id' as referred_external_id,
                data->>'user_id' as referred_user_id,
                data->>'is_referral' as is_referral,
                data->>'click_type' as click_type,
                data->>'event_type' as event_type,
                created_at,
                deleted_at
            FROM business_data
            WHERE bot_id = CAST(:bot_id AS uuid)
              AND data_type = 'log'
              AND deleted_at IS NULL
              AND (data->>'inviter_external_id') = :inviter_external_id
              AND (
                (data->>'is_referral') IN ('true', 'True')
                OR (data->>'is_referral')::boolean = true
              )
            ORDER BY created_at DESC
        """)
        
        logs = db.execute(referral_logs_query, {
            'bot_id': str(BOT_ID),
            'inviter_external_id': EXTERNAL_ID
        }).fetchall()
        
        print(f"   Found {len(logs)} referral logs:")
        for i, log in enumerate(logs, 1):
            print(f"   {i}. external_id={log.referred_external_id}, user_id={log.referred_user_id}, "
                  f"click_type={log.click_type}, created_at={log.created_at}")
        print()
        
        # 5. Show unique external_ids
        print("5️⃣ Unique external_ids that were referred:")
        unique_query = text("""
            SELECT DISTINCT
                data->>'external_id' as referred_external_id,
                COUNT(*) as referral_count,
                MIN(created_at) as first_referral,
                MAX(created_at) as last_referral
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
            GROUP BY data->>'external_id'
            ORDER BY first_referral DESC
        """)
        
        unique_refs = db.execute(unique_query, {
            'bot_id': str(BOT_ID),
            'inviter_external_id': EXTERNAL_ID
        }).fetchall()
        
        print(f"   Found {len(unique_refs)} unique referrals:")
        for i, ref in enumerate(unique_refs, 1):
            print(f"   {i}. external_id={ref.referred_external_id}, "
                  f"count={ref.referral_count}, first={ref.first_referral}")
        print()
        
        # 6. Summary
        print("=" * 80)
        print("📊 SUMMARY:")
        print("=" * 80)
        current_total = user.custom_data.get('total_invited', 0) if user.custom_data else 0
        print(f"   User custom_data['total_invited']: {current_total}")
        print(f"   SQL count (unique referrals): {sql_count}")
        print(f"   Python count (unique external_ids): {len(unique_refs)}")
        print()
        
        if current_total == sql_count == len(unique_refs):
            print("✅ All counts match!")
            return True
        else:
            print("❌ Count mismatch!")
            if current_total != sql_count:
                print(f"   ⚠️  user.custom_data['total_invited'] ({current_total}) != SQL count ({sql_count})")
                print(f"   💡 Need to update total_invited!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = check_invites_direct()
    sys.exit(0 if success else 1)
