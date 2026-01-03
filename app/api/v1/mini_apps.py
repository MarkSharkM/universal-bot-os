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
from app.services import (
    UserService, TranslationService, PartnerService,
    ReferralService, EarningsService
)
from app.utils.telegram_webapp import (
    validate_telegram_init_data,
    get_user_id_from_init_data
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
            return HTMLResponse(content=html_content)
        except Exception as e:
            logger.error(f"Error reading Mini App HTML: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error loading Mini App: {str(e)}")
    else:
        logger.error(f"Mini App HTML not found at: {html_path}")
        raise HTTPException(status_code=404, detail="Mini App HTML not found")


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
            return HTMLResponse(content=html_content)
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
    
    # Validate initData if provided
    validated_user_id = None
    if init_data:
        if not validate_telegram_init_data(init_data, bot.token):
            logger.warning(f"Invalid initData for bot_id={bot_id}")
            raise HTTPException(status_code=401, detail="Invalid initData signature")
        validated_user_id = get_user_id_from_init_data(init_data)
    
    # Get action type from data
    action = data.get("action")
    
    # Log interaction for analytics
    if validated_user_id:
        logger.info(f"Mini App callback: bot_id={bot_id}, user_id={validated_user_id}, action={action}")
    
    # Handle different actions
    if action == "partner_click":
        # Log partner click
        partner_id = data.get("partner_id")
        logger.info(f"Partner click: bot_id={bot_id}, user_id={validated_user_id}, partner_id={partner_id}")
        return {"ok": True, "action": "partner_click", "logged": True}
    
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
        raise HTTPException(status_code=400, detail="Invalid wallet format")
    
    # Save wallet
    try:
        user_service.update_wallet(user.id, wallet_address.strip())
        logger.info(f"Wallet saved: bot_id={bot_id}, user_id={user.id}, wallet={wallet_address[:20]}...")
        return {"ok": True, "message": "Wallet saved successfully"}
    except Exception as e:
        logger.error(f"Error saving wallet: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error saving wallet: {str(e)}")


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
        # Get user language for localization
        user_lang = user.language_code or 'en'
        user_lang = translation_service.detect_language(user_lang)
        
        # Earnings data
        earnings_data = earnings_service.get_earnings_data(user.id)
        
        # Partners (with user language for localized descriptions)
        partners = partner_service.get_partners(user_lang=user_lang)
        
        # TOP partners (with user language for localized descriptions)
        top_partners = partner_service.get_top_partners(user_lang=user_lang)
        
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
        earnings_translations = {
            "block2_title": translation_service.get_translation('earnings_block2_title', user_lang),
            "block2_how_it_works": translation_service.get_translation('earnings_block2_how_it_works', user_lang).replace('{{commission}}', str(commission_percent)).replace('[[commission]]', str(commission_percent)),
            "block2_examples": translation_service.get_translation('earnings_block2_examples', user_lang).replace('{{commission}}', str(commission_percent)).replace('[[commission]]', str(commission_percent)),
            "block2_enable_title": translation_service.get_translation('earnings_enable_7_title', user_lang),
            "block2_enable_steps": translation_service.get_translation('earnings_enable_7_steps', user_lang),
            "block3_title": translation_service.get_translation('earnings_block3_title', user_lang),
            "step1": translation_service.get_translation('earnings_step1_open' if earnings_data["can_unlock_top"] else 'earnings_step1_locked', user_lang, {'needed': earnings_data["invites_needed"]} if not earnings_data["can_unlock_top"] else {}),
            "step2": translation_service.get_translation('earnings_step2', user_lang),
            "step3": translation_service.get_translation('earnings_step3', user_lang),
            "step4": translation_service.get_translation('earnings_step4', user_lang),
            "auto_stats": translation_service.get_translation('earnings_auto_stats', user_lang),
            "btn_unlock_top": translation_service.get_translation('earnings_btn_unlock_top', user_lang, {'buy_top_price': earnings_data["buy_top_price"]}),
            "btn_top_partners": translation_service.get_translation('earnings_btn_top_partners', user_lang),
            "btn_activate_7": translation_service.get_translation('earnings_btn_activate_7', user_lang),
        }
        
        return {
            "ok": True,
            "user": {
                "wallet": wallet or "",
                "balance": float(user.balance) if user.balance else 0.0,
                "total_invited": earnings_data["total_invited"],
                "top_status": earnings_data["top_status"],
                "referral_link": earnings_data["referral_link"],
            },
            "earnings": {
                "earned": earnings_data["earned"],
                "can_unlock_top": earnings_data["can_unlock_top"],
                "invites_needed": earnings_data["invites_needed"],
                "required_invites": earnings_data["required_invites"],
                "commission_rate": earnings_data["commission_rate"],
                "buy_top_price": earnings_data["buy_top_price"],
                "translations": earnings_translations,
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
                # - `theme/colors/features` are kept for backward compatibility with older frontends
                "name": bot_config.get("name", bot.name or "Bot"),
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

