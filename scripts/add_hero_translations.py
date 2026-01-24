#!/usr/bin/env python3
"""Add missing translations for Hero component"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.translation import Translation
from app.models.bot import Bot

def add_missing_translations():
    """Add 'saved' and 'change_link' translations"""
    engine = create_engine(str(settings.DATABASE_URL))
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Get all active Telegram bots
        bots = db.query(Bot).filter(
            Bot.platform_type == "telegram",
            Bot.is_active == True
        ).all()
        
        print(f"Found {len(bots)} active bots")
        
        translations_data = [
            # "saved" - Status for saved link
            {"key": "saved", "uk": "Збережено", "en": "Saved", "ru": "Сохранено", "de": "Gespeichert", "es": "Guardado"},
            # "change_link" - Helper text
            {"key": "change_link", "uk": "Змінити лінку?", "en": "Change link?", "ru": "Изменить ссылку?", "de": "Link ändern?", "es": "¿Cambiar enlace?"}
        ]
        
        for bot in bots:
            print(f"\nBot: {bot.name}")
            for trans_data in translations_data:
                key = trans_data["key"]
                for lang in ["uk", "en", "ru", "de", "es"]:
                    value = trans_data[lang]
                    
                    # Check if exists
                    existing = db.query(Translation).filter(
                        Translation.bot_id == bot.id,
                        Translation.key == key,
                        Translation.language == lang
                    ).first()
                    
                    if existing:
                        existing.value = value
                        print(f"  Updated: {key} ({lang}) = {value}")
                    else:
                        new_trans = Translation(
                            bot_id=bot.id,
                            key=key,
                            language=lang,
                            value=value
                        )
                        db.add(new_trans)
                        print(f"  Created: {key} ({lang}) = {value}")
        
        db.commit()
        print("\n✅ Translations added successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_missing_translations()
