"""
AI Endpoints - Multi-tenant
Handles AI chat interactions
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_bot_id
from app.services.ai_service import AIService
from app.services.translation_service import TranslationService
from app.models.bot import Bot

router = APIRouter()


class ChatRequest(BaseModel):
    """Request model for AI chat"""
    user_id: str
    message: str
    user_lang: str = "uk"


class ChatResponse(BaseModel):
    """Response model for AI chat"""
    response: str
    language: str


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    request: ChatRequest,
    bot_id: UUID = Depends(get_bot_id),
    db: Session = Depends(get_db)
):
    """
    AI chat endpoint.
    Multi-tenant: bot_id from header identifies which bot instance.
    
    Args:
        request: Chat request with user_id, message, user_lang
        bot_id: Bot UUID (from header)
        db: Database session
    
    Returns:
        AI-generated response
    """
    try:
        # Verify bot exists
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Initialize services
        translation_service = TranslationService(db, bot_id)
        ai_service = AIService(db, bot_id, translation_service)
        
        # Get user UUID
        from app.models.user import User
        user = db.query(User).filter(
            User.bot_id == bot_id,
            User.external_id == request.user_id
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate response
        response = await ai_service.generate_response(
            user.id,
            request.message,
            request.user_lang or user.language_code
        )
        
        lang = translation_service.detect_language(
            request.user_lang or user.language_code
        )
        
        return ChatResponse(
            response=response,
            language=lang
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_ai_config(
    bot_id: UUID = Depends(get_bot_id),
    db: Session = Depends(get_db)
):
    """
    Get AI configuration for bot.
    
    Args:
        bot_id: Bot UUID (from header)
        db: Database session
    
    Returns:
        AI configuration (without sensitive data)
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    ai_config = bot.config.get('ai', {})
    
    # Return config without API key
    return {
        'provider': ai_config.get('provider', 'openai'),
        'model': ai_config.get('model', 'gpt-4o-mini'),
        'temperature': ai_config.get('temperature', 0.7),
        'max_tokens': ai_config.get('max_tokens', 2000),
        'has_api_key': bool(ai_config.get('api_key')),
        'has_system_prompt': bool(ai_config.get('system_prompt')),
    }

