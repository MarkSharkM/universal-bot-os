import os
import sys
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User
from app.models.message import Message
from app.models.business_data import BusinessData

def hard_reset_user(user_id_str):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Error: DATABASE_URL environment variable is not set.")
        return

    try:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        user_uuid = uuid.UUID(user_id_str)
        user = db.query(User).filter(User.id == user_uuid).first()
        
        if not user:
            print(f"❌ User with ID {user_id_str} not found.")
            return

        external_id = user.external_id
        print(f"🔥 HARD RESET for user: {external_id} (UUID: {user_id_str})")
        
        # 1. Delete messages
        msg_count = db.query(Message).filter(Message.user_id == user_uuid).delete()
        print(f"🗑 Deleted {msg_count} messages")
        
        # 2. Delete business data (wallets, etc.)
        from sqlalchemy import cast, String
        bd_count = db.query(BusinessData).filter(
            cast(BusinessData.data['user_id'], String) == f'"{user_id_str}"'
        ).delete(synchronize_session=False)
        print(f"🗑 Deleted {bd_count} business data records")
        
        # 3. Delete user
        db.delete(user)
        print(f"💀 User record DELETED")
        
        db.commit()
        print("🚀 Hard reset completed successfully!")
        
        db.close()
    except Exception as e:
        print(f"💥 Error: {e}")
        db.rollback()

if __name__ == "__main__":
    DEFAULT_USER_ID = "8fdd6498-4635-4551-894a-32ebd20ef345"
    user_id_to_reset = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_USER_ID
    hard_reset_user(user_id_to_reset)
