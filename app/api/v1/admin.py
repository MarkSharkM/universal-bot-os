"""
Admin API - Multi-tenant bot management
CRUD operations for bots, partners, translations, AI config
"""
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.models.bot import Bot
from app.models.business_data import BusinessData
from app.models.user import User
from app.models.translation import Translation
from app.schemas.bot import BotCreate, BotUpdate, BotResponse
from app.services.ai_service import AIService
from app.services.translation_service import TranslationService

logger = logging.getLogger(__name__)
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
    Automatically syncs username from Telegram API for Telegram bots.
    
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
        if not bot.config:
            bot.config = {}
        bot.config.update(bot_data.config)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(bot, 'config')
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
    hard_delete: bool = Query(False, description="If true, permanently delete. Otherwise soft delete."),
    db: Session = Depends(get_db)
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


@router.post("/bots/{bot_id}/users/{user_id}/reset-invites")
async def reset_user_invites(
    bot_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Reset user's invites count to 0 for testing.
    This sets total_invited to 0, locks TOP status, and DELETES all referral logs.
    
    Args:
        bot_id: Bot UUID
        user_id: User UUID
        db: Database session
    
    Returns:
        Success message with updated counts
    """
    from app.models.user import User
    from app.services.referral_service import ReferralService
    from app.models.business_data import BusinessData
    from sqlalchemy import text, cast, String
    
    user = db.query(User).filter(
        User.id == user_id,
        User.bot_id == bot_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_external_id = user.external_id
    old_count = user.custom_data.get('total_invited', 0) if user.custom_data else 0
    
    # Count logs before deletion
    logs_before = db.execute(
        text("""
            SELECT COUNT(*) as count
            FROM business_data
            WHERE bot_id = CAST(:bot_id AS uuid)
              AND data_type = 'log'
              AND deleted_at IS NULL
              AND (data->>'inviter_external_id') = :inviter_external_id
              AND (
                (data->>'is_referral') IN ('true', 'True')
                OR (data->>'is_referral')::boolean = true
              )
        """),
        {
            'bot_id': str(bot_id),
            'inviter_external_id': str(user_external_id)
        }
    ).first()
    logs_count_before = logs_before.count if logs_before else 0
    
    # Delete all referral logs for this inviter (HARD DELETE)
    # Use Python filtering (same approach as check-invites) to handle type mismatches
    all_logs = db.query(BusinessData).filter(
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'log',
        BusinessData.deleted_at.is_(None)  # Only active logs
    ).all()
    
    # Filter logs for this inviter (handle both string and number formats)
    logs_to_delete = []
    for log in all_logs:
        if log.data:
            log_inviter_id = log.data.get('inviter_external_id')
            # Compare as strings to handle type mismatches
            if str(log_inviter_id) == str(user_external_id):
                is_referral = log.data.get('is_referral')
                if is_referral == True or is_referral == 'true' or is_referral == 'True':
                    logs_to_delete.append(log)
    
    deleted_count = len(logs_to_delete)
    # Hard delete (remove from database)
    for log in logs_to_delete:
        db.delete(log)
    
    db.commit()
    
    # Reset total_invited to 0
    if not user.custom_data:
        user.custom_data = {}
    
    user.custom_data['total_invited'] = 0
    user.custom_data['top_status'] = 'locked'
    user.custom_data['top_unlock_method'] = ''
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(user, 'custom_data')
    db.commit()
    db.refresh(user)
    
    # Verify count from database (should be 0 now)
    referral_service = ReferralService(db, bot_id)
    actual_count = referral_service.count_referrals(user_id)
    
    logger.info(f"reset_user_invites: deleted {deleted_count} referral logs for user_id={user_id}, external_id={user_external_id}, old_count={old_count}, new_count={actual_count}")
    
    return {
        "success": True,
        "message": f"User invites reset successfully. Deleted {deleted_count} referral logs.",
        "user_id": str(user_id),
        "external_id": user_external_id,
        "old_total_invited": old_count,
        "new_total_invited": 0,
        "actual_count_from_db": actual_count,
        "deleted_logs_count": deleted_count,
        "logs_count_before": logs_count_before,
        "top_status": "locked",
        "note": "All referral logs were hard deleted. If actual_count_from_db > 0, there may be logs with different inviter_external_id format."
    }


@router.post("/bots/{bot_id}/users/{user_id}/test-5-invites")
async def test_5_invites_unlock(
    bot_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Test endpoint: Simulate 5 referrals and verify TOP auto-unlock.
    
    This endpoint:
    1. Creates 5 referral log entries
    2. Updates total_invited count (which should auto-unlock TOP)
    3. Returns verification results
    
    Args:
        bot_id: Bot UUID
        user_id: User UUID (the inviter)
        db: Database session
    
    Returns:
        Test results with verification
    """
    try:
        from app.services.referral_service import ReferralService
        from app.services.earnings_service import EarningsService
        from app.services.user_service import UserService
        from app.services.translation_service import TranslationService
        
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        user = db.query(User).filter(
            User.id == user_id,
            User.bot_id == bot_id
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Initialize services
        referral_service = ReferralService(db, bot_id)
        user_service = UserService(db, bot_id)
        translation_service = TranslationService(db, bot_id)
        earnings_service = EarningsService(
            db, bot_id, user_service, referral_service, translation_service
        )
        
        # Get initial state
        initial_total_invited = user.custom_data.get('total_invited', 0) if user.custom_data else 0
        initial_top_status = user.custom_data.get('top_status', 'locked') if user.custom_data else 'locked'
        
        # Create 5 referral events with unique ref_parameters
        # Each referral should have a unique ref_parameter to be counted separately
        timestamp = int(time.time())
        for i in range(1, 6):
            # Each referral needs a unique ref_parameter
            # Format: _tgr_{inviter_external_id}_{unique_suffix}
            ref_param = f"_tgr_{user.external_id}_{i}_{timestamp}"
            referred_external_id = f"test_referred_{i}_{user.external_id}_{timestamp}"
            
            log_data = BusinessData(
                bot_id=bot_id,
                data_type='log',
                data={
                    'user_id': str(referred_external_id),
                    'external_id': referred_external_id,
                    'ref_parameter': ref_param,
                    'referral_tag': ref_param,
                    'inviter_external_id': user.external_id,
                    'is_referral': True,
                    'click_type': 'Referral',
                    'event_type': 'start',
                }
            )
            db.add(log_data)
        
        db.commit()
        
        # Count created logs (we created exactly 5)
        created_logs_count = 5
        
        # Update total_invited (this should auto-unlock TOP)
        updated_user = referral_service.update_total_invited(user_id)
        
        # Refresh user to get latest data
        db.refresh(updated_user)
        
        # Get final state
        final_total_invited = updated_user.custom_data.get('total_invited', 0)
        final_top_status = updated_user.custom_data.get('top_status', 'locked')
        final_top_unlock_method = updated_user.custom_data.get('top_unlock_method', '')
        
        # Check earnings message
        earnings_data = earnings_service.build_earnings_message(user_id)
        can_unlock, invites_needed = referral_service.check_top_unlock_eligibility(user_id)
        
        # Verify results
        tests = {
            "total_invited_is_5": final_total_invited == 5,
            "top_status_is_open": final_top_status == 'open',
            "top_unlock_method_is_invites": final_top_unlock_method == 'invites',
            "earnings_shows_5_invites": earnings_data['invites'] == 5,
            "earnings_top_status_is_open": earnings_data['top_status'] == 'open',
            "can_unlock_is_true": can_unlock,
            "invites_needed_is_0": invites_needed == 0,
        }
        
        all_passed = all(tests.values())
        
        return {
            "success": all_passed,
            "message": "All tests passed!" if all_passed else "Some tests failed",
            "initial_state": {
                "total_invited": initial_total_invited,
                "top_status": initial_top_status,
            },
            "final_state": {
                "total_invited": final_total_invited,
                "top_status": final_top_status,
                "top_unlock_method": final_top_unlock_method,
            },
            "earnings_data": {
                "invites": earnings_data['invites'],
                "needed": earnings_data['needed'],
                "top_status": earnings_data['top_status'],
            },
            "eligibility_check": {
                "can_unlock": can_unlock,
                "invites_needed": invites_needed,
            },
            "tests": tests,
            "created_logs": created_logs_count,
        }
    except Exception as e:
        logger.error(f"Error in test_5_invites_unlock: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


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
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),  # Max 500 partners per request
    db: Session = Depends(get_db)
):
    """
    List partners for a bot.
    
    Args:
        bot_id: Bot UUID
        category: Filter by category (TOP, NEW)
        active_only: Show only active partners
        skip: Number of records to skip
        limit: Maximum number of records to return (max 500)
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
    
    # Get all partners first (for filtering), then paginate
    all_partners = query.all()
    
    # Filter in Python to avoid JSONB query issues
    filtered = []
    for p in all_partners:
        partner_data = p.data or {}
        
        # Apply filters
        if active_only and partner_data.get('active') != 'Yes':
            continue
        if category and partner_data.get('category') != category:
            continue
        
        filtered.append(p)
    
    # Apply pagination after filtering
    paginated = filtered[skip:skip + limit]
    
    result = []
    for p in paginated:
        partner_data = p.data or {}
        
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
    
    # Update partner data - merge with existing data
    current_data = partner.data.copy() if partner.data else {}
    current_data.update(partner_data)
    partner.data = current_data
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
    hard_delete: bool = Query(False, description="If true, permanently delete. Otherwise soft delete."),
    db: Session = Depends(get_db)
):
    """
    Delete partner (soft delete by default, keeps history).
    
    Args:
        bot_id: Bot UUID
        partner_id: Partner UUID
        hard_delete: If true, permanently delete. Otherwise soft delete.
        db: Database session
    
    Returns:
        Success message
    """
    from datetime import datetime
    
    partner = db.query(BusinessData).filter(
        BusinessData.id == partner_id,
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'partner'
    ).first()
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if hard_delete:
        # Permanent deletion
        db.delete(partner)
        message = "Partner permanently deleted"
    else:
        # Soft delete
        partner.deleted_at = datetime.now()
        message = "Partner deleted (can be restored)"
    
    db.commit()
    
    return {"message": message, "hard_delete": hard_delete}


@router.post("/bots/{bot_id}/partners/{partner_id}/restore")
async def restore_partner(
    bot_id: UUID,
    partner_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Restore soft-deleted partner.
    
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
    
    if partner.deleted_at is None:
        raise HTTPException(status_code=400, detail="Partner is not deleted")
    
    partner.deleted_at = None
    db.commit()
    
    return {"message": "Partner restored successfully"}


@router.get("/bots/{bot_id}/partners/deleted")
async def list_deleted_partners(
    bot_id: UUID,
    db: Session = Depends(get_db)
):
    """
    List soft-deleted partners (deletion history).
    
    Args:
        bot_id: Bot UUID
        db: Database session
    
    Returns:
        List of deleted partners
    """
    from sqlalchemy import and_
    
    partners = db.query(BusinessData).filter(
        and_(
            BusinessData.bot_id == bot_id,
            BusinessData.data_type == 'partner',
            BusinessData.deleted_at.isnot(None)
        )
    ).all()
    
    return [
        {
            "id": str(p.id),
            "bot_name": p.data.get('bot_name', 'Unknown'),
            "description": p.data.get('description', ''),
            "referral_link": p.data.get('referral_link', ''),
            "commission": float(p.data.get('commission', 0)),
            "category": p.data.get('category', 'NEW'),
            "active": p.data.get('active', 'No'),
            "verified": p.data.get('verified', 'No'),
            "roi_score": float(p.data.get('roi_score', 0)),
            "deleted_at": p.deleted_at.isoformat() if p.deleted_at else None
        }
        for p in partners
    ]


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


@router.post("/bots/{bot_id}/test-command")
async def test_command(
    bot_id: UUID,
    command: str = Query(..., description="Command to test (e.g., /start, /wallet, /partners)"),
    user_external_id: Optional[str] = Query(None, description="Test user external ID (default: test_user)"),
    user_lang: Optional[str] = Query("uk", description="User language code"),
    db: Session = Depends(get_db)
):
    """
    Test bot command without Telegram.
    Useful for debugging and comparing with production.
    
    Args:
        bot_id: Bot UUID
        command: Command to test (e.g., "/start", "/wallet", "/partners")
        user_external_id: Test user ID (default: "test_user")
        user_lang: User language (default: "uk")
        db: Database session
    
    Returns:
        Command response (message, buttons, etc.) with detailed debug info
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"test_command: bot_id={bot_id}, command={command}, user_external_id={user_external_id}, user_lang={user_lang}")
    
    from app.services import (
        UserService, TranslationService, CommandService,
        PartnerService, ReferralService, EarningsService
    )
    
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        logger.error(f"test_command: Bot {bot_id} not found")
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Initialize services
    user_service = UserService(db, bot_id)
    translation_service = TranslationService(db, bot_id)
    referral_service = ReferralService(db, bot_id)
    partner_service = PartnerService(db, bot_id)
    earnings_service = EarningsService(
        db, bot_id, user_service, referral_service, translation_service
    )
    command_service = CommandService(
        db, bot_id, user_service, translation_service,
        partner_service, referral_service, earnings_service
    )
    
    # Get or create test user
    test_user_id = user_external_id or "test_user"
    user = user_service.get_or_create_user(
        external_id=test_user_id,
        platform="telegram",
        language_code=user_lang,
        username="test_user",
        first_name="Test",
        last_name="User"
    )
    
    # Parse command
    logger.info(f"test_command: parsing command '{command}'")
    parsed_command = command_service.parse_command(command)
    start_param = command_service.extract_start_parameter(command)
    logger.info(f"test_command: parsed_command={parsed_command}, start_param={start_param}")
    
    if not parsed_command:
        logger.warning(f"test_command: Unknown command '{command}'")
        return {
            "error": "Unknown command",
            "input": command,
            "parsed": None
        }
    
    # Handle command
    try:
        from app.models.message import Message
        
        # Save user message
        user_message = Message(
            user_id=user.id,
            bot_id=bot_id,
            role='user',
            content=command,
            custom_data={'is_test': True}
        )
        db.add(user_message)
        
        logger.info(f"test_command: handling command {parsed_command} for user {user.id}")
        response = await command_service.handle_command(
            parsed_command,
            user.id,
            user_lang=user_lang,
            start_param=start_param
        )
        logger.info(f"test_command: command {parsed_command} completed, has_message={bool(response.get('message'))}, has_error={bool(response.get('error'))}")
        
        # Format message: convert escaped newlines to actual newlines
        message = response.get('message', '')
        if isinstance(message, str):
            message = message.replace('\\n', '\n')
            
        # Save bot response
        if message:
            bot_message = Message(
                user_id=user.id,
                bot_id=bot_id,
                role='assistant',
                content=message,
                custom_data={'is_test': True}
            )
            db.add(bot_message)
            
        db.commit()
        
        return {
            "success": True,
            "command": parsed_command,
            "input": command,
            "start_param": start_param,
            "user_id": str(user.id),
            "user_lang": user_lang,
            "response": {
                "message": message,
                "buttons": response.get('buttons', []),
                "parse_mode": response.get('parse_mode', 'HTML'),
                "other": {k: v for k, v in response.items() if k not in ['message', 'buttons', 'parse_mode']}
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"test_command: Exception handling command {parsed_command}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "command": parsed_command,
            "input": command,
            "user_id": str(user.id) if user else None
        }


@router.post("/bots/{bot_id}/users/{user_id}/set-invited")
async def set_user_invited_count(
    bot_id: UUID,
    user_id: UUID,
    total_invited: int = Query(..., description="Total invited count to set"),
    db: Session = Depends(get_db)
):
    """
    Set user's total invited count (for testing).
    
    Args:
        bot_id: Bot UUID
        user_id: User UUID
        total_invited: Total invited count to set
        db: Database session
    
    Returns:
        Updated user info
    """
    from app.models.user import User
    
    user = db.query(User).filter(
        User.id == user_id,
        User.bot_id == bot_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.custom_data:
        user.custom_data = {}
    
    user.custom_data['total_invited'] = total_invited
    # Mark JSONB field as modified for SQLAlchemy
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(user, 'custom_data')
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "user_id": str(user.id),
        "external_id": user.external_id,
        "total_invited": total_invited,
        "custom_data": user.custom_data
    }


@router.put("/translations/{key}/{lang}")
async def update_translation(
    key: str,
    lang: str,
    text: str = Query(..., description="New translation text"),
    db: Session = Depends(get_db)
):
    """
    Quick update translation directly in database.
    No deployment needed - instant fix!
    
    Args:
        key: Translation key (e.g., 'welcome')
        lang: Language code (e.g., 'uk', 'en')
        text: New translation text
        db: Database session
    
    Returns:
        Updated translation
    """
    # Find or create translation
    translation = db.query(Translation).filter(
        Translation.key == key,
        Translation.lang == lang
    ).first()
    
    if translation:
        translation.text = text
    else:
        translation = Translation(key=key, lang=lang, text=text)
        db.add(translation)
    
    db.commit()
    db.refresh(translation)
    
    return {
        "success": True,
        "key": key,
        "lang": lang,
        "text": translation.text,
        "message": "Translation updated successfully"
    }


@router.get("/translations/{key}/{lang}/visual")
async def get_translation_visual(
    key: str,
    lang: str,
    db: Session = Depends(get_db)
):
    """
    Get translation with visual formatting (spaces, line breaks visible).
    Useful for comparing with production screenshots - shows all whitespace.
    
    Args:
        key: Translation key
        lang: Language code
        db: Database session
    
    Returns:
        Translation with visual formatting markers (spaces as ·, line breaks as |)
    """
    translation = db.query(Translation).filter(
        Translation.key == key,
        Translation.lang == lang
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    text = translation.text
    lines = text.split('\\n')
    
    # Visual representation
    visual_lines = []
    for i, line in enumerate(lines, 1):
        # Show spaces as · and empty lines clearly
        visual = line.replace(' ', '·')
        if not line.strip():
            visual = "[EMPTY LINE]"
        visual_lines.append({
            "line_number": i,
            "original": line,
            "visual": visual,
            "is_empty": not line.strip(),
            "length": len(line),
            "spaces": line.count(' '),
            "leading_spaces": len(line) - len(line.lstrip()),
            "trailing_spaces": len(line) - len(line.rstrip())
        })
    
    return {
        "key": key,
        "lang": lang,
        "text": text,
        "total_lines": len(lines),
        "empty_lines": sum(1 for l in lines if not l.strip()),
        "lines": visual_lines,
        "raw": text,
        "visual_preview": "\\n".join([f"{i:2}. {l['visual']}" for i, l in enumerate(visual_lines, 1)])
    }


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


@router.patch("/bots/{bot_id}/users/{user_id}")
async def update_user(
    bot_id: UUID,
    user_id: UUID,
    top_status: Optional[str] = Query(None, description="Set TOP status: 'locked' or 'open'"),
    top_unlock_method: Optional[str] = Query(None, description="Set TOP unlock method: 'payment' or 'invites'"),
    total_invited: Optional[int] = Query(None, description="Set total invited count"),
    wallet_address: Optional[str] = Query(None, description="Set wallet address"),
    balance: Optional[float] = Query(None, description="Set user balance"),
    custom_data: Optional[Dict[str, Any]] = Body(None, description="Update custom_data (merged)"),
    db: Session = Depends(get_db)
):
    """
    Update user parameters (top_status, total_invited, wallet, etc.).
    
    Args:
        bot_id: Bot UUID
        user_id: User UUID
        top_status: 'locked' or 'open'
        top_unlock_method: 'payment' or 'invites'
        total_invited: int (number of invited friends)
        wallet_address: str (TON wallet address)
        balance: float (user balance)
        custom_data: dict (any custom data)
        db: Database session
    
    Returns:
        Updated user info
    """
    from sqlalchemy.orm.attributes import flag_modified
    
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    user = db.query(User).filter(
        User.id == user_id,
        User.bot_id == bot_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Initialize custom_data if not exists
    if not user.custom_data:
        user.custom_data = {}
    
    # Update parameters
    updated_fields = []
    
    if top_status is not None:
        user.custom_data['top_status'] = top_status
        updated_fields.append('top_status')
    
    if top_unlock_method is not None:
        user.custom_data['top_unlock_method'] = top_unlock_method
        updated_fields.append('top_unlock_method')
    
    if total_invited is not None:
        user.custom_data['total_invited'] = total_invited
        updated_fields.append('total_invited')
    
    if wallet_address is not None:
        # Allow deletion by passing empty string
        if wallet_address.strip() == '':
            # Delete wallet from custom_data
            if 'wallet_address' in user.custom_data:
                del user.custom_data['wallet_address']
                updated_fields.append('wallet_address (deleted)')
            
            # Also delete from business_data if exists
            from app.models.business_data import BusinessData
            from sqlalchemy.sql import func
            business_wallets = db.query(BusinessData).filter(
                BusinessData.bot_id == bot_id,
                BusinessData.data_type == 'wallet',
                BusinessData.data['user_id'].astext == str(user.id),
                BusinessData.deleted_at.is_(None)
            ).all()
            for bw in business_wallets:
                bw.deleted_at = func.now()
            if business_wallets:
                updated_fields.append('wallet (deleted from business_data)')
        else:
            # Set wallet address
            user.custom_data['wallet_address'] = wallet_address.strip()
            updated_fields.append('wallet_address')
    
    if balance is not None:
        user.balance = balance
        updated_fields.append('balance')
    
    if custom_data is not None:
        # Merge custom_data
        user.custom_data.update(custom_data)
        updated_fields.append('custom_data (merged)')
    
    if not updated_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Mark JSONB field as modified
    flag_modified(user, 'custom_data')
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": f"Updated fields: {', '.join(updated_fields)}",
        "user": {
            "id": str(user.id),
            "external_id": user.external_id,
            "top_status": user.custom_data.get('top_status', 'locked'),
            "top_unlock_method": user.custom_data.get('top_unlock_method', ''),
            "total_invited": user.custom_data.get('total_invited', 0),
            "wallet_address": user.custom_data.get('wallet_address', ''),
            "balance": float(user.balance),
        }
    }


@router.delete("/bots/{bot_id}/users/{user_id}")
async def delete_user(
    bot_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete user and all related data from database.
    
    This will delete:
    - User record
    - All business_data records (referral logs, wallet data, etc.)
    - All analytics_events records
    - All messages records
    
    Args:
        bot_id: Bot UUID
        user_id: User UUID
        db: Database session
    
    Returns:
        Deletion summary
    """
    from app.models.business_data import BusinessData
    from app.models.analytics_event import AnalyticsEvent
    from app.models.message import Message
    
    # Verify bot exists
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Verify user exists
    user = db.query(User).filter(
        User.id == user_id,
        User.bot_id == bot_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_external_id = user.external_id
    
    from sqlalchemy import or_, and_
    from sqlalchemy.sql import func
    from sqlalchemy import cast, String
    
    # Count related records before deletion
    # Use cast() for JSONB queries (same approach as in user_service.py)
    # Also check for NULL values to avoid errors
    from sqlalchemy import text
    
    business_data_count = db.query(BusinessData).filter(
        and_(
            BusinessData.bot_id == bot_id,
            BusinessData.deleted_at.is_(None),
            # Match by user_id in data JSON or by external_id
            # Use text() with proper NULL handling for JSONB
            or_(
                and_(
                    BusinessData.data['user_id'].isnot(None),
                    cast(BusinessData.data['user_id'], String) == str(user_id)
                ),
                and_(
                    BusinessData.data['external_id'].isnot(None),
                    cast(BusinessData.data['external_id'], String) == str(user_external_id)
                ),
                and_(
                    BusinessData.data['inviter_external_id'].isnot(None),
                    cast(BusinessData.data['inviter_external_id'], String) == str(user_external_id)
                )
            )
        )
    ).count()
    
    analytics_events_count = db.query(AnalyticsEvent).filter(
        and_(
            AnalyticsEvent.bot_id == bot_id,
            or_(
                AnalyticsEvent.user_id == user_id,
                AnalyticsEvent.user_external_id == str(user_external_id)
            )
        )
    ).count()
    
    messages_count = db.query(Message).filter(
        Message.bot_id == bot_id,
        Message.user_id == user_id
    ).count()
    
    # Delete all related data
    # 1. Delete business_data records (HARD DELETE to prevent counting old logs for new users with same external_id)
    # Use same filter logic as count query
    # IMPORTANT: Hard delete (not soft delete) to ensure logs are completely removed
    # This prevents issues when a new user is created with the same external_id
    business_data_deleted = db.query(BusinessData).filter(
        and_(
            BusinessData.bot_id == bot_id,
            or_(
                and_(
                    BusinessData.data['user_id'].isnot(None),
                    cast(BusinessData.data['user_id'], String) == str(user_id)
                ),
                and_(
                    BusinessData.data['external_id'].isnot(None),
                    cast(BusinessData.data['external_id'], String) == str(user_external_id)
                ),
                and_(
                    BusinessData.data['inviter_external_id'].isnot(None),
                    cast(BusinessData.data['inviter_external_id'], String) == str(user_external_id)
                )
            )
        )
    ).delete(synchronize_session=False)
    
    # 2. Delete analytics_events records (hard delete)
    db.query(AnalyticsEvent).filter(
        and_(
            AnalyticsEvent.bot_id == bot_id,
            or_(
                AnalyticsEvent.user_id == user_id,
                AnalyticsEvent.user_external_id == str(user_external_id)
            )
        )
    ).delete()
    
    # 3. Delete messages records (hard delete)
    db.query(Message).filter(
        Message.bot_id == bot_id,
        Message.user_id == user_id
    ).delete()
    
    # 4. Delete user record (hard delete)
    db.delete(user)
    
    # Commit all deletions
    db.commit()
    
    logger.info(f"Deleted user {user_id} (external_id: {user_external_id}) from bot {bot_id}")
    logger.info(f"Deleted {business_data_deleted} business_data records (hard delete), {analytics_events_count} analytics_events, {messages_count} messages")
    
    return {
        "success": True,
        "message": f"User {user_id} and all related data deleted successfully",
        "deleted": {
            "user_id": str(user_id),
            "external_id": user_external_id,
            "business_data_records": business_data_deleted,  # Actual deleted count (hard delete)
            "analytics_events": analytics_events_count,
            "messages": messages_count,
            "total_records": business_data_deleted + analytics_events_count + messages_count + 1  # +1 for user
        },
        "note": "Business data logs were HARD DELETED (not soft deleted) to prevent counting old logs for new users with the same external_id"
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


@router.get("/bots/{bot_id}/users/{user_id}/check-invites")
async def check_user_invites(
    bot_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Check and debug invites for a specific user.
    Shows detailed information about referral counting.
    
    Args:
        bot_id: Bot UUID
        user_id: User UUID
        db: Database session
    
    Returns:
        Detailed invite information
    """
    from app.models.business_data import BusinessData
    from app.services.referral_service import ReferralService
    from sqlalchemy import text
    
    # Verify bot exists
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Verify user exists
    user = db.query(User).filter(
        User.id == user_id,
        User.bot_id == bot_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_external_id = user.external_id
    current_total_invited = user.custom_data.get('total_invited', 0) if user.custom_data else 0
    
    # Get referral service count
    referral_service = ReferralService(db, bot_id)
    sql_count = referral_service.count_referrals(user_id)
    
    # Get all business_data logs for this inviter
    all_logs = db.query(BusinessData).filter(
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'log'
    ).all()
    
    # Filter logs for this inviter
    inviter_logs = []
    for log in all_logs:
        if log.data and log.data.get('inviter_external_id') == str(user_external_id):
            inviter_logs.append(log)
    
    # Count by deleted_at status
    active_logs = [log for log in inviter_logs if log.deleted_at is None]
    deleted_logs = [log for log in inviter_logs if log.deleted_at is not None]
    
    # Check referral logs (is_referral = true)
    referral_logs = []
    for log in active_logs:
        data = log.data or {}
        is_referral = data.get('is_referral')
        if is_referral == True or is_referral == 'true' or is_referral == 'True':
            referral_logs.append(log)
    
    # Count unique external_ids
    unique_external_ids = set()
    referral_details = []
    for log in referral_logs:
        data = log.data or {}
        external_id = data.get('external_id', '')
        if external_id:
            unique_external_ids.add(external_id)
            referral_details.append({
                "external_id": external_id,
                "user_id": data.get('user_id'),
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "is_referral": data.get('is_referral'),
                "click_type": data.get('click_type', 'Unknown')
            })
    
    # Execute raw SQL query (same as in count_referrals)
    sql_query = text("""
        SELECT COUNT(DISTINCT data->>'external_id') as count
        FROM business_data
        WHERE bot_id = CAST(:bot_id AS uuid)
          AND data_type = 'log'
          AND deleted_at IS NULL
          AND (data->>'inviter_external_id') = :inviter_external_id
          AND (
            (data->>'is_referral') IN ('true', 'True')
            OR (data->>'is_referral')::boolean = true
          )
          AND (data->>'external_id') IS NOT NULL
          AND (data->>'external_id') != ''
    """)
    
    result = db.execute(
        sql_query,
        {
            'bot_id': str(bot_id),
            'inviter_external_id': str(user_external_id)
        }
    ).first()
    
    sql_count_raw = result.count if result and hasattr(result, 'count') else 0
    
    # Check if counts match
    counts_match = sql_count == len(unique_external_ids) == sql_count_raw
    needs_update = current_total_invited != sql_count
    
    return {
        "user": {
            "id": str(user.id),
            "external_id": user.external_id,
            "username": user.custom_data.get('username', 'N/A') if user.custom_data else 'N/A',
            "current_total_invited": current_total_invited
        },
        "counts": {
            "user_custom_data_total_invited": current_total_invited,
            "referral_service_count": sql_count,
            "raw_sql_count": int(sql_count_raw),
            "python_unique_count": len(unique_external_ids),
            "counts_match": counts_match,
            "needs_update": needs_update
        },
        "logs": {
            "total_logs_for_inviter": len(inviter_logs),
            "active_logs": len(active_logs),
            "deleted_logs": len(deleted_logs),
            "referral_logs": len(referral_logs),
            "unique_external_ids": len(unique_external_ids)
        },
        "referral_details": sorted(referral_details, key=lambda x: x.get('created_at', ''), reverse=True),
        "recommendation": "Update total_invited" if needs_update else "All counts match"
    }


@router.get("/bots/{bot_id}/users")
async def list_bot_users(
    bot_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    sort_by: str = Query("last_activity", description="Sort by: 'created_at' or 'last_activity'"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db)
):
    """
    List users for a specific bot.
    
    Args:
        bot_id: Bot UUID
        skip: Number of records to skip
        limit: Maximum number of records to return
        sort_by: Sort by 'created_at' or 'last_activity' (updated_at)
        user_id: Optional user ID to filter by
        db: Database session
    
    Returns:
        List of users
    """
    # Determine sort column
    if sort_by == "last_activity":
        order_by = User.updated_at.desc()
    else:
        order_by = User.created_at.desc()
    
    query = db.query(User).filter(User.bot_id == bot_id)
    
    if user_id:
        query = query.filter(User.id == user_id)
    
    users = query.order_by(order_by).offset(skip).limit(limit).all()
    
    # Get last message for each user (for combined users+messages view)
    from app.models.message import Message
    user_ids = [u.id for u in users]
    last_messages = {}
    if user_ids:
        # Get last message per user
        for user_id in user_ids:
            last_msg = db.query(Message).filter(
                Message.user_id == user_id,
                Message.bot_id == bot_id
            ).order_by(Message.timestamp.desc()).first()
            if last_msg:
                last_messages[user_id] = {
                    "content": last_msg.content[:100] + ('...' if len(last_msg.content) > 100 else ''),  # Preview
                    "full_content": last_msg.content,  # Full content for expand
                    "role": last_msg.role,
                    "timestamp": last_msg.timestamp.isoformat() if last_msg.timestamp else None
                }
    
    return [
        {
            "id": str(u.id),
            "external_id": u.external_id,
            "platform": u.platform,
            "language_code": u.language_code,
            "balance": float(u.balance),
            "is_active": u.is_active,
            "custom_data": u.custom_data,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "updated_at": u.updated_at.isoformat() if u.updated_at else None,
            "last_activity": u.updated_at.isoformat() if u.updated_at else u.created_at.isoformat() if u.created_at else None,
            # Extract common custom_data fields for easier access
            "username": u.custom_data.get('username', '') if u.custom_data else '',
            "first_name": u.custom_data.get('first_name', '') if u.custom_data else '',
            "last_name": u.custom_data.get('last_name', '') if u.custom_data else '',
            "wallet_address": u.custom_data.get('wallet_address', '') if u.custom_data else '',
            "total_invited": u.custom_data.get('total_invited', 0) if u.custom_data else 0,
            "top_status": u.custom_data.get('top_status', 'locked') if u.custom_data else 'locked',
            "top_unlock_method": u.custom_data.get('top_unlock_method', '') if u.custom_data else '',
            "device": u.custom_data.get('device', '') if u.custom_data else '',
            "device_version": u.custom_data.get('device_version', '') if u.custom_data else '',
            # Normalize language_code - if it's iOS/Android, it's device, not language
            "device_os": u.language_code if u.language_code in ['iOS', 'Android'] else '',
            "language": u.language_code if u.language_code not in ['iOS', 'Android'] else (u.custom_data.get('language', 'uk') if u.custom_data else 'uk'),
            # Last message info
            "last_message": last_messages.get(u.id),
        }
        for u in users
    ]


@router.get("/bots/{bot_id}/messages")
async def list_bot_messages(
    bot_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    command: Optional[str] = Query(None, description="Filter by command (e.g., /start, /top)"),
    sort_by: str = Query("timestamp", description="Sort by: 'timestamp' or 'response_time'"),
    db: Session = Depends(get_db)
):
    """
    List messages grouped by command-response pairs with Response Time calculation.
    Each row represents: user command + bot response + response time.
    
    Args:
        bot_id: Bot UUID
        skip: Number of records to skip
        limit: Maximum number of records to return
        user_id: Optional filter by user ID
        command: Optional filter by command (e.g., /start, /top)
        sort_by: Sort by 'timestamp' (default) or 'response_time'
        db: Database session
    
    Returns:
        List of message pairs with response time metrics
    """
    from app.models.message import Message
    from app.models.user import User
    from sqlalchemy import and_, or_, func, desc, asc
    from datetime import datetime, timedelta
    
    # Base query for user messages (commands)
    query = db.query(Message).join(User).filter(
        Message.bot_id == bot_id,
        Message.role == 'user'
    )
    
    if user_id:
        query = query.filter(Message.user_id == user_id)
    
    if command:
        # Filter by command (e.g., /start, /top)
        query = query.filter(Message.content.like(f'{command}%'))
    
    # Get user messages ordered by timestamp with user data (already joined)
    user_messages = query.order_by(Message.timestamp.desc()).offset(skip).limit(limit).all()
    
    # OPTIMIZATION: Batch load all response messages for these user messages in one query
    if not user_messages:
        return []
    
    user_msg_ids = [msg.id for msg in user_messages]
    user_ids = list(set([msg.user_id for msg in user_messages]))
    
    # Get all assistant messages for these users after their user messages
    # Use window function approach: get next assistant message for each user message
    from sqlalchemy import text
    
    # Build a more efficient query using window functions or subquery
    # For now, use batch loading with optimized query
    response_messages_query = db.query(Message).filter(
        Message.bot_id == bot_id,
        Message.user_id.in_(user_ids),
        Message.role == 'assistant'
    ).order_by(Message.user_id, Message.timestamp.asc()).all()
    
    # Create a map: user_id -> list of assistant messages (sorted by timestamp)
    response_map = {}
    for resp_msg in response_messages_query:
        if resp_msg.user_id not in response_map:
            response_map[resp_msg.user_id] = []
        response_map[resp_msg.user_id].append(resp_msg)
    
    result = []
    for user_msg in user_messages:
        # Find the next assistant message (bot response) after this user message
        response_msg = None
        user_responses = response_map.get(user_msg.user_id, [])
        for resp in user_responses:
            if resp.timestamp > user_msg.timestamp:
                response_msg = resp
                break
        
        # Calculate response time
        response_time_ms = None
        response_time_seconds = None
        if response_msg and user_msg.timestamp and response_msg.timestamp:
            delta = response_msg.timestamp - user_msg.timestamp
            response_time_ms = int(delta.total_seconds() * 1000)
            response_time_seconds = round(delta.total_seconds(), 2)
        
        # Get user data (already loaded via JOIN, but access via relationship)
        user = user_msg.user
        if not user:
            logger.warning(f"User not found for message {user_msg.id}, user_id={user_msg.user_id}")
            continue
        
        # Extract command from content (remove /start params if present)
        command_text = user_msg.content.split()[0] if user_msg.content else user_msg.content
        
        # Get user fields
        custom_data = user.custom_data or {}
        username = custom_data.get('username', '')
        first_name = custom_data.get('first_name', '')
        last_name = custom_data.get('last_name', '')
        device_os = user.language_code if user.language_code in ['iOS', 'Android'] else ''
        device_version = custom_data.get('device_version', '')
        device = f"{device_os} {device_version}".strip() if device_os else custom_data.get('device', '')
        language = user.language_code if user.language_code not in ['iOS', 'Android'] else (custom_data.get('language', 'uk'))
        wallet_address = custom_data.get('wallet_address', '')
        total_invited = custom_data.get('total_invited', 0)
        top_status = custom_data.get('top_status', 'locked')
        balance = float(user.balance) if user.balance else 0.0
        
        result.append({
            "id": str(user_msg.id),
            "user_id": str(user.id),
            "external_id": user.external_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "device": device,
            "device_os": device_os,
            "device_version": device_version,
            "language": language,
            "wallet_address": wallet_address,
            "total_invited": total_invited,
            "top_status": top_status,
            "balance": balance,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_activity": user.updated_at.isoformat() if user.updated_at else (user.created_at.isoformat() if user.created_at else None),
            # Command data
            "command": command_text,
            "command_content": user_msg.content,
            "command_timestamp": user_msg.timestamp.isoformat() if user_msg.timestamp else None,
            # Response data
            "response_content": response_msg.content if response_msg else None,
            "response_timestamp": response_msg.timestamp.isoformat() if response_msg and response_msg.timestamp else None,
            "response_time_ms": response_time_ms,
            "response_time_seconds": response_time_seconds,
        })
    
    # Sort by response_time if requested
    if sort_by == "response_time":
        result.sort(key=lambda x: x["response_time_seconds"] if x["response_time_seconds"] is not None else float('inf'), reverse=True)
    
    return result


@router.get("/bots/{bot_id}/users/{user_id}/messages")
async def list_user_messages(
    bot_id: UUID,
    user_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List messages for a specific user.
    Useful for viewing what users type and bot responses.
    
    Args:
        bot_id: Bot UUID
        user_id: User UUID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
    
    Returns:
        List of messages (user and bot)
    """
    from app.models.message import Message
    
    messages = db.query(Message).filter(
        Message.bot_id == bot_id,
        Message.user_id == user_id
    ).order_by(Message.timestamp.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(m.id),
            "role": m.role,  # user, assistant, system
            "content": m.content,
            "custom_data": m.custom_data,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None
        }
        for m in messages
    ]


@router.get("/translations")
async def list_translations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    key: Optional[str] = None,
    lang: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List translations with optional filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        key: Filter by translation key
        lang: Filter by language
        db: Database session
    
    Returns:
        List of translations
    """
    query = db.query(Translation)
    
    if key:
        query = query.filter(Translation.key == key)
    if lang:
        query = query.filter(Translation.lang == lang)
    
    translations = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(t.id),
            "key": t.key,
            "lang": t.lang,
            "text": t.text,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in translations
    ]


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

@router.get("/bots/{bot_id}/users/{user_id}/debug-referrals")
async def debug_referrals(
    bot_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to inspect referral state for a specific user.
    Returns counts from different sources to identify discrepancies.
    """
    from app.models.user import User
    from app.models.business_data import BusinessData
    from app.services.referral_service import ReferralService
    from sqlalchemy import text, cast, String
    
    user = db.query(User).filter(User.id == user_id, User.bot_id == bot_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    referral_service = ReferralService(db, bot_id)
    
    # 1. Stored Count
    stored_count = user.custom_data.get('total_invited', 0) if user.custom_data else 0
    
    # 2. Calculated Count (via Service)
    calculated_count = referral_service.count_referrals(user_id)
    
    # 3. Raw SQL Counts (Active vs Deleted)
    user_external_id = str(user.external_id)
    
    query_active = text("""
        SELECT COUNT(*) as count
        FROM business_data
        WHERE bot_id = CAST(:bot_id AS uuid)
          AND data_type = 'log'
          AND deleted_at IS NULL
          AND (data->>'inviter_external_id') = :inviter_external_id
          AND (
            (data->>'is_referral') IN ('true', 'True')
            OR (data->>'is_referral')::boolean = true
          )
    """)
    result_active = db.execute(query_active, {'bot_id': str(bot_id), 'inviter_external_id': user_external_id}).first()
    active_logs_count = result_active.count if result_active else 0
    
    query_deleted = text("""
        SELECT COUNT(*) as count
        FROM business_data
        WHERE bot_id = CAST(:bot_id AS uuid)
          AND data_type = 'log'
          AND deleted_at IS NOT NULL
          AND (data->>'inviter_external_id') = :inviter_external_id
          AND (
            (data->>'is_referral') IN ('true', 'True')
            OR (data->>'is_referral')::boolean = true
          )
    """)
    result_deleted = db.execute(query_deleted, {'bot_id': str(bot_id), 'inviter_external_id': user_external_id}).first()
    deleted_logs_count = result_deleted.count if result_deleted else 0
    
    # 4. Sample Logs
    sample_logs = []
    logs = db.query(BusinessData).filter(
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'log',
        cast(BusinessData.data['inviter_external_id'], String) == user_external_id
    ).order_by(BusinessData.created_at.desc()).limit(10).all()
    
    for log in logs:
        sample_logs.append({
            "id": str(log.id),
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "deleted_at": log.deleted_at.isoformat() if log.deleted_at else None,
            "data": log.data
        })
        
    return {
        "user_id": str(user_id),
        "external_id": user_external_id,
        "counts": {
            "stored_total_invited": stored_count,
            "calculated_service_count": calculated_count,
            "raw_active_logs_count": active_logs_count,
            "raw_deleted_logs_count": deleted_logs_count
        },
        "sample_logs": sample_logs
    }


@router.post("/bots/{bot_id}/maintenance/cleanup-tests")
async def cleanup_test_messages(bot_id: UUID, db: Session = Depends(get_db)):
    """Temporary endpoint to clean up test messages from user 380927579"""
    from app.models.message import Message
    from app.models.user import User
    from sqlalchemy import cast, String
    from datetime import datetime, timedelta
    
    user = db.query(User).filter(User.external_id == "380927579").first()
    if not user:
        return {"status": "user_not_found"}
        
    # Delete test messages from the last hour
    hour_ago = datetime.now() - timedelta(hours=1)
    
    # Use a simpler filter for JSON column
    deleted = db.query(Message).filter(
        Message.user_id == user.id,
        Message.timestamp >= hour_ago
    ).delete(synchronize_session=False)
    
    db.commit()
    return {"status": "success", "deleted_count": deleted}


