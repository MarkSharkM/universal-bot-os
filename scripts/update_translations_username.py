#!/usr/bin/env python3
"""
Script to update translations in database: replace hardcoded username with {{bot_username}} placeholder.

Usage:
    python scripts/update_translations_username.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.translation import Translation
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_translations():
    """Update translations to replace hardcoded username with placeholder"""
    db: Session = SessionLocal()
    
    try:
        # Find all translations with hardcoded username
        translations_to_update = db.query(Translation).filter(
            (Translation.text.contains('HubAggregatorBot')) |
            (Translation.text.contains('EarnHubAggregatorBot'))
        ).all()
        
        logger.info(f"Found {len(translations_to_update)} translations to update")
        
        updates = {
            'HubAggregatorBot': '{{bot_username}}',
            '@HubAggregatorBot': '@{{bot_username}}',
            'EarnHubAggregatorBot': '{{bot_username}}',
            '@EarnHubAggregatorBot': '@{{bot_username}}',
        }
        
        updated_count = 0
        for translation in translations_to_update:
            original_text = translation.text
            new_text = original_text
            
            # Replace all occurrences
            for old, new in updates.items():
                new_text = new_text.replace(old, new)
            
            if new_text != original_text:
                translation.text = new_text
                updated_count += 1
                logger.info(f"Updated {translation.key} ({translation.lang}):")
                logger.info(f"  OLD: {original_text[:100]}...")
                logger.info(f"  NEW: {new_text[:100]}...")
        
        if updated_count > 0:
            db.commit()
            logger.info(f"✅ Successfully updated {updated_count} translations")
        else:
            logger.info("ℹ️  No translations needed updating")
        
        return updated_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error updating translations: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == '__main__':
    update_translations()
