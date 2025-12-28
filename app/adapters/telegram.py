"""
Telegram adapter implementation
"""
from typing import Dict, Any
from uuid import UUID
import httpx

from app.adapters.base import BaseAdapter
from app.core.database import SessionLocal
from app.models import Bot


class TelegramAdapter(BaseAdapter):
    """Telegram platform adapter"""
    
    BASE_URL = "https://api.telegram.org/bot"
    
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
            
            url = f"{self.BASE_URL}{token}/sendMessage"
            payload = {
                "chat_id": user_external_id,
                "text": text,
                **kwargs
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
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
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json={"chat_id": user_external_id})
                response.raise_for_status()
                return response.json()
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
            return {
                "event_type": "message",
                "user_external_id": str(message["from"]["id"]),
                "text": message.get("text", ""),
                "metadata": {
                    "message_id": message.get("message_id"),
                    "chat_id": message.get("chat", {}).get("id"),
                    "username": message.get("from", {}).get("username"),
                    "first_name": message.get("from", {}).get("first_name"),
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
        else:
            return {
                "event_type": "unknown",
                "user_external_id": "",
                "text": "",
                "metadata": payload
            }

