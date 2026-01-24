import sys
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models.user import User

# Setup logging
logging.basicConfig(level=logging.ERROR)  # Only show errors to keep output clean

def inspect_users():
    """
    List all users to help identify non-test accounts.
    """
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        
        print(f"\nFound {len(users)} users in total:\n")
        print(f"{'External ID':<25} | {'Username':<20} | {'Name':<30} | {'Created At'}")
        print("-" * 100)
        
        for user in users:
            username = user.custom_data.get('username') or 'N/A'
            first_name = user.custom_data.get('first_name') or ''
            last_name = user.custom_data.get('last_name') or ''
            full_name = f"{first_name} {last_name}".strip() or 'N/A'
            created_at = user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else 'N/A'
            
            print(f"{str(user.external_id):<25} | {username:<20} | {full_name:<30} | {created_at}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_users()
