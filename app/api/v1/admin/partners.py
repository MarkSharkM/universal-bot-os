"""
Partners endpoints for Admin API.
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
    Includes auto-expiry check logic.
    
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
    from datetime import datetime, timedelta
    
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    query = db.query(BusinessData).filter(
        BusinessData.bot_id == bot_id,
        BusinessData.data_type == 'partner'
    )
    
    # Get all partners first (for filtering and expiry check)
    all_partners = query.all()
    
    # Check for expired partners and update them
    expiry_updates_made = False
    
    for p in all_partners:
        partner_data = p.data or {}
        
        # Skip if already inactive
        if partner_data.get('active') != 'Yes':
            continue
            
        # Get start date (priority: explicit start_date -> created_at -> now)
        start_date_str = partner_data.get('start_date')
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str)
            except ValueError:
                start_date = p.created_at or datetime.now()
        else:
            # Fallback to DB creation time
            start_date = p.created_at or datetime.now()
            
        # Get duration
        try:
            duration_days = int(str(partner_data.get('duration', '9999')).replace(' ', ''))
        except (ValueError, TypeError):
            duration_days = 9999
            
        # Calculate expiry
        # Use timezone-naive comparisons for simplicity or ensure both are aware
        # p.created_at is usually timezone aware in this project
        now = datetime.now(start_date.tzinfo) if start_date.tzinfo else datetime.now()
        
        # Calculate end date
        end_date = start_date + timedelta(days=duration_days)
        
        # Check if expired
        if now > end_date and duration_days < 9000:  # 9000+ means infinite
            logger.info(f"Partner {p.id} expired! Duration: {duration_days}, Start: {start_date}, End: {end_date}")
            # Force update JSON
            new_data = dict(p.data)
            new_data['active'] = 'No'
            p.data = new_data
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(p, 'data')
            expiry_updates_made = True
            
    if expiry_updates_made:
        db.commit()
        # Clear cache
        from app.core.redis import cache
        for lang in ['uk', 'en', 'ru', 'de', 'es']:
            cache.delete(f"partners:regular:{bot_id}:100:{lang}")
            cache.delete(f"partners:top:{bot_id}:10:{lang}")
    
    # Filter in Python to avoid JSONB query issues
    filtered = []
    
    # Helper to calculate days remaining
    def get_days_remaining(p_data, p_obj):
        start_str = p_data.get('start_date')
        if start_str:
            try:
                start = datetime.fromisoformat(start_str)
            except ValueError:
                start = p_obj.created_at or datetime.now()
        else:
            start = p_obj.created_at or datetime.now()
            
        try:
            dur = int(str(p_data.get('duration', '9999')).replace(' ', ''))
        except (ValueError, TypeError):
            dur = 9999
            
        if dur > 9000: 
            return 9999
            
        now = datetime.now(start.tzinfo) if start.tzinfo else datetime.now()
        elapsed = (now - start).days
        remaining = dur - elapsed
        return remaining

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
        
        # Resolve start date for display
        start_date_val = partner_data.get('start_date')
        if not start_date_val and p.created_at:
            start_date_val = p.created_at.isoformat()
            
        days_left = get_days_remaining(partner_data, p)
        
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
            "start_date": start_date_val,
            "days_remaining": days_left
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
    from datetime import datetime
    
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Auto-add start_date if not present
    if 'start_date' not in partner_data:
        partner_data['start_date'] = datetime.now().isoformat()
    
    partner = BusinessData(
        bot_id=bot_id,
        data_type='partner',
        data=partner_data
    )
    
    db.add(partner)
    db.commit()
    db.refresh(partner)
    
    # Clear partners cache so Mini App sees new partner immediately
    from app.core.redis import cache
    for lang in ['uk', 'en', 'ru', 'de', 'es']:
        cache.delete(f"partners:regular:{bot_id}:100:{lang}")
        cache.delete(f"partners:top:{bot_id}:10:{lang}")
    
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
    
    # Clear partners cache
    from app.core.redis import cache
    for lang in ['uk', 'en', 'ru', 'de', 'es']:
        cache.delete(f"partners:regular:{bot_id}:100:{lang}")
        cache.delete(f"partners:top:{bot_id}:10:{lang}")
    
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
    
    # Clear partners cache
    from app.core.redis import cache
    for lang in ['uk', 'en', 'ru', 'de', 'es']:
        cache.delete(f"partners:regular:{bot_id}:100:{lang}")
        cache.delete(f"partners:top:{bot_id}:10:{lang}")
    
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
