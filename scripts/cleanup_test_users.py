import sys
import os
import logging
from sqlalchemy import create_engine, or_, func
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models.user import User
from app.models.business_data import BusinessData

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WHITELIST_TERMS = ["mark", "anastasiia"]

def is_whitelisted(user):
    """Check if user matches whitelist terms in username or name"""
    if not user.custom_data:
        return False
        
    username = str(user.custom_data.get('username', '')).lower()
    first_name = str(user.custom_data.get('first_name', '')).lower()
    last_name = str(user.custom_data.get('last_name', '')).lower()
    
    for term in WHITELIST_TERMS:
        if term in username:
            return True
        if term in first_name:
            return True
        if term in last_name:
            return True
            
    return False

def cleanup_all_test_users(confirmed=False):
    """
    Find and delete ALL users who are NOT in the whitelist.
    """
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Get all users
        all_users = db.query(User).all()
        
        users_to_delete = []
        users_to_keep = []
        
        for user in all_users:
            if is_whitelisted(user):
                users_to_keep.append(user)
            else:
                users_to_delete.append(user)
        
        print(f"\nTotal users: {len(all_users)}")
        print(f"Users to KEEP ({len(users_to_keep)}):")
        for user in users_to_keep:
            username = user.custom_data.get('username', 'N/A')
            name = f"{user.custom_data.get('first_name', '')} {user.custom_data.get('last_name', '')}".strip()
            print(f"✅ {user.external_id} | {username} | {name}")
            
        print(f"\nUsers to DELETE ({len(users_to_delete)}):")
        for user in users_to_delete:
            username = user.custom_data.get('username', 'N/A')
            name = f"{user.custom_data.get('first_name', '')} {user.custom_data.get('last_name', '')}".strip()
            print(f"❌ {user.external_id} | {username} | {name}")

        if len(users_to_delete) == 0:
            print("\nNo users to delete.")
            return

        if confirmed:
            print(f"\nDeleting {len(users_to_delete)} users...")
            
            for user in users_to_delete:
                db.delete(user)
                
            # Aggressive cleanup of ALL logs for deleted users
            # AND any logs that look like test data (even if user is gone or not found)
            
            # 1. Delete BusinessData for deleted users (using their external_id)
            deleted_user_ids = [str(u.external_id) for u in users_to_delete]
            deleted_uuids = [str(u.id) for u in users_to_delete]
            
            # Fetch all logs
            all_logs = db.query(BusinessData).filter(
                BusinessData.data_type.in_(['log', 'wallet'])
            ).all()
            
            logs_to_delete = []
            for log in all_logs:
                data = log.data or {}
                
                # Check 1: Linked to deleted user UUID
                if str(data.get('user_id', '')) in deleted_uuids:
                    logs_to_delete.append(log)
                    continue
                    
                # Check 2: Linked to deleted user external_id
                if str(data.get('external_id', '')) in deleted_user_ids:
                    logs_to_delete.append(log)
                    continue

                # Check 3: Is explicitly a test log (starts with test_ or check_)
                ext_id = str(data.get('external_id', ''))
                if ext_id.startswith('test_') or ext_id.startswith('final_check') or ext_id.startswith('full_check'):
                    logs_to_delete.append(log)
                    continue
            
            # Deduplicate just in case
            logs_to_delete = list(set(logs_to_delete))
            
            for log in logs_to_delete:
                db.delete(log)
                
            db.commit()
            print(f"\n✅ Deleted {len(users_to_delete)} users and {len(logs_to_delete)} related records.")
            
        else:
            print("\n⚠️  Dry run mode. Use --confirm to actually delete.")

    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    confirm = "--confirm" in sys.argv
    cleanup_all_test_users(confirm)
