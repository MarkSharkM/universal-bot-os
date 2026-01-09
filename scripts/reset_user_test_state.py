import os
import sys
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User

def reset_user_state(user_id_str):
    # DATABASE_URL should be set in environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Error: DATABASE_URL environment variable is not set.")
        return

    try:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        user_id = uuid.UUID(user_id_str)
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            print(f"❌ User with ID {user_id_str} not found.")
            return

        print(f"👤 Found user: {user.external_id} (Platform: {user.platform})")
        print(f"📂 Current custom_data: {user.custom_data}")
        
        # Reset flags
        if not user.custom_data:
            user.custom_data = {}
            
        modified = False
        
        if user.custom_data.get("did_start_7_flow"):
            user.custom_data["did_start_7_flow"] = False
            print("✅ Reset did_start_7_flow to False")
            modified = True
            
        if user.custom_data.get("has_seen_onboarding"):
            user.custom_data["has_seen_onboarding"] = False
            print("✅ Reset has_seen_onboarding to False")
            modified = True
            
        if modified:
            flag_modified(user, "custom_data")
            db.commit()
            print("🚀 User state reset successfully!")
        else:
            print("ℹ️ User state already clean (no flags to reset).")
            
        db.close()
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    # The ID we found in the logs
    DEFAULT_USER_ID = "8fdd6498-4635-4551-894a-32ebd20ef345"
    
    user_id_to_reset = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_USER_ID
    
    print(f"🔄 Resetting state for user {user_id_to_reset}...")
    reset_user_state(user_id_to_reset)
