"""
Base adapter interface for omnichannel architecture
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID


class BaseAdapter(ABC):
    """
    Base adapter interface for all platform adapters.
    This ensures that adding new platforms (WhatsApp, Web chat, etc.)
    only requires implementing this interface, without changing service layer.
    """
    
    @abstractmethod
    async def send_message(
        self,
        bot_id: UUID,
        user_external_id: str,
        text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a message to a user on this platform.
        
        Args:
            bot_id: Bot UUID
            user_external_id: Platform-specific user ID
            text: Message text
            **kwargs: Platform-specific options (keyboard, buttons, etc.)
        
        Returns:
            Dict with platform-specific response data
        """
        pass
    
    @abstractmethod
    async def get_user_info(
        self,
        bot_id: UUID,
        user_external_id: str
    ) -> Dict[str, Any]:
        """
        Get user information from the platform.
        
        Args:
            bot_id: Bot UUID
            user_external_id: Platform-specific user ID
        
        Returns:
            Dict with user info (name, username, etc.)
        """
        pass
    
    @abstractmethod
    async def handle_webhook(
        self,
        bot_id: UUID,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle incoming webhook from the platform.
        
        Args:
            bot_id: Bot UUID
            payload: Platform-specific webhook payload
        
        Returns:
            Dict with processed event data
        """
        pass
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return platform name (telegram, web, whatsapp, etc.)"""
        pass

