
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import UUID

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings
from app.models.bot import Bot
from app.models.user import User

def debug_bot_and_user(bot_id_str, user_external_id):
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        bot_id = UUID(bot_id_str)
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            print(f"❌ Bot {bot_id_str} not found")
            return
        
        print(f"🤖 Bot Name: {bot.name}")
        print(f"⚙️ Bot Config: {bot.config}")
        
        user = db.query(User).filter(
            User.bot_id == bot_id,
            User.external_id == str(user_external_id)
        ).first()
        
        if not user:
            print(f"👤 User {user_external_id} not found for this bot")
        else:
            print(f"👤 User ID: {user.id}")
            print(f"👤 User External ID: {user.external_id}")
            print(f"👤 User Lang: {user.language_code}")
            print(f"👤 User Custom Data: {user.custom_data}")
            
    finally:
        db.close()

if __name__ == "__main__":
    # Bot ID from the URL/task context: 8fdd6498-4635-4551-894a-32ebd20ef345
    # User External ID (we need to find the user's ID, but I'll try to find any recent user if not provided)
    bot_id = "8fdd6498-4635-4551-894a-32ebd20ef345"
    
    # Try to find a user who recently connected a wallet or just any user
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    recent_user = db.query(User).filter(User.bot_id == bot_id).order_by(User.updated_at.desc()).first()
    db.close()
    
    target_external_id = recent_user.external_id if recent_user else "unknown"
    debug_bot_and_user(bot_id, target_external_id)
