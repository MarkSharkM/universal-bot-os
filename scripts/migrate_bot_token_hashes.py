"""
Migration script: Populate token_hash for existing bots

This script fills token_hash column for bots that were created before
the token_hash feature was added.

Security architecture:
1. Read encrypted token from database
2. Decrypt token (in memory only)
3. Compute SHA-256 hash
4. Store hash in token_hash column
5. Token cleared from memory after hashing

Run this script after deploying migration 005_add_token_hash_to_bots.py

Usage:
    DATABASE_URL="postgresql://..." SECRET_KEY="..." python3 scripts/migrate_bot_token_hashes.py
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.core.database import SessionLocal
from app.models.bot import Bot
from app.utils.encryption import decrypt_token, hash_token
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_token_hashes():
    """
    Populate token_hash for all bots that don't have it.
    Handles both encrypted and plain-text tokens.
    """
    db = SessionLocal()
    try:
        # Find bots without token_hash
        bots_without_hash = db.query(Bot).filter(
            (Bot.token_hash == None) | (Bot.token_hash == "")
        ).all()
        
        logger.info(f"Found {len(bots_without_hash)} bots without token_hash")
        
        if not bots_without_hash:
            logger.info("All bots already have token_hash. Nothing to migrate.")
            return
        
        migrated_count = 0
        error_count = 0
        
        for bot in bots_without_hash:
            try:
                # Check if token is encrypted
                from app.utils.encryption import is_encrypted
                
                if is_encrypted(bot.token):
                    # Try to decrypt (might fail if different SECRET_KEY)
                    try:
                        decrypted_token = decrypt_token(bot.token)
                        logger.info(f"✅ Decrypted token for bot: {bot.name}")
                    except Exception as e:
                        logger.error(f"❌ Cannot decrypt token for bot {bot.id} ({bot.name}): {e}")
                        logger.error(f"   This bot was encrypted with a different SECRET_KEY")
                        logger.error(f"   Skipping this bot - manual intervention required")
                        error_count += 1
                        continue
                else:
                    # Token is plain-text (legacy bot)
                    decrypted_token = bot.token
                    logger.info(f"ℹ️  Bot {bot.name} has plain-text token (legacy)")
                
                # Compute hash
                token_hash_value = hash_token(decrypted_token)
                
                # Update bot
                bot.token_hash = token_hash_value
                
                logger.info(f"✅ Migrated bot: {bot.name} ({bot.id}) - hash: {token_hash_value[:16]}...")
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to migrate bot {bot.id} ({bot.name}): {e}")
                error_count += 1
                continue
        
        # Commit all changes
        db.commit()
        
        logger.info("=" * 60)
        logger.info(f"Migration complete!")
        logger.info(f"✅ Migrated: {migrated_count} bots")
        logger.info(f"❌ Errors: {error_count} bots")
        logger.info("=" * 60)
        
        if error_count > 0:
            logger.warning("Some bots failed migration. Check logs above.")
            logger.warning("Bots with different SECRET_KEY need manual token_hash update.")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting token_hash migration...")
    logger.info("This will populate token_hash for all bots without it.")
    logger.info("")
    
    migrate_token_hashes()
