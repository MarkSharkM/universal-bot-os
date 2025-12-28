"""
Admin API - Multi-tenant bot management
CRUD operations for bots, partners, translations, AI config
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.models.bot import Bot
from app.models.business_data import BusinessData
from app.models.user import User
from app.schemas.bot import BotCreate, BotUpdate, BotResponse
from app.services.ai_service import AIService
from app.services.translation_service import TranslationService

router = APIRouter()


# TODO: Add authentication middleware
# For now, admin endpoints are open (add auth in production)


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
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
):
    """
    Create new bot.
    
    Args:
        bot_data: Bot creation data
        db: Database session
    
    Returns:
        Created bot
    """
    bot = Bot(
        name=bot_data.name,
        platform_type=bot_data.platform_type,
        token=bot_data.token,  # TODO: Encrypt token
        default_lang=bot_data.default_lang,
        config=bot_data.config,
        is_active=True
    )
    
    db.add(bot)
    db.commit()
    db.refresh(bot)
    
    return bot


@router.patch("/bots/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: UUID,
    bot_data: BotUpdate,
    db: Session = Depends(get_db)
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
        bot.config.update(bot_data.config)
    if bot_data.default_lang is not None:
        bot.default_lang = bot_data.default_lang
    if bot_data.is_active is not None:
        bot.is_active = bot_data.is_active
    
    db.commit()
    db.refresh(bot)
    
    return bot


@router.delete("/bots/{bot_id}")
async def delete_bot(
    bot_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete bot (soft delete - set is_active=False).
    
    Args:
        bot_id: Bot UUID
        db: Database session
    
    Returns:
        Success message
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Soft delete
    bot.is_active = False
    db.commit()
    
    return {"message": "Bot deactivated successfully"}


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
    
    # Count users
    users_count = db.query(User).filter(User.bot_id == bot_id).count()
    
    # Count active users
    active_users_count = db.query(User).filter(
        User.bot_id == bot_id,
        User.is_active == True
    ).count()
    
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


@router.get("/bots/{bot_id}/partners", response_model=List[Dict[str, Any]])
async def list_bot_partners(
    bot_id: UUID,
    category: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    List partners for a bot.
    
    Args:
        bot_id: Bot UUID
        category: Filter by category (TOP, NEW)
        active_only: Show only active partners
        db: Database session
    
    Returns:
        List of partners
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    query = db.query(BusinessData).filter(
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'partner'
    )
    
    partners = query.all()
    
    # Filter in Python to avoid JSONB query issues
    result = []
    for p in partners:
        partner_data = p.data or {}
        
        # Apply filters
        if active_only and partner_data.get('active') != 'Yes':
            continue
        if category and partner_data.get('category') != category:
            continue
        
        result.append({
            "id": str(p.id),
            "bot_name": partner_data.get('bot_name', ''),
            "description": partner_data.get('description', ''),
            "description_en": partner_data.get('description_en', ''),
            "description_ru": partner_data.get('description_ru', ''),
            "description_de": partner_data.get('description_de', ''),
            "description_es": partner_data.get('description_es', ''),
            "referral_link": partner_data.get('referral_link', ''),
            "commission": partner_data.get('commission', 0),
            "category": partner_data.get('category', 'NEW'),
            "active": partner_data.get('active', 'No'),
            "verified": partner_data.get('verified', 'No'),
            "roi_score": partner_data.get('roi_score', 0),
            "duration": partner_data.get('duration', ''),
            "gpt": partner_data.get('gpt', ''),
            "short_link": partner_data.get('short_link', ''),
        })
    
    return result


@router.post("/bots/{bot_id}/partners")
async def create_partner(
    bot_id: UUID,
    partner_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Create partner for a bot.
    
    Args:
        bot_id: Bot UUID
        partner_data: Partner data
        db: Database session
    
    Returns:
        Created partner
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    partner = BusinessData(
        bot_id=bot_id,
        data_type='partner',
        data=partner_data
    )
    
    db.add(partner)
    db.commit()
    db.refresh(partner)
    
    return {
        "id": str(partner.id),
        "bot_id": str(bot_id),
        "data": partner.data
    }


@router.patch("/bots/{bot_id}/partners/{partner_id}")
async def update_partner(
    bot_id: UUID,
    partner_id: UUID,
    partner_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Update partner.
    
    Args:
        bot_id: Bot UUID
        partner_id: Partner UUID
        partner_data: Partner update data
        db: Database session
    
    Returns:
        Updated partner
    """
    partner = db.query(BusinessData).filter(
        BusinessData.id == partner_id,
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'partner'
    ).first()
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner.data.update(partner_data)
    db.commit()
    db.refresh(partner)
    
    return {
        "id": str(partner.id),
        "data": partner.data
    }


@router.delete("/bots/{bot_id}/partners/{partner_id}")
async def delete_partner(
    bot_id: UUID,
    partner_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete partner.
    
    Args:
        bot_id: Bot UUID
        partner_id: Partner UUID
        db: Database session
    
    Returns:
        Success message
    """
    partner = db.query(BusinessData).filter(
        BusinessData.id == partner_id,
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'partner'
    ).first()
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    db.delete(partner)
    db.commit()
    
    return {"message": "Partner deleted successfully"}


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

