#!/usr/bin/env python3
"""
Hard delete bot from database (permanent deletion).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.bot import Bot
from uuid import UUID

def hard_delete_bot(bot_id: str):
    """Permanently delete bot from database."""
    db = SessionLocal()
    try:
        bot_uuid = UUID(bot_id)
        bot = db.query(Bot).filter(Bot.id == bot_uuid).first()
        
        if not bot:
            print(f"❌ Bot {bot_id} not found")
            return False
        
        print(f"🗑️  Deleting bot: {bot.name} (ID: {bot_id})")
        print(f"   Platform: {bot.platform_type}")
        print(f"   Active: {bot.is_active}")
        
        # Check if bot has any related data
        from app.models.user import User
        from app.models.business_data import BusinessData
        
        users_count = db.query(User).filter(User.bot_id == bot_uuid).count()
        partners_count = db.query(BusinessData).filter(
            BusinessData.bot_id == bot_uuid
        ).count()
        
        if users_count > 0 or partners_count > 0:
            print(f"⚠️  Warning: Bot has {users_count} users and {partners_count} business data records")
            response = input("   Continue with deletion? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Deletion cancelled")
                return False
        
        # Delete bot
        db.delete(bot)
        db.commit()
        
        print(f"✅ Bot {bot_id} permanently deleted")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hard_delete_bot.py <bot_id>")
        sys.exit(1)
    
    bot_id = sys.argv[1]
    success = hard_delete_bot(bot_id)
    sys.exit(0 if success else 1)

