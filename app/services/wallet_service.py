"""
Wallet Service - Multi-tenant wallet management
Handles wallet validation, saving, and display
"""
from typing import Optional
from sqlalchemy.orm import Session
from uuid import UUID
import re

from app.services.user_service import UserService
from app.services.translation_service import TranslationService
from app.adapters.base import BaseAdapter


class WalletService:
    """
    Multi-tenant wallet service.
    Handles TON wallet validation and saving.
    """
    
    WALLET_PATTERN = r'^(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_-]{46,48}$'
    
    def __init__(
        self,
        db: Session,
        bot_id: UUID,
        user_service: UserService
    ):
        self.db = db
        self.bot_id = bot_id
        self.user_service = user_service
    
    def validate_wallet_format(self, wallet_address: str) -> bool:
        """
        Validate TON wallet address format.
        
        Args:
            wallet_address: Wallet address string
        
        Returns:
            True if valid format
        """
        if not wallet_address:
            return False
        
        wallet_address = wallet_address.strip()
        return bool(re.match(self.WALLET_PATTERN, wallet_address))
    
    async def save_wallet(
        self,
        user_id: UUID,
        wallet_address: str,
        adapter: BaseAdapter
    ) -> bool:
        """
        Validate and save wallet address.
        
        Args:
            user_id: User UUID
            wallet_address: TON wallet address
            adapter: Platform adapter for sending messages
        
        Returns:
            True if saved successfully
        """
        # Validate format
        if not self.validate_wallet_format(wallet_address):
            # Send error message
            user = self.user_service.get_user_by_id(user_id)
            if user:
                translation_service = TranslationService(self.db)
                lang = translation_service.detect_language(user.language_code)
                error_msg = translation_service.get_translation('wallet_invalid_format', lang)
                
                await adapter.send_message(
                    self.bot_id,
                    user.external_id,
                    error_msg,
                    parse_mode='HTML'
                )
            return False
        
        # Save wallet
        wallet_address = wallet_address.strip()
        self.user_service.update_wallet(user_id, wallet_address)
        
        # Send confirmation
        user = self.user_service.get_user_by_id(user_id)
        if user:
            translation_service = TranslationService(self.db)
            lang = translation_service.detect_language(user.language_code)
            success_msg = translation_service.get_translation('wallet_saved', lang)
            
            buttons = [[{
                'text': translation_service.get_translation('btn_buy_stars', lang),
                'url': 'tg://resolve?domain=wallet'
            }]]
            
            await adapter.send_message(
                self.bot_id,
                user.external_id,
                success_msg,
                reply_markup={'inline_keyboard': [[{'text': buttons[0][0]['text'], 'url': buttons[0][0]['url']}]]},
                parse_mode='HTML'
            )
        
        return True

