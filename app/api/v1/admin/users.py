"""
Users endpoints for Admin API.
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
