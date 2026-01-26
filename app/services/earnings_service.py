"""
Earnings Service - Multi-tenant earnings center
Handles earnings display, progress tracking, 7% program info
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.services.user_service import UserService
from app.services.referral_service import ReferralService
from app.services.translation_service import TranslationService
from app.models.bot import Bot

logger = logging.getLogger(__name__)


class EarningsService:
    """
    Multi-tenant earnings service.
    Builds earnings center messages with progress, TOP status, 7% info.
    """
    
    REQUIRED_INVITES_DEFAULT = 5
    
    def __init__(
        self,
        db: Session,
        bot_id: UUID,
        user_service: UserService,
        referral_service: ReferralService,
        translation_service: TranslationService
    ):
        self.db = db
        self.bot_id = bot_id
        self.user_service = user_service
        self.referral_service = referral_service
        self.translation_service = translation_service
        self._bot_config = None  # Lazy load bot.config
    
    def _get_bot_config(self) -> dict:
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
    
    def _get_bot_username(self) -> Optional[str]:
        """
        Get bot username from bot.config.username or bot.name.
        
        Returns:
            Bot username (without @) or None if not found
        """
        config = self._get_bot_config()
        username = config.get('username')
        if username:
            return username.replace('@', '').strip()
        
        # Fallback to bot.name
        bot = self.db.query(Bot).filter(Bot.id == self.bot_id).first()
        if bot and bot.name:
            # Extract username from name (remove spaces, keep only alphanumeric and underscores)
            import re
            return re.sub(r'[^a-zA-Z0-9_]', '', bot.name).strip().lower()
        
        return None
    
    def _get_required_invites(self) -> int:
        """
        Get required invites from bot.config or use default.
        
        Returns:
            Number of required invites
        """
        config = self._get_bot_config()
        referral_config = config.get('referral', {})
        return referral_config.get('required_invites', self.REQUIRED_INVITES_DEFAULT)
    
    def _get_commission_rate(self) -> float:
        """
        Get commission rate from bot.config or use default (7%).
        
        Returns:
            Commission rate as float (e.g., 0.07 for 7%)
        """
        config = self._get_bot_config()
        earnings_config = config.get('earnings', {})
        return earnings_config.get('commission_rate', 0.07)
    
    def _get_buy_top_price_from_config(self) -> int:
        """
        Get buy TOP price from bot.config or use default (1).
        
        Returns:
            Buy TOP price in stars
        """
        config = self._get_bot_config()
        earnings_config = config.get('earnings', {})
        buy_top_price = earnings_config.get('buy_top_price')
        if buy_top_price is not None:
            try:
                return int(buy_top_price)
            except:
                pass
        return 1  # Default
    
    def build_earnings_message(
        self,
        user_id: UUID,
        user_lang: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build earnings center message.
        Replaces Build_Earnings_Message Code node logic.
        
        Args:
            user_id: User UUID
            user_lang: User's language code
        
        Returns:
            Dictionary with message text, referral_link, and metadata
        """
        logger.info(f"build_earnings_message: user_id={user_id}, user_lang={user_lang}")
        
        try:
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                logger.error(f"build_earnings_message: User {user_id} not found")
                raise ValueError(f"User {user_id} not found")
            
            lang = user_lang or user.language_code or 'en'
            lang = self.translation_service.detect_language(lang)
            logger.info(f"build_earnings_message: detected lang={lang}")
            
            # Get user data
            logger.info(f"build_earnings_message: getting wallet")
            wallet = self.user_service.get_wallet(user_id)
            earned = float(user.balance) if user.balance else 0.0
            logger.info(f"build_earnings_message: wallet={wallet}, earned={earned}, balance={user.balance}")
            logger.info(f"build_earnings_message: getting top_status")
            top_status = self.user_service.get_top_status(user_id)
            
            # Generate referral link
            logger.info(f"build_earnings_message: generating referral link")
            referral_tag = self.referral_service.generate_referral_tag(user_id)
            standard_referral_link = self.referral_service.generate_referral_link(user_id)
            
            # Check for TGR link (saved by user in Mini App) - use it if available
            tgr_link = user.custom_data.get('tgr_link') if user.custom_data else None
            referral_link = tgr_link if tgr_link else standard_referral_link
            logger.info(f"build_earnings_message: using {'tgr_link' if tgr_link else 'standard'} referral_link")
            
            # Check TOP unlock eligibility (this also gets total_invited internally)
            logger.info(f"build_earnings_message: checking top unlock eligibility")
            can_unlock, invites_needed = self.referral_service.check_top_unlock_eligibility(user_id)
            logger.info(f"build_earnings_message: can_unlock={can_unlock}, invites_needed={invites_needed}")
            
            # Get total_invited after check_top_unlock_eligibility (uses cache from previous call)
            logger.info(f"build_earnings_message: getting total_invited")
            total_invited = self.referral_service.get_total_invited(user_id)
        except Exception as e:
            logger.error(f"build_earnings_message: error getting user data: {e}", exc_info=True)
            raise
        
        # Build message parts
        message_parts = []
        
        # Header
        # Show wallet info if wallet exists (non-empty) OR if earned > 0 (user has earnings even without wallet set)
        # Show "no income" only if no wallet AND no earnings
        has_wallet = wallet and wallet.strip()  # Check for non-empty wallet
        logger.info(f"build_earnings_message: has_wallet={has_wallet}, earned={earned}, condition={has_wallet or earned > 0}")
        if has_wallet or earned > 0:
            # If wallet exists, show it; otherwise show just earned amount
            wallet_display = wallet if has_wallet else 'N/A'
            header = self.translation_service.get_translation(
                'earnings_has_income',
                lang,
                {'wallet': wallet_display, 'earned': earned}
            )
            logger.info(f"build_earnings_message: using earnings_has_income header")
        else:
            header = self.translation_service.get_translation('earnings_no_income', lang)
            logger.info(f"build_earnings_message: using earnings_no_income header")
        
        title = self.translation_service.get_translation('earnings_title', lang)
        message_parts.append(f"<b>{title}</b>\n\n{header}\n")
        
        # Block 1: TOP unlock progress
        block1 = self._build_top_block(lang, total_invited, invites_needed, referral_link, can_unlock)
        message_parts.append(block1)
        
        # Block 2: 7% program
        block2 = self._build_7percent_block(lang)
        message_parts.append(block2)
        
        # Block 3: What to do now
        block3 = self._build_action_block(lang, can_unlock, invites_needed)
        message_parts.append(block3)
        
        message_text = "\n\n".join(message_parts)
        
        return {
            'text': message_text,
            'lang': lang,  # Include language for button translations
            'referral_link': referral_link,
            'invites': total_invited,
            'needed': invites_needed,
            'wallet': wallet or '',
            'earned': earned,
            'top_status': top_status,
        }
    
    def _build_top_block(
        self,
        lang: str,
        total_invited: int,
        invites_needed: int,
        referral_link: str,
        can_unlock: bool
    ) -> str:
        """Build TOP unlock progress block"""
        block_title = self.translation_service.get_translation('earnings_block1_title', lang)
        
        # Progress bar
        total_steps = self._get_required_invites()
        filled = min(total_invited, total_steps)
        bar_filled = '🟩' * filled
        bar_empty = '⬜️' * (total_steps - filled)
        bar = bar_filled + bar_empty
        
        # Friends label (language-specific)
        friends_map = {
            'uk': 'друзів',
            'en': 'friends',
            'ru': 'друзей',
            'de': 'Freunde',
            'es': 'amigos',
        }
        friends_label = friends_map.get(lang, 'friends')
        
        # To TOP label
        to_top_map = {
            'uk': 'до TOP',
            'en': 'to TOP',
            'ru': 'до TOP',
            'de': 'bis TOP',
            'es': 'hasta TOP',
        }
        to_top_label = to_top_map.get(lang, 'to TOP')
        
        line1 = self.translation_service.get_translation('earnings_block1_line1', lang)
        benefit1 = self.translation_service.get_translation('earnings_block1_benefit1', lang)
        benefit2 = self.translation_service.get_translation('earnings_block1_benefit2', lang)
        benefit3 = self.translation_service.get_translation('earnings_block1_benefit3', lang)
        
        ref_label_map = {
            'uk': '🔗 Твоя реферальна лінка:',
            'en': '🔗 Your referral link:',
            'ru': '🔗 Твоя реферальная ссылка:',
            'de': '🔗 Dein Empfehlungslink:',
            'es': '🔗 Tu enlace de referido:',
        }
        ref_label = ref_label_map.get(lang, '🔗 Your referral link:')
        
        block = f"""━━━━━━━━━━
<b>{block_title}</b>

👥 {total_invited} / {total_steps} {friends_label}
{bar}  +{invites_needed} {to_top_label}
({self.translation_service.get_translation('earnings_btn_unlock_top', lang, {'price': self._get_buy_top_price_from_config(), 'buy_top_price': self._get_buy_top_price_from_config()})})

{ref_label}
{referral_link}

{line1}
{benefit1}
{benefit2}
{benefit3}"""
        
        return block
    
    def _build_7percent_block(self, lang: str) -> str:
        """Build commission program block (configurable %)"""
        commission_rate = self._get_commission_rate()
        commission_percent = int(commission_rate * 100)  # Convert 0.07 to 7
        
        # Get bot username for translation variables
        bot_username = self._get_bot_username() or ''
        
        block_title = self.translation_service.get_translation('earnings_block2_title', lang)
        how_it_works = self.translation_service.get_translation('earnings_block2_how_it_works', lang, {
            'bot_username': bot_username
        })
        examples = self.translation_service.get_translation('earnings_block2_examples', lang)
        enable_title = self.translation_service.get_translation('earnings_enable_7_title', lang)
        enable_steps = self.translation_service.get_translation('earnings_enable_7_steps', lang, {
            'bot_username': bot_username
        })
        
        # Replace commission rate in translations if they contain placeholders
        # Note: Translations should use {{commission}} or [[commission]] placeholder
        how_it_works = how_it_works.replace('{{commission}}', str(commission_percent)).replace('[[commission]]', str(commission_percent))
        examples = examples.replace('{{commission}}', str(commission_percent)).replace('[[commission]]', str(commission_percent))
        
        block = f"""━━━━━━━━━━
<b>{block_title}</b>

{how_it_works}

{examples}

<b>{enable_title}</b>
{enable_steps}"""
        
        return block
    
    def _build_action_block(
        self,
        lang: str,
        can_unlock: bool,
        invites_needed: int
    ) -> str:
        """Build 'What to do now' block"""
        block_title = self.translation_service.get_translation('earnings_block3_title', lang)
        
        if can_unlock:
            step1 = self.translation_service.get_translation('earnings_step1_open', lang)
        else:
            step1 = self.translation_service.get_translation(
                'earnings_step1_locked',
                lang,
                {'needed': invites_needed, 'price': self._get_buy_top_price_from_config(), 'buy_top_price': self._get_buy_top_price_from_config()}
            )
        
        step2 = self.translation_service.get_translation('earnings_step2', lang)
        step3 = self.translation_service.get_translation('earnings_step3', lang)
        step4 = self.translation_service.get_translation('earnings_step4', lang)
        auto_stats = self.translation_service.get_translation('earnings_auto_stats', lang)
        
        block = f"""━━━━━━━━━━
<b>{block_title}</b>

{step1}
{step2}
{step3}
{step4}

{auto_stats}"""
        
        return block
    
    def get_earnings_data(
        self,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get earnings data as structured JSON (for Mini Apps).
        Unlike build_earnings_message() which returns HTML, this returns clean JSON.
        
        Args:
            user_id: User UUID
        
        Returns:
            Dictionary with earnings data (structured for JSON API)
        """
        logger.info(f"get_earnings_data: user_id={user_id}")
        
        try:
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                logger.error(f"get_earnings_data: User {user_id} not found")
                raise ValueError(f"User {user_id} not found")
            
            # Get user data
            wallet = self.user_service.get_wallet(user_id)
            earned = float(user.balance) if user.balance else 0.0
            top_status = self.user_service.get_top_status(user_id)
            
            # Generate referral link
            referral_tag = self.referral_service.generate_referral_tag(user_id)
            referral_link = self.referral_service.generate_referral_link(user_id)
            
            # Check TOP unlock eligibility
            can_unlock, invites_needed = self.referral_service.check_top_unlock_eligibility(user_id)
            total_invited = self.referral_service.get_total_invited(user_id)
            
            # Get config values
            required_invites = self._get_required_invites()
            commission_rate = self._get_commission_rate()
            buy_top_price = self._get_buy_top_price_from_config()
            
            return {
                "earned": earned,
                "wallet": wallet or "",
                "top_status": top_status,  # "locked" or "open"
                "can_unlock_top": can_unlock,
                "invites_needed": invites_needed,
                "total_invited": total_invited,
                "required_invites": required_invites,
                "referral_link": referral_link,
                "referral_tag": referral_tag,
                "commission_rate": commission_rate,
                "buy_top_price": buy_top_price,
            }
            
        except Exception as e:
            logger.error(f"get_earnings_data: error getting user data: {e}", exc_info=True)
            raise

