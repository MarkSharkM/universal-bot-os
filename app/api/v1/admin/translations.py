"""
Translations endpoints for Admin API.
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
