"""
Mini Apps Endpoints - Multi-tenant
Handles Telegram Mini Apps webhooks and data
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from uuid import UUID
import logging
import pathlib

from app.core.database import get_db
from app.core.dependencies import get_bot_id
from app.models.bot import Bot
from app.models.user import User
from app.models.analytics_event import AnalyticsEvent
from app.services import (
    UserService, TranslationService, PartnerService,
    ReferralService, EarningsService
)
from app.utils.telegram_webapp import (
    validate_telegram_init_data,
    get_user_id_from_init_data,
    get_start_param_from_init_data,
    parse_init_data
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/mini-app/bot-id", response_model=Dict[str, Any])
async def get_bot_id_from_init_data(
    init_data: str = Query(..., description="Telegram WebApp initData"),
    db: Session = Depends(get_db)
):
    """
    Get bot_id from initData by validating it with all bots.
    
    This allows Mini App to work without bot_id in URL.
    
    Args:
        init_data: Telegram WebApp initData
        db: Database session
    
    Returns:
        bot_id and bot info
    """
    # Try to validate initData with all active bots
    bots = db.query(Bot).filter(Bot.is_active == True).all()
    
    for bot in bots:
        if validate_telegram_init_data(init_data, bot.token):
            logger.info(f"Found bot from initData: {bot.id} ({bot.name})")
            return {
                "ok": True,
                "bot_id": str(bot.id),
                "bot_name": bot.name
            }
    
    raise HTTPException(status_code=404, detail="Bot not found for this initData")


@router.get("/mini-app/index.html", response_class=HTMLResponse)
async def mini_app_html_simple(
    db: Session = Depends(get_db)
):
    """
    Serve Mini App HTML page (without bot_id in path).
    
    Bot_id will be obtained from initData on the frontend.
    
    Args:
        db: Database session
    
    Returns:
        HTML content for Mini App
    """
    # Load HTML file
    current_file = pathlib.Path(__file__)  # app/api/v1/mini_apps.py
    app_dir = current_file.parent.parent.parent  # app/
    html_path = app_dir / "static" / "mini-app" / "index.html"
    
    if html_path.exists():
        try:
            html_content = html_path.read_text(encoding='utf-8')
            html_content = html_path.read_text(encoding='utf-8')
            # Prevent caching of index.html to ensure fresh version is always loaded
            return HTMLResponse(
                content=html_content,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        except Exception as e:
            logger.error(f"Error reading Mini App HTML: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error loading Mini App: {str(e)}")
    else:
        logger.error(f"Mini App HTML not found at: {html_path}")
        raise HTTPException(status_code=404, detail="Mini App HTML not found")


@router.get("/tonconnect-manifest.json")
@router.get("/{bot_id}/tonconnect-manifest.json")
async def tonconnect_manifest(
    request: Request,
    bot_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    Serve TON Connect manifest file.
    Supports optional bot_id to serve dynamic bot name/icon.
    """
    import pathlib
    import os
    from fastapi.responses import JSONResponse
    from app.models.bot import Bot
    
    current_file = pathlib.Path(__file__)
    app_dir = current_file.parent.parent.parent
    manifest_path = app_dir / "static" / "tonconnect-manifest.json"
    
    # Defaults
    bot_name = os.getenv("PROJECT_NAME", "EarnHub")
    
    # If bot_id is provided, try to find that specific bot
    if bot_id:
        try:
            target_bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if target_bot:
                bot_config = target_bot.config or {}
                # PRIORITIZE: Manual Name -> First Name (TG) -> Username (TG) -> Internal Name -> Fallback
                bot_name = (
                    bot_config.get("name") or 
                    bot_config.get("first_name") or 
                    bot_config.get("username") or 
                    target_bot.name or 
                    bot_name
                )
                logger.info(f"Using manifest for specific bot: {bot_name} ({bot_id})")
        except Exception as e:
            logger.error(f"Error fetching bot {bot_id} for manifest: {e}")
    else:
        # Fallback: Try to find the first active bot
        try:
            active_bot = db.query(Bot).filter(Bot.is_active == True).first()
            if active_bot:
                bot_config = active_bot.config or {}
                bot_name = (
                    bot_config.get("name") or 
                    bot_config.get("first_name") or 
                    bot_config.get("username") or 
                    active_bot.name or 
                    bot_name
                )
                logger.info(f"Using default dynamic name from active bot: {bot_name}")
        except Exception as db_err:
            logger.error(f"Error fetching default bot for manifest: {db_err}")
    
    icon_name = os.getenv("PROJECT_ICON", "icon.png")
    
    if manifest_path.exists():
        try:
            import json
            manifest_content = json.loads(manifest_path.read_text(encoding='utf-8'))
            
            # Update name with dynamic bot name
            manifest_content['name'] = bot_name
            
            # Update URL dynamically
            base_url = str(request.base_url).rstrip('/')
            if base_url.startswith('http://') and ('railway' in base_url or 'hubaggregator' in base_url):
                base_url = base_url.replace('http://', 'https://')
            
            manifest_content['url'] = base_url
            
            # Resolve relative iconUrl
            if manifest_content.get('iconUrl', '').startswith('/'):
                manifest_content['iconUrl'] = base_url + manifest_content['iconUrl']
            elif 'your-domain.com' in manifest_content.get('iconUrl', ''):
                manifest_content['iconUrl'] = f"{base_url}/static/mini-app/{icon_name}"
            
            return JSONResponse(content=manifest_content)
        except Exception as e:
            logger.error(f"Error reading TON Connect manifest: {e}", exc_info=True)
    
    # Fallback response
    base_url = str(request.base_url).rstrip('/')
    if base_url.startswith('http://') and ('railway' in base_url or 'hubaggregator' in base_url):
        base_url = base_url.replace('http://', 'https://')
        
    return JSONResponse(content={
        "url": base_url,
        "name": bot_name,
        "iconUrl": f"{base_url}/static/mini-app/{icon_name}"
    })


@router.get("/mini-app/{bot_id}/index.html", response_class=HTMLResponse)
async def mini_app_html(
    bot_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Serve Mini App HTML page (with bot_id in path - legacy endpoint).
    
    Args:
        bot_id: Bot UUID
        db: Database session
    
    Returns:
        HTML content for Mini App
    """
    # Verify bot exists
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if not bot.is_active:
        raise HTTPException(status_code=403, detail="Bot is inactive")
    
    # Load HTML file
    current_file = pathlib.Path(__file__)  # app/api/v1/mini_apps.py
    app_dir = current_file.parent.parent.parent  # app/
    html_path = app_dir / "static" / "mini-app" / "index.html"
    
    if html_path.exists():
        try:
            html_content = html_path.read_text(encoding='utf-8')
            html_content = html_path.read_text(encoding='utf-8')
            # Prevent caching of index.html to ensure fresh version is always loaded
            return HTMLResponse(
                content=html_content,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        except Exception as e:
            logger.error(f"Error reading Mini App HTML: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error loading Mini App: {str(e)}")
    else:
        logger.error(f"Mini App HTML not found at: {html_path}")
        raise HTTPException(status_code=404, detail="Mini App HTML not found")


@router.post("/mini-app/{bot_id}")
async def mini_app_webhook(
    request: Request,
    bot_id: UUID,
    data: Dict[str, Any],
    init_data: Optional[str] = Query(None, description="Telegram WebApp initData (for validation)"),
    db: Session = Depends(get_db)
):
    """
    Telegram Mini App webhook endpoint.
    Handles callbacks from Mini App (wallet save, partner clicks, etc.).
    Multi-tenant: bot_id identifies which bot instance.
    
    Rate limit: 20 requests/minute (enforced via middleware)
    
    Args:
        bot_id: Bot UUID
        data: Mini App callback data
        init_data: Telegram WebApp initData (for validation)
        db: Database session
    
    Returns:
        Response data
    """
    # Verify bot exists and is active
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if not bot.is_active:
        raise HTTPException(status_code=403, detail="Bot is inactive")
    
    # Validate initData if provided (check URL query first, then body)
    validated_user_id = None
    init_data_to_validate = init_data or data.get("init_data")  # Also check body
    
    if init_data_to_validate:
        if not validate_telegram_init_data(init_data_to_validate, bot.token):
            logger.warning(f"Invalid initData for bot_id={bot_id}")
            raise HTTPException(status_code=401, detail="Invalid initData signature")
        validated_user_id = get_user_id_from_init_data(init_data_to_validate)

    
    # Get action type from data
    action = data.get("action")
    
    # Log interaction for analytics
    if validated_user_id:
        logger.info(f"Mini App callback: bot_id={bot_id}, user_id={validated_user_id}, action={action}")
    
    # Handle partner click
    if action == "partner_click":
        # Log partner click
        partner_id = data.get("partner_id")
        logger.info(f"Partner click: bot_id={bot_id}, user_id={validated_user_id}, partner_id={partner_id}")
        return {"ok": True, "action": "partner_click", "logged": True}

    # Handle save custom data (e.g. tgr_link)
    if action == "save_custom_data":
        # Must have valid user to save data
        if not validated_user_id:
            logger.warning(f"save_custom_data called without valid user for bot_id={bot_id}")
            return {"ok": False, "error": "User not authenticated. Please reload the app."}
            
        custom_data_update = data.get("custom_data", {})
        if not custom_data_update:
            return {"ok": False, "error": "No custom_data provided"}
            
        logger.info(f"Saving custom data: bot_id={bot_id}, user_id={validated_user_id}, keys={list(custom_data_update.keys())}")
        
        try:
            # Get user
            user_service = UserService(db, bot_id)
            user = user_service.get_user(validated_user_id, platform="telegram")
            
            if not user:
                # Create user if doesn't exist (though likely exists if they are in mini app)
                user = user_service.get_or_create_user(
                    external_id=validated_user_id,
                    platform="telegram"
                )
            
            # Initialize or update custom_data
            from sqlalchemy.orm.attributes import flag_modified
            if not user.custom_data:
                user.custom_data = {}
                
            # Merge new data
            for key, value in custom_data_update.items():
                # Simple validation/sanitization could go here
                if key == "tgr_link" and value:
                    # Specific validation for TGR link if needed
                    pass
                user.custom_data[key] = value
                
            flag_modified(user, 'custom_data')
            db.commit()
            
            # TRACKING: Log TGR link save for Admin Panel analytics
            if "tgr_link" in custom_data_update:
                try:
                    from app.models.message import Message
                    import datetime
                    tgr_link = custom_data_update["tgr_link"]
                    log_msg = Message(
                        user_id=str(user.id),
                        bot_id=bot_id,
                        role='user',
                        content='/tgr_link_save',
                        custom_data={
                            'event': 'tgr_link_saved',
                            'tgr_link': tgr_link,
                            'source': 'mini_app',
                            'timestamp': datetime.datetime.utcnow().isoformat()
                        }
                    )
                    db.add(log_msg)
                    db.commit()
                    logger.info(f"✅ TGR link saved and logged for user {validated_user_id}")
                except Exception as log_err:
                    logger.error(f"Error logging TGR link save: {log_err}")
                    # Don't fail the whole operation if logging fails
            
            return {"ok": True, "action": "save_custom_data", "saved": True}
        except Exception as e:
            logger.error(f"Error saving custom data: {e}", exc_info=True)
            db.rollback()
            return {"ok": False, "error": str(e)}

    
    # Handle analytics events (Revenue Launcher)
    if data.get("type") == "analytics":
        event = data.get("event")
        event_data = data.get("data", {})
        logger.info(f"Analytics event: bot_id={bot_id}, user_id={validated_user_id}, event={event}, data={event_data}")
        
        # Store analytics event in database
        stored = False
        try:
            # Get user if exists
            user = None
            user_external_id = None
            if validated_user_id:
                user_external_id = validated_user_id
                user_service = UserService(db, bot_id)
                user = user_service.get_user(validated_user_id, platform="telegram")
                
                # Update user data from event_data if provided (username, device, etc.)
                if user and event_data:
                    from sqlalchemy.orm.attributes import flag_modified
                    updated = False
                    
                    # Initialize custom_data if not exists
                    if not user.custom_data:
                        user.custom_data = {}
                    
                    # Update username if provided
                    if 'username' in event_data and event_data['username']:
                        if user.custom_data.get('username') != event_data['username']:
                            user.custom_data['username'] = event_data['username']
                            updated = True
                    
                    # Update first_name if provided
                    if 'first_name' in event_data and event_data['first_name']:
                        if user.custom_data.get('first_name') != event_data['first_name']:
                            user.custom_data['first_name'] = event_data['first_name']
                            updated = True
                    
                    # Update last_name if provided
                    if 'last_name' in event_data and event_data['last_name']:
                        if user.custom_data.get('last_name') != event_data['last_name']:
                            user.custom_data['last_name'] = event_data['last_name']
                            updated = True
                    
                    # Update device if provided
                    if 'device' in event_data and event_data['device']:
                        if user.custom_data.get('device') != event_data['device']:
                            user.custom_data['device'] = event_data['device']
                            updated = True
                    
                    # Update device_version if provided
                    if 'device_version' in event_data and event_data['device_version']:
                        if user.custom_data.get('device_version') != event_data['device_version']:
                            user.custom_data['device_version'] = event_data['device_version']
                            updated = True
                    
                    # Update platform if provided
                    if 'platform' in event_data and event_data['platform']:
                        if user.custom_data.get('platform') != event_data['platform']:
                            user.custom_data['platform'] = event_data['platform']
                            updated = True
                    
                    # Update language_code if provided
                    if 'language_code' in event_data and event_data['language_code']:
                        if user.language_code != event_data['language_code']:
                            user.language_code = event_data['language_code']
                            updated = True
                    
                    if updated:
                        flag_modified(user, 'custom_data')
                        db.commit()
                        logger.info(f"Updated user data from analytics event: user_id={user.id}, external_id={user_external_id}")
            
            # Create analytics event
            analytics_event = AnalyticsEvent(
                bot_id=bot_id,
                user_id=user.id if user else None,
                user_external_id=user_external_id,
                event_name=event or "unknown",
                event_data=event_data or {},
                platform="telegram"
            )
            db.add(analytics_event)
            
            # ALSO CREATE MESSAGE RECORD for Admin Panel visibility
            # This satisfies the requirement to see "commands" in the admin panel
            if user:
                from app.models.message import Message
                import datetime
                
                # Map event to command style
                command_name = f"/{event}"
                if event == "view_home": command_name = "/start"
                elif event == "view_partners": command_name = "/partners"
                elif event == "view_top": command_name = "/top"
                elif event == "view_earnings": command_name = "/earnings"
                
                # Create message
                msg = Message(
                    bot_id=bot_id,
                    user_id=user.id,
                    role="user",
                    content=command_name,
                    custom_data={
                        "source": "mini_app",
                        "event": event,
                        "platform": "telegram_miniapp",
                        **event_data  # Merge details like partner_id
                    },
                    timestamp=datetime.datetime.utcnow()
                )
                db.add(msg)
                logger.info(f"Created Message record for analytics event: {command_name} (user_id={user.id})")
            
            db.commit()
            stored = True
            
        except Exception as e:
            # Log error but don't fail the request
            logger.error(f"Error storing analytics/message event: {e}", exc_info=True)
            db.rollback()
        
        return {"ok": True, "event": event, "logged": True, "stored": stored}
    
    # Default response
    return {"ok": True, "data": data}


@router.post("/mini-app/{bot_id}/wallet")
async def save_wallet_from_mini_app(
    request: Request,
    bot_id: UUID,
    wallet_address: str = Query(..., description="TON wallet address"),
    init_data: Optional[str] = Query(None, description="Telegram WebApp initData (for validation)"),
    user_id: Optional[str] = Query(None, description="User external ID (if initData not provided)"),
    db: Session = Depends(get_db)
):
    """
    Save wallet address from Mini App.
    
    Rate limit: 10 requests/minute (enforced via middleware)
    
    Args:
        bot_id: Bot UUID
        wallet_address: TON wallet address
        init_data: Telegram WebApp initData (for validation)
        user_id: User external ID (fallback if initData not provided)
        db: Database session
    
    Returns:
        Success/error response
    """
    # Verify bot
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if not bot.is_active:
        raise HTTPException(status_code=403, detail="Bot is inactive")
    
    # Validate initData if provided
    validated_user_id = None
    if init_data:
        if not validate_telegram_init_data(init_data, bot.token):
            logger.warning(f"Invalid initData for bot_id={bot_id}")
            raise HTTPException(status_code=401, detail="Invalid initData signature")
        validated_user_id = get_user_id_from_init_data(init_data)
        if not validated_user_id:
            raise HTTPException(status_code=400, detail="Could not extract user_id from initData")
    
    # Use validated user_id or fallback to provided user_id
    final_user_id = validated_user_id or user_id
    if not final_user_id:
        raise HTTPException(status_code=400, detail="user_id or init_data required")
    
    # Initialize services
    user_service = UserService(db, bot_id)
    from app.services.wallet_service import WalletService
    wallet_service = WalletService(db, bot_id, user_service)
    
    # Get or create user
    user = user_service.get_user(final_user_id, platform="telegram")
    if not user:
        user = user_service.get_or_create_user(
            external_id=final_user_id,
            platform="telegram"
        )
    
    # Validate wallet format
    if not wallet_service.validate_wallet_format(wallet_address):
        # DEBUG: Log logic failure to DB to inspect EXACT received string
        try:
            from app.models.business_data import BusinessData
            debug_log = BusinessData(
                bot_id=bot_id,
                data_type='log',  # Use 'log' so it shows in Admin Panel
                data={
                    'event': 'wallet_validation_failed_api',
                    'user_id': str(final_user_id),
                    'received_wallet_string': str(wallet_address),
                    'received_type': str(type(wallet_address)),
                    'length': len(wallet_address)
                }
            )
            db.add(debug_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log debug info in API: {e}")
            
        raise HTTPException(status_code=400, detail="Invalid wallet format")
    
    # Save wallet using WalletService (same as bot, includes Telegram notification)
    try:
        from app.adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()
        
        # Use WalletService.save_wallet which handles validation and sends Telegram message
        saved = await wallet_service.save_wallet(user.id, wallet_address.strip(), adapter)
        
        if saved:
            logger.info(f"Wallet saved via WalletService: bot_id={bot_id}, user_id={user.id}, wallet={wallet_address[:20]}...")
            return {"ok": True, "message": "Wallet saved successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to save wallet")
    except Exception as e:
        logger.error(f"Error saving wallet: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error saving wallet: {str(e)}")


@router.post("/mini-app/{bot_id}/create-invoice")
async def create_invoice_link(
    bot_id: UUID,
    init_data: Optional[str] = Query(None, description="Telegram WebApp initData (for validation)"),
    user_id: Optional[str] = Query(None, description="User external ID (if initData not provided)"),
    db: Session = Depends(get_db)
):
    """
    Create invoice link for Telegram Stars payment (for buying TOP).
    Returns invoice link that can be used with tg.openInvoice() in Mini App.
    
    Args:
        bot_id: Bot UUID
        init_data: Telegram WebApp initData (for validation)
        user_id: User external ID (fallback if initData not provided)
        db: Database session
    
    Returns:
        Invoice link URL
    """
    # Verify bot
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if not bot.is_active:
        raise HTTPException(status_code=403, detail="Bot is inactive")
    
    # Validate initData if provided
    validated_user_id = None
    if init_data:
        if not validate_telegram_init_data(init_data, bot.token):
            logger.warning(f"Invalid initData for bot_id={bot_id}")
            raise HTTPException(status_code=401, detail="Invalid initData signature")
        validated_user_id = get_user_id_from_init_data(init_data)
        if not validated_user_id:
            raise HTTPException(status_code=400, detail="Could not extract user_id from initData")
    
    # Use validated user_id or fallback to provided user_id
    final_user_id = validated_user_id or user_id
    if not final_user_id:
        raise HTTPException(status_code=400, detail="user_id or init_data required")
    
    # Get user
    user_service = UserService(db, bot_id)
    user = user_service.get_user(final_user_id, platform="telegram")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get translation for invoice
    translation_service = TranslationService(db)
    lang = translation_service.detect_language(user.language_code)
    
    # Get price from config or default
    buy_top_price = 1
    if bot.config and isinstance(bot.config, dict):
        earnings_config = bot.config.get('earnings', {})
        buy_top_price = earnings_config.get('buy_top_price', 1)
    
    title = translation_service.get_translation('buy_top_title', lang) or "Розблокувати TOP"
    description = translation_service.get_translation('buy_top_description', lang) or "Розблокувати доступ до TOP партнерів"
    label = translation_service.get_translation('buy_top_label', lang) or f"{buy_top_price} Star{'s' if buy_top_price > 1 else ''}"
    
    # Create invoice payload (unique identifier for this payment)
    payload = f"buy_top_{bot_id}_{user.id}"
    
    # For Telegram Stars (XTR), amount is the number of stars directly
    # 1 star = amount: 1 (not 100 like other currencies)
    star_amount = buy_top_price  # 1 star = amount: 1
    
    prices = [{
        "label": label,
        "amount": star_amount  # For XTR (Stars), amount = number of stars
    }]
    
    # Create invoice link via TelegramAdapter
    try:
        from app.adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()
        
        invoice_link = await adapter.create_invoice_link(
            bot_id=bot_id,
            title=title,
            description=description,
            payload=payload,
            currency="XTR",  # XTR = Telegram Stars
            prices=prices
        )
        
        logger.info(f"Invoice link created: bot_id={bot_id}, user_id={user.id}, invoice_link={invoice_link[:50]}...")
        return {"ok": True, "invoice_link": invoice_link}
    except Exception as e:
        logger.error(f"Error creating invoice link: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating invoice link: {str(e)}")


@router.get("/mini-app/{bot_id}/data")
async def get_mini_app_data(
    request: Request,
    bot_id: UUID,
    init_data: Optional[str] = Query(None, description="Telegram WebApp initData (for validation)"),
    user_id: Optional[str] = Query(None, description="User external ID (if initData not provided)"),
    db: Session = Depends(get_db)
):
    """
    Get Mini App data for user.
    
    Rate limit: 10 requests/minute (enforced via middleware)
    
    Args:
        bot_id: Bot UUID
        init_data: Telegram WebApp initData (for validation)
        user_id: User external ID (fallback if initData not provided)
        db: Database session
    
    Returns:
        User data for Mini App (structured JSON)
    """
    # Verify bot
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if not bot.is_active:
        raise HTTPException(status_code=403, detail="Bot is inactive")
    
    # Validate initData if provided
    validated_user_id = None
    if init_data:
        if not validate_telegram_init_data(init_data, bot.token):
            logger.warning(f"Invalid initData for bot_id={bot_id}")
            raise HTTPException(status_code=401, detail="Invalid initData signature")
        validated_user_id = get_user_id_from_init_data(init_data)
        if not validated_user_id:
            raise HTTPException(status_code=400, detail="Could not extract user_id from initData")
    
    # Use validated user_id or fallback to provided user_id
    final_user_id = validated_user_id or user_id
    if not final_user_id:
        raise HTTPException(status_code=400, detail="user_id or init_data required")
    
    # Auto-sync bot username if missing (critical for TON Connect twaReturnUrl)
    bot_config = bot.config or {}
    if not bot_config.get("username"):
        try:
            from app.adapters.telegram import TelegramAdapter
            adapter = TelegramAdapter()
            bot_info = await adapter.get_bot_info(bot_id)
            bot_username = bot_info.get('username')
            if bot_username:
                # Save to bot.config for future use
                if not bot.config:
                    bot.config = {}
                bot.config['username'] = bot_username
                bot.config['bot_id'] = bot_info.get('id')
                bot.config['first_name'] = bot_info.get('first_name')
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(bot, 'config')
                db.commit()
                db.refresh(bot)
                logger.info(f"Auto-synced bot username: {bot_username} for bot_id={bot_id}")
                # Update bot_config for use below
                bot_config = bot.config
        except Exception as sync_err:
            logger.warning(f"Could not auto-sync bot username: {sync_err}")
    
    # Initialize services
    user_service = UserService(db, bot_id)
    translation_service = TranslationService(db, bot_id)
    referral_service = ReferralService(db, bot_id)
    partner_service = PartnerService(db, bot_id)
    earnings_service = EarningsService(
        db, bot_id, user_service, referral_service, translation_service
    )
    
    # Get or create user
    user = user_service.get_user(final_user_id, platform="telegram")
    if not user:
        # Create user if doesn't exist
        user = user_service.get_or_create_user(
            external_id=final_user_id,
            platform="telegram"
        )
    
    # Get all data
    try:
        # Check for referral (start_param) in init_data
        if init_data:
            start_param = get_start_param_from_init_data(init_data)
            if start_param:
                # Log referral event (ReferralService handles duplicates and validation)
                try:
                    referral_service.log_referral_event(
                        user_id=user.id,
                        ref_param=start_param,
                        event_type="mini_app_start",
                        click_type="Referral"
                    )
                    # Update total invited immediately so user sees correct stats if they are the referrer
                    # (Though usually ref_param is the INVITER's ID, so this logs that 'user' was invited)
                except Exception as ref_err:
                    logger.error(f"Error logging Mini App referral: {ref_err}")

        # SYNC USER DATA FROM INIT_DATA (Language, Name, Username)
        if init_data:
            try:
                parsed_data = parse_init_data(init_data)
                user_data = parsed_data.get('user', {})
                
                if user_data:
                    is_modified = False
                    
                    # 1. Sync Language (Critical for correct translations)
                    new_lang = user_data.get('language_code')
                    if new_lang and user.language_code != new_lang:
                        user.language_code = new_lang
                        is_modified = True
                        logger.info(f"Updated user language: {user.id} -> {new_lang}")
                    
                    # 2. Sync Profile Info (First Name, Last Name, Username)
                    # Initialize custom_data if needed
                    if not user.custom_data:
                        user.custom_data = {}
                        
                    # First Name
                    new_first_name = user_data.get('first_name')
                    if new_first_name and user.custom_data.get('first_name') != new_first_name:
                        user.custom_data['first_name'] = new_first_name
                        is_modified = True
                        
                    # Last Name
                    new_last_name = user_data.get('last_name')
                    if new_last_name and user.custom_data.get('last_name') != new_last_name:
                        user.custom_data['last_name'] = new_last_name
                        is_modified = True
                        
                    # Username
                    new_username = user_data.get('username')
                    if new_username and user.custom_data.get('username') != new_username:
                        user.custom_data['username'] = new_username
                        is_modified = True
                    
                    # 3. Save changes
                    if is_modified:
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(user, 'custom_data')
                        db.commit()
                        # Refresh to ensure services see updated data
                        db.refresh(user)
                        
            except Exception as sync_err:
                logger.error(f"Error syncing user data from init_data: {sync_err}")
                # Don't fail the request, just log error

        # Get user language for localization
        user_lang = user.language_code or 'en'
        user_lang = translation_service.detect_language(user_lang)
        
        # Earnings data
        earnings_data = earnings_service.get_earnings_data(user.id)
        
        # Partners (with user language for localized descriptions)
        partners = await partner_service.get_partners(user_lang=user_lang)
        
        # TOP partners (with user language for localized descriptions)
        top_partners = await partner_service.get_top_partners(user_lang=user_lang)
        
        # User wallet
        wallet = user_service.get_wallet(user.id)
        
        # Bot config
        bot_config = bot.config or {}
        
        # Get info and welcome messages (user_lang already detected above)
        info_message = translation_service.get_translation('info_main', user_lang)
        welcome_message = translation_service.get_translation('welcome', user_lang)
        
        # Get wallet help message (for when wallet is empty)
        wallet_help = translation_service.get_translation('wallet_help', user_lang)
        if not wallet_help or wallet_help == 'wallet_help':  # Translation not found
            wallet_help = translation_service.get_translation('wallet_not_found', user_lang)
            if not wallet_help or wallet_help == 'wallet_not_found':  # Still not found
                wallet_help = translation_service.get_translation('wallet_info_empty', user_lang) or ""
        
        # Get 7% program translations for earnings
        commission_percent = int(earnings_data["commission_rate"] * 100)
        
        # Get bot username for translation variables
        bot_username = bot_config.get('username', '').replace('@', '').strip() if bot_config.get('username') else ''
        if not bot_username and bot.name:
            import re
            bot_username = re.sub(r'[^a-zA-Z0-9_]', '', bot.name).strip().lower()
        
        # Group all UI translations
        ui_translations = {
            # Navigation
            "nav_home": translation_service.get_translation('nav_home', user_lang),
            "nav_partners": translation_service.get_translation('nav_partners', user_lang),
            "nav_top": translation_service.get_translation('nav_top', user_lang),
            "loading": translation_service.get_translation('loading', user_lang),
            "retry_btn": translation_service.get_translation('retry_btn', user_lang),

            # Hero / Quest
            "stat_friends": translation_service.get_translation('stat_friends', user_lang),
            "top_program_active": translation_service.get_translation('top_program_active', user_lang),
            "link_connected": translation_service.get_translation('link_connected', user_lang),
            "paste_link_placeholder": translation_service.get_translation('paste_link_placeholder', user_lang),
            "save": translation_service.get_translation('save', user_lang),
            "where_to_get_link": translation_service.get_translation('where_to_get_link', user_lang),
            "share_your_link": translation_service.get_translation('share_your_link', user_lang),
            "unlock_top_status": translation_service.get_translation('unlock_top_status', user_lang),
            "invite_5_subtitle": translation_service.get_translation('invite_5_subtitle', user_lang),
            "invited_count": translation_service.get_translation('invited_count', user_lang),
            "goal_text": translation_service.get_translation('goal_text', user_lang),
            "invite_and_earn": translation_service.get_translation('invite_and_earn', user_lang),
            
            # Nav Cards
            "browse": translation_service.get_translation('browse', user_lang),
            "partners": translation_service.get_translation('partners', user_lang),
            "verified_partners_desc": translation_service.get_translation('verified_partners_desc', user_lang),
            "top_bots": translation_service.get_translation('top_bots', user_lang),
            "top_bots_desc": translation_service.get_translation('top_bots_desc', user_lang),

            # Money Math
            "potential_earnings": translation_service.get_translation('potential_earnings', user_lang),
            "estimates_desc": translation_service.get_translation('estimates_desc', user_lang),

            # Wallet
            "connect": translation_service.get_translation('connect', user_lang),
            "wallet_banner_text": translation_service.get_translation('wallet_banner_text', user_lang),
            "enter_wallet_error": translation_service.get_translation('enter_wallet_error', user_lang),
            "invalid_wallet_format": translation_service.get_translation('invalid_wallet_format', user_lang),
            "wallet_saved_success": translation_service.get_translation('wallet_saved_success', user_lang),
            "wallet_save_error": translation_service.get_translation('wallet_save_error', user_lang),
            "ton_connect_help": translation_service.get_translation('ton_connect_help', user_lang),

            # Partners Page
            "no_partners": translation_service.get_translation('no_partners', user_lang),
            "recommended_title": translation_service.get_translation('recommended_title', user_lang),
            "recommended_subtitle": translation_service.get_translation('recommended_subtitle', user_lang),
            "show_all": translation_service.get_translation('show_all', user_lang),
            "no_partners_found": translation_service.get_translation('no_partners_found', user_lang),
            "launch_btn": translation_service.get_translation('launch_btn', user_lang),

            # Top Page
            "top_locked_title": translation_service.get_translation('top_locked_title', user_lang),
            "top_locked_subtitle": translation_service.get_translation('top_locked_subtitle', user_lang),
            "no_top_bots": translation_service.get_translation('no_top_bots', user_lang),
            "top_profits_title": translation_service.get_translation('top_profits_title', user_lang),
            "top_profits_subtitle": translation_service.get_translation('top_profits_subtitle', user_lang),
            "open_btn": translation_service.get_translation('open_btn', user_lang),
            "estimated_share": translation_service.get_translation('estimated_share', user_lang),
            "invited_label": translation_service.get_translation('invited_label', user_lang),
            "goal_label": translation_service.get_translation('goal_label', user_lang),
            "my_progress": translation_service.get_translation('my_progress', user_lang),
            "buy_top_btn": translation_service.get_translation('buy_top_btn', user_lang),
            "share_btn": translation_service.get_translation('share_btn', user_lang),
            
            # Footer
            "about_earnhub": translation_service.get_translation('about_earnhub', user_lang),
            "footer_about_text": translation_service.get_translation('footer_about_text', user_lang),
            "footer_disclaimer": translation_service.get_translation('footer_disclaimer', user_lang),
            "terms_of_use": translation_service.get_translation('terms_of_use', user_lang),
            "privacy_policy": translation_service.get_translation('privacy_policy', user_lang),
            "support": translation_service.get_translation('support', user_lang),
            
            # Gamification
            "badge_7_path": translation_service.get_translation('badge_7_path', user_lang),
            "badge_top_member": translation_service.get_translation('badge_top_member', user_lang),
            "badge_super_sharer": translation_service.get_translation('badge_super_sharer', user_lang),
            "your_earnings": translation_service.get_translation('your_earnings', user_lang),
            "program_active": translation_service.get_translation('program_active', user_lang),
            "program_inactive": translation_service.get_translation('program_inactive', user_lang),
            "achievements": translation_service.get_translation('achievements', user_lang),
            "unlock_top": translation_service.get_translation('unlock_top', user_lang),
            "to_pro": translation_service.get_translation('to_pro', user_lang),
            "to_hub": translation_service.get_translation('to_hub', user_lang),
            "max_level": translation_service.get_translation('max_level', user_lang),
            
            # Social Proof
            "started_path": translation_service.get_translation('started_path', user_lang),
            "top_opened_today": translation_service.get_translation('top_opened_today', user_lang),
            "partners_clicked_most": translation_service.get_translation('partners_clicked_most', user_lang),
            
            # Legacy/Specific (keeping for compatibility)
            "block2_title": translation_service.get_translation('earnings_block2_title', user_lang),
            "block2_how_it_works": translation_service.get_translation('earnings_block2_how_it_works', user_lang).replace('{{commission}}', str(commission_percent)).replace('[[commission]]', str(commission_percent)),
            "block2_examples": translation_service.get_translation('earnings_block2_examples', user_lang).replace('{{commission}}', str(commission_percent)).replace('[[commission]]', str(commission_percent)),
            "block2_enable_title": translation_service.get_translation('earnings_enable_7_title', user_lang),
            "block2_enable_steps": translation_service.get_translation('earnings_enable_7_steps', user_lang, {
                'bot_username': bot_username
            }),
            "block3_title": translation_service.get_translation('earnings_block3_title', user_lang),
            "step1": translation_service.get_translation('earnings_step1_open' if earnings_data["can_unlock_top"] else 'earnings_step1_locked', user_lang, {'needed': earnings_data["invites_needed"]} if not earnings_data["can_unlock_top"] else {}),
            "step2": translation_service.get_translation('earnings_step2', user_lang),
            "step3": translation_service.get_translation('earnings_step3', user_lang),
            "step4": translation_service.get_translation('earnings_step4', user_lang),
            "auto_stats": translation_service.get_translation('earnings_auto_stats', user_lang),
            "btn_unlock_top": translation_service.get_translation('earnings_btn_unlock_top', user_lang, {'buy_top_price': earnings_data["buy_top_price"]}),
            "btn_top_partners": translation_service.get_translation('earnings_btn_top_partners', user_lang),
            "btn_activate_7": translation_service.get_translation('earnings_btn_activate_7', user_lang),
            "share_popup_title": translation_service.get_translation('share_popup_title', user_lang),
            "share_button": translation_service.get_translation('share_button', user_lang),
            
            # Onboarding
            "onboarding_title_1": translation_service.get_translation('onboarding_title_1', user_lang),
            "onboarding_step_1": translation_service.get_translation('onboarding_step_1', user_lang),
            "onboarding_step_2": translation_service.get_translation('onboarding_step_2', user_lang),
            "onboarding_step_3": translation_service.get_translation('onboarding_step_3', user_lang),
            "next_btn": translation_service.get_translation('next_btn', user_lang),
            "start_btn": translation_service.get_translation('start_btn', user_lang),

            # Wallet Details
            "connect_telegram_wallet": translation_service.get_translation('connect_telegram_wallet', user_lang),
            "choose_other_wallet": translation_service.get_translation('choose_other_wallet', user_lang),
            "view_all_wallets": translation_service.get_translation('view_all_wallets', user_lang),
            "wallet_payouts_info": translation_service.get_translation('wallet_payouts_info', user_lang),
            "wallet_no_withdrawals": translation_service.get_translation('wallet_no_withdrawals', user_lang),
            "how_to_find_address": translation_service.get_translation('how_to_find_address', user_lang),
            "instruction_step_1": translation_service.get_translation('instruction_step_1', user_lang),
            "instruction_step_2": translation_service.get_translation('instruction_step_2', user_lang),
            "instruction_step_3": translation_service.get_translation('instruction_step_3', user_lang),
            "wallet_input_label": translation_service.get_translation('wallet_input_label', user_lang),
            "cancel": translation_service.get_translation('cancel', user_lang),

            # Gamification Labels
            "starter": translation_service.get_translation('starter', user_lang),
            "pro": translation_service.get_translation('pro', user_lang),
            "hub": translation_service.get_translation('hub', user_lang),
        }
        
        # Get user custom_data for Revenue Launcher
        user_custom_data = user.custom_data or {}
        
        # RECORD SESSION IN MESSAGES (Admin Panel Visibility)
        try:
            from app.models.message import Message
            import datetime
            
            # Create message
            msg = Message(
                bot_id=bot_id,
                user_id=user.id,
                role="user",
                # Use a distinct command for app load, but /start is standard
                content="/start (Mini App)", 
                custom_data={
                    "source": "mini_app_load",
                    "platform": "telegram_miniapp"
                },
                timestamp=datetime.datetime.utcnow()
            )
            db.add(msg)
            db.commit()
            logger.info(f"Created Message record for Mini App load: /start (user_id={user.id})")
        except Exception as msg_err:
            logger.error(f"Error logging Mini App load message: {msg_err}")
            # Don't fail the request
            
        return {
            "ok": True,
            "translations": ui_translations,  # ADDED: global translations object at root
            "user": {
                "id": str(user.id),
                "language_code": user_lang,  # CRITICAL: Required for Legal.js and other client-side localization
                "wallet": wallet or "",
                "balance": float(user.balance) if user.balance else 0.0,
                "total_invited": earnings_data["total_invited"],
                "top_status": earnings_data["top_status"],
                "referral_link": earnings_data["referral_link"],
                "custom_data": user_custom_data,  # Include custom_data for frontend
                "did_start_7_flow": user_custom_data.get("did_start_7_flow", False),  # Revenue Launcher flag
                "has_seen_onboarding": user_custom_data.get("has_seen_onboarding", False),  # Onboarding flag
            },
            "earnings": {
                "earned": earnings_data["earned"],
                "can_unlock_top": earnings_data["can_unlock_top"],
                "invites_needed": earnings_data["invites_needed"],
                "required_invites": earnings_data["required_invites"],
                "commission_rate": earnings_data["commission_rate"],
                "buy_top_price": earnings_data["buy_top_price"],
                "translations": ui_translations,
            },
            "partners": partners,
            "top_partners": top_partners,
            "info": {
                "message": info_message or "",
            },
            "welcome": {
                "message": welcome_message or "",
            },
            "wallet": {
                "help": wallet_help or "",
            },
            "config": {
                # Contract:
                # - `config.ui.*` is the canonical shape expected by Mini App frontend
                # Username is already synced above if missing (critical for TON Connect twaReturnUrl)
                "username": bot_config.get("username", ""),  # Bot username for TON Connect (required!)
                "name": (
                    bot_config.get("name") or 
                    bot_config.get("first_name") or 
                    bot_config.get("username") or 
                    bot.name or 
                    "Mini App"
                ),  # Bot name with dynamic fallback
                # - `theme/colors/features` are kept for backward compatibility with older frontends
                "ui": {
                    "theme": bot_config.get("ui", {}).get("theme", "dark"),
                    "colors": bot_config.get("ui", {}).get("colors", {}),
                    "features": bot_config.get("ui", {}).get("features", {}),
                    "force_dark": bool(bot_config.get("ui", {}).get("force_dark", False)),
                },
                "theme": bot_config.get("ui", {}).get("theme", "dark"),
                "colors": bot_config.get("ui", {}).get("colors", {}),
                "features": bot_config.get("ui", {}).get("features", {}),
            }
        }
    except Exception as e:
        logger.error(f"Error getting Mini App data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

@router.post("/mini-app/{bot_id}/notify-return")
async def notify_return(
    bot_id: UUID,
    init_data: Optional[str] = Query(None, description="Telegram WebApp initData (for validation)"),
    db: Session = Depends(get_db)
):
    """
    Send a "Return to App" message to user via bot.
    Used when user is redirected to bot profile to activate partner.
    
    Args:
        bot_id: Bot UUID
        init_data: Telegram WebApp initData
        db: Database session
    """
    # Verify bot
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Validate initData
    if not init_data:
        raise HTTPException(status_code=400, detail="init_data required")
    
    if not validate_telegram_init_data(init_data, bot.token):
        logger.warning(f"Invalid initData for bot_id={bot_id}")
        raise HTTPException(status_code=401, detail="Invalid initData signature")
    
    user_external_id = str(get_user_id_from_init_data(init_data))
    if not user_external_id:
        raise HTTPException(status_code=400, detail="Could not extract user_id from initData")
    
    # Get user for language
    user_service = UserService(db, bot_id)
    user = user_service.get_user(user_external_id, platform="telegram")
    if not user:
         raise HTTPException(status_code=404, detail="User not found")
    
    # Get translations
    translation_service = TranslationService(db, bot_id)
    lang = translation_service.detect_language(user.language_code)
    
    message_text = translation_service.get_translation('notify_return_message', lang)
    # Fallback if translation not in DB yet
    if message_text == 'notify_return_message':
        message_text = "⏳ <b>Очікуємо активації...</b>\n\nНатисніть кнопку нижче, щоб повернутися в Hub після активації."
    
    button_text = translation_service.get_translation('notify_return_button', lang)
    if button_text == 'notify_return_button':
        button_text = "🔙 Я все зробив! Відкрити Hub"
    
    # Get bot configuration for Mini App URL
    bot_username = (bot.config or {}).get('username', '').replace('@', '').strip()
    if not bot_username:
        # Try to get from name as fallback
        import re
        bot_username = re.sub(r'[^a-zA-Z0-9_]', '', bot.name).strip().lower()
    
    mini_app_url = f"https://t.me/{bot_username}/app"
    
    # Create keyboard with web_app button
    reply_markup = {
        "inline_keyboard": [[
            {
                "text": button_text,
                "web_app": {"url": mini_app_url}
            }
        ]]
    }
    
    # Send message via TelegramAdapter
    try:
        from app.adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()
        await adapter.send_message(
            bot_id=bot_id,
            user_external_id=user_external_id,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        logger.info(f"Notify-return message sent: bot_id={bot_id}, user={user_external_id}")
        return {"ok": True}
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error sending notify-return message: {e}")
        # Don't fail the request if message sending fails (e.g. user blocked bot)
        return {"ok": False, "error": str(e)}
