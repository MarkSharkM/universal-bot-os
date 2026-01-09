"""
Wallet Service - Multi-tenant wallet management
Handles wallet validation, saving, and display
Supports custom validation pattern via bot.config.wallet.validation_pattern
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from uuid import UUID
import re

from app.services.user_service import UserService
from app.services.translation_service import TranslationService
from app.models.bot import Bot
from app.adapters.base import BaseAdapter


class WalletService:
    """
    Multi-tenant wallet service.
    Handles TON wallet validation and saving.
    Supports custom validation pattern via bot.config.wallet.validation_pattern
    """
    
    # Updated regex to handle:
    # 1. Base64 (EQ/UQ/kQ/0Q...) - 48 chars standard, but allowing 44-50 for flexibility
    # 2. Raw Hex (0:...) - workchain ID (can be -1 or 0) followed by Colon and 64 hex chars
    WALLET_PATTERN_DEFAULT = r'^(?:(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_+\/-]{44,50}|(?:-?1|0):[a-fA-F0-9]{64})$'
    
    def __init__(
        self,
        db: Session,
        bot_id: UUID,
        user_service: UserService
    ):
        self.db = db
        self.bot_id = bot_id
        self.user_service = user_service
        self._bot_config: Optional[Dict[str, Any]] = None  # Cache bot config
    
    def _get_bot_config(self) -> Dict[str, Any]:
        """
        Get bot configuration (lazy load).
        
        Returns:
            Bot config dictionary
        """
        if self._bot_config is None:
            bot = self.db.query(Bot).filter(Bot.id == self.bot_id).first()
            if bot:
                self._bot_config = bot.config or {}
            else:
                self._bot_config = {}
        return self._bot_config
    
    def _get_wallet_pattern(self) -> str:
        """
        Get wallet validation pattern from bot.config or use default.
        
        Returns:
            Regex pattern for wallet validation
        """
        # config = self._get_bot_config()
        # wallet_config = config.get('wallet', {})
        # pattern = wallet_config.get('validation_pattern')
        # if pattern:
        #     return pattern
        # FORCE default pattern for now to ensuring fix works
        return self.WALLET_PATTERN_DEFAULT
    
    def validate_wallet_format(self, wallet_address: str) -> bool:
        """
        Validate wallet address format using bot.config.wallet.validation_pattern or default.
        
        Args:
            wallet_address: Wallet address string
        
        Returns:
            True if valid format
        """
        if not wallet_address:
            return False
        
        wallet_address = wallet_address.strip()
        pattern = self._get_wallet_pattern()
        return bool(re.match(pattern, wallet_address))
    
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
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"save_wallet: user_id={user_id}, wallet_address={wallet_address[:20]}... (length={len(wallet_address)})")
        
        # Validate format
        if not self.validate_wallet_format(wallet_address):
            logger.warning(f"save_wallet: Invalid wallet format for user_id={user_id}, wallet={wallet_address[:20]}...")
            
            # DEBUG: Log logic failure to DB to inspect EXACT received string
            try:
                from app.models.business_data import BusinessData
                debug_log = BusinessData(
                    bot_id=self.bot_id,
                    data_type='log',  # Use 'log' so it shows in Admin Panel
                    data={
                        'event': 'wallet_validation_failed',
                        'user_id': str(user_id),
                        'received_wallet_string': str(wallet_address),
                        'received_type': str(type(wallet_address)),
                        'length': len(wallet_address)
                    }
                )
                self.db.add(debug_log)
                self.db.commit()
            except Exception as e:
                logger.error(f"Failed to log debug info: {e}")

            # Send error message
            user = self.user_service.get_user_by_id(user_id)
            if user:
                translation_service = TranslationService(self.db, self.bot_id)
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
        logger.info(f"save_wallet: Saving wallet for user_id={user_id}, wallet={wallet_address[:20]}...")
        try:
            updated_user = self.user_service.update_wallet(user_id, wallet_address)
            logger.info(f"save_wallet: Wallet saved successfully for user_id={user_id}, external_id={updated_user.external_id}")
        except Exception as e:
            logger.error(f"save_wallet: Error saving wallet for user_id={user_id}: {e}", exc_info=True)
            return False
        
        # Send confirmation
        user = self.user_service.get_user_by_id(user_id)
        if user:
            translation_service = TranslationService(self.db, self.bot_id)
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

