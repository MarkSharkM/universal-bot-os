import os
import sys
import asyncio
import logging

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.business_data import BusinessData
from app.adapters.telegram import TelegramAdapter
from app.models.bot import Bot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def restore_icons():
    db = SessionLocal()
    adapter = TelegramAdapter()
    
    try:
        # Search for the problematic bots
        search_terms = ['randgift_bot', 'boinker_bot', 'EasyGiftDropbot', 'm5bank_bot']
        
        logger.info(f"Checking database for bots: {', '.join(search_terms)}")
        
        # Get all partners
        partners = db.query(BusinessData).filter(BusinessData.data_type == 'partner').all()
        
        # We need a valid bot_id to use the adapter (to get a token)
        # We'll use the bot_id from the first partner found
        bot_id = None
        if partners:
            bot_id = partners[0].bot_id
        
        if not bot_id:
            logger.error("No partners found, cannot determine bot_id")
            return

        logger.info(f"Using Bot ID: {bot_id}")
        
        updates_count = 0
        
        for partner in partners:
            data = partner.data
            link = data.get('referral_link', '')
            name = data.get('bot_name', 'Unknown')
            current_icon = data.get('icon')
            
            # Check if this partner matches any of our search terms
            is_match = False
            target_username = None
            
            for term in search_terms:
                if term.lower() in link.lower():
                    is_match = True
                    # Extract username from link
                    import re
                    match = re.search(r't\.me/([a-zA-Z0-9_]+)', link)
                    if match:
                        target_username = match.group(1)
                    break
            
            if is_match:
                logger.info(f"Found target bot: {name} ({target_username})")
                
                if current_icon:
                    logger.info(f"  - Already has icon: YES")
                    continue
                
                logger.info(f"  - Missing icon. Fetching...")
                
                if target_username:
                    try:
                        avatar_url = await adapter.get_bot_avatar_url(bot_id, target_username)
                        if avatar_url:
                            logger.info(f"  - FETCH SUCCESS: {avatar_url[:50]}...")
                            # Update DB
                            partner.data['icon'] = avatar_url
                            # Force SQLAlchemy to detect change in JSON field
                            from sqlalchemy.orm.attributes import flag_modified
                            flag_modified(partner, 'data')
                            updates_count += 1
                        else:
                            logger.warning(f"  - FETCH FAILED: No avatar found or error")
                    except Exception as e:
                        logger.error(f"  - ERROR: {e}")
                else:
                    logger.warning("  - Could not extract username from link")

        if updates_count > 0:
            db.commit()
            logger.info(f"SUCCESS: Updated {updates_count} partners with new icons.")
        else:
            logger.info("No updates needed.")
            
    except Exception as e:
        logger.error(f"Critical error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(restore_icons())
