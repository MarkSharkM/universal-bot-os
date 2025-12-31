"""
Telegram adapter implementation
"""
from typing import Dict, Any, List
from uuid import UUID
import httpx

from app.adapters.base import BaseAdapter
from app.core.database import SessionLocal
from app.models import Bot


class TelegramAdapter(BaseAdapter):
    """Telegram platform adapter"""
    
    BASE_URL = "https://api.telegram.org/bot"
    
    # Timeout settings for Telegram API requests
    # Connect timeout: 15s (time to establish connection)
    # Read timeout: 60s (time to read response)
    # Increased to 60s to handle large messages with buttons/reply_markup
    # Telegram API can be slow during high load or with large payloads
    # Also increased connect timeout to handle network delays from Railway
    TIMEOUT = httpx.Timeout(60.0, connect=15.0, read=60.0)
    
    @property
    def platform_name(self) -> str:
        return "telegram"
    
    async def send_message(
        self,
        bot_id: UUID,
        user_external_id: str,
        text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send message via Telegram Bot API.
        
        Args:
            bot_id: Bot UUID
            user_external_id: Telegram chat_id
            text: Message text
            **kwargs: reply_markup, parse_mode, etc.
        """
        db = SessionLocal()
        try:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise ValueError(f"Bot {bot_id} not found")
            
            # TODO: Decrypt bot.token
            token = bot.token
            
            # Decode escaped newlines for proper Telegram formatting
            # When text comes from DB via JSON, \n becomes \\n (escaped)
            # We need to convert it back to actual newline character
            text = text.replace('\\n', '\n')
            
            url = f"{self.BASE_URL}{token}/sendMessage"
            payload = {
                "chat_id": user_external_id,
                "text": text,
                **kwargs
            }
            
            # Retry logic for network issues
            # 5 retries for network timeouts (max 6 attempts total)
            # This helps with temporary network issues between Railway and Telegram API
            # Increased retries because Telegram API can be slow during high load
            # With 60s read timeout, we give Telegram API more time to respond
            max_retries = 5
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                        response = await client.post(url, json=payload)
                        response.raise_for_status()
                        result = response.json()
                        # Log success on retry
                        if attempt > 0:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"Telegram API sendMessage succeeded on retry {attempt} (chat_id={user_external_id})")
                        return result
                except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                    last_error = e
                    if attempt < max_retries:
                        # Exponential backoff: 2s, 3s, 5s, 8s, 13s
                        import asyncio
                        import logging
                        logger = logging.getLogger(__name__)
                        # Fibonacci-like backoff for better spacing
                        delays = [2.0, 3.0, 5.0, 8.0, 13.0]
                        delay = delays[min(attempt, len(delays) - 1)]
                        logger.warning(f"Telegram API timeout for sendMessage (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay}s (chat_id={user_external_id})")
                        await asyncio.sleep(delay)
                        continue
                    # Log timeout after all retries
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Telegram API timeout for sendMessage after {max_retries + 1} attempts (chat_id={user_external_id}): {e}")
                    # Return error response instead of raising - don't block webhook
                    return {"ok": False, "error": "timeout", "description": "Telegram API timeout after retries"}
                except httpx.HTTPStatusError as e:
                    # Don't retry on HTTP errors (4xx, 5xx) - these are not network issues
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Telegram API error for sendMessage: {e.response.status_code} - {e.response.text}")
                    raise
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        import asyncio
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    raise
            
            # Should not reach here, but just in case
            if last_error:
                raise last_error
        finally:
            db.close()
    
    async def get_user_info(
        self,
        bot_id: UUID,
        user_external_id: str
    ) -> Dict[str, Any]:
        """Get user info from Telegram"""
        db = SessionLocal()
        try:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise ValueError(f"Bot {bot_id} not found")
            
            token = bot.token
            url = f"{self.BASE_URL}{token}/getChat"
            
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(url, json={"chat_id": user_external_id})
                response.raise_for_status()
                return response.json()
        finally:
            db.close()
    
    async def send_invoice(
        self,
        bot_id: UUID,
        user_external_id: str,
        title: str,
        description: str,
        payload: str,
        prices: List[Dict[str, Any]],
        currency: str = "XTR",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send invoice via Telegram Bot API.
        
        Args:
            bot_id: Bot UUID
            user_external_id: Telegram chat_id
            title: Invoice title
            description: Invoice description
            payload: Unique payload for payment
            currency: Currency code (XTR for Stars)
            prices: List of price objects [{"label": "...", "amount": 100}]
            **kwargs: provider_data, photo, etc.
        """
        db = SessionLocal()
        try:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise ValueError(f"Bot {bot_id} not found")
            
            token = bot.token
            url = f"{self.BASE_URL}{token}/sendInvoice"
            
            payload_data = {
                "chat_id": user_external_id,
                "title": title,
                "description": description,
                "payload": payload,
                "currency": currency,
                "prices": prices,
                **kwargs
            }
            
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(url, json=payload_data)
                response.raise_for_status()
                return response.json()
        finally:
            db.close()
    
    async def answer_callback_query(
        self,
        bot_id: UUID,
        callback_query_id: str,
        text: str = None,
        show_alert: bool = False
    ) -> Dict[str, Any]:
        """
        Answer callback query (remove loading state).
        
        Args:
            bot_id: Bot UUID
            callback_query_id: Callback query ID
            text: Optional text to show
            show_alert: Show as alert popup
        """
        db = SessionLocal()
        try:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise ValueError(f"Bot {bot_id} not found")
            
            token = bot.token
            url = f"{self.BASE_URL}{token}/answerCallbackQuery"
            
            payload = {
                "callback_query_id": callback_query_id,
            }
            if text:
                payload["text"] = text
            if show_alert:
                payload["show_alert"] = show_alert
            
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPStatusError as e:
                # 400 Bad Request usually means callback already answered or invalid
                # Don't raise - just log and return error response
                if e.response.status_code == 400:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Callback query already answered or invalid: {callback_query_id}")
                    return {"ok": False, "error": "callback_query_invalid"}
                raise
        finally:
            db.close()
    
    async def answer_pre_checkout_query(
        self,
        bot_id: UUID,
        pre_checkout_query_id: str,
        ok: bool = True,
        error_message: str = None
    ) -> Dict[str, Any]:
        """
        Answer pre-checkout query (approve or reject payment).
        
        Args:
            bot_id: Bot UUID
            pre_checkout_query_id: Pre-checkout query ID
            ok: True to approve, False to reject
            error_message: Error message if rejecting
        """
        db = SessionLocal()
        try:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise ValueError(f"Bot {bot_id} not found")
            
            token = bot.token
            url = f"{self.BASE_URL}{token}/answerPreCheckoutQuery"
            
            payload = {
                "pre_checkout_query_id": pre_checkout_query_id,
                "ok": ok
            }
            if not ok and error_message:
                payload["error_message"] = error_message
            
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        finally:
            db.close()
    
    async def get_bot_info(self, bot_id: UUID) -> Dict[str, Any]:
        """
        Get bot info from Telegram API (getMe).
        Caches username in bot.config['username'].
        
        Args:
            bot_id: Bot UUID
        
        Returns:
            Bot info dict with username, id, first_name, etc.
        """
        db = SessionLocal()
        try:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise ValueError(f"Bot {bot_id} not found")
            
            # Check cache first
            if bot.config and bot.config.get('username'):
                return {
                    'username': bot.config['username'],
                    'id': bot.config.get('bot_id'),
                    'first_name': bot.config.get('first_name', bot.name),
                }
            
            # Fetch from Telegram API
            token = bot.token
            url = f"{self.BASE_URL}{token}/getMe"
            
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(url)
                response.raise_for_status()
                result = response.json()
                
                if result.get('ok') and result.get('result'):
                    bot_info = result['result']
                    username = bot_info.get('username')
                    
                    # Cache in bot.config
                    if not bot.config:
                        bot.config = {}
                    bot.config['username'] = username
                    bot.config['bot_id'] = bot_info.get('id')
                    bot.config['first_name'] = bot_info.get('first_name')
                    
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(bot, 'config')
                    db.commit()
                    db.refresh(bot)  # Refresh to ensure changes are visible
                    
                    return bot_info
                else:
                    raise ValueError(f"Failed to get bot info: {result}")
        finally:
            db.close()
    
    async def handle_webhook(
        self,
        bot_id: UUID,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle Telegram webhook update.
        
        Returns normalized event data:
        {
            "event_type": "message" | "callback_query" | etc.,
            "user_external_id": "123456789",
            "text": "user message",
            "metadata": {...}
        }
        """
        if "message" in payload:
            message = payload["message"]
            # Check if it's a payment message
            if "successful_payment" in message:
                return {
                    "event_type": "successful_payment",
                    "user_external_id": str(message["from"]["id"]),
                    "text": "",
                    "metadata": {
                        "message_id": message.get("message_id"),
                        "payment": message.get("successful_payment"),
                    }
                }
            # Extract start parameter if present (for deep linking)
            start_param = None
            text = message.get("text", "")
            if text and text.startswith("/start"):
                # Telegram sends /start with parameter as: /start _tgr_xxx
                import re
                match = re.match(r'^/start\s+(.+)$', text, re.IGNORECASE)
                if match:
                    start_param = match.group(1).strip()
            
            return {
                "event_type": "message",
                "user_external_id": str(message["from"]["id"]),
                "text": text,
                "metadata": {
                    "message_id": message.get("message_id"),
                    "chat_id": message.get("chat", {}).get("id"),
                    "username": message.get("from", {}).get("username"),
                    "first_name": message.get("from", {}).get("first_name"),
                    "start_parameter": start_param,  # Include start parameter in metadata
                }
            }
        elif "callback_query" in payload:
            callback = payload["callback_query"]
            return {
                "event_type": "callback_query",
                "user_external_id": str(callback["from"]["id"]),
                "text": callback.get("data", ""),
                "metadata": {
                    "callback_query_id": callback.get("id"),
                    "message_id": callback.get("message", {}).get("message_id"),
                }
            }
        elif "pre_checkout_query" in payload:
            pre_checkout = payload["pre_checkout_query"]
            return {
                "event_type": "pre_checkout_query",
                "user_external_id": str(pre_checkout["from"]["id"]),
                "text": "",
                "metadata": {
                    "id": pre_checkout.get("id"),
                    "invoice_payload": pre_checkout.get("invoice_payload"),
                }
            }
        else:
            return {
                "event_type": "unknown",
                "user_external_id": "",
                "text": "",
                "metadata": payload
            }

