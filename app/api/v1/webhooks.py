"""
Telegram Webhook Endpoints - Multi-tenant
Handles Telegram webhook updates and routes to command handlers
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, Any
from uuid import UUID
import logging

from app.core.database import get_db
from app.models.bot import Bot
from app.models.user import User
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
    background_tasks: BackgroundTasks,
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
        
        # Update last_activity (updated_at) on any user interaction
        from datetime import datetime
        from sqlalchemy.orm.attributes import flag_modified
        user.updated_at = datetime.now()
        db.commit()
        db.refresh(user)  # Refresh to get updated timestamp
        
        # Route by event type
        # IMPORTANT: Respond to Telegram webhook IMMEDIATELY (200 OK)
        # Then process message asynchronously in background to avoid blocking
        # Telegram requires webhook response within seconds, otherwise it retries
        event_type = event_data.get('event_type', '')
        
        # Add background task for message processing (non-blocking)
        # FastAPI will execute these after sending response to Telegram
        if event_type == 'message':
            # Create new DB session for background task (current session will close after response)
            background_tasks.add_task(_handle_message_async,
                update, user.id, bot_id, event_data
            )
        elif event_type == 'callback_query':
            background_tasks.add_task(_handle_callback_async,
                update, user.id, bot_id
            )
        elif event_type in ['pre_checkout_query', 'successful_payment']:
            background_tasks.add_task(_handle_payment_async,
                update, user.id, bot_id
            )
        
        # Return immediately - don't wait for Telegram API or DB operations
        # Background tasks will execute after response is sent
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


async def _handle_message_async(
    update: Dict[str, Any],
    user_id: UUID,
    bot_id: UUID,
    event_data: Dict[str, Any]
):
    """
    Async wrapper for message handling - creates new DB session for background task.
    This allows webhook to return immediately while message is processed in background.
    """
    logger.info(f"_handle_message_async: START - user_id={user_id}, bot_id={bot_id}, event_type={event_data.get('event_type', 'unknown')}")
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found in background task")
            return
        logger.info(f"_handle_message_async: user found - external_id={user.external_id}")
        
        # Initialize services with new DB session
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
        adapter = TelegramAdapter()
        
        await _handle_message(
            update, user, bot_id, command_service,
            referral_service, user_service, adapter, db, event_data
        )
        logger.info(f"_handle_message_async: COMPLETED successfully for user_id={user_id}")
    except Exception as e:
        logger.error(f"Error in background message handler: {e}", exc_info=True)
    finally:
        db.close()
        logger.info(f"_handle_message_async: DB session closed for user_id={user_id}")


async def _handle_message(
    update: Dict[str, Any],
    user,
    bot_id: UUID,
    command_service: CommandService,
    referral_service: ReferralService,
    user_service: UserService,
    adapter: TelegramAdapter,
    db: Session,
    event_data: Dict[str, Any]
):
    """Handle message event"""
    message = update.get('message', {})
    text = message.get('text', '')
    if text:
        text = text.strip()
    message_id = message.get('message_id')
    
    logger.info(f"_handle_message: text='{text[:50]}...' (length={len(text) if text else 0}), starts_with_slash={text.startswith('/') if text else False}")
    
    # Save user message to database (for future AI and analytics)
    if text:
        from app.models.message import Message
        user_message = Message(
            user_id=user.id,
            bot_id=bot_id,
            role='user',
            content=text,
            custom_data={'telegram_message_id': message_id} if message_id else {}
        )
        db.add(user_message)
        db.commit()
    
    # Check if it's a wallet address (not a command)
    if text and not text.startswith('/'):
        # Try to validate as wallet using WalletService (supports bot.config)
        text_stripped = text.strip()
        wallet_service = WalletService(db, bot_id, user_service)
        if wallet_service.validate_wallet_format(text_stripped):
            # It's a wallet address
            logger.info(f"Detected wallet address for user_id={user.id}, external_id={user.external_id}, wallet={text_stripped[:20]}...")
            result = await wallet_service.save_wallet(user.id, text_stripped, adapter)
            logger.info(f"Wallet save result: {result} for user_id={user.id}")
            return
    
    # Parse command
    command = command_service.parse_command(text)
    logger.info(f"Parsed command: '{command}' from text: '{text[:50]}...' (user_id={user.id}, external_id={user.external_id})")
    
    # Try to get start parameter from metadata first (extracted by adapter)
    start_param = event_data.get('metadata', {}).get('start_parameter')
    # Fallback to extracting from text
    if not start_param:
        start_param = command_service.extract_start_parameter(text)
    
    if start_param:
        logger.info(f"Start parameter extracted: '{start_param}'")
    
    # Log referral if /start with param (but don't update inviter count yet - do it after sending message)
    inviter_external_id_for_update = None
    if command == 'start' and start_param:
        is_referral, inviter_id, ref_tag = referral_service.parse_referral_parameter(start_param)
        logger.info(f"Start with param: is_referral={is_referral}, inviter_id={inviter_id}, ref_tag={ref_tag}, start_param={start_param}")
        log_data = referral_service.log_referral_event(
            user.id,
            start_param,
            event_type='start',
            click_type='Referral' if is_referral else 'Organic'
        )
        # Store inviter_external_id to update count AFTER sending message (non-blocking)
        if is_referral and inviter_id:
            inviter_external_id_for_update = inviter_id
            logger.info(f"Will update inviter count for external_id={inviter_id} after sending message (log_data.id={log_data.id if log_data else 'None'})")
        else:
            logger.info(f"Not a referral or no inviter_id: is_referral={is_referral}, inviter_id={inviter_id}")
    
    # Handle command
    if command:
        logger.info(f"Handling command: {command} for user {user.id}")
        try:
            response = await command_service.handle_command(
                command,
                user.id,
                user_lang=user.language_code,
                start_param=start_param
            )
            
            if response.get('error'):
                logger.error(f"Command {command} returned error: {response.get('error')}")
            elif not response.get('message'):
                logger.warning(f"Command {command} returned empty message")
        except Exception as e:
            logger.error(f"Exception handling command {command}: {e}", exc_info=True)
            response = {'error': f'Error processing command: {str(e)}'}
        
        # Send response via adapter FIRST (don't block on DB commit)
        # Save bot response to database AFTER sending (async, non-blocking)
        try:
            message_text = response.get('message', '')
            message_length = len(message_text) if message_text else 0
            buttons_count = len(response.get('buttons', []))
            logger.info(f"Sending response for command {command}: message_length={message_length}, buttons={buttons_count}")
            
            # Add timeout protection - if command takes too long, log it
            # Increased to 180s to accommodate Telegram API retries (5 retries with 60s timeout each + backoff delays)
            # Max time: 60s timeout + (2+3+5+8+13)s backoff + 60s final attempt = ~151s, so 180s is safe
            import asyncio
            import time
            send_start_time = time.time()
            
            try:
                result = await asyncio.wait_for(
                    adapter.send_message(
                        bot_id,
                        user.external_id,
                        message_text,
                        reply_markup=_format_buttons(response.get('buttons', [])),
                        parse_mode=response.get('parse_mode', 'HTML')
                    ),
                    timeout=180.0  # 180 second timeout to accommodate retries (5 retries × 60s + backoff delays)
                )
                
                send_elapsed = time.time() - send_start_time
                if send_elapsed > 10.0:
                    logger.warning(f"Slow Telegram API response for command {command}: {send_elapsed:.2f}s (message_size={message_length}, buttons={buttons_count})")
                
                # Check if Telegram API returned error (e.g., timeout)
                if result.get('ok') is False:
                    error_type = result.get('error', 'unknown')
                    error_desc = result.get('description', '')
                    logger.error(f"Telegram API returned error for command {command}: {error_type} - {error_desc} (message_size={message_length}, buttons={buttons_count}, chat_id={user.external_id})")
                else:
                    # Log success with message_id if available
                    message_id = result.get('result', {}).get('message_id', 'N/A') if isinstance(result.get('result'), dict) else 'N/A'
                    logger.info(f"Successfully sent response for command {command} (message_size={message_length}, buttons={buttons_count}, chat_id={user.external_id}, telegram_message_id={message_id})")
            except asyncio.TimeoutError:
                send_elapsed = time.time() - send_start_time
                logger.error(f"Timeout sending message for command {command} after {send_elapsed:.2f}s (timeout=180s, message_size={message_length}, buttons={buttons_count})")
            except Exception as send_error:
                logger.error(f"Error sending message via Telegram API for command {command}: {send_error}", exc_info=True)
            
            # Update inviter's total_invited count AFTER attempting to send message (even if it failed)
            # This ensures counter is updated even if Telegram API fails (e.g., test users)
            # This prevents blocking webhook on slow SQL queries
            logger.info(f"Checking if need to update inviter: inviter_external_id_for_update={inviter_external_id_for_update} (type={type(inviter_external_id_for_update)}), command={command}, start_param={start_param}")
            if inviter_external_id_for_update:
                try:
                    logger.info(f"Looking for inviter with external_id={inviter_external_id_for_update}, bot_id={bot_id}")
                    inviter = db.query(User).filter(
                        and_(
                            User.bot_id == bot_id,
                            User.external_id == str(inviter_external_id_for_update),  # Ensure string comparison
                            User.platform == 'telegram'
                        )
                    ).first()
                    
                    if inviter:
                        # Save old count BEFORE update
                        old_count = inviter.custom_data.get('total_invited', 0) if inviter.custom_data else 0
                        logger.info(f"Found inviter: user_id={inviter.id}, external_id={inviter.external_id}, current_total_invited={old_count}, updating total_invited")
                        # Ensure DB sees the new log before counting
                        db.flush()
                        logger.info(f"DB flushed, calling update_total_invited for inviter user_id={inviter.id}")
                        updated_user = referral_service.update_total_invited(inviter.id)
                        # Note: update_total_invited already commits and refreshes, so we get the latest value
                        new_count = updated_user.custom_data.get('total_invited', 0) if updated_user.custom_data else 0
                        logger.info(f"Inviter total_invited updated successfully: new_count={new_count} (was {old_count}), user_id={inviter.id}, external_id={inviter.external_id}")
                    else:
                        logger.warning(f"Inviter not found for external_id={inviter_external_id_for_update}, bot_id={bot_id}. Checking all users with this external_id...")
                        # Debug: check if user exists with different platform
                        all_users = db.query(User).filter(User.external_id == str(inviter_external_id_for_update)).all()
                        logger.warning(f"Found {len(all_users)} users with external_id={inviter_external_id_for_update}: {[(u.id, u.bot_id, u.platform) for u in all_users]}")
                except Exception as update_error:
                    # Don't fail if update fails - message already sent
                    logger.error(f"Failed to update inviter total_invited: {update_error}", exc_info=True)
            else:
                logger.debug(f"No inviter_external_id_for_update to process")
                    
            # Save bot response to database AFTER attempting to send (non-blocking)
            if response.get('message'):
                try:
                    bot_message = Message(
                        user_id=user.id,
                        bot_id=bot_id,
                        role='assistant',
                        content=response.get('message', ''),
                        custom_data={}
                    )
                    db.add(bot_message)
                    db.commit()
                except Exception as db_error:
                    # Don't fail if DB save fails
                    logger.warning(f"Failed to save bot message to DB: {db_error}")
        except Exception as e:
            logger.error(f"Error in message sending block for command {command}: {e}", exc_info=True)
            # Don't raise - webhook should still return 200 OK to Telegram
    elif text:
        # Not a command, not a wallet - show wallet_invalid_format message (like in production)
        translation_service = TranslationService(db, bot_id)
        lang = translation_service.detect_language(user.language_code)
        error_message = translation_service.get_translation('wallet_invalid_format', lang)
        
        # Send error message FIRST (don't block on DB commit)
        try:
            await adapter.send_message(
                bot_id,
                user.external_id,
                error_message,
                parse_mode='HTML'
            )
            
            # Save bot response to database AFTER successful send (non-blocking)
            try:
                bot_message = Message(
                    user_id=user.id,
                    bot_id=bot_id,
                    role='assistant',
                    content=error_message,
                    custom_data={}
                )
                db.add(bot_message)
                db.commit()
            except Exception as db_error:
                # Don't fail if DB save fails - message already sent
                logger.warning(f"Failed to save error message to DB: {db_error}")
        except Exception as e:
            logger.error(f"Error sending error message via Telegram API: {e}", exc_info=True)


async def _handle_callback_async(
    update: Dict[str, Any],
    user_id: UUID,
    bot_id: UUID
):
    """
    Async wrapper for callback handling - creates new DB session for background task.
    """
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found in background callback task")
            return
        
        # Initialize services with new DB session
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
        adapter = TelegramAdapter()
        
        await _handle_callback(
            update, user, bot_id, command_service,
            referral_service, user_service, adapter, db
        )
    except Exception as e:
        logger.error(f"Error in background callback handler: {e}", exc_info=True)
    finally:
        db.close()


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
    callback_query_id = callback_query.get('id', '')
    
    # Answer callback (remove loading state)
    try:
        await adapter.answer_callback_query(bot_id, callback_query_id)
    except Exception as e:
        logger.warning(f"Failed to answer callback query: {e}")
    
    # Parse callback data
    # Check for buy_top first (even if it starts with /)
    if data == 'buy_top' or data == '/buy_top':
        # Handle buy_top payment
        try:
            await _handle_buy_top(user, bot_id, adapter, db)
        except Exception as e:
            logger.error(f"Error handling buy_top: {e}", exc_info=True)
            # Send error message to user
            translation_service = TranslationService(db, bot_id)
            lang = translation_service.detect_language(user.language_code)
            error_msg = f"❌ Помилка при відкритті інвойсу. Спробуйте пізніше."
            await adapter.send_message(
                bot_id,
                user.external_id,
                error_msg,
                parse_mode='HTML'
            )
    elif data == 'activate_7':
        # Handle 7% activation instructions
        await _handle_activate_7(user, bot_id, command_service, adapter, db)
    elif data.startswith('=/') or data.startswith('/'):
        # Handle commands (including =/top, =/earnings, /top, /earnings)
        # Remove = prefix if present
        command_text = data.lstrip('=')
        command = command_service.parse_command(command_text)
        if command:
            response = await command_service.handle_command(
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
        else:
            logger.warning(f"Unknown command in callback: {data}")
    else:
        # Unknown callback
        logger.warning(f"Unknown callback data: {data}")


async def _handle_payment_async(
    update: Dict[str, Any],
    user_id: UUID,
    bot_id: UUID
):
    """
    Async wrapper for payment handling - creates new DB session for background task.
    """
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found in background payment task")
            return
        
        # Initialize services with new DB session
        user_service = UserService(db, bot_id)
        adapter = TelegramAdapter()
        
        await _handle_payment(
            update, user, bot_id, user_service, adapter, db
        )
    except Exception as e:
        logger.error(f"Error in background payment handler: {e}", exc_info=True)
    finally:
        db.close()


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
        
        logger.info(f"Payment received: payload={invoice_payload}, user_id={user.id}")
        
        # Verify it's a buy_top payment
        if invoice_payload.startswith('buy_top_'):
            try:
                # Send confirmation FIRST (don't block on DB commit)
                translation_service = TranslationService(db, bot_id)
                lang = translation_service.detect_language(user.language_code)
                message = translation_service.get_translation('top_unlocked', lang)
                
                await adapter.send_message(
                    bot_id,
                    user.external_id,
                    message,
                    parse_mode='HTML'
                )
                
                # Unlock TOP (via payment) AFTER sending message (non-blocking)
                user_service.update_top_status(user.id, 'open', unlock_method='payment')
                logger.info(f"TOP unlocked for user {user.id} via payment")
            except Exception as e:
                logger.error(f"Error unlocking TOP: {e}", exc_info=True)
                # Try to send error message
                try:
                    await adapter.send_message(
                        bot_id,
                        user.external_id,
                        "❌ Помилка при розблокуванні TOP. Зверніться до підтримки.",
                        parse_mode='HTML'
                    )
                except:
                    pass
        else:
            logger.warning(f"Unknown payment payload: {invoice_payload}")


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
    
    # For Telegram Stars (XTR), amount is the number of stars directly
    # 1 star = amount: 1 (not 100 like other currencies)
    star_amount = price  # 1 star = amount: 1
    
    # Create invoice payload (unique identifier for this payment)
    payload = f"buy_top_{bot_id}_{user.id}"
    
    # Get label from translation
    label = translation_service.get_translation('buy_top_label', lang) or f"{price} Star{'s' if price > 1 else ''}"
    
    # Send invoice via Telegram API
    prices = [{
        "label": label,
        "amount": star_amount  # For XTR (Stars), amount = number of stars
    }]
    
    try:
        result = await adapter.send_invoice(
            bot_id=bot_id,
            user_external_id=user.external_id,
            title=title,
            description=description,
            payload=payload,
            currency="XTR",  # XTR = Telegram Stars
            prices=prices
        )
        logger.info(f"Invoice sent successfully: {result}")
    except Exception as e:
        # Log error and re-raise to handle in caller
        logger.error(f"Error sending invoice: {e}", exc_info=True)
        raise


async def _handle_activate_7(
    user,
    bot_id: UUID,
    command_service: CommandService,
    adapter: TelegramAdapter,
    db: Session
):
    """Handle activate_7 callback - show instructions"""
    translation_service = TranslationService(db, bot_id)
    lang = translation_service.detect_language(user.language_code)
    
    # Get bot username for translation variables
    from app.models.bot import Bot
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    bot_username = ''
    if bot:
        config = bot.config or {}
        username = config.get('username')
        if username:
            bot_username = username.replace('@', '').strip()
        elif bot.name:
            import re
            bot_username = re.sub(r'[^a-zA-Z0-9_]', '', bot.name).strip().lower()
    
    message = translation_service.get_translation('earnings_7_instructions', lang, {
        'bot_username': bot_username
    })
    
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




@router.post("/telegram-sync-test/{bot_id}")
async def telegram_webhook_sync_test(
    bot_id: UUID,
    update: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Synchronous test endpoint - waits for Telegram API response.
    Useful for performance testing with real Telegram API calls.
    
    Args:
        bot_id: Bot UUID
        update: Telegram update object
        db: Database session
    
    Returns:
        Response with timing info and Telegram API result
    """
    import time
    start_time = time.time()
    
    try:
        # Get bot by ID
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            logger.warning(f"Bot not found for id: {bot_id}")
            return {"ok": False, "error": "Bot not found", "elapsed": time.time() - start_time}
        if not bot.is_active:
            logger.warning(f"Bot {bot.id} is inactive")
            return {"ok": False, "error": "Bot is inactive", "elapsed": time.time() - start_time}
        
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
        
        # Initialize adapter
        adapter = TelegramAdapter()
        
        # Handle webhook
        event_data = await adapter.handle_webhook(bot_id, update)
        
        # Extract user info
        user_external_id = event_data.get('user_external_id', '')
        if not user_external_id:
            logger.warning("No user_external_id in webhook")
            return {"ok": True, "elapsed": time.time() - start_time, "note": "No user_external_id"}
        
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
        
        # Update last_activity
        from datetime import datetime
        user.updated_at = datetime.now()
        db.commit()
        db.refresh(user)
        
        # Process message SYNCHRONOUSLY (wait for Telegram API)
        event_type = event_data.get('event_type', '')
        
        telegram_start_time = time.time()
        
        if event_type == 'message':
            await _handle_message(
                update, user, bot_id, command_service,
                referral_service, user_service, adapter, db, event_data
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
        
        telegram_elapsed = time.time() - telegram_start_time
        total_elapsed = time.time() - start_time
        
        return {
            "ok": True,
            "elapsed": total_elapsed,
            "telegram_api_elapsed": telegram_elapsed,
            "event_type": event_type
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Sync webhook test error: {e}", exc_info=True)
        return {"ok": False, "error": str(e), "elapsed": elapsed}


@router.post("/telegram-test/{bot_id}")
async def telegram_webhook_test(
    bot_id: UUID,
    update: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Test endpoint for Telegram webhook - uses bot_id instead of bot_token.
    Useful for testing referral counter updates.
    
    Args:
        bot_id: Bot UUID
        update: Telegram update object
        background_tasks: FastAPI background tasks
        db: Database session
    
    Returns:
        OK response
    """
    try:
        # Get bot by ID
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            logger.warning(f"Bot not found for id: {bot_id}")
            return {"ok": False, "error": "Bot not found"}
        if not bot.is_active:
            logger.warning(f"Bot {bot.id} is inactive")
            return {"ok": False, "error": "Bot is inactive"}
        
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
        
        # Update last_activity (updated_at) on any user interaction
        from datetime import datetime
        from sqlalchemy.orm.attributes import flag_modified
        user.updated_at = datetime.now()
        db.commit()
        db.refresh(user)
        
        # Route by event type
        event_type = event_data.get('event_type', '')
        
        # Add background task for message processing (non-blocking)
        if event_type == 'message':
            background_tasks.add_task(_handle_message_async,
                update, user.id, bot_id, event_data
            )
        elif event_type == 'callback_query':
            background_tasks.add_task(_handle_callback_async,
                update, user.id, bot_id
            )
        elif event_type in ['pre_checkout_query', 'successful_payment']:
            background_tasks.add_task(_handle_payment_async,
                update, user.id, bot_id
            )
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Webhook test error: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


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

