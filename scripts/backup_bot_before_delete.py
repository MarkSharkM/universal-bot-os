#!/usr/bin/env python3
"""
Backup bot data before deletion - for recovery if needed.
"""
import sys
import os
import json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.bot import Bot
from app.models.user import User
from app.models.business_data import BusinessData
from app.models.message import Message
from uuid import UUID

def backup_bot_data(bot_id: str, output_file: str = None):
    """Backup all bot data to JSON file."""
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"backup_bot_{bot_id[:8]}_{timestamp}.json"
    
    db = SessionLocal()
    try:
        bot_uuid = UUID(bot_id)
        bot = db.query(Bot).filter(Bot.id == bot_uuid).first()
        
        if not bot:
            print(f"❌ Bot {bot_id} not found")
            return None
        
        print(f"📦 Backing up bot: {bot.name} (ID: {bot_id})")
        
        # Get all related data
        users = db.query(User).filter(User.bot_id == bot_uuid).all()
        business_data = db.query(BusinessData).filter(BusinessData.bot_id == bot_uuid).all()
        messages = db.query(Message).filter(Message.bot_id == bot_uuid).all()
        
        # Convert to dicts
        backup = {
            "backup_timestamp": datetime.now().isoformat(),
            "bot_id": str(bot_id),
            "bot": {
                "id": str(bot.id),
                "name": bot.name,
                "platform_type": bot.platform_type,
                "token": bot.token,  # Keep token for recovery
                "default_lang": bot.default_lang,
                "is_active": bot.is_active,
                "config": bot.config,
                "created_at": bot.created_at.isoformat() if bot.created_at else None,
                "updated_at": bot.updated_at.isoformat() if bot.updated_at else None,
            },
            "users": [
                {
                    "id": str(u.id),
                    "external_id": u.external_id,
                    "platform": u.platform,
                    "username": u.username,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "language_code": u.language_code,
                    "balance": float(u.balance),
                    "is_active": u.is_active,
                    "custom_data": u.custom_data,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                    "updated_at": u.updated_at.isoformat() if u.updated_at else None,
                }
                for u in users
            ],
            "business_data": [
                {
                    "id": str(bd.id),
                    "data_type": bd.data_type,
                    "data": bd.data if bd.data else {},
                    "deleted_at": bd.deleted_at.isoformat() if bd.deleted_at else None,
                    "created_at": bd.created_at.isoformat() if bd.created_at else None,
                    "updated_at": bd.updated_at.isoformat() if bd.updated_at else None,
                }
                for bd in business_data
            ],
            "messages": [
                {
                    "id": str(m.id),
                    "user_id": str(m.user_id),
                    "role": m.role,
                    "content": m.content,
                    "custom_data": m.custom_data,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                }
                for m in messages
            ],
            "counts": {
                "users": len(users),
                "business_data": len(business_data),
                "messages": len(messages),
            }
        }
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(backup, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Backup saved to: {output_file}")
        print(f"   - Bot: 1")
        print(f"   - Users: {len(users)}")
        print(f"   - Business Data: {len(business_data)}")
        print(f"   - Messages: {len(messages)}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backup_bot_before_delete.py <bot_id> [output_file]")
        sys.exit(1)
    
    bot_id = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    backup_file = backup_bot_data(bot_id, output_file)
    if backup_file:
        print(f"\n💾 Backup file: {os.path.abspath(backup_file)}")
        print("   You can use this to restore the bot if needed.")
    else:
        sys.exit(1)

