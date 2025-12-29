"""
Telegram Webhook Endpoints - Multi-tenant
Handles Telegram webhook updates and routes to command handlers
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID
import logging

from app.core.database import get_db
from app.models.bot import Bot
from app.adapters.telegram import TelegramAdapter
from app.services import (
    UserService, TranslationService, CommandService,
    PartnerService, ReferralService, EarningsService
)
from app.services.wallet_service import WalletService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/telegram/{bot_token}")
async def telegram_webhook(
    bot_token: str,
    update: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Telegram webhook endpoint.
    Multi-tenant: bot_token identifies which bot instance.
    
    Args:
        bot_token: Bot token (will be replaced with bot_id in production)
        update: Telegram update object
        db: Database session
    
    Returns:
        OK response
    """
    try:
        # Get bot by token
        bot = db.query(Bot).filter(Bot.token == bot_token).first()
        if not bot:
            logger.warning(f"Bot not found for token: {bot_token[:10]}...")
            return {"ok": False, "error": "Bot not found"}
        if not bot.is_active:
            logger.warning(f"Bot {bot.id} is inactive")
            return {"ok": False, "error": "Bot is inactive"}
        
        bot_id = bot.id
        
        # Initialize services
        user_service = UserService(db, bot_id)
        translation_service = TranslationService(db)
        referral_service = ReferralService(db, bot_id)
        partner_service = PartnerService(db, bot_id)
        earnings_service = EarningsService(
            db, bot_id, user_service, referral_service, translation_service
        )
        command_service = CommandService(
            db, bot_id, user_service, translation_service,
            partner_service, referral_service, earnings_service
        )
        
        # Initialize adapter
        adapter = TelegramAdapter()
        
        # Handle webhook
        event_data = await adapter.handle_webhook(bot_id, update)
        
        # Extract user info
        user_external_id = event_data.get('user_external_id', '')
        if not user_external_id:
            logger.warning("No user_external_id in webhook")
            return {"ok": True}
        
        # Get or create user
        from_user = update.get('message', {}).get('from') or \
                   update.get('callback_query', {}).get('from') or \
                   update.get('pre_checkout_query', {}).get('from') or {}
        
        user = user_service.get_or_create_user(
            external_id=user_external_id,
            platform="telegram",
            language_code=from_user.get('language_code'),
            username=from_user.get('username'),
            first_name=from_user.get('first_name'),
            last_name=from_user.get('last_name')
        )
        
        # Route by event type
        event_type = event_data.get('event_type', '')
        
        if event_type == 'message':
            await _handle_message(
                update, user, bot_id, command_service,
                referral_service, user_service, adapter, db
            )
        elif event_type == 'callback_query':
            await _handle_callback(
                update, user, bot_id, command_service,
                referral_service, user_service, adapter, db
            )
        elif event_type in ['pre_checkout_query', 'successful_payment']:
            await _handle_payment(
                update, user, bot_id, user_service, adapter, db
            )
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


async def _handle_message(
    update: Dict[str, Any],
    user,
    bot_id: UUID,
    command_service: CommandService,
    referral_service: ReferralService,
    user_service: UserService,
    adapter: TelegramAdapter,
    db: Session
):
    """Handle message event"""
    message = update.get('message', {})
    text = message.get('text', '').strip()
    
    # Check if it's a wallet address (not a command)
    if text and not text.startswith('/'):
        # Try to validate as wallet
        import re
        wallet_pattern = r'^(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_-]{46,48}$'
        if re.match(wallet_pattern, text):
            # It's a wallet address
            wallet_service = WalletService(db, bot_id, user_service)
            await wallet_service.save_wallet(user.id, text, adapter)
            return
    
    # Parse command
    command = command_service.parse_command(text)
    start_param = command_service.extract_start_parameter(text)
    
    # Log referral if /start with param
    if command == 'start' and start_param:
        referral_service.log_referral_event(
            user.id,
            start_param,
            event_type='start',
            click_type='Referral' if referral_service.parse_referral_parameter(start_param)[0] else 'Organic'
        )
    
    # Handle command
    if command:
        response = command_service.handle_command(
            command,
            user.id,
            user_lang=user.language_code,
            start_param=start_param
        )
        
        # Send response via adapter
        await adapter.send_message(
            bot_id,
            user.external_id,
            response.get('message', ''),
            reply_markup=_format_buttons(response.get('buttons', [])),
            parse_mode=response.get('parse_mode', 'HTML')
        )


async def _handle_callback(
    update: Dict[str, Any],
    user,
    bot_id: UUID,
    command_service: CommandService,
    referral_service: ReferralService,
    user_service: UserService,
    adapter: TelegramAdapter,
    db: Session
):
    """Handle callback_query event"""
    callback_query = update.get('callback_query', {})
    data = callback_query.get('data', '').strip()
    
    # Answer callback (remove loading state)
    # This would be done via adapter, but for now we'll handle in command
    
    # Parse callback data
    if data.startswith('/'):
        # It's a command
        command = command_service.parse_command(data)
        if command:
            response = command_service.handle_command(
                command,
                user.id,
                user_lang=user.language_code
            )
            
            await adapter.send_message(
                bot_id,
                user.external_id,
                response.get('message', ''),
                reply_markup=_format_buttons(response.get('buttons', [])),
                parse_mode=response.get('parse_mode', 'HTML')
            )
    elif data == 'buy_top' or data == '/buy_top':
        # Handle buy_top payment
        await _handle_buy_top(user, bot_id, adapter, db)
    elif data == 'activate_7':
        # Handle 7% activation instructions
        await _handle_activate_7(user, bot_id, command_service, adapter, db)
    elif data.startswith('share_from_'):
        # Handle share callback
        await _handle_share_callback(user, bot_id, command_service, adapter, db)


async def _handle_payment(
    update: Dict[str, Any],
    user,
    bot_id: UUID,
    user_service: UserService,
    adapter: TelegramAdapter,
    db: Session
):
    """Handle payment events (pre_checkout_query, successful_payment)"""
    if 'pre_checkout_query' in update:
        # Answer pre-checkout (approve payment)
        pre_checkout = update['pre_checkout_query']
        query_id = pre_checkout.get('id')
        invoice_payload = pre_checkout.get('invoice_payload', '')
        
        # Verify payload starts with buy_top
        if invoice_payload.startswith('buy_top_'):
            # Approve payment
            await adapter.answer_pre_checkout_query(
                bot_id,
                query_id,
                ok=True
            )
        else:
            # Reject unknown payment
            await adapter.answer_pre_checkout_query(
                bot_id,
                query_id,
                ok=False,
                error_message="Unknown payment"
            )
    elif update.get('message', {}).get('successful_payment'):
        # Payment successful - unlock TOP
        payment = update['message']['successful_payment']
        invoice_payload = payment.get('invoice_payload', '')
        
        # Verify it's a buy_top payment
        if invoice_payload.startswith('buy_top_'):
            # Unlock TOP
            user_service.update_top_status(user.id, 'open')
            
            # Send confirmation
            translation_service = TranslationService(db)
            lang = translation_service.detect_language(user.language_code)
            message = translation_service.get_translation('top_unlocked', lang)
            
            await adapter.send_message(
                bot_id,
                user.external_id,
                message,
                parse_mode='HTML'
            )


async def _handle_buy_top(
    user,
    bot_id: UUID,
    adapter: TelegramAdapter,
    db: Session
):
    """Handle buy_top callback - send invoice"""
    # Get bot
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        return
    
    # Get translation for invoice
    translation_service = TranslationService(db)
    lang = translation_service.detect_language(user.language_code)
    
    title = translation_service.get_translation('buy_top_title', lang)
    description = translation_service.get_translation('buy_top_description', lang)
    price = int(translation_service.get_translation('buy_top_price', lang) or 1)
    
    # Convert price to Telegram Stars format (price * 100)
    # 1 Star = 100 in Telegram API
    star_amount = price * 100
    
    # Create invoice payload (unique identifier for this payment)
    payload = f"buy_top_{bot_id}_{user.id}"
    
    # Send invoice via Telegram API
    prices = [{
        "label": f"{price} Star{'s' if price > 1 else ''}",
        "amount": star_amount
    }]
    
    try:
        await adapter.send_invoice(
            bot_id=bot_id,
            user_external_id=user.external_id,
            title=title,
            description=description,
            payload=payload,
            currency="XTR",  # XTR = Telegram Stars
            prices=prices
        )
    except Exception as e:
        # Log error but don't crash
        import logging
        logging.error(f"Error sending invoice: {e}")


async def _handle_activate_7(
    user,
    bot_id: UUID,
    command_service: CommandService,
    adapter: TelegramAdapter,
    db: Session
):
    """Handle activate_7 callback - show instructions"""
    translation_service = TranslationService(db)
    lang = translation_service.detect_language(user.language_code)
    
    message = translation_service.get_translation('earnings_7_instructions', lang)
    
    buttons = [[
        {
            'text': translation_service.get_translation('earnings_btn_unlock_top', lang, {'buy_top_price': 1}),
            'callback_data': 'buy_top'
        },
        {
            'text': translation_service.get_translation('earnings_btn_top_partners', lang),
            'callback_data': '=/top'
        }
    ]]
    
    await adapter.send_message(
        bot_id,
        user.external_id,
        message,
        reply_markup=_format_buttons(buttons),
        parse_mode='HTML'
    )


async def _handle_share_callback(
    user,
    bot_id: UUID,
    command_service: CommandService,
    adapter: TelegramAdapter,
    db: Session
):
    """Handle share callback - show referral link"""
    response = command_service.handle_command('share', user.id, user_lang=user.language_code)
    
    await adapter.send_message(
        bot_id,
        user.external_id,
        response.get('message', ''),
        reply_markup=_format_buttons(response.get('buttons', [])),
        parse_mode=response.get('parse_mode', 'HTML')
    )


def _format_buttons(buttons: list) -> Dict[str, Any]:
    """
    Format buttons for Telegram inline keyboard.
    
    Args:
        buttons: List of button rows
    
    Returns:
        Telegram inline keyboard format
    """
    if not buttons:
        return {}
    
    rows = []
    for row in buttons:
        button_row = []
        for btn in row:
            button = {
                'text': btn.get('text', '')
            }
            
            if 'url' in btn:
                button['url'] = btn['url']
            elif 'callback_data' in btn:
                button['callback_data'] = btn['callback_data']
            
            button_row.append(button)
        rows.append(button_row)
    
    return {
        'inline_keyboard': rows
    }

