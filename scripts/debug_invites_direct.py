import sys
import os
import logging
from sqlalchemy import text, cast, String
from uuid import UUID

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.business_data import BusinessData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_invites():
    db = SessionLocal()
    try:
        bot_id = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
        inviter_external_id = "380927579"
        
        print(f"--- Debugging Invites for User {inviter_external_id} ---")
        
        # 1. Get User Record
        user = db.query(User).filter(
            User.bot_id == bot_id,
            User.external_id == inviter_external_id
        ).first()
        
        if not user:
            print("User not found!")
            return
            
        print(f"User ID: {user.id}")
        print(f"Custom Data: {user.custom_data}")
        current_total = user.custom_data.get('total_invited', 0) if user.custom_data else 0
        print(f"Stored total_invited: {current_total}")
        
        # 2. Count Active Logs (Raw SQL - mimicking logic)
        query_active = text("""
            SELECT COUNT(*) as count
            FROM business_data
            WHERE bot_id = CAST(:bot_id AS uuid)
              AND data_type = 'log'
              AND deleted_at IS NULL
              AND (data->>'inviter_external_id') = :inviter_external_id
              AND (
                (data->>'is_referral') IN ('true', 'True')
                OR (data->>'is_referral')::boolean = true
              )
        """)
        
        result_active = db.execute(query_active, {
            'bot_id': bot_id, 
            'inviter_external_id': inviter_external_id
        }).first()
        print(f"Active Referral Logs (Raw SQL): {result_active.count}")

        # 3. Count Soft-Deleted Logs
        query_deleted = text("""
            SELECT COUNT(*) as count
            FROM business_data
            WHERE bot_id = CAST(:bot_id AS uuid)
              AND data_type = 'log'
              AND deleted_at IS NOT NULL
              AND (data->>'inviter_external_id') = :inviter_external_id
              AND (
                (data->>'is_referral') IN ('true', 'True')
                OR (data->>'is_referral')::boolean = true
              )
        """)
        
        result_deleted = db.execute(query_deleted, {
            'bot_id': bot_id, 
            'inviter_external_id': inviter_external_id
        }).first()
        print(f"Soft-Deleted Referral Logs (Raw SQL): {result_deleted.count}")
        
        # 4. List some sample logs to check format
        print("\n--- Sample Active Logs ---")
        logs = db.query(BusinessData).filter(
            BusinessData.bot_id == bot_id,
            BusinessData.data_type == 'log',
            BusinessData.deleted_at.is_(None),
            cast(BusinessData.data['inviter_external_id'], String) == inviter_external_id
        ).limit(5).all()
        
        for log in logs:
            print(f"ID: {log.id}, Data: {log.data}")

    finally:
        db.close()

if __name__ == "__main__":
    debug_invites()
