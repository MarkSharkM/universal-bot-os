"""
Messages endpoints for Admin API.
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


@router.post("/bots/{bot_id}/test-command")
async def test_command(
    bot_id: UUID,
    command: str = Query(..., description="Command to test (e.g., /start, /wallet, /partners)"),
    user_external_id: Optional[str] = Query(None, description="Test user external ID (default: test_user)"),
    user_lang: Optional[str] = Query("uk", description="User language code"),
    source: Optional[str] = Query("admin_test", description="Source of the test"),
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
        source: Source of the test (default: "admin_test")
        db: Database session
    
    Returns:
        Command response (message, buttons, etc.) with detailed debug info
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"test_command: bot_id={bot_id}, command={command}, user_external_id={user_external_id}, user_lang={user_lang}, source={source}")
    
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
            custom_data={'is_test': True, 'source': source}
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
                custom_data={'is_test': True, 'source': source}
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
            "source": source,
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
        
        # Priority: 1. Event/Message historical language, 2. User current language
        msg_custom_data = user_msg.custom_data or {}
        language = msg_custom_data.get('language_code') or msg_custom_data.get('language')
        if not language:
             language = user.language_code if user.language_code not in ['iOS', 'Android'] else (custom_data.get('language', 'uk'))
        wallet_address = custom_data.get('wallet_address', '')
        total_invited = custom_data.get('total_invited', 0)
        top_status = custom_data.get('top_status', 'locked')
        balance = float(user.balance) if user.balance else 0.0
        
        # Get source and platform from message custom_data (for Mini App events)
        msg_custom_data = user_msg.custom_data or {}
        source = msg_custom_data.get('source', '')
        
        # Check for platform in message custom_data (Mini App sends this from Telegram WebApp API)
        msg_platform = msg_custom_data.get('platform', '')
        if msg_platform and not device:
            device = msg_platform  # Use platform from message if user device not set
        
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
            "source": source,
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
