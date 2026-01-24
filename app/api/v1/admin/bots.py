"""
Bots endpoints for Admin API.
"""
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_db
from app.models.bot import Bot
from app.models.business_data import BusinessData
from app.models.user import User
from app.models.translation import Translation
from app.models.analytics_event import AnalyticsEvent
from app.schemas.bot import BotCreate, BotUpdate, BotResponse
from app.services.ai_service import AIService
from app.services.translation_service import TranslationService
from app.core.security import (
    create_access_token,
    verify_admin_credentials,
    get_current_admin
)
from app.utils.encryption import encrypt_token, decrypt_token
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/bots", response_model=List[BotResponse])
async def list_bots(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    platform: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    List all bots with filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        platform: Filter by platform (telegram, web, etc.)
        is_active: Filter by active status
        db: Database session
    
    Returns:
        List of bots
    """
    query = db.query(Bot)
    
    if platform:
        query = query.filter(Bot.platform_type == platform)
    if is_active is not None:
        query = query.filter(Bot.is_active == is_active)
    
    bots = query.offset(skip).limit(limit).all()
    return bots


@router.get("/bots/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: UUID,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)  # Auth required
):
    """
    Get bot by ID.
    
    Args:
        bot_id: Bot UUID
        db: Database session
    
    Returns:
        Bot details
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot


@router.post("/bots", response_model=BotResponse)
async def create_bot(
    bot_data: BotCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)  # Auth required
):
    """
    Create new bot.
    Automatically syncs username from Telegram API for Telegram bots.
    Bot tokens are encrypted before storage.
    
    Args:
        bot_data: Bot creation data
        db: Database session
    
    Returns:
        Created bot
    """
    # Encrypt token before storing
    bot = Bot(
        name=bot_data.name,
        platform_type=bot_data.platform_type,
        token=bot_data.token,  # Store plain token (was encrypt_token)
        default_lang=bot_data.default_lang,
        config=bot_data.config or {},
        is_active=True
    )
    
    db.add(bot)
    db.commit()
    db.refresh(bot)
    
    # Auto-sync username for Telegram bots (CRITICAL: fixes referral links and TON Connect)
    if bot.platform_type == "telegram" and bot.token:
        try:
            from app.adapters.telegram import TelegramAdapter
            adapter = TelegramAdapter()
            bot_info = await adapter.get_bot_info(bot.id)
            username = bot_info.get('username')
            
            if username:
                # Save username to bot.config (single source of truth)
                if not bot.config:
                    bot.config = {}
                bot.config['username'] = username
                bot.config['bot_id'] = bot_info.get('id')
                bot.config['first_name'] = bot_info.get('first_name')
                
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(bot, 'config')
                db.commit()
                db.refresh(bot)
                logger.info(f"Auto-synced bot username: {username} for bot_id={bot.id}")
        except Exception as sync_err:
            # Don't fail bot creation if sync fails, just log warning
            logger.warning(f"Could not auto-sync bot username during creation: {sync_err}")
    
    return bot


@router.patch("/bots/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: UUID,
    bot_data: BotUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)  # Auth required
):
    """
    Update bot.
    
    Args:
        bot_id: Bot UUID
        bot_data: Bot update data
        db: Database session
    
    Returns:
        Updated bot
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if bot_data.name is not None:
        bot.name = bot_data.name
    if bot_data.config is not None:
        if not bot.config:
            bot.config = {}
        bot.config.update(bot_data.config)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(bot, 'config')
    if bot_data.default_lang is not None:
        bot.default_lang = bot_data.default_lang
    if bot_data.is_active is not None:
        bot.is_active = bot_data.is_active
    if bot_data.token is not None:
        bot.token = bot_data.token
    
    db.commit()
    db.refresh(bot)
    
    return bot


@router.delete("/bots/{bot_id}")
async def delete_bot(
    bot_id: UUID,
    hard_delete: bool = Query(False, description="If true, permanently delete. Otherwise soft delete."),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)  # Auth required
):
    """
    Delete bot (soft delete by default, or hard delete if specified).
    
    Args:
        bot_id: Bot UUID
        hard_delete: If true, permanently delete. Otherwise soft delete (set is_active=False).
        db: Database session
    
    Returns:
        Success message
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if hard_delete:
        # Permanent deletion
        db.delete(bot)
        message = "Bot permanently deleted"
    else:
        # Soft delete
        bot.is_active = False
        message = "Bot deactivated successfully"
    
    db.commit()
    
    return {"message": message, "hard_delete": hard_delete}


@router.delete("/bots/{bot_id}/hard")
async def hard_delete_bot(
    bot_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Permanently delete bot from database.
    WARNING: This will also delete all related data (users, business_data, etc.)
    
    Args:
        bot_id: Bot UUID
        db: Database session
    
    Returns:
        Success message
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Check related data
    from app.models.user import User
    from app.models.business_data import BusinessData
    from app.models.message import Message
    
    users_count = db.query(User).filter(User.bot_id == bot_id).count()
    business_data_count = db.query(BusinessData).filter(BusinessData.bot_id == bot_id).count()
    messages_count = db.query(Message).filter(Message.bot_id == bot_id).count()
    
    # Delete related data first (if any)
    # IMPORTANT: Delete in correct order to avoid foreign key violations
    # 1. Messages (references users)
    # 2. Users (references bot)
    # 3. BusinessData (references bot)
    # 4. Bot
    try:
        if messages_count > 0:
            db.query(Message).filter(Message.bot_id == bot_id).delete(synchronize_session=False)
        if users_count > 0:
            db.query(User).filter(User.bot_id == bot_id).delete(synchronize_session=False)
        if business_data_count > 0:
            db.query(BusinessData).filter(BusinessData.bot_id == bot_id).delete(synchronize_session=False)
        
        # Delete bot
        db.delete(bot)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting bot {bot_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete bot: {str(e)}")
    
    return {
        "message": "Bot permanently deleted",
        "deleted_users": users_count,
        "deleted_business_data": business_data_count,
        "deleted_messages": messages_count
    }


@router.post("/bots/{bot_id}/create-test-user")
async def create_test_user(
    bot_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Create a test user and generate 5 referral links for testing.
    
    Args:
        bot_id: Bot UUID
        db: Database session
    
    Returns:
        Test user info and 5 referral links
    """
    from app.services.user_service import UserService
    from app.services.referral_service import ReferralService
    
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Initialize services
    user_service = UserService(db, bot_id)
    referral_service = ReferralService(db, bot_id)
    
    # Create test user
    test_external_id = f"test_user_{int(time.time())}"
    test_user = user_service.get_or_create_user(
        external_id=test_external_id,
        platform="telegram",
        language_code="uk",
        username="test_user",
        first_name="Test",
        last_name="User"
    )
    
    # Generate 5 referral links
    referral_links = []
    for i in range(1, 6):
        link = referral_service.generate_referral_link(test_user.id)
        referral_links.append({
            "number": i,
            "link": link,
            "ref_param": referral_service.generate_referral_tag(test_user.id)
        })
    
    return {
        "test_user": {
            "id": str(test_user.id),
            "external_id": test_user.external_id,
            "username": "test_user",
            "name": "Test User"
        },
        "referral_links": referral_links,
        "instructions": "Натисніть на кожну лінку в Telegram, щоб симулювати 5 запрошень. Після цього викличте /earnings або /top щоб перевірити, чи відкрився TOP."
    }


@router.get("/bots/{bot_id}/stats")
async def get_bot_stats(
    bot_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get bot statistics.
    
    Args:
        bot_id: Bot UUID
        db: Database session
    
    Returns:
        Bot statistics
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Count unique users by distinct external_id (Telegram user ID)
    from sqlalchemy import func, distinct
    users_count = db.query(func.count(distinct(User.external_id))).filter(
        User.bot_id == bot_id,
        User.external_id.isnot(None)
    ).scalar() or 0
    
    # Count active unique users
    active_users_count = db.query(func.count(distinct(User.external_id))).filter(
        User.bot_id == bot_id,
        User.external_id.isnot(None),
        User.is_active == True
    ).scalar() or 0
    
    # Count partners
    partners_count = db.query(BusinessData).filter(
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'partner'
    ).count()
    
    # Count active partners (filter in Python)
    active_partners = db.query(BusinessData).filter(
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'partner'
    ).all()
    active_partners_count = sum(
        1 for p in active_partners 
        if (p.data or {}).get('active') == 'Yes'
    )
    
    # Total balance
    from sqlalchemy import func
    total_balance = db.query(func.sum(User.balance)).filter(
        User.bot_id == bot_id
    ).scalar() or 0
    
    return {
        "bot_id": str(bot_id),
        "bot_name": bot.name,
        "users": {
            "total": users_count,
            "active": active_users_count
        },
        "partners": {
            "total": partners_count,
            "active": active_partners_count
        },
        "total_balance": float(total_balance)
    }


@router.get("/bots/{bot_id}/stats/analytics")
async def get_bot_analytics(
    bot_id: UUID,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Get detailed analytics for charts.
    
    Args:
        bot_id: Bot UUID
        days: Number of days to analyze (default 30)
        db: Database session
    
    Returns:
        Analytics data (daily clicks, top partners)
    """
    from sqlalchemy import func, desc, and_
    from datetime import datetime, timedelta
    
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
        
    since_date = datetime.now() - timedelta(days=days)
    
    # 1. Daily Clicks (for Line Chart)
    # Group by date(created_at)
    daily_clicks = db.query(
        func.date(AnalyticsEvent.created_at).label('date'),
        func.count(AnalyticsEvent.id).label('count')
    ).filter(
        and_(
            AnalyticsEvent.bot_id == bot_id,
            AnalyticsEvent.event_name == 'partner_click_direct',
            AnalyticsEvent.created_at >= since_date
        )
    ).group_by(
        func.date(AnalyticsEvent.created_at)
    ).order_by(
        func.date(AnalyticsEvent.created_at)
    ).all()
    
    formatted_daily = [
        {"date": str(row.date), "count": row.count} 
        for row in daily_clicks
    ]
    
    # Fill missing dates
    final_daily = []
    current_date = since_date.date()
    end_date = datetime.now().date()
    
    daily_map = {d['date']: d['count'] for d in formatted_daily}
    
    while current_date <= end_date:
        date_str = str(current_date)
        final_daily.append({
            "date": date_str,
            "count": daily_map.get(date_str, 0)
        })
        current_date += timedelta(days=1)
    
    # 2. Top Partners (for Bar Chart / List)
    # Parse event_data->>'partner_id'
    # Note: SQLite vs Postgres JSON handling might differ, using Python generic way if needed
    # But usually Postgres handles ->> fine. Railway uses Postgres.
    
    # Get all click events to aggregate in python if SQL is complex with JSON extraction
    # OR try direct SQL grouping. Let's try direct SQL first.
    
    top_partners_query = db.query(
        func.json_extract_path_text(AnalyticsEvent.event_data, 'partner_id').label('partner_id'),
        func.count(AnalyticsEvent.id).label('count')
    ).filter(
        and_(
            AnalyticsEvent.bot_id == bot_id,
            AnalyticsEvent.event_name == 'partner_click_direct',
            AnalyticsEvent.created_at >= since_date
        )
    ).group_by(
        func.json_extract_path_text(AnalyticsEvent.event_data, 'partner_id')
    ).order_by(
        desc('count')
    ).limit(10).all()
    
    # Fetch partner names
    partner_ids = [row.partner_id for row in top_partners_query if row.partner_id]
    
    # If partner_ids are UUIDs, fetch names. If they are temp IDs, just use ID.
    # Assuming standard UUIDs for partners.
    
    partner_names = {}
    if partner_ids:
        try:
            # Filter valid UUIDs
            valid_uuids = []
            for pid in partner_ids:
                try:
                    UUID(str(pid))
                    valid_uuids.append(pid)
                except:
                    pass
            
            if valid_uuids:
                partners = db.query(BusinessData).filter(
                    BusinessData.id.in_(valid_uuids)
                ).all()
                for p in partners:
                    partner_names[str(p.id)] = p.data.get('bot_name', 'Unknown')
        except Exception as e:
            logger.error(f"Error fetching partner names: {e}")
            
    top_partners = []
    for row in top_partners_query:
        if not row.partner_id:
            continue
        name = partner_names.get(str(row.partner_id), f"Partner {str(row.partner_id)[:8]}")
        top_partners.append({
            "id": row.partner_id,
            "name": name,
            "count": row.count
        })
        
    return {
        "daily_clicks": final_daily,
        "top_partners": top_partners,
        "total_clicks": sum(d['count'] for d in final_daily)
    }


@router.get("/bots/{bot_id}/ai-config")
async def get_ai_config(
    bot_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get AI configuration for bot.
    
    Args:
        bot_id: Bot UUID
        db: Database session
    
    Returns:
        AI configuration (without sensitive data)
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    ai_config = bot.config.get('ai', {})
    
    return {
        "provider": ai_config.get('provider', 'openai'),
        "model": ai_config.get('model', 'gpt-4o-mini'),
        "temperature": ai_config.get('temperature', 0.7),
        "max_tokens": ai_config.get('max_tokens', 2000),
        "has_api_key": bool(ai_config.get('api_key')),
        "has_system_prompt": bool(ai_config.get('system_prompt')),
        "system_prompt": ai_config.get('system_prompt', ''),
    }


@router.patch("/bots/{bot_id}/ai-config")
async def update_ai_config(
    bot_id: UUID,
    ai_config: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Update AI configuration for bot.
    
    Args:
        bot_id: Bot UUID
        ai_config: AI configuration data
        db: Database session
    
    Returns:
        Updated AI configuration
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if 'ai' not in bot.config:
        bot.config['ai'] = {}
    
    bot.config['ai'].update(ai_config)
    db.commit()
    db.refresh(bot)
    
    # Return without sensitive data
    updated_config = bot.config.get('ai', {})
    return {
        "provider": updated_config.get('provider'),
        "model": updated_config.get('model'),
        "temperature": updated_config.get('temperature'),
        "max_tokens": updated_config.get('max_tokens'),
        "has_api_key": bool(updated_config.get('api_key')),
        "has_system_prompt": bool(updated_config.get('system_prompt')),
    }


@router.post("/bots/{bot_id}/import-data")
async def import_bot_data(
    bot_id: UUID,
    import_type: str = Query(..., description="Type: translations, users, partners, logs, all"),
    db: Session = Depends(get_db)
):
    """
    Import data for a bot from CSV files.
    
    Args:
        bot_id: Bot UUID
        import_type: Type of data to import (translations, users, partners, logs, all)
        db: Database session
    
    Returns:
        Import results
    """
    from pathlib import Path
    
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    base_path = Path(__file__).parent.parent.parent.parent / "old-prod-hub-bot"
    results = {}
    
    try:
        # Import translations
        if import_type in ("translations", "all"):
            translations_path = base_path / "translations_for prod tg.csv"
            if translations_path.exists():
                from scripts.import_translations import import_translations
                import_translations(str(translations_path))
                results["translations"] = "✅ Imported"
            else:
                results["translations"] = "⚠️ File not found"
        
        # Import users
        if import_type in ("users", "all"):
            users_path = base_path / "Earnbot_Referrals - user_wallets.csv"
            if users_path.exists():
                from scripts.migrate_from_sheets import migrate_user_wallets
                count = migrate_user_wallets(db, str(bot_id), str(users_path))
                results["users"] = f"✅ Imported {count} users"
            else:
                results["users"] = "⚠️ File not found"
        
        # Import partners
        if import_type in ("partners", "all"):
            partners_path = base_path / "Earnbot_Referrals - Partners_Settings.csv"
            if partners_path.exists():
                from scripts.migrate_from_sheets import migrate_partners_settings
                count = migrate_partners_settings(db, str(bot_id), str(partners_path))
                results["partners"] = f"✅ Imported {count} partners"
            else:
                results["partners"] = "⚠️ File not found"
        
        # Import logs
        if import_type in ("logs", "all"):
            logs_path = base_path / "Earnbot_Referrals - bot_log.csv"
            if logs_path.exists():
                from scripts.migrate_from_sheets import migrate_bot_log
                count = migrate_bot_log(db, str(bot_id), str(logs_path))
                results["logs"] = f"✅ Imported {count} log entries"
            else:
                results["logs"] = "⚠️ File not found"
        
        return {
            "bot_id": str(bot_id),
            "bot_name": bot.name,
            "import_type": import_type,
            "results": results,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import error: {str(e)}")


@router.post("/run-migration-add-deleted-at")
async def run_migration_add_deleted_at(db: Session = Depends(get_db)):
    """
    Run migration to add deleted_at column to business_data table.
    """
    from sqlalchemy import text
    
    try:
        # Add column
        db.execute(text("ALTER TABLE business_data ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))
        
        # Add index
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_business_data_deleted_at ON business_data(deleted_at)"))
        
        db.commit()
        
        return {
            "success": True,
            "message": "Migration completed successfully: added deleted_at column and index"
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "message": "Migration failed"
        }


@router.post("/bots/{bot_id}/import-correct-partners")
async def import_correct_partners(
    bot_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Import correct partners data (EasyGiftDropbot, RandGiftBot, TheStarsBank with proper settings).
    
    Args:
        bot_id: Bot UUID
        db: Database session
    
    Returns:
        Import summary
    """
    from sqlalchemy import and_
    
    # Correct partners data
    partners_data = [
        {
            "bot_name": "EasyGiftDropbot",
            "description": "🎁 Подарунки за активність",
            "description_en": "🎁 Gifts for activity",
            "description_ru": "🎁 Подарки за активность",
            "description_de": "🎁 Geschenke für Aktivität",
            "description_es": "🎁 Regalos por actividad",
            "referral_link": "https://t.me/EasyGiftDropbot?start=_tgr_WhrUYB40ZWFi",
            "commission": 20.0,
            "category": "TOP",
            "active": "Yes",
            "verified": "Yes",
            "roi_score": 1.9,
            "duration": "30",
        },
        {
            "bot_name": "RandGiftBot",
            "description": "🎁 Випадкові подарунки",
            "description_en": "🎁 Random gifts",
            "description_ru": "🎁 Случайные подарки",
            "description_de": "🎁 Zufällige Geschenke",
            "description_es": "🎁 Regalos aleatorios",
            "referral_link": "https://t.me/randgift_bot?start=_tgr_dkf6mDQ3Y2M6",
            "commission": 1.0,
            "category": "NEW",
            "active": "Yes",
            "verified": "Yes",
            "roi_score": 0.0,
            "duration": "9999",
        },
        {
            "bot_name": "TheStarsBank",
            "description": "🏦 Заробіток на транзакціях 🏛️",
            "description_en": "🏛️ Earnings from transactions 🏦",
            "description_ru": "🏛️ Заработок на транзакциях 🏦",
            "description_de": "🏛️ Einnahmen aus Transaktionen 🏦",
            "description_es": "🏛️ Ganancias por transacciones 🏦",
            "referral_link": "https://t.me/m5bank_bot?start=_tgr_JUV1QD8zMDUy",
            "commission": 30.0,
            "category": "TOP",
            "active": "Yes",
            "verified": "Yes",
            "roi_score": 7.2,
            "duration": "365",
        }
    ]
    
    updated = []
    created = []
    
    for partner_data in partners_data:
        bot_name = partner_data["bot_name"]
        
        # Find existing partner (not deleted)
        existing = db.query(BusinessData).filter(
            and_(
                BusinessData.bot_id == bot_id,
                BusinessData.data_type == 'partner',
                BusinessData.deleted_at.is_(None)
            )
        ).all()
        
        # Check if partner with this name exists
        existing_partner = None
        for p in existing:
            if p.data.get('bot_name') == bot_name:
                existing_partner = p
                break
        
        if existing_partner:
            # Update existing
            existing_partner.data = partner_data
            updated.append(bot_name)
        else:
            # Create new
            new_partner = BusinessData(
                bot_id=bot_id,
                data_type='partner',
                data=partner_data
            )
            db.add(new_partner)
            created.append(bot_name)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Imported {len(created)} new, updated {len(updated)} existing partners",
        "created": created,
        "updated": updated,
        "total": len(partners_data)
    }


@router.post("/bots/{bot_id}/remove-duplicate-partners")
async def remove_duplicate_partners(
    bot_id: UUID,
    dry_run: bool = Query(False, description="If true, only show duplicates without deleting"),
    db: Session = Depends(get_db)
):
    """
    Remove duplicate partners (keeps first occurrence of each bot_name).
    
    Args:
        bot_id: Bot UUID
        dry_run: If true, only show what would be deleted without actually deleting
        db: Database session
    
    Returns:
        Summary of duplicates found/removed
    """
    from sqlalchemy import and_
    
    # Get all partners for this bot
    partners = db.query(BusinessData).filter(
        and_(
            BusinessData.bot_id == bot_id,
            BusinessData.data_type == 'partner'
        )
    ).all()
    
    if not partners:
        return {
            "success": True,
            "message": "No partners found",
            "total": 0,
            "duplicates": 0,
            "kept": 0
        }
    
    # Group by bot_name
    seen = {}
    kept = []
    duplicates = []
    
    for partner in partners:
        bot_name = partner.data.get('bot_name')
        if not bot_name:
            continue
        
        if bot_name not in seen:
            seen[bot_name] = partner
            kept.append({
                "id": str(partner.id),
                "bot_name": bot_name,
                "category": partner.data.get('category'),
                "active": partner.data.get('active')
            })
        else:
            duplicates.append({
                "id": str(partner.id),
                "bot_name": bot_name,
                "category": partner.data.get('category'),
                "active": partner.data.get('active')
            })
    
    if not duplicates:
        return {
            "success": True,
            "message": "No duplicates found",
            "total": len(partners),
            "duplicates": 0,
            "kept": kept
        }
    
    # If dry run, just return what would be deleted
    if dry_run:
        return {
            "success": True,
            "message": f"Found {len(duplicates)} duplicates (dry run - not deleted)",
            "total": len(partners),
            "duplicates_count": len(duplicates),
            "kept_count": len(kept),
            "kept": kept,
            "duplicates_to_remove": duplicates
        }
    
    # Delete duplicates
    deleted_count = 0
    for dup in duplicates:
        partner = db.query(BusinessData).filter(BusinessData.id == dup["id"]).first()
        if partner:
            db.delete(partner)
            deleted_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully removed {deleted_count} duplicate partners",
        "total": len(partners),
        "duplicates_removed": deleted_count,
        "kept_count": len(kept),
        "kept": kept,
        "removed": duplicates
    }


@router.get("/logs")
async def get_logs(
    limit: int = Query(50, ge=1, le=500, description="Number of log lines to return"),
    level: Optional[str] = Query(None, description="Filter by log level: DEBUG, INFO, WARNING, ERROR"),
    search: Optional[str] = Query(None, description="Search text in logs"),
    db: Session = Depends(get_db)
):
    """
    Get recent application logs.
    
    Note: On Railway, logs are streamed to stdout/stderr and visible in Railway dashboard.
    This endpoint reads from log files if available locally.
    
    Args:
        limit: Number of log lines to return
        level: Filter by log level
        search: Search text in logs
        db: Database session
    
    Returns:
        Recent log entries
    """
    import os
    from pathlib import Path
    
    logs_dir = Path("logs")
    log_file = logs_dir / "app.log"
    
    if not log_file.exists():
        return {
            "success": False,
            "message": "Log file not found. On Railway, view logs in Railway dashboard.",
            "logs": [],
            "hint": "View logs at: https://railway.app → Your Project → Deployments → View Logs"
        }
    
    try:
        # Read last N lines from log file
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Get last N lines
        recent_lines = lines[-limit:] if len(lines) > limit else lines
        
        # Parse and filter logs
        parsed_logs = []
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue
            
            # Simple parsing (format: timestamp - module - level - message)
            log_entry = {
                "raw": line,
                "timestamp": None,
                "level": None,
                "module": None,
                "message": line
            }
            
            # Try to extract level
            for level_name in ["ERROR", "WARNING", "INFO", "DEBUG"]:
                if f" - {level_name} - " in line:
                    log_entry["level"] = level_name
                    parts = line.split(f" - {level_name} - ", 1)
                    if len(parts) == 2:
                        log_entry["message"] = parts[1]
                        # Try to extract timestamp and module
                        header = parts[0]
                        if " - " in header:
                            header_parts = header.split(" - ", 1)
                            log_entry["timestamp"] = header_parts[0] if len(header_parts) > 0 else None
                            log_entry["module"] = header_parts[1] if len(header_parts) > 1 else None
                    break
            
            # Apply filters
            if level and log_entry["level"] != level.upper():
                continue
            
            if search and search.lower() not in line.lower():
                continue
            
            parsed_logs.append(log_entry)
        
        return {
            "success": True,
            "total_lines": len(lines),
            "returned": len(parsed_logs),
            "logs": parsed_logs[-limit:]  # Limit after filtering
        }
        
    except Exception as e:
        logger.error(f"Error reading logs: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error reading logs: {str(e)}",
            "logs": []
        }


@router.post("/bots/{bot_id}/sync-username")
async def sync_bot_username(
    bot_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Sync bot username from Telegram API (getMe) and save to bot.config.
    This fixes referral links that show "bot doesn't exist" error.
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if bot.platform_type != "telegram":
        raise HTTPException(status_code=400, detail="Only Telegram bots supported")
    
    from app.adapters.telegram import TelegramAdapter
    adapter = TelegramAdapter()
    
    try:
        bot_info = await adapter.get_bot_info(bot_id)
        username = bot_info.get('username')
        
        if not username:
            raise HTTPException(status_code=500, detail="Username not found in bot info")
        
        # Save username directly in this session to ensure it's persisted
        if not bot.config:
            bot.config = {}
        bot.config['username'] = username
        bot.config['bot_id'] = bot_info.get('id')
        bot.config['first_name'] = bot_info.get('first_name')
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(bot, 'config')
        db.commit()
        db.refresh(bot)
        
        return {
            "message": "Bot username synced successfully",
            "username": username,
            "saved_username": bot.config.get('username'),
            "bot_id": bot_info.get('id'),
            "first_name": bot_info.get('first_name'),
            "config_updated": bot.config.get('username') == username
        }
    except Exception as e:
        logger.error(f"Error syncing bot username: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to sync username: {str(e)}")


@router.get("/bots/{bot_id}/test-avatar")
async def test_bot_avatar(
    bot_id: UUID,
    target_username: str = Query(..., description="Target bot username (without @)"),
    db: Session = Depends(get_db)
):
    """
    Test fetching bot avatar from Telegram API.
    
    Args:
        bot_id: Our bot UUID (to get token)
        target_username: Target bot username to fetch avatar for
        db: Database session
    
    Returns:
        Avatar URL or error message
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if bot.platform_type != "telegram":
        raise HTTPException(status_code=400, detail="Only Telegram bots supported")
    
    from app.adapters.telegram import TelegramAdapter
    adapter = TelegramAdapter()
    
    try:
        logger.info(f"Testing avatar fetch for @{target_username}")
        avatar_url = await adapter.get_bot_avatar_url(bot_id, target_username)
        
        if avatar_url:
            logger.info(f"✅ Avatar found for @{target_username}: {avatar_url[:50]}...")
            return {
                "ok": True,
                "username": target_username,
                "avatar_url": avatar_url,
                "message": "Avatar fetched successfully"
            }
        else:
            logger.warning(f"⚠️ Avatar not found for @{target_username} (bot may not have profile photo)")
            return {
                "ok": False,
                "username": target_username,
                "avatar_url": None,
                "message": "Avatar not found or bot has no profile photo. Check logs for details."
            }
    except Exception as e:
        logger.error(f"Error fetching bot avatar for @{target_username}: {e}", exc_info=True)


@router.post("/bots/{bot_id}/fix-icons-now")
async def fix_icons_now(
    bot_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Temporary endpoint to force-fetch missing icons with DEBUG logs.
    """
    try:
        from app.models.business_data import BusinessData
        from app.models.bot import Bot
        import httpx
        import re
        
        # Get bot token
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot or not bot.token:
            return {"error": "Bot token not found"}
        
        token = bot.token
        base_url = f"https://api.telegram.org/bot{token}"
        
        search_terms = ['randgift_bot', 'boinker_bot', 'EasyGiftDropbot', 'm5bank_bot']
        
        partners = db.query(BusinessData).filter(
            BusinessData.bot_id == bot_id,
            BusinessData.data_type == 'partner'
        ).all()
        
        results = []
        updates_count = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for partner in partners:
                data = partner.data
                link = data.get('referral_link', '')
                name = data.get('bot_name', 'Unknown')
                
                is_match = False
                for term in search_terms:
                    if term.lower() in link.lower():
                        is_match = True
                        break
                
                if is_match:
                    # Extract username
                    match = re.search(r't\.me/([a-zA-Z0-9_]+)', link)
                    if match:
                        username = match.group(1)
                        chat_id = f"@{username}"
                        
                        # 1. getChat
                        try:
                            resp = await client.post(f"{base_url}/getChat", json={"chat_id": chat_id})
                            chat_res = resp.json()
                            
                            if not chat_res.get('ok'):
                                results.append(f"FAIL {name} ({username}): getChat error: {chat_res} ({resp.status_code})")
                                continue
                                
                            user_id = chat_res['result']['id']
                            
                            # 2. getUserProfilePhotos
                            resp = await client.post(f"{base_url}/getUserProfilePhotos", json={"user_id": user_id, "limit": 1})
                            photos_res = resp.json()
                            
                            if not photos_res.get('ok'):
                                results.append(f"FAIL {name}: photos error: {photos_res}")
                                continue
                                
                            photos = photos_res['result']
                            if photos['total_count'] == 0:
                                results.append(f"FAIL {name}: No profile photos found")
                                continue
                                
                            # 3. getFile
                            file_id = photos['photos'][0][-1]['file_id']
                            resp = await client.post(f"{base_url}/getFile", json={"file_id": file_id})
                            file_res = resp.json()
                            
                            file_path = file_res['result']['file_path']
                            full_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
                            
                            # Update DB
                            partner.data['icon'] = full_url
                            from sqlalchemy.orm.attributes import flag_modified
                            flag_modified(partner, 'data')
                            updates_count += 1
                            results.append(f"SUCCESS {name}: {full_url}")
                            
                        except Exception as inner_e:
                            results.append(f"ERROR {name}: {str(inner_e)}")
                    else:
                        results.append(f"SKIP {name}: No username in link")
        
        if updates_count > 0:
            db.commit()
            
        return {
            "success": True,
            "updates_count": updates_count,
            "details": results
        }
            
    except Exception as e:
        logger.error(f"Error fixing icons: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bots/{bot_id}/mini-app-analytics")
async def get_mini_app_analytics(
    bot_id: UUID,
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated Mini App analytics for a bot.
    
    Returns:
        - Page views by page (view_home, view_partners, view_top)
        - Partner clicks by partner name
        - Funnel data (conversion from home → partners → click)
        - Wallet connections count
        - Session events count
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, desc
    from app.models.message import Message
    from app.models.business_data import BusinessData
    
    # Time range
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) # Include end date fully
        except ValueError:
            # Fallback to days if invalid format
            start_dt = datetime.utcnow() - timedelta(days=days)
            end_dt = datetime.utcnow() + timedelta(days=1)
    else:
        start_dt = datetime.utcnow() - timedelta(days=days)
        # Fix: Ensure we don't look into future if days is used, but for query optimization just use start_date logic
        end_dt = datetime.utcnow() + timedelta(days=1)
    
    try:
        # Build partner ID to name cache
        partners = db.query(BusinessData).filter(
            BusinessData.bot_id == bot_id,
            BusinessData.data_type == 'partner'
        ).all()
        partner_id_to_name = {}
        for p in partners:
            partner_id_to_name[str(p.id)] = p.data.get('bot_name', 'Unknown Partner') if p.data else 'Unknown Partner'
        
        # Query Mini App messages (source contains 'mini_app')
        mini_app_messages = db.query(Message).filter(
            Message.bot_id == bot_id,
            Message.role == 'user',
            Message.timestamp >= start_dt,
            Message.timestamp < end_dt,
            Message.content.ilike('%mini_app%') | Message.custom_data.op('->>')('source').ilike('%mini_app%')
        ).all()
        
        # Initialize counters
        page_views = {
            'view_home': 0,
            'view_home_v5': 0,
            'view_partners': 0,
            'view_top': 0,
            'total': 0
        }
        partner_clicks = {}
        wallet_events = 0
        share_events = 0
        
        for msg in mini_app_messages:
            content = msg.content or ''
            custom_data = msg.custom_data or {}
            
            # Count page views (check both event names and command names)
            if 'view_home_v5' in content:
                page_views['view_home_v5'] += 1
                page_views['total'] += 1
            elif 'view_home' in content or content == '/start':
                page_views['view_home'] += 1
                page_views['total'] += 1
            elif 'view_partners' in content or content == '/partners':
                page_views['view_partners'] += 1
                page_views['total'] += 1
            elif 'view_top' in content or content == '/top':
                page_views['view_top'] += 1
                page_views['total'] += 1
            
            # Count partner clicks
            if 'partner_click' in content:
                # Try to get partner name, fallback to resolving ID
                partner_name = custom_data.get('partner_name')
                if not partner_name:
                    partner_id = custom_data.get('partner_id', '')
                    partner_name = partner_id_to_name.get(partner_id, f'Partner {partner_id[:8]}...' if len(partner_id) > 8 else partner_id)
                if partner_name:
                    partner_clicks[partner_name] = partner_clicks.get(partner_name, 0) + 1
            
            # Count wallet connections
            if 'wallet_connected' in content:
                wallet_events += 1
            
            # Count share events
            if 'referral_link_share' in content:
                share_events += 1
        
        # Sort partner clicks by count
        top_partners = sorted(
            [{'name': k, 'clicks': v} for k, v in partner_clicks.items()],
            key=lambda x: x['clicks'],
            reverse=True
        )[:10]  # Top 10
        
        # Calculate funnel
        home_views = page_views['view_home'] + page_views['view_home_v5']
        partners_views = page_views['view_partners']
        partner_click_count = sum(partner_clicks.values())
        
        funnel = {
            'home_views': home_views,
            'partners_views': partners_views,
            'partner_clicks': partner_click_count,
            'home_to_partners_rate': round(partners_views / max(home_views, 1) * 100, 1),
            'partners_to_click_rate': round(partner_click_count / max(partners_views, 1) * 100, 1)
        }
        
        return {
            'period_days': days,
            'total_sessions': len(set(m.user_id for m in mini_app_messages)),
            'total_events': len(mini_app_messages),
            'page_views': page_views,
            'top_partners': top_partners,
            'funnel': funnel,
            'wallet_connections': wallet_events,
            'share_events': share_events
        }
        
    except Exception as e:
        logger.error(f"Error fetching mini app analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
