"""
FastAPI dependencies for multi-tenant architecture
"""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.models.bot import Bot


def get_bot_from_header(
    x_bot_id: Optional[str] = Header(None),
    x_bot_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Bot:
    """
    Get bot from header (for multi-tenant routing).
    
    In production, use bot_id from header or extract from token.
    
    Args:
        x_bot_id: Bot UUID from header
        x_bot_token: Bot token from header (alternative)
        db: Database session
    
    Returns:
        Bot object
    """
    if x_bot_id:
        try:
            bot_id = UUID(x_bot_id)
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            if not bot.is_active:
                raise HTTPException(status_code=403, detail="Bot is inactive")
            return bot
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bot_id format")
    
    if x_bot_token:
        bot = db.query(Bot).filter(Bot.token == x_bot_token).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if not bot.is_active:
            raise HTTPException(status_code=403, detail="Bot is inactive")
        return bot
    
    raise HTTPException(status_code=400, detail="Missing bot_id or bot_token header")


def get_bot_id(bot: Bot = Depends(get_bot_from_header)) -> UUID:
    """Extract bot_id from bot object"""
    return bot.id

